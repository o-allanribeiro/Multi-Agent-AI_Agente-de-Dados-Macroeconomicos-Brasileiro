# Base de Conhecimento Teórico — Coeficiente de Gini e Desigualdade

## O que é o Coeficiente de Gini?

O Coeficiente de Gini mede a desigualdade na distribuição de renda, variando de 0 (igualdade perfeita — todos ganham igual) a 1 (desigualdade máxima — uma pessoa detém toda a renda). Na prática, países com Gini acima de 0,40 são considerados muito desiguais. O Brasil historicamente fica entre 0,50 e 0,60 — entre os mais desiguais do mundo.

## Por que a desigualdade importa além da ética?

Desigualdade muito alta:
- Reduz mobilidade social (filhos de pobres tendem a permanecer pobres)
- Limita o mercado consumidor doméstico (pobres consomem mais proporcionalmente, então concentração de renda retira demanda)
- Eleva criminalidade e instabilidade política
- Reduz eficiência do capital humano (talentos de famílias pobres ficam subaproveitados)

## Enquadramento Teórico (para o LLM usar)

- **Simon Kuznets — Hipótese do U Invertido (1955)**: Propôs que a desigualdade primeiro aumenta durante a industrialização (saída do campo para a cidade) e depois cai com o amadurecimento econômico. O Brasil seguiu parcialmente essa trajetória — mas a queda foi muito mais lenta do que o esperado, sugerindo que fatores estruturais impedem a convergência automática.

- **Thomas Piketty — r > g (Capital no Século XXI, 2013)**: Quando a taxa de retorno do capital (r) supera a taxa de crescimento econômico (g), a riqueza se concentra inexoravelmente. O único contrapeso histórico foram guerras (destruição de capital) e políticas redistributivas deliberadas. No Brasil, o retorno da renda financeira (Selic elevada) garante r estruturalmente alto.

- **Celso Furtado — Origens Estruturais**: A desigualdade brasileira não é acidente — é resultado da estrutura colonial (concentração de terra, escravidão, ausência de reforma agrária). A herança do latifúndio e da sociedade de senhores e escravizados persiste nas estruturas de poder e renda. Sem mudança estrutural, políticas redistributivas são paliativos.

- **Ricardo Paes de Barros — Decomposição do Gini**: Análise empírica mostra que a queda do Gini brasileiro (de ~0,60 nos anos 1990 para ~0,52 em 2015) deveu-se a três fatores: (1) formalização do mercado de trabalho, (2) transferências diretas de renda (Bolsa Família), (3) valorização do salário mínimo. A partir de 2015, retrocesso parcial com a crise.

- **Framework ANOGI (Análise of Gini)**: Decompõe o Gini por fontes de renda (trabalho, capital, transferências) para identificar qual componente está puxando a desigualdade. Crucial para separar "desigualdade de renda do trabalho" de "desigualdade de riqueza acumulada".

## Contexto Brasil

- Gini histórico: ~0,535 (2022, IPEA) — queda expressiva dos ~0,600 dos anos 1990, mas ainda entre os 15 países mais desiguais do mundo
- Imposto de renda muito progressivo nos EUA (~37% no topo) vs. Brasil onde tributação de dividendos é baixa e Imposto de Renda é regressivo na prática
- Programas de transferência (Bolsa Família/Auxílio Brasil) respondem por ~20% da queda do Gini desde 2003
- Tributação patrimonial inexistente (IPTU/IPVA baixos, herança levemente tributada) preserva concentração de riqueza intergeracional

## Mapeamento

| Série | Fonte | Código |
|---|---|---|
| Gini Brasil (anual) | World Bank | BRA (indicador SI.POV.GINI) |
| Gini IPEA (PNAD/PNADC) | IPEADATA | PNADC12_GINI12 |
