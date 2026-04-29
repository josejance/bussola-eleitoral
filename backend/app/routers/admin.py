"""Endpoints administrativos: trigger de ingestões, status, configuração de fontes."""
import json
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import FonteRSS, Materia, MateriaEstado, MateriaMetadata
from app.services.ai_poll_analyzer import analisar_pesquisa, aplicar_sugestao_status
from app.services.deps import require_role
from app.services.poll_importer import detectar_formato, importar_json
from app.workers.rss_poller import run_polling

logger = logging.getLogger("admin_router")

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ingestao/rss/status")
def status_ingestao_rss(db: Session = Depends(get_db), _user=Depends(require_role("admin", "editor_nacional"))):
    """Estatísticas gerais de ingestão RSS."""
    total_fontes = db.query(FonteRSS).count()
    fontes_ativas = db.query(FonteRSS).filter(FonteRSS.ativo == True).count()  # noqa: E712
    fontes_estaduais = (
        db.query(FonteRSS).filter(FonteRSS.ativo == True, FonteRSS.abrangencia == "estadual").count()  # noqa: E712
    )
    fontes_nacionais = (
        db.query(FonteRSS).filter(FonteRSS.ativo == True, FonteRSS.abrangencia == "nacional").count()  # noqa: E712
    )

    total_materias = db.query(Materia).count()
    aproveitadas = db.query(Materia).filter(Materia.aproveitada == True).count()  # noqa: E712

    ultimo_polling = (
        db.query(func.max(FonteRSS.ultimo_polling)).scalar()
    )

    capturadas_24h = (
        db.query(Materia)
        .filter(Materia.data_captura >= datetime.utcnow() - timedelta(hours=24))
        .count()
    )

    fontes_com_falha = (
        db.query(FonteRSS)
        .filter(
            FonteRSS.ativo == True,  # noqa: E712
            FonteRSS.ultimo_polling.isnot(None),
            (FonteRSS.ultimo_sucesso.is_(None))
            | (FonteRSS.ultimo_polling > FonteRSS.ultimo_sucesso),
        )
        .count()
    )

    return {
        "total_fontes": total_fontes,
        "fontes_ativas": fontes_ativas,
        "fontes_estaduais": fontes_estaduais,
        "fontes_nacionais": fontes_nacionais,
        "total_materias": total_materias,
        "materias_aproveitadas": aproveitadas,
        "capturadas_ultimas_24h": capturadas_24h,
        "fontes_com_falha_ultima": fontes_com_falha,
        "ultimo_polling": ultimo_polling.isoformat() if ultimo_polling else None,
    }


@router.get("/ingestao/rss/fontes")
def list_fontes_status(
    incluir_inativas: bool = Query(False),
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin", "editor_nacional")),
):
    """Lista todas as fontes com seus stats individuais."""
    q = db.query(FonteRSS)
    if not incluir_inativas:
        q = q.filter(FonteRSS.ativo == True)  # noqa: E712
    fontes = q.order_by(FonteRSS.abrangencia, FonteRSS.nome).all()

    return [
        {
            "id": f.id,
            "nome": f.nome,
            "url_feed": f.url_feed,
            "url_site": f.url_site,
            "tipo": f.tipo,
            "abrangencia": f.abrangencia,
            "espectro_editorial": f.espectro_editorial,
            "confiabilidade": f.confiabilidade,
            "peso_editorial": f.peso_editorial,
            "frequencia_polling_minutos": f.frequencia_polling_minutos,
            "ativo": f.ativo,
            "ultimo_polling": f.ultimo_polling.isoformat() if f.ultimo_polling else None,
            "ultimo_sucesso": f.ultimo_sucesso.isoformat() if f.ultimo_sucesso else None,
            "total_materias_capturadas": f.total_materias_capturadas or 0,
            "total_materias_aproveitadas": f.total_materias_aproveitadas or 0,
            "esta_em_falha": (
                f.ultimo_polling is not None
                and (f.ultimo_sucesso is None or f.ultimo_polling > f.ultimo_sucesso)
            ),
        }
        for f in fontes
    ]


def _run_polling_in_bg(apenas_devidas: bool, fontes_ids: list[str] | None):
    """Executa polling com sessão própria (background task não pode usar a do request)."""
    db = SessionLocal()
    try:
        return run_polling(db=db, apenas_devidas=apenas_devidas, fontes_ids=fontes_ids)
    finally:
        db.close()


@router.post("/ingestao/rss/run")
def trigger_polling_rss(
    background_tasks: BackgroundTasks,
    todas: bool = Query(False, description="Se True, ignora janela de polling e processa todas as fontes ativas"),
    fonte_id: str | None = Query(None, description="Polling específico de uma fonte (sobrescreve 'todas')"),
    sincrono: bool = Query(False, description="Se True, roda síncrono e retorna sumário (pode demorar)"),
    _user=Depends(require_role("admin", "editor_nacional")),
):
    """Dispara polling de RSS. Por padrão roda em background."""
    fontes_ids = [fonte_id] if fonte_id else None
    apenas_devidas = not todas and not fonte_id

    if sincrono:
        return _run_polling_in_bg(apenas_devidas=apenas_devidas, fontes_ids=fontes_ids)

    background_tasks.add_task(_run_polling_in_bg, apenas_devidas, fontes_ids)
    return {
        "status": "iniciado em background",
        "fontes_alvo": "específica" if fonte_id else ("todas ativas" if todas else "apenas devidas"),
    }


@router.patch("/ingestao/rss/fontes/{fonte_id}")
def update_fonte(
    fonte_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin")),
):
    """Permite ativar/desativar, ajustar espectro, peso, frequência."""
    f = db.query(FonteRSS).filter(FonteRSS.id == fonte_id).first()
    if not f:
        raise HTTPException(404, "Fonte não encontrada")

    campos_editaveis = {
        "ativo",
        "espectro_editorial",
        "confiabilidade",
        "peso_editorial",
        "frequencia_polling_minutos",
        "url_feed",
        "url_site",
        "observacao",
    }
    for k, v in payload.items():
        if k in campos_editaveis:
            setattr(f, k, v)
    db.commit()
    db.refresh(f)
    return {"id": f.id, "atualizado": True}


@router.post("/pesquisas/reextrair-todas")
def reextrair_todas_pesquisas(
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin", "editor_nacional")),
):
    """Re-extrai TODAS as pesquisas a partir do JSON bruto.

    Útil quando o re-extrator é melhorado. Apaga avaliações/intenções existentes
    e re-processa do zero.
    """
    from app.services.poll_reextractor import reextrair_todas
    return reextrair_todas(db)


@router.post("/pesquisas/importar-json")
def importar_pesquisa_json(
    payload: dict = Body(..., description="JSON da pesquisa (formato Quaest v1)"),
    rodar_ia: bool = Query(True, description="Executa análise via Claude se ANTHROPIC_API_KEY estiver configurada"),
    aplicar_sugestoes: bool = Query(False, description="Aplica sugestões da IA ao status_pt_estado (requer confiança ≥0.7)"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin", "editor_nacional", "editor_estadual")),
):
    """Importa pesquisa em formato JSON. Cria Pesquisa + AvaliacaoGoverno + IntencaoVoto.
    Opcionalmente analisa via Claude e aplica sugestões.
    """
    formato = detectar_formato(payload)
    if formato == "desconhecido":
        raise HTTPException(400, "Formato JSON não reconhecido. Suportados: quaest_v1")

    try:
        resultado = importar_json(db, payload, usuario_id=user.id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("Erro ao importar JSON")
        raise HTTPException(500, f"Erro: {e}")

    out = {
        "import": resultado,
        "ia": None,
        "status_aplicado": None,
    }

    if rodar_ia and resultado.get("status") == "criada":
        analise_res = analisar_pesquisa(db, payload, pesquisa_id=resultado["pesquisa_id"])
        out["ia"] = analise_res

        if aplicar_sugestoes and analise_res.get("status") == "ok":
            from app.models import Estado, Pesquisa
            pesquisa = db.query(Pesquisa).filter(Pesquisa.id == resultado["pesquisa_id"]).first()
            if pesquisa and pesquisa.estado_id:
                out["status_aplicado"] = aplicar_sugestao_status(
                    db, pesquisa.estado_id, analise_res["analise"], usuario_id=user.id
                )

    return out


@router.post("/pesquisas/{pesquisa_id}/analisar-ia")
def reanalisar_pesquisa(
    pesquisa_id: str,
    aplicar_sugestoes: bool = Query(False),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin", "editor_nacional", "editor_estadual")),
):
    """Roda análise IA sobre o JSON bruto de uma pesquisa já importada.
    Útil para pesquisas importadas antes de ANTHROPIC_API_KEY ser configurada,
    ou para re-analisar quando o prompt/modelo é atualizado.
    """
    from app.models import Pesquisa
    from app.models.poll import PesquisaDadosBrutos

    bruto = (
        db.query(PesquisaDadosBrutos)
        .filter(PesquisaDadosBrutos.pesquisa_id == pesquisa_id)
        .first()
    )
    if not bruto:
        raise HTTPException(404, "Pesquisa sem dados brutos para analisar")

    try:
        json_data = json.loads(bruto.dados_json)
    except json.JSONDecodeError as e:
        raise HTTPException(500, f"JSON bruto corrompido: {e}")

    analise_res = analisar_pesquisa(db, json_data, pesquisa_id=pesquisa_id)

    out = {"ia": analise_res, "status_aplicado": None}

    if aplicar_sugestoes and analise_res.get("status") == "ok":
        pesquisa = db.query(Pesquisa).filter(Pesquisa.id == pesquisa_id).first()
        if pesquisa and pesquisa.estado_id:
            out["status_aplicado"] = aplicar_sugestao_status(
                db, pesquisa.estado_id, analise_res["analise"], usuario_id=user.id
            )

    return out


@router.get("/pesquisas/{pesquisa_id}/dados-brutos")
def get_dados_brutos(
    pesquisa_id: str,
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin", "editor_nacional", "editor_estadual")),
):
    """Retorna o JSON original e a análise IA de uma pesquisa importada."""
    from app.models.poll import PesquisaDadosBrutos

    bruto = (
        db.query(PesquisaDadosBrutos)
        .filter(PesquisaDadosBrutos.pesquisa_id == pesquisa_id)
        .first()
    )
    if not bruto:
        raise HTTPException(404, "Dados brutos não encontrados para essa pesquisa")
    return {
        "pesquisa_id": pesquisa_id,
        "formato_origem": bruto.formato_origem,
        "importado_em": bruto.importado_em.isoformat() if bruto.importado_em else None,
        "dados_json": json.loads(bruto.dados_json),
        "analise_ia": json.loads(bruto.analise_ia_json) if bruto.analise_ia_json else None,
    }


@router.post("/ingestao/camara/run")
def trigger_camara(
    background_tasks: BackgroundTasks,
    com_detalhes: bool = Query(False, description="Busca detalhe individual de cada deputado (lento, ~3min)"),
    sincrono: bool = Query(False),
    _user=Depends(require_role("admin", "editor_nacional")),
):
    """Sincroniza deputados em exercício da Câmara."""
    from app.workers.camara import sincronizar_camara

    def _run():
        db = SessionLocal()
        try:
            return sincronizar_camara(db=db, com_detalhes=com_detalhes)
        finally:
            db.close()

    if sincrono:
        return _run()
    background_tasks.add_task(_run)
    return {"status": "iniciado em background"}


@router.post("/ingestao/senado/run")
def trigger_senado(
    background_tasks: BackgroundTasks,
    sincrono: bool = Query(False),
    _user=Depends(require_role("admin", "editor_nacional")),
):
    """Sincroniza senadores em exercício."""
    from app.workers.senado import sincronizar_senado

    def _run():
        db = SessionLocal()
        try:
            return sincronizar_senado(db=db)
        finally:
            db.close()

    if sincrono:
        return _run()
    background_tasks.add_task(_run)
    return {"status": "iniciado em background"}


@router.post("/ingestao/tse/run")
def trigger_tse(
    background_tasks: BackgroundTasks,
    ano: int = Query(..., description="Ano da eleição (2018, 2022, 2024)"),
    uf: str = Query(..., description="Sigla UF (BA, SP, ...) ou BR para todos"),
    apenas_principais: bool = Query(True, description="Importar só Pres/Gov/Sen/DepFed"),
    sincrono: bool = Query(False),
    _user=Depends(require_role("admin")),
):
    """Ingere candidaturas TSE para um ano/UF (lento — pode demorar minutos)."""
    from app.workers.tse import ingerir_consulta_cand
    from app.models import Estado as _Estado

    def _run():
        db = SessionLocal()
        try:
            if uf.upper() == "BR":
                # Roda todas as UFs em sequência
                ufs = [e.sigla for e in db.query(_Estado).all()]
                resultados = []
                for u in ufs:
                    try:
                        r = ingerir_consulta_cand(ano, u, db=db, apenas_principais=apenas_principais)
                        resultados.append(r)
                    except Exception as e:
                        resultados.append({"uf": u, "erro": str(e)[:200]})
                return {"todas_ufs": True, "resultados": resultados}
            else:
                return ingerir_consulta_cand(ano, uf, db=db, apenas_principais=apenas_principais)
        finally:
            db.close()

    if sincrono:
        return _run()
    background_tasks.add_task(_run)
    return {"status": "iniciado em background", "ano": ano, "uf": uf}


@router.get("/ingestao/visao-geral")
def status_geral_ingestoes(
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin", "editor_nacional")),
):
    """Status agregado de todos os tipos de ingestão."""
    from app.models import Candidatura, Eleicao, Mandato, Materia, Pesquisa, Pessoa
    from app.models.opiniao import PesquisaTematica
    from sqlalchemy import func, distinct

    return {
        "rss": {
            "fontes_ativas": db.query(FonteRSS).filter(FonteRSS.ativo == True).count(),  # noqa: E712
            "materias_total": db.query(Materia).count(),
            "materias_aproveitadas": db.query(Materia).filter(Materia.aproveitada == True).count(),  # noqa: E712
            "ultimo_polling": (db.query(func.max(FonteRSS.ultimo_polling)).scalar() or "").__str__()[:19] if db.query(func.max(FonteRSS.ultimo_polling)).scalar() else None,
        },
        "camara": {
            "deputados_cadastrados": db.query(Mandato).filter(Mandato.cargo == "deputado_federal").count(),
            "deputados_ativos": db.query(Mandato).filter(
                Mandato.cargo == "deputado_federal",
                Mandato.fim >= datetime.utcnow().date(),
            ).count(),
        },
        "senado": {
            "senadores_cadastrados": db.query(Mandato).filter(Mandato.cargo == "senador").count(),
            "senadores_ativos": db.query(Mandato).filter(
                Mandato.cargo == "senador",
                Mandato.fim >= datetime.utcnow().date(),
            ).count(),
        },
        "tse": {
            "candidaturas_total": db.query(Candidatura).count(),
            "pessoas_total": db.query(Pessoa).filter(Pessoa.deleted_at.is_(None)).count(),
            "por_eleicao": [
                {"ano": ano, "total": n}
                for ano, n in db.query(Eleicao.ano, func.count(Candidatura.id))
                .join(Candidatura, Candidatura.eleicao_id == Eleicao.id)
                .group_by(Eleicao.ano)
                .order_by(Eleicao.ano.desc())
                .all()
            ],
        },
        "pesquisas": {
            "eleitorais": db.query(Pesquisa).count(),
            "tematicas": db.query(PesquisaTematica).count(),
        },
    }


@router.get("/ingestao/rss/recentes")
def materias_recentes(
    limit: int = Query(20, le=100),
    apenas_aproveitadas: bool = Query(True),
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin", "editor_nacional")),
):
    """Últimas matérias capturadas, com link para fonte e estados vinculados."""
    q = db.query(Materia)
    if apenas_aproveitadas:
        q = q.filter(Materia.aproveitada == True)  # noqa: E712
    materias = q.order_by(desc(Materia.data_captura)).limit(limit).all()

    fontes_map = {f.id: f.nome for f in db.query(FonteRSS).all()}
    estados_por_materia = {}
    materia_ids = [m.id for m in materias]
    if materia_ids:
        rows = (
            db.query(MateriaEstado.materia_id, MateriaEstado.estado_id)
            .filter(MateriaEstado.materia_id.in_(materia_ids))
            .all()
        )
        for mid, eid in rows:
            estados_por_materia.setdefault(mid, []).append(eid)

    return [
        {
            "id": m.id,
            "titulo": m.titulo,
            "snippet": m.snippet,
            "url": m.url,
            "imagem_url": m.imagem_url,
            "autor": m.autor,
            "data_publicacao": m.data_publicacao.isoformat() if m.data_publicacao else None,
            "data_captura": m.data_captura.isoformat() if m.data_captura else None,
            "fonte_nome": fontes_map.get(m.fonte_id, "?"),
            "estados_ids": estados_por_materia.get(m.id, []),
        }
        for m in materias
    ]
