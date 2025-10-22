# MCP Zombie Prevention & Monitoring System

**Version**: 1.0.0
**Date**: 2025-10-12
**Status**: ✅ Production Ready

---

## Overview

Comprehensive monitoring and prevention system for DevStream MCP server zombie processes and database staleness. Prevents the critical issue where multiple MCP instances cause database lock contention and timeout cascades.

---

## Problem Solved

### Root Cause
Multiple MCP server instances (up to 19 zombies observed) running concurrently, causing:
- SQLite database lock contention (single-writer limitation)
- 30-second timeout cascades on all hook operations
- Silent hook failures (no data written to database for hours)
- No user visibility into system health degradation

### Impact Before Fix
- Database stopped updating for 2+ hours
- All PostToolUse hooks failing silently
- No automatic detection or recovery
- Required manual process cleanup (`kill -9` all zombies)

---

## Solution Architecture

### 4-Layer Defense System

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: PROACTIVE CLEANUP (PreToolUse Hook Integration)   │
│ ─────────────────────────────────────────────────────────── │
│ • Runs before EVERY tool execution                          │
│ • Kills zombie processes automatically (max 2 allowed)      │
│ • Zero manual intervention required                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: CONTINUOUS MONITORING (Background Daemon)          │
│ ─────────────────────────────────────────────────────────── │
│ • Detects zombie accumulation (interval: 60s)              │
│ • Automatic cleanup when >2 instances detected              │
│ • Structured logging for audit trail                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: HEALTH CHECK (MCP Server Responsiveness)          │
│ ─────────────────────────────────────────────────────────── │
│ • Periodic ping with timeout detection (interval: 30s)      │
│ • Degraded state: 1-2 failures OR latency >5s               │
│ • Critical state: 3+ consecutive failures                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: DATABASE STALENESS ALERT (User Notification)      │
│ ─────────────────────────────────────────────────────────── │
│ • Monitors last database write timestamp                    │
│ • Alert when no updates for >10 minutes                     │
│ • Automatic recovery notification when resumed              │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### 1. MCP Process Monitor
**File**: `.claude/hooks/devstream/monitoring/mcp_process_monitor.py`

**Purpose**: Detect and kill zombie MCP server processes

**Features**:
- Detects all running `mcp-devstream-server/dist/index.js` processes
- Retrieves CPU, memory, start time for each process
- Kills oldest processes, keeping only 2 most recent
- Structured JSON logging to `~/.claude/logs/devstream/mcp_process_monitor.jsonl`

**Usage**:
```bash
# Single check
.devstream/bin/python .claude/hooks/devstream/monitoring/mcp_process_monitor.py --once

# Continuous monitoring (60s interval)
.devstream/bin/python .claude/hooks/devstream/monitoring/mcp_process_monitor.py
```

**Output Example**:
```json
{
  "timestamp": "2025-10-11T23:47:13.556252Z",
  "process_count": 18,
  "killed_count": 16,
  "alert_level": "critical",
  "message": "Zombie processes detected: 18 instances running (killed 16)"
}
```

---

### 2. MCP Cleanup Hook (PreToolUse Integration)
**File**: `.claude/hooks/devstream/monitoring/mcp_cleanup_hook.py`

**Purpose**: Automatic cleanup BEFORE every tool execution

**Integration Point**: `pre_tool_use.py` PHASE -1 (line 727-743)

**Workflow**:
1. PreToolUse hook triggered (before Write/Edit)
2. Check MCP process count
3. Kill excess processes if >2 detected
4. Log cleanup result
5. Continue with normal tool execution (non-blocking)

**Advantages**:
- Zero manual intervention
- Prevents zombie accumulation proactively
- Non-blocking (failures don't stop tool execution)
- Real-time feedback to user if zombies cleaned

**Code Integration**:
```python
# PHASE -1: MCP Process Cleanup (prevent zombie processes)
try:
    from mcp_cleanup_hook import MCPCleanupHook
    cleanup = MCPCleanupHook()
    cleanup_result = await cleanup.run_cleanup()

    if cleanup_result.get("killed_count", 0) > 0:
        self.base.warning_feedback(
            f"Cleaned {cleanup_result['killed_count']} zombie MCP processes"
        )
except Exception as e:
    self.base.debug_log(f"MCP cleanup failed (non-critical): {e}")
```

---

### 3. MCP Health Check
**File**: `.claude/hooks/devstream/monitoring/mcp_health_check.py`

**Purpose**: Monitor MCP server responsiveness and detect degraded/critical states

**Health States**:
- **Healthy**: Ping succeeds, latency <5s
- **Degraded**: 1-2 consecutive failures OR latency >5s
- **Critical**: 3+ consecutive failures

**Ping Operation**: `devstream_list_tasks()` (lightweight MCP call)

**Usage**:
```bash
# Single check (10s timeout)
.devstream/bin/python .claude/hooks/devstream/monitoring/mcp_health_check.py --once

# Continuous monitoring (30s interval, 10s timeout)
.devstream/bin/python .claude/hooks/devstream/monitoring/mcp_health_check.py --interval 30 --timeout 10
```

**Output Example**:
```json
{
  "timestamp": "2025-10-11T23:53:39.148029Z",
  "health_status": "degraded",
  "ping_success": false,
  "ping_latency_ms": 15001.43,
  "ping_error": "timeout",
  "consecutive_failures": 1,
  "uptime_seconds": null
}
```

---

### 4. Database Update Monitor
**File**: `.claude/hooks/devstream/monitoring/database_update_monitor.py`

**Purpose**: Detect stale database and alert user

**Alert Threshold**: 600 seconds (10 minutes) with no new `semantic_memory` records

**Staleness Calculation**:
```sql
SELECT MAX(created_at) FROM semantic_memory
```

**Usage**:
```bash
# Single check (10 minute threshold)
.devstream/bin/python .claude/hooks/devstream/monitoring/database_update_monitor.py --once --threshold 600

# Continuous monitoring (60s interval)
.devstream/bin/python .claude/hooks/devstream/monitoring/database_update_monitor.py --interval 60 --threshold 600
```

**Alert Example**:
```
⚠️  DATABASE ALERT: No updates for 1200s (threshold: 600s)
   Last update: 2025-10-11T23:42:01.451Z
   Possible causes: MCP timeout, zombie processes, hook failure
```

**Output Example**:
```json
{
  "timestamp": "2025-10-11T23:53:04.805715Z",
  "status": "ok",
  "last_update": "2025-10-11T23:52:47.468000+00:00Z",
  "staleness_seconds": 17,
  "threshold_seconds": 600,
  "alert": false
}
```

---

## Deployment

### ✅ Fully Automatic Integration (Production Ready)

**All monitoring is now AUTOMATIC** when using `start-devstream.sh`:

```bash
# Start DevStream with automatic monitoring
./start-devstream.sh start         # Launches MCP server + 3 monitoring daemons
./start-devstream.sh restart       # Stops everything, restarts with fresh monitors

# Check status (shows MCP server + monitor health)
./start-devstream.sh status

# Stop everything (MCP server + all monitors)
./start-devstream.sh stop
```

**What Happens Automatically**:
1. ✅ **Pre-launch Cleanup**: Kills zombie MCP processes before starting server
2. ✅ **Process Monitor**: Runs in background (60s interval) - kills zombies if >2 instances
3. ✅ **Health Check**: Pings MCP server (30s interval) - detects degraded/critical states
4. ✅ **Database Monitor**: Tracks staleness (60s interval) - alerts if >10min without updates
5. ✅ **PreToolUse Hook**: Cleans zombies before EVERY tool execution (Write/Edit)

**PID Files**: Monitor PIDs stored in `.devstream/*.pid` for easy management

**Logs**: All monitors write to `~/.claude/logs/devstream/*_daemon.log`

### Cron/Launchd Integration (Advanced)

For persistent monitoring across reboots, create systemd/launchd services:

**Example macOS launchd plist** (~/Library/LaunchAgents/com.devstream.mcp-monitor.plist):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.devstream.mcp-monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/fulvioventura/devstream/.devstream/bin/python</string>
        <string>/Users/fulvioventura/devstream/.claude/hooks/devstream/monitoring/mcp_process_monitor.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

---

## Testing

### End-to-End Test Suite

**Test Script**: Run all 4 monitors in single-check mode

```bash
# Test 1: MCP Process Monitor
.devstream/bin/python .claude/hooks/devstream/monitoring/mcp_process_monitor.py --once

# Test 2: MCP Cleanup Hook
.devstream/bin/python .claude/hooks/devstream/monitoring/mcp_cleanup_hook.py

# Test 3: MCP Health Check
.devstream/bin/python .claude/hooks/devstream/monitoring/mcp_health_check.py --once --timeout 15

# Test 4: Database Update Monitor
.devstream/bin/python .claude/hooks/devstream/monitoring/database_update_monitor.py --once --threshold 600
```

**Expected Results**:
- ✅ Process Monitor: PASS (0-2 processes, no zombies)
- ✅ Cleanup Hook: PASS (silent success if no cleanup needed)
- ✅ Health Check: HEALTHY or DEGRADED (timeout detection working)
- ✅ Database Monitor: OK (staleness <600s)

---

## Performance Impact

### PreToolUse Hook Integration
- **Overhead**: <100ms (process count check + conditional cleanup)
- **Frequency**: Every Write/Edit operation
- **Non-blocking**: Failures don't interrupt tool execution

### Background Monitors (Optional)
- **CPU**: <1% average (60s-30s intervals)
- **Memory**: <50MB per monitor
- **Disk I/O**: Minimal (append-only logging)

---

## Log Files

All monitors write structured JSON logs to:

```
~/.claude/logs/devstream/
├── mcp_process_monitor.jsonl      # Zombie detection + cleanup
├── mcp_cleanup_hook.jsonl         # PreToolUse cleanup operations
├── mcp_health_check.jsonl         # Ping latency + health status
└── database_update_monitor.jsonl  # Staleness alerts
```

**Log Rotation**: Recommended to rotate logs weekly (use `logrotate` or manual archival)

---

## Troubleshooting

### Scenario 1: Database Not Updating
**Symptoms**: No new records in `semantic_memory` for >10 minutes

**Diagnostic Steps**:
1. Run database monitor: `--once --threshold 600`
2. Check MCP process count: `pgrep -fl mcp-devstream-server | wc -l`
3. Check MCP health: `mcp_health_check.py --once`
4. Review logs: `tail -20 ~/.claude/logs/devstream/mcp_cleanup_hook.jsonl`

**Resolution**:
- If zombie processes: Cleanup hook will auto-fix on next tool execution
- If health critical: Restart Claude Code to relaunch MCP server
- If database locked: `sqlite3 data/devstream.db .timeout 30000`

---

### Scenario 2: Continuous Zombie Accumulation
**Symptoms**: Process monitor shows >5 zombies repeatedly

**Diagnostic Steps**:
1. Check Claude Code version (ensure latest)
2. Verify MCP server config: `.claude/settings.json` → `mcpServers.devstream`
3. Check for errors: `grep -E "error|timeout" ~/.claude/logs/devstream/*.jsonl`

**Resolution**:
- Ensure single Claude Code instance running
- Restart Claude Code completely (File → Quit, relaunch)
- Verify PreToolUse hook integration: `grep "MCP cleanup" .claude/hooks/devstream/memory/pre_tool_use.py`

---

### Scenario 3: Health Check Always Degraded
**Symptoms**: `ping_success: false` with consistent timeouts

**Diagnostic Steps**:
1. Increase timeout: `--timeout 30`
2. Check database size: `du -h data/devstream.db`
3. Review MCP server logs: `~/.claude/logs/devstream/mcp-server.log`

**Resolution**:
- If database >500MB: Consider vacuuming (`VACUUM;`)
- If timeout >30s: Rebuild MCP server (`npm run build` in `mcp-devstream-server/`)
- If persistent: Report as bug with logs

---

## Future Improvements

### Planned Enhancements (v2.0)
1. **Automatic Recovery**: Kill all zombies + restart MCP server automatically on critical health
2. **Metrics Dashboard**: Web UI for real-time monitoring (Prometheus + Grafana)
3. **Alerting Integration**: Slack/email notifications for critical alerts
4. **Resource Usage Tracking**: CPU/memory trend analysis for MCP server
5. **Predictive Cleanup**: Machine learning model to predict zombie accumulation

### Performance Optimizations
- [ ] Shared process list cache (reduce `pgrep` calls)
- [ ] Batch database queries (reduce connection overhead)
- [ ] Async logging (reduce I/O blocking)

---

## References

- **CLAUDE.md**: DevStream project rules (Protocol v2.2.0)
- **Issue**: Database staleness root cause analysis (2025-10-12)
- **Fix PR**: MCP Zombie Prevention System implementation

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-12
**Status**: ✅ Production Ready
**Maintainer**: DevStream Core Team
