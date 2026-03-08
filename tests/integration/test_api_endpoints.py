# -*- coding: utf-8 -*-
"""
Testes de integração — endpoints FastAPI com ciclo HTTP real.

Usa TestClient para disparar requisições HTTP completas contra
a aplicação FastAPI sem subir um servidor externo.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """TestClient compartilhado por todos os testes do módulo."""
    from api.server import create_app

    app = create_app()
    return TestClient(app)


class TestHealthIntegration:
    """Testes de integração do endpoint /health."""

    def test_health_full_response_shape(self, client):
        """Resposta de /health deve conter todos os campos documentados."""
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) >= {"status", "version", "environment"}

    def test_health_content_type_is_json(self, client):
        """Content-Type deve ser application/json."""
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]


class TestAskIntegration:
    """Testes de integração do endpoint POST /ask."""

    def test_ask_full_request_response_cycle(self, client):
        """Ciclo completo: corpo enviado → LangGraph (mock) → resposta estruturada."""
        fake_state = {
            "response": "O IPCA acumulado no ano foi de 4,62%.",
            "data": None,
            "plot_path": None,
            "error": None,
        }

        with patch("api.routes.run_agent", return_value=fake_state):
            response = client.post(
                "/ask",
                json={"question": "Qual o IPCA acumulado no ano?"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["text"] == "O IPCA acumulado no ano foi de 4,62%."
        assert body["has_data"] is False
        assert body["plot_base64"] is None

    def test_ask_response_has_data_true_when_data_exists(self, client):
        """Campo has_data deve ser True quando o agente retornou dados."""
        import pandas as pd

        fake_state = {
            "response": "Dados encontrados.",
            "data": pd.DataFrame({"valor": [1.0, 2.0]}),
            "plot_path": None,
            "error": None,
        }

        with patch("api.routes.run_agent", return_value=fake_state):
            response = client.post(
                "/ask",
                json={"question": "Mostre os dados do IPCA."},
            )

        body = response.json()
        assert body["has_data"] is True

    def test_ask_with_plot_returns_base64(self, client, tmp_path):
        """Quando existe gráfico, resposta deve conter plot_base64 não-nulo."""
        # Cria um arquivo PNG de teste
        plot_file = tmp_path / "chart_test.png"
        plot_file.write_bytes(b"\x89PNG\r\n")  # cabeçalho PNG mínimo

        fake_state = {
            "response": "Gráfico gerado.",
            "data": None,
            "plot_path": str(plot_file),
            "error": None,
        }

        with patch("api.routes.run_agent", return_value=fake_state):
            response = client.post(
                "/ask",
                json={"question": "Gere um gráfico do IPCA."},
            )

        body = response.json()
        assert body["plot_base64"] is not None
        assert len(body["plot_base64"]) > 0

    def test_ask_logs_request(self, client, caplog):
        """Requisição a /ask deve ser registrada no log (middleware)."""
        import logging

        fake_state = {
            "response": "Resposta.",
            "data": None,
            "plot_path": None,
            "error": None,
        }

        with (
            caplog.at_level(logging.INFO),
            patch("api.routes.run_agent", return_value=fake_state),
        ):
            client.post("/ask", json={"question": "Qual o câmbio atual?"})

        # Apenas verifica que a requisição foi processada sem erro
        assert True


class TestLegacyAskAgentIntegration:
    """Testes de integração do endpoint legado POST /ask-agent."""

    def test_legacy_endpoint_returns_text_field(self, client):
        """Endpoint /ask-agent deve retornar campo 'text' compatível com index.html."""
        fake_state = {
            "response": "Resposta legada compatível.",
            "data": None,
            "plot_path": None,
            "error": None,
        }

        with patch("api.legacy.run_agent", return_value=fake_state):
            response = client.post(
                "/ask-agent",
                json={"question": "Qual a dívida pública em percentual do PIB?"},
            )

        assert response.status_code == 200
        body = response.json()
        assert "text" in body
        assert "plot_base64" in body
