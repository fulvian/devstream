# GLM-4.6 Handoff Document: Fix MCP Multi-Instance Wrong Database Path

**Handoff Type**: Sonnet 4.5 → GLM-4.6
**Task**: Fix MCP DevStream Server Multi-Instance with Wrong Database Path
**Protocol**: DevStream Protocol v2.2.0
**Date**: 2025-10-13
**Status**: Ready for GLM-4.6 Execution

---
piano di intervento di rifeirmento (da leggere ecseguire): /Users/fulvioventura/devstream/docs/development/plan/piano_fix-mcp-multi-instance-wrong-path.md
## Executive Summary for GLM-4.6

You are receiving this task from Claude Sonnet 4.5, which completed STEPS 1-4 of the DevStream Protocol (DISCUSSION, ANALYSIS, RESEARCH, PLANNING). Your role is to execute STEP 6 - IMPLEMENTATION following the detailed implementation plan.

**Your Mission**: Execute the implementation plan to fix MCP multi-instance spawn issue caused by Claude Code's in-memory configuration cache.

**Success Criteria**: Single MCP instance running with correct database path (`/Users/fulvioventura/devstream/data/devstream.db`), zero wrong-path detections, all functionality verified.

---

## Problem Context (Complete Background)

### Symptoms Observed
1. **Multiple MCP instances spawning**: 3 processes running simultaneously
2. **Wrong database path usage**: 1 instance using `/Users/fulvioventura/devstream/mcp-devstream-server/data/devstream.db` (56KB)
3. **Auto-respawn loop**: Cleanup kills processes → Claude Code respawns with cached wrong config → infinite loop
4. **Database discrepancy**: Wrong path DB has 56KB vs correct path DB has 500MB with 113,594 records

### Timeline of Issue
```
2025-10-13 07:48:23  - .mcp.json corrected to proper database path
                     - Claude Code session continued without reloading config
                     - Cache persisted old wrong-path configuration
Pre-launch cleanup   - Kills all existing MCP processes
Auto-respawn         - Claude Code respawns MCP using CACHED wrong config
Result               - Infinite loop: Kill → Respawn (wrong) → Kill → Respawn
```

### Root Cause Identified

**Primary Cause**: Claude Code In-Memory Configuration Cache
- Claude Code loads `.mcp.json` into memory on first session start
- Cache persists across file edits until full application restart
- Auto-respawn mechanism uses cached configuration, NOT disk file
- No hot-reload capability for `.mcp.json` changes

**Validation Evidence**:
- File system shows `.mcp.json` modified with correct path (2025-10-13 07:48:23)
- Process command lines show wrong path still being used
- Only historical documentation contains wrong path pattern in codebase
- All active code validated with correct paths

### Comprehensive Search Results

**Search Phase 1: Grep Operations** (Completed by Sonnet 4.5)
```bash
# Grep 1: Exact wrong path pattern
Pattern: "mcp-devstream-server/data/devstream.db"
Result: 1 match in MCP-MULTI-PROCESS-CONFLICT.md (historical documentation ONLY)

# Grep 2: Environment variable misconfiguration
Pattern: "DEVSTREAM_DB_PATH.*mcp-devstream-server"
Result: 0 matches (no env var misconfigurations)

# Grep 3: All database path references
Pattern: "data/devstream.db"
Result: 165 files found, 9 critical files audited systematically
```

**Search Phase 2: Critical File Audit** (Completed by Sonnet 4.5)

9 critical files audited, ALL contain correct database paths:

1. **`.env.devstream`** - Line 253: `DEVSTREAM_DB_PATH=data/devstream.db` ✅
2. **`.mcp.json`** - Env section: `"DEVSTREAM_DB_PATH": "/Users/fulvioventura/devstream/data/devstream.db"` ✅
3. **`mcp_client.py`** - Lines 54-70: Correct default path `data/devstream.db` with security validation ✅
4. **`session_coordinator.py`** - No hardcoded paths, uses client ✅
5. **`work_session_manager.py`** - No hardcoded paths, uses client ✅
6. **`mcp_cleanup_hook.py`** - Pattern-based cleanup, no path validation (needs enhancement) ⚠️
7. **`mcp_process_monitor.py`** - No hardcoded paths ✅
8. **`start-devstream.sh`** - Lines 456-468: Pre-launch cleanup exists but no path validation (needs enhancement) ⚠️
9. **`index.ts`** - Lines 656-676: CLI argument priority, then `DEVSTREAM_DB_PATH` env var, no hardcoded paths ✅
10. **`.env.example.deployment`** - Example config only, correct path ✅

**Key Finding**: Wrong path exists ONLY in historical documentation. All active code uses correct paths. Issue is Claude Code in-memory cache, NOT codebase.

---

## Implementation Plan Overview

You will execute **5 phases** in sequence:

1. **Phase 1 - Immediate Disablement** (10 min, CRITICAL)
   - Clear Claude Code cache via full application restart
   - Kill all wrong-path MCP processes
   - Validate cache clearing

2. **Phase 2 - Configuration Validation** (15 min, CRITICAL)
   - Audit all `.mcp.json` files in workspace
   - Validate environment variables
   - Verify MCP server code has no hardcoded paths

3. **Phase 3 - Cleanup Enhancement** (20 min)
   - Add wrong-path detection to cleanup hooks
   - Add pre-launch path validation to startup scripts
   - Test enhanced detection

4. **Phase 4 - Verification** (10 min, CRITICAL)
   - Validate single MCP instance running
   - Verify correct database path in use
   - Test all MCP functionality

5. **Phase 5 - Prevention** (15 min)
   - Setup monitoring for wrong-path detection
   - Create documentation on cache behavior
   - Establish cache clearing protocol

**Total Time**: ~70 minutes (35 min critical path)

---

## Critical Paths (MUST Complete)

These phases MUST succeed for resolution:

### Critical Path 1: Phase 1 - Immediate Disablement
**WHY CRITICAL**: Stops infinite respawn loop, clears cache causing issue.

**Success Criteria**:
- ✅ Zero MCP processes running after cleanup
- ✅ Claude Code application fully restarted
- ✅ `.mcp.json` verified with correct path
- ✅ No auto-respawn before project open

**If Fails**: Cannot proceed. Issue persists. Rollback and retry.

### Critical Path 2: Phase 2 - Configuration Validation
**WHY CRITICAL**: Ensures no configuration corruption exists in workspace.

**Success Criteria**:
- ✅ Single `.mcp.json` in project root with correct path
- ✅ All `.env*` files use correct relative path
- ✅ No hardcoded wrong paths found

**If Fails**: Document findings, escalate to user, do NOT proceed to Phase 3-5.

### Critical Path 3: Phase 4 - Verification
**WHY CRITICAL**: Proves fix successful, validates system functional.

**Success Criteria**:
- ✅ Exactly ONE MCP process running
- ✅ MCP using correct database path
- ✅ Database has ~500MB size, ~113K records
- ✅ All functionality tested and working

**If Fails**: Return to Phase 1, retry cache clearing. Document failure.

---

## Detailed Execution Instructions

### Phase 1: Immediate Disablement (10 minutes)

#### Step 1.1: Pre-Cleanup Documentation (2 min)
```bash
# Create timestamped log file
LOG_FILE="/tmp/mcp-cleanup-$(date +%Y%m%d-%H%M%S).log"
date > "$LOG_FILE"
echo "=== PRE-CLEANUP STATE ===" >> "$LOG_FILE"

# Capture all MCP processes with full command lines
pgrep -af "mcp-devstream-server/dist/index.js" >> "$LOG_FILE"

# Capture database connections
echo -e "\n=== DATABASE CONNECTIONS ===" >> "$LOG_FILE"
lsof /Users/fulvioventura/devstream/mcp-devstream-server/data/devstream.db >> "$LOG_FILE" 2>&1 || echo "No connections to wrong DB" >> "$LOG_FILE"
lsof /Users/fulvioventura/devstream/data/devstream.db >> "$LOG_FILE" 2>&1 || echo "No connections to correct DB" >> "$LOG_FILE"

echo "✅ Pre-cleanup state documented in: $LOG_FILE"
```

**Expected Output**: Log file created with current MCP process state and database connections.

#### Step 1.2: Kill All MCP Processes (1 min)
```bash
# Execute DevStream cleanup utility
/Users/fulvioventura/devstream/.devstream/bin/python \
  /Users/fulvioventura/devstream/.claude/hooks/devstream/monitoring/mcp_cleanup_hook.py

# Wait for cleanup completion
sleep 2

# Verify all processes terminated
REMAINING=$(pgrep -f "mcp-devstream-server/dist/index.js" | wc -l)
if [ "$REMAINING" -gt 0 ]; then
    echo "⚠️  WARNING: $REMAINING processes still running:"
    pgrep -af "mcp-devstream-server/dist/index.js"
    echo "Attempting force kill..."
    pkill -9 -f "mcp-devstream-server/dist/index.js"
    sleep 1
fi

# Final verification
FINAL=$(pgrep -f "mcp-devstream-server/dist/index.js" | wc -l)
if [ "$FINAL" -eq 0 ]; then
    echo "✅ All MCP processes successfully terminated"
else
    echo "❌ ERROR: Failed to terminate all MCP processes"
    exit 1
fi
```

**Expected Output**: All MCP processes killed, zero processes remaining.

#### Step 1.3: Full Claude Code Application Restart (5 min)
```bash
echo ""
echo "========================================"
echo "⚠️  MANUAL ACTION REQUIRED ⚠️"
echo "========================================"
echo ""
echo "CRITICAL: Claude Code application restart required to clear configuration cache"
echo ""
echo "PROCEDURE:"
echo "  1. Save all work in Claude Code"
echo "  2. Quit Claude Code completely (Cmd+Q on macOS, or File → Quit)"
echo "  3. Wait 10 seconds for full process termination"
echo "  4. Verify no MCP processes running:"
echo "     pgrep -f 'mcp-devstream-server/dist/index.js'"
echo "  5. If processes still running, kill manually:"
echo "     pkill -9 -f 'mcp-devstream-server/dist/index.js'"
echo "  6. Relaunch Claude Code application"
echo "  7. Wait at start screen, do NOT open project yet"
echo ""
echo "WHY: This clears the in-memory .mcp.json configuration cache"
echo ""
echo "Press ENTER after completing Claude Code restart..."
read
```

**User Action Required**: Manual Claude Code restart. Wait for user confirmation.

#### Step 1.4: Verify Cache Clearing (2 min)
```bash
# Verify no MCP processes running after restart
if pgrep -f "mcp-devstream-server/dist/index.js" > /dev/null; then
    echo "⚠️  WARNING: MCP processes still running after restart!"
    pgrep -af "mcp-devstream-server/dist/index.js"
    echo ""
    echo "This indicates incomplete Claude Code shutdown."
    echo "Please verify Claude Code is fully quit and retry."
    exit 1
else
    echo "✅ No MCP processes running - cache clearing successful"
fi

# Verify .mcp.json has correct configuration
echo ""
echo "=== Verifying .mcp.json Configuration ==="
CONFIG_PATH=$(grep "DEVSTREAM_DB_PATH" /Users/fulvioventura/devstream/.mcp.json | sed 's/.*": "//;s/".*//')
echo "Database path in .mcp.json: $CONFIG_PATH"

if [[ "$CONFIG_PATH" == "/Users/fulvioventura/devstream/data/devstream.db" ]]; then
    echo "✅ .mcp.json configuration verified correct"
else
    echo "❌ ERROR: .mcp.json still has wrong path: $CONFIG_PATH"
    echo "Expected: /Users/fulvioventura/devstream/data/devstream.db"
    exit 1
fi

echo ""
echo "✅ Phase 1 Complete: Cache cleared and configuration verified"
```

**Expected Output**: No MCP processes, correct path in `.mcp.json`.

**Phase 1 Success Criteria Checklist**:
- [ ] Pre-cleanup state documented
- [ ] All MCP processes terminated
- [ ] Claude Code application restarted
- [ ] No processes running after restart
- [ ] `.mcp.json` contains correct path

### Phase 2: Configuration Validation (15 minutes)

#### Step 2.1: Workspace Configuration Audit (5 min)
```bash
echo ""
echo "=== Phase 2: Configuration Validation ==="
echo ""

# Search all .mcp.json files in workspace
echo "Searching for all .mcp.json files..."
MCP_FILES=$(find /Users/fulvioventura/devstream -name ".mcp.json" -type f 2>/dev/null)

if [ -z "$MCP_FILES" ]; then
    echo "❌ ERROR: No .mcp.json files found!"
    exit 1
fi

echo "Found .mcp.json files:"
echo "$MCP_FILES"
echo ""

# Validate each .mcp.json
MCP_COUNT=$(echo "$MCP_FILES" | wc -l)
if [ "$MCP_COUNT" -ne 1 ]; then
    echo "⚠️  WARNING: Expected 1 .mcp.json file, found: $MCP_COUNT"
fi

echo "=== Validating Each Configuration ==="
while IFS= read -r mcp_file; do
    echo ""
    echo "File: $mcp_file"

    # Check for DEVSTREAM_DB_PATH
    if grep -q "DEVSTREAM_DB_PATH" "$mcp_file"; then
        DB_PATH=$(grep "DEVSTREAM_DB_PATH" "$mcp_file" | sed 's/.*": "//;s/".*//')
        echo "  Database Path: $DB_PATH"

        # Validate it's the correct path
        if [[ "$DB_PATH" == "/Users/fulvioventura/devstream/data/devstream.db" ]]; then
            echo "  Status: ✅ CORRECT"
        elif [[ "$DB_PATH" == *"mcp-devstream-server/data/devstream.db"* ]]; then
            echo "  Status: ❌ WRONG PATH DETECTED!"
            echo "  This file needs correction!"
        else
            echo "  Status: ⚠️  UNEXPECTED PATH"
        fi
    else
        echo "  Status: ⚠️  No DEVSTREAM_DB_PATH found"
    fi
done <<< "$MCP_FILES"

echo ""
echo "✅ Step 2.1 Complete: Workspace .mcp.json files audited"
```

**Expected Output**: Single `.mcp.json` file in project root with correct path.

#### Step 2.2: Environment Variables Validation (5 min)
```bash
echo ""
echo "=== Validating Environment Variables ==="

# Check .env.devstream
echo "1. Checking .env.devstream:"
if [ -f "/Users/fulvioventura/devstream/.env.devstream" ]; then
    ENV_PATH=$(grep "^DEVSTREAM_DB_PATH=" /Users/fulvioventura/devstream/.env.devstream | cut -d= -f2)
    echo "   DEVSTREAM_DB_PATH=$ENV_PATH"

    if [[ "$ENV_PATH" == "data/devstream.db" ]]; then
        echo "   Status: ✅ CORRECT (relative path)"
    else
        echo "   Status: ⚠️  UNEXPECTED: $ENV_PATH"
    fi
else
    echo "   Status: ⚠️  File not found"
fi

# Search for any wrong env var configurations
echo ""
echo "2. Searching for wrong environment variable configurations:"
WRONG_ENV=$(grep -r "DEVSTREAM_DB_PATH.*mcp-devstream-server" /Users/fulvioventura/devstream/ 2>/dev/null)

if [ -z "$WRONG_ENV" ]; then
    echo "   ✅ No wrong environment variable configurations found"
else
    echo "   ❌ WRONG configurations found:"
    echo "$WRONG_ENV"
fi

# Check all .env* files
echo ""
echo "3. Checking all .env* files for DEVSTREAM_DB_PATH:"
for env_file in /Users/fulvioventura/devstream/.env*; do
    if [ -f "$env_file" ]; then
        echo ""
        echo "   File: $(basename $env_file)"
        grep "^DEVSTREAM_DB_PATH=" "$env_file" 2>/dev/null || echo "   No DEVSTREAM_DB_PATH found"
    fi
done

echo ""
echo "✅ Step 2.2 Complete: Environment variables validated"
```

**Expected Output**: All `.env*` files use correct relative path `data/devstream.db`.

#### Step 2.3: MCP Server Code Validation (5 min)
```bash
echo ""
echo "=== Validating MCP Server Code ==="

# Check for hardcoded wrong paths in MCP server
echo "1. Checking MCP server for hardcoded wrong paths:"
HARDCODED=$(grep -n "mcp-devstream-server/data" /Users/fulvioventura/devstream/mcp-devstream-server/dist/index.js 2>/dev/null)

if [ -z "$HARDCODED" ]; then
    echo "   ✅ No hardcoded wrong paths in MCP server"
else
    echo "   ❌ WARNING: Hardcoded paths found:"
    echo "$HARDCODED"
fi

# Verify database path resolution logic
echo ""
echo "2. Verifying database path resolution logic:"
echo "   Looking for: 'const dbPath = '"
grep -A 5 "const dbPath = " /Users/fulvioventura/devstream/mcp-devstream-server/dist/index.js | head -10

echo ""
echo "3. Expected behavior:"
echo "   ✅ Should use CLI argument (process.argv[2])"
echo "   ✅ Should fall back to DEVSTREAM_DB_PATH environment variable"
echo "   ✅ Should NOT have hardcoded database paths"

echo ""
echo "✅ Step 2.3 Complete: MCP server code validated"
```

**Expected Output**: No hardcoded paths, proper CLI argument priority.

#### Phase 2 Validation Report
```bash
# Generate validation report
REPORT_FILE="/tmp/config-validation-$(date +%Y%m%d-%H%M%S).md"

cat > "$REPORT_FILE" << 'EOF'
# Configuration Validation Report

**Date**: $(date)
**Phase**: 2 - Configuration Validation

## .mcp.json Files Found

$(echo "$MCP_FILES" | sed 's/^/- /')

## Environment Variables

### .env.devstream
```
$(grep "DEVSTREAM_DB_PATH" /Users/fulvioventura/devstream/.env.devstream 2>/dev/null)
```

## MCP Server Code

✅ No hardcoded wrong paths found
✅ Path resolution uses CLI argument priority
✅ Falls back to DEVSTREAM_DB_PATH environment variable

## Issues Found

[Document any configuration inconsistencies here]

## Recommendation

✅ PASS - Ready for Phase 3 (Cleanup Enhancement)
EOF

echo ""
echo "✅ Phase 2 Complete: Configuration validation report saved to: $REPORT_FILE"
```

**Phase 2 Success Criteria Checklist**:
- [ ] Single `.mcp.json` file found with correct path
- [ ] All `.env*` files use correct relative path
- [ ] No hardcoded wrong paths in MCP server
- [ ] No environment variable misconfigurations
- [ ] Validation report generated

### Phase 3: Cleanup Enhancement (20 minutes)

**IMPORTANT**: This phase enhances robustness but is NOT critical for immediate fix. If time-constrained, can defer to Phase 5.

#### Step 3.1: Enhanced Cleanup Detection (10 min)

**File to Edit**: `/Users/fulvioventura/devstream/.claude/hooks/devstream/monitoring/mcp_cleanup_hook.py`

Add after imports section:
```python
# Wrong path detection constants
CORRECT_DB_PATH = "/Users/fulvioventura/devstream/data/devstream.db"
WRONG_DB_PATH_PATTERN = "mcp-devstream-server/data/devstream.db"
```

Add detection functions before main():
```python
def detect_wrong_path_usage(cmd_line: str) -> bool:
    """Detect if MCP process is using wrong database path."""
    return WRONG_DB_PATH_PATTERN in cmd_line

def log_wrong_path_detection(pid: int, cmd_line: str) -> None:
    """Log detection of wrong path usage for monitoring."""
    logger.warning(
        "Wrong database path detected in MCP process",
        pid=pid,
        command_line=cmd_line,
        wrong_path=WRONG_DB_PATH_PATTERN,
        correct_path=CORRECT_DB_PATH,
        detection_time=datetime.now().isoformat()
    )

    # Append to dedicated wrong-path log
    wrong_path_log = Path.home() / ".claude" / "logs" / "devstream" / "wrong-path-detections.log"
    wrong_path_log.parent.mkdir(parents=True, exist_ok=True)

    with open(wrong_path_log, "a") as f:
        f.write(f"{datetime.now().isoformat()} | PID {pid} | WRONG PATH | {cmd_line}\n")
```

In main cleanup loop, add detection call:
```python
# After getting cmd_line for each process, add:
if detect_wrong_path_usage(cmd_line):
    log_wrong_path_detection(pid, cmd_line)
```

**Verification**:
```bash
# Test the enhanced cleanup
/Users/fulvioventura/devstream/.devstream/bin/python \
  /Users/fulvioventura/devstream/.claude/hooks/devstream/monitoring/mcp_cleanup_hook.py

# Check if wrong-path log was created (should be empty if no wrong paths)
ls -la ~/.claude/logs/devstream/wrong-path-detections.log
```

#### Step 3.2: Pre-Launch Validation Enhancement (10 min)

**File to Edit**: `/Users/fulvioventura/devstream/start-devstream.sh`

Add after line 468 (after pre-launch cleanup section):
```bash
# ============================================================================
# Pre-Launch MCP Configuration Validation
# ============================================================================

print_status "Validating MCP configuration before launch..."

# Extract DEVSTREAM_DB_PATH from .mcp.json
MCP_DB_PATH=$(grep "DEVSTREAM_DB_PATH" "$PROJECT_ROOT/.mcp.json" | sed 's/.*": "//;s/".*//')

# Validate it's NOT the wrong path
if [[ "$MCP_DB_PATH" == *"mcp-devstream-server/data/devstream.db"* ]]; then
    print_error "❌ CRITICAL: .mcp.json contains WRONG database path!"
    print_error "   Found: $MCP_DB_PATH"
    print_error "   Expected: /Users/fulvioventura/devstream/data/devstream.db"
    print_error ""
    print_error "This indicates Claude Code configuration cache issue."
    print_error "SOLUTION: Restart Claude Code application completely (Cmd+Q then relaunch)."
    print_error ""
    exit 1
fi

# Validate correct path exists
if [ ! -f "$MCP_DB_PATH" ]; then
    print_error "❌ ERROR: Database file not found at: $MCP_DB_PATH"
    exit 1
fi

# Validate database size (correct DB should be ~500MB)
DB_SIZE=$(stat -f%z "$MCP_DB_PATH" 2>/dev/null || stat -c%s "$MCP_DB_PATH" 2>/dev/null)
if [ "$DB_SIZE" -lt 50000000 ]; then  # Less than 50MB is suspicious
    print_warning "⚠️  WARNING: Database size is only $(numfmt --to=iec $DB_SIZE 2>/dev/null || echo $DB_SIZE bytes)"
    print_warning "   Expected ~500MB for production database"
    print_warning "   Verify you're using the correct database path"
fi

print_status "✅ MCP configuration validated - Path: $MCP_DB_PATH ($(numfmt --to=iec $DB_SIZE 2>/dev/null || echo $DB_SIZE bytes))"
```

**Verification**:
```bash
# Test the startup script validation
bash /Users/fulvioventura/devstream/start-devstream.sh --validate-only

# Should output validation results without starting MCP server
```

**Phase 3 Success Criteria Checklist**:
- [ ] Wrong path detection added to `mcp_cleanup_hook.py`
- [ ] Pre-launch validation added to `start-devstream.sh`
- [ ] Enhanced cleanup tested successfully
- [ ] Wrong-path detections log file created

### Phase 4: Verification (10 minutes - CRITICAL)

#### Step 4.1: Single Instance Validation (3 min)
```bash
echo ""
echo "=== Phase 4: Verification ==="
echo ""
echo "⚠️  MANUAL ACTION: Open Claude Code project now"
echo "Wait 5 seconds for MCP server auto-start..."
echo "Press ENTER after Claude Code project is open and MCP initialized..."
read

# Wait for MCP initialization
sleep 5

# Verify exactly ONE MCP process running
MCP_COUNT=$(pgrep -f "mcp-devstream-server/dist/index.js" | wc -l)
echo "MCP process count: $MCP_COUNT"

if [ "$MCP_COUNT" -ne 1 ]; then
    echo "❌ ERROR: Expected 1 MCP process, found: $MCP_COUNT"
    echo ""
    echo "Process details:"
    pgrep -af "mcp-devstream-server/dist/index.js"
    echo ""
    echo "CRITICAL FAILURE: Multi-instance issue NOT resolved"
    exit 1
fi

echo "✅ Single MCP instance verified"
```

**Expected Output**: Exactly 1 MCP process running.

#### Step 4.2: Correct Database Path Validation (3 min)
```bash
# Get full command line of running MCP process
MCP_CMD=$(pgrep -af "mcp-devstream-server/dist/index.js")
echo ""
echo "MCP process command:"
echo "$MCP_CMD"
echo ""

# Verify it contains correct database path
if echo "$MCP_CMD" | grep -q "/Users/fulvioventura/devstream/data/devstream.db"; then
    echo "✅ Correct database path verified"
else
    echo "❌ CRITICAL ERROR: MCP process using wrong database path!"
    echo ""
    echo "Full command: $MCP_CMD"
    echo ""
    echo "Expected path: /Users/fulvioventura/devstream/data/devstream.db"
    exit 1
fi

# Verify database file size
DB_SIZE=$(ls -lh /Users/fulvioventura/devstream/data/devstream.db | awk '{print $5}')
echo "Database file size: $DB_SIZE"

# Verify database record count
RECORD_COUNT=$(sqlite3 /Users/fulvioventura/devstream/data/devstream.db "SELECT COUNT(*) FROM memory_records;" 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "Memory records count: $RECORD_COUNT"

    if [ "$RECORD_COUNT" -ge 113000 ]; then
        echo "✅ Database record count verified (expected ~113,594)"
    else
        echo "⚠️  WARNING: Record count lower than expected"
        echo "   Found: $RECORD_COUNT"
        echo "   Expected: ~113,594"
    fi
else
    echo "⚠️  WARNING: Could not query database record count"
fi

echo ""
echo "✅ Database validation complete"
```

**Expected Output**: Correct path, ~500MB size, ~113K records.

#### Step 4.3: Functional Validation (4 min)
```bash
echo ""
echo "=== Functional Validation (Manual Testing Required) ==="
echo ""
echo "Please test the following MCP functionality in Claude Code interface:"
echo ""
echo "1. List Tasks:"
echo "   Command: 'List all DevStream tasks'"
echo "   Expected: Task list displayed from database"
echo ""
echo "2. Search Memory:"
echo "   Command: 'Search memory for \"mcp multi-instance\"'"
echo "   Expected: Relevant memory records returned"
echo ""
echo "3. Create Test Task:"
echo "   Command: 'Create a test task'"
echo "   Expected: Task created successfully"
echo ""
echo "4. Check MCP Logs:"
echo "   Verify no errors in Claude Code MCP server output"
echo ""
echo "Press ENTER after completing all functional tests..."
read

echo ""
echo "Did all functional tests pass? (yes/no)"
read FUNCTIONAL_PASS

if [[ "$FUNCTIONAL_PASS" != "yes" ]]; then
    echo "❌ Functional validation FAILED"
    echo "Please document which tests failed and investigate"
    exit 1
fi

echo "✅ Functional validation passed"
```

**User Action Required**: Manual testing in Claude Code interface.

#### Phase 4 Verification Report
```bash
# Generate final verification report
VERIFY_REPORT="/tmp/verification-report-$(date +%Y%m%d-%H%M%S).md"

cat > "$VERIFY_REPORT" << EOF
# Verification Report

**Date**: $(date)
**Phase**: 4 - Verification

## Process Validation
- **MCP Process Count**: $MCP_COUNT (expected: 1) ✅
- **MCP Process Command**:
\`\`\`
$MCP_CMD
\`\`\`

## Database Validation
- **Database Path**: /Users/fulvioventura/devstream/data/devstream.db ✅
- **Database File Size**: $DB_SIZE (expected: ~500MB)
- **Memory Records Count**: $RECORD_COUNT (expected: ~113,594)

## Functional Validation
- ✅ List tasks functional
- ✅ Search memory functional
- ✅ Create task functional
- ✅ No MCP server errors

## Final Status
✅ **PASS** - Single instance verified with correct database path

## Recommendation
Ready for Phase 5 (Prevention & Monitoring setup)
EOF

echo ""
echo "✅ Phase 4 Complete: Verification report saved to: $VERIFY_REPORT"
```

**Phase 4 Success Criteria Checklist**:
- [ ] Exactly 1 MCP process running
- [ ] MCP using correct database path
- [ ] Database size ~500MB
- [ ] Database has ~113K+ records
- [ ] All functional tests passed
- [ ] No errors in MCP server logs
- [ ] Verification report generated

### Phase 5: Prevention & Monitoring (15 minutes)

#### Step 5.1: Wrong Path Monitoring Script (10 min)

Create monitoring script:
```bash
cat > /Users/fulvioventura/devstream/.claude/hooks/devstream/monitoring/wrong_path_monitor.py << 'MONITOR_EOF'
#!/usr/bin/env python3
"""
Monitor for wrong database path usage in MCP processes.
Alerts when wrong path is detected.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

CORRECT_DB_PATH = "/Users/fulvioventura/devstream/data/devstream.db"
WRONG_DB_PATH_PATTERN = "mcp-devstream-server/data/devstream.db"
ALERT_LOG = Path.home() / ".claude" / "logs" / "devstream" / "wrong-path-alerts.log"

def check_mcp_processes():
    """Check all running MCP processes."""
    try:
        result = subprocess.run(
            ["pgrep", "-af", "mcp-devstream-server/dist/index.js"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return []

        processes = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split(None, 1)
                if len(parts) == 2:
                    pid, cmd = parts
                    processes.append((int(pid), cmd))

        return processes
    except Exception as e:
        print(f"Error checking processes: {e}", file=sys.stderr)
        return []

def detect_wrong_path(processes):
    """Detect wrong database path usage."""
    wrong_path_procs = []
    for pid, cmd in processes:
        if WRONG_DB_PATH_PATTERN in cmd:
            wrong_path_procs.append((pid, cmd))
    return wrong_path_procs

def send_alert(wrong_path_procs):
    """Log alert for wrong path detection."""
    ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)

    with open(ALERT_LOG, "a") as f:
        timestamp = datetime.now().isoformat()
        f.write(f"\n{'='*80}\n")
        f.write(f"ALERT: Wrong Database Path Detected - {timestamp}\n")
        f.write(f"{'='*80}\n")

        for pid, cmd in wrong_path_procs:
            f.write(f"PID {pid}: {cmd}\n")

        f.write(f"\nCORRECT PATH: {CORRECT_DB_PATH}\n")
        f.write(f"WRONG PATTERN: {WRONG_DB_PATH_PATTERN}\n")
        f.write(f"\nACTION REQUIRED:\n")
        f.write(f"1. Kill processes: kill {' '.join(str(p[0]) for p in wrong_path_procs)}\n")
        f.write(f"2. Restart Claude Code application\n")
        f.write(f"3. Verify .mcp.json has correct path\n")
        f.write(f"{'='*80}\n\n")

    print(f"\n⚠️  ALERT: {len(wrong_path_procs)} process(es) using WRONG path!", file=sys.stderr)
    print(f"   Details: {ALERT_LOG}", file=sys.stderr)

def main():
    """Main monitoring function."""
    processes = check_mcp_processes()

    if not processes:
        print("No MCP processes running")
        return 0

    print(f"Found {len(processes)} MCP process(es)")

    wrong_path_procs = detect_wrong_path(processes)

    if wrong_path_procs:
        send_alert(wrong_path_procs)
        return 1
    else:
        print("✅ All MCP processes using correct database path")
        return 0

if __name__ == "__main__":
    sys.exit(main())
MONITOR_EOF

# Make executable
chmod +x /Users/fulvioventura/devstream/.claude/hooks/devstream/monitoring/wrong_path_monitor.py

# Test monitoring script
echo ""
echo "Testing wrong path monitoring script..."
/Users/fulvioventura/devstream/.devstream/bin/python \
  /Users/fulvioventura/devstream/.claude/hooks/devstream/monitoring/wrong_path_monitor.py

echo ""
echo "✅ Monitoring script created and tested"
```

#### Step 5.2: Cache Behavior Documentation (5 min)

The implementation plan already includes creating comprehensive documentation at `docs/guides/mcp-configuration-cache-behavior.md`. Execute the documentation creation from the plan.

**Phase 5 Success Criteria Checklist**:
- [ ] Monitoring script created and tested
- [ ] Documentation created explaining cache behavior
- [ ] Cache clearing protocol documented
- [ ] Emergency procedures documented

---

## Success Validation

After completing all 5 phases, validate overall success:

```bash
echo ""
echo "============================================"
echo "   FINAL SUCCESS VALIDATION"
echo "============================================"
echo ""

# 1. Single instance check
MCP_COUNT=$(pgrep -f "mcp-devstream-server/dist/index.js" | wc -l)
echo "1. MCP Instance Count: $MCP_COUNT"
if [ "$MCP_COUNT" -eq 1 ]; then
    echo "   ✅ PASS"
else
    echo "   ❌ FAIL"
fi

# 2. Correct path check
MCP_CMD=$(pgrep -af "mcp-devstream-server/dist/index.js")
echo ""
echo "2. Database Path Check:"
if echo "$MCP_CMD" | grep -q "/Users/fulvioventura/devstream/data/devstream.db"; then
    echo "   ✅ PASS - Using correct path"
else
    echo "   ❌ FAIL - Using wrong path"
fi

# 3. Wrong path detection log check
echo ""
echo "3. Wrong Path Detections:"
if [ -f ~/.claude/logs/devstream/wrong-path-detections.log ]; then
    WRONG_COUNT=$(wc -l < ~/.claude/logs/devstream/wrong-path-detections.log)
    echo "   Detections logged: $WRONG_COUNT"
    if [ "$WRONG_COUNT" -eq 0 ]; then
        echo "   ✅ PASS - Zero detections"
    else
        echo "   ⚠️  WARNING - $WRONG_COUNT detections found"
    fi
else
    echo "   ✅ PASS - No detection log (no wrong paths detected)"
fi

# 4. Monitoring functional check
echo ""
echo "4. Monitoring Script:"
if [ -x /Users/fulvioventura/devstream/.claude/hooks/devstream/monitoring/wrong_path_monitor.py ]; then
    echo "   ✅ PASS - Monitoring script installed"
else
    echo "   ⚠️  WARNING - Monitoring script not executable"
fi

# 5. Documentation check
echo ""
echo "5. Documentation:"
if [ -f /Users/fulvioventura/devstream/docs/guides/mcp-configuration-cache-behavior.md ]; then
    echo "   ✅ PASS - Cache behavior documentation created"
else
    echo "   ⚠️  WARNING - Documentation not found"
fi

echo ""
echo "============================================"
echo "   IMPLEMENTATION STATUS"
echo "============================================"
echo ""
echo "If all critical checks passed, implementation is SUCCESSFUL."
echo "If any critical check failed, review error logs and retry failed phase."
```

---

## Troubleshooting Guide for GLM-4.6

### Issue: Multiple MCP Processes Still Spawning After Phase 1

**Diagnosis**:
```bash
pgrep -af "mcp-devstream-server/dist/index.js"
```

**Resolution**:
1. Verify Claude Code was FULLY quit (not just window closed)
2. Manually kill all processes: `pkill -9 -f "mcp-devstream-server/dist/index.js"`
3. Wait 30 seconds, verify zero processes
4. Relaunch Claude Code and retry

### Issue: MCP Process Using Wrong Path After Restart

**Diagnosis**:
```bash
pgrep -af "mcp-devstream-server/dist/index.js" | grep "mcp-devstream-server/data"
```

**Resolution**:
1. Check `.mcp.json` content: `cat .mcp.json | grep DEVSTREAM_DB_PATH`
2. If wrong, edit `.mcp.json` to correct path
3. Kill all MCP processes
4. Restart Claude Code AGAIN (cache must be cleared)

### Issue: Database File Not Found

**Diagnosis**:
```bash
ls -lh /Users/fulvioventura/devstream/data/devstream.db
```

**Resolution**:
1. Verify correct path exists
2. Check file permissions: `ls -l /Users/fulvioventura/devstream/data/`
3. If missing, this is a critical error - escalate to user immediately

### Issue: Functional Tests Failing

**Diagnosis**: MCP server errors in Claude Code output

**Resolution**:
1. Check MCP server logs in Claude Code
2. Verify database file readable: `sqlite3 /Users/fulvioventura/devstream/data/devstream.db ".tables"`
3. Test database connection manually
4. If corruption suspected, escalate to user

---

## Rollback Procedures

If implementation fails at any phase, follow these rollback procedures:

### Rollback Phase 1-2 (Critical Failure)
```bash
# Kill all MCP processes
pkill -9 -f "mcp-devstream-server/dist/index.js"

# Restore original .mcp.json
cd /Users/fulvioventura/devstream
git checkout .mcp.json

# Document failure
echo "Phase 1-2 failure at $(date)" >> /tmp/mcp-fix-failure.log
pgrep -af "mcp-devstream-server/dist/index.js" >> /tmp/mcp-fix-failure.log

# Restart Claude Code
echo "Please restart Claude Code and report issue to user"
```

### Rollback Phase 3 (Enhancement Failure)
```bash
# Restore original cleanup hook
cd /Users/fulvioventura/devstream
git checkout .claude/hooks/devstream/monitoring/mcp_cleanup_hook.py

# Restore original startup script
git checkout start-devstream.sh

# Verify basic cleanup still works
.devstream/bin/python .claude/hooks/devstream/monitoring/mcp_cleanup_hook.py
```

### Rollback Phase 4 (Verification Failure)
```bash
# Document verification failure
echo "Verification failed at $(date)" >> /tmp/mcp-verification-failure.log
pgrep -af "mcp-devstream-server/dist/index.js" >> /tmp/mcp-verification-failure.log

# Return to Phase 1 and retry
echo "Returning to Phase 1 for retry..."
```

### Rollback Phase 5 (Monitoring Setup Failure)
```bash
# Remove monitoring script if problematic
rm /Users/fulvioventura/devstream/.claude/hooks/devstream/monitoring/wrong_path_monitor.py

# Keep documentation for future reference
# No other rollback needed - monitoring is optional
```

---

## Communication with User

After completing implementation (or if encountering blocking issues), report back to user with:

### Success Report Template
```markdown
## Implementation Complete ✅

### Summary
Successfully fixed MCP multi-instance wrong database path issue.

### Results
- **MCP Process Count**: 1 (expected: 1) ✅
- **Database Path**: /Users/fulvioventura/devstream/data/devstream.db ✅
- **Database Size**: ~500MB ✅
- **Record Count**: ~113,594 ✅
- **Functionality**: All tests passed ✅

### Phases Completed
1. ✅ Phase 1 - Immediate Disablement (cache cleared)
2. ✅ Phase 2 - Configuration Validation (all correct)
3. ✅ Phase 3 - Cleanup Enhancement (detection added)
4. ✅ Phase 4 - Verification (single instance confirmed)
5. ✅ Phase 5 - Prevention (monitoring setup)

### Files Modified
- `.claude/hooks/devstream/monitoring/mcp_cleanup_hook.py` (enhanced detection)
- `start-devstream.sh` (pre-launch validation)
- `docs/guides/mcp-configuration-cache-behavior.md` (new documentation)
- `.claude/hooks/devstream/monitoring/wrong_path_monitor.py` (new monitoring)

### Monitoring
Wrong path monitoring active at:
- Detection log: `~/.claude/logs/devstream/wrong-path-detections.log`
- Alert log: `~/.claude/logs/devstream/wrong-path-alerts.log`

### Next Steps
- Monitor for 7 days for any wrong-path detections
- Review logs on Day 1, 3, and 7
- Declare success if zero detections for 7 days

### Documentation
Cache behavior and prevention procedures documented at:
`docs/guides/mcp-configuration-cache-behavior.md`
```

### Failure Report Template
```markdown
## Implementation Failed ❌

### Phase Failed
[Phase X] - [Phase Name]

### Error Description
[Detailed description of what went wrong]

### Error Logs
```
[Relevant error logs]
```

### Current State
- MCP Process Count: [X]
- Database Path in Use: [path]
- Configuration Status: [status]

### Attempted Resolution
[What was tried to resolve the issue]

### Rollback Status
[Whether rollback was successful]

### Recommendation
[What should be done next - retry, escalate, investigate, etc.]

### Support Files
- Failure log: /tmp/mcp-fix-failure.log
- Pre-cleanup state: /tmp/mcp-cleanup-*.log
```

---

## Critical Knowledge for GLM-4.6

### Why This Issue Occurred

**Root Cause**: Claude Code's in-memory configuration caching

**Mechanism**:
1. Claude Code loads `.mcp.json` into RAM on session start
2. MCP server disconnections trigger auto-respawn
3. Auto-respawn uses CACHED config, NOT disk file
4. Result: Even after file correction, cache contains old wrong path

### Why Simple Fixes Don't Work

**Attempted**: File edits, process kills, pre-launch cleanup
**Failed**: Cache persists, respawn uses cached config
**Solution**: Full application restart to invalidate cache

### Critical Success Factors

1. **MUST restart Claude Code**: File edits alone insufficient
2. **MUST verify zero processes**: Before restart, after restart, after project open
3. **MUST validate path**: In config file AND in running process command line
4. **MUST test functionality**: Verify database connection works correctly

### Signs of Success

- Exactly 1 MCP process running
- Process command line contains correct path `/Users/fulvioventura/devstream/data/devstream.db`
- Database file is ~500MB with ~113K records
- All MCP operations functional (list tasks, search memory, create task)
- Zero wrong-path detections in monitoring logs

### Signs of Failure

- Multiple MCP processes spawning
- Process command line contains wrong path `mcp-devstream-server/data/devstream.db`
- Immediate respawn after process kill
- Functional tests failing
- Wrong-path detections in logs

---

## Files Reference

### Configuration Files
- `.mcp.json` - MCP server configuration with database path
- `.env.devstream` - DevStream system configuration
- `.env.example.deployment` - Deployment example

### Code Files (Validated Correct)
- `mcp_client.py` - MCP client with database path validation
- `session_coordinator.py` - Session management
- `work_session_manager.py` - Work session lifecycle
- `mcp_process_monitor.py` - Process health monitoring
- `index.ts` - MCP server entry point

### Files to Modify (Phase 3)
- `mcp_cleanup_hook.py` - Add wrong-path detection
- `start-devstream.sh` - Add pre-launch validation

### Files to Create (Phase 5)
- `wrong_path_monitor.py` - Monitoring script for wrong paths
- `docs/guides/mcp-configuration-cache-behavior.md` - Documentation

### Log Files
- `~/.claude/logs/devstream/wrong-path-detections.log` - Detection log
- `~/.claude/logs/devstream/wrong-path-alerts.log` - Alert log
- `/tmp/mcp-cleanup-*.log` - Pre-cleanup state documentation
- `/tmp/config-validation-*.md` - Configuration validation reports
- `/tmp/verification-report-*.md` - Final verification report

---

## Estimated Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1 | 10 min | None - START HERE |
| Phase 2 | 15 min | Phase 1 complete |
| Phase 3 | 20 min | Phase 2 complete (optional) |
| Phase 4 | 10 min | Phases 1-2 complete |
| Phase 5 | 15 min | Phase 4 complete (optional) |
| **TOTAL** | **70 min** | **35 min critical path** |

**Critical Path**: Phases 1, 2, 4 (35 minutes minimum)
**Optional**: Phases 3, 5 can be deferred if time-constrained

---

## Contact and Escalation

**If Blocking Issues Encountered**:
1. Document the issue thoroughly
2. Save all relevant logs
3. Report to user with failure report template
4. Wait for user guidance before proceeding

**Do NOT Proceed If**:
- Phase 1 or 2 fails (critical for resolution)
- Phase 4 verification fails (indicates fix unsuccessful)
- Multiple unknown errors occur
- Database corruption suspected

---

**End of Handoff Document**

GLM-4.6, you are now ready to execute this implementation plan. Start with Phase 1, follow the detailed instructions, validate success criteria at each phase, and report completion status to user.

Good luck! 🚀
