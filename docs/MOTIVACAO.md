
---

# Motivação e Fundamentação do Projeto

## 1. Contexto Acadêmico e Justificativa

A análise de conjuntura econômica é uma disciplina que exige a coleta, o processamento e a interpretação de múltiplos indicadores. Tradicionalmente, este é um processo manual e intensivo em tempo, que exige navegar por diferentes portais de dados, baixar séries temporais e utilizar softwares estatísticos para gerar relatórios.

Este projeto nasce da interseção entre a ciência econômica e a fronteira da Inteligência Artificial. A ascensão dos Grandes Modelos de Linguagem (LLMs), como o Google Gemini, e de arquiteturas de agentes autônomos, como o LangGraph, oferece uma oportunidade inédita de automatizar e democratizar esse processo.

A motivação central é construir um agente de IA que atue como um "economista assistente", encapsulando o fluxo de trabalho de um analista:

-   **Compreensão:** Interpretar uma pergunta em linguagem natural.
-   **Planejamento:** Identificar quais dados são necessários para a resposta.
-   **Ação:** Buscar autonomamente esses dados nas fontes oficiais corretas.
-   **Análise:** Processar os dados brutos, extraindo insights chave.
-   **Síntese:** Apresentar a resposta de forma clara e objetiva, combinando texto e visualizações em uma interface interativa.

## 2. Detalhamento das Fontes de Dados e Indicadores

A confiabilidade de um agente de análise depende da qualidade de suas fontes. Por essa razão, este projeto se conecta exclusivamente a APIs de instituições reconhecidas.

### a. Banco Central do Brasil (BCB) - SGS

O Sistema Gerenciador de Séries Temporais (SGS) é o repositório mais vasto para dados macroeconômicos no Brasil.

-   **Indicador:** IPCA (Inflação)
    -   **O que é:** O Índice Nacional de Preços ao Consumidor Amplo, principal indicador de inflação do país.
    -   **Importância:** É a referência para a meta de inflação e influencia diretamente as decisões de política monetária.

-   **Indicador:** Taxa Selic (Meta)
    -   **O que é:** A taxa básica de juros da economia brasileira.
    -   **Importância:** Principal instrumento do BCB para controlar a inflação, afetando o crédito, o consumo e o investimento.

-   **Indicador:** Taxa de Desocupação (PNAD Contínua)
    -   **O que é:** Mede a porcentagem da força de trabalho que está desocupada, mas procurando emprego.
    -   **Importância:** É o principal termômetro do mercado de trabalho e da saúde da atividade econômica.

-   **Indicador:** Dólar (PTAX - Venda)
    -   **O que é:** A taxa de câmbio de referência calculada pelo BCB.
    -   **Importância:** Essencial para entender a vulnerabilidade externa, fluxos de capital e o impacto no comércio exterior.

### b. Instituto de Pesquisa Econômica Aplicada (IPEADATA)

O IPEADATA agrega uma vasta gama de séries econômicas e sociais, facilitando o acesso a indicadores específicos.

-   **Indicador:** Formação Bruta de Capital Fixo (FBCF)
    -   **O que é:** Mede o quanto as empresas aumentaram seus bens de capital (máquinas, equipamentos, construção).
    -   **Importância:** É o principal indicador do nível de investimento na economia, refletindo a confiança dos empresários e a expectativa de crescimento futuro.

### c. Banco Mundial (World Bank)

O Banco Mundial é uma fonte global de dados comparáveis entre países, essencial para análises estruturais.

-   **Indicador:** Coeficiente de Gini
    -   **O que é:** Uma medida padrão de desigualdade de renda, variando de 0 (igualdade perfeita) a 100 (desigualdade máxima).