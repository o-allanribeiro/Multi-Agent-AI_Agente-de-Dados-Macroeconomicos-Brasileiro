# Fundamento Científico — Agente de Dados Macroeconômicos Brasileiros

> **Escopo:** Graduação em Ciências Econômicas — referências de Econometria I/II,
> Macroeconomia Aberta, Teoria Monetária e Economia do Setor Público.  
> **Objetivo:** documentar os modelos matemáticos que fundamentam cada camada do agente.

---

## Índice

1. [Estatística Descritiva de Séries Temporais](#1-estatística-descritiva-de-séries-temporais)
2. [Detecção de Tendência via Regressão OLS](#2-detecção-de-tendência-via-regressão-ols)
3. [Z-score e Percentil — Posição Histórica](#3-z-score-e-percentil--posição-histórica)
4. [Identidade de Fisher — Juros Reais](#4-identidade-de-fisher--juros-reais)
5. [Regra de Taylor — Política Monetária](#5-regra-de-taylor--política-monetária)
6. [Curva de Phillips — Inflação × Desemprego](#6-curva-de-phillips--inflação--desemprego)
7. [Taxa de Câmbio Real — Paridade de Poder de Compra](#7-taxa-de-câmbio-real--paridade-de-poder-de-compra)
8. [Modelo de Crescimento de Solow (FBCF e PIB)](#8-modelo-de-crescimento-de-solow-fbcf-e-pib)
9. [Lei de Okun — Desemprego × Produto](#9-lei-de-okun--desemprego--produto)
10. [Consistência Macroeconômica — Camada Auditor](#10-consistência-macroeconômica--camada-auditor)
11. [Mapeamento Modelo → Código](#11-mapeamento-modelo--código)
12. [Referências Bibliográficas](#12-referências-bibliográficas)

---

## 1. Estatística Descritiva de Séries Temporais

### Fundamentação (Wooldridge, cap. 10; Gujarati, cap. 12)

Antes de qualquer modelagem, um analista deve calcular as estatísticas descritivas da série para entender distribuição, localização e dispersão. O `stats_node` (Onda 3) implementa exatamente esse passo, comumente ensinado como **Análise Exploratória de Dados (EDA)** em cursos de Econometria.

### Médias em janelas temporais

Para uma série $\{y_t\}_{t=1}^{T}$, a média aritmética em janela $k$ anos é:

$$\bar{y}_{[T-k, T]} = \frac{1}{N_k} \sum_{t \in [T-k, T]} y_t$$

Onde $N_k$ é o número de observações na janela.

O agente calcula as janelas de **1, 3 e 5 anos**, além da média histórica completa ($\bar{y}_{full}$). Essa estratificação permite comparar o valor atual com regimes de curto, médio e longo prazo separadamente.

```python
# src/agente/nodes/stats.py
cutoff_1y = now - pd.DateOffset(years=1)
mean_1y   = float(s[s.index >= cutoff_1y].mean())
```

### Desvio-padrão e variância

$$\sigma^2 = \frac{1}{N-1} \sum_{t=1}^{T} (y_t - \bar{y})^2 \qquad (\text{estimador não-viesado de Bessel})$$

O desvio-padrão $\sigma$ é usado como referência de "amplitude normal" da série.

---

## 2. Detecção de Tendência via Regressão OLS

### Fundamentação (Wooldridge, cap. 3; Greene, cap. 2)

O modelo de regressão simples contra o tempo é a forma mais elementar de tendência linear estimada por Mínimos Quadrados Ordinários (OLS):

$$y_t = \alpha + \beta \cdot t + \varepsilon_t, \qquad \varepsilon_t \sim \mathcal{N}(0, \sigma^2)$$

O coeficiente $\hat{\beta}$ é o estimador OLS da tendência por unidade de tempo. Por Gauss-Markov, é BLUE (melhor estimador linear não-viesado) quando $\varepsilon_t$ são i.i.d.

### Implementação no agente

O `stats_node` usa `numpy.polyfit(degree=1)` na janela de 3 meses para estimar $\hat{\beta}$:

```python
# src/agente/nodes/stats.py
x = np.arange(len(window))
slope, _ = np.polyfit(x, window.values, 1)
```

A decisão é classificada como:
- **"alta"**: $\hat{\beta} > 0.05 \cdot \sigma$
- **"baixa"**: $\hat{\beta} < -0.05 \cdot \sigma$
- **"estável"**: $|\hat{\beta}| \leq 0.05 \cdot \sigma$

O limiar $0.05\sigma$ é calibrado para separar ruído estatístico de tendência economicamente relevante, seguindo a prática de análise de conjuntura do BCB (cf. *Notas de Política Monetária*, 2023).

---

## 3. Z-score e Percentil — Posição Histórica

### Fundamentação (Gujarati, cap. 4; Kennedy, *A Guide to Econometrics*)

O **z-score** padroniza uma observação em relação à distribuição histórica da variável, expressando-a em unidades de desvio-padrão:

$$z_t = \frac{y_t - \bar{y}}{\sigma}$$

**Interpretação:** $z > 2$ indica que o valor está 2 desvios acima da média — evento esperado em menos de 2,5% das observações numa distribuição normal.

O **percentil rank** reporta em que faixa da distribuição empírica histórica o valor atual se encontra:

$$\text{percentile\_rank}(y_T) = \frac{|\{y_t : y_t \leq y_T\}|}{N} \times 100$$

```python
# src/agente/nodes/stats.py
zscore_latest    = (latest_value - mean_full) / std_full
percentile_rank  = round(float(stats.percentileofscore(s.values, latest_value)), 1)
```

### Por que isso importa para a análise macroeconômica

Um IPCA de 6% isoladamente é ambíguo. Mas "está no percentil 85 da série histórica" e "z-score = 1,8" quantifica que é um nível elevado para os padrões brasileiros, fornecendo ao LLM e ao analista uma referência objetiva sem depender de julgamento subjetivo.

---

## 4. Identidade de Fisher — Juros Reais

### Fundamentação (Fisher, 1930; Blanchard & Fischer, cap. 4)

A **Equação de Fisher** é uma das identidades mais fundamentais da teoria monetária:

$$1 + r = \frac{1 + i}{1 + \pi}$$

Onde:
- $r$ = taxa de juros real (poder de compra)
- $i$ = taxa de juros nominal (Selic % a.a.)
- $\pi$ = inflação acumulada no período (IPCA acumulado 12 meses)

Isolando $r$:

$$r = \frac{1 + i}{1 + \pi} - 1$$

**Aproximação linear** (válida para taxas baixas): $r \approx i - \pi$

O agente usa a **fórmula exata** (não a aproximação) para máxima precisão, especialmente relevante no contexto brasileiro com taxas historicamente elevadas.

### Implementação — IPCA acumulado 12 meses

O IPCA é divulgado como variação **mensal**. Para o denominador da equação de Fisher, é necessário calcular o acumulado em 12 meses via produto composto:

$$\Pi_{12} = \prod_{k=1}^{12}(1 + \pi_{t-k}) - 1$$

```python
# src/tools/derived.py
ipca_dec    = df[ipca_col] / 100            # converte % para decimal
ipca_12m    = (1 + ipca_dec).rolling(12).apply(
                  lambda x: x.prod(), raw=True
              ) - 1                          # acumulado 12 meses
selic_aa    = df[selic_col] / 100           # % a.a. para decimal
juros_reais = (1 + selic_aa) / (1 + ipca_12m) - 1
```

### Contexto histórico (série ex-post, BCB 432/433)

| Período | Juro real médio (% a.a.) | Regime |
|---|---|---|
| 1999–2003 | ~14% | Estabilização pós-Real, âncora de câmbio |
| 2004–2013 | ~5–8% | Crescimento com inflação controlada |
| 2014–2016 | ~6–9% | Recessão + ajuste fiscal |
| 2017–2019 | ~3–5% | Recuperação com Selic em queda |
| 2020 | ~-1% | Emergência pandemia, Selic a 2% |
| 2021–2023 | ~6–9% | Ciclo de alta do COPOM |
| 2024–2026 | ~7–9% | Política monetária restritiva |

---

## 5. Regra de Taylor — Política Monetária

### Fundamentação (Taylor, 1993; Barro & Gordon, 1983)

John Taylor propôs uma **regra de política monetária** que descreve como o banco central deveria ajustar a taxa de juros nominal em resposta a desvios da inflação da meta e do produto do seu nível potencial:

$$i_t = r^* + \pi_t + \phi_\pi(\pi_t - \pi^*) + \phi_y \tilde{y}_t$$

Onde:
- $i_t$ = taxa de juros nominal (Selic)
- $r^*$ = taxa natural de juros real (~4,5% no Brasil — estimativas BCB, 2024)
- $\pi_t$ = inflação observada (IPCA)
- $\pi^*$ = meta de inflação (3% em 2026)
- $\phi_\pi$ = peso da inflação (tipicamente 1,5 — **Princípio de Taylor**: $\phi_\pi > 1$)
- $\phi_y$ = peso do hiato do produto (tipicamente 0,5)
- $\tilde{y}_t = (y_t - y_t^*)/y_t^*$ = hiato do produto

**Princípio de Taylor:** $\phi_\pi > 1$ é condição necessária para estabilidade. Se o banco central aumenta os juros nominais menos que 1% para cada 1% de inflação, os juros reais caem com a inflação — o que amplifica ao invés de combater o problema.

### Uso no auditor (Onda 3)

O `auditor_node` implementa uma versão simplificada da Regra de Taylor como regra de consistência:

```python
# src/agente/nodes/auditor.py
# Se Selic caindo E IPCA acelerando → violação da Regra de Taylor
if selic_trend == "baixa" and ipca_trend == "alta":
    flags.append("⚠️ Selic em queda com IPCA acelerando: possível afrouxamento prematuro")
```

---

## 6. Curva de Phillips — Inflação × Desemprego

### Fundamentação (Phillips, 1958; Friedman, 1968; Mankiw, cap. 14)

A **Curva de Phillips** original documentou empiricamente a relação inversa entre inflação salarial e desemprego no Reino Unido (1861–1957):

$$\pi_t = -\gamma \cdot (u_t - u^*) + \varepsilon_t, \qquad \gamma > 0$$

Onde $u^*$ é a **NAIRU** (*Non-Accelerating Inflation Rate of Unemployment*) — a taxa de desemprego compatível com inflação estável.

**Curva de Phillips Aceleracionista (Friedman-Phelps):** Incorpora expectativas:

$$\pi_t = \pi_t^e - \gamma(u_t - u^*) + \text{choques de oferta}$$

Se as expectativas são adaptativas $\pi_t^e = \pi_{t-1}$, a curva se torna:

$$\Delta\pi_t = -\gamma(u_t - u^*)$$

### No contexto brasileiro

A NAIRU estimada para o Brasil oscila entre 8–10% (BCB, *Relatório de Inflação*, 2024), muito superior a economias desenvolvidas (~4–5%), refletindo:
- Alta informalidade (~40% dos ocupados)
- Baixa mobilidade geográfica
- Descompasso entre qualificação disponível e demandada

O agente correlaciona automaticamente Selic, IPCA e Desocupação quando esses indicadores são consultados em conjunto, fornecendo ao LLM o contexto da Curva de Phillips para a análise.

---

## 7. Taxa de Câmbio Real — Paridade de Poder de Compra

### Fundamentação (Cassel, 1916; Rogoff, 1996; Obstfeld & Rogoff, cap. 4)

A **Paridade do Poder de Compra (PPP)** postula que, no longo prazo, o câmbio real converge para um valor de equilíbrio. A **taxa de câmbio real bilateral** (Brasil–EUA) é:

$$q_t = E_t \cdot \frac{P_t^{BR}}{P_t^{US}}$$

Onde:
- $E_t$ = taxa de câmbio nominal (R$/US$, PTAX)
- $P_t^{BR}$ = nível de preços no Brasil (IPCA indexado)
- $P_t^{US}$ = nível de preços nos EUA (CPI indexado)

O **índice de câmbio real** (base 100) implementado em `derived.py` simplifica para:

$$q_t^{idx} = \frac{E_t \cdot P_t^{BR}}{E_0 \cdot P_0^{BR}} \times 100$$

Onde $t=0$ é o período base. Isso permite visualizar se o Real está apreciado ou depreciado em termos reais em relação ao período de referência, independente do nível nominal.

```python
# src/tools/derived.py
ipca_base = (1 + ipca_dec).cumprod()
cambio_real_idx = (dolar / dolar.iloc[0]) * (ipca_base / ipca_base.iloc[0]) * 100
```

### Pass-through cambial

Empiricamente, uma desvalorização de 10% no câmbio eleva o IPCA em ~1–1,5% no prazo de 12 meses no Brasil (coeficiente de pass-through β ≈ 0,10–0,15), conforme estimativas em:

> Goldfajn, I.; Werlang, S. R. C. "The Pass-through from Depreciation to Inflation: A Panel Study." *PUC-Rio Working Paper*, 2000.

---

## 8. Modelo de Crescimento de Solow (FBCF e PIB)

### Fundamentação (Solow, 1956; Mankiw, Romer & Weil, 1992)

O modelo neoclássico de Solow descreve a dinâmica do capital e do produto:

$$\dot{k} = s \cdot f(k) - (n + \delta) \cdot k$$

Onde:
- $k = K/L$ = capital per capita
- $s$ = taxa de poupança/investimento (≈ FBCF/PIB)
- $f(k) = k^\alpha$ = produto per capita (função Cobb-Douglas com $\alpha \approx 0,33$)
- $n$ = taxa de crescimento populacional
- $\delta$ = taxa de depreciação do capital (~0,05)

No **estado estacionário** ($\dot{k}=0$):

$$k^* = \left(\frac{s}{n + \delta}\right)^{\frac{1}{1-\alpha}}$$

**Implicação para o Brasil (PIB e FBCF):**

Com FBCF/PIB ≈ 16–18% e $n + \delta \approx 7\%$, o capital per capita converge para um estado estacionário bem abaixo do potencial. Para crescer 3% a.a. de forma sustentada, o Brasil precisaria de FBCF/PIB ≈ 23–25% (cálculo baseado nas estimativas de Bonelli & Fonseca, *IPEA Discussion Paper*, 1998).

O agente usa isso no `analysis_node`: quando a pergunta envolve FBCF, o contexto teórico de Solow (injetado via `knowledge/fbcf_pib.md`) orienta a análise sobre "por que o Brasil cresce menos que o potencial".

---

## 9. Lei de Okun — Desemprego × Produto

### Fundamentação (Okun, 1962; Ball, Leigh & Loungani, 2013)

Arthur Okun documentou empiricamente que variações na taxa de desemprego estão correlacionadas com variações no PIB:

$$\Delta y_t = -\omega \cdot \Delta u_t + \varepsilon_t$$

A estimativa original para os EUA era $\omega \approx 2$. Para o Brasil, estimativas de Lemos (2014) sugerem $\omega \approx 1,5$:

> "Para cada 1 p.p. de queda no desemprego abaixo do nível natural, o PIB cresce ~1,5 p.p. acima do potencial."

**Versão em gap:**

$$\tilde{y}_t = -\omega \cdot (u_t - u^*)$$

Esta relação é utilizada no `analysis_node` quando a consulta envolve simultaneamente Desocupação e PIB, permitindo ao agente calcular implicitamente o "custo de desemprego" em termos de produto perdido.

---

## 10. Consistência Macroeconômica — Camada Auditor

### Fundamentação (Blanchard, *Macroeconomics*, cap. 22; BCB, *Manual de Auditoria*)

O `auditor_node` implementa **identidades e restrições de consistência macroeconômica** derivadas de princípios de gradua ção:

### Cheque 1 — Frescor dos dados (freshness)

Dado com `lag > 90 dias` implica que o analista está vendo uma "fotografia antiga". Diretrizes de boas práticas exigem disclosure explícito:

```
lag_days > 90  → ℹ️ aviso
lag_days > 365 → ⚠️ crítico
```

### Cheque 2 — Outliers por z-score

Se $|z_t| \geq 2.5$, o valor está a mais de 2,5 desvios padrão da média histórica. Pela distribuição normal, isso ocorre em menos de 1,2% das observações. Economicamente, tal leitura exige explicação — crise, mudança metodológica ou erro de coleta.

```python
if abs(zscore) >= 2.5:
    flag = f"🔴 OUTLIER [{col}]: z={zscore:.1f}, percentil={pctrank:.0f}%"
```

### Cheque 3 — Juros reais fora do intervalo histórico

Baseado na série histórica BCB (432/433) desde 1999:
- Mínimo razoável: $-3\%$ a.a. (observado em 2020, pandemia)
- Máximo razoável: $+18\%$ a.a. (pico na estabilização)
- Média histórica: $+6,5\%$ a.a.

Qualquer valor fora desse envelope é sinalizado como anomalia.

### Cheque 4 — Consistência Selic × IPCA (Regra de Taylor)

A Regra de Taylor implica que, em condições ortodoxas de política monetária:
- $\Delta i > 0$ quando $\pi > \pi^*$ (Selic sobe quando inflação supera meta)
- $\Delta i < 0$ quando $\pi < \pi^*$ (Selic cai quando inflação está abaixo da meta)

Violações desta relação sinalizam **risco de desancoragem de expectativas** ou **afrouxamento prematuro**, conforme amplamente documentado por Galí & Gertler (1999).

---

## 11. Mapeamento Modelo → Código

| Modelo Econômico | Onde é usado no código | Arquivo |
|---|---|---|
| Média histórica (EDA) | `_compute_series_stats()` | `nodes/stats.py` |
| Desvio-padrão de Bessel | `std_full = s.std()` | `nodes/stats.py` |
| Z-score | `zscore_latest = (v - mean) / std` | `nodes/stats.py` |
| Percentil rank (ECDF) | `scipy.stats.percentileofscore()` | `nodes/stats.py` |
| Regressão OLS (tendência) | `np.polyfit(x, y, deg=1)` | `nodes/stats.py` |
| Identidade de Fisher | `(1+Selic)/(1+IPCA_12m)−1` | `tools/derived.py` |
| IPCA acumulado 12m | `rolling(12).apply(prod)` | `tools/derived.py` |
| Taxa de câmbio real | `(E_t/E_0)×(P_BR_t/P_BR_0)×100` | `tools/derived.py` |
| Regra de Taylor (simplif.) | Checks Selic↑↓ vs IPCA aceleração | `nodes/auditor.py` |
| z-score outlier check | `\|z\| ≥ 2.5` | `nodes/auditor.py` |
| Freshness (defasagem) | `lag_days > 90/365` | `nodes/auditor.py` |
| Teoria inercial (Simonsen)| Contexto no prompt de análise | `knowledge/ipca.md` |
| Modelo Solow | Contexto no prompt de análise | `knowledge/fbcf_pib.md` |
| Curva de Phillips | Contexto no prompt de análise | `knowledge/desocupacao.md` |
| PPP / Pass-through | Contexto no prompt de análise | `knowledge/dolar.md` |
| Kuznets / r>g (Piketty) | Contexto no prompt de análise | `knowledge/gini.md` |

---

## 12. Referências Bibliográficas

### Econometria e Estatística

| Autor | Obra | Edição | Capítulos relevantes |
|---|---|---|---|
| Wooldridge, J. M. | *Introdução à Econometria* | 5ª, Cengage | Cap. 2–3 (OLS), 10–12 (séries temporais) |
| Gujarati, D. N.; Porter, D. C. | *Econometria Básica* | 5ª, McGraw-Hill | Cap. 4 (Normalidade), 12–17 (séries temporais) |
| Greene, W. H. | *Econometric Analysis* | 8ª, Pearson | Cap. 2–5 (OLS, GLS) |
| Hamilton, J. D. | *Time Series Analysis* | Princeton UP | Cap. 3 (ARMA), 11 (VAR) |
| Enders, W. | *Applied Econometric Time Series* | 4ª, Wiley | Cap. 2 (ARIMA), 5 (cointegração) |
| Kennedy, P. | *A Guide to Econometrics* | 6ª, Blackwell | Introdução conceitual |

### Teoria Macroeconômica

| Autor | Obra | Ano | Contribuição |
|---|---|---|---|
| Fisher, I. | *The Theory of Interest* | 1930 | Equação de Fisher: juros nominais vs. reais |
| Taylor, J. B. | *Discretion Versus Policy Rules* | 1993 | Regra de Taylor para política monetária |
| Phillips, A. W. | *The Relation Between Unemployment and Rate of Change of Money Wage Rates* | 1958 | Curva de Phillips original |
| Friedman, M. | *The Role of Monetary Policy* | 1968 | NAIRU, Curva de Phillips aceleracionista |
| Okun, A. M. | *Potential GNP: Its Measurement and Significance* | 1962 | Lei de Okun — relação desemprego-produto |
| Solow, R. | *A Contribution to the Theory of Economic Growth* | 1956 | Modelo de crescimento neoclássico |
| Blanchard, O. | *Macroeconomics* | 8ª, Pearson | Síntese moderna IS-LM, política monetária |
| Mankiw, N. G. | *Macroeconomia* | 9ª, LTC | Cap. 9 (crescimento), 14 (inflação/desemprego) |
| Obstfeld, M.; Rogoff, K. | *Foundations of International Macroeconomics* | MIT Press | PPP, câmbio real |

### Pensamento Econômico Brasileiro

| Autor | Obra | Ano | Contribuição |
|---|---|---|---|
| Simonsen, M. H. | *Inflação: Gradualismo x Tratamento de Choque* | 1970 | Teoria da inflação inercial brasileira |
| Arida, P.; Resende, A. L. | *Inertial Inflation and Monetary Reform* | 1985 | Fundamentos do Plano Real (URV) |
| Furtado, C. | *Formação Econômica do Brasil* | 1959 | Origens estruturais da desigualdade e subdesenvolvimento |
| Goldfajn, I.; Werlang, S. | *The Pass-through from Depreciation to Inflation* | 2000 | Pass-through cambial para o IPCA no Brasil |
| Banco Central do Brasil | *Relatório de Inflação* (trimestral) | 1999–2026 | Séries BCB, estimativas NAIRU, taxa neutra |
| IPEA | *Carta de Conjuntura* (trimestral) | 2010–2026 | Contexto histórico das séries utilizadas |

### Engenharia de Agentes e LLM

| Autor | Obra | Ano |
|---|---|---|
| Chase, H. et al. | *LangChain* (open source) | 2022+ |
| Pregel, G. (Google) | *LangGraph: Building Stateful Multi-Actor Applications* | 2024 |
| Gemini Team, Google | *Gemini: A Family of Highly Capable Multimodal Models* | 2024 |
| Yao, S. et al. | *ReAct: Synergizing Reasoning and Acting in Language Models* | 2023 |
| Wei, J. et al. | *Chain-of-Thought Prompting Elicits Reasoning in LLMs* | 2022 |
