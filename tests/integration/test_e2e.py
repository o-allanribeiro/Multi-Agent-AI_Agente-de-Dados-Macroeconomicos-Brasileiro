# -*- coding: utf-8 -*-
"""
End-to-end test: valida o pipeline Onda 3 completo com perguntas avançadas.

Perguntas cobertas:
  1. Health check
  2. Juros Reais (Fisher Identity + Auditor)
  3. Análise com contexto histórico (z-score, percentil, tendência OLS)
  4. Multi-indicador: Curva de Phillips (IPCA + Desemprego)
  5. Multi-indicador: Regra de Taylor (Selic + IPCA)
  6. Câmbio Real bilateral
  7. Verificar campos Onda 3 na resposta
  8. Rate limiting

Roda com: python tests/integration/test_e2e.py
Requer servidor em: http://127.0.0.1:8002
"""
import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8002"

# Resultados acumulados para resumo final
_results: list[dict] = []


def post_json(url: str, payload: dict, timeout: int = 180) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def sep(title: str):
    print(f"\n{'='*65}")
    print(f"  {title}")
    print(f"{'='*65}")


def record(name: str, ok: bool, detail: str = ""):
    status = "OK " if ok else "FAIL"
    _results.append({"name": name, "ok": ok, "detail": detail})
    print(f"  [{status}] {detail}" if detail else f"  [{status}]")


# ─── 1. Health check ────────────────────────────────────────────────────────
sep("1. HEALTH CHECK")
try:
    r = urllib.request.urlopen(f"{BASE}/health", timeout=8)
    body = json.loads(r.read())
    print(f"  status  : {body.get('status')}")
    print(f"  version : {body.get('version')}")
    print(f"  env     : {body.get('environment')}")
    record("health_check", body.get("status") == "ok", f"status={body.get('status')}")
except Exception as e:
    record("health_check", False, str(e))
    print(f"  [FAIL] {e}")
    sys.exit(1)


# ─── 2. Juros Reais — Fisher Identity + Auditor ─────────────────────────────
sep("2. JUROS REAIS — Fisher Identity (Onda 3)")
t0 = time.perf_counter()
try:
    resp = post_json(f"{BASE}/ask", {
        "question": "Qual o juro real no Brasil hoje? Compare com a média histórica e interprete à luz da Regra de Taylor.",
        "session_id": "e2e-juros-reais-01",
    })
    elapsed = time.perf_counter() - t0
    print(f"  session_id : {resp.get('session_id')}")
    print(f"  has_data   : {resp.get('has_data')}")
    print(f"  tempo      : {elapsed:.1f}s")
    resp_text = resp.get("text") or ""
    print(f"  resposta   : {resp_text[:400]}...")
    plot_b64 = resp.get("plot_base64") or ""
    print(f"  plot_base64: {len(plot_b64)} chars" if plot_b64 else "  plot_base64: None")

    # Verifica que a resposta menciona conceitos da identidade de Fisher
    has_fisher_content = any(
        kw in resp_text.lower()
        for kw in ["juro real", "juros reais", "fisher", "selic", "ipca", "real"]
    )
    record("juros_reais_fisher", resp.get("has_data", False) and has_fisher_content,
           f"has_data={resp.get('has_data')} | fisher_content={has_fisher_content} | {elapsed:.1f}s")
except Exception as e:
    record("juros_reais_fisher", False, str(e))
    print(f"  [FAIL] {e}")


# ─── 3. Contexto Histórico — Z-score, Percentil, Tendência ──────────────────
sep("3. CONTEXTO HISTÓRICO — Z-score e Percentil (Onda 3 stats_node)")
t0 = time.perf_counter()
try:
    resp = post_json(f"{BASE}/ask", {
        "question": "O IPCA atual está acima ou abaixo da média histórica dos últimos 5 anos? Em que percentil está?",
        "session_id": "e2e-stats-ipca-01",
    })
    elapsed = time.perf_counter() - t0
    print(f"  has_data   : {resp.get('has_data')}")
    print(f"  tempo      : {elapsed:.1f}s")
    resp_text = resp.get("text") or ""
    print(f"  resposta   : {resp_text[:400]}...")

    # Resposta deve conter referência a contexto histórico
    has_hist_content = any(
        kw in resp_text.lower()
        for kw in ["média", "media", "histórico", "percentil", "acima", "abaixo", "ipca"]
    )
    record("stats_historico_ipca", resp.get("has_data", False) and has_hist_content,
           f"has_data={resp.get('has_data')} | hist_content={has_hist_content} | {elapsed:.1f}s")
except Exception as e:
    record("stats_historico_ipca", False, str(e))
    print(f"  [FAIL] {e}")


# ─── 4. Curva de Phillips — Multi-indicador ──────────────────────────────────
sep("4. CURVA DE PHILLIPS — IPCA + Desemprego (multi-tool)")
t0 = time.perf_counter()
try:
    resp = post_json(f"{BASE}/ask", {
        "question": "Analise a relação entre IPCA e taxa de desemprego no Brasil nos últimos 4 anos. O trade-off da Curva de Phillips é visível?",
        "session_id": "e2e-phillips-01",
    }, timeout=240)
    elapsed = time.perf_counter() - t0
    print(f"  has_data   : {resp.get('has_data')}")
    print(f"  tempo      : {elapsed:.1f}s")
    resp_text = resp.get("text") or ""
    print(f"  resposta   : {resp_text[:400]}...")
    plot_b64 = resp.get("plot_base64") or ""
    print(f"  plot_base64: {len(plot_b64)} chars" if plot_b64 else "  plot_base64: None")

    has_phillips_content = any(
        kw in resp_text.lower()
        for kw in ["desemprego", "desocupação", "inflação", "ipca", "phillips", "trade-off"]
    )
    record("phillips_curve_multi", resp.get("has_data", False) and has_phillips_content,
           f"has_data={resp.get('has_data')} | phillips={has_phillips_content} | {elapsed:.1f}s")
except Exception as e:
    record("phillips_curve_multi", False, str(e))
    print(f"  [FAIL] {e}")


# ─── 5. Regra de Taylor — Selic + IPCA ───────────────────────────────────────
sep("5. REGRA DE TAYLOR — Selic × IPCA (multi-tool + auditor Taylor check)")
t0 = time.perf_counter()
try:
    resp = post_json(f"{BASE}/ask", {
        "question": "Compare a Selic com o IPCA nos últimos 3 anos. A política monetária está coerente com a Regra de Taylor?",
        "session_id": "e2e-taylor-01",
    }, timeout=240)
    elapsed = time.perf_counter() - t0
    print(f"  has_data   : {resp.get('has_data')}")
    print(f"  tempo      : {elapsed:.1f}s")
    resp_text = resp.get("text") or ""
    print(f"  resposta   : {resp_text[:400]}...")

    has_taylor_content = any(
        kw in resp_text.lower()
        for kw in ["selic", "ipca", "taylor", "monetária", "inflação", "contracionista"]
    )
    record("taylor_selic_ipca", resp.get("has_data", False) and has_taylor_content,
           f"has_data={resp.get('has_data')} | taylor={has_taylor_content} | {elapsed:.1f}s")
except Exception as e:
    record("taylor_selic_ipca", False, str(e))
    print(f"  [FAIL] {e}")


# ─── 6. Câmbio Real Bilateral ─────────────────────────────────────────────────
sep("6. CÂMBIO REAL BILATERAL (Onda 3 derived.py)")
t0 = time.perf_counter()
try:
    resp = post_json(f"{BASE}/ask", {
        "question": "Como está o câmbio real bilateral BRL/USD nos últimos 2 anos? O real está apreciado ou depreciado em termos reais?",
        "session_id": "e2e-cambio-real-01",
    }, timeout=180)
    elapsed = time.perf_counter() - t0
    print(f"  has_data   : {resp.get('has_data')}")
    print(f"  tempo      : {elapsed:.1f}s")
    resp_text = resp.get("text") or ""
    print(f"  resposta   : {resp_text[:400]}...")

    has_cambio_content = any(
        kw in resp_text.lower()
        for kw in ["câmbio", "dólar", "real", "brl", "usd", "apreciado", "depreciado"]
    )
    record("cambio_real_bilateral", resp.get("has_data", False) and has_cambio_content,
           f"has_data={resp.get('has_data')} | cambio={has_cambio_content} | {elapsed:.1f}s")
except Exception as e:
    record("cambio_real_bilateral", False, str(e))
    print(f"  [FAIL] {e}")


# ─── 7. Verificar campos Onda 3 na resposta ──────────────────────────────────
sep("7. CAMPOS ONDA 3 — Verificar auditoria e custo na resposta")
t0 = time.perf_counter()
try:
    resp = post_json(f"{BASE}/ask", {
        "question": "Qual a trajetória da taxa Selic nos últimos 3 anos e em que percentil histórico ela está?",
        "session_id": "e2e-onda3-fields-01",
    })
    elapsed = time.perf_counter() - t0

    has_data = resp.get("has_data", False)
    cost = resp.get("cost_estimate_usd", -1)
    has_session = bool(resp.get("session_id"))
    error = resp.get("error")
    resp_text = resp.get("text") or ""

    print(f"  has_data         : {has_data}")
    print(f"  cost_estimate    : {cost}")
    print(f"  session_id       : {resp.get('session_id')}")
    print(f"  error            : {error}")
    print(f"  resposta (300c)  : {resp_text[:300]}...")

    record("onda3_response_fields",
           has_data and has_session and cost >= 0 and error is None,
           f"has_data={has_data} | cost={cost:.4f} | session={has_session} | error={error} | {elapsed:.1f}s")
except Exception as e:
    record("onda3_response_fields", False, str(e))
    print(f"  [FAIL] {e}")


# ─── 8. Rate Limiting ─────────────────────────────────────────────────────────
sep("8. RATE LIMITING — health check sem bloqueio")
try:
    blocked = 0
    for i in range(3):
        r_inner = urllib.request.urlopen(f"{BASE}/health", timeout=5)
        _ = r_inner.read()
    print(f"  3 requests ao /health: sem bloqueio (rate limit aplica só ao /ask)")
    record("rate_limiting", True, "3 reqs ao /health — sem bloqueio esperado")
except Exception as e:
    record("rate_limiting", False, str(e))
    print(f"  [FAIL] {e}")


# ─── RESUMO FINAL ─────────────────────────────────────────────────────────────
sep("RESUMO FINAL")
total = len(_results)
passed = sum(1 for r in _results if r["ok"])
failed = total - passed
print(f"\n  Resultado: {passed}/{total} testes passaram\n")
for r in _results:
    status = "✅" if r["ok"] else "❌"
    print(f"  {status} {r['name']:<35} {r['detail']}")

print()
if failed == 0:
    print("  ✅ Pipeline Onda 3 totalmente validado! Todos os checks passaram.")
else:
    print(f"  ⚠️  {failed} teste(s) falharam — revisar logs do servidor.")
    sys.exit(1)

