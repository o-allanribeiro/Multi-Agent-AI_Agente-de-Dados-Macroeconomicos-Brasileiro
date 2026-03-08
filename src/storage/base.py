# -*- coding: utf-8 -*-
"""
StorageBackend — Classe base abstrata para persistência de conversas.

Abstração que permite trocar o backend (SQLite ↔ DynamoDB) sem
alterar o código da aplicação — padrão Strategy.
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConversationRecord:
    """Representa uma conversa armazenada."""

    session_id: str
    question: str
    response: str
    has_data: bool = False
    has_plot: bool = False
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "question": self.question,
            "response": self.response,
            "has_data": self.has_data,
            "has_plot": self.has_plot,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


class StorageBackend(ABC):
    """Interface abstrata para backends de armazenamento."""

    @abstractmethod
    def save(self, record: ConversationRecord) -> None:
        """Persiste um registro de conversa."""
        ...

    @abstractmethod
    def get(self, session_id: str) -> Optional[ConversationRecord]:
        """Recupera uma conversa pelo session_id."""
        ...

    @abstractmethod
    def list_recent(self, limit: int = 20) -> List[ConversationRecord]:
        """Retorna as N conversas mais recentes."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Verifica se o backend está acessível."""
        ...
