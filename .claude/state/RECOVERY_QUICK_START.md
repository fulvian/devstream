# 🚀 Quick Recovery Guide - Post-Restart

**Last Checkpoint**: 2025-10-02 16:36 UTC
**Commit**: ed57ea3
**Reason**: MCP tools investigation

---

## ⚡ 60-Second Recovery

### 1. Verify Environment (10s)
```bash
cd /Users/fulvioventura/devstream
git branch --show-current  # Expected: release/v0.1.0-beta
cat .claude/state/current_task.json  # Expected: FASE 5.4 complete
```

### 2. Test MCP Tools (20s)
```bash
# Check server
curl -s http://localhost:9090/health

# In Claude session, test tool availability:
mcp__devstream__devstream_list_tasks
```

**Expected**:
- ✅ If tools available → MCP registration works after restart
- ❌ If tools NOT available → Deeper MCP issue (investigate .claude/mcp_servers.json)

### 3. Read Full Context (30s)
```bash
cat .claude/state/session_checkpoint_pre_restart.md
```

---

## 📋 Current Status

**Task**: diagnose-macos-crashes
**Progress**: 18/20 micro-tasks (145/170 min) - 90% complete
**Branch**: release/v0.1.0-beta
**Phase**: FASE 5.4 ✅ → FASE 6.1 ⏳

---

## 🎯 Next Actions (FASE 6)

### FASE 6.1: Security Review (10 min)
```
Delegate to @code-reviewer:
- OWASP Top 10 validation
- Rate limiters prevent DoS
- Input sanitization
- Files: debouncer.py, rate_limiter.py, resource_monitor.py, pre_tool_use.py
```

### FASE 6.2: Performance Review (10 min)
```
Delegate to @code-reviewer:
- Overhead analysis (<1ms measured)
- Total hook latency <10ms
- Memory impact
```

### FASE 6.3: Architecture Review (10 min)
```
Delegate to @code-reviewer:
- SOLID principles
- Type hints coverage
- Docstrings completeness
- Maintainability
```

---

## 🔑 Key Context

### What We Completed (FASE 5.4)
- ✅ 6/6 stress tests passing (100%)
- ✅ Root cause analysis: 3 causes identified
- ✅ ResourceMonitor ACTIVE in production
- ✅ Zero crashes under stress scenarios

### ResourceMonitor Status
- **ACTIVE**: Monitors RAM/CPU/Ollama/Swap every PreToolUse call
- **Action**: CRITICAL → skip_heavy_injection (prevents crashes)
- **Integration**: pre_tool_use.py lines 87-97, 690-719

### Test Results Validated
- Debounce rate: 90% (target: 80%)
- Rate limiting: 10 ops/sec memory, 5 ops/sec Ollama
- Performance: <1ms overhead (target: <10ms)
- Crash prevention: 100% (0 crashes in stress tests)

---

## 📁 Important Files

**State**:
- `.claude/state/current_task.json` - Task progress
- `.claude/state/session_checkpoint_pre_restart.md` - Full context
- `FASE_5.4_ROOT_CAUSE_FIX.md` - Root cause analysis

**Implementation**:
- `.claude/hooks/devstream/utils/debouncer.py` (377 lines)
- `.claude/hooks/devstream/utils/rate_limiter.py` (242 lines)
- `.claude/hooks/devstream/monitoring/resource_monitor.py` (356 lines)

**Tests**:
- `tests/stress/test_crash_prevention.py` (6/6 passed)

---

## 🔧 If MCP Tools Still Missing

### Check 1: MCP Server
```bash
curl -s http://localhost:9090/health
# Expected: {"status":"healthy"}
```

### Check 2: MCP Configuration
```bash
cat .claude/mcp_servers.json
# Check "devstream" entry exists
```

### Check 3: Restart MCP Server
```bash
# Stop server
pkill -f "node.*mcp-devstream-server"

# Start server
cd mcp-devstream-server
node dist/index.js &
```

### Check 4: Claude Code Logs
```bash
# Check for MCP connection errors
tail -50 ~/.claude/logs/main.log | grep -i mcp
```

---

**Created**: 2025-10-02 16:36 UTC
**Ready to Resume**: ✅ YES
**Estimated Time to Complete**: 30 minutes (FASE 6.1-6.3)
