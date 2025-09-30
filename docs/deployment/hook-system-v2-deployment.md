# DevStream Hook System V2.0 - Deployment Guide

**Date**: 2025-09-30
**Version**: 2.0.0
**Status**: ✅ PRODUCTION READY

---

## 📋 Pre-Deployment Checklist

### ✅ Completed
- [x] All 5 hooks implemented with cchooks
- [x] Configuration updated (array format)
- [x] File permissions set (chmod +x)
- [x] JSON configuration validated
- [x] Memory storage tested
- [x] Documentation complete
- [x] Validation report stored in DevStream memory

### ⚠️ Required Before Deployment
- [ ] Claude Code restart required for settings.json changes
- [ ] Verify MCP server is running (`./start-devstream.sh status`)
- [ ] Confirm .env.devstream configuration
- [ ] Backup current settings.json (if modified)

---

## 🚀 Deployment Steps

### Step 1: Verify Current State

```bash
# Check git status
git status

# Expected changes:
# - .claude/hooks/devstream/memory/pre_tool_use.py (modified)
# - .claude/hooks/devstream/memory/post_tool_use.py (modified)
# - .claude/hooks/devstream/context/user_query_context_enhancer.py (modified)
# - .claude/hooks/devstream/context/project_context.py (modified)
# - .claude/hooks/devstream/tasks/stop.py (modified)
# - .claude/settings.json (modified)
# - docs/development/phase-b-c-validation-report.md (new)
```

### Step 2: Verify MCP Server Status

```bash
# Check MCP server is running
./start-devstream.sh status

# Expected output:
# ✅ MCP Server is running (PID: XXXXX)
# ✅ DevStream database accessible
```

### Step 3: Verify Hook Files

```bash
# Verify all hooks are executable
ls -la .claude/hooks/devstream/memory/*.py
ls -la .claude/hooks/devstream/context/*.py
ls -la .claude/hooks/devstream/tasks/*.py

# All files should have 'x' permission: -rwxr-xr-x
```

### Step 4: Validate Configuration

```bash
# Validate settings.json syntax
python3 -m json.tool < .claude/settings.json > /dev/null && echo "✅ Valid JSON"

# Check hook configuration
grep -A 10 "PreToolUse\|PostToolUse\|UserPromptSubmit\|SessionStart\|Stop" .claude/settings.json
```

### Step 5: Test Environment Configuration

```bash
# Verify .env.devstream exists
test -f .env.devstream && echo "✅ Environment config found"

# Check critical settings
grep "DEVSTREAM_HOOKS_ENABLED" .env.devstream
grep "DEVSTREAM_FEEDBACK_LEVEL" .env.devstream
```

### Step 6: Restart Claude Code

**CRITICAL**: Claude Code must be restarted for settings.json changes to take effect.

```bash
# Close Claude Code completely
# Then restart from terminal or IDE
```

### Step 7: Verify Hook Execution

After restart, perform a test operation:

```bash
# Create a test file to trigger PreToolUse and PostToolUse
echo "# Test hook execution" > /tmp/hook_deployment_test.txt
```

Expected behavior:
- PreToolUse should inject context (if relevant)
- PostToolUse should store in memory
- No blocking errors
- Minimal user feedback (if enabled)

### Step 8: Monitor Initial Operations

Watch for:
- Hook execution time (should be < 30s)
- Memory storage success
- Context7 integration (if triggered)
- Any non-blocking warnings

---

## 🔧 Configuration Reference

### settings.json Structure

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": ["uv", "run", "--script",
          "$CLAUDE_PROJECT_DIR/.claude/hooks/devstream/context/user_query_context_enhancer.py"],
        "timeout": 30
      }]
    }],
    "PreToolUse": [{
      "matcher": "Write|Edit|MultiEdit",
      "hooks": [{
        "type": "command",
        "command": ["uv", "run", "--script",
          "$CLAUDE_PROJECT_DIR/.claude/hooks/devstream/memory/pre_tool_use.py"],
        "timeout": 30
      }]
    }],
    "PostToolUse": [{
      "matcher": "Write|Edit|MultiEdit",
      "hooks": [{
        "type": "command",
        "command": ["uv", "run", "--script",
          "$CLAUDE_PROJECT_DIR/.claude/hooks/devstream/memory/post_tool_use.py"],
        "timeout": 30
      }]
    }],
    "SessionStart": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": ["uv", "run", "--script",
          "$CLAUDE_PROJECT_DIR/.claude/hooks/devstream/context/project_context.py"],
        "timeout": 30
      }]
    }],
    "Stop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": ["uv", "run", "--script",
          "$CLAUDE_PROJECT_DIR/.claude/hooks/devstream/tasks/stop.py"],
        "timeout": 30
      }]
    }]
  }
}
```

### .env.devstream Key Settings

```bash
# Global enable/disable
DEVSTREAM_HOOKS_ENABLED=true

# Feedback level (silent|minimal|verbose)
DEVSTREAM_FEEDBACK_LEVEL=minimal

# Fallback mode (graceful|strict)
DEVSTREAM_FALLBACK_MODE=graceful

# Debug logging
DEVSTREAM_DEBUG=false

# Context7 integration
DEVSTREAM_CONTEXT7_ENABLED=true
DEVSTREAM_CONTEXT7_TOKEN_LIMIT=2000

# Memory operations
DEVSTREAM_MEMORY_SEARCH_ENABLED=true
DEVSTREAM_MEMORY_STORE_ENABLED=true
```

---

## 🐛 Troubleshooting

### Issue: Hooks Not Executing

**Symptoms**: No hook feedback, operations complete without enhancement

**Solutions**:
1. Verify Claude Code was restarted after settings.json changes
2. Check MCP server is running: `./start-devstream.sh status`
3. Verify hook files are executable: `ls -la .claude/hooks/devstream/**/*.py`
4. Check .env.devstream: `DEVSTREAM_HOOKS_ENABLED=true`

### Issue: Hook Timeout Errors

**Symptoms**: "Hook execution timeout" warnings

**Solutions**:
1. Check MCP server responsiveness
2. Increase timeout in settings.json (currently 30s)
3. Enable debug mode: `DEVSTREAM_DEBUG=true` in .env.devstream
4. Check network connectivity (for Context7 calls)

### Issue: Memory Storage Failures

**Symptoms**: "Memory storage unavailable" warnings

**Solutions**:
1. Verify MCP server is running
2. Check database file exists: `ls -la data/devstream.db`
3. Test MCP connection: `python3 tests/standalone/test_mcp_server.py`
4. Check disk space availability

### Issue: Context7 Not Triggering

**Symptoms**: No library documentation in context

**Solutions**:
1. Verify Context7 enabled: `DEVSTREAM_CONTEXT7_ENABLED=true`
2. Check trigger patterns in user query/file content
3. Enable debug logs to see trigger detection
4. Verify Context7 MCP server is accessible

---

## 📊 Monitoring & Observability

### Key Metrics to Track

1. **Hook Execution Time**
   - Target: < 30 seconds
   - Monitor: Check feedback messages
   - Alert: If consistently > 25 seconds

2. **Memory Storage Success Rate**
   - Target: > 95%
   - Monitor: Count success vs failure messages
   - Alert: If < 90%

3. **Context7 Integration Rate**
   - Target: Triggers on relevant queries
   - Monitor: Count Context7 docs injections
   - Optimize: Refine trigger patterns

4. **User Feedback Volume**
   - Target: Minimal, non-invasive
   - Monitor: User complaints about noise
   - Adjust: Feedback level in .env.devstream

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# In .env.devstream
DEVSTREAM_DEBUG=true
DEVSTREAM_FEEDBACK_LEVEL=verbose
```

Check logs:
- Hook execution details
- MCP call traces
- Context7 trigger detection
- Memory storage operations

---

## 🔄 Rollback Procedure

If issues occur, rollback to previous version:

### Quick Rollback

```bash
# 1. Stop Claude Code

# 2. Restore previous settings.json
git checkout HEAD~1 .claude/settings.json

# 3. Restore previous hook files
git checkout HEAD~1 .claude/hooks/devstream/

# 4. Restart Claude Code
```

### Selective Rollback (Disable Specific Hooks)

```bash
# Disable specific hook in .env.devstream
DEVSTREAM_HOOK_PRETOOLUSE=false
DEVSTREAM_HOOK_POSTTOOLUSE=false
# etc.

# Restart Claude Code for changes to take effect
```

---

## 🎯 Success Criteria

Hook system is successfully deployed when:

- ✅ All 5 hooks execute without blocking errors
- ✅ Hook execution time < 30 seconds
- ✅ Memory storage successful for file operations
- ✅ Context7 triggers on relevant queries
- ✅ User feedback minimal and non-invasive
- ✅ No Claude Code operation is blocked
- ✅ Session initialization includes project context

---

## 📝 Post-Deployment Tasks

### Immediate (Day 1)
- [ ] Monitor first 10 Write/Edit operations
- [ ] Verify memory storage success rate
- [ ] Check hook execution times
- [ ] Collect initial user feedback

### Short-Term (Week 1)
- [ ] Analyze Context7 trigger effectiveness
- [ ] Tune memory search relevance
- [ ] Optimize hook performance if needed
- [ ] Document any issues encountered

### Long-Term (Month 1)
- [ ] Evaluate overall system effectiveness
- [ ] Plan Phase 2 enhancements
- [ ] Collect usage statistics
- [ ] Refine configuration based on data

---

## 🔗 References

- **Validation Report**: `docs/development/phase-b-c-validation-report.md`
- **Implementation Docs**: `docs/development/hook-system-v2-phase-a-complete.md`
- **Architecture**: `docs/architecture/hook-system-design.md`
- **MCP Server**: `./start-devstream.sh`
- **Environment Config**: `.env.devstream`

---

## 💡 Tips & Best Practices

1. **Always restart Claude Code** after settings.json changes
2. **Monitor feedback level** - adjust if too noisy
3. **Enable debug mode** only for troubleshooting
4. **Check MCP server status** if hooks fail
5. **Test with simple operations** first (Write to /tmp)
6. **Gradually enable hooks** if unsure (disable some initially)
7. **Backup settings.json** before major changes
8. **Use validation script** to verify configuration

---

**Deployment Status**: ✅ READY
**Next Action**: Restart Claude Code and monitor
**Support**: Check DevStream memory for troubleshooting guides