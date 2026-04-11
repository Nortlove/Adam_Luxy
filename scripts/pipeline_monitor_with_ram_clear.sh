#!/bin/bash
# Periodic pipeline progress check + RAM clear during re-ingestion / full pipeline.
# Run in background while run_full_reingestion.py or run_full_pipeline.py is running.
#
# Usage:
#   ./scripts/pipeline_monitor_with_ram_clear.sh [interval_minutes] [log_file]
#   Default: interval=15 min, log=data/pipeline_monitor.log
#
# Example (background):
#   nohup ./scripts/pipeline_monitor_with_ram_clear.sh 15 data/pipeline_monitor.log &
#   Or foreground with 10-min interval: ./scripts/pipeline_monitor_with_ram_clear.sh 10

set -e
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

INTERVAL_MIN="${1:-15}"
LOG_FILE="${2:-$PROJECT_ROOT/data/pipeline_monitor.log}"
REINGESTION_LOG="$PROJECT_ROOT/data/reingestion_remaining.log"
PIPELINE_LOG="$PROJECT_ROOT/data/pipeline_output.log"
OUTPUT_DIR="$PROJECT_ROOT/data/reingestion_output"

mkdir -p "$(dirname "$LOG_FILE")"
SECONDS=$((INTERVAL_MIN * 60))

log() {
    echo "$1" | tee -a "$LOG_FILE"
}

while true; do
    TS=$(date '+%Y-%m-%d %H:%M:%S')
    log ""
    log "========== $TS =========="

    # 1. Re-ingestion progress
    if [[ -d "$OUTPUT_DIR" ]]; then
        COUNT=$(find "$OUTPUT_DIR" -maxdepth 1 -name '*_result.json' ! -name 'TOTAL_result.json' 2>/dev/null | wc -l | tr -d ' ')
        log "Re-ingestion: $COUNT category result files (target 32-33)"
    else
        log "Re-ingestion: output dir not found"
    fi

    # 2. Is re-ingestion or pipeline running?
    if pgrep -f "run_full_reingestion.py" >/dev/null 2>&1; then
        log "Process: run_full_reingestion.py is RUNNING"
    else
        log "Process: run_full_reingestion.py not running"
    fi
    if pgrep -f "run_full_pipeline.py" >/dev/null 2>&1; then
        log "Process: run_full_pipeline.py is RUNNING"
    else
        log "Process: run_full_pipeline.py not running"
    fi

    # 3. Recent log tail (last 3 lines of re-ingestion or pipeline log)
    if [[ -f "$REINGESTION_LOG" ]]; then
        log "--- Last lines of reingestion_remaining.log ---"
        tail -3 "$REINGESTION_LOG" 2>/dev/null | while read -r line; do log "  $line"; done
    fi
    if [[ -f "$PIPELINE_LOG" ]]; then
        log "--- Last lines of pipeline_output.log ---"
        tail -2 "$PIPELINE_LOG" 2>/dev/null | while read -r line; do log "  $line"; done
    fi

    # 4. Memory snapshot
    log "--- Memory ---"
    if command -v vm_stat &>/dev/null; then
        vm_stat | grep -E "Pages (free|active|inactive)" | while read -r line; do log "  $line"; done
    fi
    if command -v sysctl &>/dev/null; then
        sysctl vm.swapusage 2>/dev/null | while read -r line; do log "  $line"; done
    fi

    # 5. RAM clear (purge on macOS)
    log "--- RAM clear (purge) ---"
    if command -v purge &>/dev/null; then
        purge 2>/dev/null || sudo purge 2>/dev/null || true
        log "  Purge done."
    else
        log "  (purge not available)"
    fi

    log "Next check in ${INTERVAL_MIN} minutes."
    sleep "$SECONDS"
done
