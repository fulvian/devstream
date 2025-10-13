#!/bin/bash
# DevStream Root Cleanup Script
# Date: 2025-10-12
# Purpose: Clean up root directory according to GitHub/Context7 best practices

set -e  # Exit on error

PROJECT_ROOT="/Users/fulvioventura/devstream"
BACKUP_DIR=".archive/root-backup-$(date +%Y%m%d-%H%M%S)"
LOG_FILE="$PROJECT_ROOT/scripts/cleanup_root_$(date +%Y%m%d-%H%M%S).log"

cd "$PROJECT_ROOT"

echo "=== DevStream Root Cleanup ===" | tee "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Create backup directory
echo "Step 1/6: Creating backup..." | tee -a "$LOG_FILE"
mkdir -p "$BACKUP_DIR"
echo "✅ Backup directory created: $BACKUP_DIR" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Function to backup and move file
backup_and_move() {
    local file=$1
    local dest=$2

    if [ -f "$file" ] || [ -d "$file" ]; then
        # Backup
        cp -r "$file" "$BACKUP_DIR/" 2>/dev/null || true

        # Create destination directory
        mkdir -p "$(dirname "$dest")"

        # Move
        mv "$file" "$dest"
        echo "  ✓ $file → $dest" | tee -a "$LOG_FILE"
    else
        echo "  ⚠ Not found: $file" | tee -a "$LOG_FILE"
    fi
}

# Function to safe delete
safe_delete() {
    local file=$1

    if [ -f "$file" ] || [ -d "$file" ]; then
        # Backup before delete
        cp -r "$file" "$BACKUP_DIR/" 2>/dev/null || true
        rm -rf "$file"
        echo "  ✓ Deleted: $file" | tee -a "$LOG_FILE"
    else
        echo "  ⚠ Not found: $file" | tee -a "$LOG_FILE"
    fi
}

# ========================================
# Step 2: Delete temporary/generated files
# ========================================
echo "Step 2/6: Deleting temporary/generated files..." | tee -a "$LOG_FILE"

# Pip install errors
safe_delete "=0.1.4"
safe_delete "=1.0.0"
safe_delete "=23.0.0"
safe_delete "=3.8.0"

# Coverage files
safe_delete ".coverage"
safe_delete "htmlcov"

# Log files
safe_delete "backfill_20251007_085802.log"
safe_delete "backfill_continuous_20251007_090530.log"
safe_delete "backfill_output.log"
safe_delete "backfill_verbose_20251007_090151.log"
safe_delete "devstream-server.log"
safe_delete "final_sync.log"
safe_delete "sync_final.log"
safe_delete "test_post_tool_use.txt"
safe_delete "test_session_tracking.txt"

# Backup env
safe_delete ".env.devstream.backup-20251002-165842"

# Prova directory
safe_delete "prova"

echo "✅ Temporary files deleted" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# ========================================
# Step 3: Move docs to docs/
# ========================================
echo "Step 3/6: Moving documentation files..." | tee -a "$LOG_FILE"

# Architecture docs
backup_and_move "AGENTS.md" "docs/architecture/AGENTS.md"

# Deployment docs
backup_and_move "DEPLOY_GLM46_OPTIMIZED.md" "docs/deployment/DEPLOY_GLM46_OPTIMIZED.md"
backup_and_move "ZAI_NATIVE_SETUP_FINAL.md" "docs/deployment/ZAI_NATIVE_SETUP_FINAL.md"

# Guides
backup_and_move "GLM46_QUICKSTART.md" "docs/guides/GLM46_QUICKSTART.md"
backup_and_move "GLM46_REASONING_MODE_GUIDE.md" "docs/guides/GLM46_REASONING_MODE_GUIDE.md"
backup_and_move "QUICKSTART_ZAI.md" "docs/guides/QUICKSTART_ZAI.md"
backup_and_move "START_DEVSTREAM.md" "docs/guides/START_DEVSTREAM.md"
backup_and_move "START_WITH_ZAI.md" "docs/guides/START_WITH_ZAI.md"

# Implementation docs
backup_and_move "ZAI_INTEGRATION_SUMMARY.md" "docs/implementation/ZAI_INTEGRATION_SUMMARY.md"

# Verification docs
backup_and_move "CACHE_VERIFICATION.md" "docs/verification/CACHE_VERIFICATION.md"
backup_and_move "FASE_5.4_COMPLETION_SUMMARY.md" "docs/verification/FASE_5.4_COMPLETION_SUMMARY.md"
backup_and_move "FASE_5.4_ROOT_CAUSE_FIX.md" "docs/verification/FASE_5.4_ROOT_CAUSE_FIX.md"
backup_and_move "PHASE_5_TEST_COMPLETION_REPORT.md" "docs/verification/PHASE_5_TEST_COMPLETION_REPORT.md"
backup_and_move "PHASE_C_VALIDATION_SUMMARY.md" "docs/verification/PHASE_C_VALIDATION_SUMMARY.md"
backup_and_move "SMOKE_TEST_RESULTS.md" "docs/verification/SMOKE_TEST_RESULTS.md"
backup_and_move "TEST_RESULTS_PHASE_C.md" "docs/verification/TEST_RESULTS_PHASE_C.md"

echo "✅ Documentation files moved" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# ========================================
# Step 4: Move tests to tests/
# ========================================
echo "Step 4/6: Moving test files..." | tee -a "$LOG_FILE"

# Create tests/manual directory
mkdir -p tests/manual
mkdir -p tests/fixtures

# Test scripts to tests/manual/
backup_and_move "test_adaptive_search.md" "tests/manual/test_adaptive_search.md"
backup_and_move "test_concurrency_implementation.py" "tests/manual/test_concurrency_implementation.py"
backup_and_move "test_crash_prevention.py" "tests/manual/test_crash_prevention.py"
backup_and_move "test_embedding_comparison.js" "tests/manual/test_embedding_comparison.js"
backup_and_move "test_embedding_comparison.py" "tests/manual/test_embedding_comparison.py"
backup_and_move "test_fase1_integration.py" "tests/manual/test_fase1_integration.py"
backup_and_move "test_fase3_implementation.py" "tests/manual/test_fase3_implementation.py"
backup_and_move "test_hook_verification.py" "tests/manual/test_hook_verification.py"
backup_and_move "test_natural_language_queries.py" "tests/manual/test_natural_language_queries.py"
backup_and_move "test_natural_language_search.py" "tests/manual/test_natural_language_search.py"
backup_and_move "test_new_db_operations.py" "tests/manual/test_new_db_operations.py"
backup_and_move "test_optimized_search.py" "tests/manual/test_optimized_search.py"
backup_and_move "test_post_tool_use.py" "tests/manual/test_post_tool_use.py"
backup_and_move "test_quality_evaluator_simple.py" "tests/manual/test_quality_evaluator_simple.py"
backup_and_move "test_quality_evaluator.py" "tests/manual/test_quality_evaluator.py"
backup_and_move "test_quick_queries.py" "tests/manual/test_quick_queries.py"
backup_and_move "test_quick_search.py" "tests/manual/test_quick_search.py"
backup_and_move "test_rag_quality_evaluation.py" "tests/manual/test_rag_quality_evaluation.py"
backup_and_move "test_realtime_sync.py" "tests/manual/test_realtime_sync.py"
backup_and_move "test_search_consistency.py" "tests/manual/test_search_consistency.py"
backup_and_move "test_session_fix_simple.py" "tests/manual/test_session_fix_simple.py"
backup_and_move "test_simple_search.py" "tests/manual/test_simple_search.py"
backup_and_move "test_trigger_end_to_end.py" "tests/manual/test_trigger_end_to_end.py"
backup_and_move "test_vector_search_functional.py" "tests/manual/test_vector_search_functional.py"
backup_and_move "test_zai_connection.sh" "tests/manual/test_zai_connection.sh"
backup_and_move "test_zai_e2e.sh" "tests/manual/test_zai_e2e.sh"
backup_and_move "test-backfill-dryrun.py" "tests/manual/test-backfill-dryrun.py"
backup_and_move "test-posttooluse-retry.py" "tests/manual/test-posttooluse-retry.py"
backup_and_move "test-retry-simple.py" "tests/manual/test-retry-simple.py"
backup_and_move "test-vector-search-manual.js" "tests/manual/test-vector-search-manual.js"

# JSON fixtures to tests/fixtures/
backup_and_move "embedding_python.json" "tests/fixtures/embedding_python.json"
backup_and_move "embedding_typescript.json" "tests/fixtures/embedding_typescript.json"
backup_and_move "test_query_embedding.json" "tests/fixtures/test_query_embedding.json"
backup_and_move "events_demo.json" "tests/fixtures/events_demo.json"
backup_and_move "events_demo.jsonl" "tests/fixtures/events_demo.jsonl"

echo "✅ Test files moved" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# ========================================
# Step 5: Move scripts to scripts/
# ========================================
echo "Step 5/6: Moving script files..." | tee -a "$LOG_FILE"

backup_and_move "full-backfill.py" "scripts/full-backfill.py"
backup_and_move "verify_complete_database.py" "scripts/verify_complete_database.py"
backup_and_move "verify_real_sync.py" "scripts/verify_real_sync.py"
backup_and_move "UPDATE_GLM46_IP.sh" "scripts/UPDATE_GLM46_IP.sh"
backup_and_move "context7-wrapper.sh" "scripts/context7-wrapper.sh"

echo "✅ Script files moved" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# ========================================
# Step 6: Move config files to config/
# ========================================
echo "Step 6/6: Moving config files..." | tee -a "$LOG_FILE"

backup_and_move "claude-code-router-config-optimized.json" "config/claude-code-router-config-optimized.json"
backup_and_move ".env.example.deployment" "config/.env.example.deployment"

echo "✅ Config files moved" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# ========================================
# Final report
# ========================================
echo "=== CLEANUP COMPLETE ===" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "📊 Summary:" | tee -a "$LOG_FILE"
echo "  - Backup location: $BACKUP_DIR" | tee -a "$LOG_FILE"
echo "  - Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "✅ Root directory cleaned successfully!" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Show remaining root files
echo "📁 Remaining files in root:" | tee -a "$LOG_FILE"
ls -1 "$PROJECT_ROOT" | grep -v "^\." | grep -v "^scripts$" | grep -v "^tests$" | grep -v "^docs$" | grep -v "^src$" | grep -v "^config$" | grep -v "^data$" | grep -v "^schema$" | grep -v "^templates$" | grep -v "^examples$" | grep -v "^sqlite-extensions$" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

echo "Completed: $(date)" | tee -a "$LOG_FILE"
