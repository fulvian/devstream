#!/bin/bash
# DevStream Production Backfill Script
# Runs embedding backfill in background with logging

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$HOME/.claude/logs/devstream"
LOG_FILE="$LOG_DIR/backfill_$(date +%Y%m%d_%H%M%S).log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

echo "🚀 Starting DevStream Backfill (Background)"
echo "=" >> "$LOG_FILE"
echo "Backfill started at $(date)" >> "$LOG_FILE"
echo "Log file: $LOG_FILE"
echo "=" >> "$LOG_FILE"
echo ""

# Run backfill in background with nohup
cd "$PROJECT_ROOT"
nohup .devstream/bin/python .claude/hooks/devstream/memory/backfill_embeddings.py \
  --batch-size 16 \
  --db-path data/devstream.db \
  >> "$LOG_FILE" 2>&1 &

BACKFILL_PID=$!

echo "✅ Backfill process started"
echo "   PID: $BACKFILL_PID"
echo "   Log: $LOG_FILE"
echo ""
echo "Monitor progress:"
echo "   tail -f $LOG_FILE"
echo ""
echo "Check status:"
echo "   ps aux | grep $BACKFILL_PID"
echo ""
echo "Estimated completion: ~2 hours"

# Save PID for later monitoring
echo "$BACKFILL_PID" > "$LOG_DIR/backfill.pid"
