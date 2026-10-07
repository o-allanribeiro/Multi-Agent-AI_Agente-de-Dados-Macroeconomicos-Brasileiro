# -*- coding: utf-8 -*-
"""
Testes unitários da API REST — Agente Macro-BR.

Usa TestClient do FastAPI (via httpx) para testar endpoints
sem subir um servidor real.
"""

from unittest.mock import patch

import pytest


@pytest.fixture()
def test_client():
    """Cliente de teste para a API FastAPI."""
    from fastapi.testclient import TestClient

    from api.server import create_app

    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """Testes do endpoint GET /health."""

    def test_health_returns_ok(self, test_client):
        """Endpoint /health deve retornar status 200 e body com status='ok'."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "environment" in data

    def test_health_environment_is_testing(self, test_client):
        """Ambiente deve ser 'testing' nos testes."""
        response = test_client.get("/health")
        assert response.json()["environment"] == "testing"


class TestAskEndpoint:
    """Testes do endpoint POST /ask."""

    def test_ask_returns_200_with_valid_question(self, test_client):
        """Endpoint /ask deve retornar 200 com pergunta válida."""
        mock_state = {
            "response": "Análise mock do IPCA.",
            "data": None,
            "plot_path": None,
            "error": None,
        }

        with patch("api.routes.run_agent", return_value=mock_state):
            response = test_client.post(
                "/ask",
                json={"question": "Qual a evolução do IPCA nos últimos 2 anos?"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "session_id" in data
        assert "has_data" in data

    def test_ask_with_short_question_returns_422(self, test_client):
        """Pergunta com menos de 5 caracteres deve retornar 422 (validação Pydantic)."""
        response = test_client.post("/ask", json={"question": "hi"})
        assert response.status_code == 422

    def test_ask_without_question_returns_422(self, test_client):
        """Requisição sem campo question deve retornar 422."""
        response = test_client.post("/ask", json={})
        assert response.status_code == 422

    def test_ask_includes_session_id(self, test_client):
        """Resposta deve conter session_id."""
        mock_state = {
            "response": "Resposta simulada.",
            "data": None,
            "plot_path": None,
            "error": None,
        }

        with patch("api.routes.run_agent", return_value=mock_state):
            response = test_client.post(
                "/ask",
                json={"question": "Qual a taxa Selic atual?"},
            )

        data = response.json()
        assert data["session_id"] is not None
        assert len(data["session_id"]) > 0

    def test_ask_custom_session_id(self, test_client):
        """Session ID fornecido na requisição deve ser mantido na resposta."""
        mock_state = {
            "response": "Resposta.",
            "data": None,
            "plot_path": None,
            "error": None,
        }

        with patch("api.routes.run_agent", return_value=mock_state):
            response = test_client.post(
                "/ask",
                json={"question": "Como está o câmbio dólar?", "session_id": "minha-sessao"},
            )

        assert response.json()["session_id"] == "minha-sessao"


class TestCORSConfiguration:
    """
    Testes de CORS — garante que allow_credentials nunca é habilitado junto
    com origem wildcard ('*'), combinação inválida e sinalizada por scanners
    de segurança (ver docs/CHANGELOG.md).
    """

    def test_default_cors_is_not_wildcard(self, monkeypatch):
        """Sem CORS_ORIGINS configurado, o padrão são só origens locais (nunca '*')."""
        from agente.config import Settings

        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        origins = Settings(_env_file=None).cors_origins_list
        assert "*" not in origins
        assert all("localhost" in o or "127.0.0.1" in o for o in origins)

    def test_credentials_disabled_for_wildcard_origin(self, test_client, monkeypatch):
        """CORS_ORIGINS='*' explícito não deve habilitar allow_credentials."""
        from fastapi.testclient import TestClient

        from agente.config import get_settings

        monkeypatch.setenv("CORS_ORIGINS", "*")
        get_settings.cache_clear()
        import api.server as server_module

        test_client = TestClient(server_module.create_app())
        try:
            self._assert_no_credentials(test_client)
        finally:
            get_settings.cache_clear()

    @staticmethod
    def _assert_no_credentials(test_client):
        response = test_client.options(
            "/health",
            headers={
                "Origin": "https://exemplo.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-credentials") != "true"

    def test_credentials_enabled_for_explicit_origin(self, monkeypatch):
        """Com origem explícita configurada, allow_credentials deve ser habilitado."""
        from fastapi.testclient import TestClient

        from agente.config import get_settings

        monkeypatch.setenv("CORS_ORIGINS", "https://app.orgao.gov.br")
        get_settings.cache_clear()
        try:
            import api.server as server_module

            app = server_module.create_app()
            client = TestClient(app)
            response = client.options(
                "/health",
                headers={
                    "Origin": "https://app.orgao.gov.br",
                    "Access-Control-Request-Method": "GET",
                },
            )
            assert response.headers.get("access-control-allow-credentials") == "true"
        finally:
            get_settings.cache_clear()  # restaura o singleton para os demais testes


class TestAdminDataStatus:
    """
    Testes do endpoint GET /admin/data-status.

    `api/admin.py` importa `get_warehouse_store` no topo do módulo (não
    lazy-import como stats.py), então o mock precisa alvejar
    "api.admin.get_warehouse_store" diretamente — o autouse
    `bypass_warehouse_store` (tests/conftest.py) protege apenas imports locais
    (ex: dentro de stats_node), não este binding de nível de módulo.
    """

    def test_data_status_returns_all_registered_series(self, test_client):
        from unittest.mock import MagicMock

        mock_store = MagicMock()
        mock_store.list_status.return_value = [
            {
                "series_id": "bcb_432",
                "label": "Selic",
                "source": "bcb",
                "frequency": "diario",
                "row_count": 100,
                "first_date": "2020-01-01",
                "last_date": "2026-08-01",
                "lag_days": 1,
                "last_refreshed_at": "2026-08-01T00:00:00",
                "last_error": None,
            }
        ]
        with patch("api.admin.get_warehouse_store", return_value=mock_store):
            response = test_client.get("/admin/data-status")

        assert response.status_code == 200
        data = response.json()["series"]
        assert data[0]["series_id"] == "bcb_432"
        assert data[0]["status_color"] == "green"

    def test_data_status_marks_critical_lag_as_red(self, test_client):
        from unittest.mock import MagicMock

        mock_store = MagicMock()
        mock_store.list_status.return_value = [
            {
                "series_id": "wb_gini",
                "label": "Gini",
                "source": "world_bank",
                "frequency": "anual",
                "row_count": 10,
                "first_date": "1990-01-01",
                "last_date": "2020-01-01",
                "lag_days": 500,
                "last_refreshed_at": None,
                "last_error": None,
            }
        ]
        with patch("api.admin.get_warehouse_store", return_value=mock_store):
            response = test_client.get("/admin/data-status")

        assert response.json()["series"][0]["status_color"] == "red"

    def test_data_status_never_collected_is_gray(self, test_client):
        from unittest.mock import MagicMock

        mock_store = MagicMock()
        mock_store.list_status.return_value = [
            {
                "series_id": "bcb_1",
                "label": "Dólar",
                "source": "bcb",
                "frequency": "diario",
                "row_count": 0,
                "first_date": None,
                "last_date": None,
                "lag_days": None,
                "last_refreshed_at": None,
                "last_error": None,
            }
        ]
        with patch("api.admin.get_warehouse_store", return_value=mock_store):
            response = test_client.get("/admin/data-status")

        assert response.json()["series"][0]["status_color"] == "gray"


class TestAdminRefresh:
    """Testes do endpoint POST /admin/refresh."""

    def test_refresh_returns_results_per_series(self, test_client):
        from warehouse.pipeline import RefreshResult

        fake_results = [
            RefreshResult("bcb_432", "Selic", True, 100),
            RefreshResult("bcb_433", "IPCA", False, 50, error="timeout"),
        ]
        with patch("api.admin.refresh_all", return_value=fake_results):
            response = test_client.post("/admin/refresh")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["succeeded"] == 1
        assert data["results"][1]["error"] == "timeout"


class TestLegacyEndpoint:
    """Testes do endpoint legado POST /ask-agent (compatibilidade)."""

    def test_legacy_endpoint_exists(self, test_client):
        """Endpoint /ask-agent deve existir para compatibilidade com o frontend."""
        mock_state = {
            "response": "Resposta legada.",
            "data": None,
            "plot_path": None,
            "error": None,
        }

        with patch("api.legacy.run_agent", return_value=mock_state):
            response = test_client.post(
                "/ask-agent",
                json={"question": "Qual o IPCA do último mês?"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "plot_base64" in data


class TestAdminRefreshAuth:
    """POST /admin/refresh exige X-API-Key quando ADMIN_API_KEY está configurada."""

    @staticmethod
    def _client(monkeypatch, **env):
        from fastapi.testclient import TestClient

        from agente.config import get_settings

        for key in ("ADMIN_API_KEY", "APP_ENV"):
            monkeypatch.delenv(key, raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        get_settings.cache_clear()
        import api.server as server_module

        return TestClient(server_module.create_app())

    def test_wrong_or_missing_key_is_rejected(self, monkeypatch):
        from agente.config import get_settings

        client = self._client(monkeypatch, ADMIN_API_KEY="segredo-de-teste")
        try:
            with patch("api.admin.refresh_all", return_value=[]) as refresh:
                assert client.post("/admin/refresh").status_code == 401
                assert (
                    client.post("/admin/refresh", headers={"X-API-Key": "errada"}).status_code
                    == 401
                )
                refresh.assert_not_called()
        finally:
            get_settings.cache_clear()

    def test_correct_key_is_accepted(self, monkeypatch):
        from agente.config import get_settings

        client = self._client(monkeypatch, ADMIN_API_KEY="segredo-de-teste")
        try:
            with patch("api.admin.refresh_all", return_value=[]):
                response = client.post("/admin/refresh", headers={"X-API-Key": "segredo-de-teste"})
            assert response.status_code == 200
        finally:
            get_settings.cache_clear()

    def test_disabled_in_production_without_key(self, monkeypatch):
        from agente.config import get_settings

        client = self._client(monkeypatch, APP_ENV="production")
        try:
            with patch("api.admin.refresh_all", return_value=[]) as refresh:
                assert client.post("/admin/refresh").status_code == 503
                refresh.assert_not_called()
        finally:
            get_settings.cache_clear()

    def test_status_endpoint_stays_public(self, monkeypatch):
        from agente.config import get_settings

        client = self._client(monkeypatch, ADMIN_API_KEY="segredo-de-teste")
        try:
            response = client.get("/admin/data-status")
            assert response.status_code == 200
        finally:
            get_settings.cache_clear()


class TestLegacyRateLimit:
    """O endpoint legado /ask-agent tem o mesmo limite de 10/min do /ask."""

    def test_eleventh_request_is_throttled(self, test_client):
        from api.limiter import limiter

        limiter.reset()
        mock_state = {"response": "ok", "data": None, "plot_path": None, "error": None}
        try:
            with patch("api.legacy.run_agent", return_value=mock_state):
                codes = [
                    test_client.post(
                        "/ask-agent", json={"question": "Qual o IPCA do mês?"}
                    ).status_code
                    for _ in range(11)
                ]
        finally:
            limiter.reset()
        assert codes[:10] == [200] * 10
        assert codes[10] == 429

    def test_legacy_rejects_oversized_question(self, test_client):
        response = test_client.post("/ask-agent", json={"question": "x" * 501})
        assert response.status_code == 422
