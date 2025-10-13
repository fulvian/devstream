#!/bin/bash
# DevStream Backfill Monitor
# Monitors backfill progress with dynamic intervals

LOG_DIR="$HOME/.claude/logs/devstream"
PID_FILE="$LOG_DIR/backfill.pid"
LOG_FILE=$(ls -t "$LOG_DIR"/backfill_production_*.log 2>/dev/null | head -1)

# Check if backfill is running
if [ ! -f "$PID_FILE" ]; then
    echo "❌ No backfill PID file found at $PID_FILE"
    exit 1
fi

PID=$(cat "$PID_FILE")

if ! ps -p $PID > /dev/null 2>&1; then
    echo "❌ Backfill process (PID: $PID) is not running"
    echo "Check log: $LOG_FILE"
    exit 1
fi

echo "📊 DevStream Backfill Monitor"
echo "========================================"
echo "PID: $PID"
echo "Log: $LOG_FILE"
echo "========================================"
echo ""

START_TIME=$(date +%s)
ITERATION=0

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    ELAPSED_MIN=$((ELAPSED / 60))

    # Check if process is still running
    if ! ps -p $PID > /dev/null 2>&1; then
        echo ""
        echo "🛑 Backfill process completed or stopped"
        echo "Final log output:"
        tail -20 "$LOG_FILE"
        break
    fi

    # Extract progress from log
    LAST_BATCH=$(grep "Processing batch" "$LOG_FILE" | tail -1)
    LAST_ETA=$(grep "ETA:" "$LOG_FILE" | tail -1)
    PROGRESS_LINE=$(grep "Progress:" "$LOG_FILE" | tail -1)

    echo "⏰ $(date '+%H:%M:%S') | Elapsed: ${ELAPSED_MIN} min"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if [ -n "$LAST_BATCH" ]; then
        echo "$LAST_BATCH"
    fi

    if [ -n "$LAST_ETA" ]; then
        echo "$LAST_ETA"
    fi

    if [ -n "$PROGRESS_LINE" ]; then
        echo "$PROGRESS_LINE"
    fi

    # Check vec_semantic_memory count
    VEC_COUNT=$(.devstream/bin/python -c "
import sqlite3
import sys
sys.path.append('.claude/hooks/devstream/utils')
from sqlite_vec_helper import get_db_connection_with_vec
conn = get_db_connection_with_vec('data/devstream.db')
count = conn.execute('SELECT COUNT(*) FROM vec_semantic_memory').fetchone()[0]
conn.close()
print(count)
" 2>/dev/null)

    if [ -n "$VEC_COUNT" ]; then
        echo "📊 vec_semantic_memory records: $VEC_COUNT"
    fi

    # Check for errors
    ERROR_COUNT=$(grep -c "ERROR" "$LOG_FILE" 2>/dev/null)
    if [ -n "$ERROR_COUNT" ] && [ "$ERROR_COUNT" -gt 0 ]; then
        echo "⚠️  Errors detected: $ERROR_COUNT"
        echo "Recent errors:"
        grep "ERROR" "$LOG_FILE" | tail -3
    else
        echo "✅ No errors detected"
    fi

    echo ""

    ITERATION=$((ITERATION + 1))

    # Dynamic interval: 5 min for first 30 min, then 10 min
    if [ $ELAPSED_MIN -lt 30 ]; then
        INTERVAL=300  # 5 minutes
        echo "Next check in 5 minutes..."
    else
        INTERVAL=600  # 10 minutes
        echo "Next check in 10 minutes..."
    fi

    sleep $INTERVAL
done

echo ""
echo "========================================"
echo "📋 Backfill Monitor Stopped"
echo "========================================"
