# Resultados dos Testes — Onda 3

> Executado em: 2026-03-10  
> Versão: commit pós-Onda 3 (`3c6d827` + fix câmbio real)  
> Python: 3.13.2 | LangGraph | Gemini 2.5 Flash | FastAPI

---

## 1. Testes Unitários

**Resultado: 67/67 passaram** — cobertura 69% (linhas relevantes: 92–96%)

### Execução

```powershell
$env:PYTHONPATH = "src"
$env:STORAGE_BACKEND = "sqlite"
$env:APP_ENV = "testing"
$env:GOOGLE_API_KEY = "test-key-mock"
$env:LOG_LEVEL = "ERROR"
.\venv\Scripts\python.exe -m pytest tests/unit/ -v --tb=short
# 67 passed in 18.89s
```

### Cobertura por módulo (destaques)

| Módulo                        | Cobertura | Notas                           |
|-------------------------------|----------:|--------------------------------|
| `nodes/auditor.py`            | 96 %      | 9 casos: defasagem, outlier, Fisher, Taylor |
| `nodes/stats.py`              | 96 %      | 8 casos: z-score, tendência, percentil, médias |
| `tools/derived.py`            | 92 %      | 17 casos: Fisher, câmbio real, keywords |
| `api/schemas.py`              | 100 %     | Contratos de API validados      |
| `tools/bcb.py`                | 92 %      | BCB + cache bypass              |
| `tools/ipea.py`               | 90 %      | IPEA + cache bypass             |

### Novos testes adicionados (Onda 3 — 34 métodos)

#### `TestStatsNode` (8 testes)

| Teste | Verifica |
|-------|---------|
| `test_computes_zscore_for_clear_outlier` | Z-score > 3.0 para valor 25 em série de média 10 |
| `test_trend_direction_alta` | Tendência "alta" quando últimos 3 meses crescem |
| `test_trend_direction_baixa` | Tendência "baixa" quando últimos 3 meses caem |
| `test_percentile_rank_at_max_value` | Valor máximo → percentil > 95 |
| `test_stats_returns_empty_on_no_data` | df=None → campos históricos vazios |
| `test_stats_text_contains_zscore_label` | Texto de saída contém "Z-score" |
| `test_detects_juros_reais_and_applies_fisher` | Pergunta "juro real" → `derived_data["juros_reais"]` não vazio |
| `test_mean_1y_3y_5y_are_populated` | Série de 72 pontos → médias 1a/3a/5a preenchidas |

#### `TestAuditorNode` (9 testes)

| Teste | Verifica |
|-------|---------|
| `test_no_flags_when_no_data` | Sem dados históricos → sem flags |
| `test_flag_stale_data_critical` | Defasagem 500 dias → flag "CRÍTICO" |
| `test_flag_stale_data_warning` | Defasagem 120 dias → flag "DEFASADO" (não crítico) |
| `test_flag_outlier_zscore_high` | Z-score 3.8 → flag "OUTLIER" |
| `test_flag_juros_reais_extreme_high` | Juro real 22% → flag "EXTREMOS" |
| `test_flag_juros_reais_negative` | Juro real −5% → flag "NEGATIVOS" |
| `test_flag_juros_reais_normal_range_produces_info_flag` | Juro real 7% → flag informativo, sem EXTREMOS |
| `test_multiple_flags_counted_in_summary` | Lag 400d + Z 4.5 → ≥ 2 flags no resumo |
| `test_taylor_flag_when_selic_high_and_ipca_rising` | Selic 13.75 + IPCA em alta → flag "TENSÃO" |

#### `TestDerivedTools` (17 testes)

| Teste | Verifica |
|-------|---------|
| `test_juros_reais_fisher_math` | (1.12 / 1.005^12) − 1 ≈ 5.49 % (tolerância ±0.5 pp) |
| `test_juros_reais_positive_with_selic_high` | Selic 13.75 → juro real positivo |
| `test_juros_reais_output_datetime_index` | Índice da saída é DatetimeIndex |
| `test_juros_reais_returns_none_without_selic` | Sem coluna Selic → None |
| `test_juros_reais_returns_none_without_ipca` | Sem coluna IPCA → None |
| `test_juros_reais_works_with_named_columns` | Colunas "selic"/"ipca" reconhecidas |
| `test_cambio_real_starts_at_base_100` | Primeiro ponto = 100.0 |
| `test_cambio_real_preserves_nominal_column` | Coluna "cambio_nominal" presente |
| `test_cambio_real_returns_none_without_cambio` | Sem coluna câmbio → None |
| `test_detect_keywords_juros_reais` | "juro real", "taxa real", "selic real" → "juros_reais" |
| `test_detect_keywords_cambio_real` | "câmbio real", "poder de compra do real" → "cambio_real" |
| `test_detect_keywords_no_match` | Pergunta genérica → lista vazia |
| `test_detect_keywords_both` | Pergunta com ambos → ["juros_reais", "cambio_real"] |
| `test_apply_derived_returns_dataframe` | Dispatcher retorna DataFrame |
| `test_apply_derived_empty_list` | Lista vazia → dict vazio |
| `test_apply_derived_unknown_name` | Nome desconhecido → ignorado silenciosamente |

---

## 2. Testes de Integração (E2E)

**Resultado: 8/8 passaram**

### Execução

```powershell
# Servidor rodando em segundo plano na porta 8002
$env:PYTHONPATH = "src"
.\venv\Scripts\python.exe tests/integration/test_e2e.py
# 8/8 testes passaram
```

### Resultados por cenário

| # | Cenário | Status | Tempo | Observação |
|---|---------|--------|------:|-----------|
| 1 | Health Check | ✅ | — | `status=ok`, `version=0.1.0` |
| 2 | Juros Reais — Identidade de Fisher | ✅ | 56.1s | `has_data=True`, conteúdo Fisher detectado |
| 3 | Contexto Histórico IPCA (z-score/percentil) | ✅ | 27.9s | Percentil 35.6 %, média histórica calculada |
| 4 | Curva de Phillips (IPCA + Desemprego) | ✅ | 36.9s | Multi-tool: IBGE + BCB, gráfico gerado |
| 5 | Regra de Taylor (Selic × IPCA) | ✅ | 42.9s | Auditor sem flags, análise restritiva |
| 6 | Câmbio Real Bilateral BRL/USD | ✅ | 47.7s | Correção de alinhamento diário→mensal aplicada |
| 7 | Campos Onda 3 (custo, session_id, audit) | ✅ | 32.2s | `cost=0.0007 USD`, `error=None` |
| 8 | Rate Limiting (health sem bloqueio) | ✅ | — | 3 reqs ao `/health` sem throttle |

### Exemplos de respostas geradas

**Juros Reais (Fisher, 56 s):**
> "Com base nas projeções de uma Taxa Selic de **15,0% ao ano** e uma inflação anualizada de **4,04%**, o juro real *ex-ante* projetado para 2026 alcança **10,54% ao ano**. Este patamar é extremamente elevado…"

**IPCA Histórico (27.9 s):**
> "O IPCA registrado em janeiro de 2026 foi de **0,33%**. Este valor se encontra **abaixo da média histórica** dos últimos cinco anos (0,4739%). O IPCA atual está no **percentil 35,6%** do histórico…"

**Câmbio Real (47.7 s):**
> "A análise é **severamente comprometida pela defasagem crítica dos dados de inflação doméstica (IPCA)**. O último dado disponível para o IPCA é de dezembro de 2023, com uma defasagem de 830 dias…" *(auditor detectou e reportou a limitação)*

---

## 3. Bugs Encontrados e Corrigidos

### Bug 1 — `compute_cambio_real`: IndexError em DataFrame vazio

**Sintoma:** Requisição de câmbio real retornava HTTP 500.

**Causa raiz:** BCB série 1 (Dólar) retorna frequência diária (504 obs./2 anos); BCB série 433 (IPCA) retorna frequência mensal (24 obs./2 anos). O `pd.concat(..., axis=1).dropna()` combinava os dois sem alinhar datas → resultado com 0 linhas → `price_index.iloc[0]` lançava `IndexError`.

**Correção** em `src/tools/derived.py` → `compute_cambio_real`:
```python
# Antes (quebrava com datas desalinhadas)
result = result.sort_index().dropna()

# Depois (reamostrar ambos para mensal antes de combinar)
cambio_monthly = result[cambio_col].resample("MS").mean()
ipca_monthly   = result[ipca_col].resample("MS").mean()
result = pd.concat([cambio_monthly, ipca_monthly], axis=1).dropna()

if result.empty:
    logger.warning("Câmbio real: DataFrame vazio após alinhamento de frequências")
    return None
```

**Impacto:** Câmbio mensal médio + IPCA mensal → ~24 pontos alinhados → cálculo correto do índice real.

### Bug 2 — Testes unitários falhavam por cache SQLite compartilhado

**Sintoma:** Testes retornavam dados reais ao invés de mocks quando o arquivo `output/series_cache.db` existia.

**Correção** em `tests/conftest.py` — fixture `bypass_series_cache` com `monkeypatch.setattr` em todos os 4 módulos de tools.

---

## 4. Infraestrutura de Testes

### Fixtures principais (`tests/conftest.py`)

| Fixture | Escopo | Propósito |
|---------|--------|-----------|
| `mock_agent_state` | function | Estado LangGraph com todos os campos Onda 3 |
| `sample_selic_df` | session | 72 pontos mensais de Selic (~432) |
| `sample_ipca_df` | session | 72 pontos mensais de IPCA (~433) |
| `sample_combined_df` | session | Merge Selic + IPCA para testes de derivados |
| `bypass_series_cache` | function (autouse) | Patches `get_series_cache` em todos os tools |

### Isolamento de cache

O `bypass_series_cache` fixture é **autouse** (aplicado automaticamente a todos os testes unitários):
```python
@pytest.fixture(autouse=True, scope="function")
def bypass_series_cache(monkeypatch):
    noop = lambda: MagicMock(get=lambda *a, **kw: (None, False))
    monkeypatch.setattr(_bcb,  "get_series_cache", noop)
    monkeypatch.setattr(_ipea, "get_series_cache", noop)
    monkeypatch.setattr(_ibge, "get_series_cache", noop)
    monkeypatch.setattr(_wb,   "get_series_cache", noop)
```

---

## 5. Métricas de Qualidade

| Métrica | Valor |
|---------|-------|
| Testes unitários | 67/67 passaram |
| Cobertura total | 69 % |
| Testes E2E | 8/8 passaram |
| Tempo médio de resposta E2E | ~41 s |
| Custo estimado por query | ~$0.0007 USD |
| Bugs críticos corrigidos | 2 |
| Novos testes Onda 3 | 34 |
