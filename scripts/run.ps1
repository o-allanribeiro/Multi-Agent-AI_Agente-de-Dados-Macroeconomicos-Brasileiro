# =============================================================================
# scripts/run.ps1 — Atalhos para Windows (PowerShell)
# Projeto: Agente Macro-BR
#
# USO: .\scripts\run.ps1 -Command <comando>
# =============================================================================

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        "install", "install-dev", "install-aws",
        "run", "run-dev", "cli",
        "test", "test-unit", "lint", "format",
        "docker-up", "docker-down", "docker-logs",
        "clean"
    )]
    [string]$Command
)

$env:PYTHONPATH = "src"
$ComposeFile = "deployment/docker-compose.yml"

switch ($Command) {
    "install"     { pip install -r requirements.txt }
    "install-dev" { pip install -r requirements-dev.txt }
    "install-aws" { pip install -r requirements-aws.txt }

    "run" {
        uvicorn main:app --host 0.0.0.0 --port 8000
    }
    "run-dev" {
        $env:APP_ENV = "development"
        $env:LOG_FORMAT = "text"
        uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    }
    "cli" {
        python src/cli.py
    }

    "test"      { pytest tests/ -v }
    "test-unit" { pytest tests/unit/ -v }

    "lint" {
        flake8 src/ tests/ --max-line-length=100 --exclude=__pycache__,venv
    }
    "format" {
        black src/ tests/
        isort src/ tests/
    }

    "docker-up"   { docker-compose -f $ComposeFile up --build -d }
    "docker-down" { docker-compose -f $ComposeFile down }
    "docker-logs" { docker-compose -f $ComposeFile logs -f }

    "clean" {
        Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
        Get-ChildItem -Recurse -Directory -Filter ".pytest_cache" | Remove-Item -Recurse -Force
        Get-ChildItem -Recurse -Directory -Filter ".mypy_cache" | Remove-Item -Recurse -Force
        Get-ChildItem -Recurse -Directory -Filter "htmlcov" | Remove-Item -Recurse -Force
        Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force
        Remove-Item -Path ".coverage" -ErrorAction SilentlyContinue
        Write-Host "Limpeza concluída." -ForegroundColor Green
    }
}
