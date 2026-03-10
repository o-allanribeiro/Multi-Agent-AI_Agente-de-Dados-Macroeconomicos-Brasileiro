
-----

# 🤖 Agente de IA para Análise de Dados Macroeconômicos do Brasil

> **Stack:** Python 3.11 · LangGraph · Gemini 2.5 Flash · FastAPI · SQLite/DynamoDB  
> **Status:** Desenvolvimento ativo — pipeline multi-ferramenta com cache e análise comparativa

## Resumo

Este projeto acadêmico de código aberto demonstra a construção de um agente de Inteligência Artificial autônomo capaz de responder perguntas em linguagem natural sobre a conjuntura econômica do Brasil. O agente busca dados de fontes oficiais, aplica contexto teórico econômico, gera análises textuais e produz visualizações — tudo de forma autônoma via pipeline LangGraph + Gemini.

Suporta perguntas simples ("Qual a Selic atual?") e perguntas comparativas multi-indicador ("Compare a Selic com o IPCA dos últimos 2 anos") com subplots automáticos.

---

## Indicadores Cobertos

| Indicador | Código | Fonte |
|---|---|---|
| IPCA — Variação Mensal | 433 | BCB/SGS |
| Taxa Selic Meta (COPOM) | 432 | BCB/SGS |
| Taxa de Desocupação (PNAD) | 24369 | BCB/SGS |
| Taxa de Câmbio — Dólar PTAX | 1 | BCB/SGS |
| PIB Trimestral (variação %) | `pib_trimestral` | IBGE/SIDRA |
| IPCA-15 (prévia de inflação) | `ipca15` | IBGE/SIDRA |
| Rendimento Médio Real PNAD | `rendimento_pnad` | IBGE/SIDRA |
| Formação Bruta de Capital Fixo | `GAC12_INDFBCF12` | IPEADATA |
| Coeficiente de Gini | `SI.POV.GINI` | Banco Mundial |

---

## Arquitetura do Pipeline

```
Pergunta do Usuário
        │
  ┌─────▼──────┐
  │  Planner   │  Gemini → JSON com lista de ferramentas [{tool, params}, ...]
  └─────┬──────┘
        │  (itera para cada ferramenta na fila)
  ┌─────▼──────┐
  │   Action   │  Executa ferramenta → acumula DataFrames (com retry + cache)
  └─────┬──────┘
        │  pending_tools vazia?
        │  sim → continua │ não → loop de volta ao Action
  ┌─────▼──────┐
  │  Analysis  │  Gemini com teoria econômica + aviso automático de defasagem
  └─────┬──────┘
  ┌─────▼──────┐
  │    Plot    │  Matplotlib: série única ou subplots por indicador
  └─────┬──────┘
  ┌─────▼──────┐
  │  Response  │  Gemini sintetiza análise → resposta final em PT-BR
  └─────┬──────┘
        ▼
   API Response (JSON: text + plot_base64)
```

**Camadas de suporte:**
- `src/tools/cache.py` — Cache SQLite de séries temporais (TTL por frequência)
- `src/utils/http.py` — Retry com backoff exponencial (3 tentativas)
- `src/knowledge/` — Base teórica em Markdown (injetada no prompt de análise)
- `src/storage/` — SQLite (dev) ou DynamoDB (prod) para histórico de conversas

---

## Como Executar

### Pré-requisitos

- Python 3.11+
- Chave da Google AI Studio: [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

### 1. Clonar e instalar

```bash
git clone https://github.com/o-allanribeiro/Multi-Agent-AI_Agente-de-Dados-Macroeconomicos-Brasileiro.git
cd Multi-Agent-AI_Agente-de-Dados-Macroeconomicos-Brasileiro

python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Edite `.env` e preencha ao menos:
```
GOOGLE_API_KEY="sua_chave_aqui"
```

### 3. Iniciar o servidor

```bash
# Na raiz do projeto (não dentro de src/)
$env:PYTHONPATH = "src"   # PowerShell
# export PYTHONPATH=src   # bash

uvicorn src.asgi:app --reload --port 8000
```

### 4. Abrir a interface

Abra `index.html` diretamente no navegador. A interface se conecta ao servidor na porta 8000.

---

## Perguntas de Exemplo

```
"Qual a evolução do IPCA nos últimos 2 anos?"
"Me mostre a trajetória da Selic desde 2022."
"Como está o Coeficiente de Gini no Brasil?"
"Compare a Selic com o IPCA dos últimos 12 meses."
"Qual o rendimento médio dos trabalhadores brasileiros?"
"Me mostre o PIB trimestral dos últimos 3 anos."
```

Para mais exemplos, consulte [docs/PERGUNTAS_DEMO.md](docs/PERGUNTAS_DEMO.md).

---

## DynamoDB Local (opcional — para teste de persistência)

Por padrão o agente usa SQLite. Para testar com DynamoDB Local:

**Pré-requisito:** Java 11+ instalado. Se não tiver:

```powershell
winget install Microsoft.OpenJDK.21
```

**Iniciar DynamoDB Local:**

```powershell
.\scripts\start_dynamodb_local.ps1
```

**Criar tabela e índice:**

```bash
python scripts/setup_dynamodb_local.py
```

**Ativar no `.env`:**

```
STORAGE_BACKEND="dynamodb"
DYNAMODB_ENDPOINT_URL="http://localhost:8001"
AWS_REGION="us-east-1"
DYNAMODB_TABLE_NAME="agente-macro-conversations"
```

> **Nota:** O DynamoDB Local roda em memória (`-inMemory`). Dados são perdidos ao reiniciar o processo. Para persistência local, edite `start_dynamodb_local.ps1` e remova `-inMemory`.

---

## Via Docker

```bash
cd deployment
docker compose up --build
```

Para incluir DynamoDB Local no Docker:

```bash
docker compose --profile dynamodb up --build
```

---

## Estrutura do Projeto

```
├── src/
│   ├── agente/
│   │   ├── agent.py          # Grafo LangGraph (pipeline com multi-tool loop)
│   │   ├── state.py          # AgentState (TypedDict com pending_tools + datasets)
│   │   ├── config.py         # Settings via Pydantic
│   │   └── nodes/
│   │       ├── planner.py    # Planner → lista de ferramentas
│   │       ├── action.py     # Executor + next_tool_node (loop multi-ferramenta)
│   │       ├── analysis.py   # Análise comparativa + aviso de defasagem
│   │       ├── plot.py       # Matplotlib: single / subplots multi-série
│   │       └── response.py   # Síntese final
│   ├── tools/
│   │   ├── bcb.py            # BCB/SGS (IPCA, Selic, Câmbio, Desocupação)
│   │   ├── ibge.py           # IBGE/SIDRA (PIB, IPCA-15, Rendimento PNAD)
│   │   ├── ipea.py           # IPEADATA (FBCF)
│   │   ├── world_bank.py     # Banco Mundial (Gini)
│   │   ├── registry.py       # ToolRegistry imutável
│   │   └── cache.py          # Cache SQLite de séries (TTL por frequência)
│   ├── knowledge/            # Teoria econômica em Markdown (injetada no LLM)
│   ├── storage/
│   │   ├── sqlite.py         # Backend SQLite (desenvolvimento)
│   │   └── dynamodb.py       # Backend DynamoDB (produção / GSI query)
│   ├── api/
│   │   ├── server.py         # FastAPI factory + rate limiting (slowapi)
│   │   ├── routes.py         # POST /ask (10 req/min) + custo estimado por req
│   │   └── limiter.py        # Singleton do rate limiter
│   └── utils/
│       ├── http.py           # Retry com backoff exponencial
│       └── cost_tracker.py   # Estimativa de custo Gemini por requisição
├── scripts/
│   ├── setup_dynamodb_local.py   # Cria tabela + GSI RecentConversationsIndex
│   └── start_dynamodb_local.ps1  # Inicia DynamoDB Local
├── deployment/
│   └── docker-compose.yml
├── docs/
│   ├── PERGUNTAS_DEMO.md
│   └── MOTIVACAO.md
├── .env.example              # Template de variáveis (documentado por ambiente)
├── requirements.txt
└── index.html                # Frontend (HTML + Tailwind + JS)
```

---

## Limitações Conhecidas

- **Dados do Banco Mundial (Gini):** lag de 2-3 anos. O agente sinaliza automaticamente a defasagem na análise.
- **Análise multi-indicador:** máximo de eficiência com 2-3 séries simultâneas. Perguntas muito amplas podem gerar respostas longas.
- **Cache de séries:** dados são armazenados localmente em `output/series_cache.db`. Em ambientes com múltiplos workers, o cache SQLite não é compartilhado entre processos.

---

### [➡️ Exemplos de Perguntas para Demonstração][def]

[def]: docs/PERGUNTAS_DEMO.md