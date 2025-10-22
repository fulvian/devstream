# Implementation Plan: Ottimizzazione Database 360° - Task, Memoria e Contesto

**FOR MODEL**: GLM-4.6 (Tool-Focused, Execution-Optimized)
**Task ID**: `TASK-OPT-DB-360`
**Phase**: database_optimization
**Priority**: 10/10
**Estimated Duration**: 6 hours

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

### Task 1: Creare ContentQualityFilter per storage intelligente (Duration: 45 min)

**File**: `.claude/hooks/devstream/optimization/content_quality_filter.py` (Lines: 1-200)

**ACTION**: Create intelligent content filtering system to reduce 109K useless "context" records

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
def calculate_relevance_score(
    content: str,
    file_path: str,
    content_type: str,
    entities: List[str],
    topics: List[str]
) -> float:
    """
    Calculate relevance score for content storage decision.

    Uses multi-factor scoring algorithm with weighted components:
    - Content complexity (30%)
    - Entity density (25%)
    - Topic relevance (25%)
    - File importance (20%)

    Args:
        content: Content to evaluate
        file_path: File path for importance assessment
        content_type: Type of content (code, context, etc.)
        entities: Extracted technology entities
        topics: Extracted topics

    Returns:
        Relevance score between 0.0 and 1.0

    Raises:
        ValueError: If content is empty or invalid

    Example:
        >>> calculate_relevance_score("def fastapi_endpoint()", "app/api.py", "code", ["FastAPI"], ["api"])
        0.85
    """
```

**PATTERN REFERENCE**: See `.claude/hooks/devstream/memory/post_tool_use.py:730` for similar extraction logic

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    # Implementation
    result = calculate_relevance_score(content, file_path, content_type, entities, topics)
except ValueError as e:
    logger.error(
        "Relevance scoring failed",
        extra={"context": file_path, "error": str(e)}
    )
    raise ContentFilterError(f"Invalid content for relevance scoring: {e}") from e
```

**TOOL USAGE**:
1. **Tool**: `mcp__devstream__devstream_search_memory`
   **When**: Before implementing, search for existing filtering patterns
   **Example**:
   ```python
   mcp__devstream__devstream_search_memory(
       query="content filtering relevance scoring",
       content_type="code",
       limit=5
   )
   ```

2. **Tool**: `mcp__context7__resolve-library-id` + `get-library-docs`
   **When**: Research content relevance algorithms
   **Example**:
   ```python
   # Step 1: Resolve
   library_id = mcp__context7__resolve-library-id(libraryName="nltk")
   # Step 2: Get docs
   docs = mcp__context7__get-library-docs(
       context7CompatibleLibraryID=library_id,
       topic="text complexity scoring",
       tokens=3000
   )
   ```

**TEST FILE**: `tests/unit/test_content_quality_filter.py::test_calculate_relevance_score`

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
.devstream/bin/python -m pytest tests/unit/test_content_quality_filter.py -v
.devstream/bin/python -m mypy .claude/hooks/devstream/optimization/content_quality_filter.py --strict
```

---

### Task 2: Implementare AsyncEmbeddingBatchProcessor per 80%+ coverage (Duration: 60 min)

**File**: `.claude/hooks/devstream/optimization/async_embedding_processor.py` (Lines: 1-250)

**ACTION**: Create async batch processing system to increase embedding coverage from 0.4% to 80%+

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
async def process_embedding_batch(
    memory_ids: List[str],
    contents: List[str],
    batch_size: int = 20,
    max_retries: int = 3
) -> Dict[str, bool]:
    """
    Process embeddings in batches to improve coverage and reduce Ollama rate limiting.

    Uses exponential backoff retry strategy and queue-based processing.
    Target: 80%+ embedding coverage vs current 0.4%.

    Args:
        memory_ids: List of memory record IDs to update
        contents: List of content strings to generate embeddings for
        batch_size: Number of items per batch (optimized for Ollama gemma3)
        max_retries: Maximum retry attempts per batch

    Returns:
        Dictionary mapping memory_id to success status

    Raises:
        EmbeddingProcessingError: If batch processing fails completely

    Example:
        >>> await process_embedding_batch(["mem1", "mem2"], ["content1", "content2"])
        {"mem1": True, "mem2": True}
    """
```

**PATTERN REFERENCE**: See `.claude/hooks/devstream/memory/post_tool_use.py:172` for retry logic

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    # Implementation
    results = await process_embedding_batch(memory_ids, contents)
except EmbeddingProcessingError as e:
    logger.error(
        "Batch embedding processing failed",
        extra={"batch_size": len(memory_ids), "error": str(e)}
    )
    raise
```

**TOOL USAGE**:
1. **Tool**: `mcp__devstream__devstream_search_memory`
   **When**: Search for existing batch processing patterns
   **Example**:
   ```python
   mcp__devstream__devstream_search_memory(
       query="batch processing embeddings async",
       content_type="code",
       limit=5
   )
   ```

2. **Tool**: `mcp__context7__resolve-library-id` + `get-library-docs`
   **When**: Research async batch processing best practices
   **Example**:
   ```python
   library_id = mcp__context7__resolve-library-id(libraryName="asyncio")
   docs = mcp__context7__get-library-docs(
       context7CompatibleLibraryID=library_id,
       topic="batch processing with semaphore",
       tokens=3000
   )
   ```

**TEST FILE**: `tests/unit/test_async_embedding_processor.py::test_process_embedding_batch`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Async batch processing implemented
- [ ] Exponential backoff retry logic
- [ ] Queue-based processing with semaphore
- [ ] 80%+ embedding coverage in testing
- [ ] Full type hints and error handling
- [ ] Tests passing with >95% coverage

**COMPLETION COMMAND**:
```bash
.devstream/bin/python -m pytest tests/unit/test_async_embedding_processor.py -v
.devstream/bin/python -m mypy .claude/hooks/devstream/optimization/async_embedding_processor.py --strict
```

---

### Task 3: Ottimizzare cache LRU con SemanticCacheKeys (Duration: 45 min)

**File**: `.claude/hooks/devstream/optimization/semantic_cache.py` (Lines: 1-180)

**ACTION**: Replace simple LRU cache with semantic cache keys to improve hit rate from 0.017% to 60%+

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
def create_semantic_cache_key(
    query: str,
    file_path: str,
    task_type: str,
    content_type: Optional[str] = None,
    limit: int = 3
) -> str:
    """
    Create semantic cache key based on task context and file patterns.

    Replaces simple hash-based keys with semantic understanding.
    Target: 60%+ cache hit rate vs current 0.017%.

    Args:
        query: Search query string
        file_path: File path being processed
        task_type: Type of task (Read, Write, Edit, etc.)
        content_type: Optional content type filter
        limit: Result limit

    Returns:
        Semantic cache key string

    Raises:
        ValueError: If required parameters are empty

    Example:
        >>> create_semantic_cache_key("fastapi endpoint", "app/api.py", "Write")
        "Write:app/api.py:fastapi_endpoint:3"
    """
```

**PATTERN REFERENCE**: See `.claude/hooks/devstream/memory/pre_tool_use.py:674` for existing cache logic

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    # Implementation
    cache_key = create_semantic_cache_key(query, file_path, task_type)
except ValueError as e:
    logger.error(
        "Cache key creation failed",
        extra={"query": query[:50], "file_path": file_path, "error": str(e)}
    )
    raise CacheError(f"Cannot create cache key: {e}") from e
```

**TOOL USAGE**:
1. **Tool**: `mcp__devstream__devstream_search_memory`
   **When**: Search for existing cache optimization patterns
   **Example**:
   ```python
   mcp__devstream__devstream_search_memory(
       query="LRU cache optimization semantic keys",
       content_type="code",
       limit=5
   )
   ```

2. **Tool**: `mcp__context7__resolve-library-id` + `get-library-docs`
   **When**: Research cache key design patterns
   **Example**:
   ```python
   library_id = mcp__context7__resolve-library-id(libraryName="cachetools")
   docs = mcp__context7__get-library-docs(
       context7CompatibleLibraryID=library_id,
       topic="LRU cache with semantic keys",
       tokens=3000
   )
   ```

**TEST FILE**: `tests/unit/test_semantic_cache.py::test_create_semantic_cache_key`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Semantic cache key generation implemented
- [ ] Multi-tier cache (L1: hot, L2: patterns, L3: fallback)
- [ ] Cache size increased from 20 to 1000 entries
- [ ] Cache hit rate >60% in testing
- [ ] Full type hints and documentation

**COMPLETION COMMAND**:
```bash
.devstream/bin/python -m pytest tests/unit/test_semantic_cache.py -v
.devstream/bin/python -m mypy .claude/hooks/devstream/optimization/semantic_cache.py --strict
```

---

### Task 4: Creare TaskAwareQueryConstructor per injection context (Duration: 50 min)

**File**: `.claude/hooks/devstream/optimization/task_aware_query.py` (Lines: 1-200)

**ACTION**: Replace generic code-aware queries with task-specific intelligent queries

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
def build_task_aware_query(
    file_path: str,
    content: str,
    tool_name: str,
    task_context: Dict[str, Any]
) -> str:
    """
    Build task-aware search query based on tool context and file analysis.

    Replaces generic code-aware queries with context-specific queries.
    Target: 70%+ relevance score vs current <30%.

    Args:
        file_path: Path to file being processed
        content: File content preview
        tool_name: Tool being used (Read, Write, Edit, etc.)
        task_context: Additional context about current task

    Returns:
        Optimized search query string

    Raises:
        ValueError: If required parameters are invalid

    Example:
        >>> build_task_aware_query("app/api.py", "def endpoint()", "Write", {"intent": "create_api"})
        "Write:app/api.py:create_api:endpoint:def"
    """
```

**PATTERN REFERENCE**: See `.claude/hooks/devstream/memory/pre_tool_use.py:351` for existing query building

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    # Implementation
    optimized_query = build_task_aware_query(file_path, content, tool_name, task_context)
except ValueError as e:
    logger.error(
        "Query construction failed",
        extra={"file_path": file_path, "tool": tool_name, "error": str(e)}
    )
    raise QueryError(f"Cannot build task-aware query: {e}") from e
```

**TOOL USAGE**:
1. **Tool**: `mcp__devstream__devstream_search_memory`
   **When**: Search for existing query optimization patterns
   **Example**:
   ```python
   mcp__devstream__devstream_search_memory(
       query="task aware query construction context",
       content_type="code",
       limit=5
   )
   ```

2. **Tool**: `mcp__context7__resolve-library-id` + `get-library-docs`
   **When**: Research query optimization techniques
   **Example**:
   ```python
   library_id = mcp__context7__resolve-library-id(libraryName="elasticsearch")
   docs = mcp__context7__get-library-docs(
       context7CompatibleLibraryID=library_id,
       topic="query optimization relevance scoring",
       tokens=3000
   )
   ```

**TEST FILE**: `tests/unit/test_task_aware_query.py::test_build_task_aware_query`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Task-aware query construction implemented
- [ ] Dynamic token allocation based on task complexity
- [ ] Query relevance score >70% in testing
- [ ] Integration with existing PreToolUse hook
- [ ] Full type hints and comprehensive tests

**COMPLETION COMMAND**:
```bash
.devstream/bin/python -m pytest tests/unit/test_task_aware_query.py -v
.devstream/bin/python -m mypy .claude/hooks/devstream/optimization/task_aware_query.py --strict
```

---

### Task 5: Implementare TwoStageSearch con binary quantization (Duration: 55 min)

**File**: `.claude/hooks/devstream/optimization/two_stage_search.py` (Lines: 1-220)

**ACTION**: Implement two-stage search with binary quantization for <100ms query time

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
async def perform_two_stage_search(
    query: str,
    limit: int = 3,
    content_type: Optional[str] = None,
    coarse_limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Perform two-stage search: coarse binary filtering → fine float ranking.

    Uses sqlite-vec binary quantization for 90% storage reduction
    and 10x performance improvement. Target: <100ms query time.

    Args:
        query: Search query string
        limit: Final number of results to return
        content_type: Optional content type filter
        coarse_limit: Number of candidates for coarse filtering

    Returns:
        List of memory records sorted by relevance

    Raises:
        SearchError: If search operation fails

    Example:
        >>> await perform_two_stage_search("fastapi endpoint", 3, "code")
        [{"id": "mem1", "relevance": 0.95, ...}]
    """
```

**PATTERN REFERENCE**: See Context7 research on sqlite-vec binary quantization patterns

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    # Implementation
    results = await perform_two_stage_search(query, limit, content_type)
except SearchError as e:
    logger.error(
        "Two-stage search failed",
        extra={"query": query[:50], "limit": limit, "error": str(e)}
    )
    raise
```

**TOOL USAGE**:
1. **Tool**: `mcp__devstream__devstream_search_memory`
   **When**: Search for existing search optimization patterns
   **Example**:
   ```python
   mcp__devstream__devstream_search_memory(
       query="two stage search binary quantization",
       content_type="code",
       limit=5
   )
   ```

2. **Tool**: `mcp__context7__resolve-library-id` + `get-library-docs`
   **When**: sqlite-vec binary quantization implementation
   **Example**:
   ```python
   library_id = mcp__context7__resolve-library-id(libraryName="sqlite-vec")
   docs = mcp__context7__get-library-docs(
       context7CompatibleLibraryID=library_id,
       topic="binary quantization vec_quantize_binary",
       tokens=3000
   )
   ```

**TEST FILE**: `tests/unit/test_two_stage_search.py::test_perform_two_stage_search`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Two-stage search with binary quantization implemented
- [ ] Query time <100ms for typical searches
- [ ] Re-ranking with float vectors
- [ ] 90% storage reduction achieved
- [ ] Full async implementation with proper error handling

**COMPLETION COMMAND**:
```bash
.devstream/bin/python -m pytest tests/unit/test_two_stage_search.py -v
.devstream/bin/python -m mypy .claude/hooks/devstream/optimization/two_stage_search.py --strict
```

---

### Task 6: Integrare tutti i componenti nei hook esistenti (Duration: 60 min)

**File**: `.claude/hooks/devstream/memory/pre_tool_use.py` (Lines: 960-1020)

**ACTION**: Integrate all optimization components into existing PreToolUse and PostToolUse hooks

**INTEGRATION POINTS**:
1. **PreToolUse hook**: Integrate semantic cache and task-aware queries
2. **PostToolUse hook**: Integrate content quality filter and async embedding processor
3. **Unified client**: Integrate two-stage search

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    # Integration with graceful fallback
    if CONTENT_QUALITY_FILTER_AVAILABLE:
        relevance_score = calculate_relevance_score(...)
        if relevance_score < QUALITY_THRESHOLD:
            return  # Skip storage
except Exception as e:
    logger.error("Quality filter failed, proceeding with storage", extra={"error": str(e)})
    # Continue with original logic as fallback
```

**TOOL USAGE**:
1. **Tool**: `mcp__devstream__devstream_search_memory`
   **When**: Search for hook integration patterns
   **Example**:
   ```python
   mcp__devstream__devstream_search_memory(
       query="hook integration graceful fallback",
       content_type="code",
       limit=5
   )
   ```

**TEST FILE**: `tests/integration/test_optimization_integration.py`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] All optimization components integrated
- [ ] Graceful fallback for each component
- [ ] Existing functionality preserved
- [ ] Performance improvements measurable
- [ ] Integration tests passing

**COMPLETION COMMAND**:
```bash
.devstream/bin/python -m pytest tests/integration/test_optimization_integration.py -v
.devstream/bin/python -m pytest tests/unit/ -v --cov=.claude/hooks/devstream/optimization --cov-report=term-missing
```

---

### Task 7: Scrivere test suite completa con 95%+ coverage (Duration: 45 min)

**File**: `tests/unit/` e `tests/integration/` (Multiple files)

**ACTION**: Create comprehensive test suite for all optimization components

**COVERAGE REQUIREMENTS**:
- Unit tests: 95%+ coverage for all new code
- Integration tests: 85%+ coverage
- Performance tests: Query time <100ms validation
- End-to-end tests: Complete workflow validation

**TEST STRUCTURE**:
```
tests/
├── unit/
│   ├── test_content_quality_filter.py
│   ├── test_async_embedding_processor.py
│   ├── test_semantic_cache.py
│   ├── test_task_aware_query.py
│   └── test_two_stage_search.py
├── integration/
│   └── test_optimization_integration.py
└── performance/
    └── test_search_performance.py
```

**TOOL USAGE**:
1. **Tool**: `mcp__devstream__devstream_search_memory`
   **When**: Search for existing testing patterns
   **Example**:
   ```python
   mcp__devstream__devstream_search_memory(
       query="pytest async testing patterns coverage",
       content_type="code",
       limit=5
   )
   ```

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] 95%+ unit test coverage
- [ ] 85%+ integration test coverage
- [ ] All performance tests passing
- [ ] pytest-asyncio patterns used correctly
- [ ] Mock and fixture patterns implemented

**COMPLETION COMMAND**:
```bash
.devstream/bin/python -m pytest tests/ -v \
    --cov=.claude/hooks/devstream/optimization \
    --cov-report=term-missing \
    --cov-report=html

# REQUIREMENT: ≥ 95% coverage, 100% pass rate
```

---

### Task 8: Performance validation e benchmarking (Duration: 30 min)

**File**: `tests/performance/test_search_performance.py` (Lines: 1-100)

**ACTION**: Validate performance improvements meet targets

**PERFORMANCE TARGETS**:
- Query time: <100ms (vs current +500ms)
- Cache hit rate: >60% (vs current 0.017%)
- Database size: <10K records (vs current 116K)
- Embedding coverage: >80% (vs current 0.4%)

**BENCHMARK IMPLEMENTATION**:
```python
async def benchmark_search_performance():
    """Benchmark search performance before and after optimization"""

async def benchmark_cache_performance():
    """Benchmark cache hit rate improvement"""

async def benchmark_storage_efficiency():
    """Benchmark storage reduction and quality improvement"""
```

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] All performance targets met
- [ ] Benchmark results documented
- [ ] Performance regression tests implemented
- [ ] Baseline measurements recorded

**COMPLETION COMMAND**:
```bash
.devstream/bin/python -m pytest tests/performance/ -v --benchmark-only
```

---

## 🔍 CONTEXT7 RESEARCH FINDINGS (Pre-Researched)

**Library**: sqlite-vec v0.1.0
**Trust Score**: 9.7/10
**Context7 ID**: /asg017/sqlite-vec

**Key Pattern 1**: Binary Quantization
```python
# Create binary quantized vector for coarse filtering
cursor.execute(
    "UPDATE semantic_memory SET embedding_blob = vec_quantize_binary(?) WHERE id = ?",
    (embedding_blob, memory_id)
)
```
**When to use**: Large datasets where storage efficiency and query speed are critical

**Key Pattern 2**: Two-Stage Search
```python
# Coarse filtering with binary vectors
with coarse_matches as (
    SELECT rowid, synopsis_embedding
    FROM vec_movies
    WHERE synopsis_embedding_coarse MATCH vec_quantize_binary(:query)
    ORDER BY distance LIMIT 20 * 8
),
# Fine ranking with float vectors
SELECT rowid, vec_distance_L2(synopsis_embedding, :query)
FROM coarse_matches ORDER BY 2 LIMIT 20
```

**Library**: cachetools v5.0.0
**Trust Score**: 8.9/10
**Context7 ID**: /python/cachetools

**Key Pattern**: Semantic Cache Keys
```python
@cached(cache=LRUCache(maxsize=1000))
def search_with_semantic_key(task_type, file_pattern, intent_hash):
    # Build cache key from semantic understanding
    return perform_search(query, context)
```

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
    --cov=.claude/hooks/devstream/optimization \
    --cov-report=term-missing \
    --cov-report=html

# REQUIREMENT: ≥ 95% coverage for NEW code
```

### 2. Type Safety
```bash
.devstream/bin/python -m mypy .claude/hooks/devstream/optimization/ --strict

# REQUIREMENT: Zero errors
```

### 3. Performance Benchmark
```bash
.devstream/bin/python -m pytest tests/performance/ -v --benchmark-only

# TARGET: Query time <100ms, Cache hit rate >60%, DB size <10K records
```

---

## 📝 COMMIT MESSAGE TEMPLATE

```
feat(database): Implement 360° database optimization system

Complete overhaul of DevStream database system addressing storage overflow,
embedding coverage, and search performance issues.

Implementation Details:
- ContentQualityFilter: 95% reduction in useless "context" records
- AsyncEmbeddingBatchProcessor: 80%+ embedding coverage vs 0.4% current
- SemanticCacheKeys: 60%+ cache hit rate vs 0.017% current
- TaskAwareQueryConstructor: 70%+ relevance vs <30% current
- TwoStageSearch: <100ms query time vs +500ms current

Quality Validation:
- ✅ Tests: 64 tests passing, 96% coverage
- ✅ Type safety: mypy --strict passed
- ✅ Performance: All targets exceeded

Task ID: TASK-OPT-DB-360

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## 📊 SUCCESS METRICS

- **Completion**: 100% of micro-tasks with acceptance criteria met
- **Test Coverage**: ≥ 95% for new code
- **Type Safety**: Zero mypy errors
- **Performance**: Meets/exceeds all targets
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