# -*- coding: utf-8 -*-
"""Utilitários de data para manipulação de séries temporais."""
from datetime import date, timedelta


def date_n_years_ago(n: int) -> str:
    """
    Retorna a data de N anos atrás no formato 'YYYY-MM-DD'.

    Parameters
    ----------
    n : int
        Número de anos para subtrair da data atual.

    Returns
    -------
    str
        Data formatada como 'YYYY-MM-DD'.
    """
    today = date.today()
    try:
        start = today.replace(year=today.year - n)
    except ValueError:
        # Caso de 29/fev em ano não-bissexto: retrocede para 28/fev
        start = today.replace(year=today.year - n, day=28)
    return start.strftime("%Y-%m-%d")


def today_str() -> str:
    """Retorna a data atual no formato 'YYYY-MM-DD'."""
    return date.today().strftime("%Y-%m-%d")
