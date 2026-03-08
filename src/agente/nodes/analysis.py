# -*- coding: utf-8 -*-
"""
Nó de Análise (Analysis) — Agente Macro-BR.

Responsabilidade: gerar análise textual concisa a partir do DataFrame
coletado, usando o LLM como "economista sênior".

Entrada  → state["data"], state["question"]
Saída    → state["analysis"]
"""
import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from agente.config import get_settings
from agente.state import AgentState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
Você é um economista sênior do Banco Central do Brasil com vasta experiência
em análise de conjuntura macroeconômica.

Sua tarefa é analisar os dados de uma série temporal e fornecer um resumo
analítico conciso de 2 a 3 parágrafos.

Inclua obrigatoriamente:
1. Tendência geral no período (alta, queda, estabilidade, volatilidade)
2. Valor mais recente e data correspondente
3. Valores mínimo e máximo históricos do período
4. Contexto econômico relevante que explique os movimentos principais

Seja direto, técnico e baseie-se ESTRITAMENTE nos dados fornecidos.
Não especule além dos dados. Use linguagem formal adequada a relatórios governamentais.

Resumo Estatístico:
{data_summary}
"""


def analysis_node(state: AgentState) -> AgentState:
    """
    Nó de Análise: gera análise textual a partir dos dados coletados.

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

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM_PROMPT),
            ("human", "Com base nesse resumo estatístico, analise a pergunta: {question}"),
        ]
    )

    chain = prompt | llm | StrOutputParser()

    # Constrói resumo estatístico estruturado para o LLM
    series_name = df.columns[0]
    last_value = df[series_name].iloc[-1]
    last_date = df.index.max().strftime("%d/%m/%Y")
    min_value = df[series_name].min()
    min_date = df[series_name].idxmin().strftime("%d/%m/%Y")
    max_value = df[series_name].max()
    max_date = df[series_name].idxmax().strftime("%d/%m/%Y")
    period_start = df.index.min().strftime("%d/%m/%Y")

    data_summary = (
        f"Série: {series_name}\n"
        f"Período: {period_start} a {last_date}\n"
        f"Número de registros: {len(df)}\n"
        f"Valor mais recente ({last_date}): {last_value:.4f}\n"
        f"Valor mínimo ({min_date}): {min_value:.4f}\n"
        f"Valor máximo ({max_date}): {max_value:.4f}\n"
        f"Média do período: {df[series_name].mean():.4f}\n"
        f"Desvio padrão: {df[series_name].std():.4f}"
    )

    try:
        analysis = chain.invoke(
            {
                "data_summary": data_summary,
                "question": state["question"],
            }
        )
        state["analysis"] = analysis
        logger.info("Análise gerada | session=%s | chars=%d", state.get("session_id"), len(analysis))

    except Exception as exc:
        logger.error("Erro no nó ANALYSIS: %s", exc, exc_info=True)
        state["analysis"] = (
            f"Dados disponíveis porém não foi possível gerar análise completa. "
            f"Resumo: {series_name} de {period_start} a {last_date}. "
            f"Último valor: {last_value:.4f}."
        )

    return state
