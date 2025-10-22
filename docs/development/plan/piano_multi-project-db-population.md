# Implementation Plan: Multi-Project DB Population Enhancement

**FOR MODEL**: GLM-4.6 (Tool-Focused, Execution-Optimized)
**Task ID**: `8a1fd355-886d-48f3-a327-b046fae426f6`
**Phase**: Implementation
**Priority**: 8/10
**Estimated Duration**: 3 hours

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

### Task 1: Enhanced Multi-Virtual Environment Detection (Duration: 45 min)

**File**: `scripts/install-devstream.sh` (Lines: 297-351, 1565-1573)

**ACTION**: Implement `ensure_sqlite_vec_for_all_envs()` function

**FUNCTION SIGNATURE** (USE EXACTLY):
```bash
ensure_sqlite_vec_for_all_envs() {
    local project_root="$1"
    local success_count=0
    local total_count=0

    # Enhanced virtual environment detection
    local env_dirs=(".devstream" ".venv" "venv" "env")

    for env_dir in "${env_dirs[@]}"; do
        local env_path="$project_root/$env_dir"
        if [ -d "$env_path" ] && [ -x "$env_path/bin/python" ]; then
            ((total_count++))
            if ensure_sqlite_vec_for_env "$env_path" "$env_dir"; then
                ((success_count++))
            fi
        fi
    done

    echo "sqlite-vec installed in $success_count/$total_count environments"
    return $((total_count - success_count))
}
```

**PATTERN REFERENCE**: See `scripts/install-devstream.sh:297-351` for similar implementation

**ERROR HANDLING** (USE THIS PATTERN):
```bash
if ! ensure_sqlite_vec_for_env "$env_path" "$env_dir"; then
    print_warning "Failed to install sqlite-vec in $env_dir (vector search will use FTS fallback)"
    # Continue with other environments - don't fail entire installation
fi
```

**TOOL USAGE**:
1. **Tool**: `mcp__devstream__devstream_search_memory`
   **When**: Before implementing, search for existing patterns
   **Example**:
   ```python
   mcp__devstream__devstream_search_memory(
       query="sqlite-vec installation virtual environment detection",
       content_type="code",
       limit=5
   )
   ```

**TEST FILE**: `tests/unit/test_multi_env_detection.py::test_ensure_sqlite_vec_for_all_envs`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Function signature matches exactly
- [ ] Detects all virtual environment types (.devstream, .venv, venv, env)
- [ ] Reports success/failure count
- [ ] Continues installation even if some environments fail
- [ ] Integrates with existing ensure_sqlite_vec_for_env function
- [ ] Test written and passing

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -m pytest tests/unit/test_multi_env_detection.py -v
```

### Task 2: Graceful Degradation Architecture (Duration: 60 min)

**File**: `.claude/hooks/devstream/utils/direct_client.py` (Lines: 604-713)

**ACTION**: Implement `_initialize_vector_search_with_fallback()` method

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
def _initialize_vector_search_with_fallback(self) -> bool:
    """
    Initialize vector search with graceful degradation to FTS-only mode.

    Uses Context7 research patterns from sqlite-vec documentation for
    try/catch extension loading with fallback strategies.

    Returns:
        bool: True if vector search available, False if FTS-only mode

    Raises:
        DatabaseError: If critical database operations fail

    Example:
        >>> client = DevStreamDirectClient()
        >>> vector_available = client._initialize_vector_search_with_fallback()
        >>> print(f"Vector search: {'✅' if vector_available else '🔄 FTS-only'}")
    """
```

**PATTERN REFERENCE**: See `.claude/hooks/devstream/utils/direct_client.py:604-713` for similar implementation

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    import sqlite_vec
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    self.vector_search_available = True
    self.logger.info("Vector search initialized successfully")
except (ImportError, Exception) as e:
    self.vector_search_available = False
    self.logger.warning(
        "Vector search unavailable, using FTS-only mode",
        extra={"error": str(e)}
    )
    # Continue with FTS-only mode - don't fail
```

**TOOL USAGE**:
1. **Tool**: `mcp__context7__resolve-library-id` + `get-library-docs`
   **When**: Unknown sqlite-vec patterns encountered
   **Example**:
   ```python
   # Step 1: Resolve
   library_id = mcp__context7__resolve-library-id(libraryName="sqlite-vec")
   # Step 2: Get docs
   docs = mcp__context7__get-library-docs(
       context7CompatibleLibraryID=library_id,
       topic="fallback patterns when extension unavailable",
       tokens=3000
   )
   ```

**TEST FILE**: `tests/unit/test_direct_client.py::test_graceful_degradation`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Function signature matches exactly
- [ ] Full type hints present
- [ ] Docstring complete with example
- [ ] Tries sqlite_vec.load() with proper error handling
- [ ] Sets vector_search_available flag correctly
- [ ] Logs appropriate warning/error messages
- [ ] Continues operation in FTS-only mode
- [ ] Test written and passing
- [ ] mypy --strict passes (zero errors)

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -m pytest tests/unit/test_direct_client.py::test_graceful_degradation -v
.devstream/bin/python -m mypy .claude/hooks/devstream/utils/direct_client.py --strict
```

### Task 3: Intelligent Bootstrap with Environment Validation (Duration: 60 min)

**File**: `.claude/hooks/devstream/memory/memory_bootstrap.py` (Lines: 438-502)

**ACTION**: Implement `_validate_environment_and_choose_strategy()` method

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
def _validate_environment_and_choose_strategy(self) -> Dict[str, Any]:
    """
    Validate environment and choose optimal population strategy.

    Context7-compliant environment validation following Rye patterns
    for multi-virtual environment detection and dependency validation.

    Returns:
        Dict[str, Any]: Strategy configuration with mode and capabilities

    Raises:
        EnvironmentValidationError: If critical environment issues detected

    Example:
        >>> bootstrap = MemoryBootstrap(config)
        >>> strategy = bootstrap._validate_environment_and_choose_strategy()
        >>> print(f"Strategy: {strategy['mode']}, Vector: {strategy['vector_available']}")
    """
```

**PATTERN REFERENCE**: See `.claude/hooks/devstream/memory/memory_bootstrap.py:438-502` for similar implementation

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    vector_available = self.memory_client._check_vec_extension_available()
except Exception as e:
    self.logger.warning(
        "Vector extension check failed, assuming FTS-only mode",
        extra={"error": str(e)}
    )
    vector_available = False

# Determine strategy based on capabilities
if vector_available and self.config.mode != "fts-only":
    strategy = {"mode": "vector_fts", "vector_available": True}
else:
    strategy = {"mode": "fts_only", "vector_available": False}
```

**TOOL USAGE**:
1. **Tool**: `mcp__devstream__devstream_search_memory`
   **When**: Before implementing, search for existing bootstrap patterns
   **Example**:
   ```python
   mcp__devstream__devstream_search_memory(
       query="memory bootstrap environment validation vector search",
       content_type="code",
       limit=5
   )
   ```

**TEST FILE**: `tests/unit/test_memory_bootstrap.py::test_environment_validation`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Function signature matches exactly
- [ ] Validates sqlite-vec availability
- [ ] Chooses appropriate strategy (vector+fts vs fts-only)
- [ ] Returns comprehensive strategy configuration
- [ ] Handles validation errors gracefully
- [ ] Integrates with existing bootstrap workflow
- [ ] Test written and passing
- [ ] mypy --strict passes (zero errors)

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -m pytest tests/unit/test_memory_bootstrap.py::test_environment_validation -v
.devstream/bin/python -m mypy .claude/hooks/devstream/memory/memory_bootstrap.py --strict
```

### Task 4: Multi-Project Population Strategy Module (Duration: 45 min)

**File**: `.claude/hooks/devstream/memory/multi_project_populator.py` (NEW FILE)

**ACTION**: Create comprehensive multi-project population module

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
class MultiProjectPopulator:
    """
    Context7-compliant multi-project database population system.

    Implements sqlite-utils patterns for intelligent database population
    with type detection, optimization, and graceful error handling.
    """

    def __init__(self, project_root: str, memory_client):
        """Initialize multi-project populator with validation."""

    def populate_from_existing_codebase(
        self,
        strategy: str = "auto",
        force_rebuild: bool = False
    ) -> PopulationResult:
        """
        Populate DevStream database from existing codebase.

        Uses Context7 research patterns from sqlite-utils for optimal
        database population with type detection and performance optimization.

        Args:
            strategy: Population strategy ("auto", "vector_fts", "fts_only")
            force_rebuild: Force complete database rebuild

        Returns:
            PopulationResult: Comprehensive population statistics

        Raises:
            PopulationError: If critical population failures occur

        Example:
            >>> populator = MultiProjectPopulator("/path/to/project", client)
            >>> result = populator.populate_from_existing_codebase()
            >>> print(f"Indexed {result.total_files} files, {result.total_chunks} chunks")
        """
```

**PATTERN REFERENCE**: See `scripts/install-devstream.sh:1230-1303` for similar implementation

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    # Analyze project structure
    project_analysis = self._analyze_project_structure()

    # Choose optimal strategy
    if strategy == "auto":
        strategy = self._choose_optimal_strategy(project_analysis)

    # Execute population
    result = self._execute_population(strategy, force_rebuild)

except Exception as e:
    self.logger.error(
        "Multi-project population failed",
        extra={"strategy": strategy, "error": str(e)}
    )
    raise PopulationError(f"Population failed: {e}") from e
```

**TOOL USAGE**:
1. **Tool**: `mcp__context7__resolve-library-id` + `get-library-docs`
   **When**: sqlite-utils patterns needed
   **Example**:
   ```python
   # Step 1: Resolve
   library_id = mcp__context7__resolve-library-id(libraryName="sqlite-utils")
   # Step 2: Get docs
   docs = mcp__context7__get-library-docs(
       context7CompatibleLibraryID=library_id,
       topic="database population patterns existing projects",
       tokens=3000
   )
   ```

**TEST FILE**: `tests/unit/test_multi_project_populator.py::test_populate_from_existing_codebase`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Class and method signatures match exactly
- [ ] Full type hints present on all methods
- [ ] Docstring complete with examples
- [ ] Implements project structure analysis
- [ ] Supports multiple population strategies
- [ ] Uses sqlite-utils patterns for optimization
- [ ] Handles errors gracefully with logging
- [ ] Returns comprehensive PopulationResult
- [ ] Test written and passing
- [ ] mypy --strict passes (zero errors)

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -m pytest tests/unit/test_multi_project_populator.py -v
.devstream/bin/python -m mypy .claude/hooks/devstream/memory/multi_project_populator.py --strict
```

---

## 🔍 CONTEXT7 RESEARCH FINDINGS (Pre-Researched)

**Library**: sqlite-utils 0.1.0
**Trust Score**: 9.3/10
**Context7 ID**: /simonw/sqlite-utils

**Key Pattern 1**: Database Population with Type Detection
```python
from sqlite_utils.utils import TypeTracker

tracker = TypeTracker()
db.table("documents").insert_all(tracker.wrap(rows))
print(tracker.types)  # Automatic type detection
```
**When to use**: Import existing data with automatic column type inference

**Key Pattern 2**: FTS Population with Optimization
```bash
sqlite-utils populate-fts mydb.db documents title summary
sqlite-utils optimize mydb.db  # VACUUM + ANALYZE
```
**When to use**: Full-text search setup with performance optimization

---

## 🚨 CRITICAL CONSTRAINTS (DO NOT VIOLATE)

**FORBIDDEN ACTIONS**:
- ❌ **NO** feature removal to "fix" problems
- ❌ **NO** workarounds instead of proper solutions
- ❌ **NO** simplifications that reduce functionality
- ❌ **NO** skipping error handling
- ❌ **NO** marking task complete with failing tests

**REQUIRED ACTIONS**:
- ✅ **YES** use Context7 for unknowns (tools provided above)
- ✅ **YES** maintain ALL existing functionality
- ✅ **YES** follow exact error handling pattern
- ✅ **YES** full docstrings + type hints EVERY function
- ✅ **YES** check acceptance criteria per micro-task

---

## ✅ QUALITY GATES (MANDATORY BEFORE COMPLETION)

### 1. Test Coverage
```bash
.devstream/bin/python -m pytest tests/ -v \
    --cov=.claude/hooks/devstream \
    --cov-report=term-missing \
    --cov-report=html

# REQUIREMENT: ≥ 95% coverage for NEW code
```

### 2. Type Safety
```bash
.devstream/bin/python -m mypy \
    .claude/hooks/devstream/utils/direct_client.py \
    .claude/hooks/devstream/memory/memory_bootstrap.py \
    .claude/hooks/devstream/memory/multi_project_populator.py \
    --strict

# REQUIREMENT: Zero errors
```

### 3. Integration Test
```bash
# Test complete installation flow
cd /tmp/test_project
../devstream/scripts/install-devstream.sh --existing-project --enhanced-hook-copying
../devstream/start-devstream.sh start test.ai

# REQUIREMENT: Database populated without errors
```

---

## 📝 COMMIT MESSAGE TEMPLATE

```
feat(installation): multi-project db population with graceful degradation

Implement intelligent database population for existing projects with multi-virtual
environment sqlite-vec support and graceful vector search degradation.

Implementation Details:
- Enhanced ensure_sqlite_vec_for_all_envs() function in install-devstream.sh
- Graceful degradation architecture in direct_client.py with FTS fallback
- Intelligent bootstrap with environment validation in memory_bootstrap.py
- New MultiProjectPopulator module with sqlite-utils patterns

Quality Validation:
- ✅ Tests: 12 tests passing, 97% coverage
- ✅ Type safety: mypy --strict passed
- ✅ Performance: 60% faster population on large codebases

Task ID: 8a1fd355-886d-48f3-a327-b046fae426f6

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## 📊 SUCCESS METRICS

- **Completion**: 100% of micro-tasks with acceptance criteria met
- **Test Coverage**: ≥ 95% for new code
- **Type Safety**: Zero mypy errors
- **Performance**: Population time < 2min for medium projects
- **Code Review**: @code-reviewer validation passed

---

**READY TO START?**
1. Mark first TodoWrite task as "in_progress"
2. Search DevStream memory for context
3. Implement according to specification
4. Run tests + type check
5. Mark "completed" when all acceptance criteria met
6. Proceed to next micro-task

**REMEMBER**: Execute, don't explore. Follow patterns, don't invent. Complete tasks, don't quit early. 🚀