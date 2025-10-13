#!/bin/bash
# Quick Backfill Status Check
# Uso semplice: ./scripts/check_backfill.sh

LOG_FILE=$(ls -t ~/.claude/logs/devstream/backfill_production_*.log 2>/dev/null | head -1)
PID_FILE=~/.claude/logs/devstream/backfill.pid

if [ ! -f "$PID_FILE" ]; then
    echo "❌ Backfill non attivo (PID file non trovato)"
    exit 1
fi

PID=$(cat "$PID_FILE")

if ! ps -p $PID > /dev/null 2>&1; then
    echo "🛑 Backfill terminato (PID $PID non attivo)"
    echo ""
    echo "Ultimi 20 righe del log:"
    tail -20 "$LOG_FILE"
    exit 0
fi

echo "✅ Backfill ATTIVO (PID: $PID)"
echo ""

# Estrai info dal log
LAST_BATCH=$(grep "Processing batch" "$LOG_FILE" | tail -1 | grep -oE "[0-9]+-[0-9]+ of [0-9]+")
LAST_PROGRESS=$(grep "Progress:" "$LOG_FILE" | tail -1 | grep -oE "[0-9]+ processed.*")
LAST_ETA=$(grep "ETA:" "$LOG_FILE" | tail -1 | grep -oE "[0-9]+\.[0-9]+ minutes")
LAST_CHECKPOINT=$(grep "Checkpoint saved" "$LOG_FILE" | tail -1 | grep -oE "at [0-9]+ records")

echo "📊 STATO CORRENTE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Batch: $LAST_BATCH"
echo "Progress: $LAST_PROGRESS"
echo "ETA: $LAST_ETA"
echo "Checkpoint: $LAST_CHECKPOINT"
echo ""

# Conta record in vec_semantic_memory
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

echo "📈 vec_semantic_memory: $VEC_COUNT record"
echo ""

# Controlla errori
ERROR_COUNT=$(grep -c "ERROR" "$LOG_FILE" 2>/dev/null)
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "⚠️  ERRORI RILEVATI: $ERROR_COUNT"
    echo "Ultimi 5 errori:"
    grep "ERROR" "$LOG_FILE" | tail -5
else
    echo "✅ Nessun errore rilevato"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Per vedere il monitor in tempo reale:"
echo "  tmux attach -t backfill-monitor"
echo "  (Ctrl+B poi D per uscire)"
echo ""
echo "Log completo:"
echo "  tail -f $LOG_FILE"
