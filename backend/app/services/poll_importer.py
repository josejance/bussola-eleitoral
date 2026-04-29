"""Importador de pesquisas em formato JSON (Quaest e variações).

Suporta múltiplos formatos:
- Quaest v1 (estadual com `pesquisa.identificacao` rico)
- Quaest v2 (nacional com instituicoes lista, registro string, sem local)
- Quaest v3 (sem chave 'pesquisa' raiz, formato compacto JAN26+)
- Pesquisas temáticas (sem registro eleitoral, com questoes_N)

Detecta automaticamente eleitoral vs temática e roteia para o destino correto.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    AvaliacaoGoverno,
    Eleicao,
    Estado,
    InstitutoPesquisa,
    IntencaoVoto,
    Partido,
    Pesquisa,
    Pessoa,
)
from app.models.opiniao import (
    PesquisaTematica,
    PesquisaTematicaDadosBrutos,
    PesquisaTematicaQuestao,
)
from app.models.poll import PesquisaDadosBrutos
from app.services.poll_normalizer import (
    detectar_nacional_por_titulo,
    detectar_tema,
    detectar_tipo_pesquisa,
    extrair_amostra,
    extrair_contratante,
    extrair_margem,
    extrair_metodologia,
    extrair_nivel_confianca,
    extrair_periodo,
    extrair_registro_tse,
    get_root,
    normalizar_local,
)

logger = logging.getLogger("poll_importer")


# ===== Helpers DB =====

def _find_estado(db: Session, sigla: str | None) -> Estado | None:
    if not sigla:
        return None
    return db.query(Estado).filter(Estado.sigla == sigla.upper()).first()


def _find_or_create_instituto(db: Session, nome: str) -> InstitutoPesquisa:
    nome = nome.strip()
    if not nome:
        nome = "Desconhecido"
    inst = db.query(InstitutoPesquisa).filter(InstitutoPesquisa.nome.ilike(nome)).first()
    if inst:
        return inst
    inst = InstitutoPesquisa(nome=nome, confiabilidade_score=4)
    db.add(inst)
    db.flush()
    return inst


def _find_pessoa(db: Session, nome: str) -> Pessoa | None:
    if not nome:
        return None
    p = db.query(Pessoa).filter(Pessoa.nome_completo == nome).first()
    if p:
        return p
    p = db.query(Pessoa).filter(Pessoa.nome_urna == nome).first()
    if p:
        return p
    return db.query(Pessoa).filter(Pessoa.nome_completo.ilike(f"%{nome}%")).first()


def _find_partido(db: Session, sigla: str | None) -> Partido | None:
    if not sigla:
        return None
    return db.query(Partido).filter(Partido.sigla == sigla.upper()).first()


# ===== Detector de formato (mantido para compatibilidade) =====

def detectar_formato(data: dict) -> str:
    """Detecta formato. Sempre retorna 'quaest_universal' agora — o detector real
    é detectar_tipo_pesquisa() em poll_normalizer.
    """
    if not isinstance(data, dict):
        return "desconhecido"
    root = get_root(data)
    if not isinstance(root, dict):
        return "desconhecido"
    if "identificacao" in root:
        return "quaest_universal"
    return "desconhecido"


# ===== Importador principal =====

def importar_json(
    db: Session,
    data: dict,
    usuario_id: str | None = None,
    arquivo_origem: str | None = None,
) -> dict:
    """Detecta tipo, normaliza e roteia."""
    if not isinstance(data, dict):
        raise ValueError("JSON deve ser um objeto raiz")

    root = get_root(data)
    if not isinstance(root, dict):
        raise ValueError("JSON sem estrutura reconhecível")

    # Fallback: se não tem identificacao mas tem resultados, tenta inferir do nome do arquivo
    if "identificacao" not in root:
        if "resultados" not in root:
            raise ValueError("JSON sem 'identificacao' nem 'resultados' — formato desconhecido")
        # Cria identificação inferida do arquivo
        root = dict(root)
        root["identificacao"] = _inferir_identificacao(arquivo_origem or "", root.get("resultados", {}))

    tipo = detectar_tipo_pesquisa(root)

    if tipo == "tematica":
        return importar_tematica(db, data, root, usuario_id=usuario_id, arquivo_origem=arquivo_origem)
    elif tipo == "eleitoral_nacional":
        return importar_eleitoral(db, data, root, abrangencia="nacional", usuario_id=usuario_id, arquivo_origem=arquivo_origem)
    elif tipo == "eleitoral_estadual":
        return importar_eleitoral(db, data, root, abrangencia="estadual", usuario_id=usuario_id, arquivo_origem=arquivo_origem)
    else:
        raise ValueError(f"Tipo de pesquisa não suportado: {tipo}")


# ===== Importador eleitoral (estadual e nacional) =====

def importar_eleitoral(
    db: Session,
    data: dict,
    root: dict,
    abrangencia: str,
    usuario_id: str | None = None,
    arquivo_origem: str | None = None,
) -> dict:
    """Importa pesquisa eleitoral. Para estadual, exige UF detectado. Para nacional, estado_id=None."""
    ident = root["identificacao"]
    spec = root.get("especificacoes_tecnicas", {})
    resultados = root.get("resultados", {})

    msgs: list[str] = []

    # Estado (apenas se estadual)
    estado = None
    if abrangencia == "estadual":
        _, sigla = normalizar_local(ident.get("local"))
        if not sigla:
            raise ValueError(f"Local '{ident.get('local')}' não mapeável para UF")
        estado = _find_estado(db, sigla)
        if not estado:
            raise ValueError(f"Estado '{sigla}' não cadastrado no banco")

    # Instituto
    contratante, executora = extrair_contratante(ident.get("instituicoes"))
    instituto = _find_or_create_instituto(db, executora or "Desconhecido")

    # Eleição
    eleicao = db.query(Eleicao).filter(Eleicao.ano == 2026, Eleicao.turno == 1).first()
    if not eleicao:
        raise ValueError("Eleição 2026/1 não encontrada — rode seed principal")

    # Registro TSE
    registro = extrair_registro_tse(ident.get("registro_eleitoral"))

    # Idempotência: se registro existe, retorna existente
    if registro:
        existing = db.query(Pesquisa).filter(Pesquisa.registro_tse == registro).first()
        if existing:
            return {
                "status": "ja_existente",
                "tipo": f"eleitoral_{abrangencia}",
                "pesquisa_id": existing.id,
                "mensagens": [f"Pesquisa com registro {registro} já existe"],
                "estatisticas": {},
            }

    # Datas
    inicio, fim = extrair_periodo(ident.get("periodo"), spec)

    # Amostra & margem
    amostra_raw = spec.get("amostra") or spec.get("entrevistas")
    amostra = extrair_amostra(amostra_raw)
    margem = extrair_margem(spec.get("margem_erro") or spec.get("margem_erro_maxima") or spec.get("margem_erro_percentual"))
    nivel = extrair_nivel_confianca(spec.get("nivel_confianca"))

    # Metodologia
    metodologia = extrair_metodologia(spec.get("metodo_coleta") or spec.get("metodologia"))

    pesquisa = Pesquisa(
        instituto_id=instituto.id,
        eleicao_id=eleicao.id,
        estado_id=estado.id if estado else None,
        registro_tse=registro,
        abrangencia=abrangencia,
        data_inicio_campo=inicio,
        data_fim_campo=fim,
        amostra=amostra,
        margem_erro=margem,
        nivel_confianca=nivel,
        metodologia=metodologia,
        contratante=contratante,
        tipo_cenario="estimulado",
        turno_referencia=1,
        origem_dado="insercao_manual",
        status_revisao="aprovada",
        observacao=f"Importada via JSON em {datetime.utcnow().isoformat()}"
        + (f" (arquivo: {arquivo_origem})" if arquivo_origem else ""),
    )
    db.add(pesquisa)
    db.flush()
    msgs.append(f"Pesquisa criada (id={pesquisa.id})")

    estats = {"avaliacoes": 0, "intencoes": 0, "pessoas_vinculadas": 0}

    # Extração de resultados — tenta múltiplos formatos
    extrair_avaliacoes(db, pesquisa, resultados, estats, abrangencia)
    extrair_intencoes(db, pesquisa, resultados, estats)

    # Salva JSON bruto
    db.add(
        PesquisaDadosBrutos(
            pesquisa_id=pesquisa.id,
            formato_origem=f"quaest_{abrangencia}",
            dados_json=json.dumps(data, ensure_ascii=False),
            importado_por=usuario_id,
            importado_em=datetime.utcnow(),
        )
    )
    db.commit()

    msgs.append(
        f"{estats['avaliacoes']} avaliações, {estats['intencoes']} intenções, "
        f"{estats['pessoas_vinculadas']} pessoas vinculadas"
    )

    return {
        "status": "criada",
        "tipo": f"eleitoral_{abrangencia}",
        "pesquisa_id": pesquisa.id,
        "estado_sigla": estado.sigla if estado else None,
        "instituto_nome": instituto.nome,
        "estatisticas": estats,
        "mensagens": msgs,
    }


def extrair_avaliacoes(db: Session, pesquisa: Pesquisa, resultados: Any, estats: dict, abrangencia: str):
    """Extrai aprovação/avaliação de governo de múltiplos formatos.

    Formatos suportados:
    - resultados.aprovacao_governo_<NOME>: dict com dados_gerais
    - resultados.questao_N: dict com titulo "Aprovação..." e dados_gerais
    """
    if not isinstance(resultados, dict):
        return

    for key, val in resultados.items():
        if not isinstance(val, dict):
            continue

        is_aprovacao = key.startswith("aprovacao_governo")
        is_avaliacao = key.startswith("avaliacao_governo")
        is_questao = key.startswith("questao_")

        # Heurística: se questao_N tem "aprovação" no título, é aprovação
        titulo_q = (val.get("titulo") or val.get("enunciado") or "").lower()
        if is_questao:
            if "aprov" in titulo_q and "governo" in titulo_q:
                is_aprovacao = True
            elif "avalia" in titulo_q and "governo" in titulo_q:
                is_avaliacao = True

        if not (is_aprovacao or is_avaliacao):
            continue

        dados = val.get("dados_gerais", [])
        if not isinstance(dados, list) or not dados:
            continue

        ultimo = dados[-1] if isinstance(dados[-1], dict) else None
        if not ultimo:
            continue

        # Identifica pessoa avaliada
        nome_alvo = _extrair_nome_questao(val.get("questao") or val.get("enunciado") or titulo_q or key)
        pessoa = _find_pessoa(db, nome_alvo) if nome_alvo else None

        nivel = "presidencial" if abrangencia == "nacional" else "estadual"

        kwargs = {
            "pesquisa_id": pesquisa.id,
            "nivel": nivel,
            "pessoa_avaliada_id": pessoa.id if pessoa else None,
            "cargo_avaliado": "presidente" if abrangencia == "nacional" else "governador",
            "nao_sabe": _f(ultimo.get("ns_nr") or ultimo.get("ns") or ultimo.get("nao_sabe")),
        }
        if is_aprovacao:
            kwargs.update({
                "aprova": _f(ultimo.get("aprova") or ultimo.get("aprovacao")),
                "desaprova": _f(ultimo.get("desaprova") or ultimo.get("desaprovacao")),
            })
        if is_avaliacao:
            kwargs.update({
                "otimo_bom": _f(ultimo.get("positivo") or ultimo.get("otimo_bom") or ultimo.get("bom")),
                "regular": _f(ultimo.get("regular")),
                "ruim_pessimo": _f(ultimo.get("negativo") or ultimo.get("ruim_pessimo") or ultimo.get("ruim")),
            })

        db.add(AvaliacaoGoverno(**kwargs))
        estats["avaliacoes"] += 1
        if pessoa:
            estats["pessoas_vinculadas"] += 1


def extrair_intencoes(db: Session, pesquisa: Pesquisa, resultados: Any, estats: dict):
    """Extrai intenções de voto de múltiplos formatos.

    Formatos suportados:
    - resultados.intencao_voto_governador / _presidente: dict com cenarios.candidatos
    - resultados.questao_N (com 'intenção de voto' no título): dados_gerais.cenarioX.candidatos
    """
    if not isinstance(resultados, dict):
        return

    for key, val in resultados.items():
        if not isinstance(val, dict):
            continue

        is_intencao = "intencao_voto" in key
        if key.startswith("questao_"):
            t = (val.get("titulo") or val.get("enunciado") or "").lower()
            if "intenç" in t and "voto" in t:
                is_intencao = True

        if not is_intencao:
            continue

        # Achata cenários
        cenarios_raw = val.get("cenarios") or val.get("dados_gerais")
        if isinstance(cenarios_raw, dict):
            # dict como {Cenário 1: {...}, Cenário 2: {...}}
            cenarios = list(cenarios_raw.values())
        elif isinstance(cenarios_raw, list):
            # Pode ser [{...}, ...] de cenários OU [{nome, percentual}, ...] direto
            if cenarios_raw and isinstance(cenarios_raw[0], dict) and "candidatos" in cenarios_raw[0]:
                cenarios = cenarios_raw
            else:
                cenarios = [{"candidatos": cenarios_raw}]
        else:
            continue

        for cenario in cenarios:
            if not isinstance(cenario, dict):
                continue
            candidatos = cenario.get("candidatos") or cenario.get("resultados") or []
            if not isinstance(candidatos, list):
                continue
            for posicao, c in enumerate(candidatos, start=1):
                if not isinstance(c, dict):
                    continue
                nome = c.get("nome") or c.get("candidato") or c.get("opcao")
                pct = _f(c.get("percentual") or c.get("pct") or c.get("intencao") or c.get("valor"))
                if not nome or pct is None:
                    continue
                pessoa = _find_pessoa(db, nome)
                partido = _find_partido(db, c.get("partido"))
                db.add(
                    IntencaoVoto(
                        pesquisa_id=pesquisa.id,
                        pessoa_id=pessoa.id if pessoa else None,
                        partido_referencia_id=partido.id if partido else None,
                        nome_referencia=str(nome)[:150],
                        percentual=pct,
                        posicao_no_cenario=posicao,
                    )
                )
                estats["intencoes"] += 1


def _f(v: Any) -> float | None:
    """Converte para float seguro, ignorando lixo."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.replace(",", ".").strip().rstrip("%").strip()
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _extrair_nome_questao(questao: str) -> str | None:
    """Extrai nome próprio de uma questão de aprovação."""
    import re
    if not questao:
        return None
    # Padrão "que X Y está fazendo" ou "X Y está fazendo"
    m = re.search(r"que\s+([A-ZÁ-Ú][a-zá-ú]+(?:\s+[A-ZÁ-Ú][a-zá-ú]+)+)", questao)
    if m:
        return m.group(1)
    m = re.search(r"presidente\s+([A-ZÁ-Ú][a-zá-ú]+(?:\s+[A-ZÁ-Ú][a-zá-ú]+)*)", questao)
    if m:
        return m.group(1)
    m = re.search(r"opinião,?\s+([A-ZÁ-Ú][a-zá-ú]+(?:\s+[A-ZÁ-Ú][a-zá-ú]+)+)\s+está", questao)
    if m:
        return m.group(1)
    # Busca por nomes-chave conhecidos
    NOMES_CONHECIDOS = ["Lula", "Jerônimo Rodrigues", "Bolsonaro", "Tarcísio", "Pacheco", "Haddad"]
    for n in NOMES_CONHECIDOS:
        if n in questao:
            return n
    return None


# ===== Importador temática =====

def importar_tematica(
    db: Session,
    data: dict,
    root: dict,
    usuario_id: str | None = None,
    arquivo_origem: str | None = None,
) -> dict:
    """Importa pesquisa de opinião sobre tema (não-eleitoral)."""
    ident = root["identificacao"]
    spec = root.get("especificacoes_tecnicas", {})
    resultados = root.get("resultados", {})

    msgs: list[str] = []

    contratante, executora = extrair_contratante(ident.get("instituicoes"))
    instituto = _find_or_create_instituto(db, executora or "Quaest")

    # Local
    abrang, sigla = normalizar_local(ident.get("local"))
    estado = _find_estado(db, sigla) if sigla else None

    # Tema (heurístico)
    tema = detectar_tema(root, arquivo_origem or "")

    inicio, fim = extrair_periodo(ident.get("periodo"), spec)

    amostra = extrair_amostra(spec.get("amostra") or spec.get("entrevistas"))
    margem = extrair_margem(spec.get("margem_erro") or spec.get("margem_erro_maxima") or spec.get("margem_erro_percentual"))
    nivel = extrair_nivel_confianca(spec.get("nivel_confianca"))
    metodologia = extrair_metodologia(spec.get("metodo_coleta") or spec.get("metodologia"))

    titulo = ident.get("titulo") or "Pesquisa Temática"
    subtitulo = ident.get("subtitulo")

    # Idempotência: por título + data fim
    if fim:
        existing = (
            db.query(PesquisaTematica)
            .filter(
                PesquisaTematica.titulo == titulo,
                PesquisaTematica.data_fim_campo == fim,
                PesquisaTematica.tema == tema,
            )
            .first()
        )
        if existing:
            return {
                "status": "ja_existente",
                "tipo": "tematica",
                "pesquisa_id": existing.id,
                "mensagens": [f"Pesquisa temática '{titulo}' ({tema}) já existente"],
                "estatisticas": {},
            }

    pesquisa = PesquisaTematica(
        instituto_id=instituto.id,
        titulo=titulo[:300],
        subtitulo=subtitulo[:300] if subtitulo else None,
        tema=tema,
        abrangencia=abrang if abrang in ("nacional", "estadual") else "nacional",
        estado_id=estado.id if estado else None,
        data_inicio_campo=inicio,
        data_fim_campo=fim,
        amostra=amostra,
        margem_erro=margem,
        nivel_confianca=nivel,
        metodologia=metodologia,
        contratante=contratante,
        registro_eleitoral=extrair_registro_tse(ident.get("registro_eleitoral")),
        publico_alvo=spec.get("publico_alvo"),
        observacao=f"Importada via JSON em {datetime.utcnow().isoformat()}"
        + (f" (arquivo: {arquivo_origem})" if arquivo_origem else ""),
    )
    db.add(pesquisa)
    db.flush()
    msgs.append(f"Pesquisa temática criada (tema={tema}, id={pesquisa.id})")

    # Extrai questões
    n_questoes = 0
    if isinstance(resultados, dict):
        for key, val in resultados.items():
            if not isinstance(val, dict):
                continue
            numero_match = None
            if key.startswith("questao_"):
                try:
                    numero_match = int(key.split("_")[1])
                except (ValueError, IndexError):
                    pass

            titulo_q = val.get("titulo") or val.get("enunciado") or key
            enunciado = val.get("enunciado") or val.get("questao")
            dados_gerais = val.get("dados_gerais")
            cruzamentos = val.get("cruzamentos")

            db.add(
                PesquisaTematicaQuestao(
                    pesquisa_id=pesquisa.id,
                    numero=numero_match or (n_questoes + 1),
                    titulo_questao=str(titulo_q)[:500] if titulo_q else None,
                    enunciado=str(enunciado) if enunciado else None,
                    tipo_resposta="multipla_escolha",
                    dados_gerais_json=json.dumps(dados_gerais, ensure_ascii=False) if dados_gerais else None,
                    cruzamentos_json=json.dumps(cruzamentos, ensure_ascii=False) if cruzamentos else None,
                )
            )
            n_questoes += 1

    msgs.append(f"{n_questoes} questões extraídas")

    db.add(
        PesquisaTematicaDadosBrutos(
            pesquisa_id=pesquisa.id,
            formato_origem="quaest_tematica",
            dados_json=json.dumps(data, ensure_ascii=False),
            arquivo_origem=arquivo_origem,
            importado_por=usuario_id,
            importado_em=datetime.utcnow(),
        )
    )
    db.commit()

    return {
        "status": "criada",
        "tipo": "tematica",
        "pesquisa_id": pesquisa.id,
        "tema": tema,
        "instituto_nome": instituto.nome,
        "estatisticas": {"questoes": n_questoes},
        "mensagens": msgs,
    }


def _inferir_identificacao(fname: str, resultados: dict) -> dict:
    """Infere identificação básica do nome do arquivo + chaves de resultados.

    Para JSONs como MINAS_ABR26 que só têm 'resultados' sem metadados.
    """
    fname_upper = fname.upper()

    # Mapeamento UF do nome do arquivo
    LOCAL_PREFIXES = {
        "BAHIA": "Bahia", "MINAS": "Minas Gerais", "PARANA": "Paraná",
        "PERNAMBUCO": "Pernambuco", "RIO": "Rio de Janeiro", "SAO_PAULO": "São Paulo",
        "SP": "São Paulo", "BA": "Bahia", "MG": "Minas Gerais", "PR": "Paraná",
        "PE": "Pernambuco", "RJ": "Rio de Janeiro",
    }
    local_inferido = None
    for prefix, nome in LOCAL_PREFIXES.items():
        if fname_upper.startswith(prefix + "_") or fname_upper.startswith(prefix + "-"):
            local_inferido = nome
            break

    # Se tem palavra "Romeu Zema" ou nome de governador na chave, MG
    if not local_inferido and isinstance(resultados, dict):
        keys_str = " ".join(resultados.keys()).lower()
        if "zema" in keys_str:
            local_inferido = "Minas Gerais"

    # Tenta extrair mês/ano do nome
    import re as _re
    m = _re.search(r"([A-Z]{3})(\d{2})", fname_upper)
    periodo = None
    if m:
        mes_abrev, ano_2d = m.group(1), m.group(2)
        periodo = f"{mes_abrev}/20{ano_2d}"

    return {
        "titulo": f"Pesquisa importada de {fname}" if fname else "Pesquisa importada",
        "subtitulo": "Identificação inferida do arquivo (metadados ausentes no JSON original)",
        "local": local_inferido or "Brasil",
        "periodo": periodo,
        "instituicoes": "Quaest",
        "registro_eleitoral": None,
    }


# ===== Aliases mantidos para compatibilidade =====

def importar_quaest_v1(db, data, usuario_id=None):
    """Compat: roteia para importar_json."""
    return importar_json(db, data, usuario_id=usuario_id)
