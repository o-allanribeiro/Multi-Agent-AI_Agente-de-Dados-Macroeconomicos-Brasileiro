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
import pandas as pd

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
    # Indicadores derivados — Onda 3
    "juros_reais_pct": ("Juros Reais Ex-Post — Identidade de Fisher",       "% a.a."),
    "cambio_real_idx": ("Câmbio Real Bilateral BRL/USD (Base 100)",         "Índice"),
    "cambio_nominal":  ("Câmbio Nominal BRL/USD (PTAX Venda)",              "R$/USD"),
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

    df               = state.get("data")
    derived_data     = state.get("derived_data") or {}
    historical_stats = state.get("historical_stats") or {}
    audit_flags      = state.get("audit_flags") or []

    has_raw     = df is not None and not df.empty
    has_derived = bool(derived_data)

    if not has_raw and not has_derived:
        logger.warning("Sem dados para plotar. Pulando geração de gráfico.")
        return state

    settings = get_settings()
    output_dir = Path(settings.agent_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    session_id = state.get("session_id", "default")
    plot_path = str(output_dir / f"chart_{session_id}.png")

    n_series = len(df.columns) if has_raw else 0

    try:
        plt.style.use("seaborn-v0_8-whitegrid")

        if has_derived:
            _plot_with_derived(df, derived_data, state, plot_path, historical_stats, audit_flags)
        elif n_series == 1:
            _plot_single(df, state, plot_path, historical_stats, audit_flags)
        else:
            _plot_multi(df, state, plot_path, historical_stats, audit_flags)

        state["plot_path"] = plot_path
        logger.info(
            "Gráfico salvo | path=%s | séries=%d | derivados=%d",
            plot_path, n_series, len(derived_data),
        )

    except Exception as exc:
        logger.error("Erro no nó PLOT: %s", exc, exc_info=True)

    return state


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _resolve_label(series_name, state: AgentState = None):
    """Resolve (display_name, y_unit) para um código/chave de série."""
    series_key: object = series_name
    try:
        series_key = int(series_name)
    except (ValueError, TypeError):
        pass

    label_info = _SERIES_LABELS.get(series_key)
    if label_info is None and state is not None:
        tool_params = state.get("tool_params") or {}
        tool_name = state.get("tool_to_use", "")
        if tool_name == "get_gini_series":
            label_info = _SERIES_LABELS.get("SI.POV.GINI")
        elif tool_name == "get_ipea_series":
            label_info = _SERIES_LABELS.get(tool_params.get("series_code", ""))

    return label_info if label_info else (str(series_name), "Valor")


def _draw_mean_line(ax, mean_value: float, label: str = "Média histórica") -> None:
    """Adiciona linha horizontal de média histórica ao eixo."""
    ax.axhline(
        y=mean_value,
        color="orangered",
        linewidth=1.1,
        linestyle="--",
        alpha=0.75,
        label=f"{label}: {mean_value:.2f}",
        zorder=2,
    )
    ax.legend(fontsize=8, loc="upper left", framealpha=0.7)


def _add_audit_footer(fig, audit_flags: list) -> None:
    """
    Adiciona rodapé de auditoria quando há flags críticas.
    Exibe apenas flags com CRÍTICO, OUTLIER, EXTREMOS ou NEGATIVOS.
    """
    if not audit_flags:
        return
    visible = [
        f for f in audit_flags
        if any(kw in f for kw in ("CRÍTICO", "OUTLIER", "EXTREMOS", "NEGATIVOS"))
    ]
    if not visible:
        return
    labels_text = " | ".join(visible[:3])
    fig.text(
        0.5, 0.0,
        f"\u26a0\ufe0f  {labels_text}",
        ha="center",
        fontsize=7.5,
        color="firebrick",
        style="italic",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": "#fff0f0",
              "edgecolor": "firebrick", "alpha": 0.8},
    )


def _draw_series_panel(
    ax,
    series: "pd.Series",
    display_name: str,
    y_unit: str,
    color: str,
    mean_val: float = None,
) -> None:
    """Renderiza um painel de série temporal com anotação de último valor."""
    ax.plot(series.index, series, color=color, linewidth=2)
    ax.fill_between(series.index, series, alpha=0.07, color=color)
    ax.annotate(
        f"{series.iloc[-1]:.2f}",
        xy=(series.index[-1], series.iloc[-1]),
        xytext=(8, 8),
        textcoords="offset points",
        fontsize=8,
        color=color,
        arrowprops={"arrowstyle": "->", "color": color, "lw": 1.0},
    )
    if mean_val is not None:
        _draw_mean_line(ax, mean_val)
    if series.min() < 0 < series.max():
        ax.axhline(y=0, color="gray", linewidth=0.7, linestyle="--", alpha=0.5)
    ax.set_title(display_name, fontsize=11, fontweight="bold", loc="left", pad=6)
    ax.set_ylabel(y_unit, fontsize=10)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.tick_params(axis="x", rotation=25)


def _plot_single(df: "pd.DataFrame", state: AgentState, plot_path: str,
                 historical_stats: dict = None, audit_flags: list = None) -> None:
    """Gráfico de linha único com fill_between, anotação e linha de média histórica."""
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

    # Linha de média histórica (Onda 3)
    stats = (historical_stats or {}).get(str(series_name), {})
    mean_ref = stats.get("mean_full") or stats.get("mean_5y")
    if mean_ref is not None:
        _draw_mean_line(ax, mean_ref)

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

    # Rodapé de auditoria (Onda 3)
    _add_audit_footer(fig, audit_flags)

    plt.tight_layout(rect=(0, 0.04, 1, 1))
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


_PALETTE = [
    "#1f4e79", "#c00000", "#375623", "#7030a0",
    "#c55a11", "#2f5496", "#833c00", "#4472c4",
]

_COLOR_DERIVED = {
    "juros_reais": "#375623",   # verde escuro
    "cambio_real": "#7030a0",   # roxo
}


def _plot_multi(df: "pd.DataFrame", state: AgentState, plot_path: str,
               historical_stats: dict = None, audit_flags: list = None) -> None:
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

        # Linha de média histórica (Onda 3)
        stats = (historical_stats or {}).get(str(col), {})
        mean_ref = stats.get("mean_full") or stats.get("mean_5y")
        if mean_ref is not None:
            _draw_mean_line(ax, mean_ref)

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

    # Rodapé de auditoria (Onda 3)
    _add_audit_footer(fig, audit_flags)

    plt.tight_layout(rect=(0, 0.03, 1, 0.99))
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_with_derived(
    df: "pd.DataFrame | None",
    derived_data: dict,
    state: AgentState,
    plot_path: str,
    historical_stats: dict = None,
    audit_flags: list = None,
) -> None:
    """
    Figura com painéis das séries brutas + painéis de indicadores derivados.

    Painéis gerados por entrada de derived_data:
      - juros_reais  → 1 painel: juros_reais_pct
      - cambio_real  → 2 painéis: cambio_nominal + cambio_real_idx
    """
    raw_cols = list(df.columns) if (df is not None and not df.empty) else []

    # Monta lista de painéis derivados: (tag, series, display_name, y_unit, color)
    derived_panels: list = []
    for name, der_df in derived_data.items():
        if der_df is None or der_df.empty:
            continue
        color = _COLOR_DERIVED.get(name, "#4472c4")
        if name == "juros_reais" and "juros_reais_pct" in der_df.columns:
            dn, yu = _SERIES_LABELS.get("juros_reais_pct", ("Juros Reais", "% a.a."))
            derived_panels.append((name, der_df["juros_reais_pct"].dropna(), dn, yu, color))
        elif name == "cambio_real":
            if "cambio_nominal" in der_df.columns:
                dn, yu = _SERIES_LABELS.get("cambio_nominal", ("Câmbio Nominal", "R$/USD"))
                derived_panels.append(
                    (name + "_nom", der_df["cambio_nominal"].dropna(), dn, yu, "#1f4e79")
                )
            if "cambio_real_idx" in der_df.columns:
                dn, yu = _SERIES_LABELS.get("cambio_real_idx", ("Câmbio Real", "Índice"))
                derived_panels.append(
                    (name + "_idx", der_df["cambio_real_idx"].dropna(), dn, yu, color)
                )

    n_total = len(raw_cols) + len(derived_panels)
    if n_total == 0:
        return

    fig, axes = plt.subplots(n_total, 1, figsize=(12, 4 * n_total), sharex=False)
    if n_total == 1:
        axes = [axes]

    # Título geral
    all_names = (
        [_resolve_label(c, state)[0] for c in raw_cols]
        + [p[2] for p in derived_panels]
    )
    fig.suptitle(
        " × ".join(all_names[:3]) + (" × …" if len(all_names) > 3 else ""),
        fontsize=12,
        fontweight="bold",
        y=0.995,
    )

    # Painéis de séries brutas
    for i, col in enumerate(raw_cols):
        display_name, y_unit = _resolve_label(col, state)
        series = df[col].dropna()
        if series.empty:
            axes[i].set_visible(False)
            continue
        stats = (historical_stats or {}).get(str(col), {})
        mean_ref = stats.get("mean_full") or stats.get("mean_5y")
        _draw_series_panel(axes[i], series, display_name, y_unit, _PALETTE[i % len(_PALETTE)], mean_ref)

    # Painéis derivados
    for j, (_, series, display_name, y_unit, color) in enumerate(derived_panels):
        _draw_series_panel(axes[len(raw_cols) + j], series, display_name, y_unit, color)

    # Rodapé de fonte
    periods_str = ""
    if df is not None and not df.empty:
        s = df[df.columns[0]].dropna()
        if not s.empty:
            periods_str = (
                f"{s.index.min().strftime('%b/%Y')} – {s.index.max().strftime('%b/%Y')}"
            )
    fig.text(
        0.5, 0.002,
        "Fonte: Agente Macro-BR" + (f" | Período: {periods_str}" if periods_str else ""),
        ha="center", fontsize=7, color="gray",
    )

    # Rodapé de auditoria (Onda 3)
    _add_audit_footer(fig, audit_flags)

    plt.tight_layout(rect=(0, 0.03, 1, 0.995))
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
