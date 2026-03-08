# -*- coding: utf-8 -*-
"""Pacote storage — Abstração de persistência (SQLite ↔ DynamoDB)."""
from functools import lru_cache

from storage.base import ConversationRecord, StorageBackend


@lru_cache(maxsize=1)
def get_storage() -> StorageBackend:
    """
    Factory singleton que retorna o backend de storage configurado.

    O backend é determinado pela variável STORAGE_BACKEND no .env:
    - "sqlite"   → SQLiteBackend (desenvolvimento)
    - "dynamodb" → DynamoDBBackend (produção AWS)
    """
    from agente.config import get_settings

    settings = get_settings()

    if settings.storage_backend == "dynamodb":
        from storage.dynamodb import DynamoDBBackend

        return DynamoDBBackend(
            table_name=settings.dynamodb_table_name,
            region=settings.aws_region,
            endpoint_url=settings.dynamodb_endpoint_url,
        )

    # Default: SQLite
    from storage.sqlite import SQLiteBackend

    return SQLiteBackend(database_url=settings.database_url)


__all__ = ["ConversationRecord", "StorageBackend", "get_storage"]
