# -*- coding: utf-8 -*-
"""
Nó de Visualização (Plot) — Agente Macro-BR.

Responsabilidade: gerar gráfico de linha da série temporal, salvar
em disco e armazenar o caminho no estado.

Entrada  → state["data"], state["session_id"]
Saída    → state["plot_path"]
"""
import logging
import os
from pathlib import Path

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from agente.config import get_settings
from agente.state import AgentState

# Backend não-interativo: necessário para servidor sem display
matplotlib.use("Agg")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapeamento: código/chave da série → (nome para exibição, unidade do eixo Y)
# Cobre todas as fontes: BCB (int), IBGE (str), IPEA (str), World Bank (str)
# ---------------------------------------------------------------------------
_SERIES_LABELS: dict = {
    # BCB / SGS — codes
    433:   ("IPCA — Variação Mensal",                 "% ao mês"),
    188:   ("IPCA — Acumulado 12 meses",              "% a.a."),
    432:   ("Taxa Selic Meta (COPOM)",                "% a.a."),
    11:    ("Taxa Selic Over",                        "% a.a."),
    24369: ("Taxa de Desocupação — PNAD Contínua",    "%"),
    1:     ("Taxa de Câmbio — Dólar PTAX (Venda)",   "R$/USD"),
    21619: ("Taxa de Câmbio — Dólar PTAX (Compra)",  "R$/USD"),
    4189:  ("Taxa de Câmbio — Euro / Real",           "R$/EUR"),
    10813: ("IPCA — Acumulado no Ano",               "% a.a."),
    13522: ("IPCA-E — Acumulado 12 meses",           "% a.a."),
    # IBGE / SIDRA — keys
    "pib_trimestral":  ("PIB Trimestral — Variação vs. Trimestre Anterior", "% (t/t-1)"),
    "ipca15":          ("IPCA-15 — Prévia da Inflação",                     "Variação % ao mês"),
    "rendimento_pnad": ("Rendimento Médio Real Habitual — PNAD Contínua",   "R$ mensais"),
    # IPEA — codes
    "GAC12_INDFBCF12": ("Formação Bruta de Capital Fixo (FBCF)",            "Índice (2010 = 100)"),
    # World Bank — indicator codes
    "SI.POV.GINI":     ("Coeficiente de Gini — Brasil",                     "Índice (0 – 1)"),
    "NY.GDP.MKTP.CD":  ("PIB — Dólares Correntes (Banco Mundial)",          "USD"),
}


def plot_node(state: AgentState) -> AgentState:
    """
    Nó de Visualização: gera e salva gráfico da série temporal.

    - Série única: gráfico de linha com fill_between e anotação do último valor.
    - Múltiplas séries: subplots verticais (1 por série), paleta de cores distinta.

    Parameters
    ----------
    state : AgentState
        Estado com 'data' e 'session_id' preenchidos.

    Returns
    -------
    AgentState
        Estado atualizado com 'plot_path'.
    """
    logger.info("Executando nó PLOT | session=%s", state.get("session_id"))

    df = state.get("data")
    if df is None or df.empty:
        logger.warning("Sem dados para plotar. Pulando geração de gráfico.")
        return state

    settings = get_settings()
    output_dir = Path(settings.agent_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    session_id = state.get("session_id", "default")
    plot_path = str(output_dir / f"chart_{session_id}.png")

    n_series = len(df.columns)

    try:
        plt.style.use("seaborn-v0_8-whitegrid")

        if n_series == 1:
            _plot_single(df, state, plot_path)
        else:
            _plot_multi(df, state, plot_path)

        state["plot_path"] = plot_path
        logger.info("Gráfico salvo | path=%s | séries=%d", plot_path, n_series)

    except Exception as exc:
        logger.error("Erro no nó PLOT: %s", exc, exc_info=True)

    return state


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _resolve_label(series_name, state: AgentState):
    """Resolve (display_name, y_unit) para um código/chave de série."""
    series_key: object = series_name
    try:
        series_key = int(series_name)
    except (ValueError, TypeError):
        pass

    label_info = _SERIES_LABELS.get(series_key)
    if label_info is None:
        tool_params = state.get("tool_params") or {}
        tool_name = state.get("tool_to_use", "")
        if tool_name == "get_gini_series":
            label_info = _SERIES_LABELS.get("SI.POV.GINI")
        elif tool_name == "get_ipea_series":
            label_info = _SERIES_LABELS.get(tool_params.get("series_code", ""))

    return label_info if label_info else (str(series_name), "Valor")


def _plot_single(df: "pd.DataFrame", state: AgentState, plot_path: str) -> None:
    """Gráfico de linha único com fill_between e anotação."""
    fig, ax = plt.subplots(figsize=(12, 6))

    series_name = df.columns[0]
    color_primary = "#1f4e79"
    color_secondary = "#2e75b6"

    display_name, y_unit = _resolve_label(series_name, state)

    series = df[series_name].dropna()

    ax.plot(series.index, series, color=color_primary, linewidth=2, zorder=3)
    ax.fill_between(series.index, series, alpha=0.08, color=color_secondary)

    last_date = series.index[-1]
    last_value = series.iloc[-1]
    ax.annotate(
        f"{last_value:.2f}",
        xy=(last_date, last_value),
        xytext=(10, 10),
        textcoords="offset points",
        fontsize=9,
        color=color_primary,
        arrowprops={"arrowstyle": "->", "color": color_primary, "lw": 1.2},
    )

    ax.set_title(display_name, fontsize=16, fontweight="bold", pad=15)
    ax.set_xlabel("Data", fontsize=12)
    ax.set_ylabel(y_unit, fontsize=12)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.autofmt_xdate(rotation=30)

    if series.min() < 0 < series.max():
        ax.axhline(y=0, color="gray", linewidth=0.8, linestyle="--", alpha=0.6)

    fig.text(
        0.5, 0.01,
        f"Fonte: Agente Macro-BR | Período: "
        f"{series.index.min().strftime('%b/%Y')} – {series.index.max().strftime('%b/%Y')}",
        ha="center", fontsize=8, color="gray",
    )

    plt.tight_layout(rect=(0, 0.03, 1, 1))
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


_PALETTE = [
    "#1f4e79", "#c00000", "#375623", "#7030a0",
    "#c55a11", "#2f5496", "#833c00", "#4472c4",
]


def _plot_multi(df: "pd.DataFrame", state: AgentState, plot_path: str) -> None:
    """Subplots verticais: um painel por série para escalas diferentes."""
    n = len(df.columns)
    fig, axes = plt.subplots(n, 1, figsize=(12, 4 * n), sharex=False)
    if n == 1:
        axes = [axes]

    # Título geral com nomes de todos os indicadores
    labels = [_resolve_label(col, state)[0] for col in df.columns]
    fig.suptitle(
        "Análise Comparativa: " + " × ".join(labels),
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )

    for ax, col, color in zip(axes, df.columns, _PALETTE):
        display_name, y_unit = _resolve_label(col, state)
        series = df[col].dropna()
        if series.empty:
            ax.set_visible(False)
            continue

        ax.plot(series.index, series, color=color, linewidth=2)
        ax.fill_between(series.index, series, alpha=0.07, color=color)

        # Anotação último valor
        ax.annotate(
            f"{series.iloc[-1]:.2f}",
            xy=(series.index[-1], series.iloc[-1]),
            xytext=(8, 8),
            textcoords="offset points",
            fontsize=8,
            color=color,
            arrowprops={"arrowstyle": "->", "color": color, "lw": 1.0},
        )

        if series.min() < 0 < series.max():
            ax.axhline(y=0, color="gray", linewidth=0.7, linestyle="--", alpha=0.5)

        ax.set_title(display_name, fontsize=11, fontweight="bold", loc="left", pad=6)
        ax.set_ylabel(y_unit, fontsize=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.tick_params(axis="x", rotation=25)

    # Rodapé global
    periods = [
        f"{df[c].dropna().index.min().strftime('%b/%Y')}–{df[c].dropna().index.max().strftime('%b/%Y')}"
        for c in df.columns if not df[c].dropna().empty
    ]
    fig.text(
        0.5, 0.005,
        "Fonte: Agente Macro-BR | " + " | ".join(f"{c}: {p}" for c, p in zip(df.columns, periods)),
        ha="center", fontsize=7, color="gray",
    )

    plt.tight_layout(rect=(0, 0.02, 1, 0.99))
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
