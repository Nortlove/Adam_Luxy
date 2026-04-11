#!/bin/bash
# Periodic RAM monitoring and optional clear for ADAM pipeline
# Use during long runs (re-ingestion, pipeline) to reduce Cursor/system crashes.
# Run: ./scripts/monitor_and_clear_ram.sh [--clear]
# Or in a loop every 15 min: while true; do ./scripts/monitor_and_clear_ram.sh --clear; sleep 900; done

set -e
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== $(date -u '+%Y-%m-%d %H:%M:%S') UTC ==="

# macOS memory summary
if command -v vm_stat &>/dev/null; then
    echo "--- Memory (vm_stat) ---"
    vm_stat | grep -E "Pages (free|active|inactive|wired|speculative)"
fi
if command -v sysctl &>/dev/null; then
    echo "--- Swap ---"
    sysctl vm.swapusage 2>/dev/null || true
fi

# Process memory (top 5 by RSS)
echo "--- Top 5 processes by memory ---"
ps -eo pid,rss,comm | sort -k2 -rn | head -6

# Optional: run purge to free inactive memory (macOS)
if [[ "${1:-}" == "--clear" ]]; then
    echo ""
    echo "Running purge (requires sudo for full effect)..."
    if command -v purge &>/dev/null; then
        purge 2>/dev/null || sudo purge
        echo "Purge done."
    else
        echo "No purge command (not macOS?). Use scripts/clear_ram.sh on macOS."
    fi
fi

echo ""
