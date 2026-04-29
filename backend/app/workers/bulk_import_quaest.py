"""Bulk import de JSONs Quaest a partir de um diretório.

Uso:
    python -m app.workers.bulk_import_quaest [diretorio]

Itera sobre todos os .json, importa cada um, ignora erros isolados
(JSON malformado, etc.) e gera relatório consolidado.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from app.database import SessionLocal
from app.models.base import Base
from app.database import engine
from app.services.poll_importer import importar_json

logger = logging.getLogger("bulk_import")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def bulk_import(diretorio: str | Path) -> dict:
    """Importa todos os .json de um diretório."""
    Base.metadata.create_all(bind=engine)  # garante tabelas novas

    diretorio = Path(diretorio)
    if not diretorio.is_dir():
        raise ValueError(f"{diretorio} não é diretório")

    arquivos = sorted(diretorio.glob("*.json"))
    logger.info(f"Encontrados {len(arquivos)} arquivos JSON em {diretorio}")

    sumario = {
        "total_arquivos": len(arquivos),
        "criadas": 0,
        "ja_existentes": 0,
        "erros_parse": 0,
        "erros_import": 0,
        "por_tipo": {"eleitoral_estadual": 0, "eleitoral_nacional": 0, "tematica": 0},
        "detalhes": [],
    }

    db = SessionLocal()
    try:
        for arq in arquivos:
            entry = {"arquivo": arq.name}

            # 1) Parse JSON
            try:
                with open(arq, encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                entry["status"] = "erro_parse"
                entry["erro"] = f"JSON malformado: {e}"[:200]
                sumario["erros_parse"] += 1
                sumario["detalhes"].append(entry)
                logger.warning(f"  [PARSE ERR] {arq.name}: {e}")
                continue

            # 2) Importa
            try:
                resultado = importar_json(db, data, arquivo_origem=arq.name)
                tipo = resultado.get("tipo", "?")
                status = resultado.get("status", "?")
                entry["status"] = status
                entry["tipo"] = tipo
                entry["pesquisa_id"] = resultado.get("pesquisa_id")
                entry["estatisticas"] = resultado.get("estatisticas")
                entry["mensagens"] = resultado.get("mensagens")

                if status == "criada":
                    sumario["criadas"] += 1
                    if tipo in sumario["por_tipo"]:
                        sumario["por_tipo"][tipo] += 1
                    estats = resultado.get("estatisticas") or {}
                    extras = []
                    if "avaliacoes" in estats:
                        extras.append(f"{estats['avaliacoes']} aval")
                    if "intencoes" in estats:
                        extras.append(f"{estats['intencoes']} int")
                    if "questoes" in estats:
                        extras.append(f"{estats['questoes']} questoes")
                    extra_str = " | ".join(extras) if extras else ""
                    logger.info(f"  [OK] {arq.name}: {tipo} {extra_str}")
                elif status == "ja_existente":
                    sumario["ja_existentes"] += 1
                    logger.info(f"  [SKIP] {arq.name}: ja existente")

            except Exception as e:
                db.rollback()
                entry["status"] = "erro_import"
                entry["erro"] = str(e)[:300]
                sumario["erros_import"] += 1
                logger.warning(f"  [IMPORT ERR] {arq.name}: {e}")

            sumario["detalhes"].append(entry)
    finally:
        db.close()

    return sumario


def imprimir_sumario(sumario: dict):
    print("\n" + "=" * 60)
    print("  SUMARIO DA IMPORTACAO")
    print("=" * 60)
    print(f"Total arquivos:     {sumario['total_arquivos']}")
    print(f"Criadas:            {sumario['criadas']}")
    print(f"Ja existentes:      {sumario['ja_existentes']}")
    print(f"Erros de parse:     {sumario['erros_parse']}")
    print(f"Erros de import:    {sumario['erros_import']}")
    print()
    print("Por tipo:")
    for tipo, n in sumario["por_tipo"].items():
        print(f"  {tipo}: {n}")
    print()
    print("Detalhes:")
    for d in sumario["detalhes"]:
        status = d.get("status", "?")
        tipo = d.get("tipo", "")
        extra = ""
        if d.get("estatisticas"):
            e = d["estatisticas"]
            parts = [f"{k}={v}" for k, v in e.items() if v]
            extra = " | " + ", ".join(parts) if parts else ""
        print(f"  [{status:15s}] {d['arquivo']:50s} {tipo}{extra}")
        if d.get("erro"):
            print(f"      ERRO: {d['erro'][:100]}")


if __name__ == "__main__":
    diretorio = sys.argv[1] if len(sys.argv) > 1 else "data/pesquisas"
    sumario = bulk_import(diretorio)
    imprimir_sumario(sumario)
