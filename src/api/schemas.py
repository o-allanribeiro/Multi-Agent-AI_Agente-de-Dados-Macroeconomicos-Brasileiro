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
    cost_estimate_usd: float = Field(
        default=0.0,
        description="Estimativa de custo em USD para esta requisição (Gemini tokens).",
    )
    error: Optional[str] = Field(
        default=None,
        description="Mensagem de erro, se houver.",
    )


class ConversationItem(BaseModel):
    """Item de histórico retornado pelo endpoint /history."""

    session_id: str
    question: str
    response: str
    has_data: bool
    has_plot: bool
    timestamp: str
    error: Optional[str] = None


class HistoryResponse(BaseModel):
    """Corpo da resposta do endpoint /history."""

    conversations: list[ConversationItem]
    total: int


class HealthResponse(BaseModel):
    """Resposta do endpoint de health check."""

    status: str = Field(description="'ok' se o serviço está operacional.")
    version: str = Field(description="Versão da API.")
    environment: str = Field(description="Ambiente de execução.")


class SeriesStatusItem(BaseModel):
    """Status de atualização de uma série do data warehouse histórico."""

    series_id: str = Field(description="Identificador da série no warehouse (ex: 'bcb_432').")
    label: str = Field(description="Nome amigável do indicador.")
    source: str = Field(description="Fonte de dados ('bcb' | 'ibge' | 'ipea' | 'world_bank').")
    frequency: str = Field(description="Frequência da série.")
    row_count: int = Field(description="Número de linhas salvas no histórico.")
    first_date: Optional[str] = Field(default=None, description="Data do primeiro ponto salvo.")
    last_date: Optional[str] = Field(default=None, description="Data do último ponto salvo.")
    lag_days: Optional[int] = Field(
        default=None, description="Dias entre o último ponto salvo e hoje."
    )
    last_refreshed_at: Optional[str] = Field(
        default=None, description="Timestamp UTC da última tentativa de atualização."
    )
    last_error: Optional[str] = Field(
        default=None, description="Erro da última tentativa de atualização, se houver."
    )
    status_color: str = Field(description="'green' | 'amber' | 'red' | 'gray' (nunca coletada).")


class DataStatusResponse(BaseModel):
    """Corpo da resposta do endpoint GET /admin/data-status."""

    series: list[SeriesStatusItem]


class SeriesRefreshResult(BaseModel):
    """Resultado da atualização de uma série individual."""

    series_id: str
    label: str
    success: bool
    rows_after: int
    error: Optional[str] = None


class RefreshResponse(BaseModel):
    """Corpo da resposta do endpoint POST /admin/refresh."""

    results: list[SeriesRefreshResult]
    total: int
    succeeded: int
