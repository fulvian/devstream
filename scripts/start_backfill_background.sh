#!/bin/bash
# Start backfill in background with logging

LOG_DIR="$HOME/.claude/logs/devstream"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/backfill_$(date +%Y%m%d_%H%M%S).log"

echo "🚀 Starting Backfill in Background"
echo "Log: $LOG_FILE"

nohup .devstream/bin/python scripts/backfill_embeddings_production.py > "$LOG_FILE" 2>&1 &
PID=$!

echo "✅ Backfill started (PID: $PID)"
echo "$PID" > "$LOG_DIR/backfill.pid"
echo ""
echo "Monitor progress:"
echo "  tail -f $LOG_FILE"
echo ""
echo "Check if running:"
echo "  ps aux | grep $PID"
