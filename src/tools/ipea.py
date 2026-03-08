# -*- coding: utf-8 -*-
"""
Ferramenta IPEADATA — Instituto de Pesquisa Econômica Aplicada.

Coleta séries temporais via API REST pública do IPEADATA (OData v4).

Séries suportadas:
  - FBCF (GAC12_INDFBCF12): Formação Bruta de Capital Fixo

Referência: http://www.ipeadata.gov.br/api/
"""
import logging
from typing import Optional

import pandas as pd
import requests

from tools.base import DataSource
from utils.validators import validate_series_code

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{series_code}')"

# Mapeamento centralizado de séries IPEA
IPEA_SERIES_MAP: dict[str, dict] = {
    "fbcf": {
        "code": "GAC12_INDFBCF12",
        "name": "Formação Bruta de Capital Fixo (FBCF)",
        "unit": "Índice (média 1995 = 100, dessazonalizado)",
        "description": "Mede o nível de investimento em bens de capital da economia.",
    },
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


class IPEADataSource(DataSource):
    """Fonte de dados do IPEADATA via API OData REST."""

    source_name = "IPEADATA"

    def fetch(
        self,
        series_code: str,
        timeout: int = 30,
        **kwargs,
    ) -> Optional[pd.DataFrame]:
        """
        Busca uma série temporal do IPEADATA.

        Parameters
        ----------
        series_code : str
            Código da série no IPEADATA (ex: 'GAC12_INDFBCF12').
        timeout : int
            Timeout em segundos para a requisição HTTP.

        Returns
        -------
        Optional[pd.DataFrame]
            DataFrame com índice DatetimeIndex e 1 coluna,
            ou None em caso de erro.
        """
        if not validate_series_code(series_code):
            logger.error("Código de série IPEA inválido: %s", series_code)
            return None

        url = _BASE_URL.format(series_code=series_code)
        logger.info("Consultando IPEADATA | série=%s", series_code)

        try:
            response = requests.get(url, headers=_HEADERS, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            if not data or "value" not in data or not data["value"]:
                self._log_empty(series_code)
                return None

            df = pd.DataFrame(data["value"])[["VALDATA", "VALVALOR"]]
            df = df.rename(columns={"VALDATA": "Date", "VALVALOR": series_code})

            # Conversão robusta de datas (erros → NaT → drop)
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df.dropna(subset=["Date"])
            df = df.set_index("Date").sort_index()

            self._log_success(series_code, len(df))
            return df

        except requests.exceptions.RequestException as exc:
            self._log_error(series_code, exc)
            return None
        except Exception as exc:
            self._log_error(series_code, exc)
            return None


_ipea_source = IPEADataSource()


def get_ipea_series(series_code: str) -> Optional[pd.DataFrame]:
    """
    Função de conveniência para buscar série do IPEADATA.

    Parameters
    ----------
    series_code : str
        Código da série (ex: 'GAC12_INDFBCF12').

    Returns
    -------
    Optional[pd.DataFrame]
    """
    return _ipea_source.fetch(series_code=series_code)
