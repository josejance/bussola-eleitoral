"""Classificação automática do posicionamento_governo de votações via Claude.

Para cada votação sem classificação humana, usa Claude Haiku para sugerir:
- a_favor (governo apoia aprovação)
- contra (governo é contra aprovação)
- liberada (votação liberada, sem orientação fechada)
- sem_orientacao (matéria interna do legislativo)

Sugestão fica em `classificacao_ia_sugerida` + `classificacao_ia_confianca`.
Se confiança ≥ 0.85 e auto-aprovação ativa, vira `posicionamento_governo`.
"""
from __future__ import annotations

import json
import logging
from typing import Iterable

from sqlalchemy.orm import Session

from app.config import settings
from app.models import VotacaoCongresso

logger = logging.getLogger("ai_votacao")

SYSTEM_PROMPT = """Você é analista político brasileiro. Sua tarefa é classificar votações no Congresso \
quanto à provável posição do governo Lula (PT, gestão 2023+).

Considere:
- Pautas econômicas progressivas / distributivas / proteção social → A FAVOR
- Pautas conservadoras / redutoras de direitos / anti-ambientais → CONTRA
- Matérias administrativas internas / homenagens / regimentais → SEM ORIENTAÇÃO
- Pautas técnicas com divisão da base → LIBERADA
- Quando incerto, prefira "desconhecido"

Responda APENAS com JSON estrito, sem texto adicional, sem markdown."""


def classificar_lote(
    db: Session,
    votacao_ids: Iterable[str] | None = None,
    limit: int = 30,
    apenas_sem_classificacao: bool = True,
) -> dict:
    """Classifica lote de votações via Claude.

    Se votacao_ids não fornecido, pega as N mais recentes sem classificação.
    """
    if not settings.anthropic_api_key:
        return {"status": "skip", "mensagem": "ANTHROPIC_API_KEY não configurada"}

    try:
        import anthropic
    except ImportError:
        return {"status": "erro", "mensagem": "SDK anthropic não instalada"}

    q = db.query(VotacaoCongresso)
    if votacao_ids:
        q = q.filter(VotacaoCongresso.id.in_(list(votacao_ids)))
    if apenas_sem_classificacao:
        q = q.filter(VotacaoCongresso.posicionamento_governo == "desconhecido")
        q = q.filter(VotacaoCongresso.classificacao_ia_sugerida.is_(None))
    q = q.order_by(VotacaoCongresso.data.desc()).limit(limit)

    votacoes = q.all()
    if not votacoes:
        return {"status": "ok", "classificadas": 0, "mensagem": "Nenhuma votação pendente"}

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    sumario = {
        "classificadas": 0,
        "auto_aprovadas": 0,
        "tokens_total": 0,
        "custo_centavos": 0,
        "por_classe": {"a_favor": 0, "contra": 0, "liberada": 0, "sem_orientacao": 0, "desconhecido": 0},
    }

    for vot in votacoes:
        ementa = (vot.ementa or "")[:500]
        descricao = (vot.descricao_completa or "")[:1000]

        user_msg = f"""Classifique esta votação:

Data: {vot.data}
Tipo: {vot.tipo_proposicao or '?'} {vot.numero or ''}/{vot.ano or '?'}
Ementa: {ementa}
Descrição: {descricao}

Responda em JSON:
{{
  "classificacao": "a_favor|contra|liberada|sem_orientacao|desconhecido",
  "confianca": 0.0,
  "tema": "economia|tributacao|ambiente|saude|educacao|seguranca|direitos|internacional|administrativa|outros",
  "justificativa": "máx 200 chars"
}}"""

        try:
            msg = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=300,
                system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user_msg}],
            )
            resp = msg.content[0].text.strip()
            # Remove markdown se houver
            if resp.startswith("```"):
                resp = "\n".join(resp.split("\n")[1:-1])

            try:
                analise = json.loads(resp)
            except json.JSONDecodeError:
                logger.warning(f"JSON inválido para {vot.id}: {resp[:100]}")
                continue

            classe = analise.get("classificacao", "desconhecido")
            confianca = float(analise.get("confianca", 0))
            tema = analise.get("tema")

            vot.classificacao_ia_sugerida = classe
            vot.classificacao_ia_confianca = confianca
            if tema:
                vot.tema = tema

            # Auto-aprova se confiança alta
            if confianca >= 0.85 and classe != "desconhecido":
                vot.posicionamento_governo = classe
                sumario["auto_aprovadas"] += 1

            sumario["classificadas"] += 1
            sumario["por_classe"][classe] = sumario["por_classe"].get(classe, 0) + 1

            # Custo: Haiku ~$1/MTok input + $5/MTok output
            it = msg.usage.input_tokens
            ot = msg.usage.output_tokens
            sumario["tokens_total"] += it + ot
            custo_usd = (it * 1.0 + ot * 5.0) / 1_000_000
            sumario["custo_centavos"] += int(round(custo_usd * 5 * 100))

        except Exception as e:
            logger.warning(f"Erro classificando {vot.id}: {e}")

    db.commit()
    return {"status": "ok", **sumario}


def main():
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        s = classificar_lote(db, limit=30)
        print(s)
    finally:
        db.close()


if __name__ == "__main__":
    main()
