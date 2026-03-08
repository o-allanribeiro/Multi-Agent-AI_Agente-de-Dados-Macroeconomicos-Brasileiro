# -*- coding: utf-8 -*-
"""
SQLiteBackend — Persistência local via SQLite.

Usado em desenvolvimento e em deploys on-premises simples.
Para produção AWS, substituir por DynamoDBBackend.

Não requer dependências externas (usa sqlite3 nativo do Python).
"""
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator, List, Optional

from storage.base import ConversationRecord, StorageBackend

logger = logging.getLogger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS conversations (
    session_id  TEXT PRIMARY KEY,
    question    TEXT NOT NULL,
    response    TEXT NOT NULL,
    has_data    INTEGER NOT NULL DEFAULT 0,
    has_plot    INTEGER NOT NULL DEFAULT 0,
    error       TEXT,
    timestamp   TEXT NOT NULL
);
"""


class SQLiteBackend(StorageBackend):
    """
    Backend SQLite para persistência de conversas.

    Thread-safe: usa ``check_same_thread=False`` com controle
    explícito de transação via context manager.

    Parameters
    ----------
    database_url : str
        URL do banco SQLite. Exemplos:
        - ``sqlite:///./agente_macro.db`` (arquivo relativo)
        - ``sqlite:////abs/path/db.sqlite``
        - ``sqlite:///:memory:`` (apenas em testes)
    """

    def __init__(self, database_url: str) -> None:
        # Remove prefixo 'sqlite:///' para obter o path do arquivo
        self._db_path = database_url.replace("sqlite:///", "")
        self._initialize()

    def _initialize(self) -> None:
        """Cria a tabela se não existir."""
        with self._conn() as conn:
            conn.execute(_DDL)
        logger.debug("SQLiteBackend inicializado | path=%s", self._db_path)

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def save(self, record: ConversationRecord) -> None:
        """Insere ou atualiza (upsert) uma conversa."""
        sql = """
        INSERT INTO conversations
            (session_id, question, response, has_data, has_plot, error, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            response  = excluded.response,
            has_data  = excluded.has_data,
            has_plot  = excluded.has_plot,
            error     = excluded.error,
            timestamp = excluded.timestamp
        """
        with self._conn() as conn:
            conn.execute(
                sql,
                (
                    record.session_id,
                    record.question,
                    record.response,
                    int(record.has_data),
                    int(record.has_plot),
                    record.error,
                    record.timestamp.isoformat(),
                ),
            )
        logger.debug("Conversa salva | session=%s", record.session_id)

    def get(self, session_id: str) -> Optional[ConversationRecord]:
        """Recupera conversa por session_id (ou None se não encontrado)."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM conversations WHERE session_id = ?",
                (session_id,),
            ).fetchone()

        if row is None:
            return None

        return ConversationRecord(
            session_id=row["session_id"],
            question=row["question"],
            response=row["response"],
            has_data=bool(row["has_data"]),
            has_plot=bool(row["has_plot"]),
            error=row["error"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
        )

    def list_recent(self, limit: int = 20) -> List[ConversationRecord]:
        """Retorna as N conversas mais recentes, ordenadas por timestamp desc."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM conversations ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()

        return [
            ConversationRecord(
                session_id=r["session_id"],
                question=r["question"],
                response=r["response"],
                has_data=bool(r["has_data"]),
                has_plot=bool(r["has_plot"]),
                error=r["error"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
            )
            for r in rows
        ]

    def health_check(self) -> bool:
        """Verifica se o banco está acessível."""
        try:
            with self._conn() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as exc:
            logger.error("SQLite health check falhou: %s", exc)
            return False
