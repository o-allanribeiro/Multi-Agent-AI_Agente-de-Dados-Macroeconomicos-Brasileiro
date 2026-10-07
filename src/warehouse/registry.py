# -*- coding: utf-8 -*-
"""
warehouse/registry.py — Manifesto único de séries do data warehouse.

Cada fonte de dados (tools/bcb.py, tools/ibge.py, tools/ipea.py,
tools/world_bank.py) nomeia a coluna do DataFrame retornado de um jeito
diferente (código numérico, chave semântica, código bruto da fonte) — não dá
para inferir identidade a partir do nome da coluna. Este registry é a única
fonte de verdade: cada série tem um `id` estável e um `raw_code` (o nome de
coluna que a fonte realmente produz), usado por `resolve_series_id()` para
o `stats_node` encontrar o histórico correto no warehouse.
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Callable, List, Optional

import pandas as pd

from tools.bcb import get_bcb_series
from tools.fred import FRED_SERIES_MAP, fred_available, get_fred_series
from tools.ibge import get_ibge_series
from tools.ipea import get_ipea_series
from tools.world_bank import WorldBankDataSource

logger = logging.getLogger(__name__)

# Piso de backfill inicial — BCB/IBGE/IPEA não têm dados confiáveis muito
# antes disso para os indicadores cobertos; Banco Mundial usa seu próprio
# início (1980) via _wb_fetch.
WAREHOUSE_BACKFILL_START = "2000-01-01"


@dataclass(frozen=True)
class SeriesSpec:
    """Especificação de uma série fetchável pelo warehouse."""

    id: str
    """Identificador estável do warehouse (ex: 'bcb_432')."""

    source: str
    """Nome da fonte ('bcb' | 'ibge' | 'ipea' | 'world_bank' | 'fred')."""

    raw_code: str
    """Nome da coluna que a função de fetch produz (ex: '432', 'pib_trimestral')."""

    label: str
    """Nome amigável para exibição (painel de status, CLI)."""

    frequency: str
    """'diario' | 'mensal' | 'trimestral' | 'anual' — mesma convenção de tools/cache.py."""

    refresh_mode: str
    """
    'append_incremental': fonte suporta start_date; backfill busca desde
        WAREHOUSE_BACKFILL_START, atualizações buscam só o delta.
    'refetch_full': fonte sempre retorna o histórico completo (ou o máximo
        que a API permite) — cada refresh reconsulta tudo e deduplica.
    """

    fetch: Callable[..., "Optional[pd.DataFrame]"]
    """Callable(start_date: str | None = None, end_date: str | None = None) -> DataFrame | None.

    Para 'refetch_full', ambos os parâmetros são ignorados. Para
    'append_incremental', definem a janela buscada — `end_date` só é usado
    pelo backfill em blocos (séries diárias do BCB rejeitam janelas > 10 anos;
    ver `pipeline._fetch_bcb_chunked`), atualizações incrementais normais
    passam só `start_date` (busca até hoje)."""


def _wb_fetch(
    start_date: Optional[str] = None, end_date: Optional[str] = None
) -> Optional[pd.DataFrame]:
    """Busca o Gini do Banco Mundial. Ignora os parâmetros (fonte 'refetch_full')."""
    return WorldBankDataSource().fetch(
        series_code="SI.POV.GINI",
        country_code="BRA",
        start_year=1980,
        end_year=date.today().year,
    )


SERIES_REGISTRY: List[SeriesSpec] = [
    SeriesSpec(
        id="bcb_432",
        source="bcb",
        raw_code="432",
        label="Taxa Selic Meta (COPOM)",
        frequency="diario",
        refresh_mode="append_incremental",
        fetch=lambda start_date=None, end_date=None: get_bcb_series(
            432, start_date=start_date or WAREHOUSE_BACKFILL_START, end_date=end_date
        ),
    ),
    SeriesSpec(
        id="bcb_1",
        source="bcb",
        raw_code="1",
        label="Taxa de Câmbio — Dólar PTAX (Venda)",
        frequency="diario",
        refresh_mode="append_incremental",
        fetch=lambda start_date=None, end_date=None: get_bcb_series(
            1, start_date=start_date or WAREHOUSE_BACKFILL_START, end_date=end_date
        ),
    ),
    SeriesSpec(
        id="bcb_433",
        source="bcb",
        raw_code="433",
        label="IPCA — Variação Mensal",
        frequency="mensal",
        refresh_mode="append_incremental",
        fetch=lambda start_date=None, end_date=None: get_bcb_series(
            433, start_date=start_date or WAREHOUSE_BACKFILL_START, end_date=end_date
        ),
    ),
    SeriesSpec(
        id="bcb_24369",
        source="bcb",
        raw_code="24369",
        label="Taxa de Desocupação (PNAD Contínua)",
        frequency="mensal",
        refresh_mode="append_incremental",
        fetch=lambda start_date=None, end_date=None: get_bcb_series(
            24369, start_date=start_date or WAREHOUSE_BACKFILL_START, end_date=end_date
        ),
    ),
    SeriesSpec(
        id="ibge_pib_trimestral",
        source="ibge",
        raw_code="pib_trimestral",
        label="PIB Trimestral (variação %)",
        frequency="trimestral",
        refresh_mode="refetch_full",
        fetch=lambda start_date=None, end_date=None: get_ibge_series("pib_trimestral", last_n=60),
    ),
    SeriesSpec(
        id="ibge_ipca15",
        source="ibge",
        raw_code="ipca15",
        label="IPCA-15 (prévia)",
        frequency="mensal",
        refresh_mode="refetch_full",
        fetch=lambda start_date=None, end_date=None: get_ibge_series("ipca15", last_n=60),
    ),
    SeriesSpec(
        id="ibge_rendimento_pnad",
        source="ibge",
        raw_code="rendimento_pnad",
        label="Rendimento Médio Real — PNAD",
        frequency="mensal",
        refresh_mode="refetch_full",
        fetch=lambda start_date=None, end_date=None: get_ibge_series("rendimento_pnad", last_n=60),
    ),
    SeriesSpec(
        id="ipea_fbcf",
        source="ipea",
        raw_code="GAC12_INDFBCF12",
        label="Formação Bruta de Capital Fixo",
        frequency="mensal",
        refresh_mode="refetch_full",
        fetch=lambda start_date=None, end_date=None: get_ipea_series("GAC12_INDFBCF12"),
    ),
    SeriesSpec(
        id="wb_gini",
        source="world_bank",
        raw_code="SI.POV.GINI",
        label="Coeficiente de Gini — Brasil",
        frequency="anual",
        refresh_mode="refetch_full",
        fetch=_wb_fetch,
    ),
]


def _fred_spec(code: str, label: str) -> SeriesSpec:
    """SeriesSpec de uma série FRED mensal (a API devolve o histórico completo)."""
    return SeriesSpec(
        id=f"fred_{code.lower()}",
        source="fred",
        raw_code=code,
        label=label,
        frequency="mensal",
        refresh_mode="refetch_full",
        fetch=lambda start_date=None, end_date=None: get_fred_series(code),
    )


# FRED é opcional: sem FRED_API_KEY as séries ficam fora do manifesto, e o
# refresh do warehouse não registra falhas por uma fonte que nunca foi ativada.
if fred_available():
    SERIES_REGISTRY.extend(
        _fred_spec(meta["code"], f"{meta['name']} — EUA (FRED)")
        for meta in FRED_SERIES_MAP.values()
    )

_COLUMN_TO_SERIES_ID = {spec.raw_code: spec.id for spec in SERIES_REGISTRY}
_ID_TO_SPEC = {spec.id: spec for spec in SERIES_REGISTRY}


def resolve_series_id(column_name: object) -> Optional[str]:
    """
    Resolve o nome de uma coluna de DataFrame (ex: '432', 'pib_trimestral')
    para o series_id do warehouse (ex: 'bcb_432').

    Retorna None para colunas não registradas (ex: indicadores derivados como
    'juros_reais_pct' — fora de escopo do warehouse nesta versão).
    """
    return _COLUMN_TO_SERIES_ID.get(str(column_name))


def get_spec(series_id: str) -> Optional[SeriesSpec]:
    """Retorna a SeriesSpec de um series_id, ou None se desconhecido."""
    return _ID_TO_SPEC.get(series_id)
