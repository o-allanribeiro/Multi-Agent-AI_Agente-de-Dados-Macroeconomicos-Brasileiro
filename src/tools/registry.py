# -*- coding: utf-8 -*-
"""
ToolRegistry — Registro centralizado de ferramentas do agente.

Implementa o padrão Registry para gerenciar tools disponíveis.
Facilita extensão (Fase D: novas fontes) via registro dinâmico,
sem necessidade de alterar o código do Planner.
"""
import logging
from functools import lru_cache
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Metadados: descrição das ferramentas para o prompt do Planner
# ---------------------------------------------------------------------------
_TOOLS_METADATA: Dict[str, Dict] = {
    "get_bcb_series": {
        "description": "Dados do Banco Central do Brasil (BCB/SGS).",
        "use_for": "IPCA, Taxa Selic, Taxa de Desocupação, Dólar PTAX",
        "params": "series_code (int), last_n_years (int) OU start_date (str YYYY-MM-DD)",
        "mapping": "IPCA=433 | Selic=432 | Desocupação=24369 | Dólar=1",
    },
    "get_ipea_series": {
        "description": "Dados do IPEADATA (Instituto de Pesquisa Econômica Aplicada).",
        "use_for": "Formação Bruta de Capital Fixo (FBCF)",
        "params": "series_code (str)",
        "mapping": "FBCF='GAC12_INDFBCF12'",
    },
    "get_gini_series": {
        "description": "Coeficiente de Gini (Banco Mundial).",
        "use_for": "Desigualdade de renda para qualquer país",
        "params": "country_code (str, padrão='BRA')",
        "mapping": "Série SI.POV.GINI — Brasil=BRA",
    },
}


class ToolRegistry:
    """
    Registro thread-safe de ferramentas disponíveis para o agente.

    Attributes
    ----------
    _tools : Dict[str, Callable]
        Mapa de nome → função da ferramenta.
    _metadata : Dict[str, Dict]
        Metadados descritivos de cada ferramenta (para o prompt do Planner).

    Examples
    --------
    >>> registry = get_tool_registry()
    >>> fn = registry.get("get_bcb_series")
    >>> df = fn(series_code=433, last_n_years=5)
    """

    def __init__(self) -> None:
        # Importação local para evitar circular imports e carregar só quando necessário
        from tools.bcb import get_bcb_series
        from tools.ipea import get_ipea_series
        from tools.world_bank import get_gini_series

        self._tools: Dict[str, Callable] = {
            "get_bcb_series": get_bcb_series,
            "get_ipea_series": get_ipea_series,
            "get_gini_series": get_gini_series,
        }
        self._metadata: Dict[str, Dict] = _TOOLS_METADATA.copy()

    def get(self, name: str) -> Optional[Callable]:
        """Retorna a função da ferramenta pelo nome, ou None se não existir."""
        tool = self._tools.get(name)
        if tool is None:
            logger.warning("Ferramenta não encontrada no registry: '%s'", name)
        return tool

    def has(self, name: str) -> bool:
        """Verifica se uma ferramenta está registrada."""
        return name in self._tools

    def register(self, name: str, fn: Callable, metadata: Optional[Dict] = None) -> None:
        """
        Registra uma nova ferramenta dinamicamente.

        Parameters
        ----------
        name : str
            Identificador único da ferramenta.
        fn : Callable
            Função de coleta de dados.
        metadata : dict, optional
            Metadados descritivos para o prompt do Planner.
        """
        self._tools[name] = fn
        if metadata:
            self._metadata[name] = metadata
        logger.info("Ferramenta registrada: '%s'", name)

    def list_tools(self) -> list[str]:
        """Retorna a lista de nomes das ferramentas disponíveis."""
        return list(self._tools.keys())

    def get_tools_description(self) -> str:
        """
        Gera uma descrição textual de todas as ferramentas para uso
        no system prompt do Planner.

        Returns
        -------
        str
            Texto formatado com numeração, descrição, uso e parâmetros.
        """
        lines = []
        for i, (name, meta) in enumerate(self._metadata.items(), start=1):
            block = (
                f"{i}. `{name}`: {meta.get('description', '')}\n"
                f"   Use para: {meta.get('use_for', 'N/A')}\n"
                f"   Parâmetros: {meta.get('params', 'N/A')}\n"
                f"   Mapeamento: {meta.get('mapping', 'N/A')}"
            )
            lines.append(block)
        return "\n\n".join(lines)


@lru_cache(maxsize=1)
def get_tool_registry() -> ToolRegistry:
    """
    Retorna a instância singleton do ToolRegistry.

    Usa ``@lru_cache`` para instanciar apenas uma vez por processo.
    """
    registry = ToolRegistry()
    logger.debug("ToolRegistry instanciado | tools=%s", registry.list_tools())
    return registry
