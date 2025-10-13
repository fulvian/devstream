# Implementation Plan: MCP Server Elimination & Direct Database Architecture

**FOR MODEL**: GLM-4.6 (Tool-Focused, Execution-Optimized)
**Task ID**: `6e63cfeb622dc7f16e9b38316589a5a5`
**Phase**: IMPLEMENTATION
**Priority**: 10/10 (CRITICAL)
**Estimated Duration**: 3.5 hours

---

## 🎯 EXECUTION PROFILE FOR GLM-4.6

You are an **expert coding agent** specialized in **precise execution** of well-defined tasks.

**YOUR STRENGTHS** (leverage these):
- ✅ Tool calling accuracy 90.6% (best-in-class)
- ✅ Efficient token usage (15% fewer than alternatives)
- ✅ Standard coding patterns excellence
- ✅ Integration with Claude Code ecosystem

**YOUR CONSTRAINTS** (respect these):
- ⚠️ AVOID prolonged reasoning (thinking mode costly - 18K tokens)
- ⚠️ FOCUS on execution over exploration
- ⚠️ FOLLOW provided patterns exactly (framework knowledge gaps)
- ⚠️ CHECK syntax precision (13% error rate - mitigate with type hints)
- ⚠️ COMPLETE micro-tasks fully (no early quit - acceptance criteria mandatory)

---

## 📋 MICRO-TASK BREAKDOWN

### Task 1: Create DevStreamDirectClient (Duration: 60 min)

**File**: `.claude/hooks/devstream/utils/direct_client.py` (Lines: 1-200)

**ACTION**: Create robust direct database client to replace MCP server

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
class DevStreamDirectClient:
    """
    Direct database client replacing MCP server.

    Uses ConnectionManager for thread-safe database access with Context7 patterns.
    Maintains 100% API compatibility with MCP client for seamless migration.

    Args:
        db_path: Path to database file (validated)

    Attributes:
        connection_manager: Thread-safe connection manager instance

    Example:
        >>> client = DevStreamDirectClient()
        >>> await client.store_memory("content", "code", ["keyword"])
        'memory_id_123'
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialize direct client with ConnectionManager."""

    async def store_memory(
        self,
        content: str,
        content_type: str,
        keywords: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Store content in semantic_memory table directly."""

    async def search_memory(
        self,
        query: str,
        content_type: Optional[str] = None,
        limit: int = 10
    ) -> Optional[Dict[str, Any]]:
        """Search semantic_memory with vector similarity."""
```

**PATTERN REFERENCE**: See `.claude/hooks/devstream/utils/mcp_client.py:105-165` for similar implementation

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    # Implementation
    result = operation()
except DatabaseError as e:
    logger.error(
        "Database operation failed",
        extra={"context": value, "error": str(e)}
    )
    raise DatabaseException("Database operation failed") from e
```

**TOOL USAGE**:
1. **Tool**: `mcp__devstream__devstream_search_memory`
   **When**: Before implementing, search for existing patterns
   **Example**:
   ```python
   mcp__devstream__devstream_search_memory(
       query="direct database client implementation",
       content_type="code",
       limit=5
   )
   ```

2. **Tool**: `mcp__context7__resolve-library-id` + `get-library-docs`
   **When**: Unknown library/pattern encountered
   **Example**:
   ```python
   # Step 1: Resolve
   library_id = mcp__context7__resolve-library-id(libraryName="sqlite3")
   # Step 2: Get docs
   docs = mcp__context7__get-library-docs(
       context7CompatibleLibraryID=library_id,
       topic="async context manager patterns",
       tokens=3000
   )
   ```

**TEST FILE**: `tests/unit/test_direct_client.py::test_store_memory`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Function signature matches exactly
- [ ] Full type hints present
- [ ] Docstring complete with example
- [ ] Error handling implemented
- [ ] Test written and passing
- [ ] mypy --strict passes (zero errors)

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -m pytest tests/unit/test_direct_client.py::test_store_memory -v
.devstream/bin/python -m mypy .claude/hooks/devstream/utils/direct_client.py --strict
```

### Task 2: Update PostToolUse Hook (Duration: 45 min)

**File**: `.claude/hooks/devstream/memory/post_tool_use.py` (Lines: 72-75)

**ACTION**: Replace MCP client import with direct client

**PATTERN**: Change import statement from:
```python
from mcp_client import get_mcp_client
```
to:
```python
from direct_client import get_direct_client as get_mcp_client
```

**TOOL USAGE**:
1. **Tool**: `mcp__devstream__devstream_search_memory`
   **When**: Before implementing, search for existing patterns
   **Example**:
   ```python
   mcp__devstream__devstream_search_memory(
       query="mcp client import replacement in hooks",
       content_type="code",
       limit=5
   )
   ```

**ACCEPTANCE CRITERIA**:
- [ ] Import statement updated
- [ ] Hook functionality tested
- [ ] No MCP server dependency
- [ ] Direct database calls working

### Task 3: Update PreToolUse Hook (Duration: 45 min)

**File**: `.claude/hooks/devstream/memory/pre_tool_use.py` (Lines: 35-71)

**ACTION**: Replace MCP client with direct client for memory search

**PATTERN**: Same as Task 2 - update import and verify functionality.

**TEST FILE**: `tests/unit/test_pre_tool_use_hook.py::test_memory_search`

### Task 4: Update User Query Context Enhancer (Duration: 30 min)

**File**: `.claude/hooks/devstream/context/user_query_context_enhancer.py` (Lines: 28-62)

**ACTION**: Replace MCP client for context enhancement functionality

**PATTERN**: Update import statement and verify context search works.

### Task 5: Add Robustness Patterns (Duration: 30 min)

**File**: `.claude/hooks/devstream/utils/robustness_patterns.py` (Lines: 1-100)

**ACTION**: Create Context7-inspired robustness patterns for database operations

**FUNCTION SIGNATURE**:
```python
async def with_interrupt_handling(
    operation: Callable,
    timeout_seconds: int = 30
) -> Any:
    """Execute operation with interrupt handling capability.

    Uses APSW-style interrupt patterns for graceful cancellation.

    Args:
        operation: Async callable to execute
        timeout_seconds: Maximum execution time

    Example:
        result = await with_interrupt_handling(
            lambda: conn.execute("SELECT ..."),
            timeout_seconds=30
        )
    """
```

**CONTEXT7 PATTERN REFERENCE**: APSW interrupt handling from research findings

### Task 6: Create Feature Flag System (Duration: 15 min)

**File**: `.claude/hooks/devstream/config/feature_flags.py` (Lines: 1-50)

**ACTION**: Create feature flag for gradual migration from MCP to direct DB

**FUNCTION SIGNATURE**:
```python
def is_direct_db_enabled() -> bool:
    """Check if direct database mode is enabled."""
    return os.getenv('DEVSTREAM_DIRECT_DB_ENABLED', 'false').lower() == 'true'
```

### Task 7: Integration Testing (Duration: 60 min)

**File**: `tests/integration/test_direct_db_migration.py` (Lines: 1-200)

**ACTION**: Create comprehensive integration tests

**TEST SCENARIOS**:
- Store and retrieve memory records
- Search functionality with vector embeddings
- Task operations (create/list/update)
- Concurrent access patterns
- Performance benchmarking

**ACCEPTANCE CRITERIA**:
- [ ] All MCP functionality replicated
- [ ] Performance meets target (<20ms per operation)
- [ ] Thread safety verified
- [ ] 95%+ test coverage
- [ ] Zero mypy errors

---

## 🔍 CONTEXT7 RESEARCH FINDINGS (Pre-Researched)

**Database Libraries Researched**:
- APSW (Trust Score: 8.0) - Thread-safe connections, interrupt handling
- aiosqlite (Trust Score: 7.7) - Async context managers
- ConnectionManager (Production-ready) - WAL mode, pooling, health monitoring

**Key Findings**:
- APSW provides native thread-safe connections with interrupt handling
- aiosqlite async context managers eliminate blocking I/O
- ConnectionManager already implements robust patterns needed

**Pattern Examples**:
```python
# APSW Thread Safety + Interrupt Handling
connection.set_busy_timeout(30000)  # 30s timeout
if operation_cancelled:
    connection.interrupt()  # Graceful cancellation

# aiosqlite Async Context Manager
async with aiosqlite.connect(db_path) as db:
    await db.execute("INSERT INTO table ...")
    await db.commit()  # Automatic on success
```

**When to use**: Use APSW for performance-critical operations, aiosqlite for general async patterns.

---

## 🚨 CRITICAL CONSTRAINTS (DO NOT VIOLATE)

**FORBIDDEN ACTIONS**:
- ❌ **NO** removal of features (find proper solution instead)
- ❌ **NO** workarounds (implement correctly using Context7)
- ❌ **NO** simplifications that reduce functionality
- ❌ **NO** skipping tests or type hints
- ❌ **NO** early quit on complex tasks (complete fully)

**REQUIRED ACTIONS**:
- ✅ **YES** use `.devstream/bin/python` for ALL commands
- ✅ **YES** follow TodoWrite plan strictly
- ✅ **YES** use Context7 for unknowns (tools provided)
- ✅ **YES** maintain ALL existing functionality
- ✅ **YES** full type hints + docstrings EVERY function
- ✅ **YES** tests for EVERY feature (95%+ coverage)

---

## ✅ QUALITY GATES (MANDATORY BEFORE COMPLETION)

### 1. Environment Verification
```bash
# Verify venv and Python version
.devstream/bin/python --version  # Must be 3.11.x
.devstream/bin/python -m pip list | grep -E "(cchooks|aiohttp|structlog)"
```

### 2. Implementation
Follow plan in this document

### 3. Testing
```bash
# After EVERY micro-task
.devstream/bin/python -m pytest tests/unit/test_{{module}}.py -v
.devstream/bin/python -m mypy {{file_path}} --strict

# Before completion (ALL tests)
.devstream/bin/python -m pytest tests/ -v \
    --cov={{module}} \
    --cov-report=term-missing \
    --cov-report=html

# REQUIREMENT: ≥95% coverage, 100% pass rate
```

### 4. Performance Validation
```bash
# Benchmark database operations
python scripts/benchmark_direct_vs_mcp.py

# TARGET: <20ms per operation (vs 1000ms MCP)
```

### 5. Memory Usage Validation
```bash
# Monitor memory usage during testing
python scripts/memory_usage_monitor.py

# TARGET: <50MB total (vs 200MB MCP server)
```

---

## 📝 COMMIT MESSAGE TEMPLATE

```
refactor(direct-db): Replace MCP server with direct database connections

Replace resource-intensive MCP server with direct SQLite connections
using existing ConnectionManager infrastructure. Improves performance 100x, reduces
memory usage 10x, eliminates process leak issues.

Implementation Details:
- Created DevStreamDirectClient with full MCP API compatibility
- Updated 4 critical hooks to use direct database connections
- Added Context7-inspired robustness patterns (interrupt handling, async context managers)
- Implemented feature flag system for gradual migration
- Added comprehensive integration tests

Quality Validation:
- ✅ Tests: 50 tests passing, 98% coverage
- ✅ Type safety: mypy --strict passed
- ✅ Performance: 15ms avg vs 1500ms MCP
- ✅ Memory: 35MB vs 200MB server

Task ID: 6e63cfeb622dc7f16e9b38316589a5a5

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## 📊 SUCCESS METRICS

- **Completion**: 100% of micro-tasks with acceptance criteria met
- **Test Coverage**: ≥ 95% for new code
- **Type Safety**: Zero mypy errors
- **Performance**: Meets target <20ms per operation
- **Code Review**: @code-reviewer validation passed
- **Memory Usage**: <50MB total (vs 200MB MCP server)

---

## 🚀 EXECUTION CHECKLIST

1. [ ] **CREATE** TodoWrite tasks from this plan
2. [ ] **VERIFY** environment: `.devstream/bin/python --version`
3. [ ] **SEARCH** DevStream memory for context
4. [ ] **START** first TodoWrite task (mark "in_progress")
5. [ ] **IMPLEMENT** according to plan specifications
6. [ ] **TEST** after each micro-task
7. [ ] **COMPLETE** task when all criteria met
8. [ ] **REPEAT** steps 4-7 for remaining tasks
9. [ ] **VALIDATE** complete implementation (all quality gates)
10. [ ] **COMMIT** if all tests pass

---

## 🔍 DEVSTREAM MEMORY ACCESS

Search for relevant context anytime:
```python
mcp__devstream__devstream_search_memory(
    query="MCP server elimination direct database",
    content_type="code",
    limit=10
)
```

---

## 📊 SUCCESS CRITERIA

- [ ] All TodoWrite tasks completed
- [ ] Tests pass 100%
- [ ] Coverage ≥ 95%
- [ ] mypy --strict passes (zero errors)
- [ ] Performance meets target: <20ms operations
- [ ] Memory usage <50MB total
- [ ] @code-reviewer validation passed
- [ ] All acceptance criteria met

---

**READY TO IMPLEMENT?**

Start with the first TodoWrite task. Execute precisely. Test thoroughly. Complete fully. 🚀

**Remember**: You are GLM-4.6 - your strength is **precise execution** of well-defined tasks. The strategic thinking is done. Now execute flawlessly. 💪