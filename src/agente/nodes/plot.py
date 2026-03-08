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


def plot_node(state: AgentState) -> AgentState:
    """
    Nó de Visualização: gera e salva gráfico da série temporal.

    O nome do arquivo inclui o session_id para evitar sobrescrita em
    requisições concorrentes.

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

    # Diretório de saída — cria se não existir
    output_dir = Path(settings.agent_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Nome único por sessão para evitar conflitos concorrentes
    session_id = state.get("session_id", "default")
    plot_filename = f"chart_{session_id}.png"
    plot_path = str(output_dir / plot_filename)

    try:
        plt.style.use("seaborn-v0_8-whitegrid")
        fig, ax = plt.subplots(figsize=(12, 6))

        series_name = df.columns[0]
        color_primary = "#1f4e79"
        color_secondary = "#2e75b6"

        ax.plot(
            df.index,
            df[series_name],
            color=color_primary,
            linewidth=2,
            zorder=3,
        )
        ax.fill_between(
            df.index,
            df[series_name],
            alpha=0.08,
            color=color_secondary,
        )

        # Marcador no último ponto
        last_date = df.index[-1]
        last_value = df[series_name].iloc[-1]
        ax.annotate(
            f"{last_value:.2f}",
            xy=(last_date, last_value),
            xytext=(10, 10),
            textcoords="offset points",
            fontsize=9,
            color=color_primary,
            arrowprops={"arrowstyle": "->", "color": color_primary, "lw": 1.2},
        )

        # Títulos e labels
        ax.set_title(f"Série Temporal: {series_name}", fontsize=16, fontweight="bold", pad=15)
        ax.set_xlabel("Data", fontsize=12)
        ax.set_ylabel("Valor", fontsize=12)

        # Formatação do eixo X
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        fig.autofmt_xdate(rotation=30)

        # Linha de referência zero (se a série cruzar zero)
        if df[series_name].min() < 0 < df[series_name].max():
            ax.axhline(y=0, color="gray", linewidth=0.8, linestyle="--", alpha=0.6)

        # Rodapé com fonte dos dados
        fig.text(
            0.5,
            0.01,
            f"Fonte: Agente Macro-BR | Período: "
            f"{df.index.min().strftime('%b/%Y')} – {df.index.max().strftime('%b/%Y')}",
            ha="center",
            fontsize=8,
            color="gray",
        )

        plt.tight_layout(rect=(0, 0.03, 1, 1))
        plt.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        state["plot_path"] = plot_path
        logger.info("Gráfico salvo | path=%s", plot_path)

    except Exception as exc:
        logger.error("Erro no nó PLOT: %s", exc, exc_info=True)
        # Não propaga o erro — análise textual ainda pode ser entregue

    return state
