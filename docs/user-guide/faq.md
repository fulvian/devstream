# DevStream FAQ (Frequently Asked Questions)

**Version**: 0.1.0-beta
**Last Updated**: 2025-10-01

Common questions and answers about DevStream.

## Table of Contents

- [General Questions](#general-questions)
- [Installation & Setup](#installation--setup)
- [Task Management](#task-management)
- [Memory System](#memory-system)
- [Context7 Integration](#context7-integration)
- [Agent System](#agent-system)
- [Performance & Optimization](#performance--optimization)
- [Troubleshooting](#troubleshooting)

---

## General Questions

### What is DevStream?

DevStream is an integrated task management and cross-session memory system for Claude Code that transforms AI-assisted development through:
- **Structured Task Management** - Granular micro-tasks (10-15 min max)
- **Semantic Memory** - Automatic storage/retrieval with embeddings
- **Context Injection** - Context7 library docs + project memory
- **Specialized Agents** - 17 domain and task specialists
- **Auto-Delegation** - Pattern-based intelligent agent routing

### Is DevStream open source?

Yes, DevStream is released under the MIT License. See [LICENSE](../../LICENSE) for details.

### What are the system requirements?

**Minimum**:
- Python 3.11+
- Node.js 16+
- 4GB RAM
- 500MB disk space

**Recommended**:
- Python 3.11+
- Node.js 20 LTS
- 8GB RAM
- 1GB disk space
- Ollama with nomic-embed-text model

### Does DevStream work offline?

**Partially**:
- ✅ Task management works offline (local SQLite)
- ✅ Memory storage works offline
- ✅ Agent system works offline
- ❌ Context7 requires internet (fetches library docs)
- ❌ Ollama embeddings require local Ollama service

**Offline Mode Configuration**:
```bash
# .env.devstream
DEVSTREAM_CONTEXT7_ENABLED=false  # Disable Context7
OLLAMA_FALLBACK_MODE=graceful     # Continue without embeddings
```

### What languages/frameworks does DevStream support?

**Fully Supported** (dedicated agents):
- **Python 3.11+** (FastAPI, Django, pytest)
- **TypeScript** (React, Next.js, Node.js)
- **Rust** (Tokio, Actix, cargo)
- **Go** (Gin, Echo, goroutines)
- **SQL** (PostgreSQL, MySQL, SQLite)
- **Infrastructure** (Docker, Kubernetes, Terraform)

**Partially Supported** (via @tech-lead):
- Java, C++, C#, Ruby, PHP, Swift, Kotlin

**Context7 Coverage**:
- 1000+ libraries across all major languages
- Official documentation retrieval

---

## Installation & Setup

### How long does installation take?

**Typical**: 5-10 minutes with automated script (`./install.sh`)

**Breakdown**:
- Prerequisites check: 30 seconds
- Python environment: 2-3 minutes
- Database initialization: 30 seconds
- MCP server build: 2-3 minutes
- Hook configuration: 1-2 minutes (manual)

### Do I need to install Ollama?

**Optional but Recommended**.

**With Ollama**:
- ✅ Semantic search (meaning-based)
- ✅ Cross-session context retention
- ✅ Better memory retrieval

**Without Ollama**:
- ✅ Keyword search still works (FTS5)
- ✅ All other features functional
- ⚠️  Less intelligent memory retrieval

**Installation**:
```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull nomic-embed-text
```

### Can I use DevStream in an existing project?

**Yes!** DevStream integrates seamlessly with existing projects.

**Steps**:
1. Install DevStream in project root
2. Scan existing codebase into memory (optional):
   ```bash
   .devstream/bin/python scripts/scan-codebase.py --directory src/
   ```
3. Start using DevStream workflow

**No code changes required** - DevStream is non-invasive.

### Can I use DevStream with multiple projects?

**Yes**, two approaches:

**Approach 1: Separate Databases** (recommended):
```bash
# Project 1
cd ~/projects/project1
./install.sh
# Uses data/devstream.db

# Project 2
cd ~/projects/project2
./install.sh
# Uses data/devstream.db (separate)
```

**Approach 2: Shared Memory**:
```bash
# .env.devstream (both projects)
DEVSTREAM_DB_PATH=/shared/devstream.db
DEVSTREAM_MEMORY_SHARED=true
```

### How do I uninstall DevStream?

```bash
# Remove virtual environment
rm -rf .devstream

# Remove database
rm -rf data/devstream.db*

# Remove MCP server
rm -rf mcp-devstream-server/node_modules
rm -rf mcp-devstream-server/dist

# Remove logs
rm -rf ~/.claude/logs/devstream

# Remove hook configuration (optional)
# Edit ~/.claude/settings.json to remove hook entries
```

---

## Task Management

### What is a micro-task?

A **micro-task** is the smallest unit of work in DevStream:
- **Duration**: 10-15 minutes maximum
- **Scope**: Single, clear objective
- **Testable**: Verifiable completion criteria
- **Atomic**: Can be completed in one session

**Example**:
- ✅ Good: "Add email validation to User model"
- ❌ Bad: "Implement entire authentication system"

### Do I have to create tasks for everything?

**Mandatory for**:
- Work > 30 minutes
- Features spanning multiple files
- Architectural changes
- Major refactoring

**Optional for**:
- Single-file edits < 15 minutes
- Documentation updates
- Small bug fixes
- Code formatting

**Automatic Task Creation**: DevStream will suggest task creation if work exceeds thresholds.

### Can I work on multiple tasks simultaneously?

**Not recommended**. DevStream enforces:
- **ONE task "in_progress" at a time** (TodoWrite restriction)
- Mark current task "completed" before starting next
- Exception: Different work sessions (different machines)

**Why?**
- Context switching reduces quality
- Memory fragmentation
- Harder to track progress

### What happens if a task fails?

**Options**:

1. **Retry** (fix issue, mark "active" again):
   ```python
   mcp__devstream__devstream_update_task:
     task_id: "task-uuid"
     status: "active"
     notes: "Retrying after fixing database connection"
   ```

2. **Skip** (no longer needed):
   ```python
   mcp__devstream__devstream_update_task:
     task_id: "task-uuid"
     status: "skipped"
     notes: "Feature requirements changed"
   ```

3. **Break Down** (task too large, create smaller tasks)

---

## Memory System

### How much memory does DevStream store?

**Per file modification**:
- Content preview: ~300 bytes
- Keywords: ~50 bytes
- Embedding: ~3KB (768 floats × 4 bytes)
- **Total**: ~3.5KB per memory entry

**Typical project** (1000 files):
- Database size: ~10-20MB
- With embeddings: ~15-25MB
- SQLite is highly efficient (compressed storage)

### How do I search memory?

**Automatic** (PreToolUse hook):
- Happens before every tool execution
- No user action required

**Manual** (for advanced queries):
```python
mcp__devstream__devstream_search_memory:
  query: "authentication JWT implementation"
  content_type: "code"  # Optional filter
  limit: 10
```

**Returns**: Top 10 results ranked by relevance (hybrid semantic + keyword search)

### Can I delete memory?

**Not directly exposed** (by design - memory is permanent context).

**Workarounds**:

1. **Reset entire database** (nuclear option):
   ```bash
   rm data/devstream.db
   .devstream/bin/python scripts/setup-db.py
   ```

2. **Direct SQL** (advanced):
   ```bash
   sqlite3 data/devstream.db
   DELETE FROM semantic_memory WHERE id = <memory-id>;
   ```

3. **Filter by date** (exclude old memories):
   ```sql
   DELETE FROM semantic_memory WHERE created_at < '2025-01-01';
   ```

### How does semantic search work?

**Hybrid Search Algorithm** (Reciprocal Rank Fusion):

1. **Semantic Search** (vector similarity):
   - Query → embedding (Ollama)
   - Find closest vectors in database
   - Captures meaning (e.g., "fast API" ≈ "FastAPI")

2. **Keyword Search** (FTS5):
   - Traditional full-text search
   - Exact term matching
   - Captures specifics (e.g., "pytest" finds "pytest")

3. **Fusion** (combine scores):
   ```python
   combined_score = (
       (1 / (60 + semantic_rank)) * 0.6 +  # 60% semantic
       (1 / (60 + keyword_rank)) * 0.4     # 40% keyword
   )
   ```

**Result**: Best of both worlds (meaning + specifics)

### Does memory slow down Claude Code?

**Typical Impact**:
- PreToolUse hook: ~100-200ms (context assembly)
- PostToolUse hook: ~50-100ms (storage)
- **Total overhead**: ~150-300ms per tool execution

**Optimization**:
- Reduce token budgets (faster but less context)
- Lower relevance threshold (fewer results)
- Disable Context7 (memory only)

---

## Context7 Integration

### What is Context7?

Context7 is a service that provides up-to-date library documentation:
- **1000+ libraries** across all major languages
- **Official documentation** directly from source
- **Automatic retrieval** based on import statements
- **Token-budget controlled** (default: 5000 tokens)

**Example**:
```python
# PreToolUse hook detects this import
from fastapi import FastAPI

# Automatically retrieves FastAPI docs
# Injects into Claude's context
```

### How does Context7 detect which library to retrieve?

**Detection Patterns**:

**Python**:
```python
import fastapi          # → Context7: /tiangolo/fastapi
from django import ...  # → Context7: /django/django
```

**TypeScript**:
```typescript
import React from 'react'  // → Context7: /facebook/react
```

**Rust**:
```rust
use tokio::runtime  // → Context7: /tokio-rs/tokio
```

**Go**:
```go
import "github.com/gin-gonic/gin"  // → Context7: /gin-gonic/gin
```

### Can I disable Context7?

**Yes**:
```bash
# Edit .env.devstream
DEVSTREAM_CONTEXT7_ENABLED=false
```

**When to disable**:
- Offline work
- Reduce hook execution time
- Library not in Context7 database

**Memory still works** without Context7 (uses DevStream memory only).

### How much does Context7 documentation consume?

**Default**: 5000 tokens per retrieval

**Token Usage Breakdown**:
- Library overview: ~1000 tokens
- Key concepts: ~1500 tokens
- Code examples: ~2000 tokens
- API reference: ~500 tokens

**Customization**:
```bash
# .env.devstream
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=3000  # Reduced
```

---

## Agent System

### How do I invoke an agent?

**Direct Invocation**:
```
@python-specialist Create a FastAPI endpoint for users
@typescript-specialist Build a React dashboard component
@code-reviewer Review authentication implementation
```

**Orchestrated Invocation** (via @tech-lead):
```
@tech-lead Build full-stack user management feature
# tech-lead delegates to @python-specialist, @typescript-specialist, etc.
```

**Auto-Delegation** (automatic):
```
"Update src/api/users.py to add pagination"
# Auto-delegates to @python-specialist (*.py pattern detected)
```

### Can I create custom agents?

**Yes!**

**Steps**:
1. Create agent file: `.claude/agents/custom/my-specialist.md`
2. Define capabilities:
   ```markdown
   ---
   name: my-specialist
   role: My Custom Specialist
   level: custom
   tools: inherit_all
   ---

   # My Specialist

   ## Expertise
   - Your custom capabilities here

   ## Guidelines
   1. Your custom guidelines here
   ```

3. Invoke: `@my-specialist <task>`

### When should I use @tech-lead vs direct specialist?

**Use @tech-lead when**:
- Multi-language/stack feature
- Architectural decisions needed
- Unsure which specialist to use
- Coordination of multiple specialists

**Use direct specialist when**:
- Single language/technology
- Clear implementation path
- Specific domain expertise needed

**Example**:
- Full-stack feature → `@tech-lead`
- Python-only API → `@python-specialist`
- Database schema → `@database-specialist`

### Is @code-reviewer mandatory?

**Yes**, before EVERY commit.

**Enforced by**:
- Auto-delegation quality gate (if enabled)
- Manual invocation (if auto-delegation disabled)

**What it checks**:
- OWASP Top 10 security
- Performance issues
- Code quality
- Test coverage (95%+)
- Architecture review

**How to use**:
```
@code-reviewer Review implementation in src/api/auth.py

# Or before commit:
"Ready to commit authentication implementation"
# Auto-delegates to @code-reviewer
```

### Can I customize agent behavior?

**Yes**, edit agent files:

**Example** (customize @python-specialist):
```bash
# Edit agent file
vi .claude/agents/domain/python-specialist.md

# Add custom guidelines:
## Custom Guidelines (Your Project)
- Always use SQLAlchemy async sessions
- Prefix all API endpoints with /api/v1
- Use structlog for all logging
```

**Agents will follow** custom guidelines in their files.

---

## Performance & Optimization

### How do I make DevStream faster?

**1. Reduce Context Budgets**:
```bash
# .env.devstream
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=3000  # Was 5000
DEVSTREAM_CONTEXT_MAX_TOKENS=1500     # Was 2000
```

**2. Enable Database WAL Mode**:
```bash
sqlite3 data/devstream.db "PRAGMA journal_mode=WAL;"
```

**3. Reduce Memory Search Limit**:
```python
# Edit .claude/hooks/devstream/memory/pre_tool_use.py
memory_results = await self.search_memory(query, limit=5)  # Was 10
```

**4. Disable Context7 Temporarily**:
```bash
DEVSTREAM_CONTEXT7_ENABLED=false
```

### How much RAM does DevStream use?

**Typical**:
- Python hooks: 50-100MB per hook execution
- MCP server: 100-200MB (Node.js)
- SQLite: 10-20MB (database cache)
- **Total**: ~200-400MB

**Peak** (with Ollama):
- Ollama service: 500MB-1GB
- Embedding generation: +200MB
- **Total**: ~1-1.5GB

**Optimization**:
- Close Ollama when not needed
- Restart MCP server periodically
- Use `OLLAMA_FALLBACK_MODE=graceful`

### Does DevStream affect Claude Code response time?

**Typical Impact**:
- Without DevStream: 2-5 seconds (Claude API)
- With DevStream: 2.5-5.5 seconds (+0.5s hook overhead)

**Breakdown**:
- PreToolUse: ~150-200ms (context injection)
- Claude API: 2-5 seconds (unchanged)
- PostToolUse: ~50-100ms (memory storage)

**Optimization**: See "How do I make DevStream faster?" above.

### Can I profile DevStream performance?

**Yes!**

**Hook Timing** (logs):
```bash
grep "Hook execution time" ~/.claude/logs/devstream/*.log
```

**Database Profiling**:
```sql
-- Enable query logging
PRAGMA query_log=ON;

-- Run queries, then check log
SELECT * FROM query_log ORDER BY time_ms DESC LIMIT 10;
```

**Python Profiling**:
```bash
# Profile hook execution
python -m cProfile -s cumtime \
  .claude/hooks/devstream/memory/pre_tool_use.py \
  < test_input.json
```

---

## Troubleshooting

### Hooks not executing. What do I check?

**Checklist**:
1. ✅ Verify `~/.claude/settings.json` exists and valid JSON
2. ✅ Hooks use `.devstream/bin/python` (not system Python)
3. ✅ Hook scripts exist and executable (`chmod +x`)
4. ✅ Check logs: `~/.claude/logs/devstream/*.log`
5. ✅ Test manually: `echo '{}' | .devstream/bin/python .claude/hooks/...`

**See**: [Troubleshooting Guide](troubleshooting.md#hook-system-issues)

### Memory not storing. What do I check?

**Checklist**:
1. ✅ `DEVSTREAM_MEMORY_ENABLED=true` in `.env.devstream`
2. ✅ Database exists and writable: `ls -l data/devstream.db`
3. ✅ PostToolUse hook executing: Check logs
4. ✅ MCP server running: `curl http://localhost:3000/health`
5. ✅ Test manually: `mcp__devstream__devstream_store_memory`

**See**: [Troubleshooting Guide](troubleshooting.md#memory-system-issues)

### Context7 not working. What do I check?

**Checklist**:
1. ✅ `DEVSTREAM_CONTEXT7_ENABLED=true` in `.env.devstream`
2. ✅ MCP server running: `curl http://localhost:3000/health`
3. ✅ Internet connection (Context7 requires online access)
4. ✅ Check PreToolUse logs for Context7 retrieval
5. ✅ Test manually: `mcp__context7__resolve-library-id`

**See**: [Troubleshooting Guide](troubleshooting.md#context7-issues)

### Agent not responding. What do I check?

**Checklist**:
1. ✅ Agent file exists: `.claude/agents/<level>/<agent>.md`
2. ✅ Agent file valid format (YAML frontmatter + markdown)
3. ✅ Agent name matches invocation: `@python-specialist`
4. ✅ Check Claude Code session (restart if needed)

**See**: [Troubleshooting Guide](troubleshooting.md#agent-system-issues)

### Where do I get help?

**Documentation**:
- [Installation Guide](../../INSTALLATION.md)
- [Getting Started](getting-started.md)
- [Troubleshooting](troubleshooting.md)

**Community**:
- GitHub Issues (bug reports, questions)
- Project Wiki (additional guides)
- Discord/Slack (if available)

**Diagnostics**:
```bash
.devstream/bin/python scripts/verify-install.py --verbose
```

---

## Additional Questions

### Does DevStream support team collaboration?

**Currently**: Single-user system

**Future** (roadmap):
- Shared semantic memory across team
- Task assignment and tracking
- Collaborative code review
- Team performance metrics

**Workaround** (now):
- Share database file (Dropbox, Git LFS)
- Export/import memory entries
- Sync via git (commit memory alongside code)

### Can DevStream integrate with other tools?

**Current Integrations**:
- Claude Code (native)
- Ollama (embeddings)
- SQLite (storage)
- Context7 (documentation)

**Possible Integrations** (community contributions welcome):
- GitHub Actions (CI/CD)
- Linear/Jira (issue tracking)
- Sentry (error monitoring)
- DataDog (performance monitoring)

### Is DevStream suitable for production?

**Current Status**: **Beta (v0.1.0)**

**Production-Ready**:
- ✅ Core functionality stable
- ✅ Automated testing
- ✅ Security validated (@code-reviewer)
- ✅ Performance optimized

**Not Production-Ready**:
- ⚠️  Beta version (breaking changes possible)
- ⚠️  Limited team collaboration
- ⚠️  Basic monitoring/alerting

**Recommendation**: Suitable for small teams and personal projects. Enterprise production use: wait for v1.0.

### How do I contribute to DevStream?

**Ways to Contribute**:
1. **Bug Reports**: GitHub Issues with `[BUG]` prefix
2. **Feature Requests**: GitHub Issues with `[FEATURE]` prefix
3. **Code Contributions**: Pull requests (follow CONTRIBUTING.md)
4. **Documentation**: Improve guides, add examples
5. **Community Support**: Answer questions on GitHub/Discord

**Development Setup**:
```bash
git clone <devstream-repo>
cd devstream
./install.sh --dev
.devstream/bin/python -m pytest tests/
```

---

**Still have questions?**
- [GitHub Issues](https://github.com/yourusername/devstream/issues)
- [Troubleshooting Guide](troubleshooting.md)
- [Documentation Index](../README.md)
