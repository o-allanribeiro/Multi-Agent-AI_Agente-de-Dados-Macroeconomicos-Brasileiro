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
