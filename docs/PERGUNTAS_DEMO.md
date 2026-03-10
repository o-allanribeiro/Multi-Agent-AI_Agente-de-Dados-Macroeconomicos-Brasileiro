
---

# Exemplos de Perguntas para Demonstração do Agente

Esta lista explora **todo o potencial do pipeline Onda 3**: indicadores derivados (Fisher Identity,
câmbio real), estatísticas históricas (z-score, percentil, tendência OLS) e auditoria automática
de consistência macroeconômica (4 checks puramente em Python, sem LLM).

Organização por nível de complexidade e funcionalidades ativadas.

---

## 🔬 Nível 1 — Análise de Série Única com Contexto Histórico

Estas perguntas ativam o `stats_node` (z-score, percentil, tendência OLS) e o `auditor_node`.
A resposta inclui onde o valor atual está em relação à distribuição histórica completa.

| Pergunta | Série ativada | Checks do Auditor |
|---|---|---|
| Qual a trajetória do IPCA nos últimos 5 anos? Compare com a média histórica. | BCB 433 | Freshness, Outlier |
| Em que percentil histórico está a Selic atual? O nível atual é usual? | BCB 432 | Outlier, Taylor |
| O desemprego atual está acima ou abaixo da média histórica dos últimos 10 anos? | IBGE PNAD | Freshness, Outlier |
| Como o dólar hoje se compara com sua média dos últimos 3 anos? | BCB 1 | Outlier |
| A FBCF atual está em que posição dentro da distribuição histórica brasileira? | IPEA FBCF | Freshness |
| O Coeficiente de Gini atual representa melhora ou piora em relação ao histórico? | WB Gini | Freshness |

**Palavras-chave que ativam análise histórica:** `média histórica`, `percentil`, `usual`, `posição histórica`, `contexto`.

---

## 🧮 Nível 2 — Indicadores Derivados (Identidades Macroeconômicas)

Estas perguntas ativam o cálculo de indicadores que **não existem diretamente nas APIs**,
derivados de duas séries via identidades econômicas em Python (sem LLM).

### 2a. Juros Reais ex-post (Identidade de Fisher)

Fórmula: `juros_reais = (1 + Selic_a.a.) / (1 + IPCA_acum_12m) − 1`

Ativar automático: qualquer pergunta com as palavras `juro real`, `juros reais`, `taxa real`,
`selic real`, `fisher`, `juro efetivo real`.

```
Qual o juro real no Brasil hoje? Como se compara com a média histórica?
Mostre a série histórica dos juros reais ex-post no Brasil desde 2020.
A taxa de juro real atual está em território contracionista ou expansionista?
Qual a trajetória dos juros reais durante o ciclo de aperto de 2022-2023?
Com Selic a 13,75% e IPCA acumulado, qual foi o juro real de equilíbrio?
```

O `auditor_node` automaticamente verifica se o resultado está no intervalo histórico BR:
- 🔴 < -3%: juros reais negativos (inflação > Selic)
- 🟢 -3% a 18%: faixa historicamente razoável
- 🔴 > 18%: patamar crítico (associado a crises)

### 2b. Câmbio Real Bilateral Simplificado

Fórmula: `cambio_real_idx = cambio_nominal × (IPCA_acum / IPCA_base)`, base 100.

Ativar automático: palavras `câmbio real`, `cambio real`, `poder de compra do real`,
`taxa real de câmbio`.

```
Como está o câmbio real bilateral Brasil-EUA nos últimos 3 anos?
Mostre o poder de compra do real em relação ao dólar corrigido pelo IPCA.
O real está apreciado ou depreciado em termos reais comparado a 2020?
```

---

## 📊 Nível 3 — Multi-Indicador (Curva de Phillips, Regra de Taylor)

Estas perguntas ativam múltiplas ferramentas (`next_tool` loop), stats para cada série
e o check de consistência Selic×IPCA do Auditor.

### Curva de Phillips (Inflação × Desemprego)

```
Analise a relação entre IPCA e desemprego no Brasil nos últimos 5 anos.
Existe trade-off inflação-desemprego visível nos dados recentes do Brasil?
Como se moveu a curva de Phillips brasileira desde a pandemia?
Compare a aceleração do IPCA com a queda da desocupação desde 2021.
```

### Regra de Taylor (Selic × IPCA)

```
Compare a Selic com o IPCA nos últimos 3 anos sob a ótica da Regra de Taylor.
A política monetária atual está sendo contracionista? Mostre Selic e IPCA juntos.
Qual o diferencial real entre Selic e IPCA desde o choque inflacionário de 2021?
A Selic está adequada para conter a inflação atual? Analise a Regra de Taylor.
```

### Aceleração do Investimento (Harrod-Domar / Solow)

```
Como o investimento (FBCF) responde às variações do PIB nos últimos 10 anos?
A taxa de investimento brasileira é suficiente para crescimento sustentado?
```

---

## 🏛️ Nível 4 — Perguntas de Alta Complexidade (Todas as Capacidades)

Estas perguntas ativam o pipeline completo: múltiplas séries, derivados, stats avançadas
e auditoria de consistência simultânea.

```
Qual é o status atual da política monetária brasileira?
Analise Selic, IPCA e juro real — o BCB está sendo ortodoxo suficiente?

Faça um diagnóstico macroeconômico do Brasil em 2025:
busque desemprego, inflação, Selic e câmbio.

Compare o ciclo de juros de 2022-2023 com o atual.
Mostre Selic histórica e juros reais nos dois períodos.

O Brasil está em armadilha de liquidez? Analise juro real,
IPCA e desemprego dos últimos 3 anos.

Com câmbio acima de R$ 5,00 e IPCA pressionado, o BCB deveria
manter ou elevar a Selic? Analise os dados e a Regra de Taylor.
```

---

## 📋 Mapa de Funcionalidades → Perguntas

| Funcionalidade Onda 3 | Pergunta que a ativa |
|---|---|
| Z-score e percentil (`stats_node`) | "está em que nível histórico?", "é usual?", "compare com a média" |
| Tendência OLS 3 meses (`stats_node`) | "tendência recente", "está subindo ou caindo?" |
| Fisher Identity (`derived.py`) | "juro real", "juros reais", "taxa real de juros" |
| Câmbio Real (`derived.py`) | "câmbio real", "poder de compra do real" |
| Flag Freshness (`auditor_node`) | qualquer série com dados antigos |
| Flag Outlier (`auditor_node`) | valores com z-score > 2.5 |
| Flag Juros Reais (`auditor_node`) | quando derivado `juros_reais` é calculado |
| Check Taylor (`auditor_node`) | quando Selic + IPCA são ambos coletados |

---

## ❌ Limitações Conhecidas

- **Dados externos ao Brasil:** O agente cobre apenas indicadores brasileiros (BCB, IBGE, IPEA, Banco Mundial para BR).
- **Séries não mapeadas:** Indicadores não cadastrados nas ferramentas não serão encontrados.
- **Causalidade:** O agente descreve padrões e consistências, mas não atribui causalidade econométrica formal.
- **Projeções:** O agente trabalha com dados históricos realizados, não faz previsões.