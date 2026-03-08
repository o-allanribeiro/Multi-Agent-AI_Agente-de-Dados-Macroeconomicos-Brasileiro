# -*- coding: utf-8 -*-
"""
Ferramenta BCB — Banco Central do Brasil (SGS).

Coleta séries temporais via Sistema Gerenciador de Séries Temporais (SGS)
usando a biblioteca `python-bcb`.

Séries suportadas:
  - IPCA (433): Inflação mensal (% variação)
  - Selic (432): Meta da taxa básica de juros (% a.a.)
  - Taxa Desocupação (24369): Desemprego PNAD Contínua (%)
  - Dólar PTAX (1): Taxa de câmbio R$/US$ cotação de venda

Referência: https://www.bcb.gov.br/estabilidadefinanceira/seriestemporais
"""
import logging
from typing import Optional, Union

import pandas as pd
from bcb import sgs

from tools.base import DataSource
from utils.date_utils import date_n_years_ago
from utils.validators import validate_series_code, validate_year_range

logger = logging.getLogger(__name__)

# Mapeamento centralizado de séries BCB
BCB_SERIES_MAP: dict[str, dict] = {
    "ipca": {
        "code": 433,
        "name": "IPCA (Inflação)",
        "unit": "% variação mensal",
        "description": "Índice Nacional de Preços ao Consumidor Amplo — indicador oficial de inflação.",
    },
    "selic": {
        "code": 432,
        "name": "Taxa Selic (Meta)",
        "unit": "% ao ano",
        "description": "Taxa básica de juros definida pelo COPOM.",
    },
    "taxa_desocupacao": {
        "code": 24369,
        "name": "Taxa de Desocupação (PNAD Contínua)",
        "unit": "%",
        "description": "Percentual de pessoas desocupadas na força de trabalho (IBGE).",
    },
    "dolar": {
        "code": 1,
        "name": "Taxa de Câmbio (Dólar PTAX - Venda)",
        "unit": "R$/US$",
        "description": "Taxa de câmbio de referência calculada diariamente pelo BCB.",
    },
}


class BCBDataSource(DataSource):
    """Fonte de dados do Banco Central do Brasil via API SGS."""

    source_name = "BCB/SGS"

    def fetch(
        self,
        series_code: Union[int, str],
        start_date: Optional[str] = None,
        last_n_years: Optional[int] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Busca uma série temporal do SGS (Banco Central do Brasil).

        Parameters
        ----------
        series_code : int or str
            Código da série no SGS (ex: 433 para IPCA).
        start_date : str, optional
            Data de início no formato 'YYYY-MM-DD'. Tem prioridade sobre last_n_years.
        last_n_years : int, optional
            Número de anos para buscar a partir de hoje.

        Returns
        -------
        Optional[pd.DataFrame]
            DataFrame com índice DatetimeIndex e 1 coluna,
            ou None em caso de erro.
        """
        # Validação
        if not validate_series_code(series_code):
            logger.error("Código de série inválido: %s", series_code)
            return None

        # Calcula data de início
        if start_date is None and last_n_years is not None:
            if not validate_year_range(last_n_years):
                logger.error("Número de anos inválido: %d", last_n_years)
                return None
            start_date = date_n_years_ago(last_n_years)
        elif start_date is None and last_n_years is None:
            logger.error("Forneça 'start_date' ou 'last_n_years'.")
            return None

        code = int(series_code)
        logger.info("Consultando BCB/SGS | série=%d | início=%s", code, start_date)

        try:
            df = sgs.get({str(code): code}, start=start_date)

            if df is None or df.empty:
                self._log_empty(str(series_code))
                return None

            df.index = pd.to_datetime(df.index)
            df = df.sort_index()

            self._log_success(str(series_code), len(df))
            return df

        except Exception as exc:
            self._log_error(str(series_code), exc)
            return None


# Instância singleton reutilizável
_bcb_source = BCBDataSource()


def get_bcb_series(
    series_code: Union[int, str],
    start_date: Optional[str] = None,
    last_n_years: Optional[int] = None,
) -> Optional[pd.DataFrame]:
    """
    Função de conveniência para buscar série do BCB.

    Mantém compatibilidade com a interface do ToolRegistry e
    com a versão anterior do código (bcb_tools.py).

    Parameters
    ----------
    series_code : int or str
        Código da série no SGS.
    start_date : str, optional
        Data de início 'YYYY-MM-DD'.
    last_n_years : int, optional
        Número de anos retroativos.

    Returns
    -------
    Optional[pd.DataFrame]
    """
    return _bcb_source.fetch(
        series_code=series_code,
        start_date=start_date,
        last_n_years=last_n_years,
    )
