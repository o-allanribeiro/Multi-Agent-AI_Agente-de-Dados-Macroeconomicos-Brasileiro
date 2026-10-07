# -*- coding: utf-8 -*-
"""
Proteção das rotas administrativas.

Política de ``require_admin_key``:
  - ``ADMIN_API_KEY`` definida → o header ``X-API-Key`` deve coincidir (401 caso contrário);
  - ``ADMIN_API_KEY`` ausente em produção → rota desabilitada (503);
  - ``ADMIN_API_KEY`` ausente fora de produção → liberada (uso local/demonstração).
"""

import secrets
from typing import Optional

from fastapi import Header, HTTPException

from agente.config import get_settings


async def require_admin_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    """Dependência FastAPI que valida a chave administrativa."""
    settings = get_settings()
    expected = (settings.admin_api_key or "").strip()

    if not expected:
        if settings.is_production():
            raise HTTPException(
                status_code=503,
                detail="Rota administrativa desabilitada: defina ADMIN_API_KEY.",
            )
        return

    if not x_api_key or not secrets.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Chave de administrador inválida ou ausente.")
