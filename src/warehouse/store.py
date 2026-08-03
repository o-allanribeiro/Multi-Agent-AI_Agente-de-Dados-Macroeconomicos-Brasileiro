# -*- coding: utf-8 -*-
"""
warehouse/store.py — Armazenamento do histórico (Parquet) e metadados (DuckDB).

Um arquivo Parquet por série (`{base_dir}/series/{series_id}.parquet`, colunas
`date`/`value`) é a fonte de verdade do histórico. DuckDB é usado só para:
  (a) a tabela de metadados de atualização (last_refreshed_at, last_error) —
      informação que não existe dentro do próprio Parquet;
  (b) consultas agregadas de status (contagem de linhas, período coberto)
      via SQL direto sobre o arquivo Parquet, sem carregá-lo inteiro em pandas.
"""

import logging
import threading
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

_META_DDL = """
CREATE TABLE IF NOT EXISTS series_meta (
    series_id           TEXT PRIMARY KEY,
    source              TEXT,
    label               TEXT,
    frequency           TEXT,
    last_refreshed_at   TIMESTAMP,
    last_error          TEXT
)
"""


def _normalize_index(idx) -> pd.DatetimeIndex:
    """
    Converte para DatetimeIndex naive (sem timezone), mesmo quando a entrada
    mistura timestamps tz-aware e naive.

    Achado em produção: a API do IPEADATA retorna algumas datas com fuso
    horário embutido e outras sem, no meio da mesma série — `pd.to_datetime()`
    direto falha nesse caso ("Tz-aware datetime.datetime cannot be converted
    to datetime64 unless utc=True"). Normalizamos via UTC e removemos o fuso,
    já que todas as outras fontes (BCB/IBGE/Banco Mundial) usam datas naive e
    o warehouse não precisa de granularidade de fuso — só a data importa.
    """
    return pd.to_datetime(idx, utc=True).tz_convert(None)


class WarehouseStore:
    """
    Histórico completo por série (Parquet) + metadados de atualização (DuckDB).

    Parameters
    ----------
    base_dir : str
        Diretório raiz do warehouse (padrão: settings.warehouse_dir).
    """

    def __init__(self, base_dir: str = "output/warehouse") -> None:
        self._base_dir = Path(base_dir)
        self._series_dir = self._base_dir / "series"
        self._series_dir.mkdir(parents=True, exist_ok=True)
        self._meta_path = self._base_dir / "meta.duckdb"
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.execute(_META_DDL)

    def _connect(self) -> "duckdb.DuckDBPyConnection":
        return duckdb.connect(str(self._meta_path))

    def _series_path(self, series_id: str) -> Path:
        return self._series_dir / f"{series_id}.parquet"

    # ------------------------------------------------------------------
    # Histórico (Parquet)
    # ------------------------------------------------------------------

    def read_full(self, series_id: str) -> pd.DataFrame:
        """
        Lê o histórico completo salvo para uma série.

        Returns
        -------
        pd.DataFrame
            Coluna única 'value', DatetimeIndex nomeado 'date'. DataFrame
            vazio (mesmo shape) se a série ainda não foi coletada.
        """
        path = self._series_path(series_id)
        if not path.exists():
            empty = pd.DataFrame({"value": pd.Series(dtype="float64")})
            empty.index = pd.DatetimeIndex([], name="date")
            return empty
        df = pd.read_parquet(path)
        df.index = _normalize_index(df.index)
        df.index.name = "date"
        return df.sort_index()

    def upsert(self, series_id: str, new_df: Optional[pd.DataFrame]) -> int:
        """
        Mescla novos dados ao histórico salvo, deduplicando por data.

        Em caso de sobreposição (ex: janela de atualização incremental com
        overlap para capturar revisões do BCB), mantém o valor mais recente
        buscado — não o mais antigo.

        Parameters
        ----------
        series_id : str
            Identificador da série (ver `warehouse.registry`).
        new_df : pd.DataFrame | None
            DataFrame recém-buscado (DatetimeIndex + 1 coluna, qualquer nome
            — normalizado para 'value'). None/vazio é um no-op seguro.

        Returns
        -------
        int
            Número total de linhas no histórico após o merge.
        """
        existing = self.read_full(series_id)

        if new_df is None or new_df.empty:
            return len(existing)

        incoming = new_df.copy()
        incoming.columns = ["value"]
        incoming.index = _normalize_index(incoming.index)
        incoming.index.name = "date"
        incoming["value"] = incoming["value"].astype("float64")

        with self._lock:
            combined = pd.concat([existing, incoming])
            combined = combined[~combined.index.duplicated(keep="last")].sort_index()
            combined.to_parquet(self._series_path(series_id))

        return len(combined)

    # ------------------------------------------------------------------
    # Metadados (DuckDB)
    # ------------------------------------------------------------------

    def record_refresh(
        self,
        series_id: str,
        source: str,
        label: str,
        frequency: str,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Registra o resultado da última tentativa de atualização de uma série."""
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO series_meta
                    (series_id, source, label, frequency, last_refreshed_at, last_error)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (series_id) DO UPDATE SET
                    source = excluded.source,
                    label = excluded.label,
                    frequency = excluded.frequency,
                    last_refreshed_at = excluded.last_refreshed_at,
                    last_error = excluded.last_error
                """,
                [
                    series_id,
                    source,
                    label,
                    frequency,
                    datetime.now(timezone.utc),
                    None if success else error,
                ],
            )

    def list_status(self, specs: list) -> List[Dict[str, Any]]:
        """
        Status por série: última atualização, nº de linhas, período coberto,
        defasagem em dias. `specs` é a lista de SeriesSpec do registry —
        garante que séries nunca atualizadas também apareçam (row_count=0).
        """
        with self._connect() as conn:
            meta_rows = {
                row[0]: row
                for row in conn.execute(
                    "SELECT series_id, last_refreshed_at, last_error FROM series_meta"
                ).fetchall()
            }

        today = date.today()
        results: List[Dict[str, Any]] = []
        for spec in specs:
            path = self._series_path(spec.id)
            if path.exists():
                row_count, first_date, last_date = duckdb.sql(
                    "SELECT count(*), min(date), max(date) "
                    f"FROM read_parquet('{path.as_posix()}')"
                ).fetchone()
            else:
                row_count, first_date, last_date = 0, None, None

            # DuckDB retorna datetime.datetime para min/max de uma coluna
            # timestamp do Parquet (mesmo quando os valores são "dia puro") —
            # normaliza para date antes de subtrair.
            last_date = pd.Timestamp(last_date).date() if last_date else None
            first_date = pd.Timestamp(first_date).date() if first_date else None
            lag_days = (today - last_date).days if last_date else None
            meta = meta_rows.get(spec.id)

            results.append(
                {
                    "series_id": spec.id,
                    "label": spec.label,
                    "source": spec.source,
                    "frequency": spec.frequency,
                    "row_count": int(row_count or 0),
                    "first_date": str(first_date) if first_date else None,
                    "last_date": str(last_date) if last_date else None,
                    "lag_days": lag_days,
                    "last_refreshed_at": meta[1].isoformat() if meta and meta[1] else None,
                    "last_error": meta[2] if meta else None,
                }
            )
        return results


# ---------------------------------------------------------------------------
# Singleton — reutiliza a mesma instância no processo (mesmo padrão de
# tools/cache.py e storage/__init__.py)
# ---------------------------------------------------------------------------
_store_instance: Optional[WarehouseStore] = None
_store_lock = threading.Lock()


def get_warehouse_store() -> WarehouseStore:
    """Retorna a instância singleton do WarehouseStore, criada sob demanda."""
    global _store_instance
    if _store_instance is None:
        with _store_lock:
            if _store_instance is None:
                from agente.config import get_settings

                _store_instance = WarehouseStore(base_dir=get_settings().warehouse_dir)
    return _store_instance
