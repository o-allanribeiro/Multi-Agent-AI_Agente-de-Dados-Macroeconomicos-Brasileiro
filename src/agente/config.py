# -*- coding: utf-8 -*-
"""
Módulo de configuração centralizada — Agente Macro-BR.

Utiliza Pydantic Settings para gerenciar configurações com:
  - Validação automática de tipos
  - Carregamento de arquivo .env
  - Suporte a variáveis de ambiente (sobrescrevem .env)
  - Compatibilidade AWS (variáveis de ambiente em ECS/Lambda)

Ordem de precedência (maior → menor):
  1. Variáveis de ambiente do sistema
  2. Arquivo .env na raiz do projeto
  3. Valores padrão definidos nesta classe

Uso:
    >>> from agente.config import get_settings
    >>> settings = get_settings()
    >>> print(settings.llm_model)
    'gemini-2.5-flash'
"""

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Raiz do projeto: src/agente/config.py → src/agente/ → src/ → PROJECT_ROOT
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"
_CONFIG_DIR = _PROJECT_ROOT / "config"


class Settings(BaseSettings):
    """
    Configurações principais da aplicação.

    Todos os campos podem ser sobrescritos por variáveis de ambiente
    com o mesmo nome (case-insensitive).

    Exemplo::

        # No .env ou como variável de sistema:
        GOOGLE_API_KEY="minha-chave"
        LOG_LEVEL="DEBUG"
        APP_ENV="production"
    """

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Credenciais (obrigatórias)
    # -------------------------------------------------------------------------
    google_api_key: str = Field(..., description="Chave da API Google AI Studio (Gemini)")

    # -------------------------------------------------------------------------
    # Ambiente
    # -------------------------------------------------------------------------
    app_env: str = Field(
        default="development", description="Ambiente: development | production | testing"
    )

    # -------------------------------------------------------------------------
    # LLM
    # -------------------------------------------------------------------------
    llm_model: str = Field(default="gemini-2.5-flash", description="Modelo Gemini a usar")
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="Temperatura do LLM")

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------
    log_level: str = Field(default="INFO", description="Nível de log: DEBUG|INFO|WARNING|ERROR")
    log_format: str = Field(default="json", description="Formato: json (CloudWatch) | text (dev)")
    log_file_path: Optional[str] = Field(
        default=None, description="Caminho do arquivo de log (None = apenas stdout)"
    )

    # -------------------------------------------------------------------------
    # API Server
    # -------------------------------------------------------------------------
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_workers: int = Field(default=1, ge=1)
    cors_origins: str = Field(
        default="http://localhost:8000,http://127.0.0.1:8000",
        description="Origens CORS separadas por vírgula ('*' só se configurado de propósito)",
    )
    admin_api_key: Optional[str] = Field(
        default=None,
        description="Chave exigida (header X-API-Key) em rotas administrativas; "
        "sem ela, essas rotas ficam desabilitadas em produção",
    )

    # -------------------------------------------------------------------------
    # Armazenamento
    # -------------------------------------------------------------------------
    storage_backend: str = Field(default="sqlite", description="Backend: sqlite | dynamodb")
    database_url: str = Field(
        default="sqlite:///./agente_macro.db",
        description="URL do SQLite ou PostgreSQL",
    )
    dynamodb_table_name: str = Field(default="agente-macro-conversations")
    dynamodb_endpoint_url: Optional[str] = Field(
        default=None,
        description="None = AWS real | 'http://localhost:8001' = DynamoDB Local",
    )

    # -------------------------------------------------------------------------
    # Agente
    # -------------------------------------------------------------------------
    agent_verbose: bool = Field(default=False, description="Exibe logs detalhados do LangGraph")
    agent_output_dir: str = Field(default="output", description="Diretório para gráficos gerados")

    # -------------------------------------------------------------------------
    # Data Warehouse (histórico incremental — DuckDB + Parquet)
    # -------------------------------------------------------------------------
    warehouse_dir: str = Field(
        default="output/warehouse",
        description="Diretório do warehouse histórico (Parquet por série + metadados DuckDB)",
    )

    # -------------------------------------------------------------------------
    # AWS (opcional — apenas para produção)
    # -------------------------------------------------------------------------
    aws_region: str = Field(default="us-east-1")
    s3_bucket_name: Optional[str] = Field(
        default=None, description="Bucket S3 para gráficos (produção)"
    )
    cloudwatch_log_group: str = Field(default="/ecs/agente-macro")

    # -------------------------------------------------------------------------
    # Validadores
    # -------------------------------------------------------------------------
    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, value: str) -> str:
        """Garante que o ambiente seja um dos valores permitidos."""
        allowed = {"development", "production", "testing"}
        if value not in allowed:
            raise ValueError(f"APP_ENV inválido: '{value}'. Deve ser um de: {allowed}")
        return value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Garante que o nível de log seja válido."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = value.upper()
        if upper not in allowed:
            raise ValueError(f"LOG_LEVEL inválido: '{value}'. Deve ser um de: {allowed}")
        return upper

    # -------------------------------------------------------------------------
    # Propriedades derivadas
    # -------------------------------------------------------------------------
    @property
    def cors_origins_list(self) -> List[str]:
        """Retorna a lista de origens CORS a partir da string separada por vírgulas."""
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def is_production(self) -> bool:
        """Retorna True se o ambiente for produção."""
        return self.app_env == "production"

    def is_development(self) -> bool:
        """Retorna True se o ambiente for desenvolvimento."""
        return self.app_env == "development"

    def is_testing(self) -> bool:
        """Retorna True se o ambiente for de testes."""
        return self.app_env == "testing"


def _load_yaml_env_defaults() -> None:
    """
    Carrega valores do YAML de configuração e os seta como variáveis de
    ambiente SOMENTE se a variável ainda não estiver definida.

    Isso garante que o YAML serve como fallback, mas variáveis de ambiente
    do sistema (ou do .env) sempre têm precedência.
    """
    env = os.getenv("APP_ENV", "development")
    config_dir = _CONFIG_DIR

    merged: dict = {}

    # 1. Carrega default.yaml
    default_file = config_dir / "default.yaml"
    if default_file.exists():
        with open(default_file, encoding="utf-8") as fh:
            merged = yaml.safe_load(fh) or {}

    # 2. Carrega e mescla environment-specific yaml
    env_file = config_dir / f"{env}.yaml"
    if env_file.exists():
        with open(env_file, encoding="utf-8") as fh:
            env_cfg = yaml.safe_load(fh) or {}
        _deep_merge(merged, env_cfg)

    # 3. Aplica ao os.environ como fallback
    _apply_to_env(merged)


def _deep_merge(base: dict, override: dict) -> None:
    """Mescla `override` em `base` de forma recursiva (in-place)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _apply_to_env(config: dict, prefix: str = "") -> None:
    """
    Aplica chaves de um dict como variáveis de ambiente com prefixo,
    ignorando chaves já definidas no ambiente.
    """
    for key, value in config.items():
        env_key = f"{prefix}{key}".upper()
        if isinstance(value, dict):
            _apply_to_env(value, f"{env_key}_")
        elif value is not None and env_key not in os.environ:
            os.environ[env_key] = str(value)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Retorna a instância singleton das configurações validadas.

    Utiliza ``@lru_cache`` para garantir carregamento único durante
    o ciclo de vida da aplicação.

    Returns
    -------
    Settings
        Instância de Settings com todos os valores validados.

    Raises
    ------
    pydantic.ValidationError
        Se alguma variável obrigatória (ex: GOOGLE_API_KEY) estiver ausente
        ou se algum valor for inválido.
    """
    _load_yaml_env_defaults()
    settings = Settings()
    logger.debug(
        "Configurações carregadas | env=%s | llm=%s | storage=%s",
        settings.app_env,
        settings.llm_model,
        settings.storage_backend,
    )
    return settings
