# -*- coding: utf-8 -*-
"""Schemas Pydantic para a API REST — Agente Macro-BR."""
from typing import Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Corpo da requisição para o endpoint /ask."""

    question: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Pergunta em linguagem natural sobre indicadores macroeconômicos.",
        examples=["Qual a evolução do IPCA nos últimos 2 anos?"],
    )
    session_id: Optional[str] = Field(
        default=None,
        description="ID de sessão para rastreamento (gerado automaticamente se omitido).",
    )


class QueryResponse(BaseModel):
    """Corpo da resposta do endpoint /ask."""

    session_id: str = Field(description="ID da sessão executada.")
    text: str = Field(description="Resposta analítica gerada pelo agente.")
    plot_base64: Optional[str] = Field(
        default=None,
        description="Gráfico em Base64 URI (data:image/png;base64,...) ou null.",
    )
    has_data: bool = Field(description="True se o agente encontrou dados para a pergunta.")
    error: Optional[str] = Field(
        default=None,
        description="Mensagem de erro, se houver.",
    )


class HealthResponse(BaseModel):
    """Resposta do endpoint de health check."""

    status: str = Field(description="'ok' se o serviço está operacional.")
    version: str = Field(description="Versão da API.")
    environment: str = Field(description="Ambiente de execução.")
