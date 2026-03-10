# -*- coding: utf-8 -*-
"""
api/limiter.py — Rate limiter centralizado (slowapi).

Singleton do Limiter para ser compartilhado por server.py e routes.py
sem criar dependência circular.

Configuração padrão:
  - /ask:    10 req/minuto por IP (chamada ao Gemini + APIs externas = alto custo)
  - /health: sem limite (monitoramento de infra)

Para aumentar limites em produção, ajuste as strings nos decoradores de rotas.
Para usar Redis como backend (múltiplos workers):
    limiter = Limiter(key_func=get_remote_address, storage_uri="redis://...")
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
