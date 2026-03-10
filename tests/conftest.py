# -*- coding: utf-8 -*-
"""
conftest.py — Fixtures globais de pytest — Agente Macro-BR.

As fixtures definidas aqui são disponíveis automaticamente
para todos os testes sem necessidade de import explícito.
"""
import os

import pandas as pd
import pytest

# Garante ambiente de testes para todos os testes
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("LOG_LEVEL", "ERROR")
os.environ.setdefault("LOG_FORMAT", "text")
os.environ.setdefault("GOOGLE_API_KEY", "test-key-mock")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("STORAGE_BACKEND", "sqlite")


@pytest.fixture(scope="session")
def sample_ipca_df() -> pd.DataFrame:
    """DataFrame de IPCA simulado para testes."""
    dates = pd.date_range(start="2022-01-01", periods=24, freq="MS")
    values = [0.54, 1.01, 1.62, 1.06, 0.47, 0.67, -0.22, -0.73, -0.29, 0.59,
              0.41, 0.54, 0.53, 0.84, 0.71, 0.61, 0.23, 0.16, -0.02, 0.26,
              0.24, 0.83, 0.89, 0.62]
    return pd.DataFrame({"433": values}, index=dates)


@pytest.fixture(scope="session")
def sample_selic_df() -> pd.DataFrame:
    """DataFrame de Taxa Selic simulado para testes."""
    dates = pd.date_range(start="2021-01-01", periods=36, freq="MS")
    values = [2.0] * 6 + [5.25, 6.25, 7.25, 8.75, 9.25, 10.75,
                           11.75, 12.75, 13.25, 13.25, 13.75, 13.75,
                           13.75, 13.75, 13.25, 12.75, 11.75, 11.25,
                           10.75, 10.50, 10.25, 10.25, 10.25, 10.50,
                           10.50, 10.50, 10.75, 10.75, 10.75, 11.25]
    return pd.DataFrame({"432": values}, index=dates)


@pytest.fixture(scope="session")
def sample_gini_df() -> pd.DataFrame:
    """DataFrame de Coeficiente de Gini simulado para testes."""
    years = list(range(2000, 2020))
    dates = pd.to_datetime([f"{y}-01-01" for y in years])
    values = [59.3, 59.0, 58.7, 58.3, 57.8, 57.1, 56.3, 55.4, 54.7, 53.9,
              53.1, 52.7, 52.3, 52.0, 51.5, 51.1, 53.3, 53.4, 53.9, 53.4]
    return pd.DataFrame({"SI.POV.GINI": values}, index=dates)


@pytest.fixture(autouse=True)
def bypass_series_cache(monkeypatch):
    """
    Desabilita o cache de séries durante testes para garantir determinismo.

    O SeriesCache é um singleton SQLite. Sem este bypass, mocks de API
    (sgs.get, requests.get) são ignorados porque o cache retorna dados
    frescos de execuções anteriores. Esta fixture substitui get_series_cache
    em todos os módulos de ferramentas por um mock que sempre retorna miss.
    """
    from unittest.mock import MagicMock

    mock_cache = MagicMock()
    mock_cache.get.return_value = (None, False)  # sempre cache miss
    mock_cache.set.return_value = None
    mock_cache.clear_all.return_value = None

    noop = lambda: mock_cache  # noqa: E731

    import tools.bcb as _bcb
    import tools.cache as _cache
    import tools.ibge as _ibge
    import tools.ipea as _ipea
    import tools.world_bank as _wb

    monkeypatch.setattr(_cache, "_cache_instance", mock_cache)
    monkeypatch.setattr(_bcb, "get_series_cache", noop)
    monkeypatch.setattr(_ipea, "get_series_cache", noop)
    monkeypatch.setattr(_ibge, "get_series_cache", noop)
    monkeypatch.setattr(_wb, "get_series_cache", noop)


@pytest.fixture()
def mock_agent_state() -> dict:
    """Estado inicial mínimo para testes de nós individuais (inclui campos Onda 3)."""
    return {
        "question": "Qual a evolução do IPCA nos últimos 2 anos?",
        "session_id": "test-001",
        "plan": None,
        "tool_to_use": None,
        "tool_params": None,
        "intermediate_steps": [],
        "data": None,
        "analysis": None,
        "plot_path": None,
        "response": None,
        "error": None,
        # Campos Onda 3
        "historical_stats": {},
        "historical_stats_text": "",
        "derived_data": {},
        "audit_flags": [],
        "audit_summary": "",
    }


@pytest.fixture()
def mock_state_with_data(mock_agent_state, sample_ipca_df) -> dict:
    """Estado com dados IPCA pré-carregados para testar nós de análise/plot/response."""
    state = mock_agent_state.copy()
    state["data"] = sample_ipca_df
    state["plan"] = "Buscar série IPCA dos últimos 2 anos."
    state["tool_to_use"] = "get_bcb_series"
    state["tool_params"] = {"series_code": 433, "last_n_years": 2}
    return state


@pytest.fixture(scope="session")
def sample_combined_df(sample_selic_df, sample_ipca_df) -> pd.DataFrame:
    """DataFrame combinado Selic + IPCA para testes de indicadores derivados."""
    # Renomeia para os nomes canônicos esperados por derived.py
    selic = sample_selic_df.rename(columns={"432": "432"})
    ipca = sample_ipca_df.rename(columns={"433": "433"})
    combined = pd.concat([selic, ipca], axis=1).dropna()
    return combined
