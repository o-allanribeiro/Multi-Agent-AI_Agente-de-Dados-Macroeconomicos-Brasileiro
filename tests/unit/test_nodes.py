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


# =============================================================================
# Onda 3 — Nó de Estatísticas Históricas
# =============================================================================

class TestStatsNode:
    """Testes do nó de estatísticas históricas (Onda 3)."""

    def _make_state(self, df, question: str = "Qual o IPCA dos últimos 5 anos?") -> dict:
        """Constrói estado de teste com todos os campos Onda 3."""
        return {
            "question": question,
            "session_id": "test-stats-001",
            "plan": None,
            "tool_to_use": None,
            "tool_params": None,
            "intermediate_steps": [],
            "data": df,
            "analysis": None,
            "plot_path": None,
            "response": None,
            "error": None,
            "historical_stats": {},
            "historical_stats_text": "",
            "derived_data": {},
            "audit_flags": [],
            "audit_summary": "",
        }

    def test_computes_zscore_for_clear_outlier(self):
        """Z-score deve ser alto quando o último valor está muito afastado da média."""
        from agente.nodes.stats import stats_node

        # 59 valores iguais e último muito diferente → z-score alto
        dates = pd.date_range(end=pd.Timestamp.now(), periods=60, freq="MS")
        values = [10.0] * 59 + [25.0]
        df = pd.DataFrame({"ipca": values}, index=dates)
        state = self._make_state(df)

        result = stats_node(state)
        z = result["historical_stats"]["ipca"]["zscore_latest"]
        assert z > 3.0, f"Z-score esperado > 3.0 para outlier claro, obtido: {z}"

    def test_trend_direction_alta(self):
        """Tendência de 3 meses deve ser 'alta' em série claramente crescente."""
        from agente.nodes.stats import stats_node

        # Base estável para garantir std > 0, depois 3 últimos meses subindo forte
        dates = pd.date_range(end=pd.Timestamp.now(), periods=36, freq="MS")
        base = [5.0] * 33 + [6.0, 7.5, 9.5]
        df = pd.DataFrame({"selic": base}, index=dates)
        state = self._make_state(df)

        result = stats_node(state)
        trend = result["historical_stats"]["selic"]["trend_3m"]
        assert trend == "alta", f"Esperado 'alta', obtido: {trend}"

    def test_trend_direction_baixa(self):
        """Tendência de 3 meses deve ser 'baixa' em série claramente decrescente."""
        from agente.nodes.stats import stats_node

        dates = pd.date_range(end=pd.Timestamp.now(), periods=36, freq="MS")
        base = [10.0] * 33 + [8.5, 6.5, 4.0]
        df = pd.DataFrame({"selic": base}, index=dates)
        state = self._make_state(df)

        result = stats_node(state)
        trend = result["historical_stats"]["selic"]["trend_3m"]
        assert trend == "baixa", f"Esperado 'baixa', obtido: {trend}"

    def test_percentile_rank_at_max_value(self):
        """Último valor sendo o máximo absoluto histórico → percentil ≈ 100%."""
        from agente.nodes.stats import stats_node

        dates = pd.date_range(end=pd.Timestamp.now(), periods=24, freq="MS")
        values = list(range(1, 24)) + [100]  # último é máximo absoluto
        df = pd.DataFrame({"indicador": values}, index=dates)
        state = self._make_state(df)

        result = stats_node(state)
        pct = result["historical_stats"]["indicador"]["percentile_rank"]
        assert pct > 95.0, f"Percentil esperado > 95 para máximo histórico, obtido: {pct}"

    def test_stats_returns_empty_on_no_data(self):
        """stats_node deve retornar estado sem stats quando não há dados."""
        from agente.nodes.stats import stats_node

        state = self._make_state(None)
        result = stats_node(state)
        assert result["historical_stats"] == {}
        assert result["historical_stats_text"] == ""
        assert result["derived_data"] == {}

    def test_stats_text_contains_zscore_label(self):
        """Texto formatado de stats deve incluir 'Z-score'."""
        from agente.nodes.stats import stats_node

        dates = pd.date_range(end=pd.Timestamp.now(), periods=24, freq="MS")
        values = [0.5 + i * 0.01 for i in range(24)]  # leve variação para std > 0
        df = pd.DataFrame({"ipca": values}, index=dates)
        state = self._make_state(df)

        result = stats_node(state)
        text = result["historical_stats_text"]
        assert "Z-score" in text, "Z-score deve aparecer no texto de contexto histórico"

    def test_detects_juros_reais_and_applies_fisher(self, sample_combined_df):
        """Pergunta sobre juro real deve disparar o cálculo Fisher e popular derived_data."""
        from agente.nodes.stats import stats_node

        state = self._make_state(
            sample_combined_df,
            question="Qual o juro real no Brasil hoje?",
        )
        result = stats_node(state)
        assert "juros_reais" in result["derived_data"], (
            "Derivado 'juros_reais' deve ser calculado para pergunta sobre juro real"
        )
        jr_df = result["derived_data"]["juros_reais"]
        assert not jr_df.empty
        assert "juros_reais_pct" in jr_df.columns

    def test_mean_1y_3y_5y_are_populated(self):
        """Médias de 1, 3 e 5 anos devem ser calculadas em séries longas o suficiente."""
        from agente.nodes.stats import stats_node

        dates = pd.date_range(end=pd.Timestamp.now(), periods=72, freq="MS")
        values = [10.0 + i * 0.05 for i in range(72)]
        df = pd.DataFrame({"selic": values}, index=dates)
        state = self._make_state(df)

        result = stats_node(state)
        st = result["historical_stats"]["selic"]
        assert st["mean_1y"] is not None
        assert st["mean_3y"] is not None
        assert st["mean_5y"] is not None


# =============================================================================
# Onda 3 — Nó Auditor de Consistência Macroeconômica
# =============================================================================

class TestAuditorNode:
    """Testes do nó auditor de consistência macroeconômica (Onda 3)."""

    def _base_state(self, historical_stats=None, derived_data=None, analysis=None) -> dict:
        return {
            "question": "Teste",
            "session_id": "test-audit-001",
            "plan": None,
            "tool_to_use": None,
            "tool_params": None,
            "intermediate_steps": [],
            "data": None,
            "analysis": analysis or "",
            "plot_path": None,
            "response": None,
            "error": None,
            "historical_stats": historical_stats or {},
            "historical_stats_text": "",
            "derived_data": derived_data or {},
            "audit_flags": [],
            "audit_summary": "",
        }

    def test_no_flags_when_no_data(self):
        """Sem stats → sem flags; summary indica 'nenhuma inconsistência'."""
        from agente.nodes.auditor import auditor_node

        result = auditor_node(self._base_state())
        assert result["audit_flags"] == []
        assert "nenhuma inconsist" in result["audit_summary"].lower()

    def test_flag_stale_data_critical(self):
        """Dado com defasagem > 365 dias → flag CRÍTICO."""
        from agente.nodes.auditor import auditor_node

        stats = {
            "ipca": {
                "latest_value": 4.5, "latest_date": "2020-01-01",
                "lag_days": 500, "zscore_latest": 0.3,
                "percentile_rank": 55, "trend_3m": "estável",
            }
        }
        result = auditor_node(self._base_state(historical_stats=stats))
        flags_text = " ".join(result["audit_flags"])
        assert "CRÍTICO" in flags_text, "Dado com 500 dias de defasagem deve gerar flag CRÍTICO"

    def test_flag_stale_data_warning(self):
        """Dado com defasagem entre 90 e 365 dias → flag de aviso (não crítico)."""
        from agente.nodes.auditor import auditor_node

        stats = {
            "gini": {
                "latest_value": 52.0, "latest_date": "2023-01-01",
                "lag_days": 120, "zscore_latest": 0.1,
                "percentile_rank": 50, "trend_3m": "estável",
            }
        }
        result = auditor_node(self._base_state(historical_stats=stats))
        flags_text = " ".join(result["audit_flags"])
        assert "DEFASADO" in flags_text, "Dado com 120 dias deve gerar flag DEFASADO"
        assert "CRÍTICO" not in flags_text

    def test_flag_outlier_zscore_high(self):
        """Z-score ≥ 2.5 deve gerar flag OUTLIER."""
        from agente.nodes.auditor import auditor_node

        stats = {
            "selic": {
                "latest_value": 26.0, "latest_date": "2025-01-01",
                "lag_days": 10, "zscore_latest": 3.8,
                "percentile_rank": 99, "trend_3m": "alta",
            }
        }
        result = auditor_node(self._base_state(historical_stats=stats))
        flags_text = " ".join(result["audit_flags"])
        assert "OUTLIER" in flags_text, "Z-score 3.8 deve gerar flag OUTLIER HISTÓRICO"

    def test_flag_juros_reais_extreme_high(self):
        """Juros reais > 18% a.a. → flag EXTREMOS."""
        from agente.nodes.auditor import auditor_node

        dates = pd.date_range(end=pd.Timestamp.now(), periods=12, freq="MS")
        df_jr = pd.DataFrame(
            {"juros_reais": [0.22] * 12, "juros_reais_pct": [22.0] * 12},
            index=dates,
        )
        result = auditor_node(self._base_state(derived_data={"juros_reais": df_jr}))
        flags_text = " ".join(result["audit_flags"])
        assert "EXTREMOS" in flags_text, "Juros reais 22% deve gerar flag EXTREMOS"

    def test_flag_juros_reais_negative(self):
        """Juros reais < -3% a.a. → flag NEGATIVOS."""
        from agente.nodes.auditor import auditor_node

        dates = pd.date_range(end=pd.Timestamp.now(), periods=12, freq="MS")
        df_jr = pd.DataFrame(
            {"juros_reais": [-0.05] * 12, "juros_reais_pct": [-5.0] * 12},
            index=dates,
        )
        result = auditor_node(self._base_state(derived_data={"juros_reais": df_jr}))
        flags_text = " ".join(result["audit_flags"])
        assert "NEGATIVOS" in flags_text, "Juros reais -5% deve gerar flag NEGATIVOS"

    def test_flag_juros_reais_normal_range_produces_info_flag(self):
        """Juros reais dentro do intervalo normal (ex: 7%) → flag informativo (não crítico)."""
        from agente.nodes.auditor import auditor_node

        dates = pd.date_range(end=pd.Timestamp.now(), periods=12, freq="MS")
        df_jr = pd.DataFrame(
            {"juros_reais": [0.07] * 12, "juros_reais_pct": [7.0] * 12},
            index=dates,
        )
        result = auditor_node(self._base_state(derived_data={"juros_reais": df_jr}))
        flags_text = " ".join(result["audit_flags"])
        # Flag informativo deve existir, mas sem EXTREMOS ou NEGATIVOS
        assert "EXTREMOS" not in flags_text
        assert "NEGATIVOS" not in flags_text
        assert "JUROS REAIS" in flags_text, "Flag informativo de juros reais deve aparecer"

    def test_multiple_flags_counted_in_summary(self):
        """audit_summary deve informar o número correto de avisos."""
        from agente.nodes.auditor import auditor_node

        # Dois problemas: dado defasado crítico + outlier extremo
        stats = {
            "ipca": {
                "latest_value": 25.0, "latest_date": "2019-01-01",
                "lag_days": 400, "zscore_latest": 4.5,
                "percentile_rank": 99, "trend_3m": "alta",
            }
        }
        result = auditor_node(self._base_state(historical_stats=stats))
        assert len(result["audit_flags"]) >= 2, "Devem ser gerados >= 2 flags distintos"
        # Summary deve conter o contador de avisos
        assert "aviso" in result["audit_summary"].lower()

    def test_taylor_flag_when_selic_high_and_ipca_rising(self):
        """Selic > 10% com IPCA em tendência de alta → alerta Taylor/tensão monetária."""
        from agente.nodes.auditor import auditor_node

        stats = {
            "432": {
                "latest_value": 13.75, "latest_date": "2025-01-01",
                "lag_days": 15, "zscore_latest": 1.0,
                "percentile_rank": 70, "trend_3m": "estável",
            },
            "ipca": {
                "latest_value": 0.82, "latest_date": "2025-01-01",
                "lag_days": 15, "zscore_latest": 1.5,
                "percentile_rank": 75, "trend_3m": "alta",
            },
        }
        result = auditor_node(self._base_state(historical_stats=stats))
        flags_text = " ".join(result["audit_flags"])
        assert "TENSÃO" in flags_text or "Taylor" in flags_text, (
            "Selic 13.75% + IPCA em alta deve gerar alerta de tensão monetária (Taylor)"
        )
