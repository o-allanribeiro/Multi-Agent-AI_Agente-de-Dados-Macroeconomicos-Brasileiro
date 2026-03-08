# -*- coding: utf-8 -*-
"""
Testes de integração — pipeline completo do agente LangGraph.

Estes testes disparam o grafo LangGraph de ponta a ponta com
ferramentas reais mockadas (sem chamadas HTTP externas).
"""
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


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
