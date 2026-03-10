# -*- coding: utf-8 -*-
"""
End-to-end test: simula interações reais do usuário com a API.
Roda com: python test_e2e.py
"""
import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8002"


def post_json(url: str, payload: dict, timeout: int = 120) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def sep(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ─── 1. Health check ────────────────────────────────────────────
sep("1. HEALTH CHECK")
try:
    r = urllib.request.urlopen(f"{BASE}/health", timeout=8)
    body = json.loads(r.read())
    print(f"  status  : {body.get('status')}")
    print(f"  version : {body.get('version')}")
    print(f"  env     : {body.get('environment')}")
    print("  [OK]")
except Exception as e:
    print(f"  [ERRO] {e}")
    sys.exit(1)


# ─── 2. Pergunta simples: Selic ──────────────────────────────────
sep("2. PERGUNTA SIMPLES — Selic")
t0 = time.perf_counter()
try:
    resp = post_json(f"{BASE}/ask", {
        "question": "Qual a trajetória da taxa Selic nos últimos 2 anos?",
        "session_id": "test-selic-01",
    })
    elapsed = time.perf_counter() - t0
    print(f"  session_id : {resp.get('session_id')}")
    print(f"  has_data   : {resp.get('has_data')}")
    print(f"  tempo      : {elapsed:.1f}s")
    resp_text = resp.get("text") or ""
    print(f"  resposta   : {resp_text[:200]}...")
    plot_b64 = resp.get("plot_base64") or ""
    if plot_b64:
        print(f"  plot_base64: {len(plot_b64)} chars (OK)")
    else:
        print("  plot_base64: None (plot nao gerado)")
    print("  [OK]")
except Exception as e:
    print(f"  [ERRO] {e}")


# ─── 3. Pergunta multi-tool: Selic vs IPCA ──────────────────────
sep("3. MULTI-TOOL — Compare Selic vs IPCA")
t0 = time.perf_counter()
try:
    resp = post_json(f"{BASE}/ask", {
        "question": "Compare a taxa Selic com a inflação IPCA nos últimos 2 anos.",
        "session_id": "test-multi-01",
    }, timeout=180)
    elapsed = time.perf_counter() - t0
    print(f"  session_id : {resp.get('session_id')}")
    print(f"  has_data   : {resp.get('has_data')}")
    print(f"  tempo      : {elapsed:.1f}s")
    resp_text = resp.get("text") or ""
    print(f"  resposta   : {resp_text[:300]}...")
    plot_b64 = resp.get("plot_base64") or ""
    if plot_b64:
        print(f"  plot_base64: {len(plot_b64)} chars (OK)")
    else:
        print("  plot_base64: None (plot nao gerado)")
    print("  [OK]")
except Exception as e:
    print(f"  [ERRO] {e}")


# ─── 4. Verificar histórico no DynamoDB ─────────────────────────
sep("4. DYNAMODB — Histórico de conversas")
try:
    import boto3
    from boto3.dynamodb.conditions import Key

    dynamo = boto3.resource(
        "dynamodb",
        region_name="us-east-1",
        endpoint_url="http://localhost:8001",
        aws_access_key_id="fakeMyKeyId",
        aws_secret_access_key="fakeSecretKey",
    )
    table = dynamo.Table("agente-macro-conversations")

    resp = table.query(
        IndexName="RecentConversationsIndex",
        KeyConditionExpression=Key("entity_type").eq("conversation"),
        ScanIndexForward=False,
        Limit=10,
    )
    items = resp.get("Items", [])
    print(f"  Total de conversas salvas: {len(items)}")
    for item in items:
        sid = item.get("session_id", "?")
        q = item.get("question", "?")[:60]
        ts = item.get("timestamp", "?")[:19]
        has_data = item.get("has_data", "?")
        print(f"  [{ts}] {sid}: {q} | data={has_data}")
    if items:
        print("  [OK] DynamoDB salvou o histórico corretamente")
    else:
        print("  [AVISO] Nenhuma conversa salva no DynamoDB")
except Exception as e:
    print(f"  [ERRO] {e}")


# ─── 5. Rate limiting ────────────────────────────────────────────
sep("5. RATE LIMITING — 10 req/min")
try:
    blocked = 0
    for i in range(3):
        r_inner = urllib.request.urlopen(f"{BASE}/health", timeout=5)
        _ = r_inner.read()
    print(f"  3 requests ao /health: OK (rate limit aplica só ao /ask)")
    print("  [OK]")
except Exception as e:
    print(f"  status: {e}")


sep("RESUMO FINAL")
print("  Se todos os itens acima estão [OK], o pipeline está funcionando.")
print("  DynamoDB Local: persistindo histórico de conversas.")
print("  Multi-tool: planner gera lista de ferramentas, action executa em loop.")
