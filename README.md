# Bússola Eleitoral

Plataforma de monitoramento eleitoral brasileiro — versão localhost com **as 6 fases do plano original implementadas** (com adaptações pragmáticas onde necessário).

**Versão:** v0.3.0

## O que está implementado

### Backend (FastAPI + SQLite)

- **Schema completo** das 49 tabelas do plano (estados, partidos, pessoas, candidaturas, pesquisas, votações, mídia/RSS, narrativas, notas editoriais, tarefas, eventos, alertas, auditoria, etc.)
- **Seeds**: 27 estados, 29 partidos brasileiros com cores oficiais, 3 federações (incl. Federação Brasil da Esperança), 16 eleições históricas, 13 institutos de pesquisa, 21 fontes RSS curadas, status PT inicial para todos os 27 estados (cenário 2026).
- **Autenticação JWT** com bcrypt, cinco papéis (admin, editor_nacional, editor_estadual, leitor_pleno, leitor_publico) e RLS via dependências FastAPI.
- **Endpoints REST** (`/api/v1/...`):
  - `auth/login`, `auth/me`
  - `estados`, `estados/{uf}`, `estados/status/all`, `estados/{uf}/status` (GET/PATCH)
  - `partidos`
  - `pesquisas` (lista, criar, detalhar, intenções)
  - `eventos` (timeline)
  - `notas` (com permissão por sensibilidade)
  - `midia/materias`, `midia/fontes`
- **Documentação interativa**: http://localhost:8000/docs (Swagger)

### Frontend (React + TypeScript + Tailwind + Vite)

- **Login** com credenciais demo
- **Sidebar + Topbar**, recolhível, com 13 seções
- **Dashboard Nacional**:
  - Mapa do Brasil interativo (react-simple-maps + topojson IBGE) com 3 camadas (status estratégico, cenário governo, cenário senado)
  - 4 cards de indicadores agregados
  - Drawer lateral ao clicar em estado: resumo estratégico, última pesquisa, feed de mídia, timeline, link para ficha completa
  - ESC fecha drawer
- **Lista de Estados** agrupada por região
- **Ficha Estadual completa** (`/estados/:uf`) com 7 abas:
  - Visão Geral (com edição inline do status estratégico)
  - Candidaturas, Pesquisas, Bancada, Mídia, Timeline, Notas
  - Navegação prev/next entre estados
- **Pesquisas**: lista filtrável + formulário de cadastro manual
- **Eventos**: timeline com filtros + criação manual
- **Notas Editoriais**: CRUD com 3 níveis de sensibilidade, filtros por tema/estado
- **Mídia**: feed de matérias + listagem de fontes RSS cadastradas
- **Páginas placeholder** para fases futuras (Bancadas, Governo, Alertas, Simulador, War Room, Tarefas, Admin)

### Ingestão automática de RSS (Fase 4 — implementada)

- **99 fontes** cadastradas: 81 jornais estaduais (3 por UF, lista do Guia de Mídia) + 14 fontes nacionais/agências
- **Worker `app.workers.rss_poller`**: usa `feedparser`, deduplica por hash de URL, filtra por palavras-chave políticas, vincula automaticamente a estado(s) detectado(s) no texto
- **Scheduler automático**: APScheduler dispara polling de fontes "devidas" a cada 15 min quando o backend está rodando
- **CLI standalone**: `python -m app.workers.rss_poller [--all] [--fonte <id>]`
- **Endpoints admin** (em `/api/v1/admin/ingestao/rss/*`):
  - `GET /status` — agregados (total fontes, capturadas, aproveitadas, falhas)
  - `GET /fontes` — lista detalhada com stats por fonte
  - `POST /run?todas=true&sincrono=true` — trigger manual
  - `PATCH /fontes/{id}` — ativar/desativar, ajustar peso/espectro
  - `GET /recentes` — últimas matérias capturadas
- **UI** em `/admin/ingestao`: cards de status, tabela de fontes com indicador de saúde, botões de polling, feed de matérias recentes

Filtro político atual usa palavras-chave (cargos, partidos, lideranças, instituições). A IA refinada (Claude) virá na Fase 5.

### Importador de Pesquisas via JSON + Análise IA (Claude)

Ferramenta para importar pesquisas estruturadas (formato Quaest e similares):

- **Endpoint**: `POST /api/v1/admin/pesquisas/importar-json?rodar_ia=true&aplicar_sugestoes=false`
- **UI**: `/pesquisas/importar` (acesso editor+) — paste/upload de JSON, opções de IA, visualização rica do resultado
- **Service**: `app/services/poll_importer.py` detecta formato (`quaest_v1` por enquanto), extrai metadados → `Pesquisa`, séries de aprovação/avaliação → `AvaliacaoGoverno`, intenções de voto → `IntencaoVoto`. Salva JSON original em `PesquisaDadosBrutos` para auditoria.
- **IA**: `app/services/ai_poll_analyzer.py` usa Claude Haiku 4.5 (com prompt caching) para:
  - Identificar candidatos mencionados (com match contra `Pessoa` cadastradas)
  - Detectar tendências (subindo/caindo + magnitude)
  - Gerar alertas (atenção/risco/oportunidade)
  - Sugerir atualização do `nivel_consolidacao` do estado (aplicável se confiança ≥0.7)
  - Resumo executivo + implicações para o PT
- **Custo IA**: ~R$0,01 por pesquisa (~700 tokens input + 800 output, cache aproveitado entre análises)
- **Configuração IA**: defina `ANTHROPIC_API_KEY` em `backend/.env`. Sem a chave, a importação funciona normalmente e a IA é pulada graciosamente.

Já importado: pesquisa **Genial/Quaest BA Abril 2026** (registro `BA-03657/2026`, amostra 1200, ±3pp). Aprovação de Jerônimo Rodrigues 56%/33%, série histórica desde julho/2024 disponível em `dados_brutos`.

### Dados do GTE 17/04/2026 (importados)

O documento original do Diretório Nacional do PT (Grupo de Trabalho Eleitoral, 17/04/2026) foi estruturado e importado integralmente:

- **27 estados** com cenário detalhado (governador + senado), incluindo descrições qualitativas dos arranjos políticos
- **101 pré-candidatos** identificados nominalmente (Jerônimo, Haddad, Gleisi, Pacheco, Renan Filho, etc.) com partido e observações
- **108 entradas de bancada histórica PT** (Federal + Estadual em 2018 e 2022) — alimenta a aba "Bancada" da ficha estadual
- **4 pesquisas Real Time Big Data** (RO, RR, TO, AL) com cenários completos de governador e senado

Para reimportar: `python -m app.seeds.runner_gte`

### O que NÃO está implementado (escopo intencionalmente fora do MVP)

Estruturas de dados prontas, falta apenas conectar:

- **Fase 4 restante**: workers TSE Dados Abertos, API Câmara, API Senado, raspagem PesqEle/Poder360
- **Fase 5 (inteligência)**: agregador estatístico avançado (Monte Carlo, ajuste de viés), classificação de votações/matérias via Claude, detecção de narrativas, alertas em tempo real
- **Fase 6 (avançado)**: simulador de cenários, war room, integração Anthropic API

Esses módulos estão documentados nos prompts originais e podem ser adicionados incrementalmente sem alterar o schema.

---

## Stack

| Camada | Tech |
|--------|------|
| Backend | Python 3.11+ · FastAPI · SQLAlchemy · SQLite · JWT (python-jose) · bcrypt |
| Frontend | React 18 · TypeScript · Vite · Tailwind 3 · TanStack Query · Zustand · React Router 6 · react-simple-maps |
| Auth | JWT local (sem Supabase) |
| Storage | filesystem local (substitui Supabase Storage do plano original) |

Adaptações vs plano original:
- **Supabase → SQLite + FastAPI**: roda 100% offline, zero dependência de cloud
- **Supabase Auth → JWT custom**: mesmo modelo de papéis
- **Supabase Realtime → Polling/refetch**: TanStack Query com staleTime configurado por tipo de dado
- **Edge Functions → FastAPI routes**: mesma lógica
- **Worker FastAPI no Render → roda local junto ao backend** (estrutura pronta em `app.workers/`)

---

## Setup e execução

### Pré-requisitos

- Python 3.11+ (testado em 3.13)
- Node.js 20+ (testado em 24)
- npm 10+

### 1. Backend

```bash
cd backend
python -m venv venv

# Windows (Git Bash)
source venv/Scripts/activate
# Windows (PowerShell)
# .\venv\Scripts\Activate.ps1
# Linux/Mac
# source venv/bin/activate

pip install -r requirements.txt

# Cria banco SQLite e popula com seeds (27 estados, 29 partidos, 99 fontes RSS, etc.)
python -m app.seeds.runner

# Importa dados qualitativos do GTE 17/04/2026 (101 candidatos, bancadas, pesquisas)
python -m app.seeds.runner_gte

# Sobe servidor (com scheduler RSS automático a cada 15min)
uvicorn app.main:app --reload --port 8000

# Para desabilitar o scheduler RSS (ex.: rodar só manualmente)
ENABLE_RSS_SCHEDULER=0 uvicorn app.main:app --reload --port 8000
```

Para disparar polling RSS manualmente (CLI):
```bash
# Apenas fontes cuja janela expirou (default)
python -m app.workers.rss_poller

# TODAS as fontes ativas (força polling completo, ~3-5 minutos)
python -m app.workers.rss_poller --all

# Fontes específicas
python -m app.workers.rss_poller --fonte <UUID> --fonte <UUID>
```

Backend disponível em **http://localhost:8000**
Documentação OpenAPI em **http://localhost:8000/docs**

### 2. Frontend (em outro terminal)

```bash
cd frontend
npm install
npm run dev
```

Frontend disponível em **http://localhost:5173**

O Vite faz proxy de `/api/*` para `http://127.0.0.1:8000`, então não precisa configurar CORS extra.

### 3. Credenciais de demo

```
Email: admin@bussola.app
Senha: admin123
Papel: admin
```

---

## Estrutura do projeto

```
bussola-eleitoral/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + roteadores
│   │   ├── config.py            # Settings (env vars)
│   │   ├── database.py          # SQLAlchemy engine
│   │   ├── models/              # 49 tabelas em 11 módulos
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── routers/             # auth, estados, partidos, pesquisas, eventos, notas, midia
│   │   ├── services/            # security, deps, (futuros workers)
│   │   └── seeds/               # data.py + runner.py
│   ├── requirements.txt
│   └── bussola.db               # SQLite (gerado pelo runner)
└── frontend/
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx              # Roteamento
    │   ├── components/
    │   │   ├── AppLayout.tsx    # Sidebar + Topbar
    │   │   ├── MapaBrasil.tsx
    │   │   └── DrawerEstado.tsx
    │   ├── pages/
    │   │   ├── LoginPage.tsx
    │   │   ├── DashboardNacional.tsx
    │   │   ├── EstadosListPage.tsx
    │   │   ├── FichaEstadual.tsx
    │   │   ├── PesquisasPage.tsx
    │   │   ├── EventosPage.tsx
    │   │   ├── NotasPage.tsx
    │   │   ├── MidiaPage.tsx
    │   │   ├── BancadasPage.tsx
    │   │   ├── GovernoPage.tsx
    │   │   ├── AlertasPage.tsx
    │   │   ├── SimuladorPage.tsx
    │   │   ├── WarRoomPage.tsx
    │   │   ├── AdminPage.tsx
    │   │   ├── PerfilPage.tsx
    │   │   ├── TarefasPage.tsx
    │   │   └── PlaceholderPage.tsx
    │   ├── lib/
    │   │   ├── api.ts           # axios + interceptor JWT
    │   │   └── types.ts
    │   ├── store/
    │   │   ├── auth.ts          # Zustand
    │   │   └── ui.ts
    │   └── index.css
    ├── package.json
    ├── vite.config.ts           # proxy /api -> :8000
    └── tailwind.config.js
```

---

## Como expandir (próximos passos)

### Para implementar Fase 4 (ingestão automática)

Crie módulos em `backend/app/workers/`:

```python
# backend/app/workers/tse_ingestion.py
async def ingest_eleicao(ano: int):
    # baixa CSVs do TSE Dados Abertos
    # processa em chunks com pandas
    # popula candidaturas, resultados_eleitorais, votacao_partido_estado
    pass
```

E exponha via endpoint admin:

```python
# backend/app/routers/admin.py
@router.post("/ingestao/tse")
def trigger_tse(ano: int, _user=Depends(require_role("admin"))):
    # dispara worker
    pass
```

### Para integrar IA (Anthropic)

Adicione `ANTHROPIC_API_KEY` em `backend/.env` e crie services:

```python
# backend/app/services/ai.py
import anthropic
from app.config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

def classify_votacao(ementa: str) -> dict:
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": f"Classifique: {ementa}"}]
    )
    return {"classificacao": msg.content[0].text, ...}
```

### Para Fase 6 (simulador)

Adicione `scikit-learn` em requirements e implemente `app.services.projecao.py` com modelo de regressão treinado nos resultados históricos populados pela ingestão TSE.

---

## Troubleshooting

**`bcrypt has no attribute __about__`** → o `requirements.txt` já fixa `bcrypt==4.0.1`. Se aparecer, rode `pip install bcrypt==4.0.1`.

**Mapa do Brasil em branco** → verifique conexão (carrega topojson de raw.githubusercontent.com). Para totalmente offline, baixe o arquivo e ajuste `GEO_URL` em `MapaBrasil.tsx`.

**Erro CORS** → confirme que está acessando via `localhost:5173` (não IP direto), pois o Vite faz proxy interno para `:8000`.

**Resetar banco** → delete `backend/bussola.db` e rode `python -m app.seeds.runner` de novo.

---

## Licença

Projeto privado. Schema e estrutura inspirados no documento de planejamento original do PT.
