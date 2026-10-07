# Changelog

Todas as alterações notáveis deste projeto são documentadas aqui.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e o projeto segue [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [Não lançado] — 2026-10 (Fonte FRED — juros dos EUA)

### Adicionado
- **Nova fonte opcional `tools/fred.py`**: `FREDDataSource` e `get_fred_series()` para
  T-Bill de 3 meses (`TB3MS`) e Treasuries de 1, 2, 5 e 10 anos (`GS1`, `GS2`, `GS5`,
  `GS10`), via API REST do FRED (`requests`, retry com backoff e cache — mesmo padrão do
  IPEA). Sem nova dependência no `requirements.txt`.
  - Ativada por `FRED_API_KEY` (variável de ambiente ou `.env`). Sem a chave, a ferramenta
    **não é registrada** no `ToolRegistry`, o Planner não a vê e as séries ficam fora do
    manifesto do warehouse — o restante do agente funciona como antes.
  - A chave é removida das mensagens de erro e de log (a API a recebe na query string).
  - Só aceita os 5 códigos mapeados (lista fechada), em maiúsculas ou minúsculas.
- **Indicador derivado `inclinacao_curva_eua`** (`tools/derived.py`): Treasury 10 anos −
  T-Bill 3 meses, em pontos percentuais; painel próprio no gráfico e palavras-chave de
  detecção ("inclinação da curva", "yield curve", "term spread").
- `knowledge/juros_externos.md`: base teórica injetada no prompt de análise.
- Séries FRED no manifesto do warehouse (`fred_tb3ms`, `fred_gs1`, `fred_gs2`, `fred_gs5`,
  `fred_gs10`), apenas quando a chave está configurada.
- Testes: `TestFREDTool`, registro condicional no `ToolRegistry` e `TestInclinacaoCurvaEUA`.

### Alterado
- Prompt do Planner: a curva de juros **brasileira** continua fora do escopo; juros dos EUA
  só são oferecidos quando `get_fred_series` está disponível.

### Corrigido
- **Fallback do nó de análise omitia séries**: quando o LLM falhava (ex: erro 503 do Gemini),
  o texto de contingência incluía só o resumo da primeira série, e a resposta final chegava a
  afirmar que faltavam dados das demais. Agora inclui o resumo de todas.
- **Dados recentes eram tratados como "futuros"**: o prompt de análise agora informa a data de
  hoje ao modelo.
- **Frequência errada na resposta** (ex: série mensal descrita como diária): o resumo
  estatístico passa a trazer a frequência inferida do espaçamento do índice.
- Documentação: versões de LangGraph e FastAPI no README e em `docs/ARQUITETURA.md` estavam
  desatualizadas em relação ao `requirements.txt`; adicionado o arquivo `LICENSE` (MIT, já
  declarada no README).

---

## [0.5.0] — 2026-08 (Data Warehouse Histórico — DuckDB + Parquet)

### Adicionado
- **Novo pacote `src/warehouse/`**: data warehouse histórico incremental.
  - `registry.py` — manifesto único das 9 séries fetcháveis (BCB, IBGE, IPEA,
    Banco Mundial) com `resolve_series_id()` (nome de coluna → series_id).
  - `store.py` — `WarehouseStore`: um Parquet por série (histórico completo,
    upsert com dedup por data) + metadados de atualização em DuckDB
    (`last_refreshed_at`, `last_error`); status agregado via SQL direto sobre
    o Parquet (`count`/`min`/`max` de data), sem carregar tudo em pandas.
  - `pipeline.py` — atualização incremental por fonte: BCB busca só o delta
    desde a última data salva (backfill inicial em blocos de 9 anos para
    séries diárias — Selic/Dólar rejeitam janelas BCB > 10 anos); IBGE/IPEA/
    Banco Mundial reconsultam o disponível (APIs não suportam range
    incremental) e o upsert deduplica. Falha isolada por série.
  - `scripts/refresh_warehouse.py` — CLI para rodar o backfill/refresh fora
    do servidor (`--status-only` para só consultar).
  - `GET /admin/data-status` e `POST /admin/refresh` (`src/api/admin.py`) —
    painel de consistência dos dados e botão de atualização manual no
    frontend (nova seção "Status dos Dados" no rodapé do sidebar).
  - `tools/bcb.py`: `get_bcb_series()` ganhou `end_date` opcional (retrocompatível,
    default = até hoje) — necessário para o backfill em blocos.

### Corrigido
- **[Inconsistência real, reportada pelo usuário em teste manual] Percentil/
  z-score variavam conforme a fase da pergunta**: `stats_node` calculava
  essas métricas sobre a mesma janela que o Planner buscou para EXIBIR no
  gráfico — "IPCA vs. média de 3 anos" e "IPCA vs. histórico" retornavam
  percentis diferentes (8,6% vs. 19,3%) para o mesmo valor atual, porque cada
  pergunta usava uma janela de dados diferente como "histórico". Corrigido:
  quando a coluna corresponde a uma série do warehouse, `stats_node` agora
  combina o histórico completo salvo com a janela ao vivo (o valor mais
  recente buscado sempre prevalece — `latest_value` nunca fica desatualizado)
  antes de calcular médias/z-score/percentil. Validado ao vivo: a mesma
  pergunta em janelas de 3 e 10 anos agora retorna exatamente o mesmo
  percentil (12,3%) e z-score (-0,86), usando as 318 observações completas do
  warehouse em ambos os casos.
- **`Tz-aware datetime.datetime cannot be converted to datetime64 unless
  utc=True`** — a API do IPEADATA retorna algumas datas com timezone
  embutido e outras sem, na mesma série (achado ao rodar o backfill real do
  FBCF). `WarehouseStore` normaliza agora via `pd.to_datetime(idx, utc=True).tz_convert(None)`.

### Validado com dados reais
Backfill completo rodado contra as APIs reais (BCB, IBGE, IPEA, Banco
Mundial): 9/9 séries — Selic (9711 linhas desde 2000), Dólar (6676), IPCA
(318), Desocupação (172), PIB Trimestral (60), IPCA-15 (60), Rendimento PNAD
(60), FBCF (364), Gini (40, corretamente sinalizado 🔴 por 944 dias de
defasagem — bate com a limitação já documentada no README).

---

## [0.4.1] — 2026-08 (Manutenção — Concorrência e Dependências)

### Corrigido
- **Bloqueio do event loop em `/ask` e `/ask-agent`**: `run_agent()` (síncrono, ~30-50s por
  requisição) era chamado direto dentro de handlers `async`, travando o servidor inteiro
  (mesmo com 1 worker) para qualquer outra requisição concorrente. Agora despachado via
  `starlette.concurrency.run_in_threadpool` em `src/api/routes.py` e `src/api/legacy.py`.
- **Vazamento de detalhes internos no erro 500**: `/ask` devolvia `str(exc)` cru no campo
  `detail` da resposta HTTP, podendo expor paths, nomes de variáveis ou fragmentos internos.
  Agora retorna mensagem genérica ao cliente; o detalhe continua logado no servidor
  (`logger.error(..., exc_info=True)`).

### Atualizado
- Dependências principais atualizadas (paradas desde meados de 2024):
  `langgraph` 0.0.57 → 1.2.10, `langchain-google-genai` 1.0.6 → 4.3.2,
  `fastapi` 0.111.0 → 0.141.1, `uvicorn` 0.29.0 → 0.52.1, `pandas` 2.2.2 → 2.3.3
  (mantido em 2.x — pandas 3.0 não foi adotado nesta rodada para não misturar uma
  major breaking change fora de escopo), `matplotlib` 3.9.0 → 3.11.1,
  `pydantic`/`pydantic-settings`, `slowapi` 0.1.9 → 0.1.10, `python-bcb`, `wbgapi`.
  Validado com a suíte completa (76 testes unitários + 10 de integração).
- Removida dependência `langchain` (pacote "guarda-chuva"): nunca foi importada
  diretamente no código — apenas `langchain-core` e `langchain-google-genai` são
  usados — e travava a resolução de `langchain-core` numa major antiga.
- Removido `convert_system_message_to_human=True` de `planner.py`, `analysis.py` e
  `response.py`: parâmetro descontinuado no `langchain-google-genai` atual (Gemini
  já trata mensagens de sistema nativamente); virou um kwarg morto e passou a ser
  silenciosamente ignorado pelas versões recentes da lib.
- Adicionado `.flake8` (inexistente até então): sem config, o `flake8` caía no
  limite padrão de 79 colunas enquanto o projeto usa 100 (padrão do `black`),
  reprovando o job `lint` do CI — que por sua vez bloqueia `unit-tests` e
  `type-check` via `needs: lint` em `.github/workflows/tests.yml`.

### Corrigido (continuação)
- **CORS wildcard + credentials**: `CORS_ORIGINS="*"` combinado com
  `allow_credentials=True` em `src/api/server.py` é uma combinação inválida
  (sinalizada por scanners de segurança). Agora `allow_credentials` é
  automaticamente `False` sempre que a origem configurada for `"*"`, e um
  aviso é logado se isso ocorrer com `APP_ENV=production`.
- **Vazamento de escopo no Auditor**: testes E2E mostraram a análise do LLM
  mencionando "projeções"/"ex-ante" para juros reais, embora o `planner.py`
  declare explicitamente que o agente só tem dados históricos observados (sem
  Boletim Focus). Novo check `_check_scope_leakage` em `src/agente/nodes/
  auditor.py` (Check 6) detecta esses termos na análise e sinaliza para o
  `response_node` recontextualizar a resposta.
- **[CRÍTICO] Duplicação silenciosa de dados em perguntas multi-ferramenta**:
  `AgentState.datasets` (e `intermediate_steps`) usava
  `Annotated[List[Any], operator.add]`. Como TODO nó do grafo faz `return state`
  (o dict inteiro mutado, não só as chaves alteradas), o LangGraph tratava
  qualquer nó que apenas repassasse `datasets` sem modificá-lo — `next_tool_node`,
  `stats_node`, `analysis_node`, `auditor_node`, `plot_node`, `response_node` —
  como uma NOVA contribuição a somar ao reducer, duplicando os DataFrames já
  coletados a cada nó subsequente do pipeline. Efeito visível: qualquer pergunta
  com 2+ ferramentas (comparações, Curva de Phillips, Regra de Taylor e,
  criticamente, os indicadores derivados — juros reais e câmbio real, que
  internamente buscam 2 séries) gerava uma coluna duplicada (ex: "432_2") no
  DataFrame final e um painel repetido no gráfico. Reproduzido isoladamente
  (2 buscas reais → `datasets` chegava a 6 entradas em vez de 2) e corrigido
  removendo o reducer: `datasets`/`intermediate_steps` agora são campos comuns
  (last-write-wins), e `action_node` é o único responsável por reconstruir a
  lista completa a cada chamada. Teste de regressão em
  `tests/integration/test_agent_flow.py::test_multi_tool_query_does_not_duplicate_datasets`.

### Melhorado
- **Gráfico de juros reais (Fisher)**: layout genérico empilhava Selic, IPCA
  mensal e Juros Reais como três séries desconectadas (e, por causa do bug
  acima, às vezes com Selic duplicada). Novo painel especializado
  `_plot_fisher()` em `src/agente/nodes/plot.py`:
  - Painel 1: Selic (nominal) e Juros Reais (real) **sobrepostos** na mesma
    escala — a distância vertical entre as duas linhas é visualmente o efeito
    da inflação, o próprio ponto da Identidade de Fisher.
  - Painel 2: IPCA **acumulado 12 meses** (o insumo real da fórmula) no lugar
    do IPCA mensal (unidade diferente, não é o que entra no cálculo).
  - `compute_juros_reais()` agora expõe `ipca_acum_12m_pct` para viabilizar o
    painel 2.
- Linha de média histórica (`_draw_mean_line`): legenda trocada de posição fixa
  (`loc="upper left"`) para `loc="best"` — evita que a caixa da legenda colida
  visualmente com a própria série quando o valor mais recente está perto do
  topo do painel.

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
