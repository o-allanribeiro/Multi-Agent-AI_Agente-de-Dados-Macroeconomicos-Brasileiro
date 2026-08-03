# -*- coding: utf-8 -*-
"""
warehouse/pipeline.py — Atualização incremental do data warehouse.

Percorre `warehouse.registry.SERIES_REGISTRY` e, para cada série:
  - 'append_incremental' (BCB): busca só o delta desde a última data salva
    (com sobreposição para capturar revisões); se ainda não há histórico,
    faz o backfill inicial desde WAREHOUSE_BACKFILL_START.
  - 'refetch_full' (IBGE/IPEA/Banco Mundial): a API não suporta busca
    incremental — reconsulta o disponível e deixa o upsert deduplicar.

Cada série roda em try/except isolado: uma fonte fora do ar não derruba as
demais (mesmo princípio do action_node — falha parcial não é falha total).
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional

import pandas as pd

from warehouse.registry import SERIES_REGISTRY, SeriesSpec
from warehouse.store import WarehouseStore, get_warehouse_store

logger = logging.getLogger(__name__)

# Margem de segurança sob o limite de 10 anos por requisição que o BCB impõe
# em séries diárias (ver tools/bcb.py). 9 anos evita acertar o limite exato
# por causa de fusos/arredondamento de data.
_MAX_DAILY_CHUNK_YEARS = 9

# Sobreposição no fetch incremental — BCB ocasionalmente revisa os últimos
# dias de uma série; sem isso, uma revisão publicada após o último refresh
# nunca seria capturada.
_INCREMENTAL_OVERLAP_DAYS = 5


@dataclass
class RefreshResult:
    series_id: str
    label: str
    success: bool
    rows_after: int
    error: Optional[str] = None


def _fetch_daily_backfill_chunked(spec: SeriesSpec, since: str) -> Optional[pd.DataFrame]:
    """
    Busca o histórico completo de uma série diária em blocos de
    `_MAX_DAILY_CHUNK_YEARS` anos, concatenando o resultado.

    Necessário porque o BCB rejeita janelas de mais de 10 anos em séries de
    periodicidade diária (Selic, Dólar) — sem isso, um backfill desde 2000
    falharia direto com HTTP error da API.
    """
    since_ts = pd.Timestamp(since)
    today_ts = pd.Timestamp(date.today())
    chunks: List[pd.DataFrame] = []

    chunk_start = since_ts
    while chunk_start <= today_ts:
        chunk_end = min(chunk_start + pd.DateOffset(years=_MAX_DAILY_CHUNK_YEARS), today_ts)
        df = spec.fetch(
            start_date=chunk_start.strftime("%Y-%m-%d"),
            end_date=chunk_end.strftime("%Y-%m-%d"),
        )
        if df is not None and not df.empty:
            chunks.append(df)
        else:
            logger.warning(
                "Bloco vazio no backfill de %s | %s a %s",
                spec.id,
                chunk_start.date(),
                chunk_end.date(),
            )
        chunk_start = chunk_end + pd.Timedelta(days=1)

    if not chunks:
        return None
    return pd.concat(chunks)


def refresh_series(spec: SeriesSpec, store: Optional[WarehouseStore] = None) -> RefreshResult:
    """Atualiza uma única série e registra o resultado nos metadados."""
    store = store or get_warehouse_store()

    try:
        if spec.refresh_mode == "refetch_full":
            new_df = spec.fetch()

        elif spec.refresh_mode == "append_incremental":
            existing = store.read_full(spec.id)
            if existing.empty:
                # Backfill inicial — chunked apenas para séries diárias
                # (mensal/trimestral/anual não têm o limite de 10 anos).
                from warehouse.registry import WAREHOUSE_BACKFILL_START

                if spec.frequency == "diario":
                    new_df = _fetch_daily_backfill_chunked(spec, WAREHOUSE_BACKFILL_START)
                else:
                    new_df = spec.fetch(start_date=WAREHOUSE_BACKFILL_START)
            else:
                last_date = existing.index.max().date()
                overlap_start = last_date - timedelta(days=_INCREMENTAL_OVERLAP_DAYS)
                new_df = spec.fetch(start_date=overlap_start.strftime("%Y-%m-%d"))
        else:
            raise ValueError(f"refresh_mode desconhecido: {spec.refresh_mode}")

        rows_after = store.upsert(spec.id, new_df)
        store.record_refresh(spec.id, spec.source, spec.label, spec.frequency, success=True)

        logger.info("Warehouse atualizado | série=%s | linhas=%d", spec.id, rows_after)
        return RefreshResult(spec.id, spec.label, success=True, rows_after=rows_after)

    except Exception as exc:
        logger.error("Falha ao atualizar série '%s': %s", spec.id, exc, exc_info=True)
        rows_after = len(store.read_full(spec.id))
        store.record_refresh(
            spec.id,
            spec.source,
            spec.label,
            spec.frequency,
            success=False,
            error=str(exc),
        )
        return RefreshResult(
            spec.id, spec.label, success=False, rows_after=rows_after, error=str(exc)
        )


def refresh_all(store: Optional[WarehouseStore] = None) -> List[RefreshResult]:
    """
    Atualiza todas as séries do registry. Falha isolada por série — uma fonte
    fora do ar não impede as demais de atualizar.
    """
    store = store or get_warehouse_store()
    results = [refresh_series(spec, store=store) for spec in SERIES_REGISTRY]

    n_ok = sum(1 for r in results if r.success)
    logger.info("Refresh do warehouse concluído | %d/%d séries OK", n_ok, len(results))
    return results
