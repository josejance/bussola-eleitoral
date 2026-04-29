"""Ingestão da API do Senado Federal.

API: https://legis.senado.leg.br/dadosabertos — XML por padrão (alguns
endpoints aceitam JSON via header Accept).

Sincroniza:
- 81 senadores em exercício
- Marca os 27 da renovação 2026 (eleitos em 2018) via campo eleicao_origem_id no Mandato
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime
from typing import Any
from xml.etree import ElementTree as ET

import httpx
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Eleicao,
    Estado,
    EventoTimeline,
    FiliacaoPartidaria,
    Mandato,
    Partido,
    Pessoa,
)

logger = logging.getLogger("senado")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

API_BASE = "https://legis.senado.leg.br/dadosabertos"
USER_AGENT = "BussolaEleitoralBot/0.1 (+localhost; pt-BR)"
TIMEOUT = 30


def _http_client() -> httpx.Client:
    return httpx.Client(
        base_url=API_BASE,
        timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
    )


def listar_senadores(client: httpx.Client) -> list[dict]:
    """Lista senadores em exercício. Tenta JSON primeiro, fallback XML."""
    r = client.get("/senador/lista/atual", headers={"Accept": "application/json"})
    r.raise_for_status()
    try:
        data = r.json()
        # Estrutura: ListaParlamentarEmExercicio.Parlamentares.Parlamentar (lista)
        parlamentares = (
            data.get("ListaParlamentarEmExercicio", {})
            .get("Parlamentares", {})
            .get("Parlamentar", [])
        )
        if isinstance(parlamentares, dict):
            parlamentares = [parlamentares]
        return parlamentares
    except (json.JSONDecodeError, ValueError):
        # Fallback: parseia XML
        root = ET.fromstring(r.text)
        return _parse_senadores_xml(root)


def _parse_senadores_xml(root: ET.Element) -> list[dict]:
    """Converte XML do Senado em lista de dicts."""
    out = []
    for p in root.iter("Parlamentar"):
        d = {}
        ident = p.find("IdentificacaoParlamentar")
        if ident is not None:
            d["IdentificacaoParlamentar"] = {
                child.tag: child.text for child in ident
            }
        mand = p.find("Mandato")
        if mand is not None:
            d["Mandato"] = {child.tag: child.text for child in mand}
        out.append(d)
    return out


def _ano_eleicao(senador: dict) -> int | None:
    """Determina o ano da eleição de origem do mandato atual.

    Senado renova 1/3 ou 2/3. Em 2026, renovam-se os eleitos em 2018.
    Os com mandato 2023-2031 foram eleitos em 2022.
    """
    mandato = senador.get("Mandato", {})
    primeira_legis = mandato.get("PrimeiraLegislaturaDoMandato", {})
    if isinstance(primeira_legis, dict):
        ano_inicio = primeira_legis.get("DataInicio")
        if ano_inicio and len(ano_inicio) >= 4:
            try:
                ano = int(ano_inicio[:4])
                if 2019 <= ano <= 2020:  # mandato 2019-2027 → eleito 2018
                    return 2018
                if 2023 <= ano <= 2024:  # mandato 2023-2031 → eleito 2022
                    return 2022
            except ValueError:
                pass
    # Fallback heurístico: se Bloco/Líder tem informação...
    return None


def sincronizar_senador(
    db: Session,
    senador: dict,
    estados_por_sigla: dict[str, str],
    partidos_por_sigla: dict[str, str],
    eleicoes: dict[int, str],
) -> dict:
    """Cria/atualiza Pessoa + Mandato + Filiação para um senador."""
    stats = {"criada": False, "atualizada": False, "mudou_partido": False}

    ident = senador.get("IdentificacaoParlamentar", {})
    if not ident:
        return stats

    cod = ident.get("CodigoParlamentar")
    nome = ident.get("NomeParlamentar") or ident.get("NomeCompletoParlamentar") or ""
    nome_civil = ident.get("NomeCompletoParlamentar") or nome
    foto = ident.get("UrlFotoParlamentar")
    sigla_partido = (ident.get("SiglaPartidoParlamentar") or "").upper().strip()
    sigla_uf = (ident.get("UfParlamentar") or "").upper().strip()
    email = ident.get("EmailParlamentar")
    sexo = ident.get("SexoParlamentar")

    if not cod or not nome:
        return stats

    # Match pessoa por id_senado em ids_externos
    pessoa = (
        db.query(Pessoa)
        .filter(
            Pessoa.deleted_at.is_(None),
            Pessoa.ids_externos_json.like(f'%"senado": "{cod}"%')
            | Pessoa.ids_externos_json.like(f'%"senado":"{cod}"%')
            | Pessoa.ids_externos_json.like(f'%"senado": {cod}%'),
        )
        .first()
    )
    if not pessoa:
        # Fallback: por nome
        pessoa = (
            db.query(Pessoa)
            .filter(Pessoa.nome_completo == nome_civil, Pessoa.deleted_at.is_(None))
            .first()
        )

    if not pessoa:
        pessoa = Pessoa(
            nome_completo=nome_civil,
            nome_urna=nome,
            foto_url=foto,
            email_publico=email,
            estado_natal_id=estados_por_sigla.get(sigla_uf),
            genero="feminino" if sexo == "Feminino" else "masculino" if sexo == "Masculino" else None,
            biografia=f"Senador{'a' if sexo == 'Feminino' else ''} por {sigla_uf} ({sigla_partido}).",
        )
        ids_ext = {"senado": str(cod)}
        pessoa.ids_externos_json = json.dumps(ids_ext, ensure_ascii=False)
        db.add(pessoa)
        db.flush()
        stats["criada"] = True
    else:
        # Atualiza
        if foto and pessoa.foto_url != foto:
            pessoa.foto_url = foto
        if email and pessoa.email_publico != email:
            pessoa.email_publico = email
        try:
            ids_ext = json.loads(pessoa.ids_externos_json or "{}")
        except json.JSONDecodeError:
            ids_ext = {}
        if str(ids_ext.get("senado", "")) != str(cod):
            ids_ext["senado"] = str(cod)
            pessoa.ids_externos_json = json.dumps(ids_ext, ensure_ascii=False)
        stats["atualizada"] = True

    # Filiação
    partido_id = partidos_por_sigla.get(sigla_partido)
    if partido_id:
        filiacao_ativa = (
            db.query(FiliacaoPartidaria)
            .filter(
                FiliacaoPartidaria.pessoa_id == pessoa.id,
                FiliacaoPartidaria.fim.is_(None),
            )
            .first()
        )
        if not filiacao_ativa:
            db.add(
                FiliacaoPartidaria(
                    pessoa_id=pessoa.id,
                    partido_id=partido_id,
                    inicio=date.today(),
                )
            )
        elif filiacao_ativa.partido_id != partido_id:
            partido_anterior = db.query(Partido).filter(Partido.id == filiacao_ativa.partido_id).first()
            sigla_anterior = partido_anterior.sigla if partido_anterior else "?"
            filiacao_ativa.fim = date.today()
            filiacao_ativa.tipo_saida = "transferencia"
            db.add(
                FiliacaoPartidaria(
                    pessoa_id=pessoa.id,
                    partido_id=partido_id,
                    inicio=date.today(),
                )
            )
            db.add(
                EventoTimeline(
                    pessoa_id=pessoa.id,
                    partido_id=partido_id,
                    estado_id=estados_por_sigla.get(sigla_uf),
                    tipo="filiacao",
                    titulo=f"Senador {nome} mudou de {sigla_anterior} para {sigla_partido}",
                    descricao=f"Detectado pela ingestão da API Senado em {datetime.utcnow().isoformat()}",
                    data_evento=datetime.utcnow(),
                    fonte_descricao="API Senado Federal",
                    automatico=True,
                    origem_automatica="api_senado",
                    relevancia=5,  # mudança no Senado é sempre relevante
                )
            )
            stats["mudou_partido"] = True

    # Mandato
    ano_eleicao = _ano_eleicao(senador)
    eleicao_origem_id = eleicoes.get(ano_eleicao) if ano_eleicao else None

    mandato_atual = (
        db.query(Mandato)
        .filter(
            Mandato.pessoa_id == pessoa.id,
            Mandato.cargo == "senador",
            Mandato.fim >= date.today(),
        )
        .first()
    )
    if not mandato_atual and partido_id and sigla_uf:
        # Determina datas baseadas no ano eleitoral
        if ano_eleicao == 2018:
            inicio = date(2019, 2, 1)
            fim = date(2027, 1, 31)
        elif ano_eleicao == 2022:
            inicio = date(2023, 2, 1)
            fim = date(2031, 1, 31)
        else:
            inicio = date(2023, 2, 1)
            fim = date(2031, 1, 31)
        db.add(
            Mandato(
                pessoa_id=pessoa.id,
                cargo="senador",
                estado_id=estados_por_sigla.get(sigla_uf),
                partido_id_no_mandato=partido_id,
                inicio=inicio,
                fim=fim,
                eh_titular=True,
                eleicao_origem_id=eleicao_origem_id,
            )
        )
    elif mandato_atual and not mandato_atual.eleicao_origem_id and eleicao_origem_id:
        mandato_atual.eleicao_origem_id = eleicao_origem_id

    return stats


def sincronizar_senado(db: Session | None = None) -> dict:
    """Sincroniza todos os senadores em exercício."""
    own_session = db is None
    if own_session:
        db = SessionLocal()

    inicio = time.time()
    sumario = {
        "total_listados": 0,
        "novas": 0,
        "atualizadas": 0,
        "mudancas_partido": 0,
        "erros": 0,
        "ciclo_2026": 0,
        "ciclo_2030": 0,
        "duracao_segundos": 0,
    }

    try:
        estados_por_sigla = {e.sigla: e.id for e in db.query(Estado).all()}
        partidos_por_sigla = {p.sigla.upper(): p.id for p in db.query(Partido).all()}
        # Eleições 2018 e 2022 (turno 1) já estão no seed
        el_2018 = db.query(Eleicao).filter(Eleicao.ano == 2018, Eleicao.turno == 1).first()
        el_2022 = db.query(Eleicao).filter(Eleicao.ano == 2022, Eleicao.turno == 1).first()
        eleicoes = {}
        if el_2018:
            eleicoes[2018] = el_2018.id
        if el_2022:
            eleicoes[2022] = el_2022.id

        with _http_client() as client:
            logger.info("Listando senadores em exercicio...")
            senadores = listar_senadores(client)
            sumario["total_listados"] = len(senadores)
            logger.info(f"  {len(senadores)} senadores encontrados")

            for sen in senadores:
                ano = _ano_eleicao(sen)
                if ano == 2018:
                    sumario["ciclo_2026"] += 1
                elif ano == 2022:
                    sumario["ciclo_2030"] += 1

                try:
                    stats = sincronizar_senador(db, sen, estados_por_sigla, partidos_por_sigla, eleicoes)
                    if stats["criada"]:
                        sumario["novas"] += 1
                    elif stats["atualizada"]:
                        sumario["atualizadas"] += 1
                    if stats["mudou_partido"]:
                        sumario["mudancas_partido"] += 1
                except Exception as e:
                    logger.warning(f"Erro: {e}")
                    sumario["erros"] += 1

            db.commit()

        sumario["duracao_segundos"] = round(time.time() - inicio, 1)
        logger.info(
            f"Concluido em {sumario['duracao_segundos']}s — {sumario['novas']} novos, "
            f"{sumario['atualizadas']} atualizados, ciclo 2026={sumario['ciclo_2026']}, ciclo 2030={sumario['ciclo_2030']}"
        )
        return sumario

    finally:
        if own_session:
            db.close()


def main():
    s = sincronizar_senado()
    print("\n=== SUMARIO ===")
    for k, v in s.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
