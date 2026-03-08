# -*- coding: utf-8 -*-
"""
Agente LangGraph — Agente Macro-BR.

Monta e compila o grafo de execução do agente usando LangGraph.
O grafo é um pipeline linear de 5 nós:

  Planner → Action → Analysis → Plot → Response

Factory pública: ``create_agent()``
"""
import logging
import uuid

from langgraph.graph import END, StateGraph

from agente.nodes import (
    action_node,
    analysis_node,
    planner_node,
    plot_node,
    response_node,
)
from agente.state import AgentState

logger = logging.getLogger(__name__)


def create_agent():
    """
    Cria e compila o grafo LangGraph do agente.

    O grafo é compilado UMA VEZ e reutilizado em todas as invocações.
    Uso com ``@lru_cache`` no ponto de chamada para singleton.

    Returns
    -------
    CompiledGraph
        Grafo compilado e pronto para invocar via ``graph.invoke(state)``.
    """
    logger.debug("Montando grafo LangGraph...")

    workflow = StateGraph(AgentState)

    # Registra os nós
    workflow.add_node("planner_step", planner_node)
    workflow.add_node("action_step", action_node)
    workflow.add_node("analysis_step", analysis_node)
    workflow.add_node("plot_step", plot_node)
    workflow.add_node("response_step", response_node)

    # Define o ponto de entrada
    workflow.set_entry_point("planner_step")

    # Conexões lineares entre os nós
    workflow.add_edge("planner_step", "action_step")
    workflow.add_edge("action_step", "analysis_step")
    workflow.add_edge("analysis_step", "plot_step")
    workflow.add_edge("plot_step", "response_step")
    workflow.add_edge("response_step", END)

    compiled = workflow.compile()
    logger.debug("Grafo compilado com sucesso.")
    return compiled


def run_agent(question: str, session_id: str | None = None) -> AgentState:
    """
    Executa o agente para uma pergunta e retorna o estado final.

    Parameters
    ----------
    question : str
        Pergunta do usuário em linguagem natural.
    session_id : str, optional
        ID da sessão para rastreamento. Gerado automaticamente se não fornecido.

    Returns
    -------
    AgentState
        Estado final após execução completa do grafo.
    """
    from functools import lru_cache

    @lru_cache(maxsize=1)
    def _get_compiled_agent():
        return create_agent()

    if session_id is None:
        session_id = str(uuid.uuid4())[:8]

    initial_state: AgentState = {
        "question": question,
        "session_id": session_id,
        "plan": None,
        "tool_to_use": None,
        "tool_params": None,
        "intermediate_steps": [],
        "data": None,
        "analysis": None,
        "plot_path": None,
        "response": None,
        "error": None,
    }

    logger.info("Invocando agente | session=%s | question='%s'", session_id, question[:80])

    agent = _get_compiled_agent()
    final_state: AgentState = agent.invoke(initial_state)

    logger.info(
        "Agente concluído | session=%s | has_data=%s | has_plot=%s",
        session_id,
        final_state.get("data") is not None,
        final_state.get("plot_path") is not None,
    )

    return final_state
