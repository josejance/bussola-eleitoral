"""Dados do GTE - Grupo de Trabalho Eleitoral - 17/04/2026.

Documento original do Diretório Nacional do PT com cenário 2026 por estado.
Contém: status do PT por UF, pré-candidatos a governo/senado, bancadas
históricas (federal e estadual 2018+2022), e pesquisas Real Time Big Data.

Atualizado em: 2026-04-17 (data do documento original)
"""

# ===========================================================================
# STATUS POR ESTADO — detalhes textuais para cenario_governador/senado
# ===========================================================================

STATUS_DETALHES = {
    "AC": {
        "cenario_governador_detalhe": "Thor Dantas (PSB) tem avançado como alternativa na base do Governo federal. Bloco PT, PCdoB, PV, Podemos, PSB. PDT, PSOL e Rede ainda discutem o apoio.",
        "cenario_senado_detalhe": "Jorge Viana (PT) titular. PSOL/Rede podem compor a coligação majoritária e apresentar um nome para a segunda vaga.",
    },
    "AM": {
        "cenario_governador_detalhe": "Omar Aziz (PSD). Caso Omar Aziz seja eleito para o Governo do Estado, Cheila Moreira (PT) assumirá sua vaga no Senado.",
        "cenario_senado_detalhe": "Eduardo Braga (MDB) e Marcelo Ramos (PT).",
    },
    "AP": {
        "cenario_governador_detalhe": "Clécio Luís (saiu do Solidariedade para o União Brasil).",
        "cenario_senado_detalhe": "Randolfe Rodrigues (PT) reeleição. O ministro Waldez Góes não se desincompatibilizou; o deputado federal Acácio Favacho (MDB) pode assumir a vaga na chapa.",
    },
    "PA": {
        "cenario_governador_detalhe": "Hana Ghassan (MDB), atual vice-governadora. PT indicou o Deputado Estadual Dirceu Ten Caten como candidato a vice. Helder pode tentar usar vaga de vice para tentar ampliar coligação.",
        "cenario_senado_detalhe": "Governador Helder Barbalho (MDB). Provável candidatura do Presidente da Assembleia, Chicão (deixou o MDB e assumiu a presidência do União Brasil). Ministro do Turismo, Celso Sabino (Sem Partido, expulso).",
        "observacao_geral": "Sem as candidaturas do Ex-Senador Paulo Rocha e da Ex-Governadora Ana Júlia ficam reduzidas as chances de ampliar a bancada federal.",
    },
    "RO": {
        "cenario_governador_detalhe": "O ex-deputado federal Expedito Netto se filiou ao PT para ser candidato ao Governo. Fórum de 8 partidos progressistas (PDT, MDB, PSB, PT, PV, PCdoB, PSOL e Rede).",
        "cenario_senado_detalhe": "Confúcio Moura (MDB) e Acir Gurgacz (PDT).",
    },
    "RR": {
        "cenario_governador_detalhe": "Possibilidade de apoiar o Presidente da Assembleia Legislativa, Soldado Sampaio (Republicanos, ex-PT/PCdoB), para o Governo. O atual Governador Antônio Denarium (PP) e seu vice Edilson Damião (Republicanos) podem ser cassados (processo no TSE). O advogado Juscelino Kubitschek Pereira colocou o nome à disposição pelo PT, em caso de eleição suplementar.",
        "cenario_senado_detalhe": "Teresa Surita (MDB), ex-prefeita; Helena Lima (MDB).",
        "observacao_geral": "PT deve priorizar chapas proporcionais para reaver representação no legislativo.",
    },
    "TO": {
        "cenario_governador_detalhe": "Katia Abreu se filiou ao PT e pode ser uma opção para o governo. Professora Dorinha (União), depois da saída de Ronaldo Caiado do União Brasil, aceita construir um palanque para a candidatura do Presidente Lula em Tocantins.",
        "cenario_senado_detalhe": "Irajá Abreu deve assumir uma das vagas ao senado na chapa do vice-governador Laurez Moreira (PSD). Paulo Mourão seria um possível nome para uma candidatura do PT ao Senado.",
    },
    "AL": {
        "cenario_governador_detalhe": "Renan Filho (MDB), atual Ministro dos Transportes. O PT no Estado de Alagoas busca a vaga de vice-governador.",
        "cenario_senado_detalhe": "Base do Governo Federal tem as candidaturas de Renan (MDB) e Arthur Lira (PP). JHC ou sua esposa podem ser alternativa para compor palanque. O deputado Paulão (PT) colocou o nome à disposição para disputar o senado, mas é também alternativa para a chapa de deputado federal.",
    },
    "BA": {
        "cenario_governador_detalhe": "Jerônimo Rodrigues (PT) reeleição.",
        "cenario_senado_detalhe": "Rui Costa (PT) e Jacques Wagner (PT).",
        "observacao_geral": "Ângelo Coronel (PSD) rompeu com o governo estadual; maioria do PSD deve se manter na base do Governo.",
    },
    "CE": {
        "cenario_governador_detalhe": "Elmano de Freitas (PT) reeleição. A vice-governadora Jade Romero se filiou ao PT e será candidata a deputada federal. O ex-chefe da casa civil Chagas Vieira (Ex-PT, se filiou ao PDT) pode ser candidato a vice.",
        "cenario_senado_detalhe": "Eunício Oliveira (MDB), Cid Gomes (PSB), Júnior Mano (PSB).",
    },
    "MA": {
        "cenario_governador_detalhe": "Indefinido. Possíveis: Orleans Brandão (MDB), Eduardo Braide (PSD), Felipe Camarão (PT).",
        "cenario_senado_detalhe": "Há 3 pré-candidaturas dentro da base do governo federal: André Fufuca (PP), Weverton Rocha (PDT), Eliziane Gama (PT).",
    },
    "PB": {
        "cenario_governador_detalhe": "Construção de palanque duplo. Vice-governador Lucas Ribeiro (PP), com apoio formal do PT no Estado. Cícero Lucena (MDB) também concorre.",
        "cenario_senado_detalhe": "João Azevedo (PSB). Nabor Wanderley (Republicanos), prefeito de Patos, pai do presidente da Câmara Hugo Motta. Veneziano Vital do Rêgo (MDB), na chapa de Cícero Lucena.",
    },
    "PE": {
        "cenario_governador_detalhe": "João Campos (PSB). Base do Governo Federal pode ter mais três candidaturas: a governadora Raquel Lyra (PSD), Ivan Moraes (PSOL) e Alfredo Gomes (PDT).",
        "cenario_senado_detalhe": "Humberto Costa (PT) e Marília Arraes (Solidariedade).",
    },
    "PI": {
        "cenario_governador_detalhe": "Rafael Fonteles (PT) reeleição, com Washington Bandeira (PT) como vice.",
        "cenario_senado_detalhe": "Marcelo Castro (MDB) e Júlio César (PSD).",
    },
    "RN": {
        "cenario_governador_detalhe": "Carlos Eduardo Xavier (PT), atual Secretário Estadual da Fazenda. Bloco de 8 partidos: PT, PCdoB, PV, MDB, PDT, CIDADANIA, PSB e REDE. PSOL ainda discute a posição.",
        "cenario_senado_detalhe": "Samanda Alves (PT) e Jean Paul Prates (PDT).",
        "observacao_geral": "No bloco de oposição, há sinais de um possível estremecimento nas relações entre Zenaide Maia (PSD) e Allyson Bezerra (União Brasil).",
    },
    "SE": {
        "cenario_governador_detalhe": "Fábio Mitidieri (PSD).",
        "cenario_senado_detalhe": "Rogério Carvalho (PT) e André Moura (União Brasil).",
    },
    "DF": {
        "cenario_governador_detalhe": "Leandro Grass (PT).",
        "cenario_senado_detalhe": "Erika Kokay (PT) e Leila Barros (PDT).",
    },
    "MT": {
        "cenario_governador_detalhe": "Natasha Slhessarenko (PSD).",
        "cenario_senado_detalhe": "Carlos Fávaro (PSD). Construção de um segundo nome para a chapa: Pedro Taques (PSB), assumiu a presidência do PSB e pode ser uma possibilidade. Carlos Fávaro defende tese de candidatura única.",
    },
    "MS": {
        "cenario_governador_detalhe": "Fábio Trad (PT), com Dona Gilda (PT) como vice.",
        "cenario_senado_detalhe": "Vander Loubet (PT) e Soraya Thronicke (PSB).",
    },
    "GO": {
        "cenario_governador_detalhe": "Luiz Cesar Bueno, ex-deputado estadual; o jornalista Cláudio Curado e o advogado Valério Luiz Filho colocaram o nome a disposição para uma candidatura própria. Marconi Perillo (PSDB) tem dado declarações públicas de que não pretende estar no palanque do Presidente Lula no primeiro turno. Além da Federação (PT/PCdoB/PV), projeta-se o apoio de REDE, PSOL e Cidadania. PDT e PSB seguem em disputa: o primeiro pela proximidade com Caiado, o segundo por divisões internas.",
        "cenario_senado_detalhe": "Alternativas para eventual candidatura PT: Jerônimo Rodrigues (ex-PSB, filiado ao PT), Cíntia Pereira, Ana Rita, Marcos Carvalho (vereador de Anápolis), Ediberto Dias e Reynaldo Pantaleão. Cíntia Dias (PSOL) também colocou o nome à disposição e o PCdoB também pode apresentar um nome.",
    },
    "ES": {
        "cenario_governador_detalhe": "Helder Salomão (PT).",
        "cenario_senado_detalhe": "Fabiano Contarato (PT). Renato Casagrande (PSB), possivelmente atrairá o segundo voto do campo progressista.",
    },
    "MG": {
        "cenario_governador_detalhe": "Pacheco (PSB).",
        "cenario_senado_detalhe": "Marília Campos (PT).",
    },
    "RJ": {
        "cenario_governador_detalhe": "Eduardo Paes (PSD).",
        "cenario_senado_detalhe": "Benedita da Silva (PT).",
    },
    "SP": {
        "cenario_governador_detalhe": "Fernando Haddad (PT).",
        "cenario_senado_detalhe": "Simone Tebet (PSB) e Marina Silva (REDE).",
    },
    "SC": {
        "cenario_governador_detalhe": "Gelson Merísio (PSB), com Angela Albino (PDT) como vice. Bloco PT, PCdoB, PV, PSB, PSOL, Rede e PDT.",
        "cenario_senado_detalhe": "Décio Lima (PT) e Afrânio Boppré (PSOL).",
    },
    "PR": {
        "cenario_governador_detalhe": "Requião Filho (PDT). Construção de uma frente com PT, PV, PCdoB, PDT, PSOL e REDE.",
        "cenario_senado_detalhe": "Gleisi Hoffmann (PT). A segunda vaga está disponível para os partidos do campo progressista. Caso a indicação fique no âmbito da federação, o PV tende a indicar Rafael Rolin, presidente do Diretório Estadual. Caso a Federação não apresente uma candidatura, o PT deve indicar o deputado federal Zeca Dirceu.",
    },
    "RS": {
        "cenario_governador_detalhe": "Juliana Brizola (PDT), com Edegar Pretto (PT) como vice.",
        "cenario_senado_detalhe": "Manuela D'Ávila (PSOL) e Paulo Pimenta (PT).",
    },
}

# ===========================================================================
# CANDIDATURAS — pré-candidatos por estado
# ===========================================================================
# Tupla: (uf, nome_completo, nome_urna, partido_sigla, cargo, eh_titular, observacao)
# cargo: governador, vice_governador, senador, deputado_federal

CANDIDATURAS = [
    # ACRE
    ("AC", "Thor Dantas", "Thor Dantas", "PSB", "governador", True, "Avança como alternativa na base do Governo federal"),
    ("AC", "Jorge Viana", "Jorge Viana", "PT", "senador", True, "Pré-candidatura PT"),
    # AMAZONAS
    ("AM", "Omar Aziz", "Omar Aziz", "PSD", "governador", True, ""),
    ("AM", "Eduardo Braga", "Eduardo Braga", "MDB", "senador", True, ""),
    ("AM", "Marcelo Ramos", "Marcelo Ramos", "PT", "senador", True, ""),
    ("AM", "Cheila Moreira", "Cheila Moreira", "PT", "senador", True, "Assume vaga de Omar Aziz no Senado se ele for eleito Governador"),
    # AMAPÁ
    ("AP", "Clécio Luís", "Clécio Luís", "UNIAO", "governador", True, "Saiu do Solidariedade para o União Brasil"),
    ("AP", "Randolfe Rodrigues", "Randolfe Rodrigues", "PT", "senador", True, "Reeleição"),
    ("AP", "Acácio Favacho", "Acácio Favacho", "MDB", "senador", True, "Pode assumir vaga se Waldez Góes não se desincompatibilizar"),
    # PARÁ
    ("PA", "Hana Ghassan", "Hana Ghassan", "MDB", "governador", True, "Atual vice-governadora"),
    ("PA", "Dirceu Ten Caten", "Dirceu Ten Caten", "PT", "vice_governador", False, "Indicado pelo PT como candidato a vice"),
    ("PA", "Helder Barbalho", "Helder Barbalho", "MDB", "senador", True, "Atual Governador"),
    ("PA", "Chicão", "Chicão", "UNIAO", "senador", True, "Presidente da Assembleia; deixou o MDB e assumiu presidência do União Brasil"),
    ("PA", "Celso Sabino", "Celso Sabino", "UNIAO", "senador", True, "Ministro do Turismo; expulso, sem partido"),
    # RONDÔNIA
    ("RO", "Expedito Netto", "Expedito Netto", "PT", "governador", True, "Ex-deputado federal, filiou-se ao PT"),
    ("RO", "Confúcio Moura", "Confúcio Moura", "MDB", "senador", True, ""),
    ("RO", "Acir Gurgacz", "Acir Gurgacz", "PDT", "senador", True, ""),
    # RORAIMA
    ("RR", "Soldado Sampaio", "Soldado Sampaio", "REPUBLICANOS", "governador", True, "Presidente da Assembleia Legislativa; ex-PT/PCdoB"),
    ("RR", "Juscelino Kubitschek Pereira", "Juscelino K. Pereira", "PT", "governador", True, "Em caso de eleição suplementar"),
    ("RR", "Teresa Surita", "Teresa Surita", "MDB", "senador", True, "Ex-prefeita"),
    ("RR", "Helena Lima", "Helena Lima", "MDB", "senador", True, ""),
    # TOCANTINS
    ("TO", "Katia Abreu", "Katia Abreu", "PT", "governador", True, "Filiou-se ao PT, pode ser opção para o governo"),
    ("TO", "Professora Dorinha", "Profª Dorinha", "UNIAO", "governador", True, "Aceita construir palanque para Lula em Tocantins"),
    ("TO", "Laurez Moreira", "Laurez Moreira", "PSD", "senador", True, "Vice-governador"),
    ("TO", "Irajá Abreu", "Irajá Abreu", "PSD", "senador", True, "Deve assumir uma vaga na chapa de Laurez Moreira"),
    ("TO", "Paulo Mourão", "Paulo Mourão", "PT", "senador", True, "Possível nome do PT"),
    # ALAGOAS
    ("AL", "Renan Filho", "Renan Filho", "MDB", "governador", True, "Atual Ministro dos Transportes"),
    ("AL", "Renan Calheiros", "Renan Calheiros", "MDB", "senador", True, ""),
    ("AL", "Arthur Lira", "Arthur Lira", "PP", "senador", True, ""),
    ("AL", "Paulão", "Paulão", "PT", "senador", True, "Colocou o nome à disposição; alternativa também para Câmara Federal"),
    # BAHIA
    ("BA", "Jerônimo Rodrigues", "Jerônimo Rodrigues", "PT", "governador", True, "Reeleição"),
    ("BA", "Rui Costa", "Rui Costa", "PT", "senador", True, ""),
    ("BA", "Jacques Wagner", "Jacques Wagner", "PT", "senador", True, ""),
    # CEARÁ
    ("CE", "Elmano de Freitas", "Elmano de Freitas", "PT", "governador", True, "Reeleição"),
    ("CE", "Chagas Vieira", "Chagas Vieira", "PDT", "vice_governador", False, "Ex-chefe da casa civil; ex-PT, agora PDT"),
    ("CE", "Eunício Oliveira", "Eunício Oliveira", "MDB", "senador", True, ""),
    ("CE", "Cid Gomes", "Cid Gomes", "PSB", "senador", True, ""),
    ("CE", "Júnior Mano", "Júnior Mano", "PSB", "senador", True, ""),
    # MARANHÃO
    ("MA", "Felipe Camarão", "Felipe Camarão", "PT", "governador", True, "Possível pré-candidatura"),
    ("MA", "Orleans Brandão", "Orleans Brandão", "MDB", "governador", True, ""),
    ("MA", "Eduardo Braide", "Eduardo Braide", "PSD", "governador", True, ""),
    ("MA", "André Fufuca", "André Fufuca", "PP", "senador", True, ""),
    ("MA", "Weverton Rocha", "Weverton Rocha", "PDT", "senador", True, ""),
    ("MA", "Eliziane Gama", "Eliziane Gama", "PT", "senador", True, ""),
    # PARAÍBA
    ("PB", "Lucas Ribeiro", "Lucas Ribeiro", "PP", "governador", True, "Vice-governador, com apoio formal do PT no Estado"),
    ("PB", "Cícero Lucena", "Cícero Lucena", "MDB", "governador", True, ""),
    ("PB", "João Azevedo", "João Azevedo", "PSB", "senador", True, ""),
    ("PB", "Nabor Wanderley", "Nabor Wanderley", "REPUBLICANOS", "senador", True, "Prefeito de Patos, pai do presidente da Câmara Hugo Motta"),
    ("PB", "Veneziano Vital do Rêgo", "Veneziano Vital", "MDB", "senador", True, "Na chapa de Cícero Lucena"),
    # PERNAMBUCO
    ("PE", "João Campos", "João Campos", "PSB", "governador", True, ""),
    ("PE", "Raquel Lyra", "Raquel Lyra", "PSD", "governador", True, "Atual governadora"),
    ("PE", "Ivan Moraes", "Ivan Moraes", "PSOL", "governador", True, ""),
    ("PE", "Alfredo Gomes", "Alfredo Gomes", "PDT", "governador", True, ""),
    ("PE", "Humberto Costa", "Humberto Costa", "PT", "senador", True, ""),
    ("PE", "Marília Arraes", "Marília Arraes", "SOLIDARIEDADE", "senador", True, ""),
    # PIAUÍ
    ("PI", "Rafael Fonteles", "Rafael Fonteles", "PT", "governador", True, "Reeleição"),
    ("PI", "Washington Bandeira", "Washington Bandeira", "PT", "vice_governador", False, ""),
    ("PI", "Marcelo Castro", "Marcelo Castro", "MDB", "senador", True, ""),
    ("PI", "Júlio César", "Júlio César", "PSD", "senador", True, ""),
    # RIO GRANDE DO NORTE
    ("RN", "Carlos Eduardo Xavier", "Carlos Eduardo", "PT", "governador", True, "Atual Secretário Estadual da Fazenda"),
    ("RN", "Samanda Alves", "Samanda Alves", "PT", "senador", True, ""),
    ("RN", "Jean Paul Prates", "Jean Paul Prates", "PDT", "senador", True, ""),
    # SERGIPE
    ("SE", "Fábio Mitidieri", "Fábio Mitidieri", "PSD", "governador", True, ""),
    ("SE", "Rogério Carvalho", "Rogério Carvalho", "PT", "senador", True, ""),
    ("SE", "André Moura", "André Moura", "UNIAO", "senador", True, ""),
    # DISTRITO FEDERAL
    ("DF", "Leandro Grass", "Leandro Grass", "PT", "governador", True, ""),
    ("DF", "Erika Kokay", "Erika Kokay", "PT", "senador", True, ""),
    ("DF", "Leila Barros", "Leila Barros", "PDT", "senador", True, ""),
    # MATO GROSSO
    ("MT", "Natasha Slhessarenko", "Natasha Slhessarenko", "PSD", "governador", True, ""),
    ("MT", "Carlos Fávaro", "Carlos Fávaro", "PSD", "senador", True, ""),
    ("MT", "Pedro Taques", "Pedro Taques", "PSB", "senador", True, "Assumiu presidência do PSB; possibilidade para 2ª vaga"),
    # MATO GROSSO DO SUL
    ("MS", "Fábio Trad", "Fábio Trad", "PT", "governador", True, ""),
    ("MS", "Dona Gilda", "Dona Gilda", "PT", "vice_governador", False, ""),
    ("MS", "Vander Loubet", "Vander Loubet", "PT", "senador", True, ""),
    ("MS", "Soraya Thronicke", "Soraya Thronicke", "PSB", "senador", True, ""),
    # GOIÁS
    ("GO", "Luiz Cesar Bueno", "Luiz Cesar Bueno", "PT", "governador", True, "Ex-deputado estadual"),
    ("GO", "Cláudio Curado", "Cláudio Curado", "PT", "governador", True, "Jornalista; colocou nome à disposição"),
    ("GO", "Valério Luiz Filho", "Valério Luiz Filho", "PT", "governador", True, "Advogado; colocou nome à disposição"),
    ("GO", "Cíntia Dias", "Cíntia Dias", "PSOL", "senador", True, "Colocou o nome à disposição"),
    # ESPÍRITO SANTO
    ("ES", "Helder Salomão", "Helder Salomão", "PT", "governador", True, ""),
    ("ES", "Fabiano Contarato", "Fabiano Contarato", "PT", "senador", True, ""),
    ("ES", "Renato Casagrande", "Renato Casagrande", "PSB", "senador", True, "Possivelmente atrairá o segundo voto do campo progressista"),
    # MINAS GERAIS
    ("MG", "Pacheco", "Rodrigo Pacheco", "PSB", "governador", True, ""),
    ("MG", "Marília Campos", "Marília Campos", "PT", "senador", True, ""),
    # RIO DE JANEIRO
    ("RJ", "Eduardo Paes", "Eduardo Paes", "PSD", "governador", True, ""),
    ("RJ", "Benedita da Silva", "Benedita da Silva", "PT", "senador", True, ""),
    # SÃO PAULO
    ("SP", "Fernando Haddad", "Fernando Haddad", "PT", "governador", True, ""),
    ("SP", "Simone Tebet", "Simone Tebet", "PSB", "senador", True, ""),
    ("SP", "Marina Silva", "Marina Silva", "REDE", "senador", True, ""),
    # SANTA CATARINA
    ("SC", "Gelson Merísio", "Gelson Merísio", "PSB", "governador", True, ""),
    ("SC", "Angela Albino", "Angela Albino", "PDT", "vice_governador", False, ""),
    ("SC", "Décio Lima", "Décio Lima", "PT", "senador", True, ""),
    ("SC", "Afrânio Boppré", "Afrânio Boppré", "PSOL", "senador", True, ""),
    # PARANÁ
    ("PR", "Requião Filho", "Requião Filho", "PDT", "governador", True, ""),
    ("PR", "Gleisi Hoffmann", "Gleisi Hoffmann", "PT", "senador", True, ""),
    ("PR", "Rafael Rolin", "Rafael Rolin", "PV", "senador", True, "Presidente do Diretório Estadual do PV; opção da Federação"),
    ("PR", "Zeca Dirceu", "Zeca Dirceu", "PT", "senador", True, "Indicação do PT caso Federação não apresente candidato"),
    # RIO GRANDE DO SUL
    ("RS", "Juliana Brizola", "Juliana Brizola", "PDT", "governador", True, ""),
    ("RS", "Edegar Pretto", "Edegar Pretto", "PT", "vice_governador", False, ""),
    ("RS", "Manuela D'Ávila", "Manuela D'Ávila", "PSOL", "senador", True, ""),
    ("RS", "Paulo Pimenta", "Paulo Pimenta", "PT", "senador", True, ""),
]

# ===========================================================================
# BANCADAS HISTÓRICAS — votação consolidada do PT por estado, eleição e cargo
# ===========================================================================
# Estrutura: { uf: { ano: { 'federal': {cadeiras, votos, pct}, 'estadual': {...} } } }

BANCADAS = {
    "AC": {
        2018: {"federal": (0, 42313, 10.13), "estadual": (2, 45325, 10.86)},
        2022: {"federal": (0, 20487, 4.72), "estadual": (0, 17971, 4.12)},
    },
    "AM": {
        2018: {"federal": (1, 222879, 12.59), "estadual": (1, 70808, 4.00)},
        2022: {"federal": (0, 114667, 5.08), "estadual": (1, 74473, 3.78)},
    },
    "AP": {
        2018: {"federal": (0, 0, 0.00), "estadual": (0, 0, 0.00)},
        2022: {"federal": (0, 14891, 3.52), "estadual": (1, 8771, 2.06)},
    },
    "PA": {
        2018: {"federal": (2, 392400, 9.92), "estadual": (3, 311237, 7.87)},
        2022: {"federal": (2, 362849, 8.02), "estadual": (4, 359653, 7.92)},
    },
    "RO": {
        2018: {"federal": (0, 18081, 2.31), "estadual": (1, 30696, 3.92)},
        2022: {"federal": (0, 43586, 5.01), "estadual": (1, 36754, 4.25)},
    },
    "RR": {
        2018: {"federal": (0, 2036, 0.75), "estadual": (1, 3628, 1.34)},
        2022: {"federal": (0, 2513, 0.86), "estadual": (0, 5251, 1.78)},
    },
    "TO": {
        2018: {"federal": (1, 44301, 6.19), "estadual": (2, 56705, 7.92)},
        2022: {"federal": (0, 67109, 8.08), "estadual": (0, 41384, 4.96)},
    },
    "AL": {
        2018: {"federal": (1, 72358, 4.95), "estadual": (0, 47330, 3.24)},
        2022: {"federal": (1, 79102, 4.79), "estadual": (1, 72248, 4.35)},
    },
    "BA": {
        2018: {"federal": (8, 1332645, 19.40), "estadual": (10, 1124678, 16.38)},
        2022: {"federal": (7, 1369997, 17.21), "estadual": (9, 1219500, 15.36)},
    },
    "CE": {
        2018: {"federal": (3, 522986, 11.38), "estadual": (4, 392601, 8.54)},
        2022: {"federal": (3, 562457, 11.01), "estadual": (8, 807069, 15.96)},
    },
    "MA": {
        2018: {"federal": (1, 170904, 5.23), "estadual": (1, 136936, 4.19)},
        2022: {"federal": (1, 224298, 6.05), "estadual": (0, 128413, 3.47)},
    },
    "PB": {
        2018: {"federal": (1, 128619, 6.47), "estadual": (0, 74488, 3.74)},
        2022: {"federal": (1, 188850, 8.55), "estadual": (2, 130449, 5.81)},
    },
    "PE": {
        2018: {"federal": (2, 414210, 9.56), "estadual": (3, 246224, 5.68)},
        2022: {"federal": (1, 355602, 7.16), "estadual": (3, 446662, 8.90)},
    },
    "PI": {
        2018: {"federal": (2, 395128, 22.10), "estadual": (5, 335324, 18.76)},
        2022: {"federal": (4, 663394, 33.89), "estadual": (12, 689349, 34.98)},
    },
    "RN": {
        2018: {"federal": (2, 263083, 16.25), "estadual": (2, 126355, 7.81)},
        2022: {"federal": (2, 293953, 15.76), "estadual": (3, 223460, 11.98)},
    },
    "SE": {
        2018: {"federal": (1, 135028, 14.15), "estadual": (2, 85905, 9.01)},
        2022: {"federal": (1, 151444, 12.71), "estadual": (1, 82863, 6.81)},
    },
    "DF": {
        2018: {"federal": (1, 130186, 9.04), "estadual": (2, 90097, 6.26)},
        2022: {"federal": (1, 227891, 14.18), "estadual": (3, 137563, 8.27)},
    },
    "MT": {
        2018: {"federal": (1, 87030, 6.82), "estadual": (2, 82986, 6.50)},
        2022: {"federal": (0, 148701, 8.59), "estadual": (2, 144969, 8.38)},
    },
    "MS": {
        2018: {"federal": (1, 140890, 11.36), "estadual": (2, 119160, 9.61)},
        2022: {"federal": (2, 201961, 14.69), "estadual": (3, 153613, 10.93)},
    },
    "GO": {
        2018: {"federal": (1, 141962, 4.68), "estadual": (2, 149005, 4.91)},
        2022: {"federal": (2, 286944, 8.34), "estadual": (3, 228299, 6.64)},
    },
    "ES": {
        2018: {"federal": (1, 140398, 7.26), "estadual": (1, 84240, 4.36)},
        2022: {"federal": (2, 208654, 10.01), "estadual": (2, 146606, 7.05)},
    },
    "MG": {
        2018: {"federal": (8, 1343933, 13.32), "estadual": (10, 1189187, 11.79)},
        2022: {"federal": (10, 1587693, 14.20), "estadual": (12, 1549610, 13.98)},
    },
    "RJ": {
        2018: {"federal": (1, 275205, 3.56), "estadual": (3, 349202, 4.52)},
        2022: {"federal": (5, 734512, 8.56), "estadual": (7, 743051, 8.74)},
    },
    "SP": {
        2018: {"federal": (8, 2067527, 9.78), "estadual": (10, 1940265, 9.18)},
        2022: {"federal": (11, 2941086, 12.63), "estadual": (18, 3720559, 16.00)},
    },
    "SC": {
        2018: {"federal": (1, 347166, 9.78), "estadual": (4, 326608, 9.20)},
        2022: {"federal": (2, 480911, 12.11), "estadual": (4, 438030, 10.93)},
    },
    "PR": {
        2018: {"federal": (3, 501524, 8.78), "estadual": (4, 413146, 7.24)},
        2022: {"federal": (5, 862421, 14.28), "estadual": (7, 687328, 11.34)},
    },
    "RS": {
        2018: {"federal": (5, 793819, 13.58), "estadual": (8, 834730, 14.28)},
        2022: {"federal": (6, 1040725, 16.92), "estadual": (11, 1102508, 17.91)},
    },
}

# ===========================================================================
# PESQUISAS — Real Time Big Data citadas no documento
# ===========================================================================
# Estrutura: lista de pesquisas com cenários

from datetime import date

PESQUISAS = [
    {
        "uf": "RO",
        "instituto_nome": "Real Time Big Data",
        "data_inicio_campo": date(2025, 12, 9),
        "data_fim_campo": date(2025, 12, 10),
        "data_divulgacao": date(2025, 12, 11),
        "amostra": 800,
        "margem_erro": 3.5,
        "metodologia": "telefonica",
        "contratante": "Não informado",
        "tipo_cenario": "estimulado",
        "turno_referencia": 1,
        "cenarios": [
            {
                "cargo": "governador",
                "candidatos": [
                    ("Ivo Cassol", "PP", 22.0),
                    ("Fernando Máximo", "UNIAO", 22.0),
                    ("Adaílton Fúria", "PSD", 16.0),
                    ("Hildon Chaves", "PSDB", 15.0),
                    ("Confúcio Moura", "MDB", 10.0),
                    ("Sérgio Gonçalves", "UNIAO", 4.0),
                    ("Samuel Costa", "REDE", 4.0),
                ],
            },
            {
                "cargo": "senador",
                "candidatos": [
                    ("Fernando Máximo", "UNIAO", 21.0),
                    ("Coronel Marcos Rocha", "UNIAO", 20.0),
                    ("Marcos Rogério", "PL", 18.0),
                    ("Bruno Bolsonaro Scheid", "PL", 15.0),
                    ("Confúcio Moura", "MDB", 13.0),
                    ("Delegado Rodrigo Camargo", "REPUBLICANOS", 6.0),
                    ("Acir Gurgacz", "PDT", 4.0),
                ],
            },
        ],
    },
    {
        "uf": "RR",
        "instituto_nome": "Real Time Big Data",
        "data_inicio_campo": date(2025, 12, 3),
        "data_fim_campo": date(2025, 12, 4),
        "data_divulgacao": date(2025, 12, 5),
        "amostra": 800,
        "margem_erro": 3.5,
        "metodologia": "telefonica",
        "contratante": "Não informado",
        "tipo_cenario": "estimulado",
        "turno_referencia": 1,
        "cenarios": [
            {
                "cargo": "governador",
                "candidatos": [
                    ("Arthur Henrique", "PL", 33.0),
                    ("Edilson Damião", "REPUBLICANOS", 28.0),
                    ("Soldado Sampaio", "REPUBLICANOS", 11.0),
                    ("Juscelino Kubitschek Pereira", "PT", 6.0),
                    ("Doutor Raposo", "PP", 5.0),
                ],
            },
            {
                "cargo": "senador",
                "candidatos": [
                    ("Teresa Surita", "MDB", 27.0),
                    ("Antônio Denarium", "PP", 24.0),
                    ("Chico Rodrigues", "PSB", 13.0),
                    ("Messias de Jesus", "REPUBLICANOS", 11.0),
                    ("Helio Lopes", "PL", 11.0),
                    ("Nicoletti", "UNIAO", 3.0),
                    ("Rodrigo Cataratas", "PRD", 3.0),
                ],
            },
        ],
    },
    {
        "uf": "TO",
        "instituto_nome": "Real Time Big Data",
        "data_inicio_campo": date(2025, 11, 25),
        "data_fim_campo": date(2025, 11, 25),
        "data_divulgacao": date(2025, 11, 26),
        "amostra": 800,
        "margem_erro": 3.5,
        "metodologia": "telefonica",
        "contratante": "Não informado",
        "tipo_cenario": "estimulado",
        "turno_referencia": 1,
        "cenarios": [
            {
                "cargo": "governador",
                "candidatos": [
                    ("Professora Dorinha", "UNIAO", 33.0),
                    ("Laurez Moreira", "PSD", 24.0),
                    ("Cinthia Ribeiro", "PSDB", 13.0),
                    ("Amélio Cayres", "REPUBLICANOS", 11.0),
                    ("Ataídes Oliveira", "NOVO", 6.0),
                ],
            },
            {
                "cargo": "senador",
                "candidatos": [
                    ("Wanderlei Barbosa", "REPUBLICANOS", 28.0),
                    ("Eduardo Gomes", "PL", 19.0),
                    ("Carlos Gaguim", "UNIAO", 12.0),
                    ("Alexandre Guimarães", "MDB", 12.0),
                    ("Vicentinho Jr.", "PP", 11.0),
                    ("Irajá", "PSD", 11.0),
                ],
            },
        ],
    },
    {
        "uf": "AL",
        "instituto_nome": "Real Time Big Data",
        "data_inicio_campo": date(2025, 11, 21),
        "data_fim_campo": date(2025, 11, 24),
        "data_divulgacao": date(2025, 11, 25),
        "amostra": 800,
        "margem_erro": 3.5,
        "metodologia": "telefonica",
        "contratante": "Não informado",
        "tipo_cenario": "estimulado",
        "turno_referencia": 1,
        "cenarios": [
            {
                "cargo": "governador",
                "candidatos": [
                    ("Renan Filho", "MDB", 48.0),
                    ("JHC", "PL", 45.0),
                ],
            },
            {
                "cargo": "senador",
                "candidatos": [
                    ("Renan Calheiros", "MDB", 26.0),
                    ("Davi Davino", "REPUBLICANOS", 21.0),
                    ("Alfredo Gaspar", "UNIAO", 18.0),
                    ("Arthur Lira", "PP", 13.0),
                    ("Paulão", "PT", 9.0),
                    ("Ítalo Bonja", "PRTB", 1.0),
                ],
            },
        ],
    },
]
