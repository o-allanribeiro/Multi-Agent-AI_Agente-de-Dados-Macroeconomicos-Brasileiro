# -*- coding: utf-8 -*-
"""
Definição do estado compartilhado do agente (AgentState).

O estado é o "backbone" do LangGraph: cada nó lê e escreve neste dict
tipado para passar informações entre etapas do fluxo.
"""

import operator
from typing import Annotated, Any, List, Optional

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
        Nome da ferramenta a ser executada na próxima iteração.
    tool_params : Optional[dict]
        Parâmetros a serem passados para a ferramenta.
    pending_tools : Optional[List[dict]]
        Fila de ferramentas pendentes para execução em cadeia.
        Cada item: {"tool_to_use": str, "tool_params": dict}.
        Populada pelo Planner para perguntas multi-indicador.
    datasets : Annotated[List[Any], operator.add]
        Lista acumulativa de DataFrames coletados por cada chamada de ferramenta.
        Usa operator.add para crescer a cada iteração do Action node.
    intermediate_steps : List[BaseMessage]
        Log de execução acumulativo (operator.add = append-only).
    data : Optional[pd.DataFrame]
        DataFrame mesclado (outer join) de todos os datasets coletados.
        Atualizado após cada ferramenta executada.
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
    pending_tools: Optional[List[dict]]
    datasets: Annotated[List[Any], operator.add]
    intermediate_steps: Annotated[List[BaseMessage], operator.add]
    data: Optional[pd.DataFrame]
    analysis: Optional[str]
    plot_path: Optional[str]
    response: Optional[str]
    error: Optional[str]
