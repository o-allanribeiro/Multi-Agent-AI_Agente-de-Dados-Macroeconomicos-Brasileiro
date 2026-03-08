# Changelog

Todas as alterações notáveis deste projeto são documentadas aqui.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e o projeto segue [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [Não lançado]

### Adicionado
- Módulo IBGE SIDRA (stub — Fase D)
- Backend DynamoDB para produção AWS
- Endpoint `POST /ask` com validação Pydantic
- CLI interativo `src/cli.py`
- Logging estruturado JSON (CloudWatch-ready)
- Cobertura de testes unitários e de integração

---

## [0.2.0] — 2024 (Evolução C1–C8)

### Adicionado
- `src/agente/config.py`: configuração centralizada via `pydantic-settings`
- `config/*.yaml`: arquivos YAML por ambiente (default, development, production, aws)
- `src/agente/nodes/`: nós LangGraph extraídos para módulos individuais
  - `planner.py`, `action.py`, `analysis.py`, `plot.py`, `response.py`
- `src/tools/base.py`: ABC `DataSource` para contrato unificado de ferramentas
- `src/tools/registry.py`: `ToolRegistry` com registro dinâmico e descrição para LLM
- `src/storage/`: abstração de persistência (SQLite dev / DynamoDB prod)
- `src/logger/config.py`: formatadores JSON e texto com supressão de loggers ruidosos
- `src/api/`: FastAPI modularizado (`server.py`, `routes.py`, `legacy.py`, `schemas.py`)
- `src/asgi.py`: ponto de entrada ASGI para uvicorn
- `pyproject.toml`: metadados do projeto e configuração de ferramentas de qualidade
- `Makefile` + `scripts/run.ps1`: atalhos de desenvolvimento
- `deployment/docker/`: Dockerfile multi-stage, Dockerfile.test, .dockerignore
- `deployment/docker-compose.yml` + `docker-compose.prod.yml`
- `.github/workflows/tests.yml`: CI (lint, mypy, testes unitários + integração, Docker build)
- `.github/workflows/code-quality.yml`: bandit, pip-audit, pre-commit
- `tests/`: conftest, fixtures, test_nodes, test_tools, test_api, integração
- `docs/ARQUITETURA.md`: diagrama completo + descrição dos componentes
- `docs/GUIA_INSTALACAO.md`: passo a passo detalhado de instalação local e Docker
- `CONTRIBUTING.md`: guia de contribuição

### Modificado
- `requirements.txt`: adicionados `pydantic>=2.7.0`, `pydantic-settings>=2.2.0`, `pyyaml>=6.0.1`
- `.gitignore`: expandido com padrões de `.env`, `output/`, `logs/`, `.venv/`
- `src/main.py`: atualizado para usar `run_agent()` da nova estrutura modular

### Corrigido
- Race condition em gráficos: plots nomeados como `chart_{session_id}.png`
- Inicialização do LLM movida para dentro das funções de nó (testabilidade)
- Importações organizadas via `isort` (PEP 8)

---

## [0.1.0] — 2024 (MVP 0)

### Adicionado
- Agente LangGraph com 5 nós: Planner → Action → Analysis → Plot → Response
- Ferramentas de dados: BCB (SGS), IPEADATA, World Bank
- API FastAPI com endpoint `POST /ask-agent`
- Frontend `index.html` com interface de chat
- CLI básico `src/main.py`
- Configuração via `.env` (Google API Key)
