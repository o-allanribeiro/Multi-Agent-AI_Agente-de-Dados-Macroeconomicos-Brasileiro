# Guia de Contribuição

Obrigado pelo interesse em contribuir com o Agente de Dados Macroeconômicos Brasileiros!
Este guia descreve o processo para reportar problemas, sugerir melhorias e submeter código.

---

## Código de Conduta

Este projeto segue o princípio de contribuição respeitosa e colaborativa.
Trate todos os colaboradores com respeito. Discussões técnicas são bem-vindas;
ataques pessoais não serão tolerados.

---

## Como Reportar Problemas (Issues)

1. Verifique se o problema já foi reportado em [Issues](../../issues).
2. Se não existir, abra uma nova issue com:
   - **Título claro** descrevendo o problema.
   - **Descrição** com passos para reproduzir.
   - **Comportamento esperado** vs. **comportamento observado**.
   - **Ambiente**: OS, versão do Python, versão das dependências.
   - Logs relevantes (sem credenciais).

---

## Como Sugerir Funcionalidades

Abra uma issue com o label `enhancement` descrevendo:

- O problema que a funcionalidade resolve.
- A solução proposta.
- Alternativas consideradas.

---

## Processo de Contribuição de Código

### 1. Fork e Clone

```bash
git clone https://github.com/<seu-usuario>/<repo>.git
cd <repo>
```

### 2. Crie uma Branch Descritiva

```bash
git checkout -b feat/nova-fonte-ibge
# ou
git checkout -b fix/corrige-calculo-ipca
```

Convenções de nomenclatura:
- `feat/` — nova funcionalidade
- `fix/` — correção de bug
- `docs/` — documentação
- `refactor/` — refactoring sem mudança de comportamento
- `test/` — adição ou correção de testes
- `chore/` — ajustes de CI, dependências, config

### 3. Configure o Ambiente de Desenvolvimento

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\Activate.ps1

pip install -r requirements-dev.txt
pre-commit install
```

### 4. Implemente a Mudança

- Siga o padrão [PEP 8](https://peps.python.org/pep-0008/).
- Use type hints em funções e métodos públicos.
- Adicione testes para qualquer nova funcionalidade.
- Mantenha funções pequenas e com responsabilidade única.

### 5. Execute os Testes e Verificações

```bash
# Formata o código
make format

# Verifica qualidade
make lint

# Testes completos com cobertura
make test-cov
```

Cobertura mínima esperada: **70%** para novos módulos.

### 6. Commit com Mensagem Clara

Siga o padrão [Conventional Commits](https://www.conventionalcommits.org/pt-br/):

```
feat(tools): adiciona fonte de dados IBGE SIDRA

Implementa IBGEDataSource com suporte a séries da tabela 1737 (IPCA).
Registra automaticamente no ToolRegistry.

Closes #42
```

Tipos aceitos: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`.

### 7. Pull Request

1. Suba a branch para seu fork: `git push origin feat/nova-fonte-ibge`
2. Abra um PR no repositório principal.
3. Preencha o template de PR com:
   - Descrição do que foi feito.
   - Referência à issue relacionada.
   - Checklist de qualidade.

---

## Padrões de Código

### Python

- Formatação: [`black`](https://black.readthedocs.io/) (linha máx. 88 chars)
- Imports: [`isort`](https://pycqa.github.io/isort/) com perfil `black`
- Linting: [`flake8`](https://flake8.pycqa.org/)
- Type checking: [`mypy`](https://mypy.readthedocs.io/) (modo leniente por ora)
- Segurança: [`bandit`](https://bandit.readthedocs.io/) (nível medio/alto bloqueante)

### Testes

- Framework: `pytest`
- Mocks: `unittest.mock` (padrão da stdlib)
- Fixtures compartilhadas em `tests/conftest.py`
- Dados de teste em `tests/fixtures/mock_data.py`
- Separação: `tests/unit/` (sem I/O externo) e `tests/integration/` (permite I/O mockado)

### Novas Fontes de Dados

Para adicionar uma nova fonte de dados:

1. Crie `src/tools/<nome>.py` implementando `DataSource`:

```python
from tools.base import DataSource

class MinhaFonteDataSource(DataSource):
    source_name = "minha_fonte"

    def fetch(self, series_code: str, **kwargs) -> Optional[pd.DataFrame]:
        ...
```

2. Adicione a função de conveniência para o `ToolRegistry`.
3. Registre em `src/tools/registry.py`.
4. Adicione testes em `tests/unit/test_tools.py`.
5. Documente em `docs/ARQUITETURA.md`.

---

## Processo de Review

- PRs precisam de **ao menos 1 aprovação** de um mantenedor.
- CI deve passar (testes + lint + security scan).
- Conflitos com `main` devem ser resolvidos antes do merge.
- Squash merge preferido para histórico limpo.

---

## Dúvidas

Abra uma issue com o label `question` ou inicie uma discussão em [Discussions](../../discussions).
