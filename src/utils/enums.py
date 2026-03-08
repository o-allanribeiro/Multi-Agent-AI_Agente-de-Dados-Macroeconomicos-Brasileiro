# -*- coding: utf-8 -*-
"""
Enumerações centralizadas do domínio.

Usar enums garante consistência: evita strings mágicas espalhadas
pelo código e facilita autocomplete + refatoração segura.
"""
from enum import Enum


class DataSourceName(str, Enum):
    """Fontes de dados integradas ao agente."""

    BCB = "bcb"           # Banco Central do Brasil
    IPEA = "ipea"         # Instituto de Pesquisa Econômica Aplicada
    WORLD_BANK = "world_bank"  # Banco Mundial
    IBGE = "ibge"         # Instituto Brasileiro de Geografia e Estatística


class Indicator(str, Enum):
    """Indicadores macroeconômicos suportados pelo agente."""

    IPCA = "ipca"
    SELIC = "selic"
    TAXA_DESOCUPACAO = "taxa_desocupacao"
    DOLAR = "dolar"
    FBCF = "fbcf"
    GINI = "gini"


class OutputFormat(str, Enum):
    """Formatos de saída para gráficos."""

    PNG = "png"
    SVG = "svg"
    PDF = "pdf"


class StorageBackend(str, Enum):
    """Backends de armazenamento disponíveis."""

    SQLITE = "sqlite"
    DYNAMODB = "dynamodb"


class AppEnvironment(str, Enum):
    """Ambientes de execução disponíveis."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"
