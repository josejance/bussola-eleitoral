"""Filtro pré-IA inteligente: identifica conteúdo político relevante.

Estratégia em camadas:
1. Match contra ENTIDADES CADASTRADAS no banco (pessoas, partidos) — alta precisão
2. Fallback: match por palavras-chave políticas genéricas
3. Detecção de estados via gentílicos/capitais

Retorna entidades vinculadas para auto-criação de materia_pessoas e materia_partidos.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

from sqlalchemy.orm import Session

# ===== Palavras-chave genéricas (fallback) =====
PALAVRAS_POLITICAS_GENERICAS = {
    "eleicao", "eleicoes", "candidato", "candidata", "candidatura",
    "governador", "governadora",
    "senador", "senadora",
    "deputado", "deputada",
    "prefeito", "prefeita",
    "presidente", "presidencia",
    "ministro", "ministra", "ministerio",
    "filiacao", "filiou", "desfiliacao",
    "coligacao", "alianca",
    "pesquisa eleitoral", "intencao de voto",
    "stf", "tse", "tcu", "pgr",
    "congresso nacional", "plenario",
    "votacao", "sancionado", "vetado",
    "pec ", "medida provisoria", "projeto de lei",
    "reforma tributaria", "reforma administrativa",
}

# ===== Estados (gentílicos + capitais, sem acentos) =====
ESTADOS_TERMOS = {
    "AC": ["acre", "acreano", "acreana", "rio branco"],
    "AL": ["alagoas", "alagoano", "alagoana", "maceio"],
    "AP": ["amapa", "amapaense", "macapa"],
    "AM": ["amazonas", "amazonense", "manaus"],
    "BA": ["bahia", "baiano", "baiana", "salvador", "soteropolitano"],
    "CE": ["ceara", "cearense", "fortaleza"],
    "DF": ["distrito federal", "brasilia", "brasiliense"],
    "ES": ["espirito santo", "capixaba", "vitoria"],
    "GO": ["goias", "goiano", "goiana", "goiania"],
    "MA": ["maranhao", "maranhense", "sao luis"],
    "MT": ["mato grosso", "mato-grossense", "cuiabano", "cuiaba"],
    "MS": ["mato grosso do sul", "sul-mato-grossense", "campo grande"],
    "MG": ["minas gerais", "mineiro", "mineira", "belo horizonte", "belorizontino"],
    "PA": ["paraense", "paraenses", "belem", "belenense", "do para ", "no para ", "estado do para"],
    "PB": ["paraiba", "paraibano", "joao pessoa", "pessoense"],
    "PR": ["parana", "paranaense", "curitiba", "curitibano"],
    "PE": ["pernambuco", "pernambucano", "recife", "recifense"],
    "PI": ["piaui", "piauiense", "teresina", "teresinense"],
    "RJ": ["rio de janeiro", "carioca", "fluminense"],
    "RN": ["rio grande do norte", "potiguar", "natal", "natalense"],
    "RS": ["rio grande do sul", "gaucho", "gaucha", "porto alegre", "porto-alegrense"],
    "RO": ["rondonia", "rondoniense", "porto velho"],
    "RR": ["roraima", "roraimense", "boa vista"],
    "SC": ["santa catarina", "catarinense", "florianopolis", "florianopolitano"],
    "SP": ["sao paulo", "paulista", "paulistano"],
    "SE": ["sergipe", "sergipano", "aracaju", "aracajuano"],
    "TO": ["tocantins", "tocantinense", "palmas"],
}

ESTADOS_TERMOS_DIACRITICOS = {
    "PA": ["Pará", "PARÁ"],
}


# ===== Helpers =====

def normalize(text: str) -> str:
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    no_acc = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", no_acc.lower()).strip()


def _matches_with_boundary(termo: str, texto: str) -> bool:
    if " " in termo:
        return termo in texto
    return re.search(rf"\b{re.escape(termo)}\b", texto) is not None


def detectar_estados(texto_normalizado: str, texto_original: str = "") -> list[str]:
    detected: set[str] = set()
    if texto_original:
        for uf, termos in ESTADOS_TERMOS_DIACRITICOS.items():
            if any(re.search(rf"\b{re.escape(t)}\b", texto_original) for t in termos):
                detected.add(uf)
    for uf, termos in ESTADOS_TERMOS.items():
        if any(_matches_with_boundary(t, texto_normalizado) for t in termos):
            detected.add(uf)
    return sorted(detected)


# ===== Snapshot de entidades cadastradas =====

@dataclass
class EntidadesCache:
    """Snapshot dos cadastrados para match rápido. TTL via clear()."""
    pessoas: list[dict] = field(default_factory=list)  # {id, nome_full_norm, nome_urna_norm, nome_original}
    partidos: list[dict] = field(default_factory=list)  # {id, sigla_norm, nome_norm}
    pessoas_pre_candidatas_ids: set[str] = field(default_factory=set)  # destaque
    versao: int = 0


_cache = EntidadesCache()


def carregar_entidades(db: Session, force: bool = False) -> EntidadesCache:
    """Carrega/recarrega o snapshot de entidades. Cacheado em memória."""
    global _cache
    if _cache.versao > 0 and not force:
        return _cache

    from app.models import Candidatura, Partido, Pessoa

    pessoas_raw = (
        db.query(Pessoa.id, Pessoa.nome_completo, Pessoa.nome_urna)
        .filter(Pessoa.deleted_at.is_(None))
        .all()
    )
    pessoas = []
    for pid, nome_c, nome_u in pessoas_raw:
        nome_full_norm = normalize(nome_c) if nome_c else ""
        nome_urna_norm = normalize(nome_u) if nome_u else ""
        # Variações: nome completo, sobrenomes únicos significativos
        if nome_full_norm and len(nome_full_norm) >= 5:
            pessoas.append({
                "id": pid,
                "termos": _gerar_variacoes_nome(nome_c or "", nome_u or ""),
                "nome_canonico": nome_c,
            })

    partidos_raw = db.query(Partido.id, Partido.sigla, Partido.nome_completo).filter(Partido.ativo == True).all()  # noqa: E712
    partidos = []
    for pid, sigla, nome in partidos_raw:
        termos = []
        if sigla:
            termos.append(sigla.lower())
        if nome:
            termos.append(normalize(nome))
        if termos:
            partidos.append({"id": pid, "sigla": sigla, "termos": termos})

    # Pessoas que são pré-candidatos (priorizam relevância)
    pre_cand_ids = {
        c[0] for c in db.query(Candidatura.pessoa_id).distinct().all() if c[0]
    }

    _cache = EntidadesCache(
        pessoas=pessoas,
        partidos=partidos,
        pessoas_pre_candidatas_ids=pre_cand_ids,
        versao=_cache.versao + 1,
    )
    return _cache


def _gerar_variacoes_nome(nome_completo: str, nome_urna: str) -> list[str]:
    """Gera termos de match para uma pessoa.

    Para "Jerônimo Rodrigues":
      - "jeronimo rodrigues" (full)
      - "jeronimo" (primeiro nome — só se único o suficiente)
      - "rodrigues" (último nome — só se sobrenome único)
    """
    termos = set()
    nomes_norm = []
    for n in (nome_completo, nome_urna):
        if n:
            nn = normalize(n)
            if nn:
                nomes_norm.append(nn)

    for nn in nomes_norm:
        # Nome completo (mínimo 2 palavras, len ≥ 8)
        if len(nn) >= 8 and " " in nn:
            termos.add(nn)
        # Sobrenome principal (último, se ≥ 6 chars e não comum)
        partes = nn.split()
        if len(partes) >= 2:
            ultimo = partes[-1]
            COMUNS = {"silva", "souza", "santos", "junior", "filho", "neto", "pereira", "oliveira", "lima", "costa", "alves", "ferreira"}
            if len(ultimo) >= 6 and ultimo not in COMUNS:
                # Sobrenome só conta se aparecer junto com o primeiro nome
                # Para evitar confusão, exigimos a sequência completa
                pass  # decide-se ignorar sobrenome isolado para evitar falsos positivos

    return sorted(termos)


def invalidar_cache_entidades():
    """Chama isso quando pessoas/partidos mudam."""
    global _cache
    _cache = EntidadesCache()


# ===== Filtro principal =====

@dataclass
class ResultadoFiltro:
    aproveitada: bool
    motivo_descarte: str | None = None
    estados_detectados: list[str] = field(default_factory=list)
    score_relevancia: int = 0
    pessoas_mencionadas_ids: list[str] = field(default_factory=list)
    partidos_mencionados_ids: list[str] = field(default_factory=list)
    matched_genericos: int = 0
    matched_entidades: int = 0


def filtrar_materia(
    titulo: str,
    snippet: str,
    db: Session | None = None,
    fonte_eh_estadual: bool = False,
) -> ResultadoFiltro:
    """Filtra matéria com base em entidades cadastradas + palavras-chave.

    Estratégia:
    - Match em pessoa cadastrada → +relevância forte (peso 5)
    - Match em partido cadastrado → +relevância média (peso 2)
    - Match em palavra-chave genérica → +relevância fraca (peso 1)

    Aproveitada se:
    - Pelo menos 1 match em entidade cadastrada, OU
    - Pelo menos 2 matches em palavras genéricas (precisa de contexto reforçado)
    - Fontes estaduais têm threshold mais baixo (1 match genérico OK)
    """
    texto_original = f"{titulo} {snippet}"
    texto = normalize(texto_original)

    if not texto.strip():
        return ResultadoFiltro(aproveitada=False, motivo_descarte="texto vazio")

    pessoas_match: list[str] = []
    partidos_match: list[str] = []
    matched_genericos = 0

    # 1) Match em entidades cadastradas (se db disponível)
    if db is not None:
        ents = carregar_entidades(db)

        for p in ents.pessoas:
            for termo in p["termos"]:
                if _matches_with_boundary(termo, texto):
                    pessoas_match.append(p["id"])
                    break  # pessoa achada, próxima

        for partido in ents.partidos:
            for termo in partido["termos"]:
                # sigla pequena (ex: PT, PL) usa boundary; nome completo pode usar substring
                if len(termo) <= 5:
                    # Match estrito em maiúsculas no texto original (PT vs petista vs petista)
                    if re.search(rf"\b{re.escape(termo.upper())}\b", texto_original):
                        partidos_match.append(partido["id"])
                        break
                else:
                    if _matches_with_boundary(termo, texto):
                        partidos_match.append(partido["id"])
                        break

    # 2) Match em palavras-chave genéricas
    for kw in PALAVRAS_POLITICAS_GENERICAS:
        if kw in texto:
            matched_genericos += 1
            if matched_genericos >= 5:
                break  # já o suficiente

    # 3) Detecta estados
    estados = detectar_estados(texto, texto_original)

    # 4) Decide aproveitamento
    matched_entidades = len(pessoas_match) + len(partidos_match)

    if matched_entidades >= 1:
        # Pessoa ou partido cadastrado → aproveita
        aproveitada = True
        motivo = None
    elif fonte_eh_estadual and matched_genericos >= 1:
        # Fonte estadual com 1 menção política genérica → aproveita (contexto local)
        aproveitada = True
        motivo = None
    elif matched_genericos >= 2:
        # 2+ palavras políticas → contexto reforçado
        aproveitada = True
        motivo = None
    else:
        aproveitada = False
        motivo = "sem entidades cadastradas nem contexto politico suficiente"

    # 5) Score de relevância
    if matched_entidades >= 3 or len(pessoas_match) >= 2:
        score = 5
    elif matched_entidades >= 2:
        score = 4
    elif matched_entidades >= 1:
        score = 3
    elif matched_genericos >= 3:
        score = 2
    else:
        score = 1

    return ResultadoFiltro(
        aproveitada=aproveitada,
        motivo_descarte=motivo,
        estados_detectados=estados,
        score_relevancia=score,
        pessoas_mencionadas_ids=list(set(pessoas_match)),
        partidos_mencionados_ids=list(set(partidos_match)),
        matched_genericos=matched_genericos,
        matched_entidades=matched_entidades,
    )


# ===== API legacy (compat com código existente) =====

def filtro_rapido(titulo: str, snippet: str) -> dict:
    """Wrapper sem db — usa apenas keywords genéricas. Mantido para compat."""
    res = filtrar_materia(titulo, snippet, db=None)
    return {
        "aproveitada": res.aproveitada,
        "motivo_descarte": res.motivo_descarte,
        "estados_detectados": res.estados_detectados,
        "score_relevancia": res.score_relevancia,
    }


def is_politico(texto_normalizado: str) -> bool:
    """Mantido para compat."""
    return any(p in texto_normalizado for p in PALAVRAS_POLITICAS_GENERICAS)
