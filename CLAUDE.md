# CLAUDE.md - DevStream Project Rules (Optimized)

**Version**: 2.2.0 | **Date**: 2025-10-09 | **Status**: Production Ready

⚠️ **MANDATORY SYSTEM RULES** - Non-negotiable, integrated via automatic hooks. Violations cause system malfunctions and rollback.

---

## 🚨 MemoryManager System (CRITICAL)

**MemoryManager** is MANDATORY and EXCLUSIVE for DevStream project memory database queries.

### Usage Rules
✅ **ALWAYS**: `from .claude.hooks.devstream.utils.direct_client import get_direct_client`
❌ **NEVER**: Python Specialist, MCP Tools, Direct SQL, bypassing MemoryManager

### Correct Pattern
```python
from .claude.hooks.devstream.utils.direct_client import get_direct_client

def search_project_memory(query: str):
    client = get_direct_client()
    return client.search_memory(query, limit=10)
```

### Direct DB Commands
```bash
# Search memory
.devstream/bin/python -c "
import asyncio, sys
sys.path.append('.claude/hooks/devstream/utils')
from direct_client import get_direct_client

async def search():
    client = get_direct_client()
    result = await client.search_memory('query', limit=10)
    print(result)
asyncio.run(search())
"

# Store memory
.devstream/bin/python -c "
import asyncio, sys
sys.path.append('.claude/hooks/devstream/utils')
from direct_client import get_direct_client

async def store():
    client = get_direct_client()
    result = await client.store_memory(
        content='content',
        content_type='code',
        keywords=['kw1', 'kw2']
    )
    print(result)
asyncio.run(store())
"

# Task management
.devstream/bin/python -c "
import asyncio, sys
sys.path.append('.claude/hooks/devstream/utils')
from direct_client import get_direct_client

async def task_ops():
    client = get_direct_client()
    # Create task
    result = await client.create_task(
        title='Task Title',
        description='Description',
        task_type='development',
        priority=5,
        phase_name='Implementation'
    )
    # List tasks
    tasks = await client.list_tasks(status='pending')
    print(result, tasks)
asyncio.run(task_ops())
"
```

---

## 🤖 Agent System (17/17 Production Ready)

### Hierarchy (4 Levels)
1. **Orchestrator**: `@tech-lead` - Multi-agent coordination
2. **Domain Specialists** (6): Python, TypeScript, Rust, Go, Database, DevOps
3. **Task Specialists** (5): API Architect, Performance, Testing, Documentation, Refactoring
4. **Quality Assurance** (6): Code Reviewer (MANDATORY), Security, Debugger, Integration, Migration

### Usage Patterns
- **Direct**: `@python-specialist Create FastAPI endpoint`
- **Orchestrated**: `@tech-lead Build full-stack feature` → delegates to specialists
- **Quality Gate**: `@code-reviewer Review src/api/users.py:45-120` (MANDATORY before commits)

### Agent Capabilities
| Agent | Use | Tools | Restrictions |
|-------|-----|-------|--------------|
| @tech-lead | Multi-stack coordination | Task, Read, Glob, Grep | Planning only |
| Domain Specialists | Language implementation | Full access | None |
| Task Specialists | Specialized operations | Full access | None |
| @code-reviewer | Quality gate (MANDATORY) | Read, Grep, Glob, Bash | Analysis only |

---

## 🎯 Tier-Based Delegation (Token Optimization)

**Purpose**: -70% token overhead (0-7K → 1K avg, 28→100 tasks/5h)

### Tiers
1. **Tier 1** (60%): Monolithic, no agents (simple tasks)
2. **Tier 2** (30%): Single specialist (file-specific)
3. **Tier 3** (5%): Multi-agent orchestration (@tech-lead)
4. **Tier 4** (5%): Quality gate (@code-reviewer, MANDATORY)

### File Mapping (Tier 2)
- `.py` → @python-specialist
- `.ts/.tsx` → @typescript-specialist
- `.sql` → @database-specialist
- `.rs` → @rust-specialist
- `.go` → @go-specialist
- `.md` docs → @documentation-specialist

### Config (.env.devstream)
```bash
DEVSTREAM_AUTO_DELEGATION_TIER1_ENABLED=true
DEVSTREAM_AUTO_DELEGATION_TIER2_THRESHOLD=0.95
DEVSTREAM_AUTO_DELEGATION_TIER3_THRESHOLD=0.70
DEVSTREAM_AUTO_DELEGATION_QUALITY_GATE=true
```

---

## 📋 7-Step Workflow (MANDATORY)

### Step 0: Enforcement Gate
**Triggers**: >15min, code implementation, architectural decisions, multi-file, Context7 research
**Flow**: User request → Complexity analysis → IF criteria met → Protocol/Override/Cancel choice

### Step 1: Discussion (MANDATORY)
- Present problem/objective
- Discuss trade-offs
- Obtain consensus
- **NEW**: Task creation at Step 1 (prevents data loss)

### Step 2: Analysis (MANDATORY)
- Analyze codebase patterns
- Identify files to modify
- Estimate complexity
- Define acceptance criteria

### Step 3: Research (MANDATORY - Context7)
- Use Context7 for technical decisions
- Research best practices
- Document findings
- Validate approach

### Step 4: Planning (MANDATORY)
- Create TodoWrite list (10-15 min micro-tasks)
- Define dependencies/completion criteria
- **NEW**: Generate implementation plan (model-specific)

### Step 5: Approval (MANDATORY + Strategic Choice)
- Present complete plan + Context7 findings
- Obtain explicit approval
- **NEW**: Choose implementation model:
  - **Option A**: Continue with Sonnet 4.5 (architectural)
  - **Option B**: Handoff to GLM-4.6 (execution, ~70% cost savings)

### Step 6: Implementation (MANDATORY)
- One micro-task at a time
- Mark "in_progress" → work → "completed"
- Document with docstrings + type hints

### Step 7: Verification (MANDATORY)
- Tests for EVERY feature
- 95%+ coverage requirement
- Validate performance
- E2E integration tests
- Error handling verification

---

## 📄 Task Lifecycle

### Creation (Step 1 - MANDATORY)
**When**: Work >15 min OR code/architecture/research
**Process**:
- `task_first_handler.py` enforces at Step 1
- Automatic complexity detection
- Interactive enforcement gate
- Use `get_direct_client().create_task()`
- Define: title, description, task_type, priority (1-10), phase_name
- Draft cleanup: >7 days auto-archived

### Execution
- Mark "active" via `get_direct_client().update_task()`
- Follow 7-step workflow
- Update progress continuously
- Register decisions/learnings
- TodoWrite real-time tracking

### Completion
- Verify TodoWrite "completed"
- Tests 100% pass
- Mark "completed"
- Register lessons learned
- Commit and push (if requested)

---

## 💾 Memory System

### Automatic Storage (PostToolUse Hook)
**When**: After EVERY tool execution
**Content Types**: code, documentation, context, output, error, decision, learning
**Process**: Automatic
1. PostToolUse hook
2. Content preview (300 chars)
3. Keywords extraction
4. Vector embeddings (Ollama)
5. SQLite + sqlite-vec storage

### Memory Search (PreToolUse Hook)
**Flow**:
1. Detect libraries (Context7)
2. Search DevStream memory
3. Assemble hybrid context
4. Inject in Claude context
5. Token budget management
**Algorithm**: Hybrid search (semantic + keyword) via RRF
**Threshold**: 0.5 relevance
**Token Budget**: Context7 5000 + Memory 2000

### Manual Operations (OPTIONAL)
**MANDATORY Access Pattern**:
```python
from .claude.hooks.devstream.utils.direct_client import get_direct_client
client = get_direct_client()
```

**Direct DB Tools**:
- `get_direct_client().store_memory()` (content, content_type, keywords)
- `get_direct_client().search_memory()` (query, content_type, limit)

---

## 📝 Context Injection

### Context7 Integration (PreToolUse Hook)
**Triggers**: Import statements, library mentions, code patterns, documentation requests
**Process**: Automatic
1. Context7 detect
2. Retrieve docs via `mcp__context7__get-library-docs`
3. Inject (max 5000 tokens)
4. Priority ordering (official docs > examples > best practices)

### DevStream Memory Context (PreToolUse Hook)
**Priority Order**:
1. Context7 Documentation (5000 tokens)
2. DevStream Memory (2000 tokens - related code/decisions)
3. Current File Context (remaining budget)

**Config** (.env.devstream):
```bash
DEVSTREAM_CONTEXT7_ENABLED=true
DEVSTREAM_CONTEXT7_AUTO_DETECT=true
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=5000
DEVSTREAM_CONTEXT_INJECTION_ENABLED=true
DEVSTREAM_CONTEXT_MAX_TOKENS=2000
DEVSTREAM_CONTEXT_RELEVANCE_THRESHOLD=0.5
```

---

## 🐍 Python Environment (MANDATORY)

### Critical Rule: Use .devstream Venv
**Configuration**:
- Venv: `.devstream`
- Python: 3.11.x
- Interpreter: `.devstream/bin/python`

**Session Start Checklist**:
```bash
# Verify venv exists
[ ! -d ".devstream" ] && python3.11 -m venv .devstream

# Verify Python version
.devstream/bin/python --version

# Verify critical dependencies
.devstream/bin/python -m pip list | grep -E "(cchooks|aiohttp|structlog)"
```

**FORBIDDEN**: `python`, `python3`, `uv run`
**REQUIRED**: `.devstream/bin/python`, `.devstream/bin/python -m pytest`, `.devstream/bin/python -m pip install`

### First-Time Setup
```bash
# Create venv
python3.11 -m venv .devstream

# Upgrade pip
.devstream/bin/python -m pip install --upgrade pip

# Install requirements
.devstream/bin/python -m pip install -r requirements.txt

# Install hook dependencies
.devstream/bin/python -m pip install cchooks>=0.1.4 aiohttp>=3.8.0 \
  structlog>=23.0.0 python-dotenv>=1.0.0
```

### Hook System Configuration
**settings.json**:
```json
{
  "hooks": {
    "PreToolUse": [{
      "hooks": [{
        "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/memory/pre_tool_use.py"
      }]
    }],
    "PostToolUse": [{
      "hooks": [{
        "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/memory/post_tool_use.py"
      }]
    }],
    "UserPromptSubmit": [{
      "hooks": [{
        "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/context/user_query_context_enhancer.py"
      }]
    }]
  }
}
```

---

## 🛠️ Tools & Configuration

### Context7 Usage (MANDATORY for Research)
**Workflow**:
1. `mcp__context7__resolve-library-id` (library name → Context7 ID)
2. `mcp__context7__get-library-docs` (ID → docs max 5000 tokens)
3. Analyze findings
4. Apply research-backed patterns

### TodoWrite Usage (MANDATORY for Planning)
**When**: Non-trivial tasks (>15 min)
**Process**:
- Create TodoWrite BEFORE implementation
- Micro-tasks 10-15 min
- Mark "in_progress" → work → "completed"
- ONE task "in_progress" at a time
**Format**: `{"content": "Imperative", "activeForm": "Present continuous", "status": "pending|in_progress|completed"}`

### Testing Requirements (MANDATORY)
**Coverage**:
- 95%+ for NEW code
- 100% pass rate before commit
- E2E integration tests
- Performance validation
- Error handling

**Structure**:
- `tests/unit/` (fast <1s)
- `tests/integration/` (E2E <10s)
- `tests/fixtures/` (test data)

**Execution**:
```bash
.devstream/bin/python -m pytest tests/ -v \
  --cov=.claude/hooks/devstream \
  --cov-report=html
```

**Thresholds**: Unit 95%+, Integration 85%+, E2E 70%+

### Async Testing Patterns (pytest-asyncio)
```python
# Async fixtures
@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def mcp_client():
    client = await create_mcp_client()
    yield client
    await client.close()

# Error testing
@pytest.mark.asyncio
async def test_error_handling():
    with pytest.raises(ConnectionError, match="timeout"):
        await failing_function()

# AsyncMock for retries
@pytest.mark.asyncio
async def test_circuit_breaker():
    mock = AsyncMock()
    mock.create_task.side_effect = [
        ConnectionError("Fail 1"),
        ConnectionError("Fail 2"),
        {"task_id": "success"}
    ]
    result = await circuit_breaker_execute(mock)
    assert mock.create_task.call_count == 3
```

### .coveragerc Configuration
```ini
[run]
source = .claude/hooks/devstream
omit = */tests/*, */test_*, __pycache__
concurrency = gevent

[report]
exclude_lines = pragma: no cover, def __repr__, raise AssertionError, raise NotImplementedError, if __name__ == .__main__:

[html]
directory = htmlcov
```

---

## 📖 Documentation Requirements

### Code Documentation (MANDATORY)
**Every function/class MUST have**:
- Docstring (description, Args, Returns, Raises, Note)
- Full type hints
- Inline comments for complex logic (>5 lines)

**Example**:
```python
def hybrid_search(
    self,
    query: str,
    limit: int = 10,
    content_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Perform hybrid search combining semantic and keyword search.
    Uses Reciprocal Rank Fusion (RRF) algorithm.

    Args:
        query: Search query string
        limit: Maximum results (default: 10)
        content_type: Optional filter by content type

    Returns:
        List of memory records sorted by relevance score

    Raises:
        DatabaseError: If database query fails

    Note:
        RRF weights: semantic 60%, keyword 40%
    """
```

### Project Documentation (MANDATORY)
**Structure**:
- `docs/architecture/` (system design - MANDATORY new systems)
- `docs/api/` (API reference - MANDATORY APIs)
- `docs/deployment/` (MANDATORY production)
- `docs/guides/` (MANDATORY user-facing features)
- `docs/development/` (MANDATORY complex features)
- `docs/tutorials/` (OPTIONAL)

**Rules**:
- Create docs for EVERY major feature
- Update BEFORE task complete
- Include code examples
- Keep in sync
- No .md files in root (except README.md, CLAUDE.md, PROJECT_STRUCTURE.md)

---

## 🎯 Quality Standards

### Code Quality (MANDATORY)
**Type Safety**:
- Full type hints ALL functions/methods
- `mypy --strict` (zero errors)
- No `Any` type hints
- No mypy errors in production

**Error Handling**:
- Structured exception hierarchy
- Logging for EVERY exception
- Graceful degradation
- User-friendly messages
- No bare `except:`
- No silent failures

**Performance**:
- async/await for I/O
- Connection pooling
- Token budget enforcement
- Performance testing
- No blocking I/O in async

**Maintainability**:
- SOLID principles
- Single responsibility
- Max function length 50 lines
- Max cyclomatic complexity 10
- No god objects
- No cryptic abbreviations

### Architecture Quality (MANDATORY)
**Separation**:
- Clear module boundaries
- Layered architecture (hooks → utils → core)
- Interface segregation
- No circular dependencies
- No tight coupling

**Configuration**:
- Environment-based (.env.devstream)
- Validate ALL config
- Defaults and documentation
- No hardcoded values
- No config in code

**Logging**:
- Structured logging (structlog)
- Context ALL log messages
- Appropriate levels (DEBUG/INFO/WARNING/ERROR)
- Log rotation
- No `print()` statements
- No logging sensitive data

---

## 🚀 Implementation Patterns

### Research-Driven Development (MANDATORY)
**Sequence**:
1. RESEARCH - Context7 → best practices → document findings
2. DESIGN - Research-based architecture → clear interfaces
3. IMPLEMENT - Validated patterns → one micro-task at a time
4. TEST - 95%+ coverage → validate assumptions
5. DOCUMENT - Lessons learned → update docs

### Micro-Task Execution (MANDATORY)
**Sequence**:
1. ANALYZE - Break down feature → 10-15 min micro-tasks → dependencies
2. PLAN - TodoWrite list → completion criteria
3. EXECUTE - One task at a time → mark "in_progress" → work → "completed"
4. VERIFY - Test after EVERY task → verify integration
5. INTEGRATE - Merge codebase → update docs

### Approval Workflow (MANDATORY)
**Sequence**:
1. DISCUSS - Present approach + trade-offs → identify risks
2. RESEARCH - Context7 validation → alternative approaches
3. APPROVE - Explicit approval → confirm acceptance criteria
4. IMPLEMENT - Follow approved approach → no deviations without approval
5. REVIEW - Validate results → document learnings

---

## 📊 Success Metrics

### Development Metrics (MANDATORY Targets)
- Task Completion: 100%
- Test Coverage: 95%+ NEW code
- Test Pass Rate: 100%
- Code Quality: Zero mypy errors
- Cyclomatic Complexity: Max 10
- Documentation Coverage: 100% docstrings
- Performance: Meet/exceed targets

### Process Metrics (MANDATORY Tracking)
- Research Quality: Context7 usage for EVERY major decision
- Collaboration: 100% approval workflow adherence
- Learning: Documented lessons learned per phase
- Innovation: Research-backed technology choices
- Delivery: On-time (planned vs actual)
- Memory Usage: Automatic storage tracking
- Context Injection: Automatic injection rate

---

## 📁 File Organization

### Project Structure (MANDATORY)
**CRITICAL**: ALWAYS follow PROJECT_STRUCTURE.md

**Documentation**:
- `docs/{architecture,api,deployment,guides,development,tutorials}/`
- No .md files in root (except README.md, CLAUDE.md, PROJECT_STRUCTURE.md)

**Tests**:
- `tests/{unit,integration,fixtures}/`
- No test files in root
- No tests mixed with source

**Naming**:
- Documentation → kebab-case (devstream-guide.md)
- Code → snake_case (pre_tool_use.py)

**File Creation Checklist**:
1. Check PROJECT_STRUCTURE.md
2. Identify correct directory
3. Use naming convention
4. Verify directory exists
5. Create file

---

## 🚨 Fundamental Rule - Problem Solving

### ⚡⚡⚡ USE CONTEXT7 TO SOLVE - NEVER SIMPLIFY ⚡⚡⚡

**MANDATORY**:
- Use Context7 to research solution
- Research best practices
- Implement research-backed solution
- Maintain ALL features functional
- Test thoroughly

**FORBIDDEN**:
- Disable features to "fix" problem
- Remove functionality as workaround
- Create temporary workarounds
- Simplify to avoid complexity
- Skip research step

---

## 📚 System Integration Reference

### Hook Integration Points
| Hook | Location | Trigger | Purpose | Status |
|------|----------|---------|---------|--------|
<<<<<<< HEAD
| PreToolUse | `.claude/hooks/devstream/memory/pre_tool_use.py` | Before EVERY tool execution | Inject Context7 + DevStream memory | `DEVSTREAM_CONTEXT_INJECTION_ENABLED` |
| PostToolUse | `.claude/hooks/devstream/memory/post_tool_use.py` | After EVERY tool execution | Store code/docs/context | `DEVSTREAM_MEMORY_ENABLED` |
| UserPromptSubmit | `.claude/hooks/devstream/context/user_query_context_enhancer.py` | On EVERY user prompt | Enhance query with context | `DEVSTREAM_QUERY_ENHANCEMENT_ENABLED` |
**NOTE**: Session tracking hooks (SessionEnd, SessionStart, PreCompact) have been **DEPRECATED** and **REMOVED** as of 2025-10-12 due to complexity and reliability issues. Cross-session summary preservation is no longer supported. Use git log or DevStream memory search to review past work.

### MCP Server Integration
**Location**: `mcp-devstream-server/` | **Port**: 3000
**Tools**:
- Task Management: `devstream_create_task`, `devstream_update_task`, `devstream_list_tasks`
- Memory System: `devstream_store_memory`, `devstream_search_memory`
- **Protocol v2.2.0 NEW**: `devstream_create_implementation_plan`, `devstream_get_implementation_plan`, `devstream_update_implementation_plan`, `devstream_list_implementation_plans`
**Config**: `.claude/mcp_servers.json` → `{"devstream": {"command": "node", "args": ["mcp-devstream-server/dist/index.js"], "env": {"DEVSTREAM_DB_PATH": "data/devstream.db"}}}`

### Implementation Plans System (Protocol v2.2.0)
**Database Schema**: `implementation_plans` table with model-specific storage (GLM-4.6 vs Sonnet 4.5)
=======
| PreToolUse | `.claude/hooks/devstream/memory/pre_tool_use.py` | Before EVERY tool | Context7 + Memory injection | ✅ Active |
| PostToolUse | `.claude/hooks/devstream/memory/post_tool_use.py` | After EVERY tool | Store code/docs/context | ✅ Active |
| UserPromptSubmit | `.claude/hooks/devstream/context/user_query_context_enhancer.py` | Every user prompt | Enhance query with context | ✅ Active |
| SessionEnd | `.claude/hooks/devstream/sessions/session_end.py` | Session exit | Generate session summary | ⚠️ **DISABLED** (2025-10-12) |
| PreCompact | `.claude/hooks/devstream/sessions/pre_compact.py` | Before /compact | Save summary pre-compaction | ⚠️ **DISABLED** (2025-10-12) |
| SessionStart | `.claude/hooks/devstream/sessions/session_start.py` | Session startup | Display previous summary | ⚠️ **DISABLED** (2025-10-12) |

### Direct Database Access Points
| Component | Access Method | Tools | Purpose | Status |
|-----------|---------------|-------|---------|--------|
| Task Management | Direct DB | `get_direct_client()` methods | Task lifecycle | ✅ Active |
| Memory System | **MemoryManager** | `get_direct_client()` methods | Semantic storage | ✅ Active |
| Implementation Plans | Direct DB | `get_direct_client()` methods | Plan management | ✅ Active |
| Vector Search | **MemoryManager** + Ollama | N/A | Memory retrieval | ✅ Active |
| Session Tracking | Direct DB | N/A | Cross-session | ✅ Active |

**🚨 CRITICAL**: Memory System and Vector Search **MUST** use MemoryManager (`get_direct_client()`) - NEVER use Python Specialist or MCP tools for memory database interrogation.

### Direct Database Integration (v2.2.0+)
**Architecture**: Direct SQLite database connection (Direct DB Architecture)
- **Direct DB**: Native SQLite access via `get_direct_client()` methods (current)
- **MCP Server**: Eliminated in v2.2.0+ for performance and reliability

**Database**: `data/devstream.db` (sqlite-vec enabled)

**Direct DB Tools** (no server required):
- Task Management: `get_direct_client().create_task()`, `get_direct_client().update_task()`, `get_direct_client().list_tasks()`
- Memory System: `get_direct_client().store_memory()`, `get_direct_client().search_memory()`
- Implementation Plans: `get_direct_client().create_implementation_plan()`, `get_direct_client().get_implementation_plan()`, `get_direct_client().update_implementation_plan()`, `get_direct_client().list_implementation_plans()`
- Memory Operations: `get_direct_client().trigger_checkpoint()`

### Implementation Plans System (v2.2.0+)
**Architecture**: Direct database integration with dual storage pattern
**Database Schema**: `implementation_plans` table
- Direct SQLite access via `get_direct_client()` methods
- Full metadata, task linkage, model type tracking
- Direct DB Architecture (no server dependency)

>>>>>>> release/v0.3.0
**Dual Storage Pattern**:
- **Database**: Direct SQLite storage with full metadata
- **Filesystem**: `docs/development/plan/piano_[task-slug].md` for human readability

**Model-Specific Templates**:
- **GLM-4.6**: `templates/implementation-plan-glm46.md` (execution-focused)
- **Sonnet 4.5**: `templates/implementation-plan-sonnet45.md` (architectural)
- **Handoff**: `templates/handoff-prompt-glm46.md` (Sonnet→GLM context transfer)

**Direct DB Tools** (Primary Interface):
- `get_direct_client().create_implementation_plan()` - Create new plan
- `get_direct_client().get_implementation_plan()` - Retrieve plan by task ID
- `get_direct_client().update_implementation_plan()` - Update existing plan
- `get_direct_client().list_implementation_plans()` - List all plans

### Environment Configuration (.env.devstream)
```bash
# Core System (MANDATORY)
DEVSTREAM_MEMORY_ENABLED=true
DEVSTREAM_MEMORY_FEEDBACK_LEVEL=minimal

# Database (MANDATORY - Direct DB Architecture)
DEVSTREAM_DB_PATH=data/devstream.db
DEVSTREAM_DIRECT_DB_ENABLED=true

# Context7 (MANDATORY)
DEVSTREAM_CONTEXT7_ENABLED=true
DEVSTREAM_CONTEXT7_AUTO_DETECT=true
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=5000

# Context Injection (MANDATORY)
DEVSTREAM_CONTEXT_INJECTION_ENABLED=true
DEVSTREAM_CONTEXT_MAX_TOKENS=2000
DEVSTREAM_CONTEXT_RELEVANCE_THRESHOLD=0.5

# Tier-Based Delegation (v2.2.0+ - MANDATORY)
DEVSTREAM_AUTO_DELEGATION_TIER1_ENABLED=true
DEVSTREAM_AUTO_DELEGATION_TIER2_THRESHOLD=0.95
DEVSTREAM_AUTO_DELEGATION_TIER3_THRESHOLD=0.70
DEVSTREAM_AUTO_DELEGATION_QUALITY_GATE=true

# Implementation Plans (v2.2.0+ - MANDATORY)
DEVSTREAM_IMPLEMENTATION_PLANS_ENABLED=true
DEVSTREAM_DUAL_STORAGE_ENABLED=true

# Session Management (v2.2.0+)
DEVSTREAM_HOOK_SESSIONSTART=false
DEVSTREAM_HOOK_SESSION_END=false
DEVSTREAM_HOOK_PRE_COMPACT=false

# Logging (RECOMMENDED)
DEVSTREAM_LOG_LEVEL=INFO
DEVSTREAM_LOG_PATH=~/.claude/logs/devstream/

# Vector Search (MANDATORY)
DEVSTREAM_VECTOR_SEARCH_ENABLED=true
DEVSTREAM_VECTOR_EMBEDDINGS_MODEL=gemma3
DEVSTREAM_VECTOR_DB_ENABLED=true
```

---

## Document Metadata

**Version**: 2.2.0+ (Protocol v2.2.0 - Direct DB Architecture)
**Last Updated**: 2025-10-14
**Status**: ✅ Production Ready - Direct DB Architecture Complete

**Key Changes v2.2.0+**:
- ✅ **Direct Database Architecture** - MCP server eliminated, direct SQLite access
- ✅ Task creation moved to Step 1 (prevents data loss)
- ✅ Implementation plans with model-specific templates
- ✅ Strategic Choice Gate at Step 5 (cost optimization)
- ✅ GLM-4.6 handoff workflow for session switching
- ✅ Dual storage pattern (DB + filesystem) for plans
- ✅ Enhanced vector search with sqlite-vec integration
- ✅ Simplified configuration with direct DB tools

**Architecture Migration**:
- ❌ ~~MCP devstream server~~ (eliminated - Direct DB Architecture)
- ✅ Direct SQLite database (`data/devstream.db`) - Primary storage
- ✅ Direct DB tools (`get_direct_client()` methods) - Primary interface
- ✅ Enhanced performance and reliability
- ✅ Reduced system complexity

**Methodology**: Research-Driven Development with Context7
**Enforcement**: Automatic via Hook System + Direct DB Architecture + Auto-Delegation + Strategic Choice Gate

---

*These rules are the foundation of the DevStream system. Violating them causes automatic system malfunctions and rollback.*
<!--
Generated with DevStream v2.0 - Context7-compliant multi-project setup
Generation timestamp: Sun Oct 19 10:17:02 CEST 2025
Template: template_processor.py
-->
