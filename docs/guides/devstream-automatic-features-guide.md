# DevStream Automatic Features Guide

**Version**: 1.0
**Date**: 2025-09-30
**Status**: Production Ready

---

## 📋 Overview

DevStream provides **automatic memory storage and context injection** for Claude Code sessions. This guide explains how the system works, how to configure it, and how to troubleshoot issues.

### What's Automatic?

1. **📝 Memory Registration** - Code, documentation, and context automatically stored
2. **💡 Context Injection** - Relevant context automatically injected into prompts
3. **🔍 Library Detection** - Context7 automatically retrieves documentation
4. **🎯 Query Enhancement** - User queries automatically enhanced with project context
5. **🔄 Cross-Session Memory** - Knowledge persists across Claude Code sessions

---

## 🎯 Feature 1: Automatic Memory Registration

### How It Works

The **PostToolUse hook** automatically captures and stores:
- Code written during sessions
- Documentation created
- Project context and decisions
- Tool outputs and results
- Error messages and resolutions

### What Gets Stored?

**Content Types**:
- `code` - Source code files
- `documentation` - Markdown and docs
- `context` - Project context and decisions
- `output` - Tool execution results
- `error` - Error messages and fixes
- `decision` - Architecture decisions
- `learning` - Lessons learned

**Storage Format**:
```json
{
  "content": "The actual content (code, docs, etc.)",
  "content_type": "code",
  "keywords": ["python", "testing", "devstream"],
  "created_at": "2025-09-30T14:00:00Z"
}
```

### Embedding Generation

DevStream automatically generates **vector embeddings** for semantic search:
- Uses SQLite-vec for efficient vector storage
- Embeddings enable semantic similarity search
- Combined with keyword search for hybrid results

### Example: Code Storage

**What You Do**:
```python
# Write code in Claude Code
def calculate_total(items):
    return sum(item.price for item in items)
```

**What Happens Automatically**:
1. PostToolUse hook detects file write
2. Content extracted and previewed
3. Stored in semantic_memory table
4. Vector embedding generated
5. Keywords extracted automatically
6. Available for future context injection

---

## 💡 Feature 2: Automatic Context Injection

### How It Works

The **PreToolUse hook** automatically injects relevant context when you:
- Write code that uses libraries
- Ask questions about the project
- Work on related features
- Need documentation reference

### Context Sources

**Priority Order**:
1. **Context7 Documentation** (highest priority)
   - Official library documentation
   - Code examples and patterns
   - Best practices

2. **DevStream Memory** (medium priority)
   - Project-specific code
   - Previous decisions
   - Lessons learned

3. **Project Context** (lowest priority)
   - Current file context
   - Related files
   - Project structure

### Example: Library Usage

**What You Type**:
```python
# I want to test async functions with pytest
```

**What Happens Automatically**:
1. PreToolUse hook detects "pytest" keyword
2. Context7 searches for pytest documentation
3. DevStream memory searches for related tests
4. Hybrid context assembled
5. Injected into Claude's context window
6. You get better, more accurate responses

---

## 🔍 Feature 3: Context7 Library Detection

### Automatic Library Recognition

Context7 automatically detects when you're working with libraries:

**Triggers**:
- Import statements (`import numpy as np`)
- Library mentions in queries (`how to use FastAPI`)
- Code patterns (async/await, decorators)
- Documentation requests

**Libraries Supported**:
- Python: pytest, FastAPI, numpy, pandas, etc.
- JavaScript: React, Next.js, Express, etc.
- And many more via Context7 MCP server

### Example: Automatic Documentation

**Scenario**: You're writing pytest tests

```python
import pytest
import asyncio

# Context7 automatically detected "pytest"
# Documentation injected:
# - pytest.mark.asyncio usage
# - Async test patterns
# - Fixture best practices
```

**Result**: Claude provides pytest-specific guidance without you asking!

---

## 🎯 Feature 4: Query Enhancement

### How It Works

The **UserPromptSubmit hook** enhances your queries with:
- Project-specific context
- Recent code changes
- Relevant decisions
- Related memories

### Example: Enhanced Query

**What You Ask**:
```
How should I structure the new API endpoint?
```

**What Gets Enhanced**:
```
[PROJECT CONTEXT]
- Current architecture: FastAPI with async patterns
- Recent decisions: RESTful design, Pydantic validation
- Related code: /api/routes/users.py, /models/schemas.py

[QUESTION]
How should I structure the new API endpoint?
```

**Result**: Context-aware response specific to YOUR project!

---

## 🔄 Feature 5: Cross-Session Memory

### Persistence Across Sessions

DevStream maintains memory across Claude Code restarts:

**What Persists**:
- All code written
- Documentation created
- Decisions made
- Lessons learned
- Error resolutions

**Database Storage**:
- SQLite database at `data/devstream.db`
- Automatic backups
- Vector embeddings preserved
- Hybrid search indices maintained

### Example: Session Continuity

**Session 1** (Morning):
```python
# You implement hybrid search
class HybridSearch:
    def search(self, query, limit=10):
        # Implementation...
```

**Session 2** (Afternoon):
```
User: "How did we implement search?"
Claude: [Automatically retrieves from memory]
"You implemented HybridSearch class with RRF algorithm..."
```

---

## ⚙️ Configuration

### Environment Variables

Configure DevStream via `.env.devstream`:

```bash
# Memory System
DEVSTREAM_MEMORY_ENABLED=true           # Enable/disable memory storage
DEVSTREAM_MEMORY_FEEDBACK_LEVEL=minimal # none | minimal | detailed

# Context7 Integration
DEVSTREAM_CONTEXT7_ENABLED=true         # Enable/disable Context7
DEVSTREAM_CONTEXT7_AUTO_DETECT=true     # Automatic library detection
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=5000    # Max tokens for C7 docs

# Context Injection
DEVSTREAM_CONTEXT_INJECTION_ENABLED=true  # Enable/disable injection
DEVSTREAM_CONTEXT_MAX_TOKENS=2000         # Max tokens for context
DEVSTREAM_CONTEXT_RELEVANCE_THRESHOLD=0.5 # Min relevance score

# Database
DEVSTREAM_DB_PATH=/path/to/devstream.db  # Database location

# Logging
DEVSTREAM_LOG_LEVEL=INFO                 # DEBUG | INFO | WARNING | ERROR
DEVSTREAM_LOG_PATH=~/.claude/logs/devstream/
```

### Per-Feature Control

**Disable Memory Storage**:
```bash
DEVSTREAM_MEMORY_ENABLED=false
```

**Disable Context7**:
```bash
DEVSTREAM_CONTEXT7_ENABLED=false
```

**Disable All Automatic Features**:
```bash
DEVSTREAM_MEMORY_ENABLED=false
DEVSTREAM_CONTEXT7_ENABLED=false
DEVSTREAM_CONTEXT_INJECTION_ENABLED=false
```

### Feedback Levels

**none**: No feedback shown
```bash
DEVSTREAM_MEMORY_FEEDBACK_LEVEL=none
# Silent operation
```

**minimal**: Basic feedback (default)
```bash
DEVSTREAM_MEMORY_FEEDBACK_LEVEL=minimal
# Shows: "✅ Memory stored", "🔍 Context injected"
```

**detailed**: Full feedback
```bash
DEVSTREAM_MEMORY_FEEDBACK_LEVEL=detailed
# Shows: Full details of operations, timings, search results
```

---

## 🔧 Performance Tuning

### Token Budget Management

**Context7 Token Budget**:
```bash
# More documentation, slower responses
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=10000

# Less documentation, faster responses (recommended)
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=5000

# Minimal documentation, fastest
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=2000
```

**Context Injection Budget**:
```bash
# More context, larger prompt
DEVSTREAM_CONTEXT_MAX_TOKENS=5000

# Balanced (recommended)
DEVSTREAM_CONTEXT_MAX_TOKENS=2000

# Minimal context
DEVSTREAM_CONTEXT_MAX_TOKENS=1000
```

### Relevance Threshold

Control which memories get injected:

```bash
# Higher threshold = only highly relevant (faster)
DEVSTREAM_CONTEXT_RELEVANCE_THRESHOLD=0.7

# Balanced (recommended)
DEVSTREAM_CONTEXT_RELEVANCE_THRESHOLD=0.5

# Lower threshold = more memories (slower)
DEVSTREAM_CONTEXT_RELEVANCE_THRESHOLD=0.3
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Memory Not Being Stored

**Symptoms**: Code written but not appearing in searches

**Solutions**:
```bash
# Check memory enabled
cat .env.devstream | grep DEVSTREAM_MEMORY_ENABLED
# Should be: DEVSTREAM_MEMORY_ENABLED=true

# Check MCP server running
ps aux | grep mcp-devstream-server
# Should show running process

# Check database exists
ls -la data/devstream.db
# Should exist and have recent modification time

# Check logs
tail -50 ~/.claude/logs/devstream/memory.log
```

#### 2. Context7 Not Working

**Symptoms**: No library documentation in responses

**Solutions**:
```bash
# Check Context7 enabled
cat .env.devstream | grep DEVSTREAM_CONTEXT7_ENABLED
# Should be: DEVSTREAM_CONTEXT7_ENABLED=true

# Check Context7 MCP server configured
cat ~/.claude/mcp_servers.json | grep context7
# Should show context7 configuration

# Test Context7 manually
# In Claude Code: "Show me pytest documentation"
# Should trigger Context7 retrieval
```

#### 3. Slow Performance

**Symptoms**: Claude Code slow to respond

**Solutions**:
```bash
# Reduce token budgets
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=2000
DEVSTREAM_CONTEXT_MAX_TOKENS=1000

# Increase relevance threshold
DEVSTREAM_CONTEXT_RELEVANCE_THRESHOLD=0.7

# Disable features temporarily
DEVSTREAM_CONTEXT7_ENABLED=false

# Check database size
du -h data/devstream.db
# If > 100MB, consider archiving old memories
```

#### 4. Hooks Not Executing

**Symptoms**: No automatic behavior at all

**Solutions**:
```bash
# Check hook system enabled
cat .claude/settings.json | grep -A 10 "hooks"
# Should show PreToolUse, PostToolUse, UserPromptSubmit

# Verify Python environment
.devstream/bin/python --version
# Should be Python 3.11.x

# Check hook dependencies
.devstream/bin/python -m pip list | grep -E "(cchooks|aiohttp|structlog)"
# All should be installed

# Test hook manually
.devstream/bin/python .claude/hooks/devstream/memory/pre_tool_use.py
# Should execute without errors
```

---

## 📊 Monitoring

### Check System Status

**Memory Statistics**:
```bash
# Count total memories
sqlite3 data/devstream.db "SELECT COUNT(*) FROM semantic_memory;"

# View recent memories
sqlite3 data/devstream.db "SELECT content_type, substr(content,1,50), created_at
  FROM semantic_memory ORDER BY created_at DESC LIMIT 10;"

# Check memory by type
sqlite3 data/devstream.db "SELECT content_type, COUNT(*)
  FROM semantic_memory GROUP BY content_type;"
```

**MCP Server Status**:
```bash
# Check server running
ps aux | grep mcp-devstream-server

# Check server logs
tail -100 ~/.claude/logs/mcp-devstream.log

# Test server connectivity
curl http://localhost:3000/health
# Should return: {"status":"healthy"}
```

**Hook Execution Logs**:
```bash
# PreToolUse logs
tail -50 ~/.claude/logs/devstream/pre_tool_use.log

# PostToolUse logs
tail -50 ~/.claude/logs/devstream/post_tool_use.log

# UserPromptSubmit logs
tail -50 ~/.claude/logs/devstream/user_prompt_submit.log
```

---

## 🔒 Privacy & Data

### What Gets Stored

**Stored Automatically**:
- Code you write during sessions
- Documentation you create
- Queries you make to Claude
- Tool outputs (file contents, command results)
- Project context

**NOT Stored**:
- Passwords or secrets (automatically filtered)
- Personal information
- External API keys
- Contents of `.gitignore` files

### Data Location

**All data stored locally**:
- Database: `data/devstream.db`
- Logs: `~/.claude/logs/devstream/`
- No cloud sync
- No external transmission
- Full control over your data

### Data Management

**View Your Data**:
```bash
# Browse all memories
sqlite3 data/devstream.db "SELECT * FROM semantic_memory;"
```

**Export Your Data**:
```bash
# Export to JSON
sqlite3 data/devstream.db ".mode json" ".once memories.json" \
  "SELECT * FROM semantic_memory;"
```

**Delete Specific Memories**:
```bash
# Delete memories older than 30 days
sqlite3 data/devstream.db "DELETE FROM semantic_memory
  WHERE created_at < datetime('now', '-30 days');"
```

**Clear All Data**:
```bash
# Complete reset (backup first!)
cp data/devstream.db data/devstream.db.backup
rm data/devstream.db
# Will be recreated on next session
```

---

## 🎓 Best Practices

### 1. Let It Work Automatically

**Don't**:
- Manually tell Claude to "store this in memory"
- Ask Claude to "remember this for later"
- Explicitly request documentation

**Do**:
- Just write code naturally
- Ask questions directly
- Trust the automatic system

### 2. Use Descriptive Names

**Good**:
```python
def calculate_user_subscription_total(user_id: int) -> float:
    """Calculate total subscription cost for user."""
    pass
```

**Why**: Descriptive names improve semantic search accuracy

### 3. Write Good Commit Messages

Commit messages get stored in memory:

**Good**:
```bash
git commit -m "Fix: Hybrid search RRF algorithm now weights semantic 60%/keyword 40%"
```

**Why**: Future sessions benefit from detailed history

### 4. Document Decisions

**In Code Comments**:
```python
# DECISION: Using RRF for hybrid search because:
# 1. Handles score normalization automatically
# 2. Balances semantic vs keyword well
# 3. Validated by Context7 research
```

**Why**: Decisions persist in memory for future reference

### 5. Monitor Performance

Periodically check:
- Database size (shouldn't exceed 500MB)
- Log file sizes
- Hook execution times in logs
- Memory search response times

---

## 🚀 Advanced Usage

### Custom Memory Queries

Use MCP tools directly for advanced queries:

```typescript
// Search memories by type
await mcp.call_tool("devstream_search_memory", {
  query: "pytest async testing",
  content_type: "code",
  limit: 10
});

// Store custom memory
await mcp.call_tool("devstream_store_memory", {
  content: "Important decision about architecture",
  content_type: "decision",
  keywords: ["architecture", "fastapi", "async"]
});
```

### Integration with Other Tools

DevStream works seamlessly with:
- **Context7**: Automatic library documentation
- **GitHub MCP**: Commit messages stored in memory
- **Task Management**: Task context available automatically
- **Custom MCP Servers**: Extend with your own tools

---

## 📚 Additional Resources

### Documentation
- [Architecture Documentation](../architecture/memory_and_context_system.md)
- [Hook System Design](../architecture/hook-system-design.md)
- [Phase 2 Testing Report](../deployment/phase-2-testing-completion-report.md)

### Source Code
- Hook implementations: `.claude/hooks/devstream/`
- MCP server: `mcp-devstream-server/`
- Tests: `tests/integration/`

### Support
- GitHub Issues: https://github.com/fulvian/devstream/issues
- Project CLAUDE.md: See root directory

---

## 🎉 Conclusion

DevStream's automatic features make Claude Code sessions:
- **More productive** - Less manual context management
- **More consistent** - Knowledge persists across sessions
- **More intelligent** - Context-aware responses
- **More efficient** - Automatic library documentation

**Just write code naturally and let DevStream handle the rest!**

---

*Guide Version*: 1.0
*Last Updated*: 2025-09-30
*Status*: Production Ready
*Tested*: 23/23 integration tests passing