# Arquitetura — Agente de Dados Macroeconômicos Brasileiros

## Visão Geral

O projeto é um **agente de IA conversacional** especializado em dados macroeconômicos brasileiros.
Recebe perguntas em linguagem natural, acessa APIs públicas de dados oficiais, realiza análises
estatísticas e retorna respostas textuais enriquecidas com gráficos.

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
│   AgentState ──► Planner ──► Action ──► Analysis ──► Plot       │
│                                                  └──► Response  │
│                                                                  │
│   Nós (src/agente/nodes/):                                       │
│     planner.py   – decide ferramenta e parâmetros (LLM)         │
│     action.py    – executa a ferramenta de dados                 │
│     analysis.py  – análise textual dos dados retornados (LLM)   │
│     plot.py      – gera gráfico matplotlib                      │
│     response.py  – consolida resposta final (LLM)               │
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

### Fluxo de Execução

```
question (str)
     │
     ▼
[planner] ── LLM decide: qual ferramenta? quais parâmetros?
     │         state.tool_to_use, state.tool_params
     ▼
[action]  ── ToolRegistry.get(tool_to_use).fetch(params)
     │         state.data = pd.DataFrame | None
     ▼
[analysis] ── LLM analisa os dados retornados
     │         state.analysis = str
     ▼
[plot]     ── matplotlib gera chart_{session_id}.png
     │         state.plot_path = str | None
     ▼
[response] ── LLM consolida análise + dados + contexto
                state.response = str  ← resposta final
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
│   ├── tools/
│   │   ├── base.py            # DataSource ABC
│   │   ├── bcb.py
│   │   ├── ipea.py
│   │   ├── ibge.py
│   │   ├── world_bank.py
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
