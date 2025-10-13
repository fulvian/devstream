# CLAUDE.md - DevStream Project Rules

**Version**: 2.2.0 | **Date**: 2025-10-09 | **Status**: Production Ready

<critical_notice>
⚠️ **MANDATORY SYSTEM RULES** - These rules are **NON-NEGOTIABLE** and integrated into DevStream through automatic hooks. Violations cause system malfunctions and automatic rollback.
</critical_notice>

---

## 🎯 System Architecture Overview

<system_architecture>
DevStream combines 4 core systems:
1. **Task Lifecycle Management** - Structured workflow with phase tracking
2. **Semantic Memory System** - Automatic code/decision storage with vector search
3. **Context Injection** - Hybrid Context7 (5000 tokens) + DevStream Memory (2000 tokens)
4. **Hook Automation** - PreToolUse, PostToolUse, UserPromptSubmit via cchooks

**Operation Mode**: Fully automatic - hooks execute without manual intervention.
</system_architecture>

---

## 🤖 Custom Agent System - Multi-Stack Development

<agent_system>
**Status**: Phase 3 Complete ✅ | 17 Agents Production Ready

### Hierarchy (4 Levels)

**Level 1: ORCHESTRATOR**
- `@tech-lead` - Task decomposition, multi-agent coordination, architectural decisions
- **NEW v2.2.0**: Tier-based delegation (complexity routing)

**Level 2: DOMAIN SPECIALISTS** (6 agents)
```
@python-specialist     → Python 3.11+, FastAPI, async, pytest
@typescript-specialist → TypeScript, React, Next.js, Server Components
@rust-specialist       → Ownership, async/await, memory safety
@go-specialist         → Goroutines, channels, cloud-native
@database-specialist   → PostgreSQL/MySQL/SQLite, query tuning
@devops-specialist     → Docker, Kubernetes, CI/CD, IaC
```

**Level 3: TASK SPECIALISTS** (5 agents)
```
@api-architect, @performance-optimizer, @testing-specialist
@documentation-specialist, @refactoring-specialist
```

**Level 4: QUALITY ASSURANCE** (6 agents)
```
@code-reviewer        → MANDATORY before commits (OWASP Top 10)
@security-auditor     → Security-focused analysis
@debugger             → Bug diagnosis and resolution
@integration-specialist → Integration testing
@migration-specialist → Data/code migrations
```

### Usage Patterns

<pattern type="direct">
**Single-language task**: `@python-specialist Create FastAPI endpoint`
</pattern>

<pattern type="orchestrated">
**Multi-stack feature**: `@tech-lead Build full-stack user management`
→ Delegates: @python-specialist (backend) → @typescript-specialist (frontend) → @code-reviewer (validation)
</pattern>

<pattern type="quality_gate">
**MANDATORY before commit**: `@code-reviewer Review src/api/users.py:45-120`
</pattern>

### Agent Capabilities Matrix

| Agent | Primary Use | Tools | Restrictions |
|-------|------------|-------|--------------|
| @tech-lead | Multi-stack coordination | Task, Read, Glob, Grep | Limited to planning |
| Domain Specialists (6) | Language-specific implementation | Full access | None |
| Task Specialists (5) | Specialized operations | Full access | None |
| @code-reviewer | Quality gate (MANDATORY) | Read, Grep, Glob, Bash | Analysis only |

### Memory Optimization

**Problem Solved**: JavaScript heap exhaustion during agent execution  
**Solution**: `node --max-old-space-size=8192 --expose-gc start-production.js`  
**Status**: Production stable ✅
</agent_system>

---

## 🎯 Tier-Based Delegation Policy (v2.2.0 - Token Optimization)

<tier_based_delegation>
**Purpose**: Reduce token overhead by -70% through strategic delegation  
**Impact**: 0-7K tokens/task → 1K average | 28→100 tasks/5h capacity

### Tier Structure

**TIER 1: Monolithic First** (60% of tasks - 0 tokens)
<tier id="1">
- **Triggers**: Single file, <50K tokens, <1h duration, straightforward
- **Agent**: NONE (Sonnet 4.5 solo)
- **Examples**: Bug fixes, single endpoint, config changes
- **Decision**: Default for simple tasks
</tier>

**TIER 2: Single Specialist** (30% of tasks - 2K tokens)
<tier id="2">
- **Triggers**: File pattern match (*.py → @python-specialist) + single-language
- **Agent**: 1 specialist ONLY (no orchestration)
- **File Mapping**:
  - `.py` → @python-specialist
  - `.ts/.tsx` → @typescript-specialist
  - `.sql` → @database-specialist
  - `.rs` → @rust-specialist
  - `.go` → @go-specialist
  - `.md` docs → @documentation-specialist
- **Decision**: Clear language-specific task
</tier>

**TIER 3: Multi-Agent Orchestration** (5% of tasks - 7K tokens)
<tier id="3">
- **Triggers**: Multi-stack OR >100K context OR architectural decisions
- **Agent**: @tech-lead → delegates N specialists
- **Examples**: Full-stack features, system refactoring
- **Decision**: Requires cross-domain coordination
</tier>

**TIER 4: Quality Gate** (5% of tasks - MANDATORY - 1K tokens)
<tier id="4">
- **Triggers**: `git commit` command (automatic detection)
- **Agent**: @code-reviewer (NON-NEGOTIABLE)
- **Examples**: EVERY commit, EVERY security-sensitive change
- **Decision**: Cannot be skipped
</tier>

### Decision Algorithm (Executable)

```python
def get_delegation_tier(context: Dict[str, Any]) -> Tuple[int, Optional[str], float]:
    """
    Determine delegation tier based on task context.
    
    Returns: (tier_number, agent_name, confidence)
    """
    # Tier 1: Monolithic (no delegation)
    if is_simple_task(context):
        return (1, None, 1.0)
    
    # Tier 2: Single specialist
    if has_clear_file_pattern(context) and is_single_language(context):
        agent = match_specialist_by_file(context["file_path"])
        return (2, agent, 0.95)
    
    # Tier 3: Multi-agent orchestration
    if is_multi_stack(context) or context.get("context_size", 0) > 100_000:
        return (3, "@tech-lead", 0.70)
    
    # Tier 4: Quality gate (MANDATORY)
    if is_commit_operation(context):
        return (4, "@code-reviewer", 1.0)
    
    # Default: Tier 1 (monolithic)
    return (1, None, 1.0)
```

### Configuration (.env.devstream)

```bash
DEVSTREAM_AUTO_DELEGATION_TIER1_ENABLED=true   # Monolithic (default)
DEVSTREAM_AUTO_DELEGATION_TIER2_THRESHOLD=0.95 # Single specialist
DEVSTREAM_AUTO_DELEGATION_TIER3_THRESHOLD=0.70 # Multi-agent
DEVSTREAM_AUTO_DELEGATION_QUALITY_GATE=true    # Mandatory reviewer
```

### Cost Analysis (Claude Code Pro Max $100/month)

**Token Budget**: 200K tokens/session

**Before Optimization**:
- Task overhead: 7K tokens (always multi-agent)
- Tasks per session: 200K / 7K ≈ 28 tasks
- Tasks per 5h: 28 tasks
- Monthly capacity: ~28 × 30 = 840 tasks

**After Optimization**:
- Task overhead: 1K tokens average (tier-based)
- Tasks per session: 200K / 1K ≈ 200 tasks
- Tasks per 5h: 100 tasks (3.5x improvement)
- Monthly capacity: ~100 × 30 = 3000 tasks (3.5x increase)

**Cost Savings**: $100 now covers 3.5x more work (equivalent to $280 value at old rate)

### All 17 Agents Preserved

**CRITICAL**: Tier-based policy uses agents *strategically*, not *always*. All 17 agents remain available for appropriate complexity levels.
</tier_based_delegation>

---

## 📋 MANDATORY WORKFLOW: 7 Sequential Steps

<seven_step_workflow>
**EVERY task MUST follow this sequence**:

### 🚨 Step 0: ENFORCEMENT GATE (MANDATORY)

<enforcement_gate>
**Triggers** (ANY condition):
- Task duration > 15 minutes
- Requires code implementation (Write, Edit tools)
- Involves architectural decisions
- Multi-file or multi-component
- Requires Context7 research

**Implementation**: `task_first_handler.py` + `enforcement_gate.py` (blocking validation)

**Flow**:
```
User Request → Complexity Analysis
     ↓
IF criteria met → 🔒 STOP EXECUTION
     ↓
"⚠️ DevStream Protocol Required
OPTIONS:
✅ [RECOMMENDED] Follow DevStream 7-step workflow
⚠️ [OVERRIDE] Skip protocol (NO quality assurance)

Risks: No Context7, No @code-reviewer, No testing, No approval

Choose: [1] Protocol [2] Override [Cancel]"
     ↓
Protocol → Execute 7 steps | Override → Log + Warn + Direct execution
```

**Override Tracking**:
- Every override logged with timestamp, justification, disabled gates
- **Audit Trail**: Query with `mcp__devstream__devstream_search_memory` using keyword **"protocol-override"**

**Violations**: Automatic detection → rollback → restart with enforcement
</enforcement_gate>

### Step 1: DISCUSSION (MANDATORY)

<step id="1" name="DISCUSSION">
**Actions**:
- Present problem/objective
- Discuss trade-offs, constraints
- Obtain consensus

**Hook**: Registers discussions in memory (`content_type: "decision"`)  
**Validation**: ≥1 discussion record required

**NEW v2.2.0**: Task creation moved to Step 1 (prevents data loss)
- `task_first_handler.py` enforces automatic task creation
- Interactive gate: Protocol/Override/Cancel options
- Draft tasks >7 days auto-archived
</step>

### Step 2: ANALYSIS (MANDATORY)

<step id="2" name="ANALYSIS">
**Actions**:
- Analyze codebase for similar patterns
- Identify files to modify
- Estimate complexity
- Define acceptance criteria

**Hook**: Requires context injection from memory  
**Validation**: Verify codebase pattern analysis completed
</step>

### Step 3: RESEARCH (MANDATORY - Context7)

<step id="3" name="RESEARCH">
**Actions**:
- Use Context7 for technical decisions
- Research best practices
- Document findings
- Validate approach

**Hook**: Context7 integration automatic via PreToolUse  
**Validation**: Verify Context7 docs in context injection log
</step>

### Step 4: PLANNING (MANDATORY - TodoWrite + Implementation Plan)

<step id="4" name="PLANNING">
**Actions**:
- Create TodoWrite list (micro-tasks MAX 10-15 min)
- Define dependencies and completion criteria
- **NEW v2.2.0**: Generate implementation plan (model-specific template)

**Dual Storage**:
- **Database**: SQLite with metadata + task linkage
- **Filesystem**: `docs/development/plan/piano_[task-slug].md`

**Templates**:
- GLM-4.6: Execution-focused, micro-tasks, syntax precision
- Sonnet 4.5: Architectural, ADRs, component-level

**Hook**: `implementation_plan_generator.py` automates plan at Step 4  
**Validation**: Task list + implementation plan must exist before implementation
</step>

### Step 5: APPROVAL (MANDATORY + Strategic Choice Gate)

<step id="5" name="APPROVAL">
**Actions**:
- Present complete plan + Context7 findings
- Obtain explicit approval ("OK", "proceed", "approved")
- **NEW v2.2.0 - Strategic Choice Gate**: Choose implementation model:
  - **Option A**: Continue with **Sonnet 4.5** (architectural work, 30+ hour focus)
  - **Option B**: Handoff to **GLM-4.6** (precise execution, ~70% cost savings)

**GLM Handoff Workflow** (if Option B):
1. Generate handoff prompt with context transfer
2. Save plan + handoff to DB and filesystem
3. Display handoff instructions
4. Close Sonnet session → Start GLM session

**Hook**: Memory registers approval + model choice  
**Validation**: Approval record + model selection before commit
</step>

### Step 6: IMPLEMENTATION (MANDATORY - Guided)

<step id="6" name="IMPLEMENTATION">
**Actions**:
- One micro-task at a time
- Mark "in_progress" → work → mark "completed"
- Document with docstrings + type hints

**Hook**: PostToolUse registers code automatically  
**Validation**: Every written file registered in memory
</step>

### Step 7: VERIFICATION/TEST (MANDATORY)

<step id="7" name="VERIFICATION">
**Actions**:
- Tests for EVERY feature
- 95%+ coverage requirement
- Validate performance
- E2E integration tests
- Error handling verification

**Hook**: Requires test validation before completion  
**Validation**: Test results documented in memory
</step>
</seven_step_workflow>

---

## 📄 Task Lifecycle Management

<task_lifecycle>
### Task Creation (Step 1 - MANDATORY)

<rule type="task_creation">
**WHEN**: Work > 15 min OR code/architecture/research  
**CRITICAL**: Task creation at Step 1 (old protocol: Step 5)

**Process**:
- ✅ `task_first_handler.py` enforces at Step 1
- ✅ Automatic complexity detection
- ✅ Interactive enforcement gate
- ✅ Use `mcp__devstream__devstream_create_task`
- ✅ Define: title, description, task_type, priority (1-10), phase_name
- ✅ Draft cleanup: >7 days auto-archived

**Forbidden**:
- ❌ Manual tasks without MCP
- ❌ Creating tasks at Step 5
</rule>

### Task Execution

<rule type="task_execution">
**WHEN**: During implementation

**Process**:
- ✅ Mark "active" via `mcp__devstream__devstream_update_task`
- ✅ Follow 7-step workflow
- ✅ Update progress continuously
- ✅ Register decisions/learnings
- ✅ TodoWrite real-time tracking

**Forbidden**:
- ❌ Multiple tasks simultaneously without approval
</rule>

### Task Completion

<rule type="task_completion">
**WHEN**: All acceptance criteria met

**Process**:
- ✅ Verify TodoWrite "completed"
- ✅ Tests 100% pass
- ✅ Mark "completed"
- ✅ Register lessons learned
- ✅ Commit and push (if requested)

**Forbidden**:
- ❌ Mark "completed" with failing tests
- ❌ Pending TodoWrite items
</rule>
</task_lifecycle>

---

## 💾 Memory System

<memory_system>
### Automatic Storage (PostToolUse Hook)

<rule type="memory_storage">
**WHEN**: Automatic after EVERY tool execution

**Content Types**: `code`, `documentation`, `context`, `output`, `error`, `decision`, `learning`

**Process**: AUTOMATIC
1. PostToolUse hook
2. Content preview (300 chars)
3. Keywords extraction
4. Vector embeddings (Ollama)
5. SQLite + sqlite-vec storage

**User Action**: None - fully automatic
</rule>

### Memory Search (PreToolUse Hook)

<rule type="memory_search">
**WHEN**: Automatic before EVERY tool execution

**Flow**:
1. Detect libraries (Context7)
2. Search DevStream memory
3. Assemble hybrid context
4. Inject in Claude context
5. Token budget management

**Algorithm**: Hybrid search (semantic + keyword) via RRF  
**Threshold**: 0.5 relevance  
**Token Budget**: Context7 5000 + Memory 2000

**User Action**: None - fully automatic
</rule>

### Manual Operations (OPTIONAL)

<rule type="manual_memory">
**Tools**:
- `mcp__devstream__devstream_store_memory` (content, content_type, keywords)
- `mcp__devstream__devstream_search_memory` (query, content_type, limit)

**Use Case**: Advanced queries, critical context pre-session end  
**Note**: Automatic system handles 99% of cases
</rule>
</memory_system>

---

## 📝 Context Injection

<context_injection>
### Context7 Integration (PreToolUse Hook)

<rule type="context7">
**Triggers**: Import statements, library mentions, code patterns, documentation requests

**Process**: AUTOMATIC
1. Context7 detect
2. Retrieve docs via `mcp__context7__get-library-docs`
3. Inject (max 5000 tokens)
4. Priority ordering (official docs > examples > best practices)

**Config** (.env.devstream):
```bash
DEVSTREAM_CONTEXT7_ENABLED=true
DEVSTREAM_CONTEXT7_AUTO_DETECT=true
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=5000
```
</rule>

### DevStream Memory Context (PreToolUse Hook)

<rule type="memory_context">
**Priority Order**:
1. Context7 Documentation (5000 tokens)
2. DevStream Memory (2000 tokens - related code/decisions)
3. Current File Context (remaining budget)

**Process**: AUTOMATIC
1. Hybrid search (RRF)
2. Relevance filtering (threshold 0.5)
3. Token budget enforcement
4. Context assembly
5. Injection

**Config** (.env.devstream):
```bash
DEVSTREAM_CONTEXT_INJECTION_ENABLED=true
DEVSTREAM_CONTEXT_MAX_TOKENS=2000
DEVSTREAM_CONTEXT_RELEVANCE_THRESHOLD=0.5
```
</rule>

### Quality Optimizations (2025-10-02)

<optimization_summary status="production_ready">
**Improvements**:
1. Code-aware queries (83% size reduction: 313→50 chars)
2. Relevance filtering (min_relevance=0.03, 50% noise reduction)
3. Token budget enforcement (2000 token max strict)
4. Context7 advisory pattern (non-blocking recommendations)
5. Library name normalization (lowercase for compatibility)

**Performance** (validated 2025-10-02):
- Query construction: <1ms avg
- Token estimation: ±1 token accuracy
- Memory search: +25% relevance
- False positives: -30% reduction
- Context7 advisory: 100% success
</optimization_summary>
</context_injection>

---

## 🐍 Python Environment (MANDATORY)

<python_environment>
### 🚨 CRITICAL RULE: Always Use .devstream Venv

<rule type="python_venv" priority="critical">
**Configuration**:
- Venv: `.devstream`
- Python: 3.11.x
- Interpreter: `.devstream/bin/python`

**Session Start Checklist** (EVERY session):
```bash
# 1. Verify venv exists
[ ! -d ".devstream" ] && python3.11 -m venv .devstream

# 2. Verify Python version (MUST be 3.11.x)
.devstream/bin/python --version

# 3. Verify critical dependencies
.devstream/bin/python -m pip list | grep -E "(cchooks|aiohttp|structlog)"
```

**FORBIDDEN**:
- ❌ `python script.py`
- ❌ `python3 script.py`
- ❌ `uv run script.py` (non-persistent)

**REQUIRED**:
- ✅ `.devstream/bin/python script.py`
- ✅ `.devstream/bin/python -m pytest`
- ✅ `.devstream/bin/python -m pip install package`
</rule>

### First-Time Setup

<rule type="venv_setup">
**When**: Venv missing or corrupted

**Steps**:
```bash
# 1. Create venv
python3.11 -m venv .devstream

# 2. Upgrade pip
.devstream/bin/python -m pip install --upgrade pip

# 3. Install requirements
.devstream/bin/python -m pip install -r requirements.txt

# 4. Install hook dependencies
.devstream/bin/python -m pip install cchooks>=0.1.4 aiohttp>=3.8.0 \
  structlog>=23.0.0 python-dotenv>=1.0.0

# 5. Verify
.devstream/bin/python -m pip list | head -20
```
</rule>

### Hook System Configuration

<rule type="hook_config">
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

**CRITICAL**: Hooks MUST use `.devstream/bin/python`, NOT system Python
</rule>
</python_environment>

---

## 🛠️ Tools & Configuration

<tools_configuration>
### Context7 Usage (MANDATORY for Research)

<rule type="context7_usage">
**Workflow**:
1. `mcp__context7__resolve-library-id` (library name → Context7 ID)
2. `mcp__context7__get-library-docs` (ID → docs max 5000 tokens)
3. Analyze findings
4. Apply research-backed patterns

**Forbidden**:
- ❌ Skip Context7 for new technologies
</rule>

### TodoWrite Usage (MANDATORY for Planning)

<rule type="todowrite">
**WHEN**: Non-trivial tasks (>15 min)

**Process**:
- ✅ Create TodoWrite BEFORE implementation
- ✅ Micro-tasks 10-15 min
- ✅ Mark "in_progress" → work → "completed"
- ✅ ONE task "in_progress" at a time

**Format**:
```json
{
  "content": "Imperative form",
  "activeForm": "Present continuous",
  "status": "pending|in_progress|completed"
}
```

**Forbidden**:
- ❌ Start without TodoWrite
- ❌ Mark "completed" with pending sub-tasks
</rule>

### Testing Requirements (MANDATORY)

<rule type="testing">
**Coverage**:
- ✅ 95%+ for NEW code
- ✅ 100% pass rate before commit
- ✅ E2E integration tests
- ✅ Performance validation
- ✅ Error handling

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

**Thresholds**:
- Unit: 95%+
- Integration: 85%+
- E2E: 70%+

**Async Testing**: pytest-asyncio for async functions, proper fixture scoping, AsyncMock for retries

**Forbidden**:
- ❌ Commit with failing tests
- ❌ Commit without tests
</rule>

### pytest-asyncio Patterns (Context7 Research)

<patterns type="async_testing">
**Pattern 1: Async Fixtures**
```python
@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def mcp_client():
    client = await create_mcp_client()
    yield client
    await client.close()
```

**Pattern 2: Error Testing**
```python
@pytest.mark.asyncio
async def test_error_handling():
    with pytest.raises(ConnectionError, match="timeout"):
        await failing_function()
```

**Pattern 3: AsyncMock for Retries**
```python
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

**Pattern 4: Async Context Manager**
```python
@pytest.mark.asyncio
async def test_async_context_manager():
    async with AsyncDatabaseConnection() as conn:
        result = await conn.execute("SELECT 1")
        assert result is not None
```

**Pattern 5: Concurrent Operations**
```python
@pytest.mark.asyncio
async def test_concurrent_operations():
    tasks = [async_op("task1"), async_op("task2"), async_op("task3")]
    results = await asyncio.gather(*tasks)
    assert len(results) == 3
```

**Pattern 6: Async Generators**
```python
@pytest.mark.asyncio
async def test_async_generator():
    async def data_stream():
        for i in range(3):
            yield f"data-{i}"
            await asyncio.sleep(0.01)
    
    results = [item async for item in data_stream()]
    assert results == ["data-0", "data-1", "data-2"]
```

**Pattern 7: Timeout Testing**
```python
@pytest.mark.asyncio
async def test_async_timeout():
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(slow_async_function(), timeout=0.1)
```

**Common Pitfalls to Avoid**:
- ❌ Missing `@pytest.mark.asyncio` decorator
- ❌ Fixture scope mismatch
- ❌ Not awaiting async calls
- ❌ Mixing sync/async improperly
- ❌ Not cleaning up async resources
</patterns>

### .coveragerc Configuration (Async Testing)

```ini
[run]
source = .claude/hooks/devstream
omit =
    */tests/*
    */test_*
    __pycache__
concurrency = gevent

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__:

[html]
directory = htmlcov
```

**CRITICAL**: `concurrency = gevent` required for async testing

### CI/CD Integration (GitHub Actions)

```yaml
name: Test Protocol Enforcement

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11]

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m venv .devstream
        .devstream/bin/pip install -e .[test]

    - name: Run unit tests
      run: |
        .devstream/bin/python -m pytest tests/unit/ -v \
          --cov=.claude/hooks/devstream \
          --cov-report=xml \
          --cov-fail-under=95

    - name: Run integration tests
      run: |
        .devstream/bin/python -m pytest tests/integration/ -v \
          --cov-append \
          --cov-fail-under=85

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```
</tools_configuration>

---

## 📖 Documentation Requirements

<documentation>
### Code Documentation (MANDATORY)

<rule type="code_docs">
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

**Forbidden**:
- ❌ Missing docstrings
- ❌ Missing type hints
</rule>

### Project Documentation (MANDATORY)

<rule type="project_docs">
**Structure**:
- `docs/architecture/` (system design - MANDATORY new systems)
- `docs/api/` (API reference - MANDATORY APIs)
- `docs/deployment/` (MANDATORY production)
- `docs/guides/` (MANDATORY user-facing features)
- `docs/development/` (MANDATORY complex features)
- `docs/tutorials/` (OPTIONAL)

**Rules**:
- ✅ Create docs for EVERY major feature
- ✅ Update BEFORE task complete
- ✅ Include code examples
- ✅ Keep in sync

**Forbidden**:
- ❌ .md files in root (except README.md, CLAUDE.md, PROJECT_STRUCTURE.md)
- ❌ Outdated documentation
</rule>

### Progress Documentation (MANDATORY)

<rule type="progress_docs">
**Must Document**:
- TodoWrite tracking
- Implementation notes per phase
- Lessons learned per completed task
- Decision rationale
- Test results

**Storage**: Automatic via PostToolUse hook (`content_type: "learning"`, `"decision"`)
</rule>
</documentation>

---

## 🎯 Quality Standards

<quality_standards>
### Code Quality (MANDATORY)

<rule type="code_quality">
**Type Safety**:
- ✅ Full type hints ALL functions/methods
- ✅ `mypy --strict` (zero errors)
- ❌ `Any` type hints
- ❌ mypy errors in production

**Error Handling**:
- ✅ Structured exception hierarchy
- ✅ Logging for EVERY exception
- ✅ Graceful degradation
- ✅ User-friendly messages
- ❌ Bare `except:`
- ❌ Silent failures

**Performance**:
- ✅ async/await for I/O
- ✅ Connection pooling
- ✅ Token budget enforcement
- ✅ Performance testing
- ❌ Blocking I/O in async
- ❌ No performance validation

**Maintainability**:
- ✅ SOLID principles
- ✅ Single responsibility
- ✅ Max function length 50 lines
- ✅ Max cyclomatic complexity 10
- ❌ God objects
- ❌ Cryptic abbreviations
</rule>

### Architecture Quality (MANDATORY)

<rule type="architecture_quality">
**Separation**:
- ✅ Clear module boundaries
- ✅ Layered architecture (hooks → utils → core)
- ✅ Interface segregation
- ❌ Circular dependencies
- ❌ Tight coupling

**Configuration**:
- ✅ Environment-based (.env.devstream)
- ✅ Validate ALL config
- ✅ Defaults and documentation
- ❌ Hardcoded values
- ❌ Config in code

**Logging**:
- ✅ Structured logging (structlog)
- ✅ Context ALL log messages
- ✅ Appropriate levels (DEBUG/INFO/WARNING/ERROR)
- ✅ Log rotation
- ❌ `print()` statements
- ❌ Logging sensitive data
</rule>
</quality_standards>

---

## 🚀 Implementation Patterns

<implementation_patterns>
### Research-Driven Development (MANDATORY)

<pattern type="research_driven">
**Sequence**:
1. **RESEARCH** - Context7 → best practices → document findings
2. **DESIGN** - Research-based architecture → clear interfaces
3. **IMPLEMENT** - Validated patterns → one micro-task at a time
4. **TEST** - 95%+ coverage → validate assumptions
5. **DOCUMENT** - Lessons learned → update docs

**Enforcement**: Hook registers research findings in memory
</pattern>

### Micro-Task Execution (MANDATORY)

<pattern type="micro_task">
**Sequence**:
1. **ANALYZE** - Break down feature → 10-15 min micro-tasks → dependencies
2. **PLAN** - TodoWrite list → completion criteria
3. **EXECUTE** - One task at a time → mark "in_progress" → work → "completed"
4. **VERIFY** - Test after EVERY task → verify integration
5. **INTEGRATE** - Merge codebase → update docs

**Enforcement**: TodoWrite tool tracks compliance
</pattern>

### Approval Workflow (MANDATORY)

<pattern type="approval">
**Sequence**:
1. **DISCUSS** - Present approach + trade-offs → identify risks
2. **RESEARCH** - Context7 validation → alternative approaches
3. **APPROVE** - Explicit approval → confirm acceptance criteria
4. **IMPLEMENT** - Follow approved approach → no deviations without approval
5. **REVIEW** - Validate results → document learnings

**Enforcement**: Memory registers approval as "decision"
</pattern>
</implementation_patterns>

---

## 📊 Success Metrics

<success_metrics>
### Development Metrics (MANDATORY Targets)

<metrics type="development">
- ✅ Task Completion: 100%
- ✅ Test Coverage: 95%+ NEW code
- ✅ Test Pass Rate: 100%
- ✅ Code Quality: Zero mypy errors
- ✅ Cyclomatic Complexity: Max 10
- ✅ Documentation Coverage: 100% docstrings
- ✅ Performance: Meet/exceed targets
</metrics>

### Process Metrics (MANDATORY Tracking)

<metrics type="process">
- ✅ Research Quality: Context7 usage for EVERY major decision
- ✅ Collaboration: 100% approval workflow adherence
- ✅ Learning: Documented lessons learned per phase
- ✅ Innovation: Research-backed technology choices
- ✅ Delivery: On-time (planned vs actual)
- ✅ Memory Usage: Automatic storage tracking
- ✅ Context Injection: Automatic injection rate

**Storage**: Automatic via DevStream memory system
</metrics>
</success_metrics>

---

## 📁 File Organization

<file_organization>
### Project Structure (MANDATORY)

<rule type="file_structure">
**CRITICAL**: ALWAYS follow PROJECT_STRUCTURE.md

**Documentation**:
- ✅ `docs/{architecture,api,deployment,guides,development,tutorials}/`
- ❌ .md files in root (except README.md, CLAUDE.md, PROJECT_STRUCTURE.md)

**Tests**:
- ✅ `tests/{unit,integration,fixtures}/`
- ❌ Test files in root
- ❌ Tests mixed with source

**Naming**:
- Documentation → kebab-case (devstream-guide.md)
- Code → snake_case (pre_tool_use.py)

**File Creation Checklist**:
1. Check PROJECT_STRUCTURE.md
2. Identify correct directory
3. Use naming convention
4. Verify directory exists
5. Create file
</rule>
</file_organization>

---

## 🚨 FUNDAMENTAL RULE - Problem Solving

<problem_solving>
### ⚡⚡⚡ USE CONTEXT7 TO SOLVE - NEVER SIMPLIFY ⚡⚡⚡

<rule type="problem_solving" priority="critical">
**MANDATORY**:
- ✅ Use Context7 to research solution
- ✅ Research best practices
- ✅ Implement research-backed solution
- ✅ Maintain ALL features functional
- ✅ Test thoroughly

**FORBIDDEN**:
- ❌ Disable features to "fix" problem
- ❌ Remove functionality as workaround
- ❌ Create temporary workarounds
- ❌ Simplify to avoid complexity
- ❌ Skip research step

**Enforcement**: Code review rejects workarounds and feature disabling
</rule>
</problem_solving>

---

## 🔮 Future Phases & Roadmap

<future_phases>
### Phase 4 (Advanced Specialists)

- **@security-auditor** - OWASP Top 10, penetration testing, compliance
- **@debugger** - Advanced debugging workflows, root cause analysis
- **@refactoring-specialist** - Code smell detection, SOLID compliance
- **@integration-specialist** - Cross-system integration, API versioning

### Phase 5 (AI-Powered Optimization)

- **Pattern Matcher Fine-tuning** - Learn from delegation history
- **Context Budget ML** - Predictive token allocation
- **Quality Gate Automation** - AI-powered code review prioritization
- **Cross-Session Learning** - Knowledge graph from past tasks
</future_phases>

---

## 📚 System Integration Reference

<system_integration>
### Hook Integration Points

| Hook | Location | Trigger | Purpose | Status |
|------|----------|---------|---------|--------|
| PreToolUse | `.claude/hooks/devstream/memory/pre_tool_use.py` | Before EVERY tool | Context7 + Memory injection | ✅ Active |
| PostToolUse | `.claude/hooks/devstream/memory/post_tool_use.py` | After EVERY tool | Store code/docs/context | ✅ Active |
| UserPromptSubmit | `.claude/hooks/devstream/context/user_query_context_enhancer.py` | Every user prompt | Enhance query with context | ✅ Active |
| SessionEnd | `.claude/hooks/devstream/sessions/session_end.py` | Session exit | Generate session summary | ⚠️ **DISABLED** (2025-10-12) |
| PreCompact | `.claude/hooks/devstream/sessions/pre_compact.py` | Before /compact | Save summary pre-compaction | ⚠️ **DISABLED** (2025-10-12) |
| SessionStart | `.claude/hooks/devstream/sessions/session_start.py` | Session startup | Display previous summary | ⚠️ **DISABLED** (2025-10-12) |

### Direct Database Access Points

| Component | Access Method | Tools | Purpose | Status |
|-----------|---------------|-------|---------|--------|
| Task Management | Direct MCP | `mcp__devstream__devstream_*` | Task lifecycle | ✅ Active |
| Memory System | Direct MCP | `mcp__devstream__devstream_*` | Semantic storage | ✅ Active |
| Implementation Plans | Direct MCP | `mcp__devstream__devstream_*` | Plan management | ✅ Active |
| Vector Search | Direct DB + Ollama | N/A | Memory retrieval | ✅ Active |
| Session Tracking | Direct DB | N/A | Cross-session | ✅ Active |

### Cross-Session Summary System

<notice type="system_disabled">
⚠️ **SYSTEM DISABLED (2025-10-12)** - Cross-session summary system interferes with Claude Code auto-compacting. All session hooks disabled via `.env.devstream`.

**Re-enable**: Set `DEVSTREAM_HOOK_SESSIONSTART=true`, `DEVSTREAM_HOOK_SESSION_END=true`, `DEVSTREAM_HOOK_PRE_COMPACT=true`
</notice>

### Direct Database Integration (v2.2.0+)

<integration type="direct_db">
**Architecture**: Direct SQLite database connection (MCP server eliminated)

**Database**: `data/devstream.db` (sqlite-vec enabled)

**Direct MCP Tools** (no server required):
- Task Management: `mcp__devstream__devstream_create_task`, `mcp__devstream__devstream_update_task`, `mcp__devstream__devstream_list_tasks`
- Memory System: `mcp__devstream__devstream_store_memory`, `mcp__devstream__devstream_search_memory`
- Implementation Plans: `mcp__devstream__devstream_create_implementation_plan`, `mcp__devstream__devstream_get_implementation_plan`, `mcp__devstream__devstream_update_implementation_plan`, `mcp__devstream__devstream_list_implementation_plans`
- Memory Operations: `mcp__devstream__devstream_trigger_checkpoint`

**Key Benefits**:
- ✅ Eliminated MCP server dependency
- ✅ Direct database access (faster, more reliable)
- ✅ Reduced system complexity
- ✅ Lower memory footprint
- ✅ Better error handling

**Database Schema**:
- `tasks` - Task lifecycle management
- `memory` - Semantic memory with vector embeddings
- `implementation_plans` - Model-specific implementation plans
- `sessions` - Cross-session tracking
</integration>

### Implementation Plans System (v2.2.0+)

<integration type="implementation_plans">
**Architecture**: Direct database integration with dual storage pattern

**Database Schema**: `implementation_plans` table
- Direct SQLite access via `mcp__devstream__devstream_*` tools
- Full metadata, task linkage, model type tracking
- No MCP server dependency

**Dual Storage Pattern**:
- **Database**: Direct SQLite storage with full metadata
- **Filesystem**: `docs/development/plan/piano_[task-slug].md` for human readability

**Model-Specific Templates**:
- **GLM-4.6**: `templates/implementation-plan-glm46.md` (execution-focused)
- **Sonnet 4.5**: `templates/implementation-plan-sonnet45.md` (architectural)
- **Handoff**: `templates/handoff-prompt-glm46.md` (Sonnet→GLM context transfer)

**Direct DB Tools**:
- `mcp__devstream__devstream_create_implementation_plan` - Create new plan
- `mcp__devstream__devstream_get_implementation_plan` - Retrieve plan by task ID
- `mcp__devstream__devstream_update_implementation_plan` - Update existing plan
- `mcp__devstream__devstream_list_implementation_plans` - List all plans

**Strategic Choice Gate**: Interactive model selection at Step 5 with auto plan generation
**Hook Integration**: `implementation_plan_generator.py` automates at Step 4
</integration>

### Environment Configuration (.env.devstream)

```bash
# Core System (MANDATORY)
DEVSTREAM_MEMORY_ENABLED=true
DEVSTREAM_MEMORY_FEEDBACK_LEVEL=minimal

# Database (MANDATORY - Direct DB Architecture)
DEVSTREAM_DB_PATH=data/devstream.db
DEVSTREAM_DIRECT_DB_ENABLED=true
DEVSTREAM_MCP_SERVER_ENABLED=false

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
DEVSTREAM_HOOK_SESSIONSTART=false    # Disabled to prevent auto-compacting interference
DEVSTREAM_HOOK_SESSION_END=false     # Disabled to prevent auto-compacting interference
DEVSTREAM_HOOK_PRE_COMPACT=false     # Disabled to prevent auto-compacting interference

# Logging (RECOMMENDED)
DEVSTREAM_LOG_LEVEL=INFO
DEVSTREAM_LOG_PATH=~/.claude/logs/devstream/

# Vector Search (MANDATORY)
DEVSTREAM_VECTOR_SEARCH_ENABLED=true
DEVSTREAM_VECTOR_EMBEDDINGS_MODEL=gemma3  # Ollama model
DEVSTREAM_VECTOR_DB_ENABLED=true
```
</system_integration>

---

<document_metadata>
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
- ❌ ~~MCP devstream server~~ (eliminated)
- ✅ Direct SQLite database (`data/devstream.db`)
- ✅ Direct MCP tools (`mcp__devstream__devstream_*`)
- ✅ Enhanced performance and reliability
- ✅ Reduced system complexity

**Methodology**: Research-Driven Development with Context7
**Enforcement**: Automatic via Hook System + Direct DB Integration + Auto-Delegation + Strategic Choice Gate
</document_metadata>

---

*These rules are the foundation of the DevStream system. Violating them causes automatic system malfunctions and rollback.*