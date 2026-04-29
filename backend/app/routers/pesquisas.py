from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AvaliacaoGoverno,
    InstitutoPesquisa,
    IntencaoVoto,
    Pesquisa,
    Pessoa,
)
from app.schemas.common import IntencaoVotoOut, PesquisaCreate, PesquisaOut
from app.services.deps import get_current_user, require_role

router = APIRouter(prefix="/pesquisas", tags=["pesquisas"])


@router.get("/institutos")
def list_institutos(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    """Lista institutos com contagem de pesquisas."""
    from sqlalchemy import func
    rows = (
        db.query(
            InstitutoPesquisa.id,
            InstitutoPesquisa.nome,
            InstitutoPesquisa.sigla,
            InstitutoPesquisa.confiabilidade_score,
            func.count(Pesquisa.id).label("total"),
        )
        .outerjoin(Pesquisa, Pesquisa.instituto_id == InstitutoPesquisa.id)
        .filter(InstitutoPesquisa.ativo == True)  # noqa: E712
        .group_by(InstitutoPesquisa.id)
        .order_by(desc("total"))
        .all()
    )
    return [
        {
            "id": r[0],
            "nome": r[1],
            "sigla": r[2],
            "confiabilidade_score": r[3],
            "total_pesquisas": r[4],
        }
        for r in rows
    ]


@router.get("/historico/avaliacao-governo")
def historico_avaliacao_governo(
    nivel: str = Query("estadual", description="estadual|presidencial|municipal"),
    estado_id: str | None = Query(None, description="Filtra por UF (apenas se nivel=estadual)"),
    pessoa_id: str | None = Query(None, description="Filtra por pessoa avaliada"),
    instituto_id: str | None = Query(None),
    desde: date | None = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Série temporal de aprovação/avaliação. Cada ponto: data, valores + metadata.

    Útil para gráfico de linha: aprovação do governo Lula no tempo,
    ou aprovação de governador estadual.
    """
    q = (
        db.query(AvaliacaoGoverno, Pesquisa, InstitutoPesquisa)
        .join(Pesquisa, Pesquisa.id == AvaliacaoGoverno.pesquisa_id)
        .join(InstitutoPesquisa, InstitutoPesquisa.id == Pesquisa.instituto_id)
        .filter(AvaliacaoGoverno.nivel == nivel)
        .filter(Pesquisa.status_revisao == "aprovada")
    )
    if estado_id:
        q = q.filter(Pesquisa.estado_id == estado_id)
    if pessoa_id:
        q = q.filter(AvaliacaoGoverno.pessoa_avaliada_id == pessoa_id)
    if instituto_id:
        q = q.filter(Pesquisa.instituto_id == instituto_id)
    if desde:
        q = q.filter(AvaliacaoGoverno.periodo_referencia >= desde)

    # Ordena por periodo_referencia (série histórica) com fallback para data_fim_campo
    rows = q.all()

    # Hidrata pessoa_avaliada
    pessoa_ids = list({r[0].pessoa_avaliada_id for r in rows if r[0].pessoa_avaliada_id})
    pessoas_map = {
        p.id: p
        for p in db.query(Pessoa).filter(Pessoa.id.in_(pessoa_ids)).all()
    } if pessoa_ids else {}

    out = []
    for av, pesq, inst in rows:
        # Usa periodo_referencia se existir, senão data_fim_campo
        data_efetiva = av.periodo_referencia or pesq.data_fim_campo
        out.append({
            "pesquisa_id": pesq.id,
            "data": data_efetiva.isoformat() if data_efetiva else None,
            "data_pesquisa": pesq.data_fim_campo.isoformat() if pesq.data_fim_campo else None,
            "instituto": {
                "id": inst.id,
                "nome": inst.nome,
                "sigla": inst.sigla,
                "confiabilidade": inst.confiabilidade_score,
            },
            "pessoa_avaliada": (
                {
                    "id": pessoas_map[av.pessoa_avaliada_id].id,
                    "nome": pessoas_map[av.pessoa_avaliada_id].nome_urna or pessoas_map[av.pessoa_avaliada_id].nome_completo,
                }
                if av.pessoa_avaliada_id and av.pessoa_avaliada_id in pessoas_map
                else None
            ),
            "amostra": pesq.amostra,
            "margem_erro": float(pesq.margem_erro) if pesq.margem_erro else None,
            "registro_tse": pesq.registro_tse,
            "aprova": float(av.aprova) if av.aprova is not None else None,
            "desaprova": float(av.desaprova) if av.desaprova is not None else None,
            "otimo_bom": float(av.otimo_bom) if av.otimo_bom is not None else None,
            "regular": float(av.regular) if av.regular is not None else None,
            "ruim_pessimo": float(av.ruim_pessimo) if av.ruim_pessimo is not None else None,
            "nao_sabe": float(av.nao_sabe) if av.nao_sabe is not None else None,
        })
    out.sort(key=lambda x: x["data"] or "0000")
    return out


@router.get("/{pesquisa_id}/cenarios")
def cenarios_de_pesquisa(
    pesquisa_id: str,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Agrupa as intenções de uma pesquisa por cenário (1T-Cenário I, 2T-Cenário 1, etc)."""
    import json
    intencoes = (
        db.query(IntencaoVoto)
        .filter(IntencaoVoto.pesquisa_id == pesquisa_id)
        .order_by(IntencaoVoto.posicao_no_cenario)
        .all()
    )
    cenarios: dict[str, list] = {}
    for i in intencoes:
        recorte = json.loads(i.recorte_json) if i.recorte_json else {}
        cen_label = recorte.get("cenario") or "Cenário único"
        cenarios.setdefault(cen_label, []).append({
            "nome": i.nome_referencia,
            "percentual": float(i.percentual) if i.percentual else 0,
            "posicao": i.posicao_no_cenario,
            "pessoa_id": i.pessoa_id,
        })

    # Ordena cenários: Espontânea, 1T, 2T
    def _sort_key(label: str):
        if "Espont" in label:
            return (0, label)
        if "1T" in label or "1º" in label:
            return (1, label)
        if "2T" in label or "2º" in label:
            return (2, label)
        return (3, label)

    return {
        "pesquisa_id": pesquisa_id,
        "cenarios": [
            {"label": cen, "candidatos": sorted(cands, key=lambda c: c.get("posicao") or 999)}
            for cen, cands in sorted(cenarios.items(), key=lambda x: _sort_key(x[0]))
        ],
    }


@router.get("/agregador")
def agregador_pesquisas(
    estado_id: str | None = Query(None, description="Se vazio: agregado nacional"),
    cargo: str | None = Query(None),
    cenario: str = Query("estimulado"),
    desde: date | None = Query(None),
    incluir_apenas_tse: bool = Query(False),
    meia_vida_dias: int = Query(14, ge=3, le=60),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Agregador estatístico ponderado de intenções de voto."""
    from app.services.aggregator import calcular_agregado
    return calcular_agregado(
        db,
        estado_id=estado_id,
        cargo=cargo,
        cenario=cenario,
        desde=desde,
        incluir_apenas_tse=incluir_apenas_tse,
        meia_vida_dias=meia_vida_dias,
    )


@router.get("/agregador/monte-carlo")
def monte_carlo_endpoint(
    estado_id: str | None = Query(None),
    cenario: str = Query("estimulado"),
    n_simulacoes: int = Query(10000, ge=1000, le=50000),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Executa simulação Monte Carlo sobre o agregado atual.

    Retorna: prob de vitória 1T, prob de ir a 2T, top 5 cenários de 2T.
    """
    from app.services.aggregator import calcular_agregado, monte_carlo_simulacao

    agregado = calcular_agregado(db, estado_id=estado_id, cenario=cenario)
    candidatos = agregado.get("candidatos", [])
    # Filtra ruído (Branco/Nulo, Indecisos)
    candidatos = [
        c for c in candidatos
        if not any(k in c["nome"].lower() for k in ["branco", "nulo", "indeciso", "ns/nr", "não vai votar", "nao vai votar"])
    ][:8]  # top 8 candidatos reais

    return {
        "candidatos_considerados": [c["nome"] for c in candidatos],
        **monte_carlo_simulacao(candidatos, n_simulacoes=n_simulacoes),
    }


@router.get("/comparador")
def comparar_pesquisas(
    pesquisa_ids: str = Query(..., description="IDs separados por vírgula (max 5)"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Retorna detalhes de até 5 pesquisas para comparação lado a lado."""
    ids = [s.strip() for s in pesquisa_ids.split(",") if s.strip()][:5]
    if not ids:
        raise HTTPException(400, "Nenhum ID fornecido")

    rows = (
        db.query(Pesquisa, InstitutoPesquisa)
        .join(InstitutoPesquisa, InstitutoPesquisa.id == Pesquisa.instituto_id)
        .filter(Pesquisa.id.in_(ids))
        .all()
    )

    out = []
    for pesq, inst in rows:
        intencoes = (
            db.query(IntencaoVoto)
            .filter(IntencaoVoto.pesquisa_id == pesq.id)
            .order_by(IntencaoVoto.posicao_no_cenario)
            .all()
        )
        out.append(
            {
                "id": pesq.id,
                "instituto": {"id": inst.id, "nome": inst.nome, "sigla": inst.sigla},
                "data_fim_campo": pesq.data_fim_campo.isoformat() if pesq.data_fim_campo else None,
                "amostra": pesq.amostra,
                "margem_erro": float(pesq.margem_erro) if pesq.margem_erro else None,
                "registro_tse": pesq.registro_tse,
                "estado_id": pesq.estado_id,
                "abrangencia": pesq.abrangencia,
                "tipo_cenario": pesq.tipo_cenario,
                "intencoes": [
                    {
                        "nome": iv.nome_referencia,
                        "percentual": float(iv.percentual) if iv.percentual else 0,
                        "posicao": iv.posicao_no_cenario,
                    }
                    for iv in intencoes
                    if iv.nome_referencia and iv.percentual
                ],
            }
        )
    return out


@router.get("/historico/intencao-voto")
def historico_intencao_voto(
    eleicao_id: str | None = Query(None),
    estado_id: str | None = Query(None),
    cargo: str | None = Query(None, description="governador|senador|presidente"),
    instituto_id: str | None = Query(None),
    desde: date | None = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Série de intenções de voto agrupadas por candidato ao longo do tempo."""
    q = (
        db.query(IntencaoVoto, Pesquisa, InstitutoPesquisa)
        .join(Pesquisa, Pesquisa.id == IntencaoVoto.pesquisa_id)
        .join(InstitutoPesquisa, InstitutoPesquisa.id == Pesquisa.instituto_id)
        .filter(Pesquisa.status_revisao == "aprovada")
    )
    if eleicao_id:
        q = q.filter(Pesquisa.eleicao_id == eleicao_id)
    if estado_id:
        q = q.filter(Pesquisa.estado_id == estado_id)
    if instituto_id:
        q = q.filter(Pesquisa.instituto_id == instituto_id)
    if desde:
        q = q.filter(Pesquisa.data_fim_campo >= desde)

    rows = q.order_by(Pesquisa.data_fim_campo).all()

    return [
        {
            "pesquisa_id": pesq.id,
            "data": pesq.data_fim_campo.isoformat() if pesq.data_fim_campo else None,
            "instituto_nome": inst.nome,
            "instituto_id": inst.id,
            "candidato_nome": iv.nome_referencia,
            "percentual": float(iv.percentual) if iv.percentual else 0,
            "posicao": iv.posicao_no_cenario,
            "amostra": pesq.amostra,
            "margem_erro": float(pesq.margem_erro) if pesq.margem_erro else None,
        }
        for iv, pesq, inst in rows
    ]


@router.get("", response_model=list[PesquisaOut])
def list_pesquisas(
    estado_id: str | None = Query(None),
    instituto_id: str | None = Query(None),
    desde: date | None = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    q = db.query(Pesquisa)
    if estado_id:
        q = q.filter(Pesquisa.estado_id == estado_id)
    if instituto_id:
        q = q.filter(Pesquisa.instituto_id == instituto_id)
    if desde:
        q = q.filter(Pesquisa.data_fim_campo >= desde)
    return q.order_by(desc(Pesquisa.data_fim_campo)).limit(limit).all()


@router.post("", response_model=PesquisaOut, status_code=201)
def create_pesquisa(
    payload: PesquisaCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin", "editor_nacional", "editor_estadual")),
):
    p = Pesquisa(**payload.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.get("/{pesquisa_id}", response_model=PesquisaOut)
def get_pesquisa(pesquisa_id: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    p = db.query(Pesquisa).filter(Pesquisa.id == pesquisa_id).first()
    if not p:
        raise HTTPException(404, "Pesquisa não encontrada")
    return p


@router.get("/{pesquisa_id}/intencoes", response_model=list[IntencaoVotoOut])
def list_intencoes(pesquisa_id: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return (
        db.query(IntencaoVoto)
        .filter(IntencaoVoto.pesquisa_id == pesquisa_id)
        .order_by(IntencaoVoto.posicao_no_cenario)
        .all()
    )
