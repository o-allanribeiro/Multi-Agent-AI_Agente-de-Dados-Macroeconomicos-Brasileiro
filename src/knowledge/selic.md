# Base de Conhecimento Teórico — Taxa Selic

## O que é a Selic?

A Taxa Selic (Sistema Especial de Liquidação e de Custódia) é a taxa básica de juros da economia brasileira, definida pelo COPOM (Comitê de Política Monetária do Banco Central) a cada 45 dias. Ela remunera os títulos públicos federais e serve de referência para todas as outras taxas de juros da economia — crédito pessoal, financiamentos, CDBs, etc.

## Por que a Selic influencia tudo?

Quando o BCB sobe a Selic, o crédito fica mais caro → consumo cai → empresas investem menos → pressão sobre preços recua → inflação cede. O custo é crescimento econômico mais lento e desemprego mais alto no curto prazo. É o dilema clássico de política monetária: estabilidade de preços vs. atividade econômica.

## Enquadramento Teórico (para o LLM usar)

- **Regra de Taylor (1993)**: Relaciona a taxa de juros nominal à inflação e ao nível de atividade:
  `Selic = Juro neutro + Inflação + α × (Inflação − Meta) + β × (PIB − PIB potencial)`
  Se α > 0 e inflação supera a meta, o BCB deve subir a Selic mais do que 1:1 (Princípio de Taylor).

- **Taxa Neutra (r*)**: É a Selic que nem estimula nem restringe a economia quando a inflação está na meta. No Brasil, estimativas variam entre 4,5% e 6% ao ano em termos reais — das mais altas do mundo, reflexo de incerteza fiscal e prêmio de risco estrutural.

- **Milton Friedman e o Monetarismo**: "A inflação é sempre e em qualquer lugar um fenômeno monetário." Controlar a expansão da base monetária seria suficiente. A prática brasileira mostra que, dada a indexação histórica, apenas controle monetário não basta — daí a combinação com o regime de metas.

- **Mário Henrique Simonsen — Teoria dos Jogos na Inflação**: Nenhum agente quer ser o primeiro a parar de reajustar preços. A Selic alta força a "cooperação" ao tornar o crédito caro demais para continuar o ciclo de repasses.

## Contexto Brasil

- Selic historicamente elevada versus emergentes comparáveis (México, Chile, Colômbia)
- Juro real (Selic − IPCA esperado) acima de 7% a.a. em 2025-2026: nível restritivo severo
- Efeito: inibe investimento (FBCF) e eleva custo da dívida pública
- COPOM comunica decisões com forward guidance — mercado forma expectativas para ciclos inteiros

## Mapeamento SGS/BCB

| Série | Código |
|---|---|
| Selic meta (% a.a.) | 432 |
| Selic efetiva (% a.d.) | 11 |
| Juro real ex-ante implícito (Focus) | 4466 |
