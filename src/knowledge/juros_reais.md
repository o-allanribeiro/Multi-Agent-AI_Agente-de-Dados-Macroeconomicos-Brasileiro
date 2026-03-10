# Juros Reais no Brasil — Referência Macroeconômica

## Definição

A **taxa de juros reais** representa o custo efetivo do crédito descontada a inflação.
Ela responde à pergunta: "quanto estou ganhando (ou pagando) de verdade, além da inflação?"

### Juros Reais *Ex-Post* (realizados)
Calculados usando inflação **observada** no período:

$$r_{real} = \frac{1 + r_{nominal}}{1 + \pi} - 1$$

### Juros Reais *Ex-Ante* (esperados)
Calculados usando inflação **esperada** (Focus/COPOM):

$$r_{real}^{exp} = \frac{1 + r_{nominal}}{1 + \mathbb{E}[\pi]} - 1$$

---

## Identidade de Fisher (usada neste agente)

Este agente utiliza a **Identidade de Fisher** para o cálculo ex-post:

```
juros_reais = (1 + Selic_aa) / (1 + IPCA_12m_acumulado) - 1
```

- **Selic**: taxa SELIC Over anualizada (BCB série 432), em % a.a.
- **IPCA**: inflação acumulada em 12 meses (janela rolante), calculada como produto dos índices mensais.

> Aproximação simplificada (válida para baixas taxas): `r_real ≈ r_nominal - π`
> O agente usa a fórmula exata de Fisher para precisão.

---

## Contexto Histórico Brasileiro

| Período | Juros Reais (aprox.) | Contexto |
|---|---|---|
| 1995–1998 | 15–25% a.a. | Plano Real, âncora cambial |
| 1999–2002 | 8–15% a.a. | Flutuação cambial, crise argentina |
| 2003–2005 | 10–14% a.a. | Lula 1, meta de inflação reafirmada |
| 2006–2010 | 5–8% a.a. | Crescimento, pré-crise 2008 |
| 2011–2014 | 2–4% a.a. | Nova Matriz Econômica, Selic artificialmente baixa |
| 2015–2016 | 6–9% a.a. | Recessão, ajuste fiscal |
| 2017–2019 | 2–5% a.a. | Recuperação lenta, inflação baixa |
| 2020–2021 | -1–2% a.a. | Pandemia COVID-19, Selic em 2% |
| 2022–2023 | 6–9% a.a. | Ciclo de alta do COPOM (combate à inflação pós-COVID) |
| 2024 | 7–9% a.a. | Selic em 10,75–12,25%, ancoragem de expectativas |

**Média histórica** (1999–2024): ~6,5% a.a.
**Máximo histórico recente**: ~14% a.a. (2003)
**Mínimo histórico recente**: ~-3% a.a. (2020, pandemia)

---

## Interpretação de Política Monetária

### Taylor Rule (simplificada)
O COPOM reage à inflação desviando da meta:

$$i \approx r^* + \pi_{meta} + \phi_\pi (\pi - \pi_{meta}) + \phi_y (y - y^*)$$

Onde:
- $i$ = taxa Selic nominal
- $r^*$ = taxa neutra real (~4–5% no Brasil)
- $\phi_\pi$ > 1 (princípio de Taylor — resposta maior que 1:1 à inflação)
- $\phi_y$ = sensibilidade ao hiato do produto

### Sinais Macroeconômicos

| Situação | Interpretação |
|---|---|
| Juros reais > 6% | Política monetária **contracionista** — freia crescimento/inflação |
| Juros reais entre 2–5% | Zona **neutra** (depende da taxa natural) |
| Juros reais < 2% | Política **expansionista** — estimula crescimento |
| Juros reais negativos | Política **ultra-expansionista** — emergência (pandemia, crise) |

---

## Impactos Econômicos

- **Crédito**: juros reais altos elevam custo de financiamentos, reduzem consumo e investimento (efeito crowding-out)
- **Câmbio**: juros reais altos atraem capital externo (carry trade) → apreciação do Real
- **Dívida pública**: serviço da dívida aumenta com juros reais elevados (risco fiscal)
- **Inflação**: juros reais positivos e crescentes sinalizam aperto monetário → desinflação esperada
- **Atividade**: correlação negativa com crescimento no curto prazo

---

## Alertas de Consistência (usados pelo Auditor)

1. **Juros reais > 10%**: histórico anormal — verificar se Selic ou IPCA estão atípicos
2. **Juros reais < -2%**: política de emergência — contexto de crise esperado
3. **Selic subindo + IPCA subindo**: risco de desancoragem de expectativas
4. **Selic caindo + IPCA acelerando**: possível afrouxamento prematuro

---

## Fontes de Dados

| Indicador | Fonte | Série |
|---|---|---|
| Selic Over (% a.a.) | Banco Central do Brasil | BCB série 432 |
| IPCA mensal (% a.m.) | BCB/IPEA | BCB série 433 ou IBGE SIDRA |
| IPCA-15 | BCB | BCB série 185 |
| Inflação esperada 12m | BCB Focus | Endpoint /ExpectativasMercadoAnuais |
