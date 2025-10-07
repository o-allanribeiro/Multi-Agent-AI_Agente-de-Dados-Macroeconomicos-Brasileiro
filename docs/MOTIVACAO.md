Claro! Aqui está o texto formatado em Markdown, ideal para um arquivo `README.md` no GitHub, por exemplo.

---

# Motivação e Fundamentação do Projeto

## 1. Contexto Acadêmico e Justificativa

A análise de conjuntura econômica é uma disciplina que exige a coleta, o processamento e a interpretação de múltiplos indicadores macroeconômicos. Tradicionalmente, este é um processo manual e intensivo em tempo, realizado por analistas que precisam navegar por diferentes portais de dados, baixar séries temporais e utilizar softwares estatísticos para gerar visualizações e relatórios. A complexidade aumenta quando consideramos a necessidade de cruzar informações e manter as análises constantemente atualizadas.

Este projeto nasce da interseção entre a ciência econômica e a fronteira da Inteligência Artificial. A ascensão dos Grandes Modelos de Linguagem (LLMs), como o Google Gemini, e de arquiteturas de agentes autônomos, como o LangGraph, oferece uma oportunidade inédita de automatizar e democratizar esse processo.

A motivação central é construir um agente de IA que atue como um "economista assistente", encapsulando o fluxo de trabalho de um analista:

* **Compreensão:** Interpretar uma pergunta em linguagem natural.
* **Planejamento:** Identificar quais dados são necessários para responder à pergunta.
* **Ação:** Buscar autonomamente esses dados nas fontes oficiais corretas.
* **Análise:** Processar os dados brutos, extraindo estatísticas chave.
* **Síntese:** Apresentar a resposta de forma clara e objetiva, combinando texto e visualizações.

Ao desenvolver tal ferramenta de forma aberta e acadêmica, o projeto visa não apenas a criar uma aplicação prática, mas também a servir como um material de estudo sobre a aplicação de IA generativa em domínios especializados.

## 2. Detalhamento das Fontes de Dados e Indicadores

A confiabilidade de um agente de análise de dados depende inteiramente da qualidade e da procedência de suas fontes. Por essa razão, este projeto se conecta exclusivamente a APIs de instituições públicas brasileiras, que são a referência para o mercado e a academia.

### a. Banco Central do Brasil (BCB) - Sistema Gerenciador de Séries Temporais (SGS)

O SGS é o repositório mais vasto e utilizado para dados macroeconômicos e financeiros no Brasil. A interação se dará através da biblioteca `python-bcb`.

* **Indicador: IPCA (Inflação)**
    * **O que é:** O Índice Nacional de Preços ao Consumidor Amplo é o principal indicador de inflação do país. Mede a variação de preços de uma cesta de produtos e serviços consumida pelas famílias com rendimento de 1 a 40 salários mínimos.
    * **Importância:** É a referência para a meta de inflação perseguida pelo BCB e influencia diretamente as decisões de política monetária (taxa Selic).

* **Indicador: Taxa Selic (Meta)**
    * **O que é:** A taxa básica de juros da economia brasileira, definida pelo Comitê de Política Monetária (COPOM) a cada 45 dias.
    * **Importância:** É o principal instrumento do BCB para controlar a inflação. Suas alterações afetam todas as outras taxas de juros do país, influenciando o crédito, o consumo e o investimento.

* **Indicador: Taxa de Desocupação (PNAD Contínua)**
    * **O que é:** Mede a porcentagem da força de trabalho que está desocupada, mas procurando ativamente por emprego. Os dados são coletados pelo IBGE, mas a série histórica ajustada sazonalmente é facilmente acessível pelo BCB.
    * **Importância:** É o principal termômetro do mercado de trabalho, refletindo a saúde da atividade econômica e o bem-estar social.

### b. Instituto de Pesquisa Econômica Aplicada (IPEADATA)

O IPEADATA é uma base de dados mantida pelo IPEA, que agrega uma vasta gama de séries econômicas e sociais de diversas fontes, facilitando o acesso.

* **Indicador: PIB (Produto Interno Bruto)**
    * **O que é:** A soma de todos os bens e serviços finais produzidos no país em um determinado período.
    * **Importância:** É a medida mais abrangente da atividade econômica. A variação do PIB indica o crescimento ou a recessão da economia.

### c. Instituto Brasileiro de Geografia e Estatística (IBGE) - SIDRA

O SIDRA é o sistema que disponibiliza os dados de todas as pesquisas do IBGE. Sua API é extremamente poderosa, permitindo um alto grau de granularidade.

* **Uso Potencial (Exemplo):** Embora os indicadores centrais sejam acessados via BCB e IPEA por simplicidade, a API do IBGE seria a ferramenta para perguntas mais detalhadas, como: "Qual foi a inflação do grupo 'Alimentação e Bebidas' no último mês?". Isso demonstra o potencial de expansão do agente para consultas mais complexas no futuro.