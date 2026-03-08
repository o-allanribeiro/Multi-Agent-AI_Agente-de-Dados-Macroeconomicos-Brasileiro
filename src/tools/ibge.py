# -*- coding: utf-8 -*-
"""
Ferramenta IBGE — Instituto Brasileiro de Geografia e Estatística.

FASE D (Expansão de Dados): stub para futura integração com a API IBGE.
Referência: https://servicodados.ibge.gov.br/api/docs
"""
import logging
from typing import Optional

import pandas as pd

from tools.base import DataSource

logger = logging.getLogger(__name__)


class IBGEDataSource(DataSource):
    """Fonte de dados do IBGE via API REST (implementação futura — Fase D)."""

    source_name = "IBGE"

    def fetch(self, series_code: str, **kwargs) -> Optional[pd.DataFrame]:
        """
        Placeholder para integração futura com a API IBGE.

        TODO (Fase D):
          - Integrar PNAD Contínua por setor (desemprego setorial)
          - Integrar IBGE Agregados (PIB, produção industrial)
          - Referência: https://servicodados.ibge.gov.br/api/docs/agregados

        Parameters
        ----------
        series_code : str
            Código do indicador IBGE.

        Returns
        -------
        None
            Retorna None até a implementação da Fase D.
        """
        logger.warning(
            "IBGEDataSource.fetch() não implementado ainda (Fase D). série=%s",
            series_code,
        )
        return None
