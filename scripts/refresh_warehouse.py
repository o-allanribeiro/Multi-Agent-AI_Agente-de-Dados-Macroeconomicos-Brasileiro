# -*- coding: utf-8 -*-
"""
refresh_warehouse.py — Atualiza o data warehouse histórico do Agente Macro-BR.

Percorre todas as séries registradas em `warehouse.registry.SERIES_REGISTRY`
(Selic, IPCA, Dólar, Desocupação, PIB, IPCA-15, Rendimento PNAD, FBCF, Gini) e
atualiza o histórico salvo em Parquet (backfill completo na primeira vez,
incremental nas seguintes). Mesmo pipeline usado por `POST /admin/refresh`.

Uso:
    PYTHONPATH=src python scripts/refresh_warehouse.py

    # Windows PowerShell:
    $env:PYTHONPATH="src"; python scripts/refresh_warehouse.py

Pré-requisito: variáveis de ambiente da aplicação configuradas (.env na raiz
do projeto — GOOGLE_API_KEY não é necessária para este script, mas
APP_ENV/etc. seguem o mesmo `agente.config.get_settings()`).
"""

import sys
from pathlib import Path

# Garante que src/ está no path quando executado como script solto
_SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

try:
    import duckdb  # noqa: F401
    import pyarrow  # noqa: F401
except ImportError:
    print("[ERRO] duckdb/pyarrow não encontrados. Execute:  pip install duckdb pyarrow")
    sys.exit(1)

import argparse  # noqa: E402

from warehouse.pipeline import refresh_all  # noqa: E402
from warehouse.registry import SERIES_REGISTRY  # noqa: E402
from warehouse.store import get_warehouse_store  # noqa: E402

# Mesmos limiares de agente/nodes/auditor.py (duplicado aqui para manter este
# script leve — sem depender do FastAPI/pydantic da camada de API).
_FRESHNESS_WARN_DAYS = 90
_FRESHNESS_CRITICAL_DAYS = 365


def _status_color(lag_days) -> str:
    if lag_days is None:
        return "novo"
    if lag_days > _FRESHNESS_CRITICAL_DAYS:
        return "vermelho"
    if lag_days > _FRESHNESS_WARN_DAYS:
        return "amarelo"
    return "verde"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Atualiza o data warehouse histórico (Parquet + DuckDB)."
    )
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="Só mostra o status atual das séries, sem buscar dados novos.",
    )
    args = parser.parse_args()

    print(f"\n{'=' * 64}")
    print("  Agente Macro-BR — Data Warehouse Histórico")
    print(f"  Séries registradas: {len(SERIES_REGISTRY)}")
    print(f"{'=' * 64}\n")

    store = get_warehouse_store()

    if args.status_only:
        for row in store.list_status(SERIES_REGISTRY):
            _print_status_row(row)
        return

    print("Atualizando... (backfill inicial pode levar ~1 min para séries diárias do BCB)\n")
    results = refresh_all(store=store)

    n_ok = sum(1 for r in results if r.success)
    for r in results:
        tag = "[OK]  " if r.success else "[ERRO]"
        detail = f"{r.rows_after} linhas" if r.success else r.error
        print(f"  {tag} {r.label:<45} ({r.series_id}) — {detail}")

    print(f"\n[PRONTO] {n_ok}/{len(results)} séries atualizadas com sucesso.\n")

    print("Status final:\n")
    for row in store.list_status(SERIES_REGISTRY):
        _print_status_row(row)


def _print_status_row(row: dict) -> None:
    lag = f"{row['lag_days']}d" if row["lag_days"] is not None else "—"
    color = _status_color(row["lag_days"])
    print(
        f"  [{color:<8}] {row['label']:<45} | linhas={row['row_count']:<6} | "
        f"último={row['last_date'] or '—':<12} | defasagem={lag}"
    )


if __name__ == "__main__":
    main()
