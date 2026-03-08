# -*- coding: utf-8 -*-
"""
Nó de Ação (Action) — Agente Macro-BR.

Responsabilidade: executar a ferramenta de dados selecionada pelo Planner
e armazenar o DataFrame resultante no estado.

Entrada  → state["tool_to_use"], state["tool_params"]
Saída    → state["data"]
"""
import logging

from agente.state import AgentState
from tools.registry import get_tool_registry

logger = logging.getLogger(__name__)


def action_node(state: AgentState) -> AgentState:
    """
    Nó de Ação: executa a ferramenta de coleta de dados.

    Parameters
    ----------
    state : AgentState
        Estado com 'tool_to_use' e 'tool_params' definidos pelo Planner.

    Returns
    -------
    AgentState
        Estado atualizado com 'data' (DataFrame) ou com 'error' em caso de falha.
    """
    logger.info("Executando nó ACTION | session=%s", state.get("session_id"))

    tool_name = state.get("tool_to_use", "none")
    tool_params = state.get("tool_params") or {}

    # Sem ferramenta — pergunta fora do escopo
    if not tool_name or tool_name == "none":
        logger.info("Nenhuma ferramenta selecionada. Pergunta pode estar fora do escopo.")
        return state

    registry = get_tool_registry()

    if not registry.has(tool_name):
        logger.error("Ferramenta não encontrada no registry: '%s'", tool_name)
        state["error"] = f"Ferramenta desconhecida: '{tool_name}'"
        return state

    tool_fn = registry.get(tool_name)

    try:
        logger.info("Executando ferramenta '%s' com params: %s", tool_name, tool_params)

        result_df = tool_fn(**tool_params) if tool_params else tool_fn()

        if result_df is None or result_df.empty:
            logger.warning("Ferramenta retornou DataFrame vazio para: %s", tool_name)
            state["error"] = "A consulta não retornou dados para o período solicitado."
        else:
            state["data"] = result_df
            logger.info("Dados armazenados | shape=%s", result_df.shape)

    except TypeError as exc:
        # Parâmetros incorretos passados para a ferramenta
        logger.error("Parâmetros inválidos para '%s': %s", tool_name, exc, exc_info=True)
        state["error"] = f"Parâmetros inválidos para a ferramenta '{tool_name}': {exc}"
    except Exception as exc:
        logger.error("Erro ao executar '%s': %s", tool_name, exc, exc_info=True)
        state["error"] = f"Erro na coleta de dados: {exc}"

    return state
