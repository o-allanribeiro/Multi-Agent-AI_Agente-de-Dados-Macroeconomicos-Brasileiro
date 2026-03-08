# -*- coding: utf-8 -*-
"""Funções de validação de inputs para as ferramentas de dados."""
from typing import Union


def validate_series_code(code: Union[int, str]) -> bool:
    """
    Valida que um código de série temporal é não-vazio e do tipo correto.

    Parameters
    ----------
    code : int or str
        Código da série (ex: 433 para IPCA, 'GAC12_INDFBCF12' para FBCF).

    Returns
    -------
    bool
        True se válido, False caso contrário.
    """
    if isinstance(code, int):
        return code > 0
    if isinstance(code, str):
        return bool(code.strip())
    return False


def validate_year_range(n_years: int, min_years: int = 1, max_years: int = 50) -> bool:
    """
    Valida que o número de anos está dentro do intervalo permitido.

    Parameters
    ----------
    n_years : int
        Número de anos a buscar.
    min_years : int
        Mínimo permitido (padrão: 1).
    max_years : int
        Máximo permitido (padrão: 50).

    Returns
    -------
    bool
    """
    return min_years <= n_years <= max_years
