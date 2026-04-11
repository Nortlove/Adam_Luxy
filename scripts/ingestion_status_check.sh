#!/usr/bin/env bash
# Ingestion status check – run periodically (e.g. every 1–2 hours). Exits immediately; no long-running tail.
# Usage: ./scripts/ingestion_status_check.sh   or   bash scripts/ingestion_status_check.sh

set -e
ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
LOG="$ROOT/data/reingestion_output/ingestion.log"
OUT="$ROOT/data/reingestion_output"

echo "=== $(date -u '+%Y-%m-%d %H:%M:%S') UTC ==="
echo ""

# 1. Process running?
if pgrep -f "unified_ingestion_with_product_copy" >/dev/null 2>&1; then
  echo "STATUS:  RUNNING"
  pgrep -fl "unified_ingestion_with_product_copy" || true
else
  echo "STATUS:  NOT RUNNING (ingestion may have finished or stopped)"
fi
echo ""

# 2. Result file count (per-category *_result.json)
COUNT=$(find "$OUT" -maxdepth 1 -name '*_result.json' 2>/dev/null | wc -l | tr -d ' ')
echo "RESULT FILES:  $COUNT category result(s)"
echo ""

# 3. Last 5 log lines (no tail -f; instant)
echo "LOG (last 5 lines):"
if [ -f "$LOG" ]; then
  tail -5 "$LOG"
else
  echo "  (no log file)"
fi
echo ""

# 4. Optional: latest review count from log (if present)
if [ -f "$LOG" ]; then
  LAST_REVIEW_LINE=$(grep -E "reviews \|.*products linked" "$LOG" 2>/dev/null | tail -1)
  if [ -n "$LAST_REVIEW_LINE" ]; then
    echo "LATEST PROGRESS:  $LAST_REVIEW_LINE"
  fi
fi
echo "---"
