"""Ingestão TSE Dados Abertos — versão localhost.

Fonte: https://cdn.tse.jus.br/estatistica/sead/odsele/

Estratégia pragmática para localhost (CSVs grandes):
- Download SOB DEMANDA por (ano, uf) — não baixa tudo
- Cache local em data/tse/cache/
- Processamento em chunks
- Idempotente (verifica registros existentes)

Atualmente suporta:
- consulta_cand_AAAA: lista de candidaturas registradas
- votacao_partido_munzona_AAAA: agregação por partido (se baixado)
"""
from __future__ import annotations

import csv
import hashlib
import io
import logging
import time
import zipfile
from datetime import date
from pathlib import Path
from typing import Iterator

import httpx
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Candidatura,
    Eleicao,
    Estado,
    Mandato,
    Partido,
    Pessoa,
)

logger = logging.getLogger("tse")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

CDN_BASE = "https://cdn.tse.jus.br/estatistica/sead/odsele"
USER_AGENT = "BussolaEleitoralBot/0.1 (+localhost; pt-BR)"
CACHE_DIR = Path("data/tse/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ===== Cargo TSE → enum interno =====

CARGO_MAP = {
    "1": "presidente",
    "2": "vice_presidente",
    "3": "governador",
    "4": "vice_governador",
    "5": "senador",
    "6": "deputado_federal",
    "7": "deputado_estadual",
    "8": "deputado_distrital",
    "9": "1_suplente_senador",
    "10": "2_suplente_senador",
    "11": "prefeito",
    "12": "vice_prefeito",
    "13": "vereador",
}

STATUS_MAP = {
    "DEFERIDO": "deferido",
    "INDEFERIDO": "indeferido",
    "RENUNCIA": "renunciante",
    "FALECIDO": "falecido",
    "REGISTRADO": "registrado",
    "PENDENTE": "pre_candidatura",
    "CANDIDATO INAPTO": "indeferido",
    "AGUARDANDO JULGAMENTO": "sub_judice",
}


def _hash_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:32] if s else ""


def _normalizar_data(s: str) -> date | None:
    """Aceita dd/mm/yyyy."""
    if not s or s in ("#NULO#", "#NE#"):
        return None
    try:
        d, m, y = s.split("/")
        return date(int(y), int(m), int(d))
    except (ValueError, AttributeError):
        return None


# ===== Download =====

def url_consulta_cand(ano: int) -> str:
    return f"{CDN_BASE}/consulta_cand/consulta_cand_{ano}.zip"


def baixar_zip(url: str, destino: Path, progress: bool = True) -> Path:
    """Baixa zip se não estiver em cache."""
    if destino.exists() and destino.stat().st_size > 1000:
        logger.info(f"  Cache hit: {destino.name}")
        return destino

    logger.info(f"  Download: {url}")
    with httpx.stream("GET", url, headers={"User-Agent": USER_AGENT}, timeout=600, follow_redirects=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        with open(destino, "wb") as f:
            for chunk in r.iter_bytes(chunk_size=8192 * 16):
                f.write(chunk)
                downloaded += len(chunk)
                if progress and total:
                    pct = downloaded * 100 // total
                    if downloaded % (8192 * 64) < 8192 * 16:
                        print(f"\r    {pct}% ({downloaded // 1024 // 1024} MB)", end="")
    if progress:
        print()
    logger.info(f"  Concluido: {destino.stat().st_size // 1024 // 1024} MB")
    return destino


def listar_csvs_zip(zip_path: Path, ano: int, uf: str | None = None) -> list[str]:
    """Lista nomes de CSVs dentro do zip, opcionalmente filtrando por UF."""
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        if uf:
            uf = uf.upper()
            names = [n for n in names if f"_{uf}_" in n.upper() or n.upper().endswith(f"_{uf}.CSV")]
        return [n for n in names if n.lower().endswith(".csv")]


def ler_csv_zip(zip_path: Path, csv_name: str, encoding: str = "latin-1") -> Iterator[dict]:
    """Itera linhas do CSV (sep=';', encoding latin-1 padrão TSE)."""
    with zipfile.ZipFile(zip_path) as z:
        with z.open(csv_name) as f:
            text = io.TextIOWrapper(f, encoding=encoding, newline="")
            reader = csv.DictReader(text, delimiter=";")
            for row in reader:
                yield row


# ===== Processamento de candidaturas =====

def processar_consulta_cand(
    db: Session,
    zip_path: Path,
    ano: int,
    uf: str,
    eleicao: Eleicao,
    estados_por_sigla: dict[str, str],
    partidos_por_sigla: dict[str, str],
    apenas_principais: bool = False,
) -> dict:
    """Processa CSV consulta_cand de uma UF. Cria Pessoa + Candidatura.

    apenas_principais: se True, importa apenas Presidente/Governador/Senador/Deputado Federal
                       (pula Estadual, Vereador, Prefeito — útil pra demo)
    """
    stats = {"total_linhas": 0, "candidaturas_criadas": 0, "pessoas_criadas": 0, "erros": 0, "puladas": 0}

    csvs = listar_csvs_zip(zip_path, ano, uf)
    if not csvs:
        logger.warning(f"  Nenhum CSV para UF={uf} no zip")
        return stats

    estado_id = estados_por_sigla.get(uf.upper())
    cargos_aceitos = {"presidente", "vice_presidente", "governador", "vice_governador", "senador", "deputado_federal"}
    if not apenas_principais:
        cargos_aceitos |= {"deputado_estadual", "deputado_distrital", "1_suplente_senador", "2_suplente_senador"}

    pessoas_cache: dict[str, str] = {}  # cpf_hash → pessoa_id

    for csv_name in csvs:
        logger.info(f"  Processando {csv_name}...")
        batch_size = 0

        for row in ler_csv_zip(zip_path, csv_name):
            stats["total_linhas"] += 1

            try:
                cd_cargo = row.get("CD_CARGO", "")
                cargo = CARGO_MAP.get(cd_cargo)
                if not cargo or cargo not in cargos_aceitos:
                    stats["puladas"] += 1
                    continue

                # Apenas turno 1
                nr_turno = row.get("NR_TURNO", "1")
                if nr_turno != "1":
                    stats["puladas"] += 1
                    continue

                nome_completo = (row.get("NM_CANDIDATO") or "").strip()
                nome_urna = (row.get("NM_URNA_CANDIDATO") or "").strip()
                nr_cpf = (row.get("NR_CPF_CANDIDATO") or "").strip()
                cpf_hash = _hash_str(nr_cpf) if nr_cpf and nr_cpf != "-1" else None
                sg_partido = (row.get("SG_PARTIDO") or "").upper().strip()
                nr_urna_str = row.get("NR_CANDIDATO", "")
                nr_urna = int(nr_urna_str) if nr_urna_str.isdigit() else None
                ds_situacao = (row.get("DS_SITUACAO_CANDIDATURA") or "").upper().strip()
                status = STATUS_MAP.get(ds_situacao, "registrado")
                ds_nascimento = row.get("DT_NASCIMENTO")
                data_nasc = _normalizar_data(ds_nascimento)
                ds_genero = (row.get("DS_GENERO") or "").lower().strip()
                genero = {"feminino": "feminino", "masculino": "masculino"}.get(ds_genero)
                ds_raca = (row.get("DS_COR_RACA") or "").lower().strip()

                if not nome_completo:
                    continue

                partido_id = partidos_por_sigla.get(sg_partido)

                # Pessoa: identifica por cpf_hash quando disponível
                pessoa_id = None
                if cpf_hash and cpf_hash in pessoas_cache:
                    pessoa_id = pessoas_cache[cpf_hash]
                elif cpf_hash:
                    # Match no banco por cpf_hash
                    pessoa_existente = db.query(Pessoa).filter(Pessoa.cpf_hash == cpf_hash).first()
                    if pessoa_existente:
                        pessoa_id = pessoa_existente.id
                        pessoas_cache[cpf_hash] = pessoa_id

                if not pessoa_id:
                    # Cria pessoa
                    pessoa = Pessoa(
                        nome_completo=nome_completo,
                        nome_urna=nome_urna or nome_completo,
                        cpf_hash=cpf_hash,
                        nascimento=data_nasc,
                        genero=genero,
                        raca_cor=ds_raca if ds_raca and ds_raca != "#nulo#" else None,
                        estado_natal_id=estado_id,
                    )
                    db.add(pessoa)
                    db.flush()
                    pessoa_id = pessoa.id
                    if cpf_hash:
                        pessoas_cache[cpf_hash] = pessoa_id
                    stats["pessoas_criadas"] += 1

                # Candidatura: verifica duplicidade
                existing = (
                    db.query(Candidatura)
                    .filter(
                        Candidatura.eleicao_id == eleicao.id,
                        Candidatura.pessoa_id == pessoa_id,
                        Candidatura.cargo == cargo,
                        Candidatura.estado_id == estado_id,
                    )
                    .first()
                )
                if existing:
                    # Atualiza status / partido se mudou
                    if status != existing.status_registro:
                        existing.status_registro = status
                    if partido_id and existing.partido_id != partido_id:
                        existing.partido_id = partido_id
                    if nr_urna and not existing.numero_urna:
                        existing.numero_urna = nr_urna
                    continue

                if not partido_id:
                    continue  # candidatura sem partido válido

                db.add(
                    Candidatura(
                        eleicao_id=eleicao.id,
                        pessoa_id=pessoa_id,
                        cargo=cargo,
                        partido_id=partido_id,
                        estado_id=estado_id,
                        numero_urna=nr_urna,
                        status_registro=status,
                        eh_titular=cargo not in ("vice_presidente", "vice_governador", "1_suplente_senador", "2_suplente_senador"),
                    )
                )
                stats["candidaturas_criadas"] += 1
                batch_size += 1

                if batch_size >= 200:
                    db.commit()
                    batch_size = 0

            except Exception as e:
                logger.warning(f"  linha {stats['total_linhas']}: {e}")
                stats["erros"] += 1

        db.commit()

    return stats


# ===== Entry point =====

def ingerir_consulta_cand(
    ano: int,
    uf: str,
    db: Session | None = None,
    apenas_principais: bool = True,
) -> dict:
    """Ingere candidaturas de uma UF e ano específicos."""
    own_session = db is None
    if own_session:
        db = SessionLocal()

    inicio = time.time()
    sumario = {"ano": ano, "uf": uf.upper(), "duracao_segundos": 0}

    try:
        # Verifica eleição
        eleicao = (
            db.query(Eleicao)
            .filter(Eleicao.ano == ano, Eleicao.turno == 1)
            .first()
        )
        if not eleicao:
            raise ValueError(f"Eleição {ano}/1 não encontrada — rode seed principal")

        # Estados/partidos
        estados_por_sigla = {e.sigla: e.id for e in db.query(Estado).all()}
        partidos_por_sigla = {p.sigla.upper(): p.id for p in db.query(Partido).all()}

        if uf.upper() not in estados_por_sigla:
            raise ValueError(f"UF '{uf}' não encontrada no banco")

        # Download
        url = url_consulta_cand(ano)
        zip_path = CACHE_DIR / f"consulta_cand_{ano}.zip"
        baixar_zip(url, zip_path)

        # Processa
        stats = processar_consulta_cand(
            db, zip_path, ano, uf.upper(), eleicao, estados_por_sigla, partidos_por_sigla,
            apenas_principais=apenas_principais,
        )
        sumario.update(stats)
        sumario["duracao_segundos"] = round(time.time() - inicio, 1)

        logger.info(
            f"Concluido: {stats['candidaturas_criadas']} candidaturas, "
            f"{stats['pessoas_criadas']} pessoas, {stats['erros']} erros em {sumario['duracao_segundos']}s"
        )
        return sumario

    finally:
        if own_session:
            db.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ingestão TSE Dados Abertos")
    parser.add_argument("--ano", type=int, required=True, help="Ano da eleição (2018, 2022, 2024, 2026)")
    parser.add_argument("--uf", type=str, required=True, help="Sigla da UF (BA, SP, ...) ou BR para todas")
    parser.add_argument("--todos-cargos", action="store_true", help="Inclui Estadual/Vereador/Prefeito (padrão: só principais)")
    args = parser.parse_args()

    if args.uf.upper() == "BR":
        # Todos os estados
        from app.database import SessionLocal
        db = SessionLocal()
        ufs = [e.sigla for e in db.query(Estado).all()]
        db.close()
        for uf in ufs:
            try:
                s = ingerir_consulta_cand(args.ano, uf, apenas_principais=not args.todos_cargos)
                print(f"  {uf}: {s.get('candidaturas_criadas', 0)} cand, {s.get('pessoas_criadas', 0)} pessoas")
            except Exception as e:
                print(f"  {uf}: ERRO {e}")
    else:
        s = ingerir_consulta_cand(args.ano, args.uf, apenas_principais=not args.todos_cargos)
        print("\n=== SUMARIO ===")
        for k, v in s.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
