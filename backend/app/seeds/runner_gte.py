"""Runner do seed GTE 2026: aplica os dados qualitativos ao banco.

Idempotente: pode ser executado múltiplas vezes. Pessoas são identificadas
por (nome_completo, partido, estado) — match aproximado para evitar duplicatas
entre chapas (ex: Renan Filho aparece como candidato e seu pai Renan Calheiros).
"""
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Candidatura,
    Eleicao,
    Estado,
    FiliacaoPartidaria,
    InstitutoPesquisa,
    IntencaoVoto,
    Partido,
    Pesquisa,
    Pessoa,
    StatusPTEstado,
    VotacaoPartidoEstado,
)
from app.seeds.gte_2026 import (
    BANCADAS,
    CANDIDATURAS,
    PESQUISAS,
    STATUS_DETALHES,
)


def _get_partido_map(db: Session) -> dict[str, str]:
    return {p.sigla: p.id for p in db.query(Partido).all()}


def _get_estado_map(db: Session) -> dict[str, str]:
    return {e.sigla: e.id for e in db.query(Estado).all()}


def _get_eleicao(db: Session, ano: int, turno: int = 1) -> Eleicao | None:
    return (
        db.query(Eleicao)
        .filter(Eleicao.ano == ano, Eleicao.turno == turno)
        .first()
    )


def aplicar_status_detalhes(db: Session, estados_map: dict[str, str]) -> int:
    """Atualiza cenario_*_detalhe e observacao_geral em status_pt_estado."""
    n = 0
    for uf, dados in STATUS_DETALHES.items():
        eid = estados_map.get(uf)
        if not eid:
            continue
        s = db.query(StatusPTEstado).filter(StatusPTEstado.estado_id == eid).first()
        if not s:
            s = StatusPTEstado(estado_id=eid)
            db.add(s)
        for k, v in dados.items():
            setattr(s, k, v)
        n += 1
    db.commit()
    return n


def _ensure_pessoa(
    db: Session,
    nome_completo: str,
    nome_urna: str,
    partido_id: str,
    estado_id: str,
) -> Pessoa:
    """Localiza ou cria pessoa. Match por nome_completo + estado_natal_id (heurística)."""
    p = (
        db.query(Pessoa)
        .filter(
            Pessoa.nome_completo == nome_completo,
            Pessoa.deleted_at.is_(None),
        )
        .first()
    )
    if p:
        return p
    p = Pessoa(
        nome_completo=nome_completo,
        nome_urna=nome_urna,
        estado_natal_id=estado_id,
    )
    db.add(p)
    db.flush()
    # Filiação atual
    db.add(
        FiliacaoPartidaria(
            pessoa_id=p.id,
            partido_id=partido_id,
            inicio=date(2024, 1, 1),  # default
        )
    )
    return p


def aplicar_candidaturas(
    db: Session,
    estados_map: dict[str, str],
    partidos_map: dict[str, str],
) -> int:
    """Cria pessoas + candidaturas pré-2026."""
    eleicao = _get_eleicao(db, 2026, turno=1)
    if not eleicao:
        raise RuntimeError("Eleição 2026/1 não encontrada — rode primeiro o seed principal")

    n = 0
    for uf, nome_completo, nome_urna, sigla, cargo, eh_titular, observacao in CANDIDATURAS:
        eid = estados_map.get(uf)
        pid = partidos_map.get(sigla)
        if not eid:
            print(f"  [skip] estado {uf} não encontrado")
            continue
        if not pid:
            print(f"  [skip] partido {sigla} não encontrado para {nome_completo}")
            continue

        pessoa = _ensure_pessoa(db, nome_completo, nome_urna, pid, eid)

        # Verifica se candidatura já existe
        existing = (
            db.query(Candidatura)
            .filter(
                Candidatura.eleicao_id == eleicao.id,
                Candidatura.pessoa_id == pessoa.id,
                Candidatura.cargo == cargo,
                Candidatura.estado_id == eid,
            )
            .first()
        )
        if existing:
            existing.partido_id = pid
            existing.observacao = observacao or None
            existing.eh_titular = eh_titular
            existing.status_registro = "pre_candidatura"
            continue

        db.add(
            Candidatura(
                eleicao_id=eleicao.id,
                pessoa_id=pessoa.id,
                cargo=cargo,
                partido_id=pid,
                estado_id=eid,
                status_registro="pre_candidatura",
                eh_titular=eh_titular,
                observacao=observacao or None,
            )
        )
        n += 1

    db.commit()
    return n


def aplicar_bancadas(
    db: Session,
    estados_map: dict[str, str],
    partidos_map: dict[str, str],
) -> int:
    """Popula votacao_partido_estado para PT 2018+2022, federal+estadual."""
    pt_id = partidos_map.get("PT")
    if not pt_id:
        raise RuntimeError("Partido PT não encontrado")

    eleicoes = {
        2018: _get_eleicao(db, 2018, turno=1),
        2022: _get_eleicao(db, 2022, turno=1),
    }
    if not all(eleicoes.values()):
        raise RuntimeError("Eleição 2018 ou 2022 não encontrada")

    n = 0
    for uf, anos in BANCADAS.items():
        eid = estados_map.get(uf)
        if not eid:
            continue
        for ano, cargos in anos.items():
            eleicao = eleicoes[ano]
            for cargo_key, (cadeiras, votos, pct) in cargos.items():
                cargo = "deputado_federal" if cargo_key == "federal" else "deputado_estadual"
                existing = (
                    db.query(VotacaoPartidoEstado)
                    .filter(
                        VotacaoPartidoEstado.eleicao_id == eleicao.id,
                        VotacaoPartidoEstado.partido_id == pt_id,
                        VotacaoPartidoEstado.estado_id == eid,
                        VotacaoPartidoEstado.cargo == cargo,
                    )
                    .first()
                )
                if existing:
                    existing.votos_totais = votos
                    existing.percentual_total = pct
                    existing.bancada_eleita = cadeiras
                    continue
                db.add(
                    VotacaoPartidoEstado(
                        eleicao_id=eleicao.id,
                        partido_id=pt_id,
                        estado_id=eid,
                        cargo=cargo,
                        votos_totais=votos,
                        percentual_total=pct,
                        bancada_eleita=cadeiras,
                    )
                )
                n += 1
    db.commit()
    return n


def aplicar_pesquisas(
    db: Session,
    estados_map: dict[str, str],
    partidos_map: dict[str, str],
) -> int:
    """Insere pesquisas Real Time Big Data e suas intenções de voto."""
    eleicao = _get_eleicao(db, 2026, turno=1)
    if not eleicao:
        return 0

    n = 0
    for ps in PESQUISAS:
        eid = estados_map.get(ps["uf"])
        if not eid:
            continue

        # Busca/cria instituto
        instituto = (
            db.query(InstitutoPesquisa)
            .filter(InstitutoPesquisa.nome == ps["instituto_nome"])
            .first()
        )
        if not instituto:
            instituto = InstitutoPesquisa(nome=ps["instituto_nome"], confiabilidade_score=4)
            db.add(instituto)
            db.flush()

        # Verifica se pesquisa já existe (por instituto + estado + data fim)
        existing = (
            db.query(Pesquisa)
            .filter(
                Pesquisa.instituto_id == instituto.id,
                Pesquisa.estado_id == eid,
                Pesquisa.data_fim_campo == ps["data_fim_campo"],
            )
            .first()
        )
        if existing:
            continue  # idempotência

        pesquisa = Pesquisa(
            instituto_id=instituto.id,
            eleicao_id=eleicao.id,
            estado_id=eid,
            data_inicio_campo=ps["data_inicio_campo"],
            data_fim_campo=ps["data_fim_campo"],
            data_divulgacao=ps["data_divulgacao"],
            amostra=ps["amostra"],
            margem_erro=ps["margem_erro"],
            nivel_confianca=95.0,
            metodologia=ps["metodologia"],
            contratante=ps["contratante"],
            tipo_cenario=ps["tipo_cenario"],
            turno_referencia=ps["turno_referencia"],
            origem_dado="insercao_manual",
            status_revisao="aprovada",
            observacao="Importada do documento GTE 17/04/2026",
        )
        db.add(pesquisa)
        db.flush()
        n += 1

        # Intenções de voto
        for cenario in ps["cenarios"]:
            for posicao, (nome, sigla, pct) in enumerate(cenario["candidatos"], start=1):
                partido_id = partidos_map.get(sigla)
                # Tenta achar pessoa existente
                pessoa = (
                    db.query(Pessoa)
                    .filter(Pessoa.nome_completo == nome)
                    .first()
                )
                db.add(
                    IntencaoVoto(
                        pesquisa_id=pesquisa.id,
                        pessoa_id=pessoa.id if pessoa else None,
                        partido_referencia_id=partido_id,
                        nome_referencia=nome,
                        percentual=pct,
                        posicao_no_cenario=posicao,
                    )
                )

    db.commit()
    return n


def run_all():
    db = SessionLocal()
    try:
        estados_map = _get_estado_map(db)
        partidos_map = _get_partido_map(db)

        print("[gte] Aplicando detalhes de status por estado...")
        n_status = aplicar_status_detalhes(db, estados_map)
        print(f"  - {n_status} estados atualizados")

        print("[gte] Criando pessoas e candidaturas pre-2026...")
        n_cand = aplicar_candidaturas(db, estados_map, partidos_map)
        print(f"  - {n_cand} candidaturas novas (existentes foram atualizadas)")

        print("[gte] Populando bancadas historicas (PT 2018 + 2022)...")
        n_banc = aplicar_bancadas(db, estados_map, partidos_map)
        print(f"  - {n_banc} entradas bancada novas")

        print("[gte] Importando pesquisas Real Time Big Data...")
        n_pesq = aplicar_pesquisas(db, estados_map, partidos_map)
        print(f"  - {n_pesq} pesquisas novas")

        print("[gte] Concluido.")
    finally:
        db.close()


if __name__ == "__main__":
    run_all()
