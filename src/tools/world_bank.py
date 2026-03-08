# -*- coding: utf-8 -*-
"""
Ferramenta Banco Mundial — World Bank Open Data.

Coleta indicadores sociais e de desenvolvimento via biblioteca `wbgapi`.

Séries suportadas:
  - Gini (SI.POV.GINI): Coeficiente de Gini (desigualdade de renda)

Referência: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
"""
import logging
from typing import Optional

import pandas as pd
import wbgapi as wb

from tools.base import DataSource

logger = logging.getLogger(__name__)

WB_SERIES_MAP: dict[str, dict] = {
    "gini": {
        "code": "SI.POV.GINI",
        "name": "Coeficiente de Gini",
        "unit": "Índice (0 = igualdade total | 100 = desigualdade máxima)",
        "description": "Medida padrão de desigualdade de renda.",
    },
}


class WorldBankDataSource(DataSource):
    """Fonte de dados do Banco Mundial via wbgapi."""

    source_name = "World Bank"

    def fetch(
        self,
        series_code: str = "SI.POV.GINI",
        country_code: str = "BRA",
        start_year: int = 1980,
        end_year: int = 2024,
        **kwargs,
    ) -> Optional[pd.DataFrame]:
        """
        Busca um indicador do Banco Mundial para um país.

        Parameters
        ----------
        series_code : str
            Código do indicador (ex: 'SI.POV.GINI').
        country_code : str
            Código ISO alpha-3 do país (padrão: 'BRA').
        start_year : int
            Ano de início da série.
        end_year : int
            Ano de fim da série.

        Returns
        -------
        Optional[pd.DataFrame]
        """
        logger.info(
            "Consultando Banco Mundial | série=%s | país=%s | período=%d-%d",
            series_code,
            country_code,
            start_year,
            end_year,
        )

        try:
            df_wide = wb.data.DataFrame(
                series_code,
                economy=country_code,
                time=range(start_year, end_year + 1),
            )

            # Transforma formato wide (anos como colunas → YR1990, YR1991...)
            # para formato long (uma linha por ano)
            df_long = df_wide.reset_index().melt(
                id_vars=["economy"],
                var_name="Year",
                value_name=series_code,
            )

            # Remove prefixo 'YR' dos anos e converte para datetime
            df_long["Date"] = pd.to_datetime(
                df_long["Year"].str.replace("YR", "", regex=False),
                format="%Y",
            )

            df_final = (
                df_long[["Date", series_code]]
                .dropna(subset=[series_code])
                .set_index("Date")
                .sort_index()
            )

            if df_final.empty:
                self._log_empty(series_code)
                return None

            self._log_success(series_code, len(df_final))
            return df_final

        except Exception as exc:
            self._log_error(series_code, exc)
            return None


_wb_source = WorldBankDataSource()


def get_gini_series(country_code: str = "BRA") -> Optional[pd.DataFrame]:
    """
    Função de conveniência para buscar o Coeficiente de Gini.

    Parameters
    ----------
    country_code : str
        Código ISO alpha-3 do país (padrão: 'BRA').

    Returns
    -------
    Optional[pd.DataFrame]
    """
    return _wb_source.fetch(series_code="SI.POV.GINI", country_code=country_code)
