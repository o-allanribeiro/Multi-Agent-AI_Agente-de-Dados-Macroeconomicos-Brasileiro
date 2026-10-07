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

REGRAS GERAIS:
- Para perguntas simples (um indicador), use UMA ferramenta.
- Para comparações ("compare X com Y") ou análises multi-indicador, use 2 ou mais ferramentas.
- Se a pergunta não puder ser respondida com as ferramentas disponíveis, use "none".
- Para last_n_years: "últimos 2 anos" → 2, "desde 2020" → calcule até hoje, "histórico" → 10.
- Sempre inclua os parâmetros necessários em "tool_params" de cada ferramenta.
- Use o mesmo last_n_years para todas as ferramentas de uma comparação.

DISTINÇÃO CRÍTICA — DADOS HISTÓRICOS vs. EXPECTATIVAS/PROJEÇÕES:
  - O agente SOMENTE possui dados históricos observados (séries temporais passadas).
  - Perguntas sobre "expectativa", "projeção", "previsão", "forecast" de taxas (ex: IPCA
    esperado, Selic futura, Focus) NÃO podem ser respondidas com as ferramentas disponíveis.
  - Nesse caso, use "none" e explique claramente a limitação no campo "plan".
  - NUNCA utilize série de IPCA (433) ou Selic (432) para responder sobre expectativas
    futuras — são séries de dados realizados, não projeções.

INDICADORES DERIVADOS (calculados a partir de 2 séries primárias):
  - "juros reais" / "taxa real de juros" / "juro efetivo real" / "selic real" / "juro real ex-post":
      → Buscar OBRIGATORIAMENTE: Selic (BCB série 432) + IPCA (BCB série 433)
      → Fórmula Fisher: juros_reais = (1 + Selic) / (1 + IPCA_acum_12m) - 1
      → NÃO responder apenas com Selic ou apenas com IPCA — resultado é derivado de AMBOS.
      → "juro real ex-ante" / "expectativa de juro real" / "juro real esperado" = USE "none"
         (requer dados do Boletim Focus, não disponíveis neste agente).

  - "câmbio real" / "taxa real de câmbio" / "poder de compra do real":
      → Buscar OBRIGATORIAMENTE: Dólar PTAX (BCB série 1) + IPCA (BCB série 433)
      → Não responder apenas com o câmbio nominal.

  - "inclinação da curva de juros americana" / "yield curve" / "term spread" (SOMENTE se a
    ferramenta get_fred_series estiver listada acima):
      → Buscar OBRIGATORIAMENTE: Treasury 10 anos (GS10) + T-Bill 3 meses (TB3MS),
        ambas por get_fred_series
      → Inclinação = GS10 - TB3MS; não responder apenas com uma das duas séries.

ESCOPO DO AGENTE (para referência ao usar "none"):
  Dados disponíveis: IPCA, Taxa Selic, Taxa de Desocupação (PNAD), Dólar PTAX,
  FBCF, PIB Trimestral (IBGE/IPEA), Coeficiente de Gini (Banco Mundial).
  Juros dos EUA (T-Bill 3m e Treasuries de 1, 2, 5 e 10 anos): SOMENTE se a ferramenta
  get_fred_series estiver listada acima; caso contrário, use "none".
  NÃO disponíveis: Boletim Focus, IPCA esperado, Selic terminal, curva de juros brasileira
  (DI/pré), LCI, LCA, spreads bancários, dados do Tesouro Direto, dados de empresas.

EXEMPLOS DE MAPEAMENTO:
  "Qual o juro real?"                      → tools: [Selic/432, IPCA/433]
  "Juros reais no Brasil"                  → tools: [Selic/432, IPCA/433]
  "Expectativa de juros reais"             → none (requer Focus/ex-ante, fora do escopo)
  "Gráfico de expectativa de juros reais"  → none (idem)
  "Compare Selic e IPCA"                   → tools: [Selic/432, IPCA/433]
  "Desigualdade vs PIB"                    → tools: [Gini, PIB-IBGE]
  "Evolução do câmbio real"               → tools: [Dolar/1, IPCA/433]
  "Juros dos Treasuries de 10 anos"        → tools: [fred/GS10] (se disponível; senão none)
  "Selic versus T-Bill americano"          → tools: [Selic/432, fred/TB3MS] (se disponível)

Responda APENAS com JSON válido no seguinte formato:
{{
  "plan": "<descrição detalhada do que você vai fazer, incluindo motivo se usar none>",
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
