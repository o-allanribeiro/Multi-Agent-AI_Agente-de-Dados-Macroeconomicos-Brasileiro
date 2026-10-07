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
analítico técnico adequado a relatórios governamentais e acadêmicos.

ESTRUTURA DO RESUMO ANALÍTICO:
1. **Tendência e Regime**: tendência geral no período (alta, queda, estabilidade, volatilidade),
   identificando mudanças de regime se houver.
2. **Estatísticas Relevantes**: valor mais recente, data, mínimo e máximo históricos, média, desvio.
3. **Contexto de Política Econômica**: fatores que explicam os movimentos principais (COPOM,
   choques externos, COVID-19, ciclos eleitorais, etc.).
4. **Qualidade dos Dados**: Se o resumo indicar DEFASAGEM, mencione explicitamente e alerte o leitor.
   Se houver outliers ou anomalias nas estatísticas, comente.

{theory_section}

{historical_context}

Baseie-se ESTRITAMENTE nos dados fornecidos. Use linguagem técnica formal.
Não invente números além dos presentes no resumo estatístico abaixo.

Resumo Estatístico:
{data_summary}
"""

_SYSTEM_PROMPT_MULTI = """\
Você é um economista sênior do Banco Central do Brasil com vasta experiência
em análise de conjuntura macroeconômica.

Sua tarefa é fazer uma análise COMPARATIVA entre os múltiplos indicadores abaixo,
adequada a relatórios acadêmicos e documentos de política econômica.

ESTRUTURA DA ANÁLISE COMPARATIVA:
1. **Comportamento Individual**: para cada indicador — tendência, min, max, último valor.
2. **Relação entre Indicadores**: correlação aparente, causalidade, defasagens observáveis.
3. **Indicadores Derivados**: se houver juros_reais ou cambio_real, destaque o resultado,
   explique a fórmula utilizada (Fisher, PPP) e compare com a série bruta.
4. **Implicações de Política Econômica**: o que a combinação desses dados implica para
   a política monetária, fiscal ou cambial do Brasil.
5. **Qualidade dos Dados**: Para indicadores com DEFASAGEM, alerte explicitamente;
   comente outliers ou anomalias identificadas.

{theory_section}

{historical_context}

Baseie-se ESTRITAMENTE nos dados fornecidos. Use linguagem técnica formal.

Resumo Estatístico (múltiplas séries):
{data_summary}
"""


def _infer_frequency(index: pd.DatetimeIndex) -> str:
    """Infere a frequência (diária/mensal/trimestral/anual) pelo espaçamento mediano do índice."""
    if len(index) < 3:
        return "indeterminada"
    median_days = pd.Series(index).diff().dropna().dt.days.median()
    if median_days <= 4:
        return "diária"
    if median_days <= 40:
        return "mensal"
    if median_days <= 110:
        return "trimestral"
    return "anual"


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
        f"  Registros: {len(series)} (frequência observada: {_infer_frequency(series.index)})\n"
        f"  Valor mais recente ({last_date.strftime('%d/%m/%Y')}): {last_val:.4f}\n"
        f"  Mínimo ({min_date.strftime('%d/%m/%Y')}): {min_val:.4f}\n"
        f"  Máximo ({max_date.strftime('%d/%m/%Y')}): {max_val:.4f}\n"
        f"  Média do período: {mean_val:.4f} | Desvio padrão: {std_val:.4f}" + lag_warning
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
    # O modelo não sabe a data de hoje: sem isto, dados recentes parecem "futuros".
    today_note = (
        f"Data de hoje: {datetime.now().strftime('%d/%m/%Y')}. "
        "Todas as datas até hoje são dados observados, não projeções.\n\n"
    )
    data_summary = (
        today_note + f"Plano de consulta: {plan_context}\n\n" + "\n\n".join(summaries)
    )

    # ------------------------------------------------------------------
    # Carrega base teórica para cada série presente no DataFrame
    # ------------------------------------------------------------------
    theory_parts = []
    seen_topics = set()
    for col in df.columns:
        # Tenta resolver via series_code direto (nome da coluna)
        series_code = col
        # Para análise única, prefere o code do tool_params
        if not is_multi:
            series_code = tool_params.get("series_code") or col

        content = get_theory_for_tool(tool_name, series_code)
        if content and content not in seen_topics:
            theory_parts.append(content)
            seen_topics.add(content)

    # Inclui teoria para indicadores derivados (juros_reais, cambio_real)
    for name, derived_df in derived_data.items():
        for col in derived_df.columns:
            content = get_theory_for_tool("derived", col)
            if content and content not in seen_topics:
                theory_parts.append(content)
                seen_topics.add(content)

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
                "data_summary": data_summary,
                "theory_section": theory_section,
                "historical_context": historical_context,
                "question": state["question"],
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
        # Inclui o resumo de TODAS as séries (antes só a primeira), para que a
        # resposta final não afirme que há dados ausentes quando eles existem.
        state["analysis"] = (
            f"Dados disponíveis porém não foi possível gerar análise completa. "
            f"Indicadores: {', '.join(df.columns.tolist())}.\n\n"
            + "\n\n".join(summaries)
        )

    return state
