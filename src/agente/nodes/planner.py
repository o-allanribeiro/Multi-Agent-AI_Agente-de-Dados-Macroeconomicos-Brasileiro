# -*- coding: utf-8 -*-
"""
Nó de Planejamento (Planner) — Agente Macro-BR.

Responsabilidade: interpretar a pergunta do usuário, selecionar a
ferramenta correta e definir os parâmetros de execução.

Entrada  → state["question"]
Saída    → state["plan"], state["tool_to_use"], state["tool_params"]
"""
import logging

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from agente.config import get_settings
from agente.state import AgentState
from tools.registry import get_tool_registry

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
Você é um economista especialista e assistente de pesquisa macroeconômica do Brasil.
Sua tarefa é analisar a pergunta do usuário e criar um plano de ação detalhado,
escolhendo a melhor ferramenta disponível para responder a pergunta.

Ferramentas disponíveis:
{tools_description}

REGRAS:
- Escolha APENAS UMA ferramenta por vez.
- Se a pergunta não puder ser respondida com as ferramentas disponíveis, use "none".
- Para o parâmetro last_n_years, interprete a pergunta:
  "últimos 2 anos" → 2, "desde 2020" → calcule os anos até hoje, "histórico completo" → 10.
- Sempre inclua os parâmetros necessários em "tool_params".

Responda APENAS com JSON válido no seguinte formato:
{{
  "plan": "<descrição do que você vai fazer>",
  "tool_to_use": "<nome_da_ferramenta ou 'none'>",
  "tool_params": {{<parâmetros da ferramenta ou null>}}
}}
"""


def planner_node(state: AgentState) -> AgentState:
    """
    Nó de Planejamento: analisa a pergunta e decide qual ferramenta usar.

    Parameters
    ----------
    state : AgentState
        Estado atual do agente com 'question' preenchida.

    Returns
    -------
    AgentState
        Estado atualizado com 'plan', 'tool_to_use' e 'tool_params'.
    """
    logger.info("Executando nó PLANNER | session=%s", state.get("session_id"))

    settings = get_settings()
    registry = get_tool_registry()

    llm = ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.google_api_key,
        temperature=settings.llm_temperature,
        convert_system_message_to_human=True,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM_PROMPT),
            ("human", "{question}"),
        ]
    )

    chain = prompt | llm | JsonOutputParser()

    try:
        result = chain.invoke(
            {
                "tools_description": registry.get_tools_description(),
                "question": state["question"],
            }
        )

        state["plan"] = result.get("plan", "Plano não gerado.")
        state["tool_to_use"] = result.get("tool_to_use", "none")
        state["tool_params"] = result.get("tool_params") or {}

        logger.info(
            "Plano gerado | tool=%s | params=%s",
            state["tool_to_use"],
            state["tool_params"],
        )

    except Exception as exc:
        logger.error("Erro no nó PLANNER: %s", exc, exc_info=True)
        state["error"] = f"Falha no planejamento: {exc}"
        state["tool_to_use"] = "none"
        state["tool_params"] = {}

    return state
