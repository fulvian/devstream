# Implementation Plan: Context7 Direct Client Integration - Hybrid Architecture

**FOR MODEL**: GLM-4.6 (Tool-Focused, Execution-Optimized)
**Task ID**: context7-direct-client-hybrid
**Phase**: implementation
**Priority**: 9/10
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

### **IMPLEMENTATION STRATEGY**: Hybrid Architecture with Fallback

**Architecture Pattern**:
```
Phase 1: MCP Server (100%) + Direct Client (0%) - Baseline
Phase 2: MCP Server (90%) + Direct Client (10%) - Gradual rollout
Phase 3: MCP Server (50%) + Direct Client (50%) - A/B testing
Phase 4: MCP Server (10%) + Direct Client (90%) - Majority migration
Phase 5: MCP Server (0%) + Direct Client (100%) + MCP Fallback - Complete
```

### Task 1: Context7 Direct HTTP Client (Duration: 90 min)

**File**: `.claude/hooks/devstream/utils/context7_direct_client.py` (Lines: 1-200)

**ACTION**: Implementare Context7DirectHttpClient con aiohttp ottimizzato

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
class Context7DirectHttpClient:
    """
    Direct HTTP client for Context7 API with optimized aiohttp connection pooling.
    Provides library resolution, documentation retrieval, and graceful fallback.

    Attributes:
        session: aiohttp ClientSession with optimized connection pooling
        api_key: Context7 API key from environment
        base_url: Context7 API base URL
        cache: LRU cache for responses
        circuit_breaker: Circuit breaker for fault tolerance
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.context7.com",
        cache_size: int = 100,
        circuit_breaker_threshold: int = 3
    ) -> None:
        """
        Initialize Context7 Direct HTTP Client.

        Args:
            api_key: Context7 API key (from ENV if None)
            base_url: Context7 API base URL
            cache_size: LRU cache size for responses
            circuit_breaker_threshold: Failure threshold for circuit breaker
        """

    async def resolve_library_id(
        self,
        library_name: str
    ) -> Optional[str]:
        """
        Resolve library name to Context7 library ID via direct HTTP API.

        Args:
            library_name: Library/framework name to resolve

        Returns:
            Context7 library ID (format: /org/project) or None

        Raises:
            Context7APIError: If API call fails
            CircuitBreakerError: If circuit breaker is open
        """

    async def get_library_docs(
        self,
        library_id: str,
        topic: Optional[str] = None,
        tokens: int = 5000
    ) -> Optional[str]:
        """
        Get documentation for library from Context7 via direct HTTP API.

        Args:
            library_id: Context7 library ID (format: /org/project)
            topic: Optional specific topic
            tokens: Maximum tokens to retrieve

        Returns:
            Documentation string or None

        Raises:
            Context7APIError: If API call fails
            CircuitBreakerError: If circuit breaker is open
        """
```

**PATTERN REFERENCE**: See `.claude/hooks/devstream/utils/context7_client.py:35-150` for similar implementation

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    async with self.session.get(url, params=params) as response:
        response.raise_for_status()
        data = await response.json()
        return self._extract_library_id(data)
except aiohttp.ClientError as e:
    logger.error(
        "Context7 API call failed",
        extra={"library_name": library_name, "error": str(e)}
    )
    self.circuit_breaker.record_failure()
    raise Context7APIError(f"Failed to resolve library: {library_name}") from e
```

**TOOL USAGE**:
1. **Tool**: `mcp__devstream__devstream_search_memory`
   **When**: Before implementing, search for existing HTTP client patterns
   **Example**:
   ```python
   mcp__devstream__devstream_search_memory(
       query="aiohttp client connection pooling retry patterns",
       content_type="code",
       limit=5
   )
   ```

2. **Tool**: `mcp__context7__resolve-library-id` + `get-library-docs`
   **When**: Test against existing MCP implementation
   **Example**:
   ```python
   # Step 1: Resolve
   library_id = mcp__context7__resolve-library-id(libraryName="aiohttp")
   # Step 2: Get docs
   docs = mcp__context7__get-library-docs(
       context7CompatibleLibraryID=library_id,
       topic="connection pooling",
       tokens=3000
   )
   ```

**TEST FILE**: `tests/unit/test_context7_direct_client.py::test_resolve_library_id`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Class signature matches exactly
- [ ] Full type hints present
- [ ] Docstring complete with examples
- [ ] Connection pooling configured (limit=30, limit_per_host=10)
- [ ] Circuit breaker implemented with 3-failure threshold
- [ ] LRU cache with 100-entry limit
- [ ] Error handling with Context7APIException
- [ ] Test written and passing
- [ ] mypy --strict passes (zero errors)

**COMPLETION COMMAND**:
```bash
# Run after implementation
.devstream/bin/python -m pytest tests/unit/test_context7_direct_client.py -v
.devstream/bin/python -m mypy .claude/hooks/devstream/utils/context7_direct_client.py --strict
```

### Task 2: Hybrid Context7 Manager (Duration: 60 min)

**File**: `.claude/hooks/devstream/utils/context7_hybrid_manager.py` (Lines: 1-150)

**ACTION**: Implementare Context7HybridManager con feature flags e fallback

**FUNCTION SIGNATURE** (USE EXACTLY):
```python
class Context7HybridManager:
    """
    Hybrid Context7 manager supporting both MCP and Direct HTTP clients.
    Implements gradual rollout with feature flags and automatic fallback.

    Attributes:
        direct_client: Context7DirectHttpClient instance
        mcp_enabled: MCP client availability flag
        direct_enabled: Direct client enabled via feature flag
        circuit_breaker: Circuit breaker for mode switching
        metrics: Performance and reliability metrics
    """

    def __init__(
        self,
        direct_enabled: Optional[bool] = None,
        mcp_fallback: bool = True
    ) -> None:
        """
        Initialize hybrid Context7 manager.

        Args:
            direct_enabled: Override feature flag (None = use ENV)
            mcp_fallback: Enable MCP as fallback when direct fails
        """

    async def resolve_library_id(
        self,
        library_name: str,
        force_mode: Optional[str] = None  # "direct" or "mcp"
    ) -> Optional[str]:
        """
        Resolve library ID using hybrid strategy.

        Args:
            library_name: Library name to resolve
            force_mode: Force specific mode ("direct" or "mcp")

        Returns:
            Context7 library ID or None

        Raises:
            Context7Error: If both modes fail
        """

    async def get_library_docs(
        self,
        library_id: str,
        topic: Optional[str] = None,
        tokens: int = 5000,
        force_mode: Optional[str] = None
    ) -> Optional[str]:
        """
        Get library docs using hybrid strategy.

        Args:
            library_id: Context7 library ID
            topic: Optional topic
            tokens: Max tokens
            force_mode: Force specific mode

        Returns:
            Documentation or None
        """

    def _should_use_direct_mode(self) -> bool:
        """
        Determine if direct mode should be used based on feature flags.

        Returns:
            True if direct mode enabled and available
        """

    def _record_mode_metrics(self, mode: str, success: bool, duration: float) -> None:
        """
        Record performance metrics for mode selection optimization.

        Args:
            mode: "direct" or "mcp"
            success: Operation success
            duration: Operation duration in seconds
        """
```

**PATTERN REFERENCE**: See `.claude/hooks/devstream/utils/unified_client.py:521-600` for hybrid client pattern

**ERROR HANDLING** (USE THIS PATTERN):
```python
try:
    if self._should_use_direct_mode():
        return await self.direct_client.resolve_library_id(library_name)
    else:
        return await self._call_mcp_resolve_library(library_name)
except Context7Error as e:
    if mcp_fallback and mode == "direct":
        logger.warning(f"Direct mode failed, falling back to MCP: {e}")
        return await self._call_mcp_resolve_library(library_name)
    raise
```

**FEATURE FLAG CONFIGURATION**:
```python
def _should_use_direct_mode(self) -> bool:
    """Check feature flag with gradual rollout logic."""
    if self.direct_enabled is not None:
        return self.direct_enabled

    # Environment-based gradual rollout
    flag = os.getenv("DEVSTREAM_CONTEXT7_DIRECT_ENABLED", "false").lower()
    if flag == "true":
        return True
    elif flag == "rollout":
        # 10% rollout based on hash of library name
        return hash(library_name) % 10 == 0
    return False
```

**TEST FILE**: `tests/unit/test_context7_hybrid_manager.py::test_hybrid_resolution`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Class implements hybrid strategy correctly
- [ ] Feature flag support: true/false/rollout modes
- [ ] MCP fallback when direct mode fails
- [ ] Metrics collection for performance tracking
- [ ] Force mode override functionality
- [ ] Circuit breaker for mode switching
- [ ] Full type hints and documentation
- [ ] Tests covering all failure scenarios

**COMPLETION COMMAND**:
```bash
.devstream/bin/python -m pytest tests/unit/test_context7_hybrid_manager.py -v
.devstream/bin/python -m mypy .claude/hooks/devstream/utils/context7_hybrid_manager.py --strict
```

### Task 3: Update PreToolUse Hook Integration (Duration: 45 min)

**File**: `.claude/hooks/devstream/memory/pre_tool_use.py` (Lines: 435-487)

**ACTION**: Sostituire advisory pattern con direct HTTP calls

**SPECIFIC CHANGES**:
```python
# REPLACE lines 435-487 in get_context7_docs method:

async def get_context7_docs(self, file_path: str, content: str) -> Optional[str]:
    """
    Get Context7 documentation using hybrid manager (direct + MCP fallback).

    Instead of emitting advisory messages, directly retrieves documentation
    using hybrid strategy with automatic fallback.
    """
    try:
        # Initialize hybrid manager (lazy initialization)
        if not hasattr(self, 'context7_manager'):
            from ..utils.context7_hybrid_manager import Context7HybridManager
            self.context7_manager = Context7HybridManager()

        # Detect libraries from imports/usage
        libraries = self._detect_libraries(content, file_path)

        if not libraries:
            self.base.debug_log("No external libraries detected for Context7")
            return None

        self.base.debug_log(f"Context7 direct retrieval - detected libraries: {', '.join(libraries)}")

        # Build formatted documentation directly
        docs_sections = []

        for lib in libraries[:3]:  # Limit to top 3 to avoid context bloat
            try:
                # Resolve library ID
                library_id = await self.context7_manager.resolve_library_id(lib)
                if not library_id:
                    continue

                # Get documentation
                docs = await self.context7_manager.get_library_docs(
                    library_id=library_id,
                    topic=self._extract_topic_from_code(content, lib),
                    tokens=1500  # Reduced per library for total 5000 budget
                )

                if docs:
                    docs_sections.append(f"### {lib.title()} ({library_id})\n\n{docs}")

            except Exception as e:
                self.base.debug_log(f"Failed to retrieve docs for {lib}: {e}")
                continue

        if not docs_sections:
            return None

        # Assemble final context
        formatted = "# Context7 Documentation\n\n"
        formatted += "\n\n---\n\n".join(docs_sections)
        formatted += "\n\n---\n*Retrieved via DevStream Context7 Direct Client*"

        self.base.success_feedback(f"Retrieved Context7 docs for {len(docs_sections)} libraries")
        return formatted

    except Exception as e:
        self.base.debug_log(f"Context7 direct retrieval failed: {e}")
        # Fallback to advisory pattern on failure
        return await self._emit_context7_advisory_fallback(libraries)

async def _emit_context7_advisory_fallback(self, libraries: List[str]) -> Optional[str]:
    """Fallback to advisory pattern if direct retrieval fails."""
    advisory = "# Context7 Advisory (Fallback Mode)\n\n"
    advisory += f"**File**: {Path(file_path).name}\n\n"
    advisory += f"**Detected Libraries**: {', '.join(libraries)}\n\n"
    advisory += "**Direct retrieval failed - using manual MCP calls:\n\n"

    for lib in libraries[:3]:
        advisory += f"### {lib}\n\n"
        advisory += "1. Resolve library ID:\n"
        advisory += f"```\nmcp__context7__resolve-library-id\n"
        advisory += f"libraryName: {lib}\n```\n\n"
        advisory += "2. Retrieve documentation:\n"
        advisory += f"```\nmcp__context7__get-library-docs\n"
        advisory += f"context7CompatibleLibraryID: <resolved_id_from_step_1>\n"
        advisory += f"tokens: 5000\n```\n\n"

    return advisory

def _extract_topic_from_code(self, content: str, library: str) -> Optional[str]:
    """Extract relevant topics from code for better documentation targeting."""
    # Look for common patterns that indicate what the user is working on
    topics = []

    # Framework-specific patterns
    if library == "fastapi":
        if re.search(r'@app\.(get|post|put|delete)', content):
            topics.append("routing")
        if re.search(r'pydantic|BaseModel', content):
            topics.append("models")
    elif library == "pytest":
        if re.search(r'@pytest\.fixture', content):
            topics.append("fixtures")
        if re.search(r'pytest-asyncio', content):
            topics.append("async")
    elif library == "aiohttp":
        if re.search(r'ClientSession|session\.', content):
            topics.append("client")
        if re.search(r'web\.Application|@routes\.', content):
            topics.append("server")

    return " ".join(topics[:2]) if topics else None
```

**PATTERN REFERENCE**: Current advisory pattern in lines 435-487

**ERROR HANDLING**: Graceful fallback to advisory pattern if hybrid manager fails

**TEST FILE**: `tests/unit/test_pre_tool_use_context7_integration.py::test_direct_retrieval`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Advisory pattern replaced with direct calls
- [ ] Hybrid manager integration working
- [ ] Fallback to advisory on failure
- [ ] Topic extraction for better targeting
- [ ] Token budget management (5000 total)
- [ ] Error handling preserves functionality
- [ ] Performance metrics collection

**COMPLETION COMMAND**:
```bash
.devstream/bin/python -m pytest tests/unit/test_pre_tool_use_context7_integration.py -v
.devstream/bin/python -m mypy .claude/hooks/devstream/memory/pre_tool_use.py --strict
```

### Task 4: Configuration and Feature Flags (Duration: 30 min)

**File**: `.env.example.deployment` (Lines: ADD to existing)

**ACTION**: Add configuration variables for gradual rollout

**ADD THESE LINES**:
```bash
# Context7 Direct Client Configuration
DEVSTREAM_CONTEXT7_DIRECT_ENABLED=false          # true/false/rollout
DEVSTREAM_CONTEXT7_DIRECT_CACHE_SIZE=100        # LRU cache size
DEVSTREAM_CONTEXT7_DIRECT_TIMEOUT=30           # Request timeout in seconds
DEVSTREAM_CONTEXT7_DIRECT_CB_THRESHOLD=3       # Circuit breaker failure threshold
DEVSTREAM_CONTEXT7_METRICS_ENABLED=true        # Enable performance metrics
DEVSTREAM_CONTEXT7_MCP_FALLBACK=true           # Enable MCP fallback
```

**File**: `.claude/hooks/devstream/config/context7_config.py` (CREATE NEW)

**ACTION**: Create configuration management for Context7

**FUNCTION SIGNATURE**:
```python
@dataclass
class Context7Config:
    """Configuration for Context7 Direct Client integration."""
    direct_enabled: Union[bool, str] = False
    cache_size: int = 100
    timeout: int = 30
    circuit_breaker_threshold: int = 3
    metrics_enabled: bool = True
    mcp_fallback: bool = True

    @classmethod
    def from_env(cls) -> 'Context7Config':
        """Load configuration from environment variables."""
        return cls(
            direct_enabled=os.getenv("DEVSTREAM_CONTEXT7_DIRECT_ENABLED", "false"),
            cache_size=int(os.getenv("DEVSTREAM_CONTEXT7_DIRECT_CACHE_SIZE", "100")),
            timeout=int(os.getenv("DEVSTREAM_CONTEXT7_DIRECT_TIMEOUT", "30")),
            circuit_breaker_threshold=int(os.getenv("DEVSTREAM_CONTEXT7_DIRECT_CB_THRESHOLD", "3")),
            metrics_enabled=os.getenv("DEVSTREAM_CONTEXT7_METRICS_ENABLED", "true").lower() == "true",
            mcp_fallback=os.getenv("DEVSTREAM_CONTEXT7_MCP_FALLBACK", "true").lower() == "true"
        )

    def should_use_direct_mode(self, library_name: Optional[str] = None) -> bool:
        """
        Determine if direct mode should be used based on configuration.

        Returns:
            True if direct mode should be used
        """
        if isinstance(self.direct_enabled, bool):
            return self.direct_enabled
        elif self.direct_enabled == "rollout":
            # 10% rollout based on hash if library name provided
            if library_name:
                return hash(library_name) % 10 == 0
            return False
        return False
```

**TEST FILE**: `tests/unit/test_context7_config.py::test_configuration_loading`

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] Configuration loaded from environment
- [ ] Support for true/false/rollout modes
- [ ] Default values properly set
- [ ] Type validation and error handling
- [ ] Rollout logic based on hash distribution

**COMPLETION COMMAND**:
```bash
.devstream/bin/python -m pytest tests/unit/test_context7_config.py -v
.devstream/bin/python -m mypy .claude/hooks/devstream/config/context7_config.py --strict
```

### Task 5: Testing and Validation (Duration: 45 min)

**File**: `tests/integration/test_context7_hybrid_integration.py` (CREATE NEW)

**ACTION**: Comprehensive integration tests for hybrid system

**TEST STRUCTURE**:
```python
class TestContext7HybridIntegration:
    """Integration tests for Context7 Hybrid Manager."""

    @pytest_asyncio.fixture
    async def hybrid_manager(self):
        """Create hybrid manager for testing."""
        return Context7HybridManager(direct_enabled=True, mcp_fallback=True)

    @pytest.mark.asyncio
    async def test_direct_mode_resolution(self, hybrid_manager):
        """Test library resolution in direct mode."""

    @pytest.mark.asyncio
    async def test_mcp_fallback_on_direct_failure(self, hybrid_manager):
        """Test MCP fallback when direct mode fails."""

    @pytest.mark.asyncio
    async def test_feature_flag_rollout_logic(self):
        """Test gradual rollout feature flag logic."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self, hybrid_manager):
        """Test circuit breaker triggers fallback."""

    @pytest.mark.asyncio
    async def test_pre_tool_use_integration(self):
        """Test PreToolUse hook integration."""

    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self, hybrid_manager):
        """Test metrics collection for monitoring."""

    @pytest.mark.asyncio
    async def test_end_to_end_documentation_retrieval(self):
        """Test complete flow from library detection to docs retrieval."""
```

**File**: `tests/performance/test_context7_performance.py` (CREATE NEW)

**ACTION**: Performance benchmarking tests

**BENCHMARK TESTS**:
```python
class TestContext7Performance:
    """Performance benchmarks for Context7 Direct Client."""

    @pytest.mark.asyncio
    async def benchmark_direct_vs_mcp_performance(self):
        """Compare performance of direct vs MCP mode."""

    @pytest.mark.asyncio
    async def benchmark_connection_pooling_efficiency(self):
        """Test connection pooling effectiveness."""

    @pytest.mark.asyncio
    async def benchmark_cache_hit_ratios(self):
        """Test cache effectiveness for repeated queries."""

    @pytest.mark.asyncio
    async def benchmark_memory_usage_comparison(self):
        """Compare memory usage between direct and MCP modes."""
```

**PERFORMANCE TARGETS**:
- Direct mode: <200ms average response time
- Cache hit ratio: >80% for repeated queries
- Memory usage: <50MB for 100 concurrent requests
- Success rate: >99% with automatic fallback

**ACCEPTANCE CRITERIA** (CHECK ALL BEFORE MARKING COMPLETE):
- [ ] All integration tests passing
- [ ] Performance benchmarks meet targets
- [ ] MCP fallback working correctly
- [ ] Feature flag logic validated
- [ ] Circuit breaker functionality verified
- [ ] End-to-end workflow tested
- [ ] Error scenarios covered

**COMPLETION COMMAND**:
```bash
.devstream/bin/python -m pytest tests/integration/test_context7_hybrid_integration.py -v
.devstream/bin/python -m pytest tests/performance/test_context7_performance.py -v
```

---

## 🔍 CONTEXT7 RESEARCH FINDINGS (Pre-Researched)

### **Libraries Researched**:

1. **aiohttp** (`/aio-libs/aiohttp`) - Trust Score: 9.3/10
   - Connection pooling with configurable limits
   - TCPConnector optimization patterns
   - FIFO connection pool for better reuse
   - Graceful shutdown and cleanup

2. **backoff** (`/cenkalti/backoff`) - Trust Score: 9.1/10
   - Exponential backoff with jitter
   - Circuit breaker patterns
   - Retry policies for fault tolerance

3. **Feature Flags** (`/thomaspoignant/go-feature-flag`) - Trust Score: 9.9/10
   - Gradual rollout strategies
   - A/B testing patterns
   - Rollback mechanisms

### **Key Pattern 1**: aiohttp Connection Pooling
```python
connector = aiohttp.TCPConnector(
    limit=30,                    # Total connections
    limit_per_host=10,          # Per-host connections
    keepalive_timeout=15,       # Keep-alive timeout
    enable_cleanup_closed=True  # Cleanup on close
)
session = aiohttp.ClientSession(connector=connector)
```
**When to use**: High-performance HTTP client with connection reuse

### **Key Pattern 2**: Exponential Backoff with Circuit Breaker
```python
def retry_with_backoff(operation, max_retries=3):
    for attempt in range(max_retries):
        try:
            return operation()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = 2 ** attempt + random.uniform(0, 1)
            time.sleep(delay)
```
**When to use**: Fault-tolerant API calls with automatic recovery

### **Key Pattern 3**: Feature Flag Gradual Rollout
```python
def should_enable_feature(user_id: str, rollout_percentage: int) -> bool:
    return hash(user_id) % 100 < rollout_percentage
```
**When to use**: Controlled feature rollout with user-based segmentation

---

## 🚨 CRITICAL CONSTRAINTS (DO NOT VIOLATE)

**FORBIDDEN ACTIONS**:
- ❌ **NO** removal of MCP server during Phase 1-4
- ❌ **NO** breaking changes to existing interface
- ❌ **NO** forcing direct mode without fallback
- ❌ **NO** skipping circuit breaker implementation
- ❌ **NO** marking task complete with failing tests

**REQUIRED ACTIONS**:
- ✅ **YES** use Context7 for unknowns (tools provided above)
- ✅ **YES** maintain ALL existing functionality
- ✅ **YES** implement feature flags with gradual rollout
- ✅ **YES** include MCP fallback mechanism
- ✅ **YES** full type hints + docstrings EVERY function
- ✅ **YES** tests for EVERY feature (95%+ coverage)

---

## ✅ QUALITY GATES (MANDATORY BEFORE COMPLETION)

### 1. Test Coverage
```bash
.devstream/bin/python -m pytest tests/ -v \
    --cov=.claude/hooks/devstream/utils/context7_direct_client \
    --cov-report=term-missing \
    --cov-report=html

# REQUIREMENT: ≥ 95% coverage for NEW code
```

### 2. Type Safety
```bash
.devstream/bin/python -m mypy .claude/hooks/devstream/utils/context7_*.py --strict

# REQUIREMENT: Zero errors
```

### 3. Performance Benchmark
```bash
.devstream/bin/python -m pytest tests/performance/test_context7_performance.py -v

# TARGET: Direct mode <200ms, >80% cache hit ratio
```

---

## 📝 COMMIT MESSAGE TEMPLATE

```
feat(context7): implement hybrid direct client with gradual rollout

Add Context7 Direct HTTP Client with aiohttp optimization while maintaining
MCP server as fallback. Implements feature flags for gradual rollout from
MCP to direct mode.

Implementation Details:
- Context7DirectHttpClient with connection pooling and circuit breaker
- Context7HybridManager supporting both direct and MCP modes
- Feature flag configuration (true/false/rollout) for gradual migration
- Updated PreToolUse hook with direct documentation retrieval
- Comprehensive testing and performance benchmarks

Quality Validation:
- ✅ Tests: 25 tests passing, 96% coverage
- ✅ Type safety: mypy --strict passed
- ✅ Performance: Direct mode 150ms avg, 85% cache hit ratio

Task ID: context7-direct-client-hybrid

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## 📊 SUCCESS METRICS

- **Completion**: 100% of micro-tasks with acceptance criteria met
- **Test Coverage**: ≥ 95% for new code
- **Type Safety**: Zero mypy errors
- **Performance**: Direct mode <200ms, >80% cache hit ratio
- **Reliability**: >99% success rate with automatic fallback
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