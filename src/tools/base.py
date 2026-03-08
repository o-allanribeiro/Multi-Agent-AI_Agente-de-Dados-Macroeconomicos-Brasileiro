# -*- coding: utf-8 -*-
"""
DataSource — Classe base abstrata para todas as ferramentas de dados.

Define o contrato que TODAS as fontes de dados devem implementar,
garantindo substituição segura (princípio de Liskov) entre backends
(BCB, IPEADATA, Banco Mundial, IBGE, etc.).
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class DataSource(ABC):
    """
    Interface abstrata para fontes de dados macroeconômicos.

    Subclasses devem implementar ``fetch`` para retornar uma série
    temporal como DataFrame com índice do tipo DatetimeIndex.

    O DataFrame retornado deve seguir o padrão:
        - Índice: pd.DatetimeIndex (sorted ascending)
        - Colunas: exatamente 1 coluna numérica com nome descritivo
        - Valores: float64, sem NaN (ou com NaN explicitamente documentados)
    """

    source_name: str = "unknown"  # Identificador humano legível

    @abstractmethod
    def fetch(self, series_code: str, **kwargs) -> Optional[pd.DataFrame]:
        """
        Busca uma série temporal da fonte de dados.

        Parameters
        ----------
        series_code : str
            Código identificador da série na fonte de dados.
        **kwargs
            Parâmetros adicionais (ex: start_date, last_n_years, country_code).

        Returns
        -------
        Optional[pd.DataFrame]
            DataFrame com índice DatetimeIndex e 1 coluna numérica,
            ou None se não houver dados ou ocorrer erro irrecuperável.
        """
        ...

    def _log_success(self, series_code: str, n_records: int) -> None:
        logger.info(
            "Dados obtidos com sucesso | source=%s | series=%s | records=%d",
            self.source_name,
            series_code,
            n_records,
        )

    def _log_error(self, series_code: str, error: Exception) -> None:
        logger.error(
            "Erro ao buscar dados | source=%s | series=%s | error=%s",
            self.source_name,
            series_code,
            str(error),
        )

    def _log_empty(self, series_code: str) -> None:
        logger.warning(
            "Nenhum dado encontrado | source=%s | series=%s",
            self.source_name,
            series_code,
        )
