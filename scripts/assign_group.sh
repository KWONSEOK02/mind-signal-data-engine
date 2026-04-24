#!/usr/bin/env bash
# DUAL_2PC 세션에 groupId 주입 wrapper — Phase 17.5
# Usage: ./scripts/assign_group.sh <group_id> <de_url_1> <de_url_2> [secret]
#   secret: optional 4번째 인자. 생략 시 env ENGINE_SECRET_KEY 사용함
# Example: ./scripts/assign_group.sh 507f1f77... https://abc.ngrok.app https://xyz.ngrok.app mysecret
set -e

GROUP_ID="$1"
DE_A="$2"
DE_B="$3"
ENGINE_SECRET="${4:-${ENGINE_SECRET_KEY:-}}"

if [ -z "$GROUP_ID" ] || [ -z "$DE_A" ] || [ -z "$DE_B" ]; then
  echo "Usage: $0 <group_id> <de_url_1> <de_url_2> [secret]" >&2
  exit 1
fi
if [ -z "$ENGINE_SECRET" ]; then
  echo "[error] secret missing: pass as 4th arg or set ENGINE_SECRET_KEY env" >&2
  exit 1
fi

echo "[assign] DE A → ${DE_A}/control/assign-group"
curl -sS -X POST \
  -H "Content-Type: application/json" \
  -H "X-Engine-Secret: ${ENGINE_SECRET}" \
  -d "{\"group_id\": \"${GROUP_ID}\"}" \
  "${DE_A}/control/assign-group"
echo ""

echo "[assign] DE B → ${DE_B}/control/assign-group"
curl -sS -X POST \
  -H "Content-Type: application/json" \
  -H "X-Engine-Secret: ${ENGINE_SECRET}" \
  -d "{\"group_id\": \"${GROUP_ID}\"}" \
  "${DE_B}/control/assign-group"
echo ""

echo "[assign] done"
