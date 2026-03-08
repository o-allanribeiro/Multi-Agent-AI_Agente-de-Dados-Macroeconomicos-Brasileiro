# -*- coding: utf-8 -*-
"""
Factory da aplicação FastAPI — Agente Macro-BR.

Centraliza a criação e configuração da app FastAPI:
  - Registro de middlewares (CORS, logging de requests)
  - Inclusão de routers
  - Configuração de docs (Swagger/OpenAPI)

Uso:
    from api.server import create_app
    app = create_app()
"""
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from agente.config import get_settings
from api.routes import router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Cria e configura a instância da aplicação FastAPI.

    Returns
    -------
    FastAPI
        Aplicação completamente configurada, pronta para servir requisições.
    """
    settings = get_settings()

    app = FastAPI(
        title="Agente Macro-BR — API",
        description=(
            "API do Agente de IA para Análise de Dados Macroeconômicos Brasileiros. "
            "Processa perguntas em linguagem natural sobre indicadores econômicos "
            "e retorna análises textuais com visualizações gráficas."
        ),
        version="0.1.0",
        docs_url="/docs" if not settings.is_production() else None,
        redoc_url="/redoc" if not settings.is_production() else None,
        license_info={"name": "Apache 2.0", "url": "https://www.apache.org/licenses/LICENSE-2.0"},
    )

    # -------------------------------------------------------------------------
    # Middleware de CORS
    # -------------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )

    # -------------------------------------------------------------------------
    # Middleware de logging de requests (timing)
    # -------------------------------------------------------------------------
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "HTTP | %s %s | status=%d | duration=%.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    # -------------------------------------------------------------------------
    # Eventos de lifecycle
    # -------------------------------------------------------------------------
    @app.on_event("startup")
    async def on_startup():
        logger.info(
            "API iniciada | env=%s | host=%s | port=%d",
            settings.app_env,
            settings.api_host,
            settings.api_port,
        )

    @app.on_event("shutdown")
    async def on_shutdown():
        logger.info("API encerrada.")

    # -------------------------------------------------------------------------
    # Routers
    # -------------------------------------------------------------------------
    app.include_router(router)

    # Endpoint legado para compatibilidade com o frontend existente
    from api.legacy import legacy_router
    app.include_router(legacy_router)

    return app
