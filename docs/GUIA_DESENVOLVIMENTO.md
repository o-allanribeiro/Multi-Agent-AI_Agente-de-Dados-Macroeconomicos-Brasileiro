# Guia de Desenvolvimento e Testes

> **Requisitos:** Python 3.11 · venv ativado · `.env` configurado

---

## Índice

1. [Configuração do Ambiente Local](#1-configuração-do-ambiente-local)
2. [Executar o Servidor](#2-executar-o-servidor)
3. [Executar Testes](#3-executar-testes)
4. [Depuração e Logs](#4-depuração-e-logs)
5. [Adicionar um Novo Indicador](#5-adicionar-um-novo-indicador)
6. [Adicionar um Novo Nó ao Pipeline](#6-adicionar-um-novo-nó-ao-pipeline)
7. [Qualidade de Código](#7-qualidade-de-código)
8. [Storage: SQLite vs DynamoDB Local](#8-storage-sqlite-vs-dynamodb-local)
9. [Docker](#9-docker)
10. [Checklist de Pull Request](#10-checklist-de-pull-request)

---

## 1. Configuração do Ambiente Local

```powershell
# 1. Clonar
git clone https://github.com/o-allanribeiro/Multi-Agent-AI_Agente-de-Dados-Macroeconomicos-Brasileiro.git
cd "PROJETO MULTI AGENTE-  Agente de Dados Macroeconômicos Brasileiros"

# 2. Criar e ativar virtualenv
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Instalar dependências (produção + dev)
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Variáveis de ambiente
Copy-Item .env.example .env
# Edite .env: preencha GOOGLE_API_KEY
```

### Variáveis essenciais (`.env`)

```dotenv
# Obrigatório
GOOGLE_API_KEY=sua_chave_aqui

# Ambiente (development | production | testing)
APP_ENV=development

# Storage (sqlite | dynamodb)
STORAGE_BACKEND=sqlite

# DynamoDB Local (apenas se STORAGE_BACKEND=dynamodb)
DYNAMODB_ENDPOINT_URL=http://localhost:8001
AWS_REGION=us-east-1
DYNAMODB_TABLE_NAME=agente-macro-conversations

# Servidor
API_HOST=127.0.0.1
API_PORT=8002
```

---

## 2. Executar o Servidor

### SQLite (recomendado para desenvolvimento)

```powershell
$env:PYTHONPATH = "src"
$env:STORAGE_BACKEND = "sqlite"
.\venv\Scripts\python.exe -m uvicorn src.asgi:app --host 127.0.0.1 --port 8002 --reload
```

Acesse: `http://127.0.0.1:8002` — abre a interface HTML diretamente.

> **Nota:** A porta 8000 é usada pelo Docker Desktop. Use sempre 8002 no Windows.

### Testar via PowerShell (sem abrir o browser)

```powershell
$body = '{"question": "Qual a Selic atual?", "session_id": "test-001"}'
Invoke-RestMethod -Method POST `
  -Uri "http://127.0.0.1:8002/ask" `
  -ContentType "application/json" `
  -Body $body | ConvertTo-Json -Depth 5
```

### Endpoints disponíveis

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Interface HTML (index.html) |
| `POST` | `/ask` | Pergunta ao agente |
| `GET` | `/history?limit=20` | Histórico de conversas |
| `GET` | `/health` | Health check |
| `POST` | `/ask-agent` | Legado (compatibilidade) |

---

## 3. Executar Testes

```powershell
$env:PYTHONPATH = "src"

# Todos os testes
.\venv\Scripts\python.exe -m pytest tests/ -v

# Apenas unitários (rápido, sem chamadas externas)
.\venv\Scripts\python.exe -m pytest tests/unit/ -v

# Apenas integração
.\venv\Scripts\python.exe -m pytest tests/integration/ -v

# Com cobertura
.\venv\Scripts\python.exe -m pytest tests/ --cov=src --cov-report=term-missing

# E2E (requer servidor rodando na porta 8002)
.\venv\Scripts\python.exe -m pytest tests/integration/test_e2e.py -v -s
```

### Estrutura de testes

```
tests/
├── conftest.py              # Fixtures globais (mock_state, mock_settings, etc.)
├── fixtures/
│   └── mock_data.py         # DataFrames e estados mock reutilizáveis
├── unit/
│   ├── test_api.py          # Testa routes.py e schemas.py (sem LLM)
│   ├── test_nodes.py        # Testa cada nó do pipeline (mock LLM)
│   └── test_tools.py        # Testa ferramentas de dados (mock HTTP)
└── integration/
    ├── test_agent_flow.py   # Pipeline completo com mock de LLM
    ├── test_api_endpoints.py# FastAPI TestClient end-to-end
    └── test_e2e.py          # E2E real (requer API key e internet)
```

### Escrevendo um novo teste unitário

```python
# tests/unit/test_nodes.py
def test_stats_node_computes_zscore(mock_state):
    """stats_node deve calcular z-score correto para série sintética."""
    import numpy as np
    import pandas as pd
    from agente.nodes.stats import stats_node

    # Arrange: série com média 10, std 2, último valor 14
    dates = pd.date_range("2020-01-01", periods=60, freq="MS")
    values = [10.0] * 59 + [14.0]
    mock_state["data"] = pd.DataFrame({"indicador": values}, index=dates)
    mock_state["question"] = "teste"

    # Act
    result = stats_node(mock_state)

    # Assert
    stats = result["historical_stats"]["indicador"]
    assert abs(stats["zscore_latest"] - 2.0) < 0.1
```

---

## 4. Depuração e Logs

### Aumentar verbosidade

```powershell
$env:LOG_LEVEL = "DEBUG"
$env:PYTHONPATH = "src"
.\venv\Scripts\python.exe -m uvicorn src.asgi:app --host 127.0.0.1 --port 8002 --reload
```

### Testar um nó individualmente

```powershell
$env:PYTHONPATH = "src"
.\venv\Scripts\python.exe -c "
from agente.agent import create_agent
g = create_agent()
print('Nodes:', list(g.nodes.keys()))
"
```

### Verificar compilação do grafo

```powershell
$env:PYTHONPATH = "src"
.\venv\Scripts\python.exe -c "
from agente.agent import run_agent
result = run_agent('Qual a Selic atual?')
print('Response:', result.get('response', '')[:200])
print('Audit flags:', result.get('audit_flags', []))
print('Historical stats keys:', list((result.get('historical_stats') or {}).keys()))
"
```

### Verificar derivados (Fisher identity)

```powershell
$env:PYTHONPATH = "src"
.\venv\Scripts\python.exe -c "
from agente.agent import run_agent
result = run_agent('Qual o juro real no Brasil hoje?')
print('Derived data keys:', list((result.get('derived_data') or {}).keys()))
print('Audit summary:', result.get('audit_summary', 'N/A'))
"
```

---

## 5. Adicionar um Novo Indicador

### Passo 1 — Implementar a ferramenta

Crie ou edite um arquivo em `src/tools/`. Herde de `DataSource`:

```python
# src/tools/meu_modulo.py
from tools.base import DataSource
import pandas as pd

class MinhaFerramenta(DataSource):
    name = "minha_ferramenta"
    description = "Descreva o indicador para o planner LLM."

    def fetch(self, series_code: str, last_n_years: int = 5, **kwargs) -> pd.DataFrame:
        # Sua lógica de coleta aqui
        ...
```

### Passo 2 — Registrar no ToolRegistry

```python
# src/tools/registry.py — no bloco de registro
from tools.meu_modulo import MinhaFerramenta
registry.register(MinhaFerramenta())
```

### Passo 3 — Criar arquivo de conhecimento teórico

```markdown
# src/knowledge/meu_indicador.md
## O que é ...
## Por que importa ...
## Enquadramento Teórico
## Contexto Brasil
## Mapeamento
```

### Passo 4 — Mapear na base de conhecimento

```python
# src/knowledge/__init__.py — adicione mapeamento
TOOL_THEORY_MAP = {
    ...
    "minha_ferramenta": "meu_indicador.md",
}
```

### Passo 5 — Escrever testes unitários

```python
# tests/unit/test_tools.py
def test_minha_ferramenta_retorna_dataframe(requests_mock):
    ...
```

---

## 6. Adicionar um Novo Nó ao Pipeline

### Passo 1 — Criar `src/agente/nodes/meu_no.py`

```python
from agente.state import AgentState
import logging

logger = logging.getLogger(__name__)

def meu_no(state: AgentState) -> AgentState:
    logger.info("Executando nó MEU_NO | session=%s", state.get("session_id"))
    # lógica aqui
    state["meu_campo"] = "resultado"
    return state
```

### Passo 2 — Exportar em `nodes/__init__.py`

```python
from agente.nodes.meu_no import meu_no
__all__ = [..., "meu_no"]
```

### Passo 3 — Adicionar campo ao `state.py`

```python
class AgentState(TypedDict):
    ...
    meu_campo: Optional[str]
```

### Passo 4 — Registrar e conectar em `agent.py`

```python
from agente.nodes import meu_no

workflow.add_node("meu_step", meu_no)
workflow.add_edge("no_anterior_step", "meu_step")
workflow.add_edge("meu_step", "proximo_step")
```

### Passo 5 — Inicializar campo em `run_agent()`

```python
initial_state = {
    ...
    "meu_campo": None,
}
```

---

## 7. Qualidade de Código

```powershell
$env:PYTHONPATH = "src"

# Formatação
.\venv\Scripts\python.exe -m black src/ tests/

# Ordenação de imports
.\venv\Scripts\python.exe -m isort src/ tests/

# Type checking
.\venv\Scripts\python.exe -m mypy src/ --ignore-missing-imports

# Linting
.\venv\Scripts\python.exe -m flake8 src/ tests/ --max-line-length=100

# Segurança (OWASP)
.\venv\Scripts\python.exe -m bandit -r src/ -ll
```

### Pre-commit (opcional)

```powershell
.\venv\Scripts\python.exe -m pre_commit install
# Agora roda automaticamente a cada commit
```

---

## 8. Storage: SQLite vs DynamoDB Local

### SQLite (padrão, sem configuração)

```powershell
$env:STORAGE_BACKEND = "sqlite"
# Banco criado em: src/output/conversations.db (auto)
```

### DynamoDB Local (testar comportamento AWS)

**Pré-requisito:** Java 11+ instalado.

```powershell
# 1. Baixar DynamoDB Local (apenas uma vez)
# Coloque o JAR em scripts/dynamodb-local/

# 2. Iniciar (mantém dados em memória)
.\scripts\start_dynamodb_local.ps1

# 3. Criar tabela e GSI
$env:PYTHONPATH = "src"
.\venv\Scripts\python.exe scripts/setup_dynamodb_local.py

# 4. Usar no servidor
$env:STORAGE_BACKEND = "dynamodb"
$env:DYNAMODB_ENDPOINT_URL = "http://localhost:8001"
$env:PYTHONPATH = "src"
.\venv\Scripts\python.exe -m uvicorn src.asgi:app --host 127.0.0.1 --port 8002 --reload
```

> **Timeout configurado:** `connect_timeout=3s, max_attempts=1` — se o DynamoDB não estiver
> rodando, o servidor usa o fallback graciosamente (não trava).

---

## 9. Docker

```powershell
# Build e subir (apenas API)
cd deployment
docker compose up --build

# Com DynamoDB Local
docker compose --profile dynamodb up --build

# Produção
docker compose -f docker-compose.prod.yml up --build
```

O Dockerfile usa build multi-stage:
1. `builder` — instala dependências
2. `runtime` — imagem mínima para produção

---

## 10. Checklist de Pull Request

- [ ] `get_errors()` sem erros de lint/type
- [ ] Testes unitários escritos para nova funcionalidade
- [ ] `pytest tests/unit/ -v` — todos aprovados
- [ ] `pytest tests/integration/ -v` — todos aprovados
- [ ] Novo indicador tem arquivo `knowledge/*.md`
- [ ] Novo campo no estado tem inicialização em `run_agent()`
- [ ] `CHANGELOG.md` atualizado com a mudança
- [ ] Sem credenciais (`GOOGLE_API_KEY` etc.) vazadas no código
