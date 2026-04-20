#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR="openspec/changes/trade-execution-split-aware-linking/validation/artifacts"
mkdir -p "$ARTIFACT_DIR"

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
ACCOUNT_ID="${ACCOUNT_ID:-11111111-1111-1111-1111-111111111111}"
TOKEN="${TOKEN:-}"
IMPORT_FILE="${IMPORT_FILE:-tests/test_data/ibkr/TraderJournal_anonymized_combined.xml}"

if [[ -z "$TOKEN" ]]; then
  echo "TOKEN is required." | tee "$ARTIFACT_DIR/performance-summary.txt"
  exit 1
fi

if [[ ! -f "$IMPORT_FILE" ]]; then
  echo "Import file not found: $IMPORT_FILE" | tee "$ARTIFACT_DIR/performance-summary.txt"
  exit 1
fi

echo "Running baseline import timing..."
time curl -sS -X POST "$API_BASE_URL/api/v1/imports/ibkr" \
  -H "Authorization: Bearer $TOKEN" \
  -F "account_id=$ACCOUNT_ID" \
  -F "file=@$IMPORT_FILE" \
  > "$ARTIFACT_DIR/performance-baseline.json" \
  2> "$ARTIFACT_DIR/performance-baseline.time.txt"

echo "Running split-aware import timing..."
time curl -sS -X POST "$API_BASE_URL/api/v1/imports/ibkr" \
  -H "Authorization: Bearer $TOKEN" \
  -F "account_id=$ACCOUNT_ID" \
  -F "file=@$IMPORT_FILE" \
  > "$ARTIFACT_DIR/performance-split.json" \
  2> "$ARTIFACT_DIR/performance-split.time.txt"

echo "Performance run finished." | tee "$ARTIFACT_DIR/performance-summary.txt"
echo "Compute regression as: (split - baseline) / baseline" | tee -a "$ARTIFACT_DIR/performance-summary.txt"
