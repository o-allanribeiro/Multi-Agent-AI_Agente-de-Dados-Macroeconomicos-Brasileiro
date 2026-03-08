# Guia de Instalação e Execução

## Requisitos

| Dependência | Versão mínima | Verificação |
|---|---|---|
| Python | 3.11 | `python --version` |
| pip | 23+ | `pip --version` |
| Docker | 24+ (opcional) | `docker --version` |
| docker compose | v2+ (opcional) | `docker compose version` |

---

## 1. Configuração do Ambiente Local

### 1.1 Clone o repositório

```bash
git clone <url-do-repositorio>
cd "PROJETO MULTI AGENTE-  Agente de Dados Macroeconômicos Brasileiros"
```

### 1.2 Crie e ative o ambiente virtual

```bash
# Linux / macOS
python -m venv .venv
source .venv/bin/activate

# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 1.3 Instale as dependências

```bash
# Produção
pip install -r requirements.txt

# Desenvolvimento (inclui pytest, black, mypy, etc.)
pip install -r requirements-dev.txt

# AWS (DynamoDB, boto3 — opcional para dev local)
pip install -r requirements-aws.txt
```

### 1.4 Configure as variáveis de ambiente

```bash
# Copie o arquivo de exemplo
cp .env.example .env
```

Edite `.env` e preencha ao menos:

```dotenv
GOOGLE_API_KEY=sua_chave_aqui
APP_ENV=development
```

> Obtenha a chave em [Google AI Studio](https://aistudio.google.com/app/apikey).

---

## 2. Execução Local

### 2.1 Servidor da API (modo desenvolvimento)

#### Linux / macOS / WSL

```bash
PYTHONPATH=src uvicorn asgi:app --reload --port 8000
```

#### Windows PowerShell

```powershell
$env:PYTHONPATH="src"
uvicorn asgi:app --reload --port 8000
```

#### Via Makefile (Linux/macOS)

```bash
make run-dev
```

#### Via script PowerShell

```powershell
.\scripts\run.ps1 run
```

Acesse:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Frontend: abra `index.html` no navegador

### 2.2 CLI Interativo

```bash
# Linux / macOS
PYTHONPATH=src python src/cli.py

# Windows PowerShell
$env:PYTHONPATH="src"
python src/cli.py
```

---

## 3. Execução com Docker

### 3.1 Build e start

```bash
cd deployment
docker compose up --build
```

### 3.2 Apenas a API (sem rebuild)

```bash
docker compose up api
```

### 3.3 Rodar os testes no container

```bash
docker compose --profile test up tests
```

---

## 4. Testes

### 4.1 Todos os testes

```bash
# Linux / macOS
PYTHONPATH=src pytest tests/ -v

# Windows PowerShell
$env:PYTHONPATH="src"; pytest tests/ -v
```

### 4.2 Apenas testes unitários

```bash
pytest tests/unit/ -v
```

### 4.3 Com cobertura de código

```bash
pytest tests/ --cov=src --cov-report=html
# Abra htmlcov/index.html no navegador
```

### 4.4 Via Makefile

```bash
make test           # todos os testes
make test-unit      # apenas unitários
make test-cov       # com relatório de cobertura
```

---

## 5. Qualidade de Código

```bash
# Formata o código automaticamente
make format
# equivalente a: black src/ tests/ && isort src/ tests/

# Verifica sem modificar
make lint
# equivalente a: black --check && isort --check && flake8

# Type check
make type-check
# equivalente a: mypy src/
```

---

## 6. Configuração por Ambiente

| Arquivo | Ambiente | `APP_ENV` |
|---|---|---|
| `config/default.yaml` | Base (sempre carregado) | — |
| `config/development.yaml` | Dev local | `development` |
| `config/production.yaml` | Produção | `production` |
| `config/aws.yaml` | Parâmetros AWS | qualquer |

Para executar em modo produção localmente:

```bash
APP_ENV=production PYTHONPATH=src uvicorn asgi:app --port 8000
```

---

## 7. Estrutura do `.env`

Consulte `.env.example` para a lista completa de variáveis. As essenciais são:

```dotenv
# Obrigatório
GOOGLE_API_KEY=

# Opcional — padrões sensatos já definidos em config/default.yaml
APP_ENV=development
LLM_MODEL=gemini-2.5-flash
API_PORT=8000
LOG_LEVEL=INFO
```

---

## 8. Solução de Problemas Comuns

### `ModuleNotFoundError: No module named 'agente'`

Causa: `PYTHONPATH` não configurado.

```bash
# Certifique-se de exportar/definir antes de executar
export PYTHONPATH=src   # Linux/macOS
$env:PYTHONPATH="src"   # Windows PowerShell
```

### `pydantic_settings` não encontrado

```bash
pip install pydantic-settings
```

### `yaml` não encontrado

```bash
pip install pyyaml
```

### Erro ao importar `boto3` (sem AWS configurado)

O `StorageBackend` usa SQLite por padrão em `development`/`testing`.
`DynamoDBBackend` é instanciado apenas quando `APP_ENV=production` e `USE_DYNAMODB=true`.
Você **não** precisa do boto3 para rodar localmente.

### Gráfico não gerado

Verifique se o diretório `output/` existe e tem permissão de escrita:

```bash
mkdir -p output
```
