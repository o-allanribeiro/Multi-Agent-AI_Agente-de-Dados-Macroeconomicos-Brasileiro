# -*- coding: utf-8 -*-
"""
DynamoDBBackend — Persistência na AWS DynamoDB.

Implementação do StorageBackend para ambiente de produção na AWS.
Requer: boto3 instalado (requirements-aws.txt) e credenciais AWS configuradas.

FASE B: Este módulo será completamente implementado quando formos
migrar para produção AWS. Por ora, é um stub documentado.

Para testar local sem AWS:
    1. Instale DynamoDB Local: docker run -p 8001:8000 amazon/dynamodb-local
    2. Configure DYNAMODB_ENDPOINT_URL="http://localhost:8001"

Tabela esperada (DynamoDB):
    Partition Key: session_id (String)
    TTL attribute: expires_at (Number — Unix timestamp)
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from storage.base import ConversationRecord, StorageBackend

logger = logging.getLogger(__name__)


class DynamoDBBackend(StorageBackend):
    """
    Backend AWS DynamoDB para persistência de conversas em produção.

    Parameters
    ----------
    table_name : str
        Nome da tabela DynamoDB.
    region : str
        Região AWS (ex: 'us-east-1').
    endpoint_url : str, optional
        URL customizada para DynamoDB Local.
    ttl_days : int
        Dias até expiração automática dos registros (via TTL).
    """

    def __init__(
        self,
        table_name: str,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        ttl_days: int = 90,
    ) -> None:
        try:
            import boto3

            self._table_name = table_name
            self._ttl_days = ttl_days

            dynamodb = boto3.resource(
                "dynamodb",
                region_name=region,
                endpoint_url=endpoint_url,
            )
            self._table = dynamodb.Table(table_name)
            logger.info(
                "DynamoDBBackend inicializado | table=%s | region=%s", table_name, region
            )
        except ImportError:
            raise RuntimeError(
                "boto3 não instalado. Execute: pip install -r requirements-aws.txt"
            )

    def save(self, record: ConversationRecord) -> None:
        """Salva conversa no DynamoDB com TTL automático."""
        expires_at = int(
            (datetime.now(timezone.utc) + timedelta(days=self._ttl_days)).timestamp()
        )
        item = record.to_dict()
        item["expires_at"] = expires_at

        self._table.put_item(Item=item)
        logger.debug("Conversa salva no DynamoDB | session=%s", record.session_id)

    def get(self, session_id: str) -> Optional[ConversationRecord]:
        """Recupera conversa por session_id."""
        response = self._table.get_item(Key={"session_id": session_id})
        item = response.get("Item")
        if not item:
            return None

        return ConversationRecord(
            session_id=item["session_id"],
            question=item["question"],
            response=item["response"],
            has_data=item.get("has_data", False),
            has_plot=item.get("has_plot", False),
            error=item.get("error"),
            timestamp=datetime.fromisoformat(item["timestamp"]),
        )

    def list_recent(self, limit: int = 20) -> List[ConversationRecord]:
        """
        Lista conversas recentes.

        TODO (Fase B): Implementar com GSI (Global Secondary Index) por timestamp.
        Por ora, retorna lista vazia para não quebrar a interface.
        """
        logger.warning("DynamoDBBackend.list_recent() requer GSI — não implementado ainda.")
        return []

    def health_check(self) -> bool:
        """Verifica acessibilidade da tabela DynamoDB."""
        try:
            self._table.load()
            return True
        except Exception as exc:
            logger.error("DynamoDB health check falhou: %s", exc)
            return False
