# -*- coding: utf-8 -*-
"""
Nó de Ação (Action) e Próxima Ferramenta (NextTool) — Agente Macro-BR.

Responsabilidade:
  - action_node: executar a ferramenta selecionada e acumular os resultados.
  - next_tool_node: desempilhar a próxima ferramenta da fila e preparar o estado.

Entrada  → state["tool_to_use"], state["tool_params"]
Saída    → state["data"], state["datasets"]  (action_node)
           state["tool_to_use"], state["tool_params"], state["pending_tools"]  (next_tool_node)
"""
import logging

import pandas as pd

from agente.state import AgentState
from tools.registry import get_tool_registry

logger = logging.getLogger(__name__)


def _merge_datasets(dfs: list) -> pd.DataFrame:
    """
    Junta múltiplos DataFrames num único DF wide usando outer join no DatetimeIndex.

    Renomeia colunas duplicadas com sufixo numérico (_1, _2, ...) para evitar
    ValueError quando duas ferramentas retornam a mesma série (ex: BCB 432 × 432).
    """
    if not dfs:
        return pd.DataFrame()
    if len(dfs) == 1:
        return dfs[0]

    result = dfs[0].copy()
    for i, df in enumerate(dfs[1:], start=2):
        # Renomear colunas do df que colidem com o result existente
        overlap = set(result.columns) & set(df.columns)
        if overlap:
            rename_map = {col: f"{col}_{i}" for col in overlap}
            df = df.rename(columns=rename_map)
        result = result.join(df, how="outer")
    return result.sort_index()


def action_node(state: AgentState) -> AgentState:
    """
    Nó de Ação: executa a ferramenta de coleta de dados e acumula resultados.

    Ao final, atualiza state["data"] com o merge de todas as séries coletadas
    até o momento (incluindo iterações anteriores via state["datasets"]).

    Parameters
    ----------
    state : AgentState
        Estado com 'tool_to_use' e 'tool_params' definidos pelo Planner.

    Returns
    -------
    AgentState
        Estado atualizado com 'data' (DataFrame mesclado) e 'datasets'
        (nova entrada adicionada pelo reducer operator.add).
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
            # 'datasets' não tem reducer (ver agente/state.py) — este nó é o
            # único responsável por reconstruir a lista completa a cada
            # chamada (prev + novo), não apenas retornar o item novo.
            prev_datasets: list = state.get("datasets") or []
            new_datasets = prev_datasets + [result_df]
            merged = _merge_datasets(new_datasets)
            state["data"] = merged
            state["datasets"] = new_datasets
            logger.info(
                "Dados acumulados | nova_série=%s | total_colunas=%d | shape=%s",
                result_df.columns[0],
                len(merged.columns),
                merged.shape,
            )

    except TypeError as exc:
        logger.error("Parâmetros inválidos para '%s': %s", tool_name, exc, exc_info=True)
        state["error"] = f"Parâmetros inválidos para a ferramenta '{tool_name}': {exc}"
    except Exception as exc:
        logger.error("Erro ao executar '%s': %s", tool_name, exc, exc_info=True)
        state["error"] = f"Erro na coleta de dados: {exc}"

    return state


def next_tool_node(state: AgentState) -> AgentState:
    """
    Nó de Próxima Ferramenta: desempilha o próximo item da fila pending_tools.

    Executado após action_node quando há ferramentas restantes na fila.
    Prepara tool_to_use e tool_params para a próxima iteração do action_node.

    Parameters
    ----------
    state : AgentState
        Estado com 'pending_tools' não-vazio.

    Returns
    -------
    AgentState
        Estado com tool_to_use, tool_params e pending_tools atualizados.
    """
    pending = list(state.get("pending_tools") or [])
    if pending:
        next_tool = pending[0]
        state["tool_to_use"] = next_tool.get("tool_to_use", "none")
        state["tool_params"] = next_tool.get("tool_params") or {}
        state["pending_tools"] = pending[1:]
        logger.info(
            "Próxima ferramenta preparada | tool=%s | params=%s | restantes=%d",
            state["tool_to_use"],
            state["tool_params"],
            len(state["pending_tools"]),
        )
    return state

