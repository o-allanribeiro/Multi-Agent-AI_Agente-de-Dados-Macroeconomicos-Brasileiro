# =============================================================================
# Makefile — Agente Macro-BR
# Atalhos para operações comuns de desenvolvimento, testes e deployment.
#
# USO:
#   Linux / macOS / WSL / Git Bash:  make <comando>
#   Windows (PowerShell nativo):      use scripts/run.ps1 (ver pasta scripts/)
#
# REQUER: make instalado
#   Windows via Chocolatey:  choco install make
#   Windows via Scoop:       scoop install make
# =============================================================================

.PHONY: help install install-dev install-aws \
        test test-unit test-integration test-cov \
        lint format type-check quality \
        run run-dev \
        docker-up docker-down docker-build docker-logs docker-clean \
        clean

# Variáveis configuráveis
PYTHONPATH_CMD := PYTHONPATH=src
API_HOST       := 0.0.0.0
API_PORT       := 8000
COMPOSE_FILE   := deployment/docker-compose.yml
COMPOSE_PROD   := deployment/docker-compose.prod.yml

# =============================================================================
# Ajuda
# =============================================================================
help:  ## Exibe esta mensagem de ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Instalação de Dependências
# =============================================================================
install:  ## Instala dependências de produção
	pip install -r requirements.txt

install-dev:  ## Instala dependências de desenvolvimento e testes
	pip install -r requirements-dev.txt

install-aws:  ## Instala dependências de produção + AWS
	pip install -r requirements-aws.txt

# =============================================================================
# Testes
# =============================================================================
test:  ## Executa todos os testes com cobertura
	$(PYTHONPATH_CMD) pytest tests/ -v

test-unit:  ## Executa apenas testes unitários
	$(PYTHONPATH_CMD) pytest tests/unit/ -v

test-integration:  ## Executa apenas testes de integração
	$(PYTHONPATH_CMD) pytest tests/integration/ -v

test-cov:  ## Executa testes e abre relatório de cobertura HTML
	$(PYTHONPATH_CMD) pytest tests/ -v
	open htmlcov/index.html || start htmlcov/index.html || xdg-open htmlcov/index.html

# =============================================================================
# Qualidade de Código
# =============================================================================
lint:  ## Verifica estilo de código com flake8
	$(PYTHONPATH_CMD) flake8 src/ tests/ --max-line-length=100 --exclude=__pycache__,venv

format:  ## Formata código com black + isort
	$(PYTHONPATH_CMD) black src/ tests/
	$(PYTHONPATH_CMD) isort src/ tests/

type-check:  ## Verifica tipos estáticos com mypy
	$(PYTHONPATH_CMD) mypy src/ --config-file=pyproject.toml

quality: lint type-check  ## Executa lint + verificação de tipos

# =============================================================================
# Execução Local
# =============================================================================
run:  ## Inicia o servidor API (produção local)
	$(PYTHONPATH_CMD) uvicorn main:app \
		--host $(API_HOST) \
		--port $(API_PORT) \
		--workers 1

run-dev:  ## Inicia o servidor API com hot-reload (desenvolvimento)
	APP_ENV=development LOG_FORMAT=text \
	$(PYTHONPATH_CMD) uvicorn main:app \
		--host $(API_HOST) \
		--port $(API_PORT) \
		--reload

cli:  ## Inicia a interface CLI interativa
	$(PYTHONPATH_CMD) python src/cli.py

# =============================================================================
# Docker
# =============================================================================
docker-build:  ## Constrói as imagens Docker
	docker-compose -f $(COMPOSE_FILE) build

docker-up:  ## Inicia todos os serviços (detached)
	docker-compose -f $(COMPOSE_FILE) up --build -d

docker-down:  ## Para e remove containers
	docker-compose -f $(COMPOSE_FILE) down

docker-logs:  ## Exibe logs dos containers em tempo real
	docker-compose -f $(COMPOSE_FILE) logs -f

docker-prod:  ## Inicia ambiente de produção (requer .env configurado)
	docker-compose -f $(COMPOSE_PROD) up --build -d

docker-clean:  ## Remove containers, imagens e volumes
	docker-compose -f $(COMPOSE_FILE) down --volumes --rmi all

# =============================================================================
# Limpeza
# =============================================================================
clean:  ## Remove arquivos temporários e cache
	find . -type d -name "__pycache__" -not -path "./venv/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -not -path "./venv/*" -delete 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	@echo "Limpeza concluída."
