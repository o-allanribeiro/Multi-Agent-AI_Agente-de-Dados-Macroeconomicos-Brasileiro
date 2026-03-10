# Base de Conhecimento Teórico — Inflação (IPCA / IPCA-15)

## O que é o IPCA?

O IPCA (Índice Nacional de Preços ao Consumidor Amplo) é o indicador oficial de inflação do Brasil, calculado pelo IBGE. Mede a variação de preços de uma cesta de produtos e serviços consumidos por famílias com renda entre 1 e 40 salários mínimos nas principais regiões metropolitanas. O **IPCA-15** é uma prévia, apurada dos dias 16 do mês anterior ao dia 15 do mês atual — chega antes e antecipa a tendência.

## Por que a inflação importa?

Inflação alta corrói o poder de compra: se os salários não sobem no mesmo ritmo, as pessoas ficam mais pobres em termos reais. Uma inflação muito baixa ou negativa (deflação) também é perigosa, pois indica que a economia está parada — as pessoas adiam compras esperando preços menores, o que derruba a produção e o emprego.

## Enquadramento Teórico (para o LLM usar)

- **Teoria da Inércia Inflacionária (Simonsen/PUC-Rio)**: No Brasil, a inflação tem componente inercial forte — empresas e trabalhadores reajustam preços/salários com base na inflação passada, criando um ciclo que se auto-alimenta. Foi exatamente esse mecanismo que o Plano Real (1994) quebrou com a URV (Unidade Real de Valor), que sincronizou preços relativos sem congelamento.

- **Regra de Taylor**: O Banco Central reage ao desvio da inflação em relação à meta ($\pi^* = 3\%$ em 2026) subindo a Selic. Se o IPCA está acima da meta, a Selic sobe para encarecer o crédito, frear o consumo e reduzir a pressão sobre preços.

- **Expectativas (Modelo de Metas)**: No regime de metas de inflação, tão importante quanto a inflação corrente são as expectativas futuras (Focus/BCB). Se agentes esperam inflação alta, cobram isso nos contratos — e a expectativa vira realidade.

- **Choques de Oferta vs. Demanda**: Alta de combustíveis (oferta) e aquecimento do mercado de trabalho (demanda) atuam de formas diferentes e exigem respostas distintas de política monetária.

## Contexto Brasil

- Meta de inflação 2026: 3% (± 1,5 p.p.)
- IPCA estruturalmente acima de pares emergentes dado o peso de preços administrados (~25% do índice: energia elétrica, combustíveis, planos de saúde)
- Taxa de repasse cambial (pass-through): desvalorização do Real eleva preços de importados e energia, pressionando o IPCA

## Mapeamento SGS/BCB

| Série | Código |
|---|---|
| IPCA variação mensal | 433 |
| IPCA-15 variação mensal | 188 |
| Expectativa IPCA 12 meses (Focus) | 13521 |
