"""Endpoints do simulador de cenários."""
from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.deps import require_role
from app.services.simulador import simular_cenario

router = APIRouter(prefix="/simulador", tags=["simulador"])


# Cenários pré-configurados
CENARIOS_PRESET = {
    "atual": {
        "nome": "Cenário base atual (abr/2026)",
        "descricao": "Aprovação Lula em ~40%, status PT por estado conforme GTE 17/04/2026",
        "aprovacao_lula": 40.0,
        "ajustes_estados": {},
    },
    "lula_55": {
        "nome": "Lula com 55% de aprovação",
        "descricao": "Cenário otimista: aprovação alta puxa todos os candidatos da base",
        "aprovacao_lula": 55.0,
        "ajustes_estados": {},
    },
    "lula_30": {
        "nome": "Crise: Lula com 30% de aprovação",
        "descricao": "Cenário pessimista: queda de aprovação afeta candidatos aliados",
        "aprovacao_lula": 30.0,
        "ajustes_estados": {},
    },
    "uniao_brasil_base": {
        "nome": "União Brasil entra integralmente na base",
        "descricao": "Bonus +5pp em estados onde União Brasil é forte",
        "aprovacao_lula": 45.0,
        "ajustes_estados": {
            "BA": {"bonus_coligacao": 3},
            "RJ": {"bonus_coligacao": 5},
            "AP": {"bonus_coligacao": 8},
        },
    },
    "psb_rompe": {
        "nome": "PSB rompe com governo em 5 estados",
        "descricao": "PE, ES, MG, PB, MA — PSB sai da base; força candidatura própria PT",
        "aprovacao_lula": 40.0,
        "ajustes_estados": {
            "PE": {"cenario_governador": "candidatura_propria", "bonus_coligacao": -5},
            "ES": {"cenario_governador": "candidatura_propria", "bonus_coligacao": -5},
            "MG": {"cenario_governador": "candidatura_propria", "bonus_coligacao": -5},
            "PB": {"cenario_governador": "candidatura_propria", "bonus_coligacao": -5},
            "MA": {"cenario_governador": "apoio_sem_cargo", "bonus_coligacao": -5},
        },
    },
}


@router.get("/presets")
def list_presets(_user=Depends(require_role("admin", "editor_nacional", "editor_estadual"))):
    """Lista cenários pré-configurados."""
    return [
        {"key": key, **{k: v for k, v in val.items() if k != "ajustes_estados"}}
        for key, val in CENARIOS_PRESET.items()
    ]


@router.get("/presets/{key}")
def get_preset(
    key: str,
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin", "editor_nacional", "editor_estadual")),
):
    """Roda simulação de um preset."""
    preset = CENARIOS_PRESET.get(key)
    if not preset:
        return {"error": "preset não encontrado"}
    resultado = simular_cenario(
        db,
        aprovacao_lula=preset["aprovacao_lula"],
        ajustes_estados=preset["ajustes_estados"],
    )
    return {"preset": {"key": key, **{k: v for k, v in preset.items() if k != "ajustes_estados"}}, **resultado}


@router.post("/simular")
def simular(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin", "editor_nacional", "editor_estadual")),
):
    """Simula cenário customizado.

    Payload:
    {
      "aprovacao_lula": 40.0,
      "bonus_coligacao_geral": 0,
      "ajustes_estados": {
        "BA": {"cenario_governador": "candidatura_propria", "bonus_coligacao": 5}
      }
    }
    """
    return simular_cenario(
        db,
        aprovacao_lula=float(payload.get("aprovacao_lula", 40.0)),
        bonus_coligacao_geral=float(payload.get("bonus_coligacao_geral", 0)),
        ajustes_estados=payload.get("ajustes_estados") or {},
    )
