#!/bin/bash
# Test script per verificare il launcher fino al punto di pre-launch
# Questo script modifica temporaneamente start_claude_with_devstream per fermarsi prima di exec

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_PROJECT="/Users/fulvioventura/exc-to-pdf"

echo "=========================================="
echo "Test Launcher - Dry Run Mode"
echo "=========================================="
echo ""
echo "Script directory: $SCRIPT_DIR"
echo "Test project:     $TEST_PROJECT"
echo ""

# Cambia alla directory del progetto
cd "$TEST_PROJECT" || {
  echo "ERROR: Cannot change to test project directory"
  exit 1
}

echo "Current directory: $(pwd)"
echo ""

# Crea una versione modificata del launcher con dry-run
TMP_LAUNCHER="$SCRIPT_DIR/start-devstream2-dryrun.sh"
cp "$SCRIPT_DIR/start-devstream2.sh" "$TMP_LAUNCHER"

# Modifica la funzione start_claude_with_devstream per fermarsi prima di exec
# Sostituisce "exec claude" con "echo \"DRY-RUN: Would exec claude\" && return 0"
sed -i.bak 's/exec claude/echo "🔍 DRY-RUN: Would exec claude in directory: $(pwd)" \&\& echo "   DEVSTREAM_DB_PATH: $DEVSTREAM_DB_PATH" \&\& return 0/' "$TMP_LAUNCHER"

# Sostituisce anche "exec \"\$zai_script\"" per z.ai mode
sed -i.bak2 's/exec "\$zai_script"/echo "🔍 DRY-RUN: Would exec z.ai script: $zai_script" \&\& return 0/' "$TMP_LAUNCHER"

echo "=========================================="
echo "Executing launcher in DRY-RUN mode..."
echo "=========================================="
echo ""

# Esegue il launcher modificato
"$TMP_LAUNCHER" start anthropic 2>&1 | tail -80

# Cleanup
rm -f "$TMP_LAUNCHER" "$TMP_LAUNCHER.bak" "$TMP_LAUNCHER.bak2"

echo ""
echo "=========================================="
echo "Dry-run completed"
echo "=========================================="
