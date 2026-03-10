# -*- coding: utf-8 -*-
"""
utils/http.py — Utilitário de retry com backoff exponencial.

Aplica retry automático em chamadas a APIs externas que podem falhar
por timeout, reset de conexão ou instabilidade transiente (ex: IBGE/SIDRA).

Estratégia:
  - Tentativas: max_retries (padrão 3)
  - Delay crescente: base_delay * 2^attempt (1s → 2s → 4s)
  - Só faz retry em exceções transitórias (rede), não em erros de lógica (ex: 404)

Exemplo de uso:
    from utils.http import with_retry
    import requests

    resp = with_retry(
        lambda: requests.get(url, timeout=20),
        exc_types=(requests.exceptions.Timeout, requests.exceptions.ConnectionError),
    )
"""
import logging
import time
from typing import Callable, Optional, Tuple, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_retry(
    fn: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    exc_types: Optional[Tuple[Type[Exception], ...]] = None,
) -> T:
    """
    Executa ``fn()`` até ``max_retries`` vezes com backoff exponencial.

    Parameters
    ----------
    fn : Callable[[], T]
        Função sem argumentos a invocar (use lambda para passar parâmetros).
    max_retries : int
        Número máximo de tentativas (padrão: 3). Total inclui a primeira chamada.
    base_delay : float
        Delay base em segundos. Cresce como base_delay * 2^attempt.
        Tentativa 1 → 1s, tentativa 2 → 2s, tentativa 3 → 4s.
    exc_types : tuple of Exception types, optional
        Tipos de exceção tratados com retry. Outros tipos são propagados imediatamente.
        Padrão: (Exception,) — captura qualquer exceção.

    Returns
    -------
    T
        Valor de retorno de ``fn()`` na primeira tentativa bem-sucedida.

    Raises
    ------
    Exception
        A última exceção após esgotar todas as tentativas.
    """
    if exc_types is None:
        exc_types = (Exception,)

    last_exc: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            return fn()
        except exc_types as exc:
            last_exc = exc
            if attempt == max_retries - 1:
                # Última tentativa — propaga a exceção
                logger.error(
                    "Todas as %d tentativas falharam | erro: %s: %s",
                    max_retries,
                    type(exc).__name__,
                    exc,
                )
                raise

            delay = base_delay * (2 ** attempt)
            logger.warning(
                "Tentativa %d/%d falhou (%s: %s) — aguardando %.1fs antes de tentar novamente",
                attempt + 1,
                max_retries,
                type(exc).__name__,
                str(exc)[:120],
                delay,
            )
            time.sleep(delay)

    # Nunca alcançado, mas satisfaz o type checker
    raise last_exc  # type: ignore[misc]
