
-----

# 🤖 Agente de IA para Análise de Dados Macroeconômicos do Brasil

## Resumo

Este projeto acadêmico de código aberto demonstra a construção de um agente de Inteligência Artificial autônomo, utilizando a arquitetura **LangGraph** e o poder do modelo de linguagem **Gemini** do Google. O objetivo é criar um assistente de pesquisa interativo, acessível via interface web, capaz de responder a perguntas em linguagem natural sobre a conjuntura econômica do Brasil, buscando dados de fontes oficiais, realizando análises e gerando visualizações de forma autônoma.

## Missão e Escopo

O propósito central deste agente é democratizar o acesso e a análise de dados macroeconômicos brasileiros, servindo como uma ferramenta prática e visual para estudantes, pesquisadores e analistas.

### Objetivo Principal

O agente é projetado para compreender perguntas formuladas em português, como:

> "Como está a inflação acumulada no Brasil este ano?"

> "Qual a trajetória da taxa Selic desde o início do governo atual?"

> "Gere um gráfico mostrando a evolução do Coeficiente de Gini."

A resposta final não se limita a um número, mas consiste em uma análise textual concisa acompanhada de uma visualização de dados (gráfico) relevante, tudo apresentado em uma interface de chat.

### Indicadores Centrais

Para garantir foco e eficácia, o escopo atual do agente cobre os seguintes indicadores fundamentais:

  - **Inflação**: Índice Nacional de Preços ao Consumidor Amplo (IPCA).
  - **Taxa de Juros**: Meta da Taxa Selic.
  - **Mercado de Trabalho**: Taxa de Desocupação (PNAD Contínua).
  - **Câmbio**: Taxa de Câmbio (Dólar PTAX - Venda).
  - **Investimento**: Formação Bruta de Capital Fixo (FBCF).
  - **Desigualdade**: Coeficiente de Gini.

### Fontes de Dados

A credibilidade do agente é sustentada pela utilização exclusiva de APIs de instituições oficiais, garantindo precisão e atualidade:

  - **Banco Central do Brasil (BCB)**: Via Sistema Gerenciador de Séries Temporais (SGS).
  - **Instituto de Pesquisa Econômica Aplicada (IPEADATA)**: Fonte para dados de investimento.
  - **Banco Mundial (World Bank)**: Fonte para o Coeficiente de Gini.

## Arquitetura e Tecnologias

O projeto é construído sobre uma arquitetura moderna que separa o backend (lógica do agente) do frontend (interface do usuário).

  - **Estrutura de Agente (LangGraph)**: Orquestra o fluxo de trabalho do agente (Planejar -\> Agir -\> Analisar -\> Plotar -\> Responder).
  - **Motor de Raciocínio (Google Gemini)**: Atua como o "cérebro" do agente, interpretando as perguntas, escolhendo as ferramentas e gerando as análises.
  - **Backend (FastAPI)**: Um servidor web Python que expõe o agente como uma API, permitindo a comunicação com a interface web.
  - **Frontend (HTML + Tailwind CSS + JavaScript)**: Uma interface de chat de página única que envia as perguntas do usuário para o servidor e exibe as respostas de forma interativa.

## Como Executar o Projeto

#### 1\. Clone o repositório

```bash
# Adicione aqui o comando 'git clone' quando o repositório estiver no GitHub
git clone https://github.com/o-allanribeiro/Multi-Agent-AI_Agente-de-Dados-Macroeconomicos-Brasileiro.git
cd o-allanribeiro/Multi-Agent-AI_Agente-de-Dados-Macroeconomicos-Brasileiro```

#### 2\. Crie e ative um ambiente virtual

```bash
# Crie o ambiente virtual
python -m venv venv
```

```bash
# Ative o ambiente (Windows - PowerShell)
.\venv\Scripts\Activate
```

```bash
# Ative o ambiente (macOS/Linux)
source venv/bin/activate
```

#### 3\. Instale as dependências

```bash
pip install -r requirements.txt
```

#### 4\. Configure suas chaves de API

  - Abra o novo arquivo `.env` e adicione sua chave da API do Google AI Studio no formato:
    ```
    GOOGLE_API_KEY="sua_chave_aqui"
    ```

#### 5\. Inicie o Servidor (Backend)

  - Navegue até a pasta `src`.
    ```bash
    cd src
    ```
  - Inicie o servidor FastAPI. Mantenha este terminal aberto.
    ```bash
    python -m uvicorn server:app
    ```

#### 6\. Abra a Interface (Frontend)

  - Na pasta principal do projeto, abra o arquivo `index.html` diretamente no seu navegador de preferência.

## Como Interagir com o Agente

A interface de chat estará pronta para receber suas perguntas. O agente responde melhor a perguntas diretas que contenham as palavras-chave dos indicadores que ele conhece.

Para uma lista detalhada de exemplos de perguntas que funcionam bem e para entender melhor as limitações atuais do agente, consulte o nosso guia:

### [➡️ Exemplos de Perguntas para Demonstração][def]

[def]: docs/PERGUNTAS_DEMO.md