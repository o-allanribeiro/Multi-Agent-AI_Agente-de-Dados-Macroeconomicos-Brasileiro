# -*- coding: utf-8 -*-
"""
utils/cost_tracker.py — Estimativa de custo por requisição (Gemini + APIs).

Registra métricas de uso no log estruturado para análise posterior.
Não há chamada de API externa — apenas logging local.

Referências de preço (Gemini 2.5 Flash, março 2026 — verificar em aistudio.google.com):
  - Input:  $0.075 / 1M tokens (thinking desativado)
  - Output: $0.30  / 1M tokens

As estimativas são APROXIMADAS baseadas em médias observadas.
Use os logs de 'cost_estimate_usd' para calibrar a estimativa ao longo do tempo.

Uso:
    from utils.cost_tracker import log_request_cost
    log_request_cost(session_id, tool_used, has_data, has_plot, duration_ms)
"""
import logging

logger = logging.getLogger("cost_tracker")

# ------------------------------------------------------------------
# Estimativas médias de tokens por fase do pipeline (valores observados)
# ------------------------------------------------------------------
_PLANNER_INPUT_TOKENS  = 800    # prompt do sistema + descrição das ferramentas + pergunta
_PLANNER_OUTPUT_TOKENS = 150    # JSON do plano
_ANALYSIS_INPUT_TOKENS = 2_500  # prompt + teoria (~2KB) + dados + pergunta
_ANALYSIS_OUTPUT_TOKENS = 600   # 2-3 parágrafos
_RESPONSE_INPUT_TOKENS  = 1_200 # análise + plano + pergunta
_RESPONSE_OUTPUT_TOKENS = 400   # resposta final

# Por ferramenta extra (multi-tool): add planner é zero (já calculado), só analysis
_EXTRA_SERIES_ANALYSIS_INPUT  = 1_800
_EXTRA_SERIES_ANALYSIS_OUTPUT = 400

# Preços Gemini 2.5 Flash (USD / 1M tokens)
_PRICE_INPUT_PER_M  = 0.075
_PRICE_OUTPUT_PER_M = 0.30


def estimate_cost(n_tools: int = 1) -> dict:
    """
    Estima custo em USD para uma requisição com n_tools ferramentas.

    Returns
    -------
    dict com chaves: input_tokens, output_tokens, cost_usd
    """
    input_t = _PLANNER_INPUT_TOKENS + _ANALYSIS_INPUT_TOKENS + _RESPONSE_INPUT_TOKENS
    output_t = _PLANNER_OUTPUT_TOKENS + _ANALYSIS_OUTPUT_TOKENS + _RESPONSE_OUTPUT_TOKENS

    # Cada ferramenta extra acrescenta uma iteração de análise
    if n_tools > 1:
        input_t  += (n_tools - 1) * _EXTRA_SERIES_ANALYSIS_INPUT
        output_t += (n_tools - 1) * _EXTRA_SERIES_ANALYSIS_OUTPUT

    cost = (input_t / 1_000_000) * _PRICE_INPUT_PER_M + \
           (output_t / 1_000_000) * _PRICE_OUTPUT_PER_M

    return {"input_tokens": input_t, "output_tokens": output_t, "cost_usd": round(cost, 6)}


def log_request_cost(
    session_id: str,
    tools_used: list,
    has_data: bool,
    has_plot: bool,
    duration_ms: float,
    cache_hits: int = 0,
) -> None:
    """
    Loga estimativa de custo para uma requisição concluída.

    Campos no log (JSON em produção):
      session_id, tools_used, n_tools, duration_ms, cache_hits,
      est_input_tokens, est_output_tokens, est_cost_usd
    """
    n_tools = len(tools_used) if tools_used else 1
    est = estimate_cost(n_tools)

    logger.info(
        "COST_ESTIMATE | session=%s | tools=%s | duration_ms=%.0f | "
        "cache_hits=%d | est_input_tokens=%d | est_output_tokens=%d | est_cost_usd=%.6f",
        session_id,
        tools_used,
        duration_ms,
        cache_hits,
        est["input_tokens"],
        est["output_tokens"],
        est["cost_usd"],
    )
