# -*- coding: utf-8 -*-
"""
Rotas administrativas — status e atualização do data warehouse histórico.

Endpoints:
  GET  /admin/data-status  → status de atualização por série (painel de consistência)
  POST /admin/refresh      → dispara atualização incremental de todas as séries
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from agente.nodes.auditor import _FRESHNESS_CRITICAL_DAYS, _FRESHNESS_WARN_DAYS
from api.schemas import (
    DataStatusResponse,
    RefreshResponse,
    SeriesRefreshResult,
    SeriesStatusItem,
)
from api.security import require_admin_key
from warehouse.pipeline import refresh_all
from warehouse.registry import SERIES_REGISTRY
from warehouse.store import get_warehouse_store

logger = logging.getLogger(__name__)

admin_router = APIRouter(prefix="/admin", tags=["Administração"])


def _status_color(lag_days: Optional[int]) -> str:
    """Reaproveita os mesmos limiares de defasagem do Auditor (Onda 3)."""
    if lag_days is None:
        return "gray"  # série ainda não coletada pelo warehouse
    if lag_days > _FRESHNESS_CRITICAL_DAYS:
        return "red"
    if lag_days > _FRESHNESS_WARN_DAYS:
        return "amber"
    return "green"


@admin_router.get("/data-status", response_model=DataStatusResponse, tags=["Administração"])
async def data_status() -> DataStatusResponse:
    """
    Status de atualização de cada série do data warehouse histórico.

    Usado pelo painel "Status dos Dados" do frontend — mostra última
    atualização, nº de linhas e defasagem por indicador.
    """
    raw = get_warehouse_store().list_status(SERIES_REGISTRY)
    items = [SeriesStatusItem(**row, status_color=_status_color(row["lag_days"])) for row in raw]
    return DataStatusResponse(series=items)


@admin_router.post(
    "/refresh",
    response_model=RefreshResponse,
    tags=["Administração"],
    dependencies=[Depends(require_admin_key)],
)
async def refresh_data() -> RefreshResponse:
    """
    Dispara a atualização incremental de todas as séries registradas.

    Pode levar de poucos segundos (atualizações incrementais normais) a
    ~1 minuto (primeiro backfill completo) — despachado via threadpool para
    não bloquear o event loop, mesmo padrão já usado em `POST /ask`
    (`src/api/routes.py`).
    """
    results = await run_in_threadpool(refresh_all)

    items = [
        SeriesRefreshResult(
            series_id=r.series_id,
            label=r.label,
            success=r.success,
            rows_after=r.rows_after,
            error=r.error,
        )
        for r in results
    ]
    n_ok = sum(1 for r in results if r.success)
    logger.info("Refresh manual do warehouse | %d/%d séries OK", n_ok, len(results))
    return RefreshResponse(results=items, total=len(items), succeeded=n_ok)
