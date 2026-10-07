# -*- coding: utf-8 -*-
"""
Módulo de conhecimento econômico teórico.

Carrega arquivos Markdown com teoria econômica por indicador
e os disponibiliza para o nó de análise enriquecer as respostas
com contexto científico fundamentado.
"""
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_KNOWLEDGE_DIR = Path(__file__).parent

# Mapeamento: nome da ferramenta / série → arquivo de conhecimento
_TOOL_TO_KNOWLEDGE: dict[str, str] = {
    # BCB
    "get_bcb_series": None,          # resolvido dinamicamente pelo series_code
    # IPEA
    "get_ipea_series": "fbcf_pib",
    # World Bank
    "get_gini_series": "gini",
    # IBGE
    "get_ibge_series": None,         # resolvido dinamicamente pelo series_code
    # FRED (juros dos EUA)
    "get_fred_series": "juros_externos",
    # Derivados (Onda 3) — resolvido pelo col name no _SERIES_TO_KNOWLEDGE
    "derived": None,
}

# Mapeamento direto por series_code/chave
_SERIES_TO_KNOWLEDGE: dict = {
    # BCB series codes
    433: "ipca",
    188: "ipca",
    432: "selic",
    11: "selic",
    24369: "desocupacao",
    1: "dolar",
    21619: "dolar",
    # IBGE keys
    "ipca15": "ipca",
    "pib_trimestral": "fbcf_pib",
    "rendimento_pnad": "desocupacao",
    # IPEA keys
    "GAC12_INDFBCF12": "fbcf_pib",
    # Indicadores derivados (Onda 3)
    "juros_reais_pct": "juros_reais",
    "cambio_real_idx": "dolar",
    "cambio_nominal":  "dolar",
    "inclinacao_curva_eua": "juros_externos",
}


@lru_cache(maxsize=20)
def load_theory(topic: str) -> str:
    """
    Carrega o arquivo Markdown de teoria econômica para o tópico dado.

    Parameters
    ----------
    topic : str
        Nome do tópico — 'ipca', 'selic', 'desocupacao', 'dolar', 'fbcf_pib', 'gini'.

    Returns
    -------
    str
        Conteúdo do arquivo Markdown, ou string vazia se não encontrado.
    """
    path = _KNOWLEDGE_DIR / f"{topic}.md"
    if not path.exists():
        logger.warning("Arquivo de teoria não encontrado: %s", path)
        return ""
    try:
        content = path.read_text(encoding="utf-8")
        logger.debug("Teoria carregada: %s (%d chars)", topic, len(content))
        return content
    except Exception as exc:
        logger.error("Erro ao carregar teoria '%s': %s", topic, exc)
        return ""


def get_theory_for_tool(tool_name: str, series_code=None) -> Optional[str]:
    """
    Resolve e carrega a teoria econômica relevante para a ferramenta/série usada.

    Parameters
    ----------
    tool_name : str
        Nome da ferramenta no ToolRegistry (ex: 'get_bcb_series').
    series_code : int | str | None
        Código ou chave da série (resolve ambiguidade quando há múltiplas por ferramenta).

    Returns
    -------
    Optional[str]
        Conteúdo Markdown da base teórica, ou None se não há teoria mapeada.
    """
    topic = None

    # Resolução por series_code primeiro (mais específico)
    if series_code is not None:
        # Tenta int e string
        topic = _SERIES_TO_KNOWLEDGE.get(series_code) or _SERIES_TO_KNOWLEDGE.get(
            str(series_code)
        )
        if topic is None:
            # Tenta converter para int
            try:
                topic = _SERIES_TO_KNOWLEDGE.get(int(series_code))
            except (ValueError, TypeError):
                pass

    # Fallback: resolve pelo nome da ferramenta
    if topic is None:
        topic = _TOOL_TO_KNOWLEDGE.get(tool_name)

    if topic is None:
        logger.debug("Nenhuma teoria mapeada para tool='%s' series='%s'", tool_name, series_code)
        return None

    content = load_theory(topic)
    return content if content else None
