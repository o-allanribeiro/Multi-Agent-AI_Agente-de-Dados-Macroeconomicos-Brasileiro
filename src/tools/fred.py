# -*- coding: utf-8 -*-
"""
Ferramenta FRED — Federal Reserve Bank of St. Louis (FRED®).

Coleta séries de juros dos Estados Unidos via API REST do FRED
(``/fred/series/observations``), usada para o eixo "juros externos × Brasil".

Séries suportadas (frequência mensal, % a.a.; média do mês):
  - TB3MS: Treasury Bill de 3 meses (mercado secundário)
  - GS1, GS2, GS5, GS10: rendimento dos títulos do Tesouro americano de
    1, 2, 5 e 10 anos (prazo constante)

Requer a variável ``FRED_API_KEY`` (ambiente ou ``.env`` na raiz do projeto).
Chave gratuita: https://fredaccount.stlouisfed.org/apikeys
Sem a chave, a ferramenta não é registrada no ToolRegistry e o resto do
agente funciona normalmente.

Referência: https://fred.stlouisfed.org/docs/api/fred/series_observations.html

This product uses the FRED® API but is not endorsed or certified by the
Federal Reserve Bank of St. Louis.
"""

import logging
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from dotenv import dotenv_values

from tools.base import DataSource
from tools.cache import get_series_cache, make_cache_key
from utils.http import with_retry
from utils.validators import validate_series_code, validate_year_range

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# src/tools/fred.py → src/tools/ → src/ → raiz do projeto
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"

# Mapeamento centralizado de séries FRED (a chave é o código em minúsculas)
FRED_SERIES_MAP: dict[str, dict] = {
    "tb3ms": {
        "code": "TB3MS",
        "name": "Treasury Bill 3 meses (mercado secundário)",
        "unit": "% a.a.",
        "description": "Juro de curto prazo dos EUA; proxy da taxa livre de risco externa.",
    },
    "gs1": {
        "code": "GS1",
        "name": "Treasury 1 ano (prazo constante)",
        "unit": "% a.a.",
        "description": "Rendimento do título do Tesouro americano de 1 ano.",
    },
    "gs2": {
        "code": "GS2",
        "name": "Treasury 2 anos (prazo constante)",
        "unit": "% a.a.",
        "description": "Rendimento do título do Tesouro americano de 2 anos.",
    },
    "gs5": {
        "code": "GS5",
        "name": "Treasury 5 anos (prazo constante)",
        "unit": "% a.a.",
        "description": "Rendimento do título do Tesouro americano de 5 anos.",
    },
    "gs10": {
        "code": "GS10",
        "name": "Treasury 10 anos (prazo constante)",
        "unit": "% a.a.",
        "description": "Rendimento do título do Tesouro americano de 10 anos.",
    },
}

_VALID_CODES = frozenset(meta["code"] for meta in FRED_SERIES_MAP.values())


def get_fred_api_key() -> Optional[str]:
    """
    Resolve a chave da API do FRED.

    Ordem: variável de ambiente ``FRED_API_KEY`` → ``.env`` na raiz do projeto.
    Lê o ``.env`` diretamente (e não via ``Settings``) porque ``Settings`` exige
    ``GOOGLE_API_KEY`` e esta checagem roda na montagem do ToolRegistry.

    Returns
    -------
    Optional[str]
        A chave, ou None se não estiver configurada (vazia conta como ausente).
    """
    key = os.environ.get("FRED_API_KEY")
    if not key and _ENV_FILE.exists():
        key = dotenv_values(_ENV_FILE).get("FRED_API_KEY")
    key = (key or "").strip()
    return key or None


def fred_available() -> bool:
    """True se há chave configurada e, portanto, a ferramenta pode ser usada."""
    return get_fred_api_key() is not None


def _sanitize_error(exc: Exception, api_key: str) -> Exception:
    """
    Recria a exceção sem expor a chave da API.

    A chave vai na query string e as mensagens do ``requests`` incluem a URL
    completa; sem isso ela apareceria nos logs de retry e de erro.
    """
    message = str(exc).replace(api_key, "***")
    try:
        return type(exc)(message)
    except Exception:
        return requests.exceptions.RequestException(message)


class FREDDataSource(DataSource):
    """Fonte de dados do FRED (Federal Reserve Bank of St. Louis) via API REST."""

    source_name = "FRED"

    def fetch(
        self,
        series_code: str,
        start_date: Optional[str] = None,
        last_n_years: Optional[int] = None,
        timeout: int = 30,
        **kwargs,
    ) -> Optional[pd.DataFrame]:
        """
        Busca uma série mensal de juros americanos no FRED.

        Parameters
        ----------
        series_code : str
            Código da série (ex: 'GS10', 'TB3MS'); aceita minúsculas.
        start_date : str, optional
            Data inicial (YYYY-MM-DD).
        last_n_years : int, optional
            Janela em anos até hoje; ignorada se ``start_date`` for informado.
        timeout : int
            Timeout em segundos para a requisição HTTP.

        Returns
        -------
        Optional[pd.DataFrame]
            DataFrame com índice DatetimeIndex e 1 coluna (o código da série),
            ou None em caso de erro, série não suportada ou ausência de chave.
        """
        if not validate_series_code(series_code):
            logger.error("Código de série FRED inválido: %r", series_code)
            return None

        code = str(series_code).strip().upper()
        if code not in _VALID_CODES:
            logger.error("Série FRED não suportada: %s | suportadas=%s", code, sorted(_VALID_CODES))
            return None

        api_key = get_fred_api_key()
        if api_key is None:
            logger.warning("FRED_API_KEY não configurada — série %s não pode ser buscada", code)
            return None

        if start_date is None and last_n_years is not None:
            if not validate_year_range(last_n_years):
                logger.error("last_n_years fora do intervalo permitido: %s", last_n_years)
                return None
            start_date = (date.today() - timedelta(days=365 * last_n_years)).isoformat()
            window_key = last_n_years
        else:
            window_key = None

        logger.info("Consultando FRED | série=%s | início=%s", code, start_date or "histórico")

        cache = get_series_cache()
        cache_key = make_cache_key(
            "fred", code, start=start_date if window_key is None else None, years=window_key
        )
        cached_df, is_fresh = cache.get(cache_key)
        if is_fresh:
            logger.info("FRED cache hit: %s", code)
            return cached_df

        params = {
            "series_id": code,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "asc",
        }
        if start_date:
            params["observation_start"] = start_date

        def _get() -> requests.Response:
            try:
                return requests.get(_BASE_URL, params=params, timeout=timeout)
            except requests.exceptions.RequestException as exc:
                raise _sanitize_error(exc, api_key) from None

        try:
            response = with_retry(
                _get,
                max_retries=3,
                base_delay=1.5,
                exc_types=(
                    requests.exceptions.Timeout,
                    requests.exceptions.ConnectionError,
                ),
            )
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as exc:
                raise _sanitize_error(exc, api_key) from None

            payload = response.json()
            observations = payload.get("observations") if isinstance(payload, dict) else None
            if not observations:
                self._log_empty(code)
                return None

            df = pd.DataFrame(observations)[["date", "value"]]
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            # O FRED marca observações ausentes com "." → vira NaN e é descartada
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df = (
                df.dropna(subset=["date", "value"])
                .rename(columns={"date": "Date", "value": code})
                .set_index("Date")
                .sort_index()
                .astype("float64")
            )

            if df.empty:
                self._log_empty(code)
                return None

            self._log_success(code, len(df))
            cache.set(cache_key, df, frequency="mensal")
            return df

        except Exception as exc:
            self._log_error(code, exc)
            return None


_fred_source = FREDDataSource()


def get_fred_series(
    series_code: str,
    start_date: Optional[str] = None,
    last_n_years: Optional[int] = None,
) -> Optional[pd.DataFrame]:
    """
    Função de conveniência para buscar uma série do FRED.

    Parameters
    ----------
    series_code : str
        'TB3MS', 'GS1', 'GS2', 'GS5' ou 'GS10'.
    start_date : str, optional
        Data inicial (YYYY-MM-DD).
    last_n_years : int, optional
        Janela em anos até hoje.

    Returns
    -------
    Optional[pd.DataFrame]
    """
    return _fred_source.fetch(
        series_code=series_code, start_date=start_date, last_n_years=last_n_years
    )
