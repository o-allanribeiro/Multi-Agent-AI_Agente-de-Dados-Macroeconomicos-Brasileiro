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
identificando TODAS as ferramentas necessárias para responder completamente.

Ferramentas disponíveis:
{tools_description}

REGRAS:
- Para perguntas simples (um indicador), use UMA ferramenta.
- Para comparações ("compare X com Y") ou análises multi-indicador, use 2 ou mais ferramentas.
- Se a pergunta não puder ser respondida com as ferramentas disponíveis, use "none".
- Para last_n_years: "últimos 2 anos" → 2, "desde 2020" → calcule até hoje, "histórico" → 10.
- Sempre inclua os parâmetros necessários em "tool_params" de cada ferramenta.
- Use o mesmo last_n_years para todas as ferramentas de uma comparação.

Responda APENAS com JSON válido no seguinte formato:
{{
  "plan": "<descrição detalhada do que você vai fazer>",
  "tools": [
    {{"tool_to_use": "<nome_da_ferramenta ou 'none'>", "tool_params": {{<parâmetros>}}}},
    {{"tool_to_use": "<segunda_ferramenta se necessário>", "tool_params": {{<parâmetros>}}}}
  ]
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

        # Suporta novo formato {"tools": [...]} e legado {"tool_to_use": ..., "tool_params": ...}
        tools_list = result.get("tools")
        if not tools_list:
            tools_list = [
                {
                    "tool_to_use": result.get("tool_to_use", "none"),
                    "tool_params": result.get("tool_params") or {},
                }
            ]

        # Valida e normaliza — garante que todos os itens têm as chaves necessárias
        valid_tools = [
            {"tool_to_use": t.get("tool_to_use", "none"), "tool_params": t.get("tool_params") or {}}
            for t in tools_list
            if isinstance(t, dict)
        ]
        if not valid_tools:
            valid_tools = [{"tool_to_use": "none", "tool_params": {}}]

        # Primeira ferramenta é executada imediatamente; as demais entram na fila
        state["tool_to_use"] = valid_tools[0]["tool_to_use"]
        state["tool_params"] = valid_tools[0]["tool_params"]
        state["pending_tools"] = valid_tools[1:]

        logger.info(
            "Plano gerado | %d ferramenta(s) | first=%s | params=%s | pending=%d",
            len(valid_tools),
            state["tool_to_use"],
            state["tool_params"],
            len(state["pending_tools"]),
        )

    except Exception as exc:
        logger.error("Erro no nó PLANNER: %s", exc, exc_info=True)
        state["error"] = f"Falha no planejamento: {exc}"
        state["tool_to_use"] = "none"
        state["tool_params"] = {}
        state["pending_tools"] = []

    return state
