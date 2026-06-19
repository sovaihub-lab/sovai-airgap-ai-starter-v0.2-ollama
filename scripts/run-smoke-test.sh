#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8080}"

echo "== Waiting for service =="
for i in $(seq 1 30); do
  if curl -s "$BASE_URL/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "== Status =="
curl -s "$BASE_URL/status" || true
echo ""

echo "== RAG with local Ollama LLM test =="
curl -s "$BASE_URL/ask"   -H "Content-Type: application/json"   -d '{"question":"Who can access confidential finance reports?","top_k":3,"use_llm":true}'
echo ""

echo "== RAG retrieve-only fallback test =="
curl -s "$BASE_URL/ask"   -H "Content-Type: application/json"   -d '{"question":"Who can access confidential finance reports?","top_k":3,"use_llm":false}'
echo ""

echo "== ML test =="
curl -s "$BASE_URL/ml/classify"   -H "Content-Type: application/json"   -d '{"text":"User cannot access VPN and needs MFA reset"}'
echo ""

echo "== Agent allowed tool test =="
curl -s "$BASE_URL/agent/run"   -H "Content-Type: application/json"   -d '{"tool":"calculator","input":"(12 * 7) + 5"}'
echo ""

echo "== Agent blocked tool test =="
curl -s "$BASE_URL/agent/run"   -H "Content-Type: application/json"   -d '{"tool":"web_search","input":"latest AI news"}'
echo ""

echo "Smoke test complete."
