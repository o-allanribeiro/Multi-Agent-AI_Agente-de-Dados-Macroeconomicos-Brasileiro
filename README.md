
# Agente de IA para Análise de Dados Macroeconômicos do Brasil

> **Stack:** Python 3.11 · LangGraph 0.0.57 · Gemini 2.5 Flash · FastAPI · SQLite/DynamoDB  
> **Versão:** Onda 3 — pipeline de 8 nós com auditor, contexto histórico e indicadores derivados  
> **Status:** Desenvolvimento ativo

---

## O que é este projeto?

Agente de Inteligência Artificial autônomo que responde perguntas em **linguagem natural** sobre a conjuntura macroeconômica brasileira. O agente:

1. **Interpreta** a pergunta e planeja quais dados buscar
2. **Coleta** dados de APIs oficiais (BCB, IPEA, IBGE, Banco Mundial)
3. **Calcula** indicadores derivados (juros reais via Identidade de Fisher, câmbio real via PPP)
4. **Contextualiza** com estatísticas históricas: média 1/3/5 anos, z-score, percentil, tendência OLS
5. **Analisa** com LLM embasado em teoria econômica (Regra de Taylor, Curva de Phillips, Solow...)
6. **Audita** consistência macroeconômica via regras Python puras (sem alucinação)
7. **Sintetiza** a resposta com visualização automática

```
Pergunta → Planner → Action(es) → Stats → Analysis → Auditor → Plot → Resposta
```

---

## Índice da Documentação

| Documento | Conteúdo |
|---|---|
| **Este README** | Visão geral, quickstart, indicadores, exemplos |
| [docs/FUNDAMENTO_CIENTIFICO.md](docs/FUNDAMENTO_CIENTIFICO.md) | Modelos econométricos, fórmulas, referências de graduação |
| [docs/ARQUITETURA.md](docs/ARQUITETURA.md) | Pipeline LangGraph, estado, diagrama de componentes |
| [docs/GUIA_DESENVOLVIMENTO.md](docs/GUIA_DESENVOLVIMENTO.md) | Setup local, testes, como adicionar indicadores/nós |
| [docs/GUIA_INSTALACAO.md](docs/GUIA_INSTALACAO.md) | Instalação passo a passo (local + Docker + AWS) |
| [docs/MOTIVACAO.md](docs/MOTIVACAO.md) | Contexto acadêmico, justificativa e fontes |
| [docs/PERGUNTAS_DEMO.md](docs/PERGUNTAS_DEMO.md) | 30+ perguntas de exemplo organizadas por tema |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Histórico de versões (Onda 1–3) |
| [src/knowledge/](src/knowledge/) | Base teórica por indicador (injetada nos prompts) |

---

---

## Indicadores Cobertos

| Indicador | Série | Fonte | Frequência |
|---|---|---|---|
| IPCA — Variação Mensal | 433 | BCB/SGS | Mensal |
| Taxa Selic Meta (COPOM) | 432 | BCB/SGS | Diária/mensal |
| Taxa de Desocupação (PNAD) | 24369 | BCB/SGS | Trimestral |
| Taxa de Câmbio — Dólar PTAX | 1 | BCB/SGS | Diária |
| PIB Trimestral (variação %) | `pib_trimestral` | IBGE/SIDRA | Trimestral |
| IPCA-15 (prévia de inflação) | `ipca15` | IBGE/SIDRA | Mensal |
| Rendimento Médio Real PNAD | `rendimento_pnad` | IBGE/SIDRA | Trimestral |
| Formação Bruta de Capital Fixo | `GAC12_INDFBCF12` | IPEADATA | Mensal |
| Coeficiente de Gini | `SI.POV.GINI` | Banco Mundial | Anual |
| **Juros Reais (derivado)** | 432 + 433 | BCB calculado | Mensal |
| **Câmbio Real (derivado)** | 1 + 433 | BCB calculado | Diária |

---

## Fundamento Científico

O agente implementa modelos de **Ciências Econômicas** diretamente em Python:

| Modelo | Implementação | Referência |
|---|---|---|
| Identidade de Fisher | `(1+Selic)/(1+IPCA_12m)−1` | Fisher (1930) |
| Regra de Taylor | Auditor: Selic↑↓ vs IPCA aceleração | Taylor (1993) |
| Regressão OLS | `np.polyfit` — tendência 3 meses | Wooldridge, cap. 3 |
| Z-score padronizado | $(y_T - \bar{y})/\sigma$ | Gujarati, cap. 4 |
| Percentil empírico (ECDF) | `scipy.stats.percentileofscore` | Distribuição empírica |
| IPCA acumulado 12m | Produto composto rolling 12 meses | Teoria monetária |
| Câmbio real (PPP) | $(E_t/E_0) \times (P_t^{BR}/P_0^{BR}) \times 100$ | Cassel (1916) |

> Documentação completa em [docs/FUNDAMENTO_CIENTIFICO.md](docs/FUNDAMENTO_CIENTIFICO.md)

---

## Arquitetura do Pipeline

```
Pergunta
   │
   ▼
[Planner]   ── Gemini: JSON lista de ferramentas [{tool, params}, ...]
   │
   ▼
[Action]    ── Executa ferramenta → acumula DataFrames (retry + cache)
   │  ↑
   │  └── [Next-Tool] ── loop se pending_tools não vazia
   │
   ▼
[Stats]     ── Python puro: média 1/3/5y, z-score, percentil, trend OLS,
   │             indicadores derivados (Fisher, câmbio real)
   │
   ▼
[Analysis]  ── Gemini: análise técnica + contexto histórico injetado
   │
   ▼
[Auditor]   ── Python puro: 4 checks de consistência macro (sem LLM)
   │
   ▼
[Plot]      ── Matplotlib: série única ou subplots multi-indicador
   │
   ▼
[Response]  ── Gemini: síntese final PT-BR + alertas de auditoria
   │
   ▼
JSON { text, plot_base64, cost_estimate_usd }
```

> Documentação completa em [docs/ARQUITETURA.md](docs/ARQUITETURA.md)

---

## Quickstart

### Pré-requisitos

- Python 3.11+
- Chave da Google AI Studio: [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

### 1. Clonar e instalar

```powershell
git clone https://github.com/o-allanribeiro/Multi-Agent-AI_Agente-de-Dados-Macroeconomicos-Brasileiro.git
cd "PROJETO MULTI AGENTE-  Agente de Dados Macroeconômicos Brasileiros"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configurar

```powershell
Copy-Item .env.example .env
# Edite .env: adicione GOOGLE_API_KEY=sua_chave
```

### 3. Executar

```powershell
$env:PYTHONPATH = "src"
$env:STORAGE_BACKEND = "sqlite"
.\venv\Scripts\python.exe -m uvicorn src.asgi:app --host 127.0.0.1 --port 8002 --reload
```

Acesse `http://127.0.0.1:8002` no navegador.

> Guia completo (Docker, DynamoDB, AWS): [docs/GUIA_INSTALACAO.md](docs/GUIA_INSTALACAO.md)  
> Workflow de desenvolvimento e testes: [docs/GUIA_DESENVOLVIMENTO.md](docs/GUIA_DESENVOLVIMENTO.md)

---

## Exemplos de Perguntas

### Indicadores simples
```
"Qual a evolução do IPCA nos últimos 2 anos?"
"Me mostre a trajetória da Selic desde 2022."
"Como está o Coeficiente de Gini no Brasil?"
```

### Indicadores derivados (computados via Python)
```
"Qual o juro real no Brasil hoje?"
"Como está a taxa de câmbio real?"
"Me explique a Selic em termos reais descontando a inflação."
```

### Multi-indicador e contexto histórico
```
"Compare a Selic com o IPCA dos últimos 12 meses."
"O juro real de hoje está acima ou abaixo da média dos últimos 5 anos?"
"A desocupação em 2024 está num nível historicamente alto ou baixo?"
```

> Lista completa (30+ exemplos): [docs/PERGUNTAS_DEMO.md](docs/PERGUNTAS_DEMO.md)

---

## Estrutura do Projeto

```
.
├── index.html                     # Interface web (HTML + Tailwind + JS)
├── .env.example                   # Template de variáveis de ambiente
├── requirements.txt
├── docs/
│   ├── FUNDAMENTO_CIENTIFICO.md  ← modelos econométricos e referências
│   ├── ARQUITETURA.md            ← pipeline Onda 3 (8 nós)
│   ├── GUIA_DESENVOLVIMENTO.md   ← setup, testes, como contribuir
│   ├── GUIA_INSTALACAO.md
│   ├── MOTIVACAO.md
│   ├── PERGUNTAS_DEMO.md
│   └── CHANGELOG.md
├── src/
│   ├── agente/
│   │   ├── agent.py              # LangGraph graph factory (8 nós)
│   │   ├── state.py              # AgentState TypedDict (18 campos)
│   │   └── nodes/
│   │       ├── planner.py        # Planner: lista ferramentas + derivados
│   │       ├── action.py         # Executor + loop multi-ferramenta
│   │       ├── stats.py          # Contexto histórico (Python puro)
│   │       ├── analysis.py       # Análise LLM + contexto histórico
│   │       ├── auditor.py        # 4 checks de consistência macro
│   │       ├── plot.py           # Matplotlib single/subplots
│   │       └── response.py       # Síntese final + alertas auditoria
│   ├── tools/
│   │   ├── bcb.py / ibge.py / ipea.py / world_bank.py
│   │   ├── derived.py            # Fisher identity, câmbio real
│   │   ├── registry.py           # ToolRegistry imutável
│   │   └── cache.py              # Cache SQLite de séries (TTL)
│   ├── knowledge/
│   │   ├── ipca.md / selic.md / juros_reais.md / dolar.md
│   │   ├── desocupacao.md / fbcf_pib.md / gini.md
│   │   └── bibliografia.md
│   ├── api/                      # FastAPI (routes, schemas, rate limiter)
│   ├── storage/                  # SQLite + DynamoDB backends
│   └── utils/                    # http retry, cost_tracker, date_utils
└── tests/
    ├── unit/                     # test_api, test_nodes, test_tools
    └── integration/              # test_agent_flow, test_e2e
```

---

## Limitações Conhecidas

| Limitação | Contorno |
|---|---|
| Gini (Banco Mundial): lag de 2-3 anos | Auditor sinaliza defasagem automaticamente |
| Cache SQLite não compartilhado entre workers | 1 worker local; Redis em produção multi-worker |
| Gemini sem garantia de disponibilidade 100% | Retry configurado (3 tentativas com backoff) |

---

## Referências Principais

- **Wooldridge, J. M.** — *Introdução à Econometria* — OLS, séries temporais
- **Fisher, I.** (1930) — *The Theory of Interest* — Identidade de Fisher
- **Taylor, J. B.** (1993) — *Discretion vs. Policy Rules* — Regra de Taylor
- **Simonsen, M. H.** (1970) — *Inflação: Gradualismo x Tratamento de Choque*
- **Furtado, C.** (1959) — *Formação Econômica do Brasil*
- **Solow, R.** (1956) — Modelo de crescimento neoclássico

> Referências completas em [docs/FUNDAMENTO_CIENTIFICO.md](docs/FUNDAMENTO_CIENTIFICO.md)

---

## Licença

MIT
