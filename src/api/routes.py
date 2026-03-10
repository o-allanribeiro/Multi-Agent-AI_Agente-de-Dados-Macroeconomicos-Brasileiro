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
import time
import uuid

from fastapi import APIRouter, HTTPException, Request

from agente.agent import run_agent
from agente.config import get_settings
from api.limiter import limiter
from api.schemas import HealthResponse, QueryRequest, QueryResponse
from storage import ConversationRecord, get_storage
from utils.cost_tracker import log_request_cost

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
@limiter.limit("10/minute")
async def ask_agent(request: Request, query: QueryRequest) -> QueryResponse:
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
    start_time = time.perf_counter()

    logger.info(
        "Nova requisição | session=%s | question='%s'",
        session_id,
        query.question[:80],
    )

    try:
        final_state = run_agent(question=query.question, session_id=session_id)
        duration_ms = (time.perf_counter() - start_time) * 1000

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

        # Loga estimativa de custo da requisição
        # n_tools = número de séries únicas coletadas (colunas do DataFrame final)
        data_df = final_state.get("data")
        n_tools = len(data_df.columns) if data_df is not None and not data_df.empty else 1
        tools_used = [str(c) for c in data_df.columns] if data_df is not None and not data_df.empty else [final_state.get("tool_to_use", "unknown")]
        log_request_cost(
            session_id=session_id,
            tools_used=tools_used,
            has_data=final_state.get("data") is not None,
            has_plot=plot_base64 is not None,
            duration_ms=duration_ms,
        )

        response_text = final_state.get("response") or "Não foi possível gerar uma resposta."
        has_data = final_state.get("data") is not None
        has_plot = plot_base64 is not None

        # Persiste conversa no storage configurado (SQLite ou DynamoDB)
        try:
            storage = get_storage()
            storage.save(
                ConversationRecord(
                    session_id=session_id,
                    question=query.question,
                    response=response_text,
                    has_data=has_data,
                    has_plot=has_plot,
                    error=final_state.get("error"),
                )
            )
            logger.debug("Conversa persistida | session=%s | backend=%s", session_id, type(storage).__name__)
        except Exception as exc_storage:
            logger.warning("Falha ao persistir conversa | session=%s | error=%s", session_id, exc_storage)

        return QueryResponse(
            session_id=session_id,
            text=response_text,
            plot_base64=plot_base64,
            has_data=has_data,
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
