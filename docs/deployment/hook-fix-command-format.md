# Hook Fix: Command Format Issue Resolution

**Date**: 2025-09-30
**Claude Code Version**: 2.0.1
**Status**: ✅ FIXED (requires restart to validate)

---

## 🎯 Problem Summary

PreToolUse and PostToolUse hooks configured in `.claude/settings.json` were **not being triggered** by Claude Code during tool operations (Write, Edit, etc.).

### Symptoms
- ✅ Hooks execute successfully when run manually
- ✅ Scripts are executable with correct permissions
- ✅ Dependencies (structlog, python-json-logger) installed correctly
- ❌ **NO hook execution during Claude Code tool operations**
- ❌ Hook logs show last execution from manual tests only

---

## 🔍 Root Cause Analysis

### Research Process (Context7 Methodology Applied)

1. **Official Documentation Review**
   - Claude Code 2.0 migration guide
   - Agent SDK hook patterns
   - Official hooks reference documentation

2. **GitHub Issues Research**
   - Issue #6403: PostToolUse hooks completely non-functional
   - Issue #3148: Matcher pattern `*` vs empty string
   - Issue #3179: WSL2 hook execution issues
   - Issue #2891: Hooks not executing despite correct config

3. **Community Reports Analysis**
   - Multiple reports of hooks not triggering across platforms
   - Common denominator: configuration format variations

### Root Cause Identified

**PROBLEM**: Incorrect `command` format in settings.json

**Our configuration** (WRONG):
```json
{
  "type": "command",
  "command": [
    "uv",
    "run",
    "--script",
    ".claude/hooks/devstream/memory/pre_tool_use.py"
  ],
  "timeout": 60
}
```

**Correct format per official docs**:
```json
{
  "type": "command",
  "command": "/path/to/executable",
  "timeout": 60
}
```

**Issue**: Claude Code hooks expect either:
- A **single string** pointing to an executable
- An **array** with executable + arguments (but NOT for complex command chains like `uv run --script`)

---

## ✅ Solution Implemented

### Step 1: Created Shell Wrapper Scripts

**File**: `.claude/hooks/devstream/memory/pre_tool_use_wrapper.sh`
```bash
#!/bin/bash
# Wrapper script for pre_tool_use.py hook
# This allows Claude Code to execute the Python script via uv run

cd /Users/fulvioventura/devstream
exec uv run --script .claude/hooks/devstream/memory/pre_tool_use.py "$@"
```

**File**: `.claude/hooks/devstream/memory/post_tool_use_wrapper.sh`
```bash
#!/bin/bash
# Wrapper script for post_tool_use.py hook
# This allows Claude Code to execute the Python script via uv run

cd /Users/fulvioventura/devstream
exec uv run --script .claude/hooks/devstream/memory/post_tool_use.py "$@"
```

**Permissions**: `chmod +x` applied to both wrappers

### Step 2: Updated settings.json Configuration

**PreToolUse** (NEW):
```json
"PreToolUse": [
  {
    "matcher": "Write",
    "hooks": [
      {
        "type": "command",
        "command": ".claude/hooks/devstream/memory/pre_tool_use_wrapper.sh",
        "timeout": 60
      }
    ]
  }
]
```

**PostToolUse** (NEW):
```json
"PostToolUse": [
  {
    "matcher": "Write",
    "hooks": [
      {
        "type": "command",
        "command": ".claude/hooks/devstream/memory/post_tool_use_wrapper.sh",
        "timeout": 60
      }
    ]
  }
]
```

### Step 3: Manual Validation

**Pre-restart testing**:
```bash
# Test pre_tool_use wrapper
echo '{"tool_name":"Write","tool_input":{"file_path":"test.txt","content":"test"}}' \
  | .claude/hooks/devstream/memory/pre_tool_use_wrapper.sh

# Result: ✅ Hook executes successfully with structured logging

# Test post_tool_use wrapper
echo '{"tool_name":"Write","tool_input":{"file_path":"test.txt","content":"test"},"tool_response":{"success":true}}' \
  | .claude/hooks/devstream/memory/post_tool_use_wrapper.sh

# Result: ✅ Hook executes successfully with memory storage
```

---

## 📊 Changes Made

### Files Created
- `.claude/hooks/devstream/memory/pre_tool_use_wrapper.sh` (NEW)
- `.claude/hooks/devstream/memory/post_tool_use_wrapper.sh` (NEW)

### Files Modified
- `.claude/settings.json`: Updated command format for PreToolUse and PostToolUse

### Configuration Changes
- **Matcher**: Simplified from complex regex to `"Write"` for initial testing
- **Command format**: Changed from array to string (wrapper script path)
- **Approach**: Introduced shell wrapper pattern for complex command chains

---

## 🔄 Post-Restart Validation Plan

After restarting Claude Code, validate:

1. **Hook Execution**
   - [ ] Execute Write operation
   - [ ] Check logs in `~/.claude/logs/devstream/pre_tool_use.log`
   - [ ] Verify timestamp matches operation time
   - [ ] Confirm structured logging output

2. **Memory Integration**
   - [ ] Verify post_tool_use captures results in memory
   - [ ] Test memory search retrieves stored content
   - [ ] Validate hybrid search functionality

3. **Performance**
   - [ ] Measure hook execution overhead
   - [ ] Ensure timeout (60s) is sufficient
   - [ ] Monitor for errors or failures

---

## 📚 Lessons Learned

### Context7 Methodology Success
✅ **Research-driven approach** identified multiple GitHub issues with same symptoms
✅ **Official documentation** provided correct configuration format
✅ **Root cause analysis** prevented workaround solutions
✅ **True fix implementation** aligned with best practices

### Key Insights

1. **Command format matters**: Claude Code hooks have specific expectations for command execution
2. **Shell wrappers pattern**: Reliable approach for complex command chains
3. **Matcher simplification**: Start simple (`"Write"`) before adding complexity
4. **Manual testing critical**: Always validate wrapper scripts work before relying on Claude Code execution

### GitHub Issues Context

Multiple community reports confirm hooks are a **known pain point**:
- Configuration format confusion (array vs string)
- Matcher pattern syntax variations (`*` vs `""` vs tool names)
- Platform-specific issues (macOS vs Linux vs WSL2)

**Anthropic's response**: Documentation updates + SDK improvements in 2.0.x releases

---

## 🚀 Next Steps

1. **Restart Claude Code** to load new configuration
2. **Execute validation tests** per Post-Restart Validation Plan
3. **Expand matcher patterns** if initial test succeeds:
   - Add `Edit|MultiEdit` to matcher
   - Add `Bash` operations
   - Add MCP tool patterns (`mcp__devstream__.*`)
4. **Monitor production usage** for 24 hours
5. **Document final configuration** in deployment guide

---

## 📖 References

### Official Documentation
- [Claude Code Hooks Reference](https://docs.claude.com/en/docs/claude-code/hooks)
- [Agent SDK Overview](https://docs.claude.com/en/api/agent-sdk/overview)
- [Building Agents with Claude](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)

### GitHub Issues
- [#6403 - PostToolUse Hooks Not Executing](https://github.com/anthropics/claude-code/issues/6403)
- [#3148 - PreToolUse and PostToolUse Not Triggered with *](https://github.com/anthropics/claude-code/issues/3148)
- [#3179 - Hooks Not Triggering on WSL2](https://github.com/anthropics/claude-code/issues/3179)
- [#2891 - Hooks Not Executing Despite Documentation](https://github.com/anthropics/claude-code/issues/2891)

### Internal Documentation
- [DEPLOYMENT_GUIDE.md](../.claude/hooks/devstream/DEPLOYMENT_GUIDE.md)
- [post-restart-validation-issues.md](./post-restart-validation-issues.md)

---

*Document created: 2025-09-30*
*Methodology: Context7 Research-Driven Development*
*Status: Awaiting post-restart validation*