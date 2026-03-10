# Changelog

Todas as alterações notáveis deste projeto são documentadas aqui.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e o projeto segue [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [0.4.0] — 2026-03 (Onda 3 — Rigor Científico)

### Adicionado
- `src/tools/derived.py`: cálculo de indicadores derivados via Python puro
  - `compute_juros_reais()` — Identidade de Fisher: `(1+Selic)/(1+IPCA_12m)−1`
  - `compute_cambio_real()` — índice de câmbio real bilateral (base 100, PPP simplificado)
  - `detect_derived_needed()` — detecção por keywords na pergunta (juros reais, câmbio real)
- `src/agente/nodes/stats.py`: nó de contexto histórico (Python puro, sem LLM)
  - Calcula: `mean_1y`, `mean_3y`, `mean_5y`, `mean_full`, `std_full`, `zscore_latest`, `percentile_rank`, `min/max`, `trend_3m`, `lag_days` por coluna
  - Implementa regressão OLS via `np.polyfit` para detecção de tendência 3 meses
  - Chama `derived.py` automaticamente se pergunta menciona indicador derivado
- `src/agente/nodes/auditor.py`: camada de auditoria de consistência macroeconômica (Python puro)
  - 4 checks: freshness (lag_days), outlier z-score ≥2.5, juros reais fora do range histórico BR, Selic×IPCA (Regra de Taylor simplificada)
- `src/agente/state.py`: 5 novos campos: `historical_stats`, `historical_stats_text`, `derived_data`, `audit_flags`, `audit_summary`
- `src/agente/agent.py`: grafo expandido de 6 → 8 nós; novo fluxo: `action → stats → analysis → auditor → plot → response`
- `src/agente/nodes/analysis.py`: `historical_context` injetado nos prompts `_SYSTEM_PROMPT_SINGLE` e `_SYSTEM_PROMPT_MULTI`; `derived_data` integrado no `data_summary`
- `src/agente/nodes/response.py`: `audit_summary` injetado no prompt final quando existem flags de auditoria
- `src/agente/nodes/planner.py`: seção **INDICADORES DERIVADOS** no system prompt com mapeamentos explícitos (ex: "juros reais" → Selic 432 + IPCA 433)
- `src/knowledge/juros_reais.md`: referência teórica completa — Fisher, histórico 1999–2026, Regra de Taylor, policy ranges
- `docs/FUNDAMENTO_CIENTIFICO.md`: documentação científica completa com modelos econométricos, fórmulas e referências bibliográficas de graduação em Ciências Econômicas
- `docs/GUIA_DESENVOLVIMENTO.md`: guia de setup local, testes, como adicionar indicadores/nós, checklist de PR
- `docs/ARQUITETURA.md`: atualizado para Onda 3 (8 nós, tabela de estado completa, seção Onda 3 com stats/auditor/derived)
- `README.md`: reescrito com índice completo, fundamento científico, quickstart atualizado (porta 8002, SQLite padrão), exemplos atualizados

### Corrigido
- **Viés do planner**: agente não retornava mais apenas Selic ou apenas IPCA para perguntas de "juros reais" — agora sempre coleta ambas as séries
- **Alucinação em derivados**: juros reais agora calculados via Python (Fisher), não estimados pelo LLM

---

## [0.3.0] — 2026-01 (Onda 2 — Multi-ferramenta e Frontend)

### Adicionado
- Pipeline multi-ferramenta: `pending_tools` queue + `next_tool_node` loop
- `ToolRegistry` imutável com registro dinâmico
- Cache SQLite de séries com TTL por frequência (`src/tools/cache.py`)
- Retry com backoff exponencial para chamadas às APIs (`src/utils/http.py`)
- Rate limiting por IP (10 req/min via `slowapi`)
- `GET /history` endpoint para histórico de conversas
- `cost_estimate_usd` por resposta (badge na interface)
- `index.html` reescrito: layout 2 painéis (histórico + chat), subplots full-width, lightbox para gráficos, custo acumulado por sessão
- `GET /` serve `index.html` via `FileResponse` (elimina CORS file://)
- boto3 timeout configurado (`connect_timeout=3, max_attempts=1`) — sem travamento quando DynamoDB não está rodando
- DynamoDB GSI `RecentConversationsIndex` para queries por timestamp
- `.env.example` documentado por variável
- Schemas Pydantic: `ConversationItem`, `HistoryResponse`, `cost_estimate_usd` em `QueryResponse`

### Corrigido
- Análise duplicada (dois `analysis_node` no grafo)
- Arquivo `.env` com BOM UTF-8 (parse falhava no Windows)
- `storage.save()` não era chamado após execução do agente
- Colunas sobrepostas em DataFrames de múltiplas ferramentas
- Acumulação incorreta de custo via `cost_tracker`
- `slowapi` não estava instalado — adicionado ao `requirements.txt`

---

## [0.2.0] — 2024 (Evolução C1–C8)

### Adicionado
- `src/agente/config.py`: configuração centralizada via `pydantic-settings`
- `config/*.yaml`: arquivos YAML por ambiente (default, development, production, aws)
- `src/agente/nodes/`: nós LangGraph extraídos para módulos individuais
  - `planner.py`, `action.py`, `analysis.py`, `plot.py`, `response.py`
- `src/tools/base.py`: ABC `DataSource` para contrato unificado de ferramentas
- `src/tools/registry.py`: `ToolRegistry` com registro dinâmico e descrição para LLM
- `src/storage/`: abstração de persistência (SQLite dev / DynamoDB prod)
- `src/logger/config.py`: formatadores JSON e texto com supressão de loggers ruidosos
- `src/api/`: FastAPI modularizado (`server.py`, `routes.py`, `legacy.py`, `schemas.py`)
- `src/asgi.py`: ponto de entrada ASGI para uvicorn
- `pyproject.toml`: metadados do projeto e configuração de ferramentas de qualidade
- `Makefile` + `scripts/run.ps1`: atalhos de desenvolvimento
- `deployment/docker/`: Dockerfile multi-stage, Dockerfile.test, .dockerignore
- `deployment/docker-compose.yml` + `docker-compose.prod.yml`
- `.github/workflows/tests.yml`: CI (lint, mypy, testes unitários + integração, Docker build)
- `.github/workflows/code-quality.yml`: bandit, pip-audit, pre-commit
- `tests/`: conftest, fixtures, test_nodes, test_tools, test_api, integração
- `docs/ARQUITETURA.md`: diagrama completo + descrição dos componentes
- `docs/GUIA_INSTALACAO.md`: passo a passo detalhado de instalação local e Docker
- `CONTRIBUTING.md`: guia de contribuição
- `src/knowledge/`: base teórica para IPCA, Selic, Câmbio, Desocupação, Gini, FBCF

### Modificado
- `requirements.txt`: adicionados `pydantic>=2.7.0`, `pydantic-settings>=2.2.0`, `pyyaml>=6.0.1`
- `.gitignore`: expandido com padrões de `.env`, `output/`, `logs/`, `.venv/`
- `src/main.py`: atualizado para usar `run_agent()` da nova estrutura modular

### Corrigido
- Race condition em gráficos: plots nomeados como `chart_{session_id}.png`
- Inicialização do LLM movida para dentro das funções de nó (testabilidade)
- Importações organizadas via `isort` (PEP 8)

---

## [0.1.0] — 2024 (MVP 0)

### Adicionado
- Pipeline LangGraph simples: Planner → Action → Analysis → Plot → Response
- Integração BCB/SGS (IPCA 433, Selic 432, Câmbio 1, Desocupação 24369)
- Integração IPEADATA (FBCF)
- Integração World Bank (Gini)
- API FastAPI básica (`POST /ask`)
- Interface HTML básica


### Adicionado
- `src/agente/config.py`: configuração centralizada via `pydantic-settings`
- `config/*.yaml`: arquivos YAML por ambiente (default, development, production, aws)
- `src/agente/nodes/`: nós LangGraph extraídos para módulos individuais
  - `planner.py`, `action.py`, `analysis.py`, `plot.py`, `response.py`
- `src/tools/base.py`: ABC `DataSource` para contrato unificado de ferramentas
- `src/tools/registry.py`: `ToolRegistry` com registro dinâmico e descrição para LLM
- `src/storage/`: abstração de persistência (SQLite dev / DynamoDB prod)
- `src/logger/config.py`: formatadores JSON e texto com supressão de loggers ruidosos
- `src/api/`: FastAPI modularizado (`server.py`, `routes.py`, `legacy.py`, `schemas.py`)
- `src/asgi.py`: ponto de entrada ASGI para uvicorn
- `pyproject.toml`: metadados do projeto e configuração de ferramentas de qualidade
- `Makefile` + `scripts/run.ps1`: atalhos de desenvolvimento
- `deployment/docker/`: Dockerfile multi-stage, Dockerfile.test, .dockerignore
- `deployment/docker-compose.yml` + `docker-compose.prod.yml`
- `.github/workflows/tests.yml`: CI (lint, mypy, testes unitários + integração, Docker build)
- `.github/workflows/code-quality.yml`: bandit, pip-audit, pre-commit
- `tests/`: conftest, fixtures, test_nodes, test_tools, test_api, integração
- `docs/ARQUITETURA.md`: diagrama completo + descrição dos componentes
- `docs/GUIA_INSTALACAO.md`: passo a passo detalhado de instalação local e Docker
- `CONTRIBUTING.md`: guia de contribuição

### Modificado
- `requirements.txt`: adicionados `pydantic>=2.7.0`, `pydantic-settings>=2.2.0`, `pyyaml>=6.0.1`
- `.gitignore`: expandido com padrões de `.env`, `output/`, `logs/`, `.venv/`
- `src/main.py`: atualizado para usar `run_agent()` da nova estrutura modular

### Corrigido
- Race condition em gráficos: plots nomeados como `chart_{session_id}.png`
- Inicialização do LLM movida para dentro das funções de nó (testabilidade)
- Importações organizadas via `isort` (PEP 8)

---

## [0.1.0] — 2024 (MVP 0)

### Adicionado
- Agente LangGraph com 5 nós: Planner → Action → Analysis → Plot → Response
- Ferramentas de dados: BCB (SGS), IPEADATA, World Bank
- API FastAPI com endpoint `POST /ask-agent`
- Frontend `index.html` com interface de chat
- CLI básico `src/main.py`
- Configuração via `.env` (Google API Key)
