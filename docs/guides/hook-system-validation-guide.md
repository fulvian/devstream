# Hook System V2.0 - Validation Guide

**Created**: 2025-09-30
**Purpose**: Quick reference per testing hook system dopo restart

---

## 🚀 Pre-Restart Checklist

✅ **Tutti completati**:
- [x] Venv `.devstream` con Python 3.11.13
- [x] Dipendenze installate (cchooks, aiohttp, structlog)
- [x] `.claude/settings.json` aggiornato (usa `.devstream/bin/python`)
- [x] Stop hook rinominato in `SessionEnd`
- [x] Script di validazione creato ed eseguito

---

## 🧪 Post-Restart: Validation Tests

### Test 1: SessionStart Hook ✅
**Trigger**: Automatico all'avvio sessione

**Expected Output**:
```html
<session-start-hook>
# 📁 DevStream Project
...
</session-start-hook>
```

**Verification**:
```bash
tail -10 ~/.claude/logs/devstream/session_start.log
# Look for timestamp AFTER restart
```

---

### Test 2: PreToolUse + PostToolUse Hooks

**Prompt**:
```
Create a file called test_validation.py with a simple hello world function
```

**Expected Behavior**:
1. ✅ PreToolUse hook executes BEFORE file creation
2. ✅ File created successfully
3. ✅ PostToolUse hook executes AFTER file creation
4. ✅ Content stored in memory

**Verification Commands**:
```bash
# Check PreToolUse log
tail -20 ~/.claude/logs/devstream/pre_tool_use.log
# Look for: "Hook execution started" with recent timestamp

# Check PostToolUse log
tail -20 ~/.claude/logs/devstream/post_tool_use.log
# Look for: "Captured Write result in memory"

# Check memory storage
sqlite3 /Users/fulvioventura/devstream/data/devstream.db \
  "SELECT id, content_type, created_at, substr(content, 1, 80)
   FROM semantic_memory
   WHERE content LIKE '%test_validation%'
   ORDER BY created_at DESC
   LIMIT 1;"
```

**Success Criteria**:
- ✅ Both logs have entries with NEW timestamps (after restart)
- ✅ Database has entry for test_validation.py
- ✅ No errors in log files

---

### Test 3: UserPromptSubmit Hook + Context7

**Prompt**:
```
How do I implement data fetching with React Query? I want to understand query invalidation and cache management.
```

**Expected Behavior**:
1. ✅ UserPromptSubmit hook detects "React Query"
2. ✅ Context7 auto-triggered for documentation
3. ✅ Response includes research-backed best practices
4. ✅ Query stored in memory

**Verification Commands**:
```bash
# Check UserPromptSubmit log
tail -50 ~/.claude/logs/devstream/user_query_context_enhancer.log | grep -A 5 "React Query"

# Check MCP calls
tail -50 ~/.claude/logs/devstream/mcp_client.jsonl | grep "context7"

# Check memory storage
sqlite3 /Users/fulvioventura/devstream/data/devstream.db \
  "SELECT content FROM semantic_memory
   WHERE content LIKE '%React Query%'
   ORDER BY created_at DESC
   LIMIT 1;"
```

**Success Criteria**:
- ✅ Context7 libraries resolved (check log for `resolve-library-id`)
- ✅ Documentation retrieved (check for `get-library-docs`)
- ✅ User query stored in memory

---

### Test 4: SessionEnd Hook (Stop)

**Command**:
```
/stop
```

**Expected Output**:
```html
<stop-hook>
📊 Session Summary
- Duration: X minutes
- Tasks: X
- Memory Entries: X
</stop-hook>

Session terminata.
```

**Verification**:
```bash
# After restart, check if stop hook ran
tail -20 ~/.claude/logs/devstream/stop.log
# Should have entry with session summary
```

**Success Criteria**:
- ✅ Session summary displayed to user
- ✅ Summary stored in memory
- ✅ Log entry with metrics

---

## 📊 Validation Results Template

Copy questo template e compila dopo i test:

```markdown
## Hook System V2.0 - Post-Restart Validation Results

**Date**: 2025-09-30
**Restart Time**: [HH:MM]
**Session ID**: [session-id]

### Test Results

| Test | Status | Log Timestamp | Memory Entry | Notes |
|------|--------|---------------|--------------|-------|
| SessionStart | ⬜ | | N/A | |
| PreToolUse | ⬜ | | ⬜ | |
| PostToolUse | ⬜ | | ⬜ | |
| UserPromptSubmit | ⬜ | | ⬜ | |
| SessionEnd | ⬜ | | ⬜ | |

### Overall Assessment

**Success Rate**: ___/5 (___%)

**Issues Found**:
- [ ] None
- [ ] [Describe issue if any]

**Status**:
- [ ] ✅ All hooks working
- [ ] ⚠️ Partial functionality
- [ ] ❌ Critical issues

### Next Actions

1. [ ] [Action item if needed]
2. [ ] [Action item if needed]
```

---

## 🔍 Troubleshooting

### Issue: PreToolUse/PostToolUse not executing

**Symptoms**:
- No new log entries after restart
- No memory storage for created files

**Diagnosis**:
```bash
# Test hook manually
.devstream/bin/python .claude/hooks/devstream/memory/pre_tool_use.py <<< '{
  "session_id": "manual-test",
  "transcript_path": "/tmp/test.jsonl",
  "cwd": "/Users/fulvioventura/devstream",
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {"file_path": "manual_test.txt", "content": "test"}
}'
```

**Expected**: Hook executes, may show MCP warning (normal)

**If fails**: Check dependencies again
```bash
.devstream/bin/python -m pip list | grep -E "(cchooks|aiohttp)"
```

---

### Issue: UserPromptSubmit not triggering Context7

**Symptoms**:
- No Context7 MCP calls in logs
- Responses don't include external documentation

**Diagnosis**:
```bash
# Check MCP client logs
tail -100 ~/.claude/logs/devstream/mcp_client.jsonl | grep "context7"
```

**Possible Causes**:
1. Context7 MCP server not running
2. Technology keyword not detected in query
3. MCP client configuration issue

**Solution**: Verify Context7 in Claude Code settings

---

### Issue: SessionEnd hook not executing

**Symptoms**:
- No stop-hook output when running `/stop`
- No session summary

**Diagnosis**:
```bash
# Check settings.json
cat .claude/settings.json | grep -A 5 "SessionEnd"
```

**Verify**:
- Hook configured as `SessionEnd` (not `Stop`)
- Command uses `.devstream/bin/python`
- Script path is correct

---

## 📈 Performance Benchmarks

**Expected Hook Performance**:

| Hook | Typical Execution | Max Acceptable |
|------|------------------|----------------|
| SessionStart | 50-200ms | 500ms |
| UserPromptSubmit | 500-2000ms | 5000ms |
| PreToolUse | 100-500ms | 2000ms |
| PostToolUse | 50-200ms | 1000ms |
| SessionEnd | 200-1000ms | 3000ms |

**If exceeding max**: Check MCP server response times in logs

---

## 🎯 Success Criteria Summary

**Minimum for Production**:
- ✅ SessionStart: 100% working
- ✅ PreToolUse: 90%+ execution rate
- ✅ PostToolUse: 90%+ execution rate
- ✅ UserPromptSubmit: 85%+ execution rate
- ⚠️ SessionEnd: 80%+ execution rate (lower priority)

**Current Status** (pre-restart):
- SessionStart: ✅ 100%
- PreToolUse: ❌ 0% → Expected ✅ 95%+
- PostToolUse: ❌ 0% → Expected ✅ 95%+
- UserPromptSubmit: ✅ 100%
- SessionEnd: ❌ 0% → Expected ✅ 90%+

**Target Overall**: **96%+ Success Rate** 🚀

---

## 📝 Additional Resources

- **Full Analysis Report**: `docs/deployment/hook-system-v2-analysis-report.md`
- **Hook System Docs**: `.claude/hooks/devstream/README.md` (if exists)
- **cchooks Documentation**: https://pypi.org/project/cchooks/

---

**Generated**: 2025-09-30T11:15:00Z
**Ready for Testing**: ✅ YES