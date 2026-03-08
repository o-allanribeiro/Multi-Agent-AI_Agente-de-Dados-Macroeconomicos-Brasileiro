# -*- coding: utf-8 -*-
"""
Nó de Resposta (Response) — Agente Macro-BR.

Responsabilidade: sintetizar a análise gerada em uma resposta final
clara, objetiva e formatada para o usuário.

Entrada  → state["analysis"], state["question"], state["plot_path"]
Saída    → state["response"]
"""
import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from agente.config import get_settings
from agente.state import AgentState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
Você é um assistente especializado em análise de dados macroeconômicos brasileiros,
produzindo relatórios para uso governamental e acadêmico.

Sua tarefa é sintetizar a análise técnica fornecida em uma resposta final
clara, bem estruturada e acessível para diferentes públicos.

DIRETRIZES:
- Use linguagem formal mas acessível (evite jargões excessivos)
- Estruture a resposta com parágrafos bem definidos
- Destaque os números mais relevantes
- Seja objetivo: máximo 3 parágrafos
- Se um gráfico foi gerado, mencione-o ao final
- Responda em português do Brasil
"""


def response_node(state: AgentState) -> AgentState:
    """
    Nó de Resposta: sintetiza a análise em resposta final para o usuário.

    Parameters
    ----------
    state : AgentState
        Estado com 'analysis', 'question' e opcionalmente 'plot_path'.

    Returns
    -------
    AgentState
        Estado atualizado com 'response'.
    """
    logger.info("Executando nó RESPONSE | session=%s", state.get("session_id"))

    # Caso sem dados (ferramenta = none ou erro anterior)
    if state.get("error") and not state.get("analysis"):
        state["response"] = (
            "Não foi possível responder a esta pergunta com os dados disponíveis. "
            "O agente suporta consultas sobre: IPCA, Taxa Selic, Taxa de Desocupação, "
            "Dólar PTAX, FBCF e Coeficiente de Gini para o Brasil. "
            "Tente reformular sua pergunta com palavras-chave desses indicadores."
        )
        return state

    settings = get_settings()

    llm = ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.google_api_key,
        temperature=settings.llm_temperature,
        convert_system_message_to_human=True,
    )

    plot_note = (
        "\n\nUm gráfico de visualização foi gerado e está disponível junto a esta resposta."
        if state.get("plot_path")
        else ""
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM_PROMPT),
            (
                "human",
                "Análise técnica gerada:\n{analysis}\n\n"
                "Formule a resposta final para a pergunta original: {question}",
            ),
        ]
    )

    chain = prompt | llm | StrOutputParser()

    try:
        response = chain.invoke(
            {
                "analysis": state.get("analysis", "Análise não disponível."),
                "question": state["question"],
            }
        )
        state["response"] = response + plot_note
        logger.info(
            "Resposta gerada | session=%s | chars=%d",
            state.get("session_id"),
            len(state["response"]),
        )

    except Exception as exc:
        logger.error("Erro no nó RESPONSE: %s", exc, exc_info=True)
        # Fallback: entrega a análise bruta se a síntese falhar
        state["response"] = (
            state.get("analysis", "Não foi possível gerar uma resposta.") + plot_note
        )

    return state
