# -*- coding: utf-8 -*-
"""
Definição do estado compartilhado do agente (AgentState).

O estado é o "backbone" do LangGraph: cada nó lê e escreve neste dict
tipado para passar informações entre etapas do fluxo.
"""

from typing import Any, List, Optional

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
    datasets : List[Any]
        Lista acumulativa de DataFrames coletados por cada chamada de ferramenta.
        Sem reducer (operator.add): campo comum (last-write-wins). O próprio
        action_node é responsável por reconstruir a lista completa a cada
        chamada (prev + novo). Usar Annotated[..., operator.add] aqui causava
        duplicação silenciosa: como todo nó do grafo faz `return state`
        (dict inteiro), qualquer nó que apenas repassasse "datasets" sem
        alterá-lo era tratado pelo LangGraph como uma NOVA contribuição a
        somar, duplicando os DataFrames já coletados a cada nó subsequente
        (bug real observado em perguntas multi-ferramenta / indicadores
        derivados — ver CHANGELOG).
    intermediate_steps : List[BaseMessage]
        Log de execução (não populado atualmente). Mesmo motivo acima: sem
        reducer, para evitar a mesma classe de bug se um nó vier a usá-lo.
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
    datasets: List[Any]
    intermediate_steps: List[BaseMessage]
    data: Optional[pd.DataFrame]
    analysis: Optional[str]
    plot_path: Optional[str]
    response: Optional[str]
    error: Optional[str]
    # --- Onda 3: contexto histórico e auditoria ---
    historical_stats: Optional[dict]
    historical_stats_text: Optional[str]
    derived_data: Optional[dict]
    audit_flags: Optional[List[str]]
    audit_summary: Optional[str]
