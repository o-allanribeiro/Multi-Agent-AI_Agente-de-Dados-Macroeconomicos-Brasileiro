# -*- coding: utf-8 -*-
"""
Rota legada — compatibilidade com o frontend existente (index.html).

O frontend original faz POST /ask-agent. Este router mantém esse
endpoint funcionando enquanto o frontend não é atualizado para /ask.
"""
import base64
import logging
import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from agente.agent import run_agent

logger = logging.getLogger(__name__)

legacy_router = APIRouter(tags=["Legado (compatibilidade)"])


class _LegacyQuery(BaseModel):
    question: str


@legacy_router.post("/ask-agent")
async def ask_agent_legacy(query: _LegacyQuery):
    """Endpoint legado — mantido para compatibilidade com o frontend index.html."""
    session_id = str(uuid.uuid4())[:8]
    logger.info("Requisição legada /ask-agent | session=%s", session_id)

    final_state = run_agent(question=query.question, session_id=session_id)

    plot_base64 = None
    plot_path = final_state.get("plot_path")
    if plot_path:
        try:
            with open(plot_path, "rb") as img_file:
                encoded = base64.b64encode(img_file.read()).decode("utf-8")
                plot_base64 = f"data:image/png;base64,{encoded}"
        except OSError:
            pass

    return {
        "text": final_state.get("response") or "Não consegui gerar uma resposta.",
        "plot_base64": plot_base64,
    }
