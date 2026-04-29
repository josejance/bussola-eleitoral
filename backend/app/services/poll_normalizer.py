"""Normalização robusta de campos heterogêneos em JSONs de pesquisa.

Lida com variações encontradas nos JSONs Quaest:
- Root: {pesquisa: {...}} OU {...} direto
- local: "Bahia" / "BAHIA" / "SÃO PAULO" / "Brasil" / ausente
- registro_eleitoral: dict {numero, data} | string "BR-XXXXX/2026" | string com texto adicional | vazio
- amostra: int | string "1.200 entrevistas" | dict {total_entrevistas} | bug 2 (era 2000)
- instituicoes: dict | string única "Quaest/Genial" | lista
- data_coleta: dict {inicio, fim} | string "9 a 13/ABRIL" | string "Janeiro 2026"
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

# ===== Mapeamento de nomes de estados =====

ESTADO_NOMES = {
    # Variações comuns → sigla canonica
    "acre": "AC", "ac": "AC",
    "alagoas": "AL", "al": "AL",
    "amapa": "AP", "amapá": "AP", "ap": "AP",
    "amazonas": "AM", "am": "AM",
    "bahia": "BA", "ba": "BA",
    "ceara": "CE", "ceará": "CE", "ce": "CE",
    "distrito federal": "DF", "df": "DF", "brasilia": "DF", "brasília": "DF",
    "espirito santo": "ES", "espírito santo": "ES", "es": "ES",
    "goias": "GO", "goiás": "GO", "go": "GO",
    "maranhao": "MA", "maranhão": "MA", "ma": "MA",
    "mato grosso": "MT", "mt": "MT",
    "mato grosso do sul": "MS", "ms": "MS",
    "minas gerais": "MG", "minas": "MG", "mg": "MG",
    "para": "PA", "pará": "PA", "pa": "PA",
    "paraiba": "PB", "paraíba": "PB", "pb": "PB",
    "parana": "PR", "paraná": "PR", "pr": "PR",
    "pernambuco": "PE", "pe": "PE",
    "piaui": "PI", "piauí": "PI", "pi": "PI",
    "rio de janeiro": "RJ", "rio": "RJ", "rj": "RJ",
    "rio grande do norte": "RN", "rn": "RN",
    "rio grande do sul": "RS", "rs": "RS",
    "rondonia": "RO", "rondônia": "RO", "ro": "RO",
    "roraima": "RR", "rr": "RR",
    "santa catarina": "SC", "sc": "SC",
    "sao paulo": "SP", "são paulo": "SP", "sp": "SP",
    "sergipe": "SE", "se": "SE",
    "tocantins": "TO", "to": "TO",
}

NACIONAL_TERMOS = {"brasil", "br", "nacional", "presidente"}

MESES_PT = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}


# ===== Funções de normalização =====

def get_root(data: dict) -> dict:
    """Aceita {pesquisa: {...}} ou {...} direto."""
    return data.get("pesquisa", data) if isinstance(data, dict) else {}


def normalizar_local(local_str: Any) -> tuple[str, str | None]:
    """Retorna (abrangencia, sigla_uf|None).
    abrangencia: 'nacional' | 'estadual' | 'desconhecido'
    """
    if not local_str:
        return ("desconhecido", None)
    s = str(local_str).strip().lower()
    s = re.sub(r"\s+", " ", s)

    if s in NACIONAL_TERMOS:
        return ("nacional", None)
    if s in ESTADO_NOMES:
        return ("estadual", ESTADO_NOMES[s])
    # Tenta substring partial
    for nome, sigla in ESTADO_NOMES.items():
        if len(nome) > 3 and nome in s:
            return ("estadual", sigla)
    return ("desconhecido", None)


def detectar_nacional_por_titulo(titulo: str) -> bool:
    """True se título indica pesquisa presidencial nacional."""
    if not titulo:
        return False
    t = titulo.lower()
    return any(kw in t for kw in ["presidente", "presidencial", "nacional", "brasil"])


def extrair_registro_tse(reg: Any) -> str | None:
    """Extrai número de registro TSE de várias formas:
    - {numero: 'BR-XXX/AAAA', data_registro: ...} → 'BR-XXX/AAAA'
    - 'BR-XXX/AAAA' → 'BR-XXX/AAAA'
    - 'BR-XXX/AAAA, em 21/04/2026' → 'BR-XXX/AAAA'
    - texto longo com regex match → primeiro match
    """
    if not reg:
        return None
    if isinstance(reg, dict):
        return reg.get("numero") or None
    if not isinstance(reg, str):
        return None
    s = reg.strip()
    if not s or s.lower() in {"não aplicável", "nao aplicavel", "não informado"}:
        return None
    # Procura padrão XX-NNNNN/AAAA
    m = re.search(r"\b([A-Z]{2}-\d{4,6}/\d{4})\b", s)
    if m:
        return m.group(1)
    # Padrão BR-NNNNN/AAAA
    m = re.search(r"\b(BR-\d{4,6}/\d{4})\b", s)
    if m:
        return m.group(1)
    return None


def extrair_amostra(amostra: Any) -> int | None:
    """Extrai número inteiro de variações:
    - 1200 → 1200
    - '1.200 entrevistas' → 1200
    - {total_entrevistas: 1200} → 1200
    - 2 (bug — era 2000) → 2 (não corrige automaticamente)
    """
    if amostra is None:
        return None
    if isinstance(amostra, dict):
        return extrair_amostra(amostra.get("total_entrevistas") or amostra.get("entrevistas"))
    if isinstance(amostra, (int, float)):
        n = int(amostra)
        # Detecta bug "2" que provavelmente é 2000
        if n < 100:
            return n * 1000  # heurística arriscada mas comum
        return n
    if isinstance(amostra, str):
        # Extrai primeiro número (suporta "1.200" como 1200, "2,004" como 2004)
        s = amostra.replace(".", "").replace(",", "")
        m = re.search(r"\b(\d{2,6})\b", s)
        if m:
            n = int(m.group(1))
            if n < 100:
                return n * 1000
            return n
    return None


def extrair_margem(margem: Any) -> float | None:
    if margem is None:
        return None
    if isinstance(margem, (int, float)):
        return float(margem)
    if isinstance(margem, str):
        s = margem.replace(",", ".").strip()
        m = re.search(r"(\d+(?:\.\d+)?)", s)
        if m:
            return float(m.group(1))
    return None


def extrair_nivel_confianca(nc: Any) -> float | None:
    if nc is None:
        return None
    if isinstance(nc, (int, float)):
        v = float(nc)
        return v if v <= 100 else v / 100
    if isinstance(nc, str):
        m = re.search(r"(\d+(?:[\.,]\d+)?)", nc)
        if m:
            v = float(m.group(1).replace(",", "."))
            return v if v <= 100 else v / 100
    return None


def extrair_metodologia(metodo: Any) -> str:
    """Normaliza para um dos enums: presencial/telefonica/online/mista/painel"""
    if not metodo:
        return "presencial"
    m = str(metodo).lower()
    if "presenc" in m or "domicil" in m or "face" in m:
        return "presencial"
    if "telef" in m:
        return "telefonica"
    if "online" in m or "internet" in m or "web" in m:
        return "online"
    if "painel" in m:
        return "painel"
    if "mista" in m or "híbrid" in m or "hibrid" in m:
        return "mista"
    return "presencial"


def extrair_contratante(instituicoes: Any) -> tuple[str | None, str | None]:
    """Retorna (contratante, executora) de variações:
    - {contratante: 'X', executora: 'Y'}
    - 'Quaest/Genial Investimentos' → executora=Quaest, contratante=Genial
    - ['Genial Investimentos', 'Quaest'] → contratante=Genial, executora=Quaest
    - 'Genial Investimentos, Quaest Pesquisa e Consultoria'
    """
    if not instituicoes:
        return (None, None)
    if isinstance(instituicoes, dict):
        return (instituicoes.get("contratante"), instituicoes.get("executora"))
    if isinstance(instituicoes, list):
        if len(instituicoes) >= 2:
            return (str(instituicoes[0]), str(instituicoes[1]))
        if instituicoes:
            return (None, str(instituicoes[0]))
    if isinstance(instituicoes, str):
        # Tenta separar por '/' ou ','
        partes = re.split(r"[/,]", instituicoes)
        partes = [p.strip() for p in partes if p.strip()]
        if len(partes) >= 2:
            # heurística: Quaest sempre é executora
            quaest_idx = next((i for i, p in enumerate(partes) if "quaest" in p.lower()), None)
            if quaest_idx is not None:
                executora = partes[quaest_idx]
                contratante = next((p for i, p in enumerate(partes) if i != quaest_idx), None)
                return (contratante, executora)
            return (partes[0], partes[1])
        return (None, partes[0] if partes else None)
    return (None, None)


def extrair_periodo(periodo: Any, spec: dict | None = None) -> tuple[date | None, date | None]:
    """Extrai (data_inicio, data_fim) de:
    - {data_coleta_inicio: '2026-04-23', data_coleta_fim: '2026-04-27'}
    - '20 a 23 de abril de 2026'
    - '9 a 13/ABRIL'
    - '08 a 11/JANEIRO' (precisa do ano em outro lugar)
    - 'Abril de 2026' → fim = último dia de abril
    """
    spec = spec or {}
    inicio = fim = None

    # 1) Formato dict explícito
    if isinstance(periodo, dict):
        inicio = _parse_date_iso(periodo.get("data_coleta_inicio") or periodo.get("inicio"))
        fim = _parse_date_iso(periodo.get("data_coleta_fim") or periodo.get("fim"))
        if inicio or fim:
            return (inicio, fim)

    # 2) Tenta usar data_coleta da spec
    data_coleta = spec.get("data_coleta") or (periodo if isinstance(periodo, str) else "")

    if isinstance(data_coleta, str):
        return _parse_periodo_string(data_coleta)

    return (None, None)


def _parse_date_iso(s: Any) -> date | None:
    if not s or not isinstance(s, str):
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _parse_periodo_string(s: str) -> tuple[date | None, date | None]:
    """Parsing flexível de strings tipo '9 a 13/ABRIL', '20 a 23 de abril de 2026'."""
    s_lower = s.lower().strip()

    # Caso 1: 'NN a NN/MES' (ano não explícito → assume ano corrente: 2026)
    m = re.search(r"(\d{1,2})\s+a\s+(\d{1,2})\s*[/de\s]+([a-zãç]+)(?:\s+de\s+(\d{4}))?", s_lower)
    if m:
        d1, d2, mes_str, ano_str = m.groups()
        ano = int(ano_str) if ano_str else 2026
        mes = MESES_PT.get(mes_str.strip()[:3], None) or MESES_PT.get(mes_str.strip(), None)
        if mes:
            try:
                return (date(ano, mes, int(d1)), date(ano, mes, int(d2)))
            except ValueError:
                pass

    # Caso 2: 'MES de AAAA' → fim = último dia do mês
    m = re.search(r"^([a-zãç]+)\s+de\s+(\d{4})$", s_lower)
    if m:
        mes_str, ano_str = m.groups()
        ano = int(ano_str)
        mes = MESES_PT.get(mes_str.strip(), None)
        if mes:
            import calendar
            ultimo_dia = calendar.monthrange(ano, mes)[1]
            return (date(ano, mes, 1), date(ano, mes, ultimo_dia))

    # Caso 3: 'MES AAAA' (sem 'de')
    m = re.search(r"^([a-zãç]+)\s+(\d{4})$", s_lower)
    if m:
        mes_str, ano_str = m.groups()
        ano = int(ano_str)
        mes = MESES_PT.get(mes_str.strip(), None)
        if mes:
            import calendar
            ultimo_dia = calendar.monthrange(ano, mes)[1]
            return (date(ano, mes, 1), date(ano, mes, ultimo_dia))

    # Caso 4: data ISO direto
    iso = _parse_date_iso(s)
    if iso:
        return (iso, iso)

    return (None, None)


# ===== Detector de tipo da pesquisa =====

def detectar_tipo_pesquisa(root: dict) -> str:
    """Retorna 'eleitoral_estadual' | 'eleitoral_nacional' | 'tematica'."""
    ident = root.get("identificacao", {})
    spec = root.get("especificacoes_tecnicas", {})
    resultados = root.get("resultados", {})

    # Tipo declarado como "Opinião" → temática
    tipo_str = (spec.get("tipo") or ident.get("tipo") or "").lower()
    if "opini" in tipo_str:
        return "tematica"

    titulo = (ident.get("titulo") or "").upper()
    subtitulo = (ident.get("subtitulo") or "").upper()
    titulo_full = titulo + " " + subtitulo

    # Sinal forte de eleitoral pelo título
    titulo_eleitoral = any(
        kw in titulo_full
        for kw in ["ELEITORAL", "PRESIDENT", "GOVERNADOR", "INTENÇÃO DE VOTO", "INTENCAO DE VOTO"]
    )

    # Tem registro TSE?
    reg = extrair_registro_tse(ident.get("registro_eleitoral"))

    # Chaves diretas de eleitoral em resultados
    eleitoral_keys_diretas = False
    questoes_eleitorais = 0
    questoes_total = 0
    if isinstance(resultados, dict):
        for k, v in resultados.items():
            k_lower = str(k).lower()
            # Snake_case
            if k_lower.startswith(("aprovacao_governo", "avaliacao_governo", "intencao_voto")):
                eleitoral_keys_diretas = True
            # Texto livre (formato MINAS): "Aprovação do governo Romeu Zema. Pergunta"
            elif any(
                kw in k_lower
                for kw in [
                    "aprovação do governo", "aprovacao do governo",
                    "avaliação do governo", "avaliacao do governo",
                    "intenção de voto", "intencao de voto",
                    "intenção do voto", "intencao do voto",
                    "voto para presidente", "voto para governador", "voto para senador",
                    "próximo governador", "proximo governador",
                ]
            ):
                eleitoral_keys_diretas = True

            if k_lower.startswith("questao_"):
                questoes_total += 1
                if isinstance(v, dict):
                    titulo_q = (v.get("titulo") or v.get("enunciado") or "").lower()
                    if any(
                        kw in titulo_q
                        for kw in [
                            "intenç", "aprovação do governo", "aprovacao do governo",
                            "avaliação do governo", "avaliacao do governo",
                            "voto para presidente", "voto para governador",
                            "voto para senador", "rejeição",
                        ]
                    ):
                        questoes_eleitorais += 1

    # Decisão final
    eh_eleitoral = (
        bool(reg)
        or eleitoral_keys_diretas
        or titulo_eleitoral
        or (questoes_total > 0 and questoes_eleitorais >= 2)  # 2+ questões eleitorais → eleitoral
    )

    if not eh_eleitoral:
        return "tematica"

    # Eleitoral — decide nacional vs estadual
    abrang, _ = normalizar_local(ident.get("local"))
    titulo_indica_nacional = (
        "PRESIDENT" in titulo_full
        or "NACIONAL" in titulo_full
        or "BRASIL" in titulo_full
    )
    titulo_indica_estadual = (
        "GOVERNADOR" in titulo_full
        or any(uf in titulo_full for uf in ["BAHIA", "MINAS", "PARANÁ", "PARANA", "PERNAMBUCO", "RIO DE JANEIRO", "SÃO PAULO", "SAO PAULO"])
    )

    if abrang == "nacional" or (titulo_indica_nacional and not titulo_indica_estadual):
        return "eleitoral_nacional"
    if abrang == "estadual" or titulo_indica_estadual:
        return "eleitoral_estadual"
    if reg and reg.startswith("BR-"):
        return "eleitoral_nacional"
    if reg and re.match(r"^[A-Z]{2}-", reg) and not reg.startswith("BR-"):
        return "eleitoral_estadual"
    return "eleitoral_nacional"


def detectar_tema(root: dict, fname: str = "") -> str:
    """Detecta tema da pesquisa temática a partir de título/subtítulo/arquivo."""
    ident = root.get("identificacao", {})
    titulo = (ident.get("titulo") or "") + " " + (ident.get("subtitulo") or "")
    texto = (titulo + " " + fname).lower()

    if "aposta" in texto:
        return "apostas_esportivas"
    if "copa" in texto or "mundial" in texto:
        return "copa_mundo"
    if "stf" in texto and "etic" in texto:
        return "etica_stf"
    if "stf" in texto:
        return "stf"
    if "imposto" in texto or "renda" in texto or "ir " in texto:
        return "imposto_renda"
    if "venezuela" in texto:
        return "venezuela"
    if "urna" in texto:
        return "urnas_eletronicas"
    if "imagem" in texto and "lider" in texto:
        return "imagem_lideres"
    if "brasil" in texto and not "presidencial" in texto:
        return "brasil_geral"
    return "outros"
