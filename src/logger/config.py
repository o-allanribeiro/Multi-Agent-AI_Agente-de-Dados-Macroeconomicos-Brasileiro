# -*- coding: utf-8 -*-
"""
Módulo de logging estruturado — Agente Macro-BR.

Configura o sistema de logging Python com:
  - Formato JSON (produção / CloudWatch) ou texto legível (desenvolvimento)
  - Compatível com AWS CloudWatch Logs via watchtower (opcional)
  - Rastreabilidade por session_id
"""
import json
import logging
import logging.config
import sys
from datetime import datetime, timezone
from typing import Optional


class _JsonFormatter(logging.Formatter):
    """
    Formatter que serializa cada registro de log como uma linha JSON.

    Compatível com o formato esperado pelo AWS CloudWatch Logs Insights,
    facilitando queries de análise de erros em produção.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Campos extras opcionais (adicionados via extra={})
        for field in ("session_id", "tool_name", "duration_ms"):
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)

        # Rastreamento de exceções
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


class _TextFormatter(logging.Formatter):
    """
    Formatter texto com cores ANSI para desenvolvimento local.
    """

    COLORS = {
        "DEBUG": "\033[36m",     # Ciano
        "INFO": "\033[32m",      # Verde
        "WARNING": "\033[33m",   # Amarelo
        "ERROR": "\033[31m",     # Vermelho
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        reset = self.COLORS["RESET"]
        record.levelname = f"{color}{record.levelname:<8}{reset}"
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    fmt: str = "json",
    file_path: Optional[str] = None,
) -> None:
    """
    Configura o sistema de logging para toda a aplicação.

    Deve ser chamado UMA VEZ na inicialização da aplicação, antes de
    qualquer outro módulo realizar logging.

    Parameters
    ----------
    level : str
        Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    fmt : str
        Formato de saída: "json" (produção) ou "text" (desenvolvimento).
    file_path : Optional[str]
        Se fornecido, também escreve logs em arquivo. Útil para dev local.
    """
    # Seleciona o formatter
    if fmt.lower() == "json":
        formatter: logging.Formatter = _JsonFormatter()
    else:
        formatter = _TextFormatter(
            fmt="%(asctime)s | %(levelname)s | %(name)-30s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Handler principal: stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)

    handlers: list[logging.Handler] = [stdout_handler]

    # Handler opcional: arquivo
    if file_path:
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Configura o root logger
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=handlers,
        force=True,  # Sobrescreve qualquer configuração anterior
    )

    # Silencia loggers ruidosos de terceiros
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)

    logging.getLogger(__name__).debug(
        "Sistema de logging configurado | level=%s | format=%s", level, fmt
    )
