Com certeza\! Aqui está o seu texto corrigido, aprimorado e formatado em Markdown para ser usado em um `README.md` no GitHub, por exemplo.

-----

# Agente de IA para Análise de Dados Macroeconômicos do Brasil

## Resumo

Este projeto acadêmico de código aberto demonstra a construção de um agente de Inteligência Artificial autônomo, utilizando a arquitetura **LangGraph** e o poder do modelo de linguagem **Gemini** do Google. O objetivo é criar um assistente de pesquisa capaz de responder a perguntas em linguagem natural sobre a conjuntura econômica do Brasil, buscando dados de fontes oficiais, realizando análises e gerando visualizações de forma autônoma.

## Missão e Escopo

O propósito central deste agente é democratizar o acesso e a análise de dados macroeconômicos brasileiros, servindo como uma ferramenta para estudantes, pesquisadores e analistas.

### Objetivo Principal

O agente é projetado para compreender perguntas complexas formuladas em português, como:

  * *"Como está a inflação acumulada no Brasil este ano?"*
  * *"Qual a trajetória da taxa Selic desde o início do governo atual?"*
  * *"Gere um gráfico mostrando a evolução do PIB trimestral desde 2020."*

A resposta final não se limita a um número, mas consiste em uma análise textual concisa acompanhada de uma visualização de dados (gráfico) relevante.

### Indicadores Centrais

Para garantir foco e eficácia, o escopo inicial do agente cobre os seguintes indicadores fundamentais da economia brasileira:

  * **Inflação:** Índice Nacional de Preços ao Consumidor Amplo (IPCA).
  * **Taxa de Juros:** Meta da Taxa Selic.
  * **Atividade Econômica:** Produto Interno Bruto (PIB) a preços de mercado.
  * **Mercado de Trabalho:** Taxa de Desocupação (PNAD Contínua).

### Fontes de Dados

A credibilidade do agente é sustentada pela utilização exclusiva de APIs de instituições oficiais brasileiras, garantindo precisão e atualidade:

  * **Banco Central do Brasil (BCB):** Via Sistema Gerenciador de Séries Temporais (SGS).
  * **Instituto de Pesquisa Econômica Aplicada (IPEADATA):** Fonte para o PIB e outras séries.
  * **Instituto Brasileiro de Geografia e Estatística (IBGE):** Acesso ao sistema SIDRA para dados detalhados.

## Arquitetura e Tecnologias

O agente é construído sobre uma arquitetura moderna e modular, baseada em grafos de estados.

  * **Estrutura de Agente (`LangGraph`):** É utilizado para orquestrar o fluxo de trabalho, permitindo a criação de ciclos de raciocínio, ação e observação que são mais flexíveis e poderosos do que scripts lineares.
  * **Motor de Raciocínio (`Google Gemini`):** Atua como o cérebro do agente, responsável por decompor as perguntas, planejar os passos, invocar as ferramentas corretas e sintetizar as respostas finais.
  * **Ferramentas (`Tools`):** Funções Python customizadas que interagem diretamente com as APIs do BCB, IPEA e IBGE.

## Como Executar o Projeto

#### 1\. Clone o repositório

```bash
# Adicione aqui o comando 'git clone' quando o repositório estiver no GitHub
git clone https://github.com/seu-usuario/seu-repositorio.git
cd seu-repositorio
```

#### 2\. Crie e ative um ambiente virtual

```bash
# Crie o ambiente virtual
python -m venv venv

# Ative o ambiente (Windows - PowerShell)
.\venv\Scripts\Activate.ps1

# Ative o ambiente (macOS/Linux)
source venv/bin/activate
```

#### 3\. Instale as dependências

```bash
pip install -r requirements.txt
```

#### 4\. Configure suas chaves de API

  * Renomeie o arquivo `.env.example` para `.env`.
  * Abra o novo arquivo `.env` e adicione sua chave da API do Google AI Studio no formato `GOOGLE_API_KEY="sua_chave_aqui"`.