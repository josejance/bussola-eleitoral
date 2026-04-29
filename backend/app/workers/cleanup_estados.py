"""Reprocessa filtro em matérias existentes com a versão atual de filtrar_materia.

Atualiza:
- Vinculações materia↔estado (remove falsos positivos, adiciona corretos)
- Vinculações materia↔pessoa (auto-detectadas pelo entity matcher)
- Vinculações materia↔partido
- Score de relevância em materia_metadata
- Flag aproveitada e motivo_descarte da matéria

Útil quando:
- Filtro foi melhorado (regras novas)
- Lista de pessoas cadastradas mudou (novos pré-candidatos)
- Quer reaplicar entity matching em matérias antigas
"""
import json
import logging

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Estado,
    FonteRSS,
    Materia,
    MateriaEstado,
    MateriaPartido,
    MateriaPessoa,
)
from app.models.media import MateriaMetadata
from app.services.text_filter import filtrar_materia, invalidar_cache_entidades

logger = logging.getLogger("cleanup")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def run_cleanup(db: Session | None = None, somente_aproveitadas: bool = False) -> dict:
    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        invalidar_cache_entidades()  # garante snapshot fresh
        estados_por_sigla = {e.sigla: e.id for e in db.query(Estado).all()}

        q = db.query(Materia)
        if somente_aproveitadas:
            q = q.filter(Materia.aproveitada == True)  # noqa: E712
        materias = q.all()
        logger.info(f"Reprocessando {len(materias)} materias")

        fontes_cache: dict[str, FonteRSS] = {f.id: f for f in db.query(FonteRSS).all()}

        stats = {
            "total": len(materias),
            "agora_aproveitadas": 0,
            "agora_descartadas": 0,
            "estados_adicionados": 0,
            "estados_removidos": 0,
            "pessoas_adicionadas": 0,
            "pessoas_removidas": 0,
            "partidos_adicionados": 0,
            "partidos_removidos": 0,
        }

        for m in materias:
            fonte = fontes_cache.get(m.fonte_id)
            fonte_estadual = fonte and fonte.abrangencia == "estadual"
            res = filtrar_materia(m.titulo or "", m.snippet or "", db=db, fonte_eh_estadual=fonte_estadual)

            # Atualiza flag de aproveitamento
            m.aproveitada = res.aproveitada
            m.motivo_descarte = res.motivo_descarte
            if res.aproveitada:
                stats["agora_aproveitadas"] += 1
            else:
                stats["agora_descartadas"] += 1

            # Se descartada, remove TODOS os vínculos
            if not res.aproveitada:
                rm_e = db.query(MateriaEstado).filter(MateriaEstado.materia_id == m.id).count()
                rm_p = db.query(MateriaPessoa).filter(MateriaPessoa.materia_id == m.id).count()
                rm_pa = db.query(MateriaPartido).filter(MateriaPartido.materia_id == m.id).count()
                db.query(MateriaEstado).filter(MateriaEstado.materia_id == m.id).delete()
                db.query(MateriaPessoa).filter(MateriaPessoa.materia_id == m.id).delete()
                db.query(MateriaPartido).filter(MateriaPartido.materia_id == m.id).delete()
                stats["estados_removidos"] += rm_e
                stats["pessoas_removidas"] += rm_p
                stats["partidos_removidos"] += rm_pa
                continue

            # ---- ESTADOS ----
            atuais_estados = {
                r.estado_id
                for r in db.query(MateriaEstado).filter(MateriaEstado.materia_id == m.id).all()
            }
            esperados_estados: set[str] = set()
            for sigla in res.estados_detectados:
                eid = estados_por_sigla.get(sigla)
                if eid:
                    esperados_estados.add(eid)
            if not esperados_estados and fonte and fonte.estados_cobertos_json:
                try:
                    esperados_estados.update(json.loads(fonte.estados_cobertos_json) or [])
                except json.JSONDecodeError:
                    pass

            for eid in atuais_estados - esperados_estados:
                db.query(MateriaEstado).filter(
                    MateriaEstado.materia_id == m.id,
                    MateriaEstado.estado_id == eid,
                ).delete()
                stats["estados_removidos"] += 1
            for eid in esperados_estados - atuais_estados:
                db.add(MateriaEstado(materia_id=m.id, estado_id=eid, relevancia_para_estado=res.score_relevancia))
                stats["estados_adicionados"] += 1

            # ---- PESSOAS ----
            atuais_pessoas = {
                r.pessoa_id
                for r in db.query(MateriaPessoa).filter(MateriaPessoa.materia_id == m.id).all()
            }
            esperadas_pessoas = set(res.pessoas_mencionadas_ids)
            for pid in atuais_pessoas - esperadas_pessoas:
                db.query(MateriaPessoa).filter(
                    MateriaPessoa.materia_id == m.id,
                    MateriaPessoa.pessoa_id == pid,
                ).delete()
                stats["pessoas_removidas"] += 1
            for pid in esperadas_pessoas - atuais_pessoas:
                db.add(MateriaPessoa(materia_id=m.id, pessoa_id=pid))
                stats["pessoas_adicionadas"] += 1

            # ---- PARTIDOS ----
            atuais_partidos = {
                r.partido_id
                for r in db.query(MateriaPartido).filter(MateriaPartido.materia_id == m.id).all()
            }
            esperados_partidos = set(res.partidos_mencionados_ids)
            for pid in atuais_partidos - esperados_partidos:
                db.query(MateriaPartido).filter(
                    MateriaPartido.materia_id == m.id,
                    MateriaPartido.partido_id == pid,
                ).delete()
                stats["partidos_removidos"] += 1
            for pid in esperados_partidos - atuais_partidos:
                db.add(MateriaPartido(materia_id=m.id, partido_id=pid))
                stats["partidos_adicionados"] += 1

            # ---- METADATA (atualiza score) ----
            meta = db.query(MateriaMetadata).filter(MateriaMetadata.materia_id == m.id).first()
            if meta:
                meta.relevancia_estrategica = res.score_relevancia
                meta.modelo_usado = "filtro_entidades"

        db.commit()
        logger.info(f"Cleanup OK: {stats}")
        return stats

    finally:
        if own_session:
            db.close()


if __name__ == "__main__":
    sumario = run_cleanup()
    print(f"\nResultado:")
    for k, v in sumario.items():
        print(f"  {k}: {v}")
