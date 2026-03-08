# -*- coding: utf-8 -*-
"""
Ponto de entrada ASGI — Agente Macro-BR.

Entry point para o servidor uvicorn.

EXECUÇÃO LOCAL (desenvolvimento):
    # Linux / macOS / Git Bash / WSL:
    PYTHONPATH=src uvicorn asgi:app --reload --port 8000

    # Windows PowerShell:
    $env:PYTHONPATH="src"; uvicorn asgi:app --reload --port 8000

    # Via Makefile (Linux/macOS/WSL):
    make run-dev

    # Via scripts PowerShell (Windows):
    .\\scripts\\run.ps1 -Command run-dev

EXECUÇÃO EM DOCKER / AWS ECS:
    uvicorn asgi:app --host 0.0.0.0 --port 8000
"""
# Logging deve ser configurado ANTES de qualquer outro import do projeto
from agente.config import get_settings
from logger.config import setup_logging

_settings = get_settings()
setup_logging(
    level=_settings.log_level,
    fmt=_settings.log_format,
    file_path=_settings.log_file_path,
)

# Importação após setup do logging  # noqa: E402
from api.server import create_app

app = create_app()
