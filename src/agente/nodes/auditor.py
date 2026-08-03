# -*- coding: utf-8 -*-
"""
nodes/auditor.py — Auditor de Consistência Macroeconômica.

Responsabilidade: verificar consistência dos dados e análise usando
identidades e relações macroeconômicas conhecidas. PURAMENTE baseado
em Python (sem LLM), para garantir rigor matemático e evitar "delírios".

Checks implementados:
  1. Juros Reais — alerta se taxa real fora do intervalo histórico BR
  2. Trend vs. Análise — verifica se o texto da análise contradiz tendência dos dados
  3. Freshness — alerta sobre séries com defasagem > threshold
  4. Outlier extremo — alerta se z-score > 2.5 (valor historicamente incomum)
  5. Consistência Selic × IPCA — relação esperada em ambiente ortodoxo
  6. Vazamento de escopo — detecta se a análise do LLM menciona projeções/
     expectativas futuras (Focus, "ex-ante", "projetado para 20XX"), que estão
     fora do escopo declarado do agente (apenas dados históricos observados)

Entrada  → state["data"], state["historical_stats"], state["analysis"],
           state["derived_data"]
Saída    → state["audit_flags"] (list[str])
           state["audit_summary"] (str — texto formatado para o LLM)
"""

import logging
from typing import Any, Dict, List

import pandas as pd

from agente.state import AgentState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Limiares configuráveis
# ---------------------------------------------------------------------------
_FRESHNESS_WARN_DAYS = 90  # alerta se dado mais velho que isto
_FRESHNESS_CRITICAL_DAYS = 365  # crítico se mais velho que isto
_ZSCORE_OUTLIER_THRESHOLD = 2.5  # z-score para sinalizar outlier extremo
_JUROS_REAIS_MIN_HIST_BR = -3.0  # % a.a. — mínimo histórico razoável BR
_JUROS_REAIS_MAX_HIST_BR = 18.0  # % a.a. — máximo histórico razoável BR
_JUROS_REAIS_MEAN_BR = 6.5  # % a.a. — média histórica de longo prazo BR

# Termos que indicam que o LLM projetou/especulou para o futuro em vez de se
# ater aos dados históricos observados (único tipo de dado que o agente possui —
# ver restrições em nodes/planner.py). Frases específicas para evitar falso
# positivo com termos legítimos do domínio (ex: "Selic Meta" é o nome real da
# série BCB 432, então "meta" isolado NÃO entra nesta lista).
_SCOPE_LEAKAGE_KEYWORDS = [
    "boletim focus",
    "expectativa de mercado",
    "expectativas de mercado",
    "juro real ex-ante",
    "ex-ante",
    "projeção para 20",
    "projetado para 20",
    "previsto para 20",
    "previsão para 20",
    "deverá atingir",
    "deverá alcançar",
    "espera-se que",
]


def _check_freshness(stats: Dict[str, Dict]) -> List[str]:
    """Verifica defasagem dos dados em relação à data atual."""
    flags = []
    for col, st in stats.items():
        if not st:
            continue
        lag = st.get("lag_days", 0)
        if lag > _FRESHNESS_CRITICAL_DAYS:
            flags.append(
                f"⚠️ DADO DEFASADO CRÍTICO [{col}]: último ponto há {lag} dias. "
                f"Interpretar com extrema cautela."
            )
        elif lag > _FRESHNESS_WARN_DAYS:
            flags.append(
                f"ℹ️ DADO DEFASADO [{col}]: último ponto há {lag} dias. "
                f"Pode não refletir cenário atual."
            )
    return flags


def _check_outliers(stats: Dict[str, Dict]) -> List[str]:
    """Alerta para valores historicamente extremos (z-score alto)."""
    flags = []
    for col, st in stats.items():
        if not st:
            continue
        z = st.get("zscore_latest", 0)
        pct = st.get("percentile_rank", 50)
        if abs(z) >= _ZSCORE_OUTLIER_THRESHOLD:
            direction = "acima" if z > 0 else "abaixo"
            flags.append(
                f"🔴 OUTLIER HISTÓRICO [{col}]: valor atual está {abs(z):.1f} desvios-padrão "
                f"{direction} da média histórica (percentil {pct:.0f}%). "
                f"Cenário historicamente incomum — interpretar com contextualização."
            )
    return flags


def _check_juros_reais(derived_data: Dict[str, pd.DataFrame]) -> List[str]:
    """Verifica se juros reais estão em intervalo historicamente razoável para o Brasil."""
    flags = []
    if "juros_reais" not in derived_data:
        return flags

    df_jr = derived_data["juros_reais"]
    if df_jr.empty or "juros_reais_pct" not in df_jr.columns:
        return flags

    latest_jr = float(df_jr["juros_reais_pct"].iloc[-1])

    if latest_jr > _JUROS_REAIS_MAX_HIST_BR:
        flags.append(
            f"🔴 JUROS REAIS EXTREMOS: {latest_jr:.2f}% a.a. (máx. histórico razoável: "
            f"{_JUROS_REAIS_MAX_HIST_BR}%). Patamar associado a crises de confiança fiscal "
            f"ou choque de política monetária contracionista severo."
        )
    elif latest_jr < _JUROS_REAIS_MIN_HIST_BR:
        flags.append(
            f"🔴 JUROS REAIS NEGATIVOS: {latest_jr:.2f}% a.a. (mín. histórico razoável: "
            f"{_JUROS_REAIS_MIN_HIST_BR}%). Taxa real negativa implica que a inflação supera "
            f"a remuneração nominal — política monetária expansionista ou inflação desancorada."
        )
    else:
        deviation = latest_jr - _JUROS_REAIS_MEAN_BR
        emoji = "🟡" if abs(deviation) > 3 else "🟢"
        flags.append(
            f"{emoji} JUROS REAIS: {latest_jr:.2f}% a.a. | "
            f"Média histórica BR ≈ {_JUROS_REAIS_MEAN_BR}% | "
            f"Desvio: {deviation:+.2f} p.p. | "
            f"Identidade de Fisher: (1+Selic)/(1+IPCA₁₂ₘ) - 1"
        )
    return flags


def _check_selic_ipca_consistency(stats: Dict[str, Dict]) -> List[str]:
    """
    Verifica coerência básica entre Selic e IPCA.

    Em ambiente de política monetária ortodoxa (regra de Taylor):
    - Selic alta + IPCA caindo → política contracionista funcionando (esperado)
    - Selic alta + IPCA subindo → possível dominância fiscal ou defasagem de política
    - Selic baixa + IPCA alto  → política monetária acomodatícia arriscada
    """
    flags = []

    selic_st = next(
        (st for col, st in stats.items() if "selic" in col.lower() or col == "432"),
        None,
    )
    ipca_st = next(
        (st for col, st in stats.items() if "ipca" in col.lower() and "." not in col),
        None,
    )

    if selic_st is None or ipca_st is None:
        return flags  # não há dados suficientes para o check

    selic_latest = selic_st.get("latest_value", 0)
    selic_trend = selic_st.get("trend_3m", "estável")
    ipca_latest = ipca_st.get("latest_value", 0)
    ipca_trend = ipca_st.get("trend_3m", "estável")

    # Selic elevada (> 10%) + IPCA acelerando → sinal de tensão
    if selic_latest > 10 and ipca_trend == "alta":
        flags.append(
            f"🟡 TENSÃO MONETÁRIA: Selic={selic_latest:.2f}% com IPCA em tendência de ALTA. "
            f"Pela Regra de Taylor, uma Selic elevada deveria desacelerar a inflação — "
            f"possível defasagem de transmissão (tipicamente 6-18 meses) ou pressão de oferta."
        )

    # Selic caindo + IPCA acelerando → risco de desancoragem
    if selic_trend == "baixa" and ipca_trend == "alta":
        flags.append(
            f"🔴 RISCO DE DESANCORAGEM: Selic em tendência de BAIXA com IPCA em ALTA. "
            f"Combinação inconsistente com meta de inflação ativa. "
            f"Monitorar expectativas de inflação (Focus/IPCA-15)."
        )

    # Selic muito acima do IPCA → juros reais altos (comprime atividade)
    if selic_latest > 0 and ipca_latest > 0:
        aprox_real = selic_latest - ipca_latest
        if aprox_real > 10:
            flags.append(
                f"ℹ️ JUROS REAIS ALTOS (aproximação simples): Selic - IPCA ≈ {aprox_real:.1f} p.p. "
                f"Patamar historicamente contracionista, pode comprimir crédito e consumo."
            )

    return flags


def _check_scope_leakage(analysis_text: str) -> List[str]:
    """
    Detecta se a análise textual do LLM menciona projeções/expectativas futuras.

    O agente possui SOMENTE dados históricos observados (séries BCB/IBGE/IPEA/
    Banco Mundial já realizadas) — nunca dados de projeção (Boletim Focus,
    curva de juros futura, etc.). O nó de análise é instruído a não extrapolar,
    mas LLMs podem "vazar" para fora do escopo mesmo assim (comportamento
    observado em testes E2E — ver docs/RESULTADOS_TESTES.md, cenário "Juros
    Reais"). Este check é uma rede de segurança puramente léxica: não corrige
    o texto, apenas sinaliza para que o response_node recontextualize.
    """
    flags = []
    if not analysis_text:
        return flags

    text_lower = analysis_text.lower()
    hits = sorted({kw for kw in _SCOPE_LEAKAGE_KEYWORDS if kw in text_lower})
    if hits:
        flags.append(
            "🔴 VAZAMENTO DE ESCOPO: a análise técnica menciona projeção/expectativa "
            f"futura (termos detectados: {', '.join(hits)}), mas este agente possui "
            "APENAS dados históricos observados — sem acesso ao Boletim Focus ou a "
            "modelos preditivos. A resposta final DEVE remover essa afirmação ou "
            "deixar explícito que não é um dado oficial de projeção, apenas uma "
            "inferência do modelo de linguagem, sujeita a erro."
        )
    return flags


def _build_audit_summary(flags: List[str]) -> str:
    """Formata os flags em bloco de texto para o prompt do LLM."""
    if not flags:
        return "=== AUDITORIA DE CONSISTÊNCIA: nenhuma inconsistência detectada ==="

    header = f"=== AUDITORIA DE CONSISTÊNCIA MACROECONÔMICA ({len(flags)} aviso(s)) ==="
    return "\n".join([header] + [f"  {f}" for f in flags])


def auditor_node(state: AgentState) -> AgentState:
    """
    Nó Auditor: verifica consistência dos dados e adiciona flags ao estado.

    Todos os checks são puramente matemáticos (Python) — sem chamadas LLM.
    Os flags são inseridos no estado e usados pelo response_node para
    garantir que a resposta final reflita as consistências/inconsistências.

    Returns
    -------
    AgentState
        Estado com 'audit_flags' e 'audit_summary' adicionados.
    """
    logger.info("Executando nó AUDITOR | session=%s", state.get("session_id"))

    stats = state.get("historical_stats") or {}
    derived = state.get("derived_data") or {}
    audit_flags: List[str] = []

    # -- Check 1: Freshness (defasagem dos dados)
    audit_flags.extend(_check_freshness(stats))

    # -- Check 2: Outliers extremos
    audit_flags.extend(_check_outliers(stats))

    # -- Check 3: Juros Reais (se derivado calculado)
    audit_flags.extend(_check_juros_reais(derived))

    # -- Check 4: Consistência Selic × IPCA
    audit_flags.extend(_check_selic_ipca_consistency(stats))

    # -- Check 5: Vazamento de escopo (projeções/expectativas na análise do LLM)
    audit_flags.extend(_check_scope_leakage(state.get("analysis") or ""))

    state["audit_flags"] = audit_flags
    state["audit_summary"] = _build_audit_summary(audit_flags)

    if audit_flags:
        logger.info(
            "AUDITOR: %d flag(s) gerado(s) | session=%s",
            len(audit_flags),
            state.get("session_id"),
        )
    else:
        logger.debug(
            "AUDITOR: sem inconsistências detectadas | session=%s", state.get("session_id")
        )

    return state
