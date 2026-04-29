"""Análise de pesquisas com Claude (Anthropic).

Identifica candidatos mencionados, gera insights estratégicos e sugere
atualizações ao status_pt_estado. Roda apenas se ANTHROPIC_API_KEY estiver
configurada — caso contrário retorna 'skip' graciosamente.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Estado, Pessoa
from app.models.editorial import StatusPTEstado
from app.models.poll import PesquisaDadosBrutos

logger = logging.getLogger("ai_poll_analyzer")


# Prompt cacheável: estável entre chamadas (políticos cadastrados muda pouco)
SYSTEM_PROMPT = """Você é analista político brasileiro experiente, especializado em pesquisas eleitorais.

Sua tarefa: receber um JSON estruturado de uma pesquisa eleitoral (formato Quaest e similares) e produzir uma análise objetiva, em português, focada no impacto para o Partido dos Trabalhadores (PT) e seus aliados.

Você responde sempre em JSON estrito, sem markdown ao redor, sem texto antes ou depois. Ignore campos de margem de erro e cruzamentos sociodemográficos detalhados — foque no quadro político.
"""


def _make_user_prompt(json_data: dict, pessoas_cadastradas: list[str]) -> str:
    """Monta prompt do usuário (volátil — JSON da pesquisa muda)."""
    return f"""Analise esta pesquisa eleitoral e retorne JSON estrito com a estrutura abaixo.

PESQUISA:
{json.dumps(json_data, ensure_ascii=False, indent=2)[:9000]}

POLÍTICOS JÁ CADASTRADOS NA PLATAFORMA (use match exato quando aplicável):
{chr(10).join(pessoas_cadastradas[:200])}

Retorne JSON com esta estrutura exata:
{{
  "candidatos_identificados": [
    {{
      "nome": "string (nome como aparece na pesquisa)",
      "match_existente": "string ou null (nome exato da lista acima se houver match)",
      "cargo_provavel": "governador|senador|deputado_federal|outro",
      "papel_na_pesquisa": "avaliado|pre_candidato|mencionado",
      "destaque_numerico": "string opcional (ex: '56% aprovação', '34% intenção')"
    }}
  ],
  "tendencias_observadas": [
    {{
      "metrica": "string (ex: 'aprovação Jerônimo', 'intenção governo')",
      "direcao": "subindo|estavel|caindo",
      "magnitude": "string (ex: '-3pp em 6 meses')",
      "implicacao": "string curta"
    }}
  ],
  "alertas": [
    {{
      "tipo": "atencao|risco|oportunidade",
      "descricao": "string max 200 chars",
      "prioridade": 1
    }}
  ],
  "implicacoes_pt": "string max 600 chars — análise estratégica focada no PT, base aliada e governo Lula no estado",
  "sugestao_status_estado": {{
    "nivel_consolidacao_sugerido": "consolidado|em_construcao|disputado|adverso|null",
    "justificativa": "string max 300 chars",
    "confianca": 0.0
  }},
  "resumo_executivo": "string max 400 chars — 2-3 frases sintetizando o ponto principal"
}}

Diretrizes:
- Use match_existente APENAS se houver correspondência muito clara com a lista
- alertas: máximo 5, ordenados por relevância
- tendencias: máximo 4
- candidatos: liste apenas os realmente mencionados nominalmente
- Tom: analítico, direto, sem floreio
- NÃO inclua texto fora do JSON
"""


def _parse_json_resposta(texto: str) -> dict | None:
    """Extrai JSON da resposta do Claude (lida com markdown opcional)."""
    texto = texto.strip()
    if texto.startswith("```"):
        # remove ```json ... ```
        linhas = texto.split("\n")
        # primeira linha e última são fences
        linhas = [l for l in linhas if not l.strip().startswith("```")]
        texto = "\n".join(linhas)
    try:
        return json.loads(texto)
    except json.JSONDecodeError as e:
        logger.warning(f"Falha ao parsear JSON da IA: {e}")
        return None


def analisar_pesquisa(
    db: Session,
    json_data: dict,
    pesquisa_id: str | None = None,
) -> dict:
    """Analisa a pesquisa via Claude e (opcionalmente) salva o resultado.

    Retorna dict com {status, analise?, custo_estimado_centavos, mensagem}.
    """
    if not settings.anthropic_api_key:
        return {
            "status": "skip",
            "mensagem": "ANTHROPIC_API_KEY não configurada — análise IA pulada. Configure em backend/.env para habilitar.",
        }

    try:
        import anthropic
    except ImportError:
        return {"status": "erro", "mensagem": "SDK anthropic não instalada"}

    # Lista de políticos cadastrados (limita a 200 para não estourar prompt)
    pessoas = (
        db.query(Pessoa.nome_completo)
        .filter(Pessoa.deleted_at.is_(None))
        .order_by(Pessoa.nome_completo)
        .limit(200)
        .all()
    )
    pessoas_str = [p[0] for p in pessoas]

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    try:
        # Usa prompt caching no SYSTEM_PROMPT (estável entre chamadas)
        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2500,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": _make_user_prompt(json_data, pessoas_str),
                }
            ],
        )
    except Exception as e:
        logger.exception("Erro ao chamar Claude")
        return {"status": "erro", "mensagem": str(e)[:300]}

    response_text = msg.content[0].text
    analise = _parse_json_resposta(response_text)

    # Custo estimado: Haiku 4.5 — $1/MTok input, $5/MTok output, $1.25 cache write, $0.10 cache read
    input_tokens = msg.usage.input_tokens
    output_tokens = msg.usage.output_tokens
    cache_read = getattr(msg.usage, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(msg.usage, "cache_creation_input_tokens", 0) or 0

    # Tokens de input "regulares" (não-cache)
    input_regular = max(input_tokens - cache_read - cache_write, 0)

    # Custo em USD: tokens × ($/MTok) / 1_000_000
    custo_usd = (
        input_regular * 1.0
        + cache_write * 1.25
        + cache_read * 0.10
        + output_tokens * 5.0
    ) / 1_000_000

    # BRL ≈ 5× USD (taxa aproximada). Centavos = USD × 5 × 100
    custo_centavos = int(round(custo_usd * 5 * 100))

    # Salva análise no PesquisaDadosBrutos se pesquisa_id foi fornecido
    if pesquisa_id and analise:
        bruto = (
            db.query(PesquisaDadosBrutos)
            .filter(PesquisaDadosBrutos.pesquisa_id == pesquisa_id)
            .first()
        )
        if bruto:
            bruto.analise_ia_json = json.dumps(analise, ensure_ascii=False)
            db.commit()

    return {
        "status": "ok" if analise else "erro_parse",
        "analise": analise,
        "raw_response": response_text if not analise else None,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read,
        "cache_write_tokens": cache_write,
        "custo_estimado_centavos": custo_centavos,
        "modelo": "claude-haiku-4-5",
    }


def aplicar_sugestao_status(
    db: Session,
    estado_id: str,
    analise: dict,
    usuario_id: str | None = None,
) -> dict:
    """Aplica a sugestão de status_estado ao banco, se confiança ≥ 0.7."""
    sug = analise.get("sugestao_status_estado") or {}
    nivel = sug.get("nivel_consolidacao_sugerido")
    conf = sug.get("confianca", 0)

    if not nivel or nivel == "null" or conf < 0.7:
        return {"aplicado": False, "motivo": f"confiança baixa ({conf}) ou sem sugestão"}

    s = db.query(StatusPTEstado).filter(StatusPTEstado.estado_id == estado_id).first()
    if not s:
        return {"aplicado": False, "motivo": "status_pt_estado não existe"}

    nivel_anterior = s.nivel_consolidacao
    s.nivel_consolidacao = nivel
    obs_existente = s.observacao_geral or ""
    nova_obs = f"[IA {analise.get('resumo_executivo', '')[:200]}]"
    s.observacao_geral = (obs_existente + "\n" + nova_obs)[:2000] if obs_existente else nova_obs
    s.atualizado_por = usuario_id

    db.commit()
    return {
        "aplicado": True,
        "nivel_anterior": nivel_anterior,
        "nivel_novo": nivel,
        "justificativa": sug.get("justificativa"),
    }
