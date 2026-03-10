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
estruturada, com rigor científico e acessível a diferentes públicos.

ESTRUTURA OBRIGATÓRIA DA RESPOSTA (use Markdown):

## Síntese
Parágrafo de 3–5 linhas resumindo o achado principal com os números mais relevantes.

## Metodologia e Fonte dos Dados
- Fonte(s): informe a origem dos dados (BCB/SGS, IBGE/SIDRA, IPEA, Banco Mundial).
- Série(s): código(s) utilizado(s) (ex: BCB série 432 – Taxa Selic Meta).
- Período analisado e frequência (mensal, trimestral, anual).
- Método de cálculo (se houver indicador derivado, ex: Identidade de Fisher).

## Análise
2–3 parágrafos com tendências, valores extremos, mudanças de regime, contexto de política econômica.
Incorpore avisos de qualidade de dados (defasagem, outliers, flags de auditoria) se presentes no contexto.

## Referências Teóricas
Liste 2–4 referências relevantes no formato:
- **Fisher (1930)** — *The Theory of Interest*: explica a relação juro nominal vs. real.
- **BCB** — Notas de Política Monetária: sobre a Selic e metas.
- Etc. Adapte às séries presentes na análise.

## Limitações
- Descreva claramente o que o agente NÃO possui (ex: dados do Boletim Focus, expectativas futuras,
  dados regionais, dados de empresas individuais).
- Se a pergunta original continha aspectos fora do escopo, mencione explicitamente.
- Máximo 3 itens.

REGRAS ADICIONAIS:
- {plot_instruction}
- Responda em português do Brasil.
- Se a análise técnica já contém avisos de auditoria, incorpore-os naturalmente.
- Se os dados têm DEFASAGEM indicada, alerte explicitamente na Síntese.
- Use linguagem formal mas acessível; evite jargões sem explicação.
- Nunca invente números além dos fornecidos na análise técnica.
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
    tool_is_none = (state.get("tool_to_use") or "none") == "none"
    no_analysis = not state.get("analysis")
    if (state.get("error") or tool_is_none) and no_analysis:
        plan = state.get("plan", "")
        # Constrói resposta cortês com contexto do plano
        out_of_scope_msg = (
            "## Fora do escopo atual do agente\n\n"
            "Sua pergunta é válida e relevante, mas os dados necessários para respondê-la "
            "**não estão disponíveis neste agente**.\n\n"
        )
        if plan:
            out_of_scope_msg += f"> {plan}\n\n"
        out_of_scope_msg += (
            "## O que este agente pode responder\n\n"
            "| Categoria | Indicadores disponíveis |\n"
            "|---|---|\n"
            "| **Inflação** | IPCA mensal (BCB 433), IPCA 12 meses (BCB 188), IPCA-E (BCB 13522) |\n"
            "| **Juros** | Taxa Selic Meta (BCB 432), Selic Over (BCB 11), **Juros Reais** (Fisher) |\n"
            "| **Câmbio** | Dólar PTAX (BCB 1), Euro/Real (BCB 4189), **Câmbio Real bilateral** |\n"
            "| **Atividade** | PIB trimestral (IBGE), FBCF — índice (IPEA) |\n"
            "| **Mercado de trabalho** | Taxa de Desocupação (PNAD Contínua, BCB 24369) |\n"
            "| **Desigualdade** | Coeficiente de Gini — Brasil (Banco Mundial) |\n\n"
            "## Limitações conhecidas\n\n"
            "- ❌ **Boletim Focus / expectativas de mercado**: projeções de IPCA, Selic e câmbio esperados "
            "não estão disponíveis (requerem acesso à API do Focus/BCB).\n"
            "- ❌ **Dados regionais**: apenas índices nacionais.\n"
            "- ❌ **Dados de empresas, setores ou títulos individuais**: fora do escopo.\n\n"
            "Tente reformular sua pergunta com os indicadores listados acima."
        )
        state["response"] = out_of_scope_msg
        return state

    settings = get_settings()

    llm = ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.google_api_key,
        temperature=settings.llm_temperature,
        convert_system_message_to_human=True,
    )

    plot_instruction = (
        "Ao final, informe que um gráfico de visualização foi gerado e está disponível."
        if state.get("plot_path")
        else "Não foi gerado gráfico nesta consulta."
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM_PROMPT),
            (
                "human",
                "Contexto da consulta: {plan}\n\n"
                "Análise técnica gerada:\n{analysis}\n\n"
                "{audit_block}"
                "Formule a resposta final para a pergunta original: {question}",
            ),
        ]
    )

    chain = prompt | llm | StrOutputParser()

    # Bloco de auditoria: inclui flags se existirem
    audit_summary = state.get("audit_summary") or ""
    audit_block = (
        f"\n{audit_summary}\n\n"
        "INSTRUÇÃO: Se houver avisos de auditoria acima, incorpore-os naturalmente "
        "na resposta final, alertando o leitor sobre inconsistências ou contexto "
        "histórico relevante.\n\n"
        if audit_summary
        else ""
    )

    try:
        response = chain.invoke(
            {
                "plan":        state.get("plan", ""),
                "analysis":    state.get("analysis", "Análise não disponível."),
                "question":    state["question"],
                "plot_instruction": plot_instruction,
                "audit_block": audit_block,
            }
        )
        state["response"] = response
        logger.info(
            "Resposta gerada | session=%s | chars=%d | audit_flags=%d",
            state.get("session_id"),
            len(state["response"]),
            len(state.get("audit_flags") or []),
        )

    except Exception as exc:
        logger.error("Erro no nó RESPONSE: %s", exc, exc_info=True)
        # Fallback: entrega a análise bruta se a síntese falhar
        state["response"] = state.get("analysis", "Não foi possível gerar uma resposta.")

    return state
