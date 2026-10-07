# Arquitetura — Agente de Dados Macroeconômicos Brasileiros

> **Versão:** Onda 3 — 8 nós LangGraph com auditor e contexto histórico  
> **Stack:** Python 3.11+ · LangGraph 1.x · Gemini 2.5 Flash · FastAPI 0.14x · SQLite/DynamoDB · DuckDB/Parquet

## Visão Geral

O projeto é um **agente de IA conversacional** especializado em dados macroeconômicos brasileiros.
Recebe perguntas em linguagem natural, acessa APIs públicas de dados oficiais, realiza análises
estatísticas com fundamento econométrico e retorna respostas textuais enriquecidas com gráficos.

A arquitetura evoluiu em três ondas:

| Versão | Nós | Descrição |
|---|---|---|
| Onda 1 (MVP) | 4 nós | Planner → Action → Analysis → Response |
| Onda 2 | 6 nós | Adicionados Next-Tool loop, multi-ferramenta, Plot, cache, retry |
| **Onda 3** | **8 nós** | **Adicionados Stats (contexto histórico) e Auditor (consistência macro)** |

---

## Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENTE                                  │
│          index.html  /  CLI  /  API REST (POST /ask)            │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP JSON
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI (src/api/)                            │
│   POST /ask  ──►  routes.py  ──►  run_agent()                   │
│   POST /ask-agent (legado) ──►  legacy.py                       │
│   GET  /health                                                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  LangGraph Pipeline (src/agente/)                │
│                                                                  │
│   Planner → Action ⟲ → Stats → Analysis → Auditor → Plot       │
│                                                    └─► Response │
│                                                                  │
│   Nós (src/agente/nodes/):                                       │
│     planner.py   – decide ferramentas e parâmetros (LLM)        │
│     action.py    – executa ferramenta + loop multi-ferramenta   │
│     stats.py     – contexto histórico (Python puro, sem LLM)    │
│     analysis.py  – análise textual com contexto histórico (LLM) │
│     auditor.py   – consistência macroeconômica (Python puro)    │
│     plot.py      – gera gráfico matplotlib                      │
│     response.py  – síntese final com alertas de auditoria (LLM) │
└───────────────────────────┬─────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌─────────────────────┐     ┌─────────────────────────────────┐
│   Data Tools        │     │   Storage Backend               │
│   (src/tools/)      │     │   (src/storage/)                │
│                     │     │                                  │
│ bcb.py   — SGS/BCB  │     │ SQLiteBackend   (dev)           │
│ ipea.py  — IPEADATA │     │ DynamoDBBackend (AWS prod)      │
│ ibge.py  — SIDRA    │     │                                  │
│ world_bank.py       │     │ ConversationRecord (dataclass)  │
│ registry.py         │     └─────────────────────────────────┘
└─────────────────────┘
```

---

## Pipeline LangGraph

### Fluxo de Execução (Onda 3 — 8 nós)

```
question (str)
     │
     ▼
[planner]      ── LLM: JSON com lista de ferramentas [{tool, params}, ...]
     │              state.tool_to_use, state.pending_tools
     ▼
[action]       ── ToolRegistry.fetch(params) → acumula DataFrames
     │              state.data + state.datasets accumulation
     ├── pending_tools?  sim → [next_tool] → voltar ao action
     │   não ↓
[stats]        ── Python puro: média 1/3/5y, z-score, percentil, tendência OLS
     │              state.historical_stats, state.historical_stats_text
     │              + computa indicadores derivados (Fisher, câmbio real)
     │              state.derived_data
     ▼
[analysis]     ── LLM: análise técnica com contexto histórico injetado
     │              state.analysis
     ▼
[auditor]      ── Python puro: 4 checks de consistência macro
     │              state.audit_flags, state.audit_summary
     ▼
[plot]         ── matplotlib: série única ou subplots multi-série
     │              state.plot_path
     ▼
[response]     ── LLM: síntese final + alertas de auditoria incorporados
                    state.response  ← resposta final em PT-BR
```

### Estado Compartilhado (`AgentState`)

| Campo | Tipo | Descrição |
|---|---|---|
| `question` | `str` | Pergunta original do usuário |
| `session_id` | `str` | UUID da sessão (gerado se não fornecido) |
| `plan` | `str` | Saída do nó planner |
| `tool_to_use` | `str` | Nome da ferramenta escolhida |
| `tool_params` | `dict` | Parâmetros para a ferramenta |
| `intermediate_steps` | `List[str]` | Log acumulado (Annotated + operator.add) |
| `data` | `pd.DataFrame \| None` | Dados retornados pela ferramenta |
| `analysis` | `str` | Análise gerada pelo LLM |
| `plot_path` | `str \| None` | Caminho do gráfico gerado |
| `response` | `str` | Resposta final consolidada |
| `error` | `str \| None` | Mensagem de erro, se houver |
| `historical_stats` | `dict` | Estatísticas por coluna: média, z-score, percentil, trend_3m |
| `historical_stats_text` | `str` | Texto formatado para injeção no prompt (contexto histórico) |
| `derived_data` | `dict` | DataFrames de indicadores derivados (juros_reais, cambio_real) |
| `audit_flags` | `list[str]` | Lista de alertas do auditor (emojis + texto) |
| `audit_summary` | `str` | Bloco formatado de auditoria para injeção no prompt |

---

## Onda 3 — Novos Componentes

### `nodes/stats.py` — Contexto Histórico (Python puro)

Roda **antes** da análise LLM. Calcula por coluna numérica do DataFrame:

| Estatística | Fórmula | Relevância |
|---|---|---|
| `mean_1y` / `mean_3y` / `mean_5y` | $\bar{y}_{[T-k,T]}$ | Comparação com regimes anteriores |
| `mean_full` / `std_full` | Média e desvio histórico completo | Base para z-score |
| `zscore_latest` | $(y_T - \bar{y}) / \sigma$ | Quão incomum é o valor atual |
| `percentile_rank` | ECDF empírica | Posição na distribuição histórica |
| `trend_3m` | OLS slope via `np.polyfit` | Direção recente (`alta/baixa/estável`) |
| `lag_days` | dias desde o último ponto | Qualidade/frescor dos dados |

Resultado formatado é injetado no prompt do `analysis_node` como
`=== CONTEXTO HISTÓRICO (calculado via Python, não estimado) ===`.

### `nodes/auditor.py` — Auditoria de Consistência (Python puro)

Roda **depois** da análise LLM. Implementa 4 regras:

| Check | Lógica | Base teórica |
|---|---|---|
| Freshness | `lag_days > 90/365` | Boas práticas de disclosure |
| Outlier | `\|z\| ≥ 2.5` | Normal: < 1,2% das observações |
| Juros reais range | `r < −3%` ou `r > 18%` | Série histórica BCB 432/433 |
| Selic × IPCA | Regra de Taylor simplificada | Taylor (1993) |

### `tools/derived.py` — Indicadores Derivados

Implementa indicadores que não existem diretamente nas APIs — são calculados
via Python a partir de séries primárias:

| Indicador | Fórmula | Dado necessário |
|---|---|---|
| Juros reais (ex-post) | $(1 + i) / (1 + \Pi_{12m}) - 1$ | Selic 432 + IPCA 433 |
| Câmbio real (índice) | $(E_t/E_0) \times (P_t^{BR}/P_0^{BR}) \times 100$ | Dólar 1 + IPCA 433 |

### `knowledge/` — Base Teórica

Arquivos Markdown injetados no `analysis_node` para embasar a análise:

| Arquivo | Indicador | Conteúdo principal |
|---|---|---|
| `ipca.md` | IPCA/IPCA-15 | Inércia inflacionária, Regra de Taylor, metas |
| `selic.md` | Selic | Taxa neutra, COPOM, forward guidance |
| `juros_reais.md` | Juros reais | Fisher, histórico 1999–2026, interpretação |
| `dolar.md` | Câmbio PTAX | PPP, pass-through, Balassa-Samuelson |
| `desocupacao.md` | Desocupação | Curva de Phillips, NAIRU, Lei de Okun |
| `fbcf_pib.md` | FBCF/PIB | Solow, multiplicador keynesiano |
| `gini.md` | Gini | Kuznets, Piketty r>g, transferências |
| `bibliografia.md` | — | Referências completas |

---

## Fontes de Dados

| Classe | Fonte | Exemplos de Séries |
|---|---|---|
| `BCBDataSource` | Sistema SGS do Banco Central do Brasil | IPCA (433), Selic (432), Câmbio USD (1) |
| `IPEADataSource` | API IPEADATA | PIB, Gini, emprego |
| `WorldBankDataSource` | API World Bank | Indicadores internacionais (PIB, educação) |
| `IBGEDataSource` | SIDRA/IBGE *(stub — Fase D)* | PNAD, Censo, IPCA-15 |

Todos implementam a ABC `DataSource` (`src/tools/base.py`):

```python
class DataSource(ABC):
    @abstractmethod
    def fetch(self, series_code: str, **kwargs) -> Optional[pd.DataFrame]:
        ...
```

---

## Configuração

Hierarquia de precedência (maior → menor):

```
Variáveis de ambiente do sistema
        ↓
Arquivo .env (dotenv)
        ↓
config/{APP_ENV}.yaml
        ↓
config/default.yaml
```

Gerenciada por `pydantic-settings` (`src/agente/config.py`):

```python
settings = get_settings()   # singleton via @lru_cache
settings.google_api_key     # str
settings.app_env            # "development" | "production" | "testing"
settings.llm_model          # "gemini-2.5-flash"
settings.api_port           # 8000
```

---

## Estrutura de Diretórios

```
.
├── config/                    # YAML por ambiente
│   ├── default.yaml
│   ├── development.yaml
│   ├── production.yaml
│   └── aws.yaml
├── deployment/
│   ├── docker/
│   │   ├── Dockerfile
│   │   ├── Dockerfile.test
│   │   └── .dockerignore
│   ├── docker-compose.yml     # dev local
│   └── docker-compose.prod.yml
├── docs/
├── src/
│   ├── agente/
│   │   ├── agent.py           # LangGraph graph factory + run_agent()
│   │   ├── config.py          # Pydantic Settings
│   │   ├── state.py           # TypedDict AgentState
│   │   └── nodes/             # Um arquivo por nó
│   ├── api/
│   │   ├── server.py          # FastAPI factory
│   │   ├── routes.py          # POST /ask, GET /health
│   │   ├── legacy.py          # POST /ask-agent (compat.)
│   │   └── schemas.py         # Pydantic I/O models
│   ├── logger/
│   │   └── config.py          # JSON/text structured logging
│   ├── storage/
│   │   ├── base.py            # StorageBackend ABC
│   │   ├── sqlite.py
│   │   └── dynamodb.py
│   ├── knowledge/             # Base teórica (Markdown → injetado nos prompts)
│   │   ├── ipca.md
│   │   ├── selic.md
│   │   ├── juros_reais.md
│   │   ├── dolar.md
│   │   ├── desocupacao.md
│   │   ├── fbcf_pib.md
│   │   ├── gini.md
│   │   └── bibliografia.md
│   ├── tools/
│   │   ├── base.py            # DataSource ABC
│   │   ├── bcb.py
│   │   ├── ipea.py
│   │   ├── ibge.py
│   │   ├── world_bank.py
│   │   ├── derived.py         # Fisher identity, câmbio real
│   │   └── registry.py
│   ├── utils/
│   │   ├── date_utils.py
│   │   ├── enums.py
│   │   └── validators.py
│   ├── asgi.py                # ASGI entry point
│   ├── cli.py                 # CLI interativo
│   └── main.py                # CLI legado
└── tests/
    ├── conftest.py
    ├── fixtures/
    ├── unit/
    └── integration/
```

---

## Infraestrutura AWS (Alvo de Produção)

| Serviço | Uso | Custo estimado |
|---|---|---|
| ECS Fargate Spot | Container da API (0.25 vCPU / 512 MB) | ~$4-8/mês |
| DynamoDB on-demand | Histórico de conversas | ~$1-3/mês |
| S3 | Armazenamento de gráficos PNG | ~$0.50/mês |
| CloudWatch Logs | Logs estruturados JSON | ~$1-2/mês |
| ECR | Repositório de imagem Docker | ~$0.50/mês |
| **Total estimado** | | **~$7-14/mês** |

Budget total do projeto: **USD 100/mês** (margem ampla para picos e LLM API).

---

## Logging

Formato JSON (CloudWatch-ready) em produção:

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "logger": "agente.nodes.action",
  "message": "Ferramenta bcb executada com sucesso",
  "session_id": "abc-123"
}
```

Formato texto colorido no terminal local (desenvolvimento).
