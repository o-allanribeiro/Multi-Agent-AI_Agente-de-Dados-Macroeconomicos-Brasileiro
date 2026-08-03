# -*- coding: utf-8 -*-
"""
Testes unitários do data warehouse histórico (DuckDB + Parquet).

Cobre: WarehouseStore (upsert/dedup, status), registry (resolução de
series_id) e pipeline (estratégias de refresh por fonte, isolamento de falhas).
"""

from datetime import date, timedelta
from unittest.mock import MagicMock

import pandas as pd
import pytest

from warehouse.registry import SeriesSpec, get_spec, resolve_series_id
from warehouse.store import WarehouseStore


@pytest.fixture()
def store(tmp_path) -> WarehouseStore:
    """WarehouseStore isolado num diretório temporário — nunca toca output/warehouse real."""
    return WarehouseStore(base_dir=str(tmp_path / "warehouse"))


def _df(dates, values, col="432") -> pd.DataFrame:
    return pd.DataFrame({col: values}, index=pd.DatetimeIndex(dates))


class TestWarehouseStore:
    def test_read_full_empty_for_unknown_series(self, store):
        result = store.read_full("bcb_432")
        assert result.empty
        assert list(result.columns) == ["value"]

    def test_upsert_creates_new_series(self, store):
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        n = store.upsert("bcb_432", _df(dates, [1.0, 2.0, 3.0, 4.0, 5.0]))
        assert n == 5
        assert len(store.read_full("bcb_432")) == 5

    def test_upsert_dedups_overlap_keeps_most_recent_fetch(self, store):
        """Sobreposição de datas: o valor buscado por último prevalece (revisões do BCB)."""
        dates1 = pd.date_range("2024-01-01", periods=5, freq="D")
        store.upsert("bcb_432", _df(dates1, [1.0, 2.0, 3.0, 4.0, 5.0]))

        dates2 = pd.date_range("2024-01-04", periods=5, freq="D")  # sobrepõe 04 e 05
        n = store.upsert("bcb_432", _df(dates2, [40.0, 50.0, 6.0, 7.0, 8.0]))

        full = store.read_full("bcb_432")
        assert n == 8, "5 + 5 com 2 sobrepostas = 8 linhas únicas"
        assert len(full) == 8
        assert full.loc["2024-01-04", "value"] == 40.0
        assert full.loc["2024-01-05", "value"] == 50.0

    def test_upsert_noop_for_none(self, store):
        dates = pd.date_range("2024-01-01", periods=3, freq="D")
        store.upsert("bcb_432", _df(dates, [1.0, 2.0, 3.0]))
        n = store.upsert("bcb_432", None)
        assert n == 3, "upsert(None) não deve alterar o histórico existente"

    def test_upsert_noop_for_empty_df(self, store):
        n = store.upsert("bcb_432", pd.DataFrame())
        assert n == 0

    def test_upsert_handles_mixed_timezone_index(self, store):
        """
        Regressão encontrada em produção: a API do IPEADATA retorna algumas
        datas com timezone embutido e outras sem, na mesma série — passar
        isso direto para pd.to_datetime() lança
        'Tz-aware datetime.datetime cannot be converted to datetime64 unless
        utc=True'. Reproduzido com dados reais do FBCF (ipea_fbcf) ao rodar
        o backfill completo pela primeira vez.
        """
        import datetime as dt

        mixed_index = pd.Index(
            [
                dt.datetime(2020, 1, 1),
                dt.datetime(2020, 2, 1, tzinfo=dt.timezone(dt.timedelta(hours=-3))),
                dt.datetime(2020, 3, 1),
            ],
            dtype=object,
        )
        df = pd.DataFrame({"GAC12_INDFBCF12": [100.0, 101.0, 102.0]}, index=mixed_index)

        n = store.upsert("ipea_fbcf", df)

        assert n == 3
        assert len(store.read_full("ipea_fbcf")) == 3

    def test_list_status_zero_for_uncollected_series(self, store):
        spec = get_spec("bcb_432")
        status = store.list_status([spec])
        assert status[0]["row_count"] == 0
        assert status[0]["last_date"] is None
        assert status[0]["lag_days"] is None

    def test_list_status_after_upsert(self, store):
        yesterday = date.today() - timedelta(days=1)
        dates = pd.date_range(end=yesterday, periods=10, freq="D")
        store.upsert("bcb_432", _df(dates, list(range(10))))

        spec = get_spec("bcb_432")
        status = store.list_status([spec])[0]
        assert status["row_count"] == 10
        assert status["last_date"] == str(yesterday)
        assert status["lag_days"] == 1

    def test_record_refresh_stores_error_on_failure(self, store):
        store.record_refresh("bcb_432", "bcb", "Selic", "diario", success=False, error="boom")
        spec = get_spec("bcb_432")
        status = store.list_status([spec])[0]
        assert status["last_error"] == "boom"
        assert status["last_refreshed_at"] is not None

    def test_record_refresh_clears_error_on_success(self, store):
        store.record_refresh("bcb_432", "bcb", "Selic", "diario", success=False, error="boom")
        store.record_refresh("bcb_432", "bcb", "Selic", "diario", success=True)
        spec = get_spec("bcb_432")
        status = store.list_status([spec])[0]
        assert status["last_error"] is None


class TestRegistry:
    def test_resolve_series_id_known_bcb_column(self):
        assert resolve_series_id("432") == "bcb_432"
        assert resolve_series_id("433") == "bcb_433"

    def test_resolve_series_id_known_ibge_column(self):
        assert resolve_series_id("pib_trimestral") == "ibge_pib_trimestral"

    def test_resolve_series_id_unknown_returns_none(self):
        assert resolve_series_id("juros_reais_pct") is None
        assert resolve_series_id("nao_existe") is None

    def test_get_spec_roundtrip(self):
        spec = get_spec("bcb_432")
        assert spec is not None
        assert spec.raw_code == "432"
        assert get_spec("inexistente") is None


class TestPipeline:
    def test_refresh_series_refetch_full_calls_fetch_without_args(self, store):
        fetch_mock = MagicMock(
            return_value=_df(
                pd.date_range("2024-01-01", periods=3, freq="D"), [1.0, 2.0, 3.0], col="GINI"
            )
        )
        spec = SeriesSpec(
            id="wb_gini",
            source="world_bank",
            raw_code="SI.POV.GINI",
            label="Gini",
            frequency="anual",
            refresh_mode="refetch_full",
            fetch=fetch_mock,
        )
        from warehouse.pipeline import refresh_series

        result = refresh_series(spec, store=store)

        assert result.success
        assert result.rows_after == 3
        fetch_mock.assert_called_once_with()

    def test_refresh_series_incremental_backfills_when_empty(self, store):
        fetch_mock = MagicMock(
            return_value=_df(
                pd.date_range("2024-01-01", periods=3, freq="MS"), [1.0, 2.0, 3.0], col="433"
            )
        )
        spec = SeriesSpec(
            id="bcb_433",
            source="bcb",
            raw_code="433",
            label="IPCA",
            frequency="mensal",
            refresh_mode="append_incremental",
            fetch=fetch_mock,
        )
        from warehouse.pipeline import refresh_series
        from warehouse.registry import WAREHOUSE_BACKFILL_START

        result = refresh_series(spec, store=store)

        assert result.success
        assert result.rows_after == 3
        fetch_mock.assert_called_once_with(start_date=WAREHOUSE_BACKFILL_START)

    def test_refresh_series_incremental_uses_overlap_when_existing(self, store):
        existing_dates = pd.date_range("2024-01-01", periods=5, freq="MS")
        store.upsert("bcb_433", _df(existing_dates, [1.0] * 5, col="433"))
        last_date = existing_dates.max().date()

        fetch_mock = MagicMock(return_value=None)
        spec = SeriesSpec(
            id="bcb_433",
            source="bcb",
            raw_code="433",
            label="IPCA",
            frequency="mensal",
            refresh_mode="append_incremental",
            fetch=fetch_mock,
        )
        from warehouse.pipeline import _INCREMENTAL_OVERLAP_DAYS, refresh_series

        refresh_series(spec, store=store)

        expected_start = (last_date - timedelta(days=_INCREMENTAL_OVERLAP_DAYS)).strftime(
            "%Y-%m-%d"
        )
        fetch_mock.assert_called_once_with(start_date=expected_start)

    def test_refresh_series_isolates_failure(self, store):
        failing_fetch = MagicMock(side_effect=RuntimeError("API fora do ar"))
        spec = SeriesSpec(
            id="bcb_432",
            source="bcb",
            raw_code="432",
            label="Selic",
            frequency="diario",
            refresh_mode="refetch_full",
            fetch=failing_fetch,
        )
        from warehouse.pipeline import refresh_series

        result = refresh_series(spec, store=store)

        assert not result.success
        assert "API fora do ar" in result.error

    def test_refresh_all_one_failure_does_not_block_others(self, store, monkeypatch):
        ok_spec = SeriesSpec(
            id="ok",
            source="bcb",
            raw_code="ok_col",
            label="OK",
            frequency="anual",
            refresh_mode="refetch_full",
            fetch=MagicMock(
                return_value=_df(
                    pd.date_range("2024-01-01", periods=2, freq="YS"), [1.0, 2.0], col="ok_col"
                )
            ),
        )
        bad_spec = SeriesSpec(
            id="bad",
            source="bcb",
            raw_code="bad_col",
            label="Bad",
            frequency="anual",
            refresh_mode="refetch_full",
            fetch=MagicMock(side_effect=RuntimeError("falhou")),
        )
        import warehouse.pipeline as pipeline_module

        monkeypatch.setattr(pipeline_module, "SERIES_REGISTRY", [ok_spec, bad_spec])

        results = pipeline_module.refresh_all(store=store)

        assert len(results) == 2
        by_id = {r.series_id: r for r in results}
        assert by_id["ok"].success
        assert not by_id["bad"].success

    def test_daily_backfill_chunks_across_10_year_limit(self):
        """Backfill diário desde 2000 deve ser em mais de 1 bloco (limite de 10 anos do BCB)."""
        from warehouse.pipeline import _fetch_daily_backfill_chunked

        call_ranges = []

        def fake_fetch(start_date=None, end_date=None):
            call_ranges.append((start_date, end_date))
            dates = pd.date_range(start=start_date, end=end_date, freq="YS")
            return _df(dates, [1.0] * len(dates)) if len(dates) else None

        spec = SeriesSpec(
            id="bcb_432",
            source="bcb",
            raw_code="432",
            label="Selic",
            frequency="diario",
            refresh_mode="append_incremental",
            fetch=fake_fetch,
        )

        result = _fetch_daily_backfill_chunked(spec, since="2000-01-01")

        assert (
            len(call_ranges) >= 3
        ), f"Esperado >= 3 blocos de 9 anos para cobrir ~26 anos, obteve {len(call_ranges)}"
        assert result is not None and not result.empty
