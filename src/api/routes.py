# -*- coding: utf-8 -*-
"""
Rotas da API REST — Agente Macro-BR.

Define os endpoints HTTP expostos pelo servidor FastAPI.

Endpoints:
  GET  /health  → Health check
  POST /ask     → Submete pergunta ao agente
"""
import base64
import logging
import uuid

from fastapi import APIRouter, HTTPException

from agente.agent import run_agent
from agente.config import get_settings
from api.schemas import HealthResponse, QueryRequest, QueryResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Monitoramento"])
async def health_check() -> HealthResponse:
    """
    Endpoint de verificação de saúde do serviço.

    Utilizado por load balancers (ALB) e pipelines de CI/CD
    para confirmar que o serviço está operacional.
    """
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version="0.1.0",
        environment=settings.app_env,
    )


@router.post("/ask", response_model=QueryResponse, tags=["Agente"])
async def ask_agent(query: QueryRequest) -> QueryResponse:
    """
    Submete uma pergunta ao agente de análise macroeconômica.

    O agente executa o pipeline completo (Planner → Action → Analysis → Plot → Response)
    de forma síncrona e retorna a análise textual junto com o gráfico (se gerado).

    **Exemplos de perguntas:**
    - "Qual a evolução do IPCA nos últimos 2 anos?"
    - "Me mostre a trajetória da Selic desde 2022."
    - "Como está o Coeficiente de Gini no Brasil?"
    """
    session_id = query.session_id or str(uuid.uuid4())[:8]

    logger.info(
        "Nova requisição | session=%s | question='%s'",
        session_id,
        query.question[:80],
    )

    try:
        final_state = run_agent(question=query.question, session_id=session_id)

        # Codifica o gráfico em Base64 se existir
        plot_base64: str | None = None
        plot_path = final_state.get("plot_path")

        if plot_path:
            try:
                with open(plot_path, "rb") as img_file:
                    encoded = base64.b64encode(img_file.read()).decode("utf-8")
                    plot_base64 = f"data:image/png;base64,{encoded}"
                logger.info("Gráfico codificado em Base64 | session=%s", session_id)
            except OSError as exc:
                logger.warning(
                    "Não foi possível ler o gráfico | session=%s | path=%s | error=%s",
                    session_id,
                    plot_path,
                    exc,
                )

        return QueryResponse(
            session_id=session_id,
            text=final_state.get("response") or "Não foi possível gerar uma resposta.",
            plot_base64=plot_base64,
            has_data=final_state.get("data") is not None,
            error=final_state.get("error"),
        )

    except Exception as exc:
        logger.error(
            "Erro interno no processamento | session=%s | error=%s",
            session_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno do servidor: {exc}",
        )
