# DevStream Configuration Guide

**Version**: 0.1.0-beta
**Audience**: Advanced users
**Time to Read**: 15 minutes

This guide covers all configuration options for DevStream, from environment variables to hook customization.

## Table of Contents

- [Configuration Files](#configuration-files)
- [Environment Variables](#environment-variables)
- [Hook Configuration](#hook-configuration)
- [Agent Settings](#agent-settings)
- [Performance Tuning](#performance-tuning)
- [Advanced Configuration](#advanced-configuration)

---

## Configuration Files

DevStream uses multiple configuration files for different purposes:

```
devstream/
├── .env.devstream          # Environment configuration (main)
├── ~/.claude/settings.json # Hook configuration (Claude Code)
├── .claude/agents/         # Agent definitions
│   ├── orchestrator/
│   ├── domain/
│   ├── task/
│   └── qa/
└── mcp-devstream-server/
    └── package.json        # MCP server configuration
```

### Configuration Priority

```
1. Environment variables (.env.devstream)
2. Hook settings (~/.claude/settings.json)
3. Agent configurations (.claude/agents/)
4. Default values (in code)
```

---

## Environment Variables

### Main Configuration File

**Location**: `<project-root>/.env.devstream`

**How to create**:
```bash
cp .env.example .env.devstream
# Edit with your settings
```

### Memory System Configuration

```bash
# ==============================================
# Memory System (MANDATORY)
# ==============================================

# Enable/disable memory storage
DEVSTREAM_MEMORY_ENABLED=true

# Feedback level: none, minimal, verbose
# - none: No feedback to user
# - minimal: Success/error messages only
# - verbose: Detailed logging
DEVSTREAM_MEMORY_FEEDBACK_LEVEL=minimal

# Memory relevance threshold (0.0-1.0)
# Higher = more strict matching
# Lower = more results but less relevant
DEVSTREAM_CONTEXT_RELEVANCE_THRESHOLD=0.5

# Maximum tokens for memory context injection
# Recommended: 2000-3000
DEVSTREAM_CONTEXT_MAX_TOKENS=2000
```

**Memory Tuning Tips**:
- **Threshold 0.3-0.4**: Exploratory search, more results
- **Threshold 0.5-0.6**: Balanced (recommended for most projects)
- **Threshold 0.7-0.9**: Highly relevant only (for specific queries)

### Context7 Integration

```bash
# ==============================================
# Context7 Integration (MANDATORY)
# ==============================================

# Enable/disable Context7 retrieval
DEVSTREAM_CONTEXT7_ENABLED=true

# Automatically detect libraries from imports
DEVSTREAM_CONTEXT7_AUTO_DETECT=true

# Token budget for Context7 docs
# Recommended: 4000-6000
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=5000

# Minimum confidence for library detection (0.0-1.0)
DEVSTREAM_CONTEXT7_DETECTION_THRESHOLD=0.7
```

**Context7 Tuning**:
- **Token Budget < 3000**: May miss important examples
- **Token Budget 4000-6000**: Balanced (recommended)
- **Token Budget > 7000**: May exceed Claude's context limit

### Agent Auto-Delegation

```bash
# ==============================================
# Agent Auto-Delegation (Phase 3)
# ==============================================

# Enable/disable auto-delegation system
DEVSTREAM_AUTO_DELEGATION_ENABLED=true

# Minimum confidence for delegation suggestions (0.0-1.0)
# Below this: @tech-lead coordination required
DEVSTREAM_AUTO_DELEGATION_MIN_CONFIDENCE=0.85

# Auto-approve threshold (0.0-1.0)
# Above this: Automatic delegation without approval
DEVSTREAM_AUTO_DELEGATION_AUTO_APPROVE=0.95

# Enforce @code-reviewer before commits (RECOMMENDED)
DEVSTREAM_AUTO_DELEGATION_QUALITY_GATE=true
```

**Delegation Tuning**:

| Threshold | Behavior | Use Case |
|-----------|----------|----------|
| **AUTO_APPROVE ≥ 0.95** | Automatic delegation | Single-file, clear patterns |
| **MIN_CONFIDENCE 0.85-0.94** | Advisory (ask user) | Multi-file same language |
| **< MIN_CONFIDENCE** | @tech-lead coordination | Multi-stack, architectural |

**Recommended Settings**:
- **Conservative**: `AUTO_APPROVE=1.0` (never auto-delegate)
- **Balanced**: `AUTO_APPROVE=0.95` (recommended)
- **Aggressive**: `AUTO_APPROVE=0.90` (more automation, higher risk)

### Database Configuration

```bash
# ==============================================
# Database (MANDATORY)
# ==============================================

# Path to SQLite database
# Use absolute path or relative to project root
DEVSTREAM_DB_PATH=data/devstream.db

# Enable WAL mode for concurrent reads
DEVSTREAM_DB_WAL_MODE=true

# Connection pool size (for MCP server)
DEVSTREAM_DB_POOL_SIZE=5

# Query timeout (milliseconds)
DEVSTREAM_DB_TIMEOUT=5000
```

**Database Tuning**:
- **WAL Mode**: ALWAYS enable for production (concurrent reads)
- **Pool Size**: 5-10 for typical usage, 20+ for high load
- **Timeout**: 5000ms recommended, increase if slow disk

### Ollama Configuration

```bash
# ==============================================
# Ollama (OPTIONAL - for semantic search)
# ==============================================

# Ollama API endpoint
OLLAMA_BASE_URL=http://localhost:11434

# Embedding model (MUST be installed)
# Recommended: nomic-embed-text (768 dimensions)
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Request timeout (milliseconds)
OLLAMA_TIMEOUT=30000

# Fallback behavior if Ollama unavailable
# - strict: Fail if Ollama down
# - graceful: Continue without embeddings
OLLAMA_FALLBACK_MODE=graceful
```

**Ollama Setup**:
```bash
# Install model
ollama pull nomic-embed-text

# Verify model
ollama list
# Should show: nomic-embed-text

# Test API
curl http://localhost:11434/api/tags
```

### Logging Configuration

```bash
# ==============================================
# Logging (RECOMMENDED)
# ==============================================

# Log level: DEBUG, INFO, WARNING, ERROR
DEVSTREAM_LOG_LEVEL=INFO

# Log output directory
# Hooks create separate log files per hook
DEVSTREAM_LOG_PATH=~/.claude/logs/devstream/

# Structured logging format
# - json: Machine-readable (production)
# - console: Human-readable (development)
DEVSTREAM_LOG_FORMAT=console

# Log rotation (days)
DEVSTREAM_LOG_RETENTION_DAYS=30
```

**Log Files**:
```
~/.claude/logs/devstream/
├── pre_tool_use.log        # Context injection logs
├── post_tool_use.log       # Memory storage logs
└── user_query_context_enhancer.log  # Query enhancement logs
```

**Log Analysis**:
```bash
# View recent context injections
tail -100 ~/.claude/logs/devstream/pre_tool_use.log

# Search for errors
grep "ERROR" ~/.claude/logs/devstream/*.log

# Count memory storage operations
grep "Memory stored" ~/.claude/logs/devstream/post_tool_use.log | wc -l
```

---

## Hook Configuration

### Claude Code Settings

**Location**: `~/.claude/settings.json`

**Full Configuration**:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/memory/pre_tool_use.py"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "hooks": [
          {
            "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/memory/post_tool_use.py"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/context/user_query_context_enhancer.py"
          }
        ]
      }
    ]
  }
}
```

### Hook Customization

**Disable Specific Hooks**:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/memory/pre_tool_use.py",
            "enabled": false
          }
        ]
      }
    ]
  }
}
```

**Hook with Environment Variables**:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/memory/pre_tool_use.py",
            "env": {
              "DEVSTREAM_CONTEXT7_ENABLED": "false",
              "DEVSTREAM_LOG_LEVEL": "DEBUG"
            }
          }
        ]
      }
    ]
  }
}
```

### Hook Execution Order

Hooks execute in **declaration order** in settings.json.

**Example** (multiple hooks):
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "command": "hook1.py"  // Runs first
          },
          {
            "command": "hook2.py"  // Runs second
          }
        ]
      }
    ]
  }
}
```

---

## Agent Settings

### Agent Configuration Files

**Location**: `.claude/agents/<level>/<agent-name>.md`

**Structure**:
```
.claude/agents/
├── orchestrator/
│   └── tech-lead.md
├── domain/
│   ├── python-specialist.md
│   ├── typescript-specialist.md
│   ├── rust-specialist.md
│   ├── go-specialist.md
│   ├── database-specialist.md
│   └── devops-specialist.md
├── task/
│   ├── api-architect.md
│   ├── performance-optimizer.md
│   ├── testing-specialist.md
│   └── documentation-specialist.md
└── qa/
    └── code-reviewer.md
```

### Agent File Format

Each agent is defined in markdown with YAML frontmatter:

```markdown
---
name: python-specialist
role: Python 3.11+ Domain Specialist
capabilities:
  - Python 3.11+ with complete type hints
  - FastAPI async development
  - pytest testing with 95%+ coverage
  - Pydantic v2 data validation
level: domain
tools: inherit_all
---

# Python Specialist

## Expertise

You are a Python domain specialist with deep expertise in:
- Python 3.11+ features (match/case, ExceptionGroups, etc.)
- Async/await patterns with asyncio
- Type-safe development with mypy --strict
- FastAPI for REST APIs
- pytest for comprehensive testing

## Guidelines

1. **Type Safety**: All functions MUST have complete type hints
2. **Testing**: 95%+ coverage for new code
3. **Documentation**: Google-style docstrings for all public APIs
4. **Error Handling**: Structured exception hierarchy
5. **Performance**: Use async/await for I/O operations

## Example

```python
from typing import Optional
from fastapi import FastAPI, HTTPException, status

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: int) -> dict[str, Any]:
    """
    Retrieve user by ID.

    Args:
        user_id: User unique identifier

    Returns:
        User data dictionary

    Raises:
        HTTPException: 404 if user not found
    """
    user = await db.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user
```

## Delegation

For cross-language tasks, delegate to @tech-lead.
For code review, ALWAYS invoke @code-reviewer before commits.
```

### Customizing Agents

**Add New Capability**:

1. Edit agent file (e.g., `.claude/agents/domain/python-specialist.md`)
2. Add to `capabilities:` list in frontmatter
3. Document in agent description

**Create Custom Agent**:

1. Create new file: `.claude/agents/custom/my-specialist.md`
2. Define capabilities and guidelines
3. Set `tools: inherit_all` or specify tools
4. Invoke with: `@my-specialist`

---

## Performance Tuning

### Memory Search Performance

**Hybrid Search Weights**:

Edit hook: `.claude/hooks/devstream/memory/pre_tool_use.py`

```python
# Adjust RRF weights (must sum to 1.0)
SEMANTIC_WEIGHT = 0.6  # Vector search importance
KEYWORD_WEIGHT = 0.4   # FTS5 search importance
```

**Recommendations**:
- **Code Search**: `SEMANTIC=0.7, KEYWORD=0.3` (meaning matters more)
- **Exact Match**: `SEMANTIC=0.4, KEYWORD=0.6` (keywords matter more)
- **Balanced**: `SEMANTIC=0.6, KEYWORD=0.4` (recommended default)

### Context Token Budgets

**Optimize for Speed** (less context, faster response):
```bash
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=3000
DEVSTREAM_CONTEXT_MAX_TOKENS=1500
```

**Optimize for Quality** (more context, better decisions):
```bash
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=6000
DEVSTREAM_CONTEXT_MAX_TOKENS=3000
```

**Optimize for Balance** (recommended):
```bash
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=5000
DEVSTREAM_CONTEXT_MAX_TOKENS=2000
```

### Database Performance

**Enable WAL Mode** (CRITICAL for concurrent reads):
```sql
-- Check current mode
PRAGMA journal_mode;

-- Enable WAL mode
PRAGMA journal_mode=WAL;

-- Verify
PRAGMA journal_mode;  -- Should return: wal
```

**Optimize Indexes**:
```sql
-- Analyze query patterns
SELECT * FROM sqlite_stat1;

-- Rebuild indexes if fragmented
REINDEX;

-- Update statistics
ANALYZE;
```

**Connection Pooling** (MCP server):
```javascript
// mcp-devstream-server/src/database.ts
const poolConfig = {
  min: 2,           // Minimum connections
  max: 10,          // Maximum connections
  idleTimeout: 30000,  // Close idle connections after 30s
};
```

---

## Advanced Configuration

### Multi-Project Setup

For multiple projects with shared memory:

**Project 1** (`.env.devstream`):
```bash
DEVSTREAM_DB_PATH=/shared/devstream/project1.db
DEVSTREAM_MEMORY_NAMESPACE=project1
```

**Project 2** (`.env.devstream`):
```bash
DEVSTREAM_DB_PATH=/shared/devstream/project2.db
DEVSTREAM_MEMORY_NAMESPACE=project2
```

**Shared Memory** (advanced):
```bash
DEVSTREAM_DB_PATH=/shared/devstream/shared.db
DEVSTREAM_MEMORY_SHARED=true
```

### Custom Hook Development

Create custom hooks in `.claude/hooks/custom/`:

**Example** (custom pre-commit hook):

```python
#!/usr/bin/env python3
"""Custom pre-commit hook."""

import sys
from pathlib import Path
from cchooks import safe_create_context, PreToolUseContext

def run(context: PreToolUseContext) -> None:
    """Execute custom pre-commit checks."""

    # Check if tool is git commit
    if context.tool_use.name != "Bash":
        return

    command = context.tool_use.input.get("command", "")
    if not command.startswith("git commit"):
        return

    # Run custom checks
    print("🔍 Running custom pre-commit checks...")

    # Example: Check for console.log in JavaScript
    js_files = Path(".").glob("**/*.js")
    for file in js_files:
        content = file.read_text()
        if "console.log" in content:
            print(f"⚠️  Warning: console.log found in {file}")

    print("✅ Custom checks complete")

if __name__ == "__main__":
    context = safe_create_context(PreToolUseContext, sys.stdin.read())
    run(context)
```

**Register in settings.json**:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/custom/pre_commit.py"
          }
        ]
      }
    ]
  }
}
```

### Environment-Specific Configuration

**Development** (`.env.devstream.development`):
```bash
DEVSTREAM_LOG_LEVEL=DEBUG
DEVSTREAM_MEMORY_FEEDBACK_LEVEL=verbose
DEVSTREAM_AUTO_DELEGATION_AUTO_APPROVE=0.90  # More automation
OLLAMA_FALLBACK_MODE=strict  # Fail if Ollama down
```

**Production** (`.env.devstream.production`):
```bash
DEVSTREAM_LOG_LEVEL=WARNING
DEVSTREAM_MEMORY_FEEDBACK_LEVEL=minimal
DEVSTREAM_AUTO_DELEGATION_AUTO_APPROVE=0.95  # Conservative
OLLAMA_FALLBACK_MODE=graceful  # Continue without Ollama
```

**Load environment-specific config**:
```bash
# Development
ln -sf .env.devstream.development .env.devstream

# Production
ln -sf .env.devstream.production .env.devstream
```

---

## Configuration Validation

**Verify Configuration**:

```bash
# Run verification script
.devstream/bin/python scripts/verify-install.py --verbose

# Check specific components
.devstream/bin/python scripts/verify-install.py --skip-optional

# Validate hook configuration
grep -A 20 "hooks" ~/.claude/settings.json
```

**Common Issues**:

| Issue | Fix |
|-------|-----|
| Hooks not executing | Check `~/.claude/settings.json` uses `.devstream/bin/python` |
| Memory not storing | Check `DEVSTREAM_MEMORY_ENABLED=true` |
| Context7 not working | Check `DEVSTREAM_CONTEXT7_ENABLED=true` and MCP server running |
| Ollama errors | Check `OLLAMA_BASE_URL` and model installed |

---

## Summary

**Key Configuration Points**:

1. **Environment Variables**: `.env.devstream` (memory, Context7, agents)
2. **Hook Settings**: `~/.claude/settings.json` (MUST use `.devstream/bin/python`)
3. **Agent Definitions**: `.claude/agents/` (customizable)
4. **Performance Tuning**: Token budgets, relevance thresholds, WAL mode

**Recommended Settings**:
- Memory relevance: `0.5` (balanced)
- Context7 budget: `5000` tokens
- Auto-delegation: `0.95` auto-approve
- Logging: `INFO` level, `console` format

**Next Steps**:
- [Agents Guide](agents-guide.md) - When to use each agent
- [Troubleshooting](troubleshooting.md) - Common issues
- [FAQ](faq.md) - Frequently asked questions

For questions: [GitHub Issues](https://github.com/yourusername/devstream/issues)
