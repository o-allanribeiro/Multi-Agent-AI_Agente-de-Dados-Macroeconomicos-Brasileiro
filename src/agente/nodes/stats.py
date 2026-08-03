# -*- coding: utf-8 -*-
"""
nodes/stats.py — Nó de Estatísticas Históricas.

Responsabilidade: calcular contexto histórico descritivo para cada série
coletada, antes de passar para o LLM. Permite que a análise compare o
cenário atual com a média histórica, percentil e tendência recente —
sem depender do LLM para fazer essa matemática.

Entrada  → state["data"] (DataFrame com séries coletadas)
Saída    → state["historical_stats"] (dict por coluna)
           state["derived_data"]     (dict de DataFrames derivados)
"""

import logging
from typing import Any, Dict

import numpy as np
import pandas as pd

from agente.state import AgentState

logger = logging.getLogger(__name__)


def _compute_series_stats(series: pd.Series) -> Dict[str, Any]:
    """
    Calcula estatísticas descritivas e de posição para uma série temporal.

    Returns
    -------
    dict com:
        latest_value, latest_date, mean_1y, mean_3y, mean_5y, mean_full,
        std_full, zscore_latest, percentile_rank, min_full, max_full,
        trend_3m (='alta'|'baixa'|'estavel'), n_obs, lag_days
    """
    s = series.dropna().copy()
    if s.empty:
        return {}

    s.index = pd.to_datetime(s.index)
    s = s.sort_index()

    now = s.index[-1]
    lag_days = (pd.Timestamp.now() - now).days

    latest_value = float(s.iloc[-1])
    latest_date = str(now.date())

    # Janelas temporais
    cutoff_1y = now - pd.DateOffset(years=1)
    cutoff_3y = now - pd.DateOffset(years=3)
    cutoff_5y = now - pd.DateOffset(years=5)

    def _mean_since(cutoff):
        sub = s[s.index >= cutoff]
        return float(sub.mean()) if not sub.empty else None

    mean_1y = _mean_since(cutoff_1y)
    mean_3y = _mean_since(cutoff_3y)
    mean_5y = _mean_since(cutoff_5y)
    mean_full = float(s.mean())
    std_full = float(s.std())

    # Z-score do valor mais recente em relação ao histórico completo
    zscore = (latest_value - mean_full) / std_full if std_full > 0 else 0.0

    # Percentil na distribuição histórica completa
    percentile_rank = float((s < latest_value).mean() * 100)

    # Tendência dos últimos 3 meses
    s_3m = s[s.index >= now - pd.DateOffset(months=3)]
    if len(s_3m) >= 2:
        slope = float(np.polyfit(range(len(s_3m)), s_3m.values, 1)[0])
        tol = std_full * 0.05 if std_full > 0 else 0.01
        if slope > tol:
            trend_3m = "alta"
        elif slope < -tol:
            trend_3m = "baixa"
        else:
            trend_3m = "estável"
    else:
        trend_3m = "insuficiente"

    return {
        "latest_value": round(latest_value, 4),
        "latest_date": latest_date,
        "lag_days": lag_days,
        "mean_1y": round(mean_1y, 4) if mean_1y is not None else None,
        "mean_3y": round(mean_3y, 4) if mean_3y is not None else None,
        "mean_5y": round(mean_5y, 4) if mean_5y is not None else None,
        "mean_full": round(mean_full, 4),
        "std_full": round(std_full, 4),
        "zscore_latest": round(zscore, 2),
        "percentile_rank": round(percentile_rank, 1),
        "min_full": round(float(s.min()), 4),
        "max_full": round(float(s.max()), 4),
        "trend_3m": trend_3m,
        "n_obs": int(len(s)),
    }


def _format_stats_context(stats: Dict[str, Dict]) -> str:
    """
    Formata o dicionário de stats em texto estruturado para o prompt do LLM.
    """
    if not stats:
        return "Estatísticas históricas: indisponíveis."

    lines = ["=== CONTEXTO HISTÓRICO (calculado via Python, não estimado) ==="]
    for col, st in stats.items():
        if not st:
            continue
        lines.append(f"\n[{col.upper()}]")
        lines.append(f"  Último valor : {st['latest_value']} ({st['latest_date']})")
        lines.append(f"  Defasagem    : {st['lag_days']} dias")
        lines.append(f"  Média 1 ano  : {st.get('mean_1y', 'N/D')}")
        lines.append(f"  Média 3 anos : {st.get('mean_3y', 'N/D')}")
        lines.append(f"  Média 5 anos : {st.get('mean_5y', 'N/D')}")
        lines.append(f"  Média total  : {st['mean_full']} (σ={st['std_full']})")
        lines.append(
            f"  Z-score atual: {st['zscore_latest']} "
            f"({'acima' if st['zscore_latest'] > 0 else 'abaixo'} da média)"
        )
        lines.append(f"  Percentil    : {st['percentile_rank']}% do histórico")
        lines.append(f"  Min / Max    : {st['min_full']} / {st['max_full']}")
        lines.append(f"  Tendência 3m : {st['trend_3m']}")

    return "\n".join(lines)


def _series_for_stats(col: str, window_series: pd.Series) -> pd.Series:
    """
    Decide qual série usar para calcular estatísticas históricas de uma coluna.

    Sem isto, z-score/percentil/médias eram calculados sobre a mesma janela
    que o Planner buscou para EXIBIR no gráfico (2, 3, 5 ou 10 anos, conforme
    a pergunta) — o mesmo valor atual podia cair em percentis bem diferentes
    dependendo de como a pergunta foi formulada (ver docs/CHANGELOG.md).

    Se a coluna corresponde a uma série conhecida do warehouse (histórico
    completo salvo incrementalmente — ver `warehouse/registry.py`), combina
    esse histórico com a janela ao vivo (o valor mais recente buscado sempre
    prevalece em caso de sobreposição, então `latest_value`/`latest_date`
    nunca ficam desatualizados por causa do warehouse). Fallback silencioso
    para a série da janela se o warehouse não tiver dados para essa coluna
    (indicadores derivados, ou série ainda não coletada pelo pipeline).
    """
    try:
        from warehouse.registry import resolve_series_id
        from warehouse.store import get_warehouse_store

        series_id = resolve_series_id(col)
        if series_id is None:
            return window_series

        full_hist = get_warehouse_store().read_full(series_id)
        if full_hist.empty:
            return window_series

        combined = pd.concat([full_hist["value"], window_series])
        return combined[~combined.index.duplicated(keep="last")].sort_index()

    except Exception as exc:
        logger.debug("Warehouse indisponível para coluna '%s', usando janela ao vivo: %s", col, exc)
        return window_series


def stats_node(state: AgentState) -> AgentState:
    """
    Nó de Estatísticas: calcula contexto histórico e indicadores derivados.

    Parâmetros calculados por série:
      - Últimos valores e datas
      - Médias de 1, 3 e 5 anos
      - Z-score e percentil em relação ao histórico completo
      - Tendência dos últimos 3 meses

    Indicadores derivados detectados na pergunta:
      - Juros Reais ex-post (Fisher): (1+Selic)/(1+IPCA_12m) - 1
      - Câmbio Real Bilateral simplificado
    """
    logger.info("Executando nó STATS | session=%s", state.get("session_id"))

    df = state.get("data")
    if df is None or df.empty:
        logger.warning("STATS: sem dados disponíveis para calcular estatísticas.")
        state["historical_stats"] = {}
        state["historical_stats_text"] = ""
        state["derived_data"] = {}
        return state

    # --- 1. Estatísticas descritivas por coluna ---
    stats: Dict[str, Dict] = {}
    for col in df.columns:
        stats[col] = _compute_series_stats(_series_for_stats(col, df[col]))

    state["historical_stats"] = stats
    state["historical_stats_text"] = _format_stats_context(stats)

    # --- 2. Indicadores derivados detectados na pergunta ---
    from tools.derived import apply_derived, detect_derived_needed

    question = state.get("question", "")
    needed = detect_derived_needed(question)

    derived_results = {}
    if needed:
        derived_map = apply_derived(df, needed)
        for name, derived_df in derived_map.items():
            derived_results[name] = derived_df
            # Calcula stats também para os derivados
            for col in derived_df.columns:
                stats[f"{name}.{col}"] = _compute_series_stats(derived_df[col])

        # Re-gera o texto de stats incluindo derivados
        state["historical_stats"] = stats
        state["historical_stats_text"] = _format_stats_context(stats)

    state["derived_data"] = derived_results

    if derived_results:
        logger.info(
            "STATS: derivados calculados=%s | session=%s",
            list(derived_results.keys()),
            state.get("session_id"),
        )

    return state
