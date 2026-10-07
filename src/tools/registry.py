# -*- coding: utf-8 -*-
"""
ToolRegistry — Registro centralizado de ferramentas do agente.

Implementa o padrão Registry para gerenciar tools disponíveis.
Facilita extensão (Fase D: novas fontes) via registro dinâmico,
sem necessidade de alterar o código do Planner.
"""
import logging
import types
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
    "get_ibge_series": {
        "description": "Dados do IBGE via API SIDRA (Sistema de Recuperação Automática).",
        "use_for": "PIB trimestral, IPCA-15 (prévia do IPCA), Rendimento médio real PNAD",
        "params": "series_code (str), last_n (int, default=20)",
        "mapping": "PIB='pib_trimestral' | IPCA-15='ipca15' | Rendimento='rendimento_pnad'",
    },
}

# Só entra no registry (e no prompt do Planner) quando FRED_API_KEY está configurada.
_FRED_TOOL_METADATA: Dict = {
    "description": "Juros dos Estados Unidos (FRED — Federal Reserve Bank of St. Louis).",
    "use_for": "T-Bill de 3 meses e Treasuries de 1, 2, 5 e 10 anos (juros externos)",
    "params": "series_code (str), last_n_years (int) OU start_date (str YYYY-MM-DD)",
    "mapping": "T-Bill 3m='TB3MS' | 1a='GS1' | 2a='GS2' | 5a='GS5' | 10a='GS10'",
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
        from tools.fred import fred_available, get_fred_series
        from tools.ibge import get_ibge_series
        from tools.ipea import get_ipea_series
        from tools.world_bank import get_gini_series

        tools: Dict[str, Callable] = {
            "get_bcb_series":  get_bcb_series,
            "get_ipea_series": get_ipea_series,
            "get_gini_series": get_gini_series,
            "get_ibge_series": get_ibge_series,
        }
        metadata: Dict[str, Dict] = dict(_TOOLS_METADATA)

        # FRED é opcional: sem chave a ferramenta nem aparece para o Planner.
        if fred_available():
            tools["get_fred_series"] = get_fred_series
            metadata["get_fred_series"] = _FRED_TOOL_METADATA
        else:
            logger.info("FRED_API_KEY ausente — ferramenta get_fred_series desativada")

        # Dicionário somente-leitura: impede mutações acidentais pós-inicialização,
        # garantindo que o singleton compartilhado em ambiente async seja thread-safe.
        self._tools: types.MappingProxyType = types.MappingProxyType(tools)
        self._metadata: types.MappingProxyType = types.MappingProxyType(metadata)

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
        Registra uma nova ferramenta.

        IMPORTANTE: opera sobre o dict interno antes de congelar (apenas em testes/setup).
        Não é thread-safe — deve ser chamado ANTES da primeira requisição (fase de startup).
        """
        # Cria novo proxy incluindo a nova entrada (MappingProxyType é imutável, recriamos)
        tools_dict = dict(self._tools)
        tools_dict[name] = fn
        self._tools = types.MappingProxyType(tools_dict)

        if metadata:
            meta_dict = dict(self._metadata)
            meta_dict[name] = metadata
            self._metadata = types.MappingProxyType(meta_dict)

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
