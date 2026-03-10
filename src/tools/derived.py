# -*- coding: utf-8 -*-
"""
tools/derived.py — Indicadores macroeconômicos derivados.

Calcula séries que não existem diretamente nas APIs mas são derivadas
de duas ou mais séries primárias via identidades macroeconômicas.

Indicadores implementados:
  - Juros Reais ex-post: (1 + Selic) / (1 + IPCA acum_12m) - 1
  - Câmbio Real Efetivo Bilateral simples: Câmbio × (IPCA_BR / IPCA_ref)
"""
import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Nomes canônicos das colunas esperadas nos DataFrames de entrada
# ---------------------------------------------------------------------------
_SELIC_COL_CANDIDATES = ["selic", "taxa_selic", "Selic", "432"]
_IPCA_COL_CANDIDATES  = ["ipca", "IPCA", "433", "ipca_ibge"]
_CAMBIO_COL_CANDIDATES = ["dolar", "dólar", "cambio", "câmbio", "usd", "1"]


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Retorna o primeiro nome de coluna presente no df dentre os candidatos."""
    for c in candidates:
        if c in df.columns:
            return c
    # Busca parcial case-insensitive como fallback
    lower_cols = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in lower_cols:
            return lower_cols[c.lower()]
    return None


# ---------------------------------------------------------------------------
# Juros Reais ex-post
# ---------------------------------------------------------------------------

def compute_juros_reais(df: pd.DataFrame) -> pd.DataFrame | None:
    """
    Calcula a taxa de juros reais ex-post (Fisher identity).

    Fórmula:
        juros_reais = (1 + selic_anual) / (1 + ipca_acum_12m) - 1

    Onde:
      - selic_anual: taxa Selic acumulada anual (série BCB 432, % a.a.)
      - ipca_acum_12m: IPCA acumulado 12 meses (calculado como rolling sum
        das variações mensais da série BCB 433, convertida para decimal)

    Retorna None se as colunas necessárias não estiverem presentes.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com pelo menos as colunas de Selic e IPCA.

    Returns
    -------
    pd.DataFrame | None
        DataFrame com coluna 'juros_reais' (decimal), ou None.
    """
    selic_col = _find_col(df, _SELIC_COL_CANDIDATES)
    ipca_col  = _find_col(df, _IPCA_COL_CANDIDATES)

    if selic_col is None or ipca_col is None:
        logger.debug(
            "compute_juros_reais: colunas necessárias não encontradas | "
            "colunas disponíveis=%s", list(df.columns)
        )
        return None

    result = df[[selic_col, ipca_col]].copy()
    result.index = pd.to_datetime(result.index)
    result = result.sort_index()

    # Selic: série BCB 432 vem como % a.a. → converte para decimal
    selic_dec = result[selic_col] / 100.0

    # IPCA: série BCB 433 vem como % mensal → acumula 12 meses rolling
    # Para alinhar com a Selic (anualizada), soma 12 meses e converte
    ipca_dec = result[ipca_col] / 100.0
    # Acumulado composto de 12 meses
    ipca_acum_12m = (1 + ipca_dec).rolling(window=12, min_periods=6).apply(
        lambda x: x.prod() - 1, raw=True
    )

    # Identidade de Fisher
    juros_reais = (1 + selic_dec) / (1 + ipca_acum_12m) - 1

    out_df = pd.DataFrame(
        {"juros_reais": juros_reais},
        index=result.index,
    ).dropna()

    out_df["juros_reais_pct"] = out_df["juros_reais"] * 100

    logger.info(
        "Juros reais calculados | %d pontos | último=%.2f%% a.a.",
        len(out_df),
        out_df["juros_reais_pct"].iloc[-1] if not out_df.empty else float("nan"),
    )
    return out_df


# ---------------------------------------------------------------------------
# Câmbio Real Bilateral simplificado
# ---------------------------------------------------------------------------

def compute_cambio_real(df: pd.DataFrame) -> pd.DataFrame | None:
    """
    Calcula o índice de câmbio real bilateral (BRL/USD) simplificado.

    Fórmula:
        cambio_real_idx = cambio_nominal × (IPCA_BR / IPCA_BR_base)

    Normalizado para base 100 no início da série.
    Útil para comparar se o real está aprecia/desvalorizando em termos reais.

    Returns None se as colunas necessárias não estiverem presentes.
    """
    cambio_col = _find_col(df, _CAMBIO_COL_CANDIDATES)
    ipca_col   = _find_col(df, _IPCA_COL_CANDIDATES)

    if cambio_col is None or ipca_col is None:
        return None

    result = df[[cambio_col, ipca_col]].copy()
    result.index = pd.to_datetime(result.index)
    result = result.sort_index()

    # Alinha frequências: câmbio pode ser diário e IPCA mensal.
    # Reamostrar ambos para mensal (month-start) garante alinhamento correto.
    cambio_monthly = result[cambio_col].resample("MS").mean()
    ipca_monthly   = result[ipca_col].resample("MS").mean()
    result = pd.concat([cambio_monthly, ipca_monthly], axis=1).dropna()

    if result.empty:
        logger.warning("Câmbio real: DataFrame vazio após alinhamento de frequências")
        return None

    # Índice de preços acumulado (base = primeiro ponto)
    ipca_dec = result[ipca_col] / 100.0
    price_index = (1 + ipca_dec).cumprod()
    price_index = price_index / price_index.iloc[0]  # normaliza base=1

    cambio_real = result[cambio_col] * price_index
    cambio_real_idx = cambio_real / cambio_real.iloc[0] * 100  # base 100

    out_df = pd.DataFrame(
        {
            "cambio_nominal": result[cambio_col],
            "cambio_real_idx": cambio_real_idx,
        },
        index=result.index,
    ).dropna()

    logger.info("Câmbio real calculado | %d pontos", len(out_df))
    return out_df


# ---------------------------------------------------------------------------
# Dispatcher: detecta derivados aplicáveis e os computa
# ---------------------------------------------------------------------------

DERIVED_KEYWORDS = {
    "juros_reais": [
        "juro real", "juros reais", "taxa real",
        "real interest", "fisher", "juro efetivo real",
        "selic real", "taxa de juro real",
    ],
    "cambio_real": [
        "câmbio real", "cambio real", "taxa real de câmbio",
        "real exchange rate", "poder de compra do real",
    ],
}


def detect_derived_needed(question: str) -> list[str]:
    """
    Detecta quais indicadores derivados são relevantes para a pergunta.

    Returns
    -------
    list[str]
        Lista de nomes de derivados detectados (ex: ['juros_reais']).
    """
    q_lower = question.lower()
    needed = []
    for derived, keywords in DERIVED_KEYWORDS.items():
        if any(kw in q_lower for kw in keywords):
            needed.append(derived)
    return needed


def apply_derived(df: pd.DataFrame, derived_names: list[str]) -> dict[str, pd.DataFrame]:
    """
    Aplica os derivados detectados a um DataFrame combinado.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com as séries primárias já coletadas.
    derived_names : list[str]
        Lista de nomes retornados por `detect_derived_needed`.

    Returns
    -------
    dict[str, pd.DataFrame]
        Mapeamento nome → DataFrame do derivado calculado.
    """
    results = {}
    for name in derived_names:
        if name == "juros_reais":
            r = compute_juros_reais(df)
            if r is not None:
                results["juros_reais"] = r
        elif name == "cambio_real":
            r = compute_cambio_real(df)
            if r is not None:
                results["cambio_real"] = r
    return results
