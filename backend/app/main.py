import logging
import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import SessionLocal, engine
from app.models.base import Base
from app.routers import admin, alertas, auth, candidaturas, estados, eventos, governo, midia, notas, opiniao, partidos, pesquisas, pessoas, simulador
from app.workers.camara import sincronizar_camara
from app.workers.rss_poller import run_polling
from app.workers.senado import sincronizar_senado

# Cria tabelas (idempotente). Em produção, usar Alembic.
Base.metadata.create_all(bind=engine)

logger = logging.getLogger("bussola")

# ---------------- Scheduler RSS ----------------

scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")


def _job_polling_rss():
    """Job agendado: polling de fontes cuja janela expirou."""
    db = SessionLocal()
    try:
        sumario = run_polling(db=db, apenas_devidas=True)
        logger.info(
            f"[scheduler] polling RSS: {sumario['fontes_processadas']} fontes, "
            f"{sumario['novas']} novas matérias ({sumario['aproveitadas']} aproveitadas), "
            f"{sumario['erros']} erros, {sumario['duracao_segundos']}s"
        )
    except Exception as e:
        logger.exception(f"[scheduler] erro no job RSS: {e}")
    finally:
        db.close()


def _job_sync_camara():
    """Job diário: sincroniza deputados da Câmara (modo rápido)."""
    db = SessionLocal()
    try:
        s = sincronizar_camara(db=db, com_detalhes=False)
        logger.info(
            f"[scheduler] Câmara: {s['atualizadas']} atualizados, "
            f"{s['mudancas_partido']} mudanças de partido"
        )
    except Exception as e:
        logger.exception(f"[scheduler] erro Câmara: {e}")
    finally:
        db.close()


def _job_sync_senado():
    """Job diário: sincroniza senadores."""
    db = SessionLocal()
    try:
        s = sincronizar_senado(db=db)
        logger.info(
            f"[scheduler] Senado: {s['atualizadas']} atualizados, "
            f"{s['mudancas_partido']} mudanças de partido"
        )
    except Exception as e:
        logger.exception(f"[scheduler] erro Senado: {e}")
    finally:
        db.close()


def _job_avaliar_alertas():
    """Job a cada 5min: avalia alertas configurados e cria notificações."""
    from app.services.alertas_engine import avaliar_todos_alertas
    db = SessionLocal()
    try:
        s = avaliar_todos_alertas(db)
        if s["notificacoes_criadas"] > 0:
            logger.info(
                f"[scheduler] alertas: {s['alertas_avaliados']} avaliados, "
                f"{s['notificacoes_criadas']} notificações criadas"
            )
    except Exception as e:
        logger.exception(f"[scheduler] erro alertas: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("ENABLE_SCHEDULERS", "1") == "1":
        scheduler.add_job(
            _job_polling_rss,
            trigger=IntervalTrigger(minutes=15, jitter=60),
            id="rss_polling",
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )
        # Câmara e Senado: 1x por dia
        scheduler.add_job(
            _job_sync_camara,
            trigger=IntervalTrigger(hours=24, jitter=600),
            id="camara_sync",
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )
        scheduler.add_job(
            _job_sync_senado,
            trigger=IntervalTrigger(hours=24, jitter=600),
            id="senado_sync",
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )
        scheduler.add_job(
            _job_avaliar_alertas,
            trigger=IntervalTrigger(minutes=5),
            id="alertas_engine",
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )
        scheduler.start()
        logger.info("Scheduler iniciado (RSS 15min, Câmara/Senado diário, alertas 5min)")
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="Bússola Eleitoral API",
    description="Plataforma de monitoramento eleitoral — backend local",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(estados.router, prefix=API_PREFIX)
app.include_router(partidos.router, prefix=API_PREFIX)
app.include_router(pesquisas.router, prefix=API_PREFIX)
app.include_router(eventos.router, prefix=API_PREFIX)
app.include_router(notas.router, prefix=API_PREFIX)
app.include_router(midia.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)
app.include_router(candidaturas.router, prefix=API_PREFIX)
app.include_router(opiniao.router, prefix=API_PREFIX)
app.include_router(pessoas.router, prefix=API_PREFIX)
app.include_router(governo.router, prefix=API_PREFIX)
app.include_router(alertas.router, prefix=API_PREFIX)
app.include_router(simulador.router, prefix=API_PREFIX)


@app.get("/")
def root():
    return {
        "app": "bussola-eleitoral",
        "version": "0.2.0",
        "status": "ok",
        "scheduler_ativo": scheduler.running,
    }


@app.get("/health")
def health():
    return {"status": "ok", "scheduler": scheduler.running}
