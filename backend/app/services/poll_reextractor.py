"""Re-extrator de pesquisas Quaest a partir do JSON bruto.

Substitui a extração superficial original por uma profunda:
- Para Aprovação/Avaliação: cada PERÍODO da série histórica vira uma AvaliacaoGoverno
- Para Intenção de Voto: cada CENÁRIO vira N IntencaoVoto, com cenario_label preservado
- Cruzamentos sociodemográficos guardados em `recorte_json` quando estruturados
- Detecta avaliado real (Lula, Jerônimo, etc) por nome explícito no título da questão
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    AvaliacaoGoverno,
    IntencaoVoto,
    Pesquisa,
    Pessoa,
)
from app.models.poll import PesquisaDadosBrutos

logger = logging.getLogger("reextractor")


# ===== Mapeamento de período (Mês/Ano) → date =====

MESES_PT = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}


def _parse_periodo(s: str) -> date | None:
    """Aceita 'Janeiro/2026', 'Jan/26', 'Abril/2025', 'Abr/24' etc."""
    if not s or not isinstance(s, str):
        return None
    s_lower = s.lower().strip().replace(" ", "")
    m = re.match(r"([a-zãç]+)[\/\-](\d{2,4})", s_lower)
    if not m:
        return None
    mes_str, ano_str = m.groups()
    mes = MESES_PT.get(mes_str[:3]) or MESES_PT.get(mes_str)
    if not mes:
        return None
    ano = int(ano_str)
    if ano < 100:
        ano = 2000 + ano
    # Último dia do mês para ordenação cronológica consistente
    import calendar
    ultimo = calendar.monthrange(ano, mes)[1]
    try:
        return date(ano, mes, ultimo)
    except ValueError:
        return None


# ===== Detector de cargo / pessoa =====

# Mapeamento explícito de termos comuns → nome canônico no banco
NOMES_CANONICOS = {
    "lula": "Luiz Inácio Lula da Silva",
    "luiz inácio lula": "Luiz Inácio Lula da Silva",
    "jerônimo rodrigues": "Jerônimo Rodrigues",
    "jeronimo rodrigues": "Jerônimo Rodrigues",
    "fernando haddad": "Fernando Haddad",
    "tarcísio de freitas": "Tarcísio de Freitas",
    "tarcisio de freitas": "Tarcísio de Freitas",
    "ratinho júnior": "Ratinho Júnior",
    "ratinho junior": "Ratinho Júnior",
    "ronaldo caiado": "Ronaldo Caiado",
    "eduardo leite": "Eduardo Leite",
    "romeu zema": "Romeu Zema",
    "rodrigo pacheco": "Rodrigo Pacheco",
    "pacheco": "Rodrigo Pacheco",
    "eduardo paes": "Eduardo Paes",
    "cláudio castro": "Cláudio Castro",
    "claudio castro": "Cláudio Castro",
    "raquel lyra": "Raquel Lyra",
    "joão campos": "João Campos",
    "joao campos": "João Campos",
    "elmano de freitas": "Elmano de Freitas",
    "rafael fonteles": "Rafael Fonteles",
    "renan filho": "Renan Filho",
    "flávio bolsonaro": "Flávio Bolsonaro",
    "flavio bolsonaro": "Flávio Bolsonaro",
    "jair bolsonaro": "Jair Bolsonaro",
    "bolsonaro": "Jair Bolsonaro",
    "simone tebet": "Simone Tebet",
    "marina silva": "Marina Silva",
}


def _detectar_pessoa_avaliada(db: Session, titulo: str) -> tuple[Pessoa | None, str]:
    """Retorna (Pessoa, cargo). Cargo: 'presidente' / 'governador' / 'outro'."""
    if not titulo:
        return None, "outro"
    t = titulo.lower()
    cargo = "presidente" if "presidente" in t else "governador" if "governador" in t else "outro"

    # 1) Match contra nomes canônicos (precisão alta)
    for termo, nome_canonico in NOMES_CANONICOS.items():
        if termo in t:
            p = db.query(Pessoa).filter(Pessoa.nome_completo == nome_canonico).first()
            if p:
                return p, cargo
            # Fallback ilike
            p = db.query(Pessoa).filter(Pessoa.nome_completo.ilike(f"%{nome_canonico}%")).first()
            if p:
                return p, cargo

    # 2) Procura nome próprio (sequência de palavras capitalizadas) — última opção
    matches = re.findall(r"\b([A-ZÁ-Ú][a-zá-ú]+(?:\s+[A-ZÁ-Ú][a-zá-ú]+){1,3})\b", titulo)
    for m in matches:
        if m.lower() in ("este governo", "do governo", "ao governo"):
            continue
        # Match exato primeiro
        p = db.query(Pessoa).filter(Pessoa.nome_completo == m).first()
        if p:
            return p, cargo

    return None, cargo


# ===== Extração de aprovação/avaliação com SÉRIE HISTÓRICA =====

def extrair_avaliacao(item: dict) -> dict:
    """Mapeia opções → campos do model AvaliacaoGoverno.

    Aceita variações: "- Aprova", "Aprova", "Aprovação", "Positivo", "Ótimo+Bom".
    """
    out = {"aprova": None, "desaprova": None, "otimo_bom": None, "regular": None,
           "ruim_pessimo": None, "nao_sabe": None}
    if not isinstance(item, dict):
        return out

    # Item pode ter chaves diretas (formato antigo) OU lista de {opcao, percentual}
    # Tenta direto:
    if "aprova" in item or "Aprova" in item:
        out["aprova"] = _f(item.get("aprova") or item.get("Aprova"))
    if "desaprova" in item:
        out["desaprova"] = _f(item.get("desaprova"))
    if "otimo_bom" in item or "positivo" in item:
        out["otimo_bom"] = _f(item.get("otimo_bom") or item.get("positivo"))
    if "regular" in item:
        out["regular"] = _f(item.get("regular"))
    if "ruim_pessimo" in item or "negativo" in item:
        out["ruim_pessimo"] = _f(item.get("ruim_pessimo") or item.get("negativo"))
    if "ns_nr" in item or "nao_sabe" in item:
        out["nao_sabe"] = _f(item.get("ns_nr") or item.get("nao_sabe"))

    return out


def _f(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.replace(",", ".").strip().rstrip("%").strip()
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _opcoes_para_avaliacao(opcoes: list[dict]) -> dict:
    """Converte lista [{opcao, percentual}] em dict aprova/desaprova/etc."""
    out = {"aprova": None, "desaprova": None, "otimo_bom": None, "regular": None,
           "ruim_pessimo": None, "nao_sabe": None}
    for item in opcoes:
        if not isinstance(item, dict):
            continue
        opcao = (item.get("opcao") or item.get("alternativa") or "").lower().strip(" -")
        pct = _f(item.get("percentual") or item.get("pct"))
        if pct is None:
            continue
        if "aprova" in opcao and "desaprova" not in opcao:
            out["aprova"] = pct
        elif "desaprova" in opcao:
            out["desaprova"] = pct
        elif "ótimo" in opcao or "otimo" in opcao or "bom" in opcao or "positivo" in opcao:
            out["otimo_bom"] = (out["otimo_bom"] or 0) + pct  # acumula ótimo+bom se vierem separados
        elif "regular" in opcao:
            out["regular"] = pct
        elif "ruim" in opcao or "péssimo" in opcao or "pessimo" in opcao or "negativo" in opcao:
            out["ruim_pessimo"] = (out["ruim_pessimo"] or 0) + pct
        elif "ns/nr" in opcao or "ns" in opcao.split() or "não sabe" in opcao or "nao sabe" in opcao:
            out["nao_sabe"] = pct
    return out


def processar_questao_avaliacao(
    db: Session,
    pesquisa: Pesquisa,
    questao: dict,
    titulo_q: str,
    estatisticas: dict,
    abrangencia: str,
):
    """Processa uma questão de aprovação/avaliação. Cria AvaliacaoGoverno
    para cada período da série histórica (se houver).
    """
    pessoa_avaliada, cargo = _detectar_pessoa_avaliada(db, titulo_q)
    nivel = "presidencial" if cargo == "presidente" else "estadual" if cargo == "governador" else (
        "presidencial" if abrangencia == "nacional" else "estadual"
    )
    cargo_norm = "presidente" if nivel == "presidencial" else "governador"

    dados_gerais = questao.get("dados_gerais")

    if isinstance(dados_gerais, list) and dados_gerais:
        # Caso 1: lista de {opcao, percentual} (formato compacto)
        if all(isinstance(x, dict) and "opcao" in x for x in dados_gerais):
            valores = _opcoes_para_avaliacao(dados_gerais)
            db.add(AvaliacaoGoverno(
                pesquisa_id=pesquisa.id,
                nivel=nivel,
                pessoa_avaliada_id=pessoa_avaliada.id if pessoa_avaliada else None,
                cargo_avaliado=cargo_norm,
                periodo_referencia=pesquisa.data_fim_campo,
                **valores,
            ))
            estatisticas["avaliacoes"] += 1
            return

        # Caso 2: lista de períodos [{periodo, aprova, desaprova, ...}]
        if all(isinstance(x, dict) and ("periodo" in x or "aprova" in x or "positivo" in x) for x in dados_gerais):
            for item in dados_gerais:
                periodo_str = item.get("periodo") or item.get("data") or ""
                data_periodo = _parse_periodo(periodo_str) or pesquisa.data_fim_campo
                aval_data = extrair_avaliacao(item)

                db.add(AvaliacaoGoverno(
                    pesquisa_id=pesquisa.id,
                    nivel=nivel,
                    pessoa_avaliada_id=pessoa_avaliada.id if pessoa_avaliada else None,
                    cargo_avaliado=cargo_norm,
                    periodo_referencia=data_periodo,
                    **aval_data,
                ))
                estatisticas["avaliacoes"] += 1


def processar_questao_intencao(
    db: Session,
    pesquisa: Pesquisa,
    questao: dict,
    titulo_q: str,
    cenario_label: str,
    estatisticas: dict,
):
    """Processa uma questão de intenção de voto. Cria IntencaoVoto por candidato com cenario_label."""
    dados_gerais = questao.get("dados_gerais")

    candidatos = []

    if isinstance(dados_gerais, list):
        for item in dados_gerais:
            if not isinstance(item, dict):
                continue
            nome = item.get("opcao") or item.get("nome") or item.get("candidato")
            pct = _f(item.get("percentual") or item.get("pct"))
            if nome and pct is not None:
                candidatos.append((nome, pct))
    elif isinstance(dados_gerais, dict):
        # Pode ser dict {Cenario1: [...], Cenario2: [...]}
        for sub_cenario, lista in dados_gerais.items():
            if not isinstance(lista, list):
                continue
            for item in lista:
                if not isinstance(item, dict):
                    continue
                nome = item.get("opcao") or item.get("nome") or item.get("candidato")
                pct = _f(item.get("percentual") or item.get("pct"))
                if nome and pct is not None:
                    candidatos.append((f"{nome}", pct))

    for posicao, (nome, pct) in enumerate(candidatos, start=1):
        pessoa = None
        # Limpa "- Lula (PT)" → "Lula"
        nome_limpo = re.sub(r"\s*\([^)]*\)", "", nome).strip().lstrip("- ").strip()
        nome_limpo_lower = nome_limpo.lower()
        if nome_limpo and nome_limpo_lower not in ("branco", "nulo", "ns/nr", "não vai votar", "nao vai votar", "indeciso", "indecisos", "branco/nulo/não vai votar", "outros"):
            # 1) Match canônico (alta precisão)
            nome_canonico = NOMES_CANONICOS.get(nome_limpo_lower)
            if nome_canonico:
                pessoa = db.query(Pessoa).filter(Pessoa.nome_completo == nome_canonico).first()
            # 2) Match exato no nome_urna
            if not pessoa:
                pessoa = db.query(Pessoa).filter(Pessoa.nome_urna == nome_limpo).first()
            # 3) Match exato no nome_completo
            if not pessoa:
                pessoa = db.query(Pessoa).filter(Pessoa.nome_completo == nome_limpo).first()
            # 4) ilike (último recurso, pode trazer falso positivo)
            if not pessoa:
                pessoa = db.query(Pessoa).filter(Pessoa.nome_urna.ilike(f"%{nome_limpo}%")).first()

        # Extrai partido entre parênteses
        partido_match = re.search(r"\(([A-Za-z]+)\)", nome)
        partido_sigla = partido_match.group(1).upper() if partido_match else None
        partido_id = None
        if partido_sigla:
            from app.models import Partido
            p = db.query(Partido).filter(Partido.sigla == partido_sigla).first()
            partido_id = p.id if p else None

        recorte = json.dumps({"cenario": cenario_label}, ensure_ascii=False)

        db.add(IntencaoVoto(
            pesquisa_id=pesquisa.id,
            pessoa_id=pessoa.id if pessoa else None,
            partido_referencia_id=partido_id,
            nome_referencia=nome[:150],
            percentual=pct,
            posicao_no_cenario=posicao,
            recorte_json=recorte,
        ))
        estatisticas["intencoes"] += 1


# ===== Entry point =====

def reextrair_pesquisa(db: Session, pesquisa_id: str) -> dict:
    """Re-extrai uma pesquisa a partir do seu JSON bruto.

    Apaga avaliacoes/intencoes existentes e reprocessa.
    """
    pesquisa = db.query(Pesquisa).filter(Pesquisa.id == pesquisa_id).first()
    if not pesquisa:
        raise ValueError(f"Pesquisa {pesquisa_id} não encontrada")

    bruto = db.query(PesquisaDadosBrutos).filter(PesquisaDadosBrutos.pesquisa_id == pesquisa_id).first()
    if not bruto:
        return {"status": "skip", "motivo": "Sem JSON bruto"}

    data = json.loads(bruto.dados_json)
    root = data.get("pesquisa", data)
    resultados = root.get("resultados", {})
    if not isinstance(resultados, dict):
        return {"status": "skip", "motivo": "Resultados não é dict"}

    # Apaga existentes
    db.query(IntencaoVoto).filter(IntencaoVoto.pesquisa_id == pesquisa_id).delete()
    db.query(AvaliacaoGoverno).filter(AvaliacaoGoverno.pesquisa_id == pesquisa_id).delete()
    db.flush()

    abrangencia = pesquisa.abrangencia or "nacional"
    estatisticas = {"avaliacoes": 0, "intencoes": 0, "questoes_processadas": 0}

    for k, q in resultados.items():
        if not isinstance(q, dict):
            continue
        titulo = q.get("titulo") or q.get("enunciado") or k
        # Combina título + chave para detecção (chaves snake_case têm "aprovacao_governo_X")
        texto_busca = f"{titulo} {k}".lower().replace("_", " ")

        # Identifica tipo: aprovação
        eh_aprovacao = any(
            kw in texto_busca
            for kw in ["aprovação do governo", "aprovacao do governo", "aprova ou desaprova",
                       "aprovacao governo", "aprova governo"]
        )
        # Avaliação ótimo/bom/regular
        eh_avaliacao = (
            "avaliação do governo" in texto_busca
            or "avaliacao do governo" in texto_busca
            or "avaliacao governo" in texto_busca
            or ("avalia" in texto_busca and any(x in texto_busca for x in ["ótimo", "otimo", "regular", "bom"]))
        )
        # Intenção de voto
        eh_intencao = (
            "intenção" in texto_busca
            or "intencao" in texto_busca
            or "voto para" in texto_busca
            or "intencao voto" in texto_busca
            or "intencao_voto" in texto_busca
        )

        if eh_aprovacao or eh_avaliacao:
            # Para chaves snake_case (BA), usa o título da pergunta interna como nome
            titulo_real = q.get("titulo") or q.get("enunciado") or _humanizar_chave(k)
            processar_questao_avaliacao(db, pesquisa, q, titulo_real, estatisticas, abrangencia)
            estatisticas["questoes_processadas"] += 1
        elif eh_intencao:
            titulo_real = q.get("titulo") or q.get("enunciado") or _humanizar_chave(k)
            m = re.search(r"cen[áa]rio[s]?\s*([IVX]+|\d+)", titulo_real, re.IGNORECASE)
            cenario_label = m.group(0) if m else "Cenário único"
            if "1º turno" in titulo_real or "1 turno" in titulo_real:
                cenario_label = f"1T - {cenario_label}"
            elif "2º turno" in titulo_real or "2 turno" in titulo_real:
                cenario_label = f"2T - {cenario_label}"
            elif "espontânea" in titulo_real.lower() or "espontanea" in titulo_real.lower():
                cenario_label = "Espontânea"
            processar_questao_intencao(db, pesquisa, q, titulo_real, cenario_label, estatisticas)
            estatisticas["questoes_processadas"] += 1

    db.commit()
    return {"status": "ok", "pesquisa_id": pesquisa_id, **estatisticas}


def _humanizar_chave(k: str) -> str:
    """aprovacao_governo_jeronimo_rodrigues → Aprovacao Governo Jeronimo Rodrigues"""
    return " ".join(w.capitalize() for w in k.replace("_", " ").split())


def reextrair_todas(db: Session) -> dict:
    """Re-extrai todas as pesquisas que têm JSON bruto."""
    brutas = db.query(PesquisaDadosBrutos.pesquisa_id).all()
    sumario = {"total": len(brutas), "ok": 0, "skip": 0, "erros": 0,
               "avaliacoes_total": 0, "intencoes_total": 0, "detalhes": []}

    for (pid,) in brutas:
        try:
            r = reextrair_pesquisa(db, pid)
            if r["status"] == "ok":
                sumario["ok"] += 1
                sumario["avaliacoes_total"] += r.get("avaliacoes", 0)
                sumario["intencoes_total"] += r.get("intencoes", 0)
            else:
                sumario["skip"] += 1
            sumario["detalhes"].append(r)
        except Exception as e:
            logger.exception(f"Erro reextraindo {pid}: {e}")
            sumario["erros"] += 1
            sumario["detalhes"].append({"pesquisa_id": pid, "status": "erro", "erro": str(e)[:200]})

    return sumario


def main():
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        s = reextrair_todas(db)
        print(f"Total: {s['total']} | OK: {s['ok']} | Skip: {s['skip']} | Erros: {s['erros']}")
        print(f"Avaliações: {s['avaliacoes_total']} | Intenções: {s['intencoes_total']}")
        for d in s['detalhes']:
            print(f"  {d}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
