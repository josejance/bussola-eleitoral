"""Executa seeds idempotentes — pode ser rodado várias vezes."""
import json
from datetime import date

from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models import (
    Eleicao,
    Estado,
    FederacaoPartidaria,
    InstitutoPesquisa,
    FonteRSS,
    Partido,
    PerfilUsuario,
    StatusPTEstado,
)
from app.models.base import Base
from app.seeds.data import (
    ELEICOES,
    ESTADOS,
    FEDERACOES,
    FONTES_ESTADUAIS,
    FONTES_NACIONAIS,
    INSTITUTOS,
    PARTIDOS,
)
from app.services.security import hash_password


def seed_estados(db: Session) -> dict[str, str]:
    """Retorna mapa sigla -> id"""
    mapa = {}
    for sigla, nome, regiao, pop, eleitorado, capital, codigo in ESTADOS:
        e = db.query(Estado).filter(Estado.sigla == sigla).first()
        if not e:
            e = Estado(
                sigla=sigla,
                nome=nome,
                regiao=regiao,
                populacao=pop,
                eleitorado_atual=eleitorado,
                capital=capital,
                codigo_ibge=codigo,
            )
            db.add(e)
            db.flush()
        mapa[sigla] = e.id
    db.commit()
    return mapa


def seed_partidos(db: Session) -> dict[str, str]:
    mapa = {}
    for sigla, nome, numero, espectro, esp_econ, esp_social, cor in PARTIDOS:
        p = db.query(Partido).filter(Partido.sigla == sigla).first()
        if not p:
            p = Partido(
                sigla=sigla,
                nome_completo=nome,
                numero_legenda=numero,
                espectro=espectro,
                espectro_economico=esp_econ,
                espectro_social=esp_social,
                ativo=True,
                cor_hex=cor,
            )
            db.add(p)
            db.flush()
        mapa[sigla] = p.id
    db.commit()
    return mapa


def seed_federacoes(db: Session, partidos: dict[str, str]):
    for fed in FEDERACOES:
        existing = db.query(FederacaoPartidaria).filter(FederacaoPartidaria.nome == fed["nome"]).first()
        if not existing:
            ids = [partidos[s] for s in fed["partidos_siglas"] if s in partidos]
            f = FederacaoPartidaria(
                nome=fed["nome"],
                sigla=fed["sigla"],
                partidos_ids_json=json.dumps(ids),
                inicio_vigencia=fed["inicio_vigencia"],
                numero_legenda=fed.get("numero_legenda"),
            )
            db.add(f)
    db.commit()


def seed_eleicoes(db: Session) -> dict[str, str]:
    """Mapa 'AAAA-T' -> id"""
    mapa = {}
    for el in ELEICOES:
        key = f"{el['ano']}-{el['turno']}"
        e = (
            db.query(Eleicao)
            .filter(Eleicao.ano == el["ano"], Eleicao.turno == el["turno"], Eleicao.tipo == el["tipo"])
            .first()
        )
        if not e:
            e = Eleicao(
                ano=el["ano"],
                turno=el["turno"],
                tipo=el["tipo"],
                data=el["data"],
                descricao=f"Eleição {el['tipo']} {el['ano']} - {el['turno']}º turno",
            )
            db.add(e)
            db.flush()
        mapa[key] = e.id
    db.commit()
    return mapa


def seed_institutos(db: Session):
    for nome, sigla, site, score in INSTITUTOS:
        existing = db.query(InstitutoPesquisa).filter(InstitutoPesquisa.nome == nome).first()
        if not existing:
            db.add(
                InstitutoPesquisa(
                    nome=nome,
                    sigla=sigla,
                    site=site or None,
                    confiabilidade_score=score,
                    ativo=True,
                )
            )
    db.commit()


def seed_fontes_rss(db: Session, estados_map: dict[str, str]):
    """Popula fontes nacionais + 81 estaduais. Idempotente; atualiza url_feed se mudou."""
    # Nacionais
    for nome, feed, site, tipo, abrang, espectro, conf, peso, freq in FONTES_NACIONAIS:
        existing = db.query(FonteRSS).filter(FonteRSS.nome == nome).first()
        if existing:
            existing.url_feed = feed
            existing.url_site = site
            continue
        db.add(
            FonteRSS(
                nome=nome,
                url_feed=feed,
                url_site=site,
                tipo=tipo,
                abrangencia=abrang,
                espectro_editorial=espectro,
                confiabilidade=conf,
                peso_editorial=peso,
                frequencia_polling_minutos=freq,
                ativo=True,
            )
        )
    db.commit()

    # Estaduais (3 por estado, 81 total)
    for uf, nome, feed, site in FONTES_ESTADUAIS:
        existing = db.query(FonteRSS).filter(FonteRSS.nome == nome).first()
        estado_id = estados_map.get(uf)
        estados_cobertos = json.dumps([estado_id]) if estado_id else None
        if existing:
            existing.url_feed = feed
            existing.url_site = site
            existing.estados_cobertos_json = estados_cobertos
            continue
        db.add(
            FonteRSS(
                nome=nome,
                url_feed=feed,
                url_site=site,
                tipo="jornal_estadual",
                abrangencia="estadual",
                estados_cobertos_json=estados_cobertos,
                espectro_editorial="centro",  # default; ajustável manualmente
                confiabilidade=3,
                peso_editorial=3,
                frequencia_polling_minutos=30,
                ativo=True,
            )
        )
    db.commit()


def seed_status_pt_inicial(db: Session, estados_map: dict[str, str], eleicoes_map: dict[str, str]):
    """Cria status_pt_estado padrão para 2026 em cada estado, com mock para demonstração."""
    eleicao_id = eleicoes_map.get("2026-1")

    # Heurística inicial — todos começam como "indefinido / em_construcao"
    # Marcamos alguns estados conhecidamente PT como exemplo
    presets = {
        "BA": ("candidatura_propria", "candidatura_propria", "consolidado", 5),
        "CE": ("candidatura_propria", "vice_aliado", "em_construcao", 5),
        "PE": ("vice_aliado", "candidatura_propria", "em_construcao", 5),
        "PI": ("candidatura_propria", "candidatura_propria", "consolidado", 4),
        "MA": ("vice_aliado", "candidatura_propria", "consolidado", 4),
        "RN": ("candidatura_propria", "vice_aliado", "em_construcao", 4),
        "PB": ("vice_aliado", "candidatura_propria", "em_construcao", 3),
        "SE": ("apoio_sem_cargo", "vice_aliado", "em_construcao", 3),
        "AL": ("apoio_sem_cargo", "indefinido", "disputado", 3),
        "MG": ("candidatura_propria", "vice_aliado", "disputado", 5),
        "SP": ("candidatura_propria", "vice_aliado", "disputado", 5),
        "RJ": ("apoio_sem_cargo", "indefinido", "disputado", 4),
        "RS": ("vice_aliado", "candidatura_propria", "em_construcao", 4),
        "PR": ("apoio_sem_cargo", "indefinido", "adverso", 3),
        "SC": ("oposicao", "oposicao", "adverso", 2),
        "GO": ("apoio_sem_cargo", "indefinido", "adverso", 3),
        "MT": ("oposicao", "oposicao", "adverso", 2),
        "MS": ("apoio_sem_cargo", "indefinido", "adverso", 2),
        "DF": ("oposicao", "indefinido", "adverso", 3),
        "PA": ("apoio_sem_cargo", "vice_aliado", "em_construcao", 4),
        "AM": ("apoio_sem_cargo", "indefinido", "disputado", 3),
        "AC": ("oposicao", "oposicao", "adverso", 2),
        "RO": ("oposicao", "oposicao", "adverso", 2),
        "RR": ("oposicao", "oposicao", "adverso", 2),
        "AP": ("apoio_sem_cargo", "indefinido", "em_construcao", 3),
        "TO": ("apoio_sem_cargo", "indefinido", "disputado", 3),
        "ES": ("apoio_sem_cargo", "indefinido", "disputado", 3),
    }

    for sigla, estado_id in estados_map.items():
        existing = db.query(StatusPTEstado).filter(StatusPTEstado.estado_id == estado_id).first()
        if existing:
            continue
        gov, sen, nivel, prio = presets.get(sigla, ("indefinido", "indefinido", "em_construcao", 3))
        db.add(
            StatusPTEstado(
                estado_id=estado_id,
                eleicao_id=eleicao_id,
                cenario_governador=gov,
                cenario_senado=sen,
                nivel_consolidacao=nivel,
                prioridade_estrategica=prio,
            )
        )
    db.commit()


def seed_admin_user(db: Session):
    """Cria usuário admin padrão se não existir."""
    admin_email = "admin@bussola.app"
    existing = db.query(PerfilUsuario).filter(PerfilUsuario.email == admin_email).first()
    if not existing:
        db.add(
            PerfilUsuario(
                email=admin_email,
                senha_hash=hash_password("admin123"),
                nome_completo="Administrador",
                nome_exibicao="Admin",
                papel="admin",
                ativo=True,
            )
        )
        db.commit()
        print(f"[seed] Usuário admin criado: {admin_email} / admin123")


def run_all():
    """Cria tabelas e roda todos os seeds."""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("[seed] Estados...")
        estados = seed_estados(db)
        print(f"  - {len(estados)} estados")

        print("[seed] Partidos...")
        partidos = seed_partidos(db)
        print(f"  - {len(partidos)} partidos")

        print("[seed] Federacoes...")
        seed_federacoes(db, partidos)

        print("[seed] Eleicoes...")
        eleicoes = seed_eleicoes(db)
        print(f"  - {len(eleicoes)} eleicoes")

        print("[seed] Institutos de pesquisa...")
        seed_institutos(db)

        print("[seed] Fontes RSS...")
        seed_fontes_rss(db, estados)

        print("[seed] Status PT por estado (cenario inicial 2026)...")
        seed_status_pt_inicial(db, estados, eleicoes)

        print("[seed] Usuario admin...")
        seed_admin_user(db)

        print("[seed] Concluido.")
    finally:
        db.close()


if __name__ == "__main__":
    run_all()
