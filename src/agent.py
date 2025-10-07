# -*- coding: utf-8 -*-
"""
Módulo principal do Agente de Pesquisa para Análise de Vulnerabilidade Estrutural.

Este script define a arquitetura do agente usando LangGraph, incluindo:
1. A definição do estado do agente (AgentState).
2. A criação dos nós que compõem o fluxo de trabalho (pensar, agir, analisar, etc.).
3. A montagem do grafo que orquestra a execução dos nós.
"""

import os
import json
from typing import TypedDict, Annotated, Optional, List
import operator
import pandas as pd
import matplotlib
import matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

# Importa as nossas funções de ferramenta dos outros módulos
from tools.bcb_tools import get_bcb_series
from tools.ipea_tools import get_ipea_series
from tools.world_bank_tools import get_gini_series

# Carrega as variáveis de ambiente (GOOGLE_API_KEY) do arquivo .env
load_dotenv()

# --- 1. Definição do Estado do Agente (AgentState) ---
class AgentState(TypedDict):
    """
    Representa o estado do nosso agente.
    """
    question: str
    plan: str
    tool_to_use: Optional[str]
    tool_params: Optional[dict]
    intermediate_steps: Annotated[List[BaseMessage], operator.add]
    data: Optional[pd.DataFrame]
    analysis: Optional[str]
    plot_path: Optional[str]
    response: Optional[str]

# --- 2. Inicialização do Modelo (LLM) ---
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

# --- 3. Definição das Ferramentas ---
tools_router = {
    "get_bcb_series": get_bcb_series,
    "get_ipea_series": get_ipea_series,
    "get_gini_series": get_gini_series,
}

# --- 4. Definição dos Nós do Grafo ---

def planner_node(state: AgentState):
    """
    Nó de Planejamento: Analisa a pergunta do usuário e decide qual ferramenta usar.
    """
    print("--- EXECUTANDO NÓ DE PLANEJAMENTO ---")
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """Você é um economista especialista e assistente de pesquisa.
                Sua tarefa é analisar a pergunta do usuário e criar um plano de ação para respondê-la,
                escolhendo a melhor ferramenta disponível.

                As ferramentas disponíveis são:
                1. `get_bcb_series`: Para dados do Banco Central do Brasil (IPCA, Selic, Desocupação, Dólar).
                   Parâmetros: `series_code` (int), `last_n_years` (int).
                   Mapeamento: IPCA=433, Selic=432, Desocupação=24369, Dólar=1.
                2. `get_ipea_series`: Para dados do IPEADATA (FBCF).
                   Parâmetros: `series_code` (str). Mapeamento: FBCF='GAC12_INDFBCF12'.
                3. `get_gini_series`: Para o Coeficiente de Gini do Banco Mundial.
                   Parâmetros: Nenhum.

                Responda em JSON com "plan", "tool_to_use", e "tool_params".
                Se nenhuma ferramenta for adequada, "tool_to_use" deve ser "none".
                """,
            ),
            ("human", "{question}"),
        ]
    )
    chain = prompt | llm | JsonOutputParser()
    result = chain.invoke({"question": state["question"]})
    state["plan"] = result.get("plan")
    state["tool_to_use"] = result.get("tool_to_use")
    state["tool_params"] = result.get("tool_params")
    print(f"Plano gerado: {state['plan']}")
    return state

def action_node(state: AgentState):
    """
    Nó de Ação: Executa a ferramenta escolhida pelo nó de planejamento.
    """
    print("--- EXECUTANDO NÓ DE AÇÃO ---")
    tool_name = state.get("tool_to_use")
    tool_params = state.get("tool_params")

    if not tool_name or tool_name == "none":
        print("Nenhuma ferramenta para executar.")
        return state
    if tool_name not in tools_router:
        print(f"Erro: Ferramenta '{tool_name}' não encontrada.")
        return state

    tool_function = tools_router[tool_name]
    try:
        if tool_params:
            result_df = tool_function(**tool_params)
        else:
            result_df = tool_function()
        state["data"] = result_df
        print("Dados obtidos e armazenados no estado.")
    except Exception as e:
        print(f"Erro ao executar a ferramenta {tool_name}: {e}")
    return state

def analysis_node(state: AgentState):
    """
    Nó de Análise: Gera uma análise textual a partir dos dados coletados.
    """
    print("--- EXECUTANDO NÓ DE ANÁLISE ---")
    df = state.get("data")
    if df is None or df.empty:
        state["analysis"] = "Não foram encontrados dados para análise."
        return state

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """Você é um economista sênior do Banco Central do Brasil.
                Sua tarefa é analisar os seguintes dados de uma série temporal e fornecer um resumo conciso (1-2 parágrafos).
                Descreva a tendência geral, mencione o valor mais recente, os valores máximo e mínimo e o período coberto pelos dados.
                Seja direto e informativo, baseando-se estritamente no resumo estatístico fornecido.
                
                Resumo Estatístico para Análise:
                {data_summary}
                """,
            ),
            ("human", "Com base nesse resumo, qual é a sua análise sobre a pergunta original: {question}?"),
        ]
    )
    chain = prompt | llm | StrOutputParser()
    
    # MELHORIA: Cria um resumo estatístico mais completo para o LLM
    series_name = df.columns[0]
    data_summary = (
        f"Resumo da série temporal '{series_name}':\n"
        f"- Período: de {df.index.min().strftime('%Y-%m-%d')} a {df.index.max().strftime('%Y-%m-%d')}\n"
        f"- Número de registros: {len(df)}\n"
        f"- Valor mínimo: {df[series_name].min():.2f}\n"
        f"- Valor máximo: {df[series_name].max():.2f}\n"
        f"- Valor mais recente ({df.index.max().strftime('%Y-%m-%d')}): {df[series_name].iloc[-1]:.2f}"
    )
    
    analysis = chain.invoke({
        "data_summary": data_summary,
        "question": state["question"]
    })
    state["analysis"] = analysis
    print("Análise gerada com sucesso.")
    return state

def plot_node(state: AgentState):
    """
    Nó de Visualização: Gera e salva um gráfico a partir dos dados.
    """
    print("--- EXECUTANDO NÓ DE VISUALIZAÇÃO ---")
    df = state.get("data")
    if df is None or df.empty:
        print("Nenhum dado para plotar.")
        return state

    try:
        # Garante que a pasta de output exista
        if not os.path.exists("output"):
            os.makedirs("output")

        fig, ax = plt.subplots(figsize=(10, 6))
        series_name = df.columns[0]
        ax.plot(df.index, df[series_name], marker='o', linestyle='-')
        
        # Formatação
        ax.set_title(f"Evolução de: {series_name}", fontsize=16)
        ax.set_xlabel("Data", fontsize=12)
        ax.set_ylabel("Valor", fontsize=12)
        ax.grid(True, which='both', linestyle='--', linewidth=0.5)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        fig.autofmt_xdate()
        plt.tight_layout()
        
        # Salva o gráfico
        plot_path = os.path.join("output", "chart.png")
        plt.savefig(plot_path)
        plt.close(fig) # Fecha a figura para liberar memória
        
        state["plot_path"] = plot_path
        print(f"Gráfico salvo com sucesso em: {plot_path}")
    except Exception as e:
        print(f"Erro ao gerar o gráfico: {e}")
    
    return state

def response_node(state: AgentState):
    """
    Nó de Resposta: Sintetiza a análise e o gráfico em uma resposta final.
    """
    print("--- EXECUTANDO NÓ DE RESPOSTA ---")
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "Você é um assistente de pesquisa econômica. Sintetize a análise fornecida em uma resposta clara e final para o usuário. Mencione que um gráfico foi gerado para visualização."),
            ("human", "Análise: {analysis}\n\nCom base nisso, formule a resposta final para a pergunta: {question}"),
        ]
    )
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({
        "analysis": state.get("analysis", "N/A"),
        "question": state.get("question")
    })
    state["response"] = response
    return state

# --- 5. Montagem do Grafo ---
print("Montando o grafo do agente...")
workflow = StateGraph(AgentState)

# Adiciona os nós ao grafo com nomes únicos
workflow.add_node("planner_step", planner_node)
workflow.add_node("action_step", action_node)
workflow.add_node("analysis_step", analysis_node)
workflow.add_node("plot_step", plot_node)
workflow.add_node("response_step", response_node)

# Define o ponto de entrada do grafo
workflow.set_entry_point("planner_step")

# Adiciona as arestas (conexões) entre os nós
workflow.add_edge("planner_step", "action_step")
workflow.add_edge("action_step", "analysis_step")
workflow.add_edge("analysis_step", "plot_step")
workflow.add_edge("plot_step", "response_step")
workflow.add_edge("response_step", END)

# Compila o grafo em uma aplicação executável
app = workflow.compile()
print("Grafo compilado com sucesso.")


# --- Bloco de Teste ---
if __name__ == '__main__':
    print("\n--- INICIANDO EXECUÇÃO DO GRAFO ---")
    
    question = "Qual a trajetória da taxa de desocupação nos últimos 10 anos?"
    
    # CORREÇÃO: Inicializa o estado com 'intermediate_steps' como uma lista vazia
    initial_state = {"question": question, "intermediate_steps": []}
    
    final_state = app.invoke(initial_state)
    
    print("\n--- ESTADO FINAL APÓS A EXECUÇÃO ---")
    print(f"Pergunta original: {final_state['question']}")
    print(f"Plano do agente: {final_state['plan']}")
    
    if final_state.get("data") is not None:
        print("\nDados obtidos (últimos 5):")
        print(final_state["data"].tail())

    print(f"\nAnálise Gerada:\n{final_state.get('analysis')}")
    print(f"\nGráfico salvo em: {final_state.get('plot_path')}")
    print(f"\n--- RESPOSTA FINAL DO AGENTE ---:\n{final_state.get('response')}")

