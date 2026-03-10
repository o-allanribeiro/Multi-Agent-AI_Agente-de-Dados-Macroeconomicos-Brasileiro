# -*- coding: utf-8 -*-
"""
tools/cache.py — Cache local de séries temporais.

Armazena séries econômicas em SQLite para evitar chamadas repetidas às APIs
externas. Estratégia:
  - Ao buscar: verifica se há cache fresco para a série + parâmetros.
  - Se fresco: retorna do cache (sem chamada de rede).
  - Se stale ou ausente: busca na API, salva no cache e retorna.

Definição de "fresco" por frequência:
  - diário (câmbio, Selic over):  2 dias
  - mensal (IPCA, desocupação):  35 dias
  - trimestral (PIB):           100 dias
  - anual (Gini/Banco Mundial): 400 dias

A chave de cache inclui a fonte, código e parâmetros de janela temporal,
garantindo que chamadas com parâmetros distintos não colidam.

Uso (transparente — chamado pelos DataSource.fetch()):
    from tools.cache import get_series_cache
    cache = get_series_cache()
    df, is_fresh = cache.get("bcb_432_last5")
    if not is_fresh:
        df = fetch_from_api(...)
        cache.set("bcb_432_last5", df, frequency="mensal")
    return df
"""
import json
import logging
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# Número de dias até o cache ser considerado stale por frequência de atualização
_STALE_DAYS: dict[str, int] = {
    "diario":      2,
    "mensal":     35,
    "trimestral": 100,
    "anual":      400,
}

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS series_cache (
    cache_key   TEXT    PRIMARY KEY,
    data_json   TEXT    NOT NULL,
    frequency   TEXT    NOT NULL,
    fetched_at  TEXT    NOT NULL,
    last_date   TEXT    NOT NULL
)
"""


class SeriesCache:
    """
    Cache SQLite de séries temporais. Thread-safe via lock interno.

    Parameters
    ----------
    db_path : str
        Caminho para o arquivo SQLite de cache.
        Padrão: output/series_cache.db (criado automaticamente).
    """

    def __init__(self, db_path: str = "output/series_cache.db") -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(_CREATE_TABLE_SQL)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path, check_same_thread=False)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def get(self, cache_key: str) -> Tuple[Optional[pd.DataFrame], bool]:
        """
        Recupera série do cache se existir.

        Returns
        -------
        (DataFrame | None, is_fresh: bool)
            ``is_fresh=True`` se o cache ainda está dentro da janela de validade.
            ``is_fresh=False`` se o cache está stale ou não existe.
        """
        with self._lock:
            try:
                with self._connect() as conn:
                    cur = conn.execute(
                        "SELECT data_json, frequency, fetched_at FROM series_cache WHERE cache_key=?",
                        (cache_key,),
                    )
                    row = cur.fetchone()
            except Exception as exc:
                logger.warning("Erro ao ler cache '%s': %s", cache_key, exc)
                return None, False

        if row is None:
            return None, False

        data_json, frequency, fetched_at_str = row

        # Verifica frescor
        stale_days = _STALE_DAYS.get(frequency, 35)
        try:
            fetched_at = datetime.fromisoformat(fetched_at_str)
            # Remove tzinfo para comparação com datetime sem tz
            if fetched_at.tzinfo is not None:
                fetched_at = fetched_at.replace(tzinfo=None)
            is_fresh = (datetime.utcnow() - fetched_at) < timedelta(days=stale_days)
        except Exception:
            is_fresh = False

        # Deserializa DataFrame
        try:
            records = json.loads(data_json)
            df = pd.DataFrame(records)
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
            logger.debug(
                "Cache %s: %s | %d registros | fresh=%s",
                "HIT" if is_fresh else "STALE",
                cache_key,
                len(df),
                is_fresh,
            )
            return df, is_fresh
        except Exception as exc:
            logger.warning("Erro ao deserializar cache '%s': %s", cache_key, exc)
            return None, False

    def set(self, cache_key: str, df: pd.DataFrame, frequency: str) -> None:
        """
        Persiste DataFrame no cache.

        Parameters
        ----------
        cache_key : str
            Chave única para a entrada (ex: "bcb_432_last5").
        df : pd.DataFrame
            DataFrame com DatetimeIndex a armazenar.
        frequency : str
            Frequência da série — chave de ``_STALE_DAYS`` (ex: "mensal").
        """
        if df is None or df.empty:
            return
        try:
            df_reset = df.reset_index()
            # Garante que a coluna de data é string ISO
            date_col = df_reset.columns[0]
            df_reset[date_col] = df_reset[date_col].astype(str)
            df_reset.columns = ["date"] + [str(c) for c in df_reset.columns[1:]]
            records = df_reset.to_dict(orient="records")
            data_json = json.dumps(records, ensure_ascii=False)
            last_date = str(df.index.max())
            fetched_at = datetime.utcnow().isoformat()

            with self._lock:
                with self._connect() as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO series_cache
                            (cache_key, data_json, frequency, fetched_at, last_date)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (cache_key, data_json, frequency, fetched_at, last_date),
                    )

            logger.info(
                "Cache salvo: %s | %d registros | freq=%s | last=%s",
                cache_key,
                len(df),
                frequency,
                last_date,
            )
        except Exception as exc:
            logger.warning("Erro ao salvar cache '%s': %s", cache_key, exc)

    def invalidate(self, cache_key: str) -> None:
        """Remove uma entrada do cache (força re-fetch na próxima chamada)."""
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM series_cache WHERE cache_key=?", (cache_key,))
        logger.info("Cache invalidado: %s", cache_key)

    def clear_all(self) -> None:
        """Remove todo o cache. Útil para testes e manutenção."""
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM series_cache")
        logger.info("Cache limpo completamente.")

    def stats(self) -> dict:
        """Retorna estatísticas do cache (total de entradas, por frequência)."""
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM series_cache").fetchone()[0]
            by_freq = conn.execute(
                "SELECT frequency, COUNT(*) FROM series_cache GROUP BY frequency"
            ).fetchall()
        return {"total": total, "by_frequency": dict(by_freq)}


# ---------------------------------------------------------------------------
# Singleton global — uma única instância por processo
# ---------------------------------------------------------------------------
_cache_instance: Optional[SeriesCache] = None
_cache_lock = threading.Lock()


def get_series_cache() -> SeriesCache:
    """
    Retorna a instância singleton do SeriesCache.

    Thread-safe: inicialização protegida por lock para evitar dupla criação.
    """
    global _cache_instance
    if _cache_instance is None:
        with _cache_lock:
            if _cache_instance is None:  # double-checked locking
                _cache_instance = SeriesCache()
    return _cache_instance


def make_cache_key(source: str, series_code, **params) -> str:
    """
    Gera chave de cache padronizada.

    Parameters
    ----------
    source : str
        Identificador da fonte (ex: "bcb", "ibge", "ipea", "wb").
    series_code : int | str
        Código ou chave da série.
    **params
        Parâmetros adicionais (ex: last_n_years=5, start_date="2020-01-01").

    Returns
    -------
    str
        Chave no formato "source_cod_k1v1_k2v2" (lowercase, sem espaços).
    """
    parts = [source, str(series_code)]
    for k, v in sorted(params.items()):
        if v is not None:
            parts.append(f"{k}{v}")
    return "_".join(parts).lower().replace(" ", "").replace("-", "")
