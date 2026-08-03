# -*- coding: utf-8 -*-
"""
Testes de integração — pipeline completo do agente LangGraph.

Estes testes disparam o grafo LangGraph de ponta a ponta com
ferramentas reais mockadas (sem chamadas HTTP externas).
"""
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from langchain_core.messages import AIMessage


@pytest.fixture()
def sample_df():
    """DataFrame de IPCA para simular retorno de ferramenta."""
    return pd.DataFrame(
        {"valor": [0.44, 0.61, 0.76, 0.69, 0.83]},
        index=pd.date_range("2024-01-01", periods=5, freq="ME"),
    )


@pytest.fixture()
def mock_llm_response():
    """Simula resposta do LLM (AIMessage)."""
    mock = MagicMock()
    mock.content = "FERRAMENTA: bcb\nPARÂMETROS: {\"series_code\": \"433\"}"
    return mock


class TestAgentPipeline:
    """Testes de integração do pipeline LangGraph completo."""

    def test_full_pipeline_runs_without_error(self, sample_df):
        """Pipeline deve executar sem levantar exceção para pergunta válida."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='FERRAMENTA: bcb\nPARÂMETROS: {"series_code": "433"}'
        )

        mock_analysis_llm = MagicMock()
        mock_analysis_llm.invoke.return_value = MagicMock(
            content="Análise: O IPCA apresentou tendência de alta."
        )

        mock_response_llm = MagicMock()
        mock_response_llm.invoke.return_value = MagicMock(
            content="Com base nos dados, o IPCA mostrou alta de 0.61%."
        )

        with (
            patch("agente.nodes.planner.ChatGoogleGenerativeAI", return_value=mock_llm),
            patch("agente.nodes.analysis.ChatGoogleGenerativeAI", return_value=mock_analysis_llm),
            patch("agente.nodes.response.ChatGoogleGenerativeAI", return_value=mock_response_llm),
            patch("tools.bcb.get_bcb_series", return_value=sample_df),
            patch("agente.nodes.plot.plt") as mock_plt,
        ):
            mock_plt.savefig = MagicMock()
            mock_plt.figure = MagicMock()
            mock_plt.close = MagicMock()

            from agente.agent import run_agent

            result = run_agent("Qual a inflação IPCA nos últimos meses?", session_id="test-int-001")

        assert result is not None
        assert isinstance(result, dict)

    def test_pipeline_returns_state_keys(self, sample_df):
        """Resultado do pipeline deve conter as chaves esperadas do estado."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='FERRAMENTA: bcb\nPARÂMETROS: {"series_code": "433"}'
        )

        mock_analysis_llm = MagicMock()
        mock_analysis_llm.invoke.return_value = MagicMock(
            content="Análise dos dados de IPCA."
        )

        mock_response_llm = MagicMock()
        mock_response_llm.invoke.return_value = MagicMock(
            content="Resposta final consolidada."
        )

        with (
            patch("agente.nodes.planner.ChatGoogleGenerativeAI", return_value=mock_llm),
            patch("agente.nodes.analysis.ChatGoogleGenerativeAI", return_value=mock_analysis_llm),
            patch("agente.nodes.response.ChatGoogleGenerativeAI", return_value=mock_response_llm),
            patch("tools.bcb.get_bcb_series", return_value=sample_df),
            patch("agente.nodes.plot.plt"),
        ):
            from agente.agent import run_agent

            result = run_agent("Qual a taxa Selic?", session_id="test-int-002")

        expected_keys = {"question", "session_id", "response"}
        assert expected_keys.issubset(result.keys()), (
            f"Chaves ausentes: {expected_keys - result.keys()}"
        )

    def test_pipeline_handles_tool_failure_gracefully(self):
        """Pipeline deve lidar com falha na ferramenta sem travar."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='FERRAMENTA: bcb\nPARÂMETROS: {"series_code": "433"}'
        )

        mock_analysis_llm = MagicMock()
        mock_analysis_llm.invoke.return_value = MagicMock(
            content="Dados indisponíveis no momento."
        )

        mock_response_llm = MagicMock()
        mock_response_llm.invoke.return_value = MagicMock(
            content="Não foi possível obter os dados. Tente novamente."
        )

        with (
            patch("agente.nodes.planner.ChatGoogleGenerativeAI", return_value=mock_llm),
            patch("agente.nodes.analysis.ChatGoogleGenerativeAI", return_value=mock_analysis_llm),
            patch("agente.nodes.response.ChatGoogleGenerativeAI", return_value=mock_response_llm),
            patch("tools.bcb.get_bcb_series", return_value=None),
            patch("agente.nodes.plot.plt"),
        ):
            from agente.agent import run_agent

            # Não deve levantar exceção
            result = run_agent("Qual o PIB atual?", session_id="test-int-003")

        assert result is not None

    def test_multi_tool_query_does_not_duplicate_datasets(self):
        """
        Regressão: perguntas com 2+ ferramentas (ex: Selic + IPCA para juro real)
        não podem duplicar séries no DataFrame final.

        Bug real observado: como AgentState.datasets usava Annotated[..., operator.add]
        e todo nó do grafo faz `return state` (dict inteiro), qualquer nó que apenas
        repassasse 'datasets' sem alterá-lo (ex: next_tool_node, stats_node) era
        tratado pelo LangGraph como uma NOVA contribuição a somar — duplicando os
        DataFrames já coletados a cada nó subsequente do pipeline. Resultado visível:
        coluna "432_2" duplicada no gráfico/dados de "Qual o juro real no Brasil hoje?".
        """
        planner_json = (
            '{"plan": "Buscar Selic e IPCA para calcular juro real via Fisher.", '
            '"tools": ['
            '{"tool_to_use": "get_bcb_series", "tool_params": {"series_code": 432, "last_n_years": 1}}, '
            '{"tool_to_use": "get_bcb_series", "tool_params": {"series_code": 433, "last_n_years": 1}}'
            ']}'
        )
        # Nota: RunnableLambda envolve objetos não-Runnable chamando-os
        # diretamente (mock(x)), não via .invoke(x) — por isso configuramos
        # tanto o retorno de chamada quanto o de .invoke.
        mock_planner_llm = MagicMock(return_value=AIMessage(content=planner_json))
        mock_planner_llm.invoke.return_value = AIMessage(content=planner_json)

        mock_analysis_llm = MagicMock(
            return_value=AIMessage(content="Análise consolidada de Selic e IPCA.")
        )
        mock_analysis_llm.invoke.return_value = mock_analysis_llm.return_value

        mock_response_llm = MagicMock(
            return_value=AIMessage(content="Resposta final sobre o juro real.")
        )
        mock_response_llm.invoke.return_value = mock_response_llm.return_value

        dates = pd.date_range("2024-01-01", periods=12, freq="MS")
        df_selic = pd.DataFrame({"432": [13.75] * 12}, index=dates)
        df_ipca = pd.DataFrame({"433": [0.5] * 12}, index=dates)

        mock_registry = MagicMock()
        mock_registry.has.return_value = True
        mock_registry.get.return_value = lambda **kwargs: (
            df_selic if kwargs.get("series_code") == 432 else df_ipca
        )

        with (
            patch("agente.nodes.planner.ChatGoogleGenerativeAI", return_value=mock_planner_llm),
            patch("agente.nodes.analysis.ChatGoogleGenerativeAI", return_value=mock_analysis_llm),
            patch("agente.nodes.response.ChatGoogleGenerativeAI", return_value=mock_response_llm),
            patch("agente.nodes.action.get_tool_registry", return_value=mock_registry),
            patch("agente.nodes.plot.plt"),
        ):
            from agente.agent import run_agent

            result = run_agent("Qual o juro real no Brasil hoje?", session_id="test-int-004")

        assert result["data"] is not None
        columns = list(result["data"].columns)
        assert columns == ["432", "433"], (
            f"Colunas duplicadas detectadas: {columns} — cada série deve aparecer "
            f"exatamente uma vez no DataFrame final"
        )
        assert len(result["datasets"]) == 2, (
            f"'datasets' deveria ter exatamente 2 entradas (1 por ferramenta), "
            f"encontrado {len(result['datasets'])}"
        )
