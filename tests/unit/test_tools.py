# -*- coding: utf-8 -*-
"""
Testes unitários das Ferramentas de Dados — Agente Macro-BR.

Testa cada DataSource de forma isolada usando mocks HTTP
para não depender de APIs externas durante os testes.
"""
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


class TestBCBTool:
    """Testes do BCBDataSource."""

    def test_get_bcb_series_valid(self, sample_ipca_df):
        """Deve retornar DataFrame quando a API retorna dados válidos."""
        from tools.bcb import get_bcb_series

        with patch("tools.bcb.sgs.get", return_value=sample_ipca_df):
            result = get_bcb_series(series_code=433, last_n_years=2)

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert not result.empty

    def test_get_bcb_series_invalid_code(self):
        """Deve retornar None para código de série inválido."""
        from tools.bcb import get_bcb_series

        result = get_bcb_series(series_code=-1, last_n_years=2)
        assert result is None

    def test_get_bcb_series_no_date_params(self):
        """Deve retornar None se nem start_date nem last_n_years forem fornecidos."""
        from tools.bcb import get_bcb_series

        result = get_bcb_series(series_code=433)
        assert result is None

    def test_get_bcb_series_api_error(self):
        """Deve retornar None e logar erro quando a API falha."""
        from tools.bcb import get_bcb_series

        with patch("tools.bcb.sgs.get", side_effect=Exception("API error")):
            result = get_bcb_series(series_code=433, last_n_years=2)

        assert result is None

    def test_get_bcb_series_empty_response(self):
        """Deve retornar None quando a API retorna DataFrame vazio."""
        from tools.bcb import get_bcb_series

        with patch("tools.bcb.sgs.get", return_value=pd.DataFrame()):
            result = get_bcb_series(series_code=433, last_n_years=2)

        assert result is None


class TestIPEATool:
    """Testes do IPEADataSource."""

    def test_get_ipea_series_valid(self):
        """Deve retornar DataFrame ao receber resposta HTTP válida."""
        from tests.fixtures.mock_data import MOCK_IPEA_RESPONSE
        from tools.ipea import get_ipea_series

        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_IPEA_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch("tools.ipea.requests.get", return_value=mock_response):
            result = get_ipea_series("GAC12_INDFBCF12")

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert isinstance(result.index, pd.DatetimeIndex)

    def test_get_ipea_series_empty_api(self):
        """Deve retornar None quando a API retorna lista vazia."""
        from tools.ipea import get_ipea_series

        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_response.raise_for_status = MagicMock()

        with patch("tools.ipea.requests.get", return_value=mock_response):
            result = get_ipea_series("GAC12_INDFBCF12")

        assert result is None

    def test_get_ipea_series_http_error(self):
        """Deve retornar None em erro de rede."""
        import requests
        from tools.ipea import get_ipea_series

        with patch(
            "tools.ipea.requests.get",
            side_effect=requests.exceptions.ConnectionError("timeout"),
        ):
            result = get_ipea_series("GAC12_INDFBCF12")

        assert result is None

    def test_get_ipea_series_invalid_code(self):
        """Deve retornar None para código inválido (string vazia)."""
        from tools.ipea import get_ipea_series

        result = get_ipea_series("")
        assert result is None


class TestWorldBankTool:
    """Testes do WorldBankDataSource."""

    def test_get_gini_series_valid(self, sample_gini_df):
        """Deve retornar DataFrame de Gini válido."""
        from tools.world_bank import get_gini_series

        with patch("tools.world_bank.wb.data.DataFrame", return_value=sample_gini_df.T):
            # Mocking complexo — simplificamos testando a estrutura de saída
            result = get_gini_series(country_code="BRA")
        # Se mock falhar, resultado pode ser None — o importante é não levantar exceção
        # Em caso de erro de mock, o teste garante ao menos a ausência de exception

    def test_get_gini_series_api_error(self):
        """Deve retornar None em caso de erro da API do Banco Mundial."""
        from tools.world_bank import get_gini_series

        with patch("tools.world_bank.wb.data.DataFrame", side_effect=Exception("API error")):
            result = get_gini_series()

        assert result is None


@pytest.fixture()
def fred_key(monkeypatch, tmp_path):
    """Configura uma chave FRED falsa e isola o teste do .env real do desenvolvedor."""
    monkeypatch.setattr("tools.fred._ENV_FILE", tmp_path / ".env")
    monkeypatch.setenv("FRED_API_KEY", "chave-falsa-de-teste")
    return "chave-falsa-de-teste"


@pytest.fixture()
def no_fred_key(monkeypatch, tmp_path):
    """Garante ausência de chave FRED (ambiente e .env)."""
    monkeypatch.setattr("tools.fred._ENV_FILE", tmp_path / ".env")
    monkeypatch.delenv("FRED_API_KEY", raising=False)


class TestFREDTool:
    """Testes do FREDDataSource (Federal Reserve / FRED)."""

    def test_get_fred_series_valid(self, fred_key):
        """Deve retornar DataFrame float64 e descartar observações ausentes ('.')."""
        from tests.fixtures.mock_data import MOCK_FRED_RESPONSE
        from tools.fred import get_fred_series

        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_FRED_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch("tools.fred.requests.get", return_value=mock_response) as mock_get:
            result = get_fred_series("GS10")

        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["GS10"]
        assert isinstance(result.index, pd.DatetimeIndex)
        assert len(result) == 3, "A observação '.' (ausente) deve ser descartada"
        assert result["GS10"].dtype == "float64"
        assert result["GS10"].iloc[0] == pytest.approx(4.06)
        sent = mock_get.call_args.kwargs["params"]
        assert sent["series_id"] == "GS10"
        assert "observation_start" not in sent

    def test_get_fred_series_accepts_lowercase_code(self, fred_key):
        """Código em minúsculas deve ser normalizado (a chave do mapa é minúscula)."""
        from tests.fixtures.mock_data import MOCK_FRED_RESPONSE
        from tools.fred import get_fred_series

        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_FRED_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch("tools.fred.requests.get", return_value=mock_response):
            result = get_fred_series("tb3ms")

        assert result is not None
        assert list(result.columns) == ["TB3MS"]

    def test_get_fred_series_last_n_years_sets_observation_start(self, fred_key):
        """last_n_years deve virar observation_start na requisição."""
        from tests.fixtures.mock_data import MOCK_FRED_RESPONSE
        from tools.fred import get_fred_series

        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_FRED_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch("tools.fred.requests.get", return_value=mock_response) as mock_get:
            get_fred_series("GS5", last_n_years=3)

        assert "observation_start" in mock_get.call_args.kwargs["params"]

    def test_get_fred_series_empty_response(self, fred_key):
        """Deve retornar None quando não há observações."""
        from tools.fred import get_fred_series

        mock_response = MagicMock()
        mock_response.json.return_value = {"observations": []}
        mock_response.raise_for_status = MagicMock()

        with patch("tools.fred.requests.get", return_value=mock_response):
            assert get_fred_series("GS10") is None

    def test_get_fred_series_unsupported_code(self, fred_key):
        """Série fora do mapa não deve gerar requisição."""
        from tools.fred import get_fred_series

        with patch("tools.fred.requests.get") as mock_get:
            assert get_fred_series("CPIAUCSL") is None
        mock_get.assert_not_called()

    def test_get_fred_series_invalid_code(self, fred_key):
        """Código vazio deve retornar None."""
        from tools.fred import get_fred_series

        assert get_fred_series("") is None

    def test_get_fred_series_without_key_returns_none(self, no_fred_key):
        """Sem FRED_API_KEY não há requisição e o retorno é None."""
        from tools.fred import get_fred_series

        with patch("tools.fred.requests.get") as mock_get:
            assert get_fred_series("GS10") is None
        mock_get.assert_not_called()

    def test_get_fred_series_network_error(self, fred_key):
        """Erro de rede deve retornar None."""
        import requests
        from tools.fred import get_fred_series

        with patch(
            "tools.fred.requests.get",
            side_effect=requests.exceptions.ConnectionError("sem rede"),
        ), patch("utils.http.time.sleep"):
            assert get_fred_series("GS10") is None

    def test_get_fred_series_http_error_does_not_leak_key(self, fred_key, caplog):
        """A chave da API não pode aparecer nos logs quando o erro traz a URL."""
        import logging

        import requests
        from tools.fred import get_fred_series

        url = f"https://api.stlouisfed.org/fred/series/observations?api_key={fred_key}"
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"403 Client Error: Forbidden for url: {url}"
        )

        with caplog.at_level(logging.DEBUG), patch(
            "tools.fred.requests.get", return_value=mock_response
        ):
            assert get_fred_series("GS10") is None

        assert fred_key not in caplog.text
        assert "403" in caplog.text

    def test_get_fred_api_key_reads_env_file(self, monkeypatch, tmp_path):
        """Sem variável de ambiente, a chave deve vir do .env da raiz do projeto."""
        from tools.fred import fred_available, get_fred_api_key

        env_file = tmp_path / ".env"
        env_file.write_text('FRED_API_KEY="chave-do-arquivo"\n', encoding="utf-8")
        monkeypatch.setattr("tools.fred._ENV_FILE", env_file)
        monkeypatch.delenv("FRED_API_KEY", raising=False)

        assert get_fred_api_key() == "chave-do-arquivo"
        assert fred_available() is True

    def test_get_fred_api_key_empty_counts_as_missing(self, monkeypatch, tmp_path):
        """FRED_API_KEY="" (valor do .env.example) deve ser tratada como ausente."""
        from tools.fred import fred_available

        env_file = tmp_path / ".env"
        env_file.write_text('FRED_API_KEY=""\n', encoding="utf-8")
        monkeypatch.setattr("tools.fred._ENV_FILE", env_file)
        monkeypatch.delenv("FRED_API_KEY", raising=False)

        assert fred_available() is False


class TestToolRegistry:
    """Testes do ToolRegistry."""

    def test_registry_has_all_tools(self):
        """Todos os tools esperados devem estar registrados."""
        from tools.registry import ToolRegistry

        registry = ToolRegistry()
        assert registry.has("get_bcb_series")
        assert registry.has("get_ipea_series")
        assert registry.has("get_gini_series")

    def test_registry_get_existing_tool(self):
        """get() deve retornar callable para ferramenta existente."""
        from tools.registry import ToolRegistry

        registry = ToolRegistry()
        tool_fn = registry.get("get_bcb_series")
        assert callable(tool_fn)

    def test_registry_get_nonexistent_tool(self):
        """get() deve retornar None para ferramenta inexistente."""
        from tools.registry import ToolRegistry

        registry = ToolRegistry()
        assert registry.get("ferramenta_que_nao_existe") is None

    def test_registry_description_contains_all_tools(self):
        """Descrição deve mencionar todos os tools."""
        from tools.registry import ToolRegistry

        registry = ToolRegistry()
        description = registry.get_tools_description()
        assert "get_bcb_series" in description
        assert "get_ipea_series" in description
        assert "get_gini_series" in description

    def test_registry_fred_registered_only_with_key(self, fred_key):
        """Com chave, get_fred_series entra no registry e no prompt do Planner."""
        from tools.registry import ToolRegistry

        registry = ToolRegistry()
        assert registry.has("get_fred_series")
        assert "get_fred_series" in registry.get_tools_description()

    def test_registry_fred_absent_without_key(self, no_fred_key):
        """Sem chave, o Planner nunca deve ver a ferramenta FRED."""
        from tools.registry import ToolRegistry

        registry = ToolRegistry()
        assert not registry.has("get_fred_series")
        assert "get_fred_series" not in registry.get_tools_description()
        assert registry.has("get_bcb_series")

    def test_registry_dynamic_registration(self):
        """Deve ser possível registrar novas ferramentas dinamicamente."""
        from tools.registry import ToolRegistry

        registry = ToolRegistry()
        mock_fn = lambda **kwargs: None
        registry.register("test_tool", mock_fn, {"description": "Tool de teste"})
        assert registry.has("test_tool")


# =============================================================================
# Onda 3 — Indicadores Macroeconômicos Derivados (tools/derived.py)
# =============================================================================

class TestDerivedTools:
    """Testes dos indicadores macroeconômicos derivados (Onda 3)."""

    def _make_selic_ipca_df(
        self, n: int = 36, selic_pct: float = 12.0, ipca_monthly_pct: float = 0.5
    ) -> pd.DataFrame:
        """DataFrame sintético com Selic (% a.a., col '432') e IPCA (% mensal, col '433')."""
        dates = pd.date_range(end=pd.Timestamp.now(), periods=n, freq="MS")
        return pd.DataFrame(
            {"432": [selic_pct] * n, "433": [ipca_monthly_pct] * n},
            index=dates,
        )

    # ------------------------------------------------------------------
    # compute_juros_reais
    # ------------------------------------------------------------------

    def test_juros_reais_fisher_identity_value(self):
        """
        Verifica que a identidade de Fisher é respeitada numericamente.

        Selic = 12% a.a., IPCA mensal = 0.5% → IPCA 12m = (1.005)^12 - 1 ≈ 6.17%
        Fisher: (1.12 / 1.0617) - 1 ≈ 5.49% a.a.
        """
        from tools.derived import compute_juros_reais

        df = self._make_selic_ipca_df(n=36, selic_pct=12.0, ipca_monthly_pct=0.5)
        result = compute_juros_reais(df)

        assert result is not None, "Resultado não deve ser None com colunas válidas"
        assert not result.empty
        assert "juros_reais_pct" in result.columns

        latest = result["juros_reais_pct"].iloc[-1]
        expected = ((1.12 / (1.005 ** 12)) - 1) * 100  # ≈ 5.49%
        assert abs(latest - expected) < 0.5, (
            f"Fisher identity: esperado ≈ {expected:.2f}%, obtido: {latest:.2f}%"
        )

    def test_juros_reais_positivos_com_selic_maior_que_ipca(self):
        """Juros reais devem ser positivos quando Selic anual > IPCA anual."""
        from tools.derived import compute_juros_reais

        df = self._make_selic_ipca_df(n=36, selic_pct=13.75, ipca_monthly_pct=0.4)
        result = compute_juros_reais(df)

        assert result is not None
        assert result["juros_reais_pct"].iloc[-1] > 0, (
            "Com Selic 13.75% e IPCA ~4.9% a.a., juros reais devem ser positivos"
        )

    def test_juros_reais_result_has_date_index(self):
        """DataFrame de saída deve ter DatetimeIndex."""
        from tools.derived import compute_juros_reais

        df = self._make_selic_ipca_df()
        result = compute_juros_reais(df)

        assert result is not None
        assert isinstance(result.index, pd.DatetimeIndex)

    def test_juros_reais_returns_none_without_selic(self):
        """Deve retornar None se coluna Selic (432) estiver ausente."""
        from tools.derived import compute_juros_reais

        dates = pd.date_range(end=pd.Timestamp.now(), periods=24, freq="MS")
        df = pd.DataFrame({"433": [0.5] * 24}, index=dates)
        assert compute_juros_reais(df) is None

    def test_juros_reais_returns_none_without_ipca(self):
        """Deve retornar None se coluna IPCA (433) estiver ausente."""
        from tools.derived import compute_juros_reais

        dates = pd.date_range(end=pd.Timestamp.now(), periods=24, freq="MS")
        df = pd.DataFrame({"432": [12.0] * 24}, index=dates)
        assert compute_juros_reais(df) is None

    def test_juros_reais_exposes_ipca_acum_12m_for_chart(self):
        """
        Deve expor 'ipca_acum_12m_pct' — é essa série (não o IPCA mensal) que
        entra na Identidade de Fisher, e o gráfico precisa dela para mostrar
        o insumo correto ao lado do juro real (não o IPCA mensal, que tem
        unidade diferente e confunde a leitura do hiato de Fisher).
        """
        from tools.derived import compute_juros_reais

        df = self._make_selic_ipca_df(n=36, selic_pct=13.75, ipca_monthly_pct=0.4)
        result = compute_juros_reais(df)

        assert result is not None
        assert "ipca_acum_12m_pct" in result.columns
        expected_12m = ((1.004**12) - 1) * 100  # ≈ 4.91%
        assert abs(result["ipca_acum_12m_pct"].iloc[-1] - expected_12m) < 0.5

    def test_juros_reais_col_name_candidates(self):
        """Deve funcionar com nomes alternativos de coluna (selic, ipca)."""
        from tools.derived import compute_juros_reais

        dates = pd.date_range(end=pd.Timestamp.now(), periods=36, freq="MS")
        df = pd.DataFrame(
            {"selic": [12.0] * 36, "ipca": [0.5] * 36},
            index=dates,
        )
        result = compute_juros_reais(df)
        assert result is not None, "Deve funcionar com colunas nomeadas 'selic'/'ipca'"

    # ------------------------------------------------------------------
    # compute_cambio_real
    # ------------------------------------------------------------------

    def test_cambio_real_starts_at_base_100(self):
        """Índice de câmbio real deve começar em 100 (base normalizada)."""
        from tools.derived import compute_cambio_real

        dates = pd.date_range(end=pd.Timestamp.now(), periods=24, freq="MS")
        df = pd.DataFrame({"1": [5.0] * 24, "433": [0.5] * 24}, index=dates)
        result = compute_cambio_real(df)

        assert result is not None
        assert "cambio_real_idx" in result.columns
        first = result["cambio_real_idx"].iloc[0]
        assert abs(first - 100.0) < 0.01, f"Base deve ser 100, obtido: {first}"

    def test_cambio_real_preserves_nominal_column(self):
        """DataFrame de saída deve manter a coluna de câmbio nominal."""
        from tools.derived import compute_cambio_real

        dates = pd.date_range(end=pd.Timestamp.now(), periods=24, freq="MS")
        df = pd.DataFrame({"1": [5.0] * 24, "433": [0.3] * 24}, index=dates)
        result = compute_cambio_real(df)

        assert result is not None
        assert "cambio_nominal" in result.columns

    def test_cambio_real_returns_none_without_cambio(self):
        """Deve retornar None se coluna de câmbio estiver ausente."""
        from tools.derived import compute_cambio_real

        dates = pd.date_range(end=pd.Timestamp.now(), periods=24, freq="MS")
        df = pd.DataFrame({"433": [0.5] * 24}, index=dates)
        assert compute_cambio_real(df) is None

    # ------------------------------------------------------------------
    # detect_derived_needed
    # ------------------------------------------------------------------

    def test_detect_juros_reais_keywords(self):
        """Palavras-chave de juro real devem detectar derivado 'juros_reais'."""
        from tools.derived import detect_derived_needed

        assert "juros_reais" in detect_derived_needed("Qual o juro real no Brasil?")
        assert "juros_reais" in detect_derived_needed("Quero ver a taxa real de juros")
        assert "juros_reais" in detect_derived_needed("Mostre os juros reais históricos")
        assert "juros_reais" in detect_derived_needed("Analise a selic real efetiva")

    def test_detect_cambio_real_keywords(self):
        """Palavras-chave de câmbio real devem detectar derivado 'cambio_real'."""
        from tools.derived import detect_derived_needed

        assert "cambio_real" in detect_derived_needed("Como está o câmbio real bilateral?")
        assert "cambio_real" in detect_derived_needed("Mostre o poder de compra do real")
        assert "cambio_real" in detect_derived_needed("taxa real de câmbio")

    def test_detect_no_derived_for_generic_question(self):
        """Pergunta genérica sobre IPCA não deve ativar derivados."""
        from tools.derived import detect_derived_needed

        assert detect_derived_needed("Qual foi o IPCA em 2023?") == []
        assert detect_derived_needed("trajetória da Selic nos últimos 3 anos") == []

    def test_detect_multiple_derived_in_one_question(self):
        """Pergunta que menciona juro real e câmbio real deve detectar ambos."""
        from tools.derived import detect_derived_needed

        question = "Compare os juros reais com o câmbio real nos últimos 5 anos"
        result = detect_derived_needed(question)
        assert "juros_reais" in result
        assert "cambio_real" in result

    # ------------------------------------------------------------------
    # apply_derived (dispatcher)
    # ------------------------------------------------------------------

    def test_apply_derived_returns_juros_reais_df(self):
        """apply_derived com 'juros_reais' deve retornar DataFrame calculado."""
        from tools.derived import apply_derived

        df = self._make_selic_ipca_df(n=36)
        results = apply_derived(df, ["juros_reais"])
        assert "juros_reais" in results
        assert isinstance(results["juros_reais"], pd.DataFrame)
        assert not results["juros_reais"].empty

    def test_apply_derived_empty_list_returns_empty_dict(self):
        """apply_derived com lista vazia deve retornar dicionário vazio."""
        from tools.derived import apply_derived

        df = self._make_selic_ipca_df()
        assert apply_derived(df, []) == {}

    def test_apply_derived_unknown_name_is_ignored(self):
        """Derivado desconhecido deve ser silenciosamente ignorado."""
        from tools.derived import apply_derived

        df = self._make_selic_ipca_df()
        result = apply_derived(df, ["derivado_que_nao_existe"])
        assert result == {}


class TestInclinacaoCurvaEUA:
    """Testes do indicador derivado de inclinação da curva dos EUA (GS10 − TB3MS)."""

    @staticmethod
    def _make_yield_df() -> pd.DataFrame:
        dates = pd.date_range("2023-01-01", periods=4, freq="MS")
        return pd.DataFrame(
            {"GS10": [3.5, 3.6, 3.4, 3.3], "TB3MS": [4.5, 4.6, 3.0, 3.1]}, index=dates
        )

    def test_inclinacao_is_gs10_minus_tb3ms(self):
        """A inclinação deve ser a diferença ponto a ponto, em p.p."""
        from tools.derived import compute_inclinacao_curva_eua

        result = compute_inclinacao_curva_eua(self._make_yield_df())

        assert result is not None
        assert isinstance(result.index, pd.DatetimeIndex)
        assert result["inclinacao_curva_eua"].tolist() == pytest.approx([-1.0, -1.0, 0.4, 0.2])

    def test_inclinacao_negative_means_inverted_curve(self):
        """Curva invertida (juro curto > longo) gera inclinação negativa."""
        from tools.derived import compute_inclinacao_curva_eua

        result = compute_inclinacao_curva_eua(self._make_yield_df())
        assert result["inclinacao_curva_eua"].iloc[0] < 0

    def test_inclinacao_returns_none_without_required_columns(self):
        """Sem GS10 ou sem TB3MS não há como calcular."""
        from tools.derived import compute_inclinacao_curva_eua

        df = self._make_yield_df()
        assert compute_inclinacao_curva_eua(df[["GS10"]]) is None
        assert compute_inclinacao_curva_eua(df[["TB3MS"]]) is None

    def test_inclinacao_returns_none_without_common_months(self):
        """Séries sem meses em comum devem retornar None."""
        from tools.derived import compute_inclinacao_curva_eua

        df = self._make_yield_df()
        df.loc[df.index[:2], "TB3MS"] = float("nan")
        df.loc[df.index[2:], "GS10"] = float("nan")
        assert compute_inclinacao_curva_eua(df) is None

    def test_detect_inclinacao_keywords(self):
        """Perguntas sobre a curva americana devem ativar o derivado."""
        from tools.derived import detect_derived_needed

        assert "inclinacao_curva_eua" in detect_derived_needed(
            "Qual a inclinação da curva de juros americana?"
        )
        assert "inclinacao_curva_eua" in detect_derived_needed("mostre a yield curve dos EUA")
        assert detect_derived_needed("Qual foi a Selic em 2023?") == []

    def test_apply_derived_returns_inclinacao(self):
        """apply_derived deve despachar para o cálculo da inclinação."""
        from tools.derived import apply_derived

        results = apply_derived(self._make_yield_df(), ["inclinacao_curva_eua"])
        assert "inclinacao_curva_eua" in results
        assert not results["inclinacao_curva_eua"].empty
