# -*- coding: utf-8 -*-
"""
Testes unitários dos Nós do LangGraph — Agente Macro-BR.

Testa cada nó de forma isolada, mockando dependências externas
(LLM, APIs) para garantir velocidade e determinismo.
"""
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


class TestActionNode:
    """Testes do nó de ação (execução de ferramentas)."""

    def test_action_with_valid_tool(self, mock_state_with_data, sample_ipca_df):
        """Nó de ação deve popular state['data'] quando a ferramenta retorna dados."""
        from agente.nodes.action import action_node

        state = {
            **mock_state_with_data,
            "data": None,  # Reset para testar o preenchimento
            "tool_to_use": "get_bcb_series",
            "tool_params": {"series_code": 433, "last_n_years": 2},
        }

        with patch("agente.nodes.action.get_tool_registry") as mock_registry:
            mock_reg_instance = MagicMock()
            mock_reg_instance.has.return_value = True
            mock_reg_instance.get.return_value = lambda **kwargs: sample_ipca_df
            mock_registry.return_value = mock_reg_instance

            result = action_node(state)

        assert result["data"] is not None
        assert not result["data"].empty

    def test_action_with_none_tool(self, mock_agent_state):
        """Nó de ação não deve fazer nada se tool_to_use='none'."""
        from agente.nodes.action import action_node

        state = {**mock_agent_state, "tool_to_use": "none"}
        result = action_node(state)
        assert result["data"] is None
        assert result.get("error") is None

    def test_action_with_unknown_tool(self, mock_agent_state):
        """Nó de ação deve registrar erro para ferramenta desconhecida."""
        from agente.nodes.action import action_node

        state = {**mock_agent_state, "tool_to_use": "ferramenta_inexistente"}

        with patch("agente.nodes.action.get_tool_registry") as mock_registry:
            mock_reg_instance = MagicMock()
            mock_reg_instance.has.return_value = False
            mock_registry.return_value = mock_reg_instance

            result = action_node(state)

        assert result.get("error") is not None

    def test_action_tool_returns_none(self, mock_agent_state):
        """Nó de ação deve registrar erro quando a ferramenta retorna None."""
        from agente.nodes.action import action_node

        state = {
            **mock_agent_state,
            "tool_to_use": "get_bcb_series",
            "tool_params": {"series_code": 433, "last_n_years": 2},
        }

        with patch("agente.nodes.action.get_tool_registry") as mock_registry:
            mock_reg_instance = MagicMock()
            mock_reg_instance.has.return_value = True
            mock_reg_instance.get.return_value = lambda **kwargs: None
            mock_registry.return_value = mock_reg_instance

            result = action_node(state)

        assert result.get("data") is None
        assert result.get("error") is not None


class TestAnalysisNode:
    """Testes do nó de análise textual."""

    def test_analysis_with_data(self, mock_state_with_data):
        """Nó de análise deve popular state['analysis'] com texto."""
        from agente.nodes.analysis import analysis_node

        with patch("agente.nodes.analysis.ChatGoogleGenerativeAI") as mock_llm_cls:
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = "Análise gerada pelo mock LLM."
            mock_llm_cls.return_value = MagicMock()

            with patch("agente.nodes.analysis.ChatPromptTemplate") as mock_prompt:
                mock_prompt.from_messages.return_value.__or__ = MagicMock(
                    return_value=MagicMock(__or__=MagicMock(return_value=mock_chain))
                )
                result = analysis_node(mock_state_with_data)

        # Verifica que analysis foi preenchida (pode ser o fallback também)
        assert result.get("analysis") is not None
        assert len(result["analysis"]) > 0

    def test_analysis_without_data(self, mock_agent_state):
        """Nó de análise deve retornar mensagem amigável quando sem dados."""
        from agente.nodes.analysis import analysis_node

        result = analysis_node(mock_agent_state)

        assert result.get("analysis") is not None
        assert "não foram encontrados" in result["analysis"].lower() or \
               "solicita" in result["analysis"].lower()


class TestPlotNode:
    """Testes do nó de visualização."""

    def test_plot_creates_file(self, mock_state_with_data, tmp_path):
        """Nó de plot deve gerar arquivo PNG."""
        from agente.nodes.plot import plot_node

        with patch("agente.nodes.plot.get_settings") as mock_settings:
            mock_settings.return_value.agent_output_dir = str(tmp_path)
            result = plot_node(mock_state_with_data)

        assert result.get("plot_path") is not None
        assert result["plot_path"].endswith(".png")

    def test_plot_without_data(self, mock_agent_state):
        """Nó de plot deve retornar sem erro quando não há dados."""
        from agente.nodes.plot import plot_node

        result = plot_node(mock_agent_state)
        assert result.get("plot_path") is None


class TestResponseNode:
    """Testes do nó de resposta."""

    def test_response_with_analysis(self, mock_state_with_data):
        """Nó de resposta deve popular state['response']."""
        from agente.nodes.response import response_node

        state = {**mock_state_with_data, "analysis": "Análise textual simulada."}

        with patch("agente.nodes.response.ChatGoogleGenerativeAI"):
            with patch("agente.nodes.response.ChatPromptTemplate") as mock_pt:
                mock_chain = MagicMock()
                mock_chain.invoke.return_value = "Resposta sintética mockada."
                mock_pt.from_messages.return_value.__or__ = MagicMock(
                    return_value=MagicMock(__or__=MagicMock(return_value=mock_chain))
                )
                result = response_node(state)

        assert result.get("response") is not None

    def test_response_with_error_no_analysis(self, mock_agent_state):
        """Nó de resposta deve retornar mensagem de fallback se houver erro."""
        from agente.nodes.response import response_node

        state = {**mock_agent_state, "error": "Dados não encontrados."}
        result = response_node(state)
        assert result.get("response") is not None
        assert len(result["response"]) > 0
