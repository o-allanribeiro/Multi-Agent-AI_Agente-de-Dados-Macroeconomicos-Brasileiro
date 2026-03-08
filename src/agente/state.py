# -*- coding: utf-8 -*-
"""
Definição do estado compartilhado do agente (AgentState).

O estado é o "backbone" do LangGraph: cada nó lê e escreve neste dict
tipado para passar informações entre etapas do fluxo.
"""

import operator
from typing import Annotated, List, Optional

import pandas as pd
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """
    Estado compartilhado entre todos os nós do grafo LangGraph.

    Attributes
    ----------
    question : str
        Pergunta original do usuário em linguagem natural.
    session_id : Optional[str]
        Identificador único da sessão/requisição (UUID). Usado para
        nomear arquivos de gráfico e rastrear conversas.
    plan : Optional[str]
        Plano de ação gerado pelo Nó de Planejamento.
    tool_to_use : Optional[str]
        Nome da ferramenta selecionada pelo planner.
    tool_params : Optional[dict]
        Parâmetros a serem passados para a ferramenta.
    intermediate_steps : List[BaseMessage]
        Log de execução acumulativo (operator.add = append-only).
    data : Optional[pd.DataFrame]
        Série temporal retornada pela ferramenta de dados.
    analysis : Optional[str]
        Análise textual gerada pelo LLM a partir dos dados.
    plot_path : Optional[str]
        Caminho local do gráfico gerado (PNG).
    response : Optional[str]
        Resposta final sintetizada para o usuário.
    error : Optional[str]
        Mensagem de erro, se houver falha em algum nó.
    """

    question: str
    session_id: Optional[str]
    plan: Optional[str]
    tool_to_use: Optional[str]
    tool_params: Optional[dict]
    intermediate_steps: Annotated[List[BaseMessage], operator.add]
    data: Optional[pd.DataFrame]
    analysis: Optional[str]
    plot_path: Optional[str]
    response: Optional[str]
    error: Optional[str]
