# -*- coding: utf-8 -*-
"""
Ferramenta IBGE — Instituto Brasileiro de Geografia e Estatística.

Integração com a API SIDRA (Sistema IBGE de Recuperação Automática).
Referência: https://servicodados.ibge.gov.br/api/docs/agregados

Indicadores implementados:
  - PIB Trimestral (Tabela 5932, Variável 6561): variação % vs. tri. anterior
  - IPCA-15 (Tabela 3065, Variável 1120): variação % mensal (prévia do IPCA)
  - PNAD — Rendimento médio real (Tabela 6392, Variável 5932): R$ mensais
"""
import logging
from typing import Optional

import pandas as pd
import requests

from tools.base import DataSource
from tools.cache import get_series_cache, make_cache_key
from utils.http import with_retry

logger = logging.getLogger(__name__)

_SIDRA_BASE = "https://servicodados.ibge.gov.br/api/v3/agregados"
_REQUEST_TIMEOUT = 20  # segundos

# Mapa de indicadores SIDRA suportados
IBGE_SERIES_MAP: dict[str, dict] = {
    "pib_trimestral": {
        "tabela": 5932,
        "variavel": 6561,
        "name": "PIB Trimestral (variação % vs. trimestre anterior)",
        "unit": "% variação trimestral",
        "freq": "trimestral",
        "description": "Taxa de crescimento do PIB a preços constantes dessazonalizado (IBGE/SCN).",
    },
    "ipca15": {
        "tabela": 3065,
        "variavel": 1120,
        "name": "IPCA-15 (variação % mensal)",
        "unit": "% variação mensal",
        "freq": "mensal",
        "description": "Prévia do IPCA — apurada do dia 16 do mês anterior ao dia 15 do mês de referência.",
    },
    "rendimento_pnad": {
        "tabela": 6390,
        "variavel": 5929,
        "name": "Rendimento médio real habitual (PNAD Contínua)",
        "unit": "R$ mensais",
        "freq": "mensal",
        "description": "Rendimento médio mensal real de todos os trabalhos das pessoas ocupadas (PNAD Contínua).",
    },
}


def _parse_sidra_response(
    data: list, series_key: str, freq: str = "mensal"
) -> Optional[pd.DataFrame]:
    """
    Converte resposta da API SIDRA em DataFrame com DatetimeIndex.

    O campo 'serie' é um dict {periodo: valor}, onde:
    - Período mensal:     '202401' → 2024-01-01 (Jan)
    - Período trimestral: '202401' → 2024-01-01 (Q1); '202402' → 2024-04-01 (Q2)
      SIDRA codifica trimestres como YYYYQN com N ∈ {01,02,03,04}.
    """
    try:
        series_block = data[0]["resultados"][0]["series"][0]["serie"]
    except (IndexError, KeyError) as exc:
        logger.error("Estrutura inesperada na resposta SIDRA: %s", exc)
        return None

    records = []
    for period_str, value_str in series_block.items():
        if value_str in ("", "-", "...", "X", ".."):
            continue
        try:
            value = float(value_str.replace(",", "."))
        except ValueError:
            continue

        # Converte período → data
        try:
            year = int(period_str[:4])
            suffix = int(period_str[4:6])
            if freq == "trimestral":
                # suffix 01-04 = quarter number → convert to start month
                month = (suffix - 1) * 3 + 1
            else:
                # mensal: suffix 01-12 = month number
                month = suffix
            date = pd.Timestamp(f"{year}-{month:02d}-01")
        except Exception:
            continue

        records.append({"date": date, series_key: value})

    if not records:
        return None

    df = pd.DataFrame(records).set_index("date").sort_index()
    return df


class IBGEDataSource(DataSource):
    """Fonte de dados do IBGE via API SIDRA."""

    source_name = "IBGE/SIDRA"

    def fetch(self, series_code: str, last_n: int = 20, **kwargs) -> Optional[pd.DataFrame]:
        """
        Busca série temporal da API SIDRA do IBGE.

        Parameters
        ----------
        series_code : str
            Chave do indicador — uma de: 'pib_trimestral', 'ipca15', 'rendimento_pnad'.
        last_n : int
            Número de períodos mais recentes a buscar (máx. 60).

        Returns
        -------
        Optional[pd.DataFrame]
            DataFrame com DatetimeIndex ou None em caso de erro.
        """
        meta = IBGE_SERIES_MAP.get(series_code)
        if meta is None:
            logger.error(
                "Série IBGE desconhecida: '%s'. Disponíveis: %s",
                series_code,
                list(IBGE_SERIES_MAP.keys()),
            )
            return None

        tabela = meta["tabela"]
        variavel = meta["variavel"]
        last_n = min(int(last_n), 60)

        if tabela == 5932:  # PIB trimestral — requer filtro por componente
            url = (
                f"{_SIDRA_BASE}/{tabela}/periodos/last{last_n}"
                f"/variaveis/{variavel}?localidades=N1[all]&classificacao=11255[90707]"
            )
        else:
            url = (
                f"{_SIDRA_BASE}/{tabela}/periodos/last{last_n}"
                f"/variaveis/{variavel}?localidades=N1[all]"
            )

        logger.info("Consultando IBGE/SIDRA | tabela=%d | variável=%d | last_n=%d", tabela, variavel, last_n)

        # Tenta cache antes da chamada de rede (SIDRA é instável — caching é essencial)
        freq = meta.get("freq", "mensal")
        cache = get_series_cache()
        cache_key = make_cache_key("ibge", series_code, lastn=last_n)
        cached_df, is_fresh = cache.get(cache_key)
        if is_fresh:
            logger.info("IBGE cache hit: %s", series_code)
            return cached_df
        if cached_df is not None:
            logger.info("IBGE cache STALE para '%s' — atualizando via API", series_code)

        try:
            resp = with_retry(
                lambda: requests.get(url, timeout=_REQUEST_TIMEOUT),
                max_retries=3,
                base_delay=2.0,
                exc_types=(
                    requests.exceptions.Timeout,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.ChunkedEncodingError,
                ),
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            logger.error("Timeout ao conectar ao IBGE/SIDRA após retries (tabela %d)", tabela)
            return None
        except requests.exceptions.HTTPError as exc:
            logger.error("Erro HTTP ao consultar IBGE/SIDRA: %s", exc)
            return None
        except Exception as exc:
            self._log_error(series_code, exc)
            return None

        freq = meta.get("freq", "mensal")
        df = _parse_sidra_response(data, series_code, freq=freq)

        if df is None or df.empty:
            self._log_empty(series_code)
            # Retorna cache stale se API falhou e há dados antigos
            if cached_df is not None:
                logger.warning("API IBGE falhou — retornando cache stale para '%s'", series_code)
                return cached_df
            return None

        cache.set(cache_key, df, frequency=freq)
        self._log_success(series_code, len(df))
        return df


# Instância singleton reutilizável
_ibge_source = IBGEDataSource()


def get_ibge_series(series_code: str, last_n: int = 20) -> Optional[pd.DataFrame]:
    """
    Função de conveniência para buscar série do IBGE/SIDRA.

    Parameters
    ----------
    series_code : str
        Chave do indicador: 'pib_trimestral', 'ipca15' ou 'rendimento_pnad'.
    last_n : int
        Número de períodos mais recentes (máx. 60). Default: 20.

    Returns
    -------
    Optional[pd.DataFrame]
        DataFrame com DatetimeIndex ou None em caso de erro.

    Examples
    --------
    >>> df = get_ibge_series("pib_trimestral", last_n=12)
    >>> df = get_ibge_series("ipca15", last_n=24)
    """
    return _ibge_source.fetch(series_code, last_n=last_n)

