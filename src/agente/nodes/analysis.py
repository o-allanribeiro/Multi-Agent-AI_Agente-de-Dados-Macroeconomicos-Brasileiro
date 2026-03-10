# -*- coding: utf-8 -*-
"""
Nó de Análise (Analysis) — Agente Macro-BR.

Responsabilidade: gerar análise textual concisa a partir do DataFrame
coletado, usando o LLM como "economista sênior".

Suporta:
  - Análise de série única
  - Análise comparativa de múltiplas séries (multi-tool queries)
  - Aviso automático de defasagem quando dados têm > 365 dias de lag

Entrada  → state["data"], state["question"]
Saída    → state["analysis"]
"""
import logging
from datetime import datetime

import pandas as pd
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from agente.config import get_settings
from agente.state import AgentState
from knowledge import get_theory_for_tool

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT_SINGLE = """\
Você é um economista sênior do Banco Central do Brasil com vasta experiência
em análise de conjuntura macroeconômica.

Sua tarefa é analisar os dados de uma série temporal e fornecer um resumo
analítico conciso de 2 a 3 parágrafos.

Inclua obrigatoriamente:
1. Tendência geral no período (alta, queda, estabilidade, volatilidade)
2. Valor mais recente e data correspondente
3. Valores mínimo e máximo históricos do período
4. Contexto econômico relevante que explique os movimentos principais
5. Se indicado no resumo que os dados têm DEFASAGEM, mencione explicitamente
   o período de referência e alerte o leitor de que o dado não é atual.

{theory_section}

{historical_context}

Seja direto, técnico e baseie-se ESTRITAMENTE nos dados fornecidos.
Use linguagem formal adequada a relatórios governamentais, porém compreensível
para um leitor sem formação estritamente econômica.

Resumo Estatístico:
{data_summary}
"""

_SYSTEM_PROMPT_MULTI = """\
Você é um economista sênior do Banco Central do Brasil com vasta experiência
em análise de conjuntura macroeconômica.

Sua tarefa é fazer uma análise COMPARATIVA entre os múltiplos indicadores abaixo.

Estruture a análise em:
1. Comportamento individual de cada indicador (tendência, min, max, último valor)
2. Relação e correlação entre os indicadores no período analisado
3. Implicações de política econômica da combinação desses dados
4. Para qualquer indicador com DEFASAGEM indicada, alerte explicitamente sobre o
   período de referência e que o dado não reflete a situação atual.
5. SE HOUVER indicadores derivados calculados (juros_reais, cambio_real etc.),
   destaque o resultado e explique a fórmula utilizada.

{theory_section}

{historical_context}

Seja direto, técnico e baseie-se ESTRITAMENTE nos dados fornecidos.
Use linguagem formal adequada a relatórios governamentais.

Resumo Estatístico (múltiplas séries):
{data_summary}
"""


def _build_series_summary(df: pd.DataFrame, col: str) -> str:
    """
    Constrói resumo estatístico de uma série, incluindo aviso de defasagem
    automático quando o último dado tem mais de 365 dias.
    """
    series = df[col].dropna()
    if series.empty:
        return f"Série ({col}): sem dados disponíveis após limpeza de valores nulos."

    last_val = series.iloc[-1]
    last_date = series.index[-1]
    min_val = series.min()
    min_date = series.idxmin()
    max_val = series.max()
    max_date = series.idxmax()
    start_date = series.index.min()
    mean_val = series.mean()
    std_val = series.std()

    lag_days = (datetime.now() - last_date.to_pydatetime().replace(tzinfo=None)).days

    lag_warning = ""
    if lag_days > 365:
        years_lag = round(lag_days / 365, 1)
        lag_warning = (
            f"\n  ⚠️  DEFASAGEM: dado mais recente tem {lag_days} dias de atraso "
            f"({years_lag} ano(s)). O valor de {last_date.strftime('%d/%m/%Y')} "
            f"NÃO reflete a situação atual. Mencione esta defasagem na análise."
        )

    return (
        f"Série ({col}):\n"
        f"  Período: {start_date.strftime('%d/%m/%Y')} a {last_date.strftime('%d/%m/%Y')}\n"
        f"  Registros: {len(series)}\n"
        f"  Valor mais recente ({last_date.strftime('%d/%m/%Y')}): {last_val:.4f}\n"
        f"  Mínimo ({min_date.strftime('%d/%m/%Y')}): {min_val:.4f}\n"
        f"  Máximo ({max_date.strftime('%d/%m/%Y')}): {max_val:.4f}\n"
        f"  Média do período: {mean_val:.4f} | Desvio padrão: {std_val:.4f}"
        + lag_warning
    )


def analysis_node(state: AgentState) -> AgentState:
    """
    Nó de Análise: gera análise textual a partir dos dados coletados.

    Detecta automaticamente análise única vs. comparativa (multi-série)
    e carrega a base de conhecimento teórico adequada para cada indicador.

    Parameters
    ----------
    state : AgentState
        Estado com 'data' (DataFrame) e 'question' preenchidos.

    Returns
    -------
    AgentState
        Estado atualizado com 'analysis'.
    """
    logger.info("Executando nó ANALYSIS | session=%s", state.get("session_id"))

    df = state.get("data")

    if df is None or df.empty:
        logger.warning("Sem dados para análise.")
        state["analysis"] = (
            "Não foram encontrados dados para o período solicitado. "
            "Tente reformular a pergunta especificando o indicador e o período desejado."
        )
        return state

    settings = get_settings()

    llm = ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.google_api_key,
        temperature=settings.llm_temperature,
        convert_system_message_to_human=True,
    )

    is_multi = len(df.columns) > 1
    plan_context = state.get("plan", "")
    tool_name = state.get("tool_to_use", "")
    tool_params = state.get("tool_params") or {}

    # ------------------------------------------------------------------
    # Contexto histórico (calculado pelo stats_node)
    # ------------------------------------------------------------------
    historical_context = state.get("historical_stats_text") or ""

    # Dados derivados (juros_reais, cambio_real etc.) calculados pelo stats_node
    derived_data = state.get("derived_data") or {}
    derived_summaries = []
    for name, derived_df in derived_data.items():
        for col in derived_df.columns:
            derived_summaries.append(_build_series_summary(derived_df, col))
    if derived_summaries:
        is_multi = True  # trata como multi quando há derivados

    # ------------------------------------------------------------------
    # Constrói resumo estatístico (por série) com detecção de defasagem
    # ------------------------------------------------------------------
    summaries = [_build_series_summary(df, col) for col in df.columns]
    if derived_summaries:
        summaries.extend(derived_summaries)
    data_summary = (
        f"Plano de consulta: {plan_context}\n\n"
        + "\n\n".join(summaries)
    )

    # ------------------------------------------------------------------
    # Carrega base teórica para cada série presente no DataFrame
    # ------------------------------------------------------------------
    theory_parts = []
    for col in df.columns:
        # Tenta resolver via series_code direto (nome da coluna)
        series_code = col
        # Para análise única, prefere o code do tool_params
        if not is_multi:
            series_code = tool_params.get("series_code") or col

        content = get_theory_for_tool(tool_name, series_code)
        if content:
            theory_parts.append(content)

    if theory_parts:
        theory_section = (
            "BASE DE CONHECIMENTO TEÓRICO (use para contextualizar a análise):\n"
            + "\n---\n".join(theory_parts)
        )
    else:
        theory_section = "Analise os dados com base no seu conhecimento econômico geral."

    # ------------------------------------------------------------------
    # Seleciona prompt e invoca LLM
    # ------------------------------------------------------------------
    system_prompt = _SYSTEM_PROMPT_MULTI if is_multi else _SYSTEM_PROMPT_SINGLE

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "Com base nesse resumo estatístico, analise a pergunta: {question}"),
        ]
    )

    chain = prompt | llm | StrOutputParser()

    try:
        analysis = chain.invoke(
            {
                "data_summary":       data_summary,
                "theory_section":     theory_section,
                "historical_context": historical_context,
                "question":           state["question"],
            }
        )
        state["analysis"] = analysis
        logger.info(
            "Análise gerada | session=%s | séries=%d | chars=%d",
            state.get("session_id"),
            len(df.columns),
            len(analysis),
        )

    except Exception as exc:
        logger.error("Erro no nó ANALYSIS: %s", exc, exc_info=True)
        # Fallback: resumo direto sem LLM
        state["analysis"] = (
            f"Dados disponíveis porém não foi possível gerar análise completa. "
            f"Indicadores: {', '.join(df.columns.tolist())}. "
            f"{summaries[0] if summaries else ''}"
        )

    return state
