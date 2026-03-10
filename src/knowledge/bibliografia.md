# Bibliografia e Referências Técnicas — Agente Macro-BR

Base de referência científica que fundamenta as análises do agente.
Organizada em quatro domínios: pensamento econômico, dados oficiais, engenharia de IA e teoria monetária.

---

## 📚 Pensamento Econômico Brasileiro

| Autor | Obra | Ano | Relevância para o agente |
|---|---|---|---|
| Furtado, C. | *Formação Econômica do Brasil* | 1959 | Base estruturalista para análise do Gini e ciclos de subdesenvolvimento |
| Simonsen, M. H. | *Inflação: Gradualismo x Tratamento de Choque* | 1970 | Teoria da inflação inercial — interpreta a persistência histórica da Selic |
| Simonsen, M. H. | *Teoria dos Jogos e a Inflação Inercial* | 1985 | Modelo de coordenação entre agentes — explica âncoras de expectativas |
| Resende, A. L.; Arida, P. | *Inertial Inflation and Monetary Reform in Brazil* | 1985 | Fundamentação teórica do Plano Real (URV) |
| Bresser-Pereira, L. C. | *Inflação Inercial e Plano Cruzado* | 1987 | Análise dos planos heterodoxos anti-inflacionários |

## 📚 Pensamento Econômico Mundial

| Autor | Obra | Ano | Relevância para o agente |
|---|---|---|---|
| Smith, A. | *A Riqueza das Nações* | 1776 | Mecanismos de preços e concorrência; fundamento dos modelos de equilíbrio |
| Ricardo, D. | *Princípios de Economia Política* | 1817 | Vantagens comparativas — análise do câmbio e balança comercial |
| Marx, K. | *O Capital* | 1867 | Conflito distributivo e ciclos de crise — lente para o Gini e desocupação |
| Marshall, A. | *Princípios de Economia* | 1890 | Elasticidades e equilíbrio de mercado — base neoclássica do agente |
| Keynes, J. M. | *Teoria Geral do Emprego, do Juro e da Moeda* | 1936 | Multiplicador keynesian; interpretação da FBCF e demanda agregada |
| Friedman, M. | *A Monetary History of the United States* | 1963 | "Inflação é sempre um fenômeno monetário" — ancora análise do IPCA/Selic |
| Solow, R. | *A Contribution to the Theory of Economic Growth* | 1956 | Modelo de crescimento — interpreta trajetória do PIB trimestral |
| Taylor, J. B. | *Discretion vs. Policy Rules in Practice* | 1993 | Regra de Taylor — formalismo central para análise da Selic vs. inflação |
| Piketty, T. | *O Capital no Século XXI* | 2013 | r > g — formaliza tendência de concentração de renda (Coeficiente de Gini) |
| Sen, A. | *Development as Freedom* | 1999 | Multi-dimensionalidade do desenvolvimento; contextualiza indicadores sociais |

---

## 📊 Fontes de Dados Oficiais

| Instituição | Recurso | URL de Referência |
|---|---|---|
| Banco Central do Brasil | Sistema Gerenciador de Séries Temporais (SGS) | https://www3.bcb.gov.br/sgspub |
| Banco Central do Brasil | API de Séries Temporais (JSON) | https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados |
| Banco Central do Brasil | Relatório Focus — Expectativas de Mercado | https://www.bcb.gov.br/publicacoes/focus |
| Banco Central do Brasil | Atas e Comunicados do COPOM | https://www.bcb.gov.br/publicacoes/atas-copom |
| Banco Central do Brasil | API Olinda/OData (Expectativas) | https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata |
| IBGE | SIDRA — Sistema de Recuperação Automática | https://servicodados.ibge.gov.br/api/v3/agregados |
| IBGE | PNAD Contínua — Mercado de Trabalho | https://www.ibge.gov.br/estatisticas/sociais/trabalho |
| IPEA | IPEADATA — Dados Macroeconômicos | http://www.ipeadata.gov.br/api/odata4/conjuntura |
| Banco Mundial | World Development Indicators (WDI) | https://data.worldbank.org/indicator/SI.POV.GINI |

---

## ⚙️ Arquitetura de IA e Engenharia de Dados

| Referência | Contribuição |
|---|---|
| LangChain & LangGraph — *Documentação Técnica* | Orquestração de agentes com grafos de estado e ciclos ReAct |
| Google AI — *Gemini API Documentation* | Modelo base do agente; Context Caching (redução de custos em até 90%) |
| Google Cloud — *Vertex AI Context Caching* | Armazena tokens estáticos (teorias, metadados) reduzindo custo de entrada |
| NVIDIA — *Chain of Thought (CoT) Prompting* | Técnica de raciocínio encadeado para análises macroeconômicas complexas |
| ImprovingAgents.com — *Which Table Format Do LLMs Understand Best?* | Markdown-KV supera CSV/JSON: 60,7% de acurácia em recuperação |
| GibsonAI — *Why Use SQL Databases for AI Agent Memory* | SQLite/SQL ideal para séries temporais: 90% de acurácia em filtros exatos |
| Oracle Developers Blog — *Comparing File Systems and Databases for AI Agent Memory* | Guia híbrido: SQL para numérico, Vector DB para texto semântico |
| TowardsDataScience — *Zero-Waste Agentic RAG* | Caching para minimizar latência e custo em arquiteturas RAG |
| Medium — *Building a Markdown Knowledge Ingestor for RAG* | Padrão de ingestão de Markdown para base teórica RAG |

---

## 🏛️ Política Monetária Brasileira

| Referência | Contribuição |
|---|---|
| Banco Central do Brasil — *Notas de Política Monetária* | Comunicação oficial das decisões do COPOM |
| BCB — *Relatório de Inflação (trimestral)* | Projeções macroeconômicas e avaliação do hiato do produto |
| Taylor, J. B. (1993) | Regra de Taylor: $i_t = r^* + \pi_t + \alpha(\pi_t - \pi^*) + \beta y_t$ |
| Loughran-McDonald Sentiment Lexicon | Léxico financeiro para NLP aplicado às atas do COPOM |
| ANPEC — *Determinantes da Taxa de Câmbio Real* | Modelos empíricos para câmbio e Efeito Balassa-Samuelson |
| SciELO — *A Nova Política Monetária: Regime de Metas de Inflação* | Fundamentação do regime de metas adotado pelo BCB em 1999 |

---

## 🏷️ Mapeamento Teoria ↔ Indicador

| Indicador | Base Teórica Principal | Arquivo de Conhecimento |
|---|---|---|
| IPCA / IPCA-15 | Taylor Rule · Simonsen inflação inercial · Plano Real | `ipca.md` |
| Taxa Selic | Taylor Rule · taxa neutra *r\** · Friedman monetarismo | `selic.md` |
| Dólar PTAX | PPP · Balassa-Samuelson · CDS / risco-país | `dolar.md` |
| Desocupação | Curva de Phillips · Lei de Okun · Marx exército de reserva · Furtado | `desocupacao.md` |
| FBCF / PIB | Keynes multiplicador · Acelerador · Solow · Furtado ciclo vicioso | `fbcf_pib.md` |
| Gini | Kuznets U · Piketty *r > g* · Furtado origens coloniais · Paes de Barros ANOGI | `gini.md` |

---

*Última atualização: Março de 2026 — Agente Macro-BR v1.0*
