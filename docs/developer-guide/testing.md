# Testing Strategy and Guidelines

**Target Audience**: Contributors, QA engineers
**Level**: Intermediate to Advanced
**Type**: Reference + How-To

## Testing Philosophy

DevStream follows **Test-Driven Development (TDD)** principles with emphasis on:

1. **High Coverage**: 95%+ for new code, 100% for critical paths
2. **Fast Execution**: Unit tests < 1s, integration tests < 10s
3. **Isolation**: Tests don't depend on each other or external services
4. **Reliability**: Tests are deterministic and don't flake
5. **Maintainability**: Tests are clear, documented, and easy to update

## Test Pyramid

```
       /\
      /  \        E2E Tests (5%)
     /____\       - Full workflow validation
    /      \      - Claude Code integration
   /________\     - Slow, expensive
  /          \
 /____________\   Integration Tests (25%)
/              \  - Component interaction
/________________\ - Database, MCP, hooks
                  - Medium speed

        Unit Tests (70%)
        - Function-level testing
        - Fast, isolated
        - Mock external dependencies
```

### Test Distribution

| Test Type | Percentage | Purpose | Execution Time |
|-----------|-----------|---------|----------------|
| **Unit** | 70% | Function-level logic, edge cases | < 1s per file |
| **Integration** | 25% | Component interaction, database | < 10s per file |
| **E2E** | 5% | Full workflow validation | < 60s per scenario |

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                 # Shared pytest fixtures
├── fixtures/                   # Test data (JSON, SQL, etc.)
│   ├── sample_embeddings.json
│   ├── sample_memories.json
│   └── sample_tasks.json
├── unit/                       # Unit tests (fast, isolated)
│   ├── __init__.py
│   ├── test_memory.py          # Memory system tests
│   ├── test_context7.py        # Context7 client tests
│   ├── test_ollama_client.py   # Ollama client tests
│   ├── test_pattern_matcher.py # Agent delegation tests
│   └── test_hybrid_search.py   # Hybrid search algorithm tests
├── integration/                # Integration tests (database, MCP)
│   ├── __init__.py
│   ├── test_pre_tool_use.py    # PreToolUse hook integration
│   ├── test_post_tool_use.py   # PostToolUse hook integration
│   ├── test_mcp_server.py      # MCP server integration
│   └── test_end_to_end.py      # Full workflow tests
└── standalone/                 # Standalone verification scripts
    ├── test_ollama_connection.py
    └── test_vector_search.py
```

## Unit Testing

### Unit Test Guidelines

**Characteristics**:
- ✅ Fast (< 1s per test file)
- ✅ No external dependencies (mock everything)
- ✅ Isolated (can run in any order)
- ✅ Deterministic (same input = same output)
- ✅ Focused (test one function/method per test)

**When to Write Unit Tests**:
- Pure functions (no side effects)
- Business logic
- Data transformations
- Algorithm implementations
- Utility functions

### Example: Memory Storage Unit Test

**File**: `tests/unit/test_memory.py`

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

# Import module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude/hooks/devstream/memory'))
from post_tool_use import PostToolUseHook


class TestPostToolUseHook:
    """Unit tests for PostToolUse hook memory storage."""

    @pytest.fixture
    def hook(self):
        """Create PostToolUseHook instance with mocked dependencies."""
        with patch('post_tool_use.get_mcp_client'), \
             patch('post_tool_use.OllamaEmbeddingClient'):
            hook = PostToolUseHook()
            # Mock MCP client
            hook.mcp_client = AsyncMock()
            # Mock Ollama client
            hook.ollama_client = Mock()
            return hook

    def test_extract_content_preview_short(self, hook):
        """Test content preview extraction for short content."""
        content = "Short content"
        preview = hook.extract_content_preview(content, max_length=300)

        assert preview == "Short content"
        assert len(preview) <= 300

    def test_extract_content_preview_long(self, hook):
        """Test content preview extraction for long content."""
        content = "A" * 1000  # Long content
        preview = hook.extract_content_preview(content, max_length=300)

        assert len(preview) <= 300
        assert preview.startswith("A")

    def test_extract_content_preview_sentence_boundary(self, hook):
        """Test content preview breaks at sentence boundary."""
        content = "First sentence. Second sentence. " + "A" * 500
        preview = hook.extract_content_preview(content, max_length=300)

        # Should break after "First sentence." (within 300 chars)
        assert "First sentence." in preview
        assert len(preview) <= 300

    def test_extract_keywords_python(self, hook):
        """Test keyword extraction for Python file."""
        file_path = "/project/src/api/users.py"
        content = "def get_users(): pass"

        keywords = hook.extract_keywords(file_path, content)

        assert "users" in keywords       # File name
        assert "api" in keywords         # Parent directory
        assert "python" in keywords      # Language
        assert "implementation" in keywords  # Always added

    def test_extract_keywords_typescript(self, hook):
        """Test keyword extraction for TypeScript file."""
        file_path = "/project/src/components/Button.tsx"
        content = "export const Button = () => <button>Click</button>"

        keywords = hook.extract_keywords(file_path, content)

        assert "Button" in keywords
        assert "components" in keywords
        assert "react" in keywords      # .tsx → React

    @pytest.mark.asyncio
    async def test_store_in_memory_success(self, hook):
        """Test successful memory storage with embedding."""
        # Setup mocks
        hook.mcp_client.call_tool = AsyncMock(return_value={
            "success": True,
            "memory_id": "MEM-12345"
        })
        hook.ollama_client.generate_embedding = Mock(return_value=[0.1] * 768)
        hook.update_memory_embedding = Mock(return_value=True)

        # Execute
        file_path = "/project/test.py"
        content = "print('hello')"
        memory_id = await hook.store_in_memory(file_path, content, "Write")

        # Verify
        assert memory_id == "MEM-12345"
        hook.mcp_client.call_tool.assert_called_once()
        hook.ollama_client.generate_embedding.assert_called_once_with(content)
        hook.update_memory_embedding.assert_called_once_with("MEM-12345", [0.1] * 768)

    @pytest.mark.asyncio
    async def test_store_in_memory_mcp_failure(self, hook):
        """Test memory storage when MCP call fails."""
        # Setup mocks
        hook.mcp_client.call_tool = AsyncMock(return_value=None)

        # Execute
        memory_id = await hook.store_in_memory("/test.py", "content", "Write")

        # Verify graceful failure
        assert memory_id is None

    @pytest.mark.asyncio
    async def test_store_in_memory_embedding_failure(self, hook):
        """Test memory storage when embedding generation fails (graceful degradation)."""
        # Setup mocks
        hook.mcp_client.call_tool = AsyncMock(return_value={
            "success": True,
            "memory_id": "MEM-12345"
        })
        hook.ollama_client.generate_embedding = Mock(side_effect=Exception("Ollama unavailable"))

        # Execute (should succeed despite embedding failure)
        memory_id = await hook.store_in_memory("/test.py", "content", "Write")

        # Verify graceful degradation
        assert memory_id == "MEM-12345"  # Memory stored, embedding failed gracefully
```

### Running Unit Tests

```bash
# Run all unit tests
.devstream/bin/python -m pytest tests/unit/ -v

# Run specific test file
.devstream/bin/python -m pytest tests/unit/test_memory.py -v

# Run specific test
.devstream/bin/python -m pytest tests/unit/test_memory.py::TestPostToolUseHook::test_extract_keywords_python -v

# Run with coverage
.devstream/bin/python -m pytest tests/unit/ --cov=.claude/hooks/devstream --cov-report=html

# Run tests matching pattern
.devstream/bin/python -m pytest tests/unit/ -k "extract_keywords" -v
```

## Integration Testing

### Integration Test Guidelines

**Characteristics**:
- ✅ Medium speed (< 10s per test file)
- ✅ Real database (in-memory SQLite for speed)
- ✅ Real MCP server (started for test session)
- ✅ Mock external APIs (Context7, Ollama)
- ✅ Test component interaction

**When to Write Integration Tests**:
- Hook execution with database
- MCP server tool calls
- Vector search with embeddings
- Hybrid search (RRF algorithm)
- Agent delegation workflow

### Example: PreToolUse Hook Integration Test

**File**: `tests/integration/test_pre_tool_use.py`

```python
import pytest
import asyncio
import sqlite3
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Import modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude/hooks/devstream'))
from memory.pre_tool_use import PreToolUseHook
from utils.sqlite_vec_helper import get_db_connection_with_vec


@pytest.fixture(scope="module")
def test_db():
    """Create in-memory test database with schema."""
    db_path = ":memory:"

    # Initialize schema
    conn = get_db_connection_with_vec(db_path)

    # Load schema
    schema_path = Path(__file__).parent.parent.parent / 'schema' / 'schema.sql'
    with open(schema_path) as f:
        conn.executescript(f.read())

    conn.close()

    yield db_path


@pytest.fixture
def hook_with_db(test_db):
    """Create PreToolUseHook with test database."""
    with patch('pre_tool_use.get_mcp_client'), \
         patch('pre_tool_use.Context7Client'), \
         patch('pre_tool_use.PatternMatcher'), \
         patch('pre_tool_use.AgentRouter'):

        hook = PreToolUseHook()
        hook.base.db_path = test_db

        # Mock MCP client
        hook.mcp_client = AsyncMock()

        # Mock Context7 client
        hook.context7 = Mock()
        hook.context7.should_trigger_context7 = AsyncMock(return_value=False)

        # Mock agent components
        hook.pattern_matcher = Mock()
        hook.agent_router = Mock()

        yield hook


class TestPreToolUseIntegration:
    """Integration tests for PreToolUse hook."""

    @pytest.mark.asyncio
    async def test_devstream_memory_search_empty(self, hook_with_db):
        """Test memory search when no memories exist."""
        # Setup
        hook_with_db.mcp_client.call_tool = AsyncMock(return_value={
            "results": []
        })

        # Execute
        result = await hook_with_db.get_devstream_memory("/test.py", "content")

        # Verify
        assert result is None  # No memories found

    @pytest.mark.asyncio
    async def test_devstream_memory_search_with_results(self, hook_with_db):
        """Test memory search with matching results."""
        # Setup
        mock_results = [
            {
                "content": "Previous implementation of similar feature",
                "relevance_score": 0.85
            },
            {
                "content": "Related code pattern",
                "relevance_score": 0.72
            }
        ]
        hook_with_db.mcp_client.call_tool = AsyncMock(return_value={
            "results": mock_results
        })

        # Execute
        result = await hook_with_db.get_devstream_memory("/test.py", "content")

        # Verify
        assert result is not None
        assert "DevStream Memory Context" in result
        assert "relevance: 0.85" in result
        assert "Previous implementation" in result

    @pytest.mark.asyncio
    async def test_context7_integration(self, hook_with_db):
        """Test Context7 documentation retrieval."""
        # Setup
        hook_with_db.context7.should_trigger_context7 = AsyncMock(return_value=True)
        hook_with_db.context7.search_and_retrieve = AsyncMock(return_value=Mock(
            success=True,
            library_id="/fastapi/fastapi",
            docs="# FastAPI Documentation\n\nFastAPI is a modern web framework...",
            error=None
        ))
        hook_with_db.context7.format_docs_for_context = Mock(
            return_value="# Context7 Documentation\n\n## FastAPI\n\nFastAPI is a modern web framework..."
        )

        # Execute
        result = await hook_with_db.get_context7_docs("/api/users.py", "from fastapi import FastAPI")

        # Verify
        assert result is not None
        assert "Context7 Documentation" in result
        assert "FastAPI" in result

    @pytest.mark.asyncio
    async def test_context_assembly_combined(self, hook_with_db):
        """Test context assembly combining Context7 + DevStream memory."""
        # Setup Context7
        hook_with_db.context7.should_trigger_context7 = AsyncMock(return_value=True)
        hook_with_db.context7.search_and_retrieve = AsyncMock(return_value=Mock(
            success=True,
            library_id="/fastapi/fastapi",
            docs="FastAPI docs",
            error=None
        ))
        hook_with_db.context7.format_docs_for_context = Mock(
            return_value="# Context7: FastAPI\n\nDocumentation here"
        )

        # Setup DevStream memory
        hook_with_db.mcp_client.call_tool = AsyncMock(return_value={
            "results": [{
                "content": "Previous FastAPI implementation",
                "relevance_score": 0.90
            }]
        })

        # Execute
        result = await hook_with_db.assemble_context("/api/users.py", "from fastapi import FastAPI")

        # Verify combined context
        assert result is not None
        assert "Context7" in result
        assert "DevStream Memory" in result
        assert "FastAPI" in result

    @pytest.mark.asyncio
    async def test_agent_delegation_single_file(self, hook_with_db):
        """Test agent delegation for single Python file (automatic)."""
        # Setup
        hook_with_db.pattern_matcher.match_patterns = Mock(return_value={
            'agent': '@python-specialist',
            'confidence': 0.95,
            'pattern': '**/*.py'
        })
        hook_with_db.agent_router.assess_task_complexity = AsyncMock(return_value=Mock(
            suggested_agent='@python-specialist',
            confidence=0.95,
            recommendation='AUTOMATIC',
            reason='Single Python file',
            complexity='low',
            architectural_impact='local'
        ))

        # Execute
        assessment = await hook_with_db.check_agent_delegation(
            file_path="/src/api/users.py",
            content="def get_users(): pass",
            tool_name="Write"
        )

        # Verify
        assert assessment is not None
        assert assessment.suggested_agent == '@python-specialist'
        assert assessment.confidence == 0.95
        assert assessment.recommendation == 'AUTOMATIC'


@pytest.mark.asyncio
async def test_end_to_end_workflow(test_db):
    """End-to-end test: Store memory → Retrieve memory → Context injection."""
    # Phase 1: Store memory (PostToolUse)
    from memory.post_tool_use import PostToolUseHook

    with patch('post_tool_use.get_mcp_client'), \
         patch('post_tool_use.OllamaEmbeddingClient'):

        post_hook = PostToolUseHook()
        post_hook.db_path = test_db
        post_hook.mcp_client = AsyncMock()
        post_hook.ollama_client = Mock()

        # Mock MCP store
        post_hook.mcp_client.call_tool = AsyncMock(return_value={
            "success": True,
            "memory_id": "MEM-E2E-001"
        })

        # Mock embedding
        post_hook.ollama_client.generate_embedding = Mock(return_value=[0.5] * 768)
        post_hook.update_memory_embedding = Mock(return_value=True)

        # Store memory
        memory_id = await post_hook.store_in_memory(
            "/src/api/users.py",
            "async def get_users(): return []",
            "Write"
        )

        assert memory_id == "MEM-E2E-001"

    # Phase 2: Retrieve memory (PreToolUse)
    from memory.pre_tool_use import PreToolUseHook

    with patch('pre_tool_use.get_mcp_client'), \
         patch('pre_tool_use.Context7Client'):

        pre_hook = PreToolUseHook()
        pre_hook.mcp_client = AsyncMock()

        # Mock memory search (returns previously stored memory)
        pre_hook.mcp_client.call_tool = AsyncMock(return_value={
            "results": [{
                "content": "async def get_users(): return []",
                "relevance_score": 0.95
            }]
        })

        # Retrieve memory
        context = await pre_hook.get_devstream_memory("/src/api/users.py", "def update_users():")

        assert context is not None
        assert "async def get_users()" in context
```

### Running Integration Tests

```bash
# Run all integration tests
.devstream/bin/python -m pytest tests/integration/ -v

# Run with real MCP server (requires server running)
MCP_SERVER_RUNNING=true .devstream/bin/python -m pytest tests/integration/ -v

# Run specific integration test
.devstream/bin/python -m pytest tests/integration/test_pre_tool_use.py -v

# Run E2E workflow test
.devstream/bin/python -m pytest tests/integration/test_end_to_end.py -v
```

## E2E Testing

### E2E Test Guidelines

**Characteristics**:
- ✅ Slow (< 60s per scenario)
- ✅ Real database (file-based SQLite)
- ✅ Real MCP server
- ✅ Real Claude Code interaction (optional)
- ✅ Test complete workflows

**When to Write E2E Tests**:
- Full hook lifecycle (PreToolUse → Tool → PostToolUse)
- Claude Code integration
- Multi-step workflows
- Production deployment validation

### Example: Full Workflow E2E Test

**File**: `tests/integration/test_end_to_end.py`

```python
import pytest
import subprocess
import tempfile
import json
from pathlib import Path


@pytest.fixture(scope="module")
def temp_project():
    """Create temporary project directory for E2E tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Setup minimal project structure
        (project_path / ".claude").mkdir()
        (project_path / ".claude" / "hooks").mkdir()
        (project_path / "data").mkdir()

        # Copy hook files
        # ... copy logic ...

        yield project_path


@pytest.mark.e2e
@pytest.mark.slow
def test_full_workflow_write_file(temp_project):
    """E2E test: Write file triggers PostToolUse → generates embedding → stores memory."""
    # Phase 1: Simulate Claude Code Write operation
    tool_input = {
        "tool_name": "Write",
        "tool_input": {
            "file_path": str(temp_project / "test.py"),
            "content": "def hello(): return 'world'"
        }
    }

    # Execute PostToolUse hook
    result = subprocess.run(
        [
            str(temp_project / ".devstream" / "bin" / "python"),
            str(temp_project / ".claude" / "hooks" / "devstream" / "memory" / "post_tool_use.py")
        ],
        input=json.dumps(tool_input),
        capture_output=True,
        text=True
    )

    # Verify hook succeeded
    assert result.returncode == 0

    # Phase 2: Verify memory stored in database
    import sqlite3
    conn = sqlite3.connect(str(temp_project / "data" / "devstream.db"))

    cursor = conn.execute("SELECT COUNT(*) FROM semantic_memory WHERE content LIKE '%hello%'")
    count = cursor.fetchone()[0]

    assert count == 1  # Memory stored

    # Phase 3: Verify embedding generated
    cursor = conn.execute("SELECT embedding FROM semantic_memory WHERE content LIKE '%hello%'")
    embedding = cursor.fetchone()[0]

    assert embedding is not None
    assert len(json.loads(embedding)) == 768  # nomic-embed-text dimension

    conn.close()
```

## Test Coverage Requirements

### Coverage Targets

| Component | Target Coverage | Critical Paths |
|-----------|----------------|----------------|
| **Hook System** | 95%+ | Memory storage, context injection |
| **MCP Server** | 90%+ | Tool handlers, database queries |
| **Utilities** | 90%+ | Embedding generation, hybrid search |
| **Agent System** | 85%+ | Pattern matching, delegation |

### Measuring Coverage

```bash
# Generate HTML coverage report
.devstream/bin/python -m pytest tests/ --cov=.claude/hooks/devstream --cov-report=html

# View report
open htmlcov/index.html

# Generate terminal coverage report
.devstream/bin/python -m pytest tests/ --cov=.claude/hooks/devstream --cov-report=term-missing

# Fail if coverage below threshold
.devstream/bin/python -m pytest tests/ --cov=.claude/hooks/devstream --cov-fail-under=95
```

### Coverage Report Example

```
Name                                      Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------
.claude/hooks/devstream/memory/pre_tool_use.py    245      8    97%   120-125, 310
.claude/hooks/devstream/memory/post_tool_use.py   198      6    97%   85-90
.claude/hooks/devstream/utils/ollama_client.py     87      12    86%   45-50, 72-78
-----------------------------------------------------------------------
TOTAL                                    1245     45    96%
```

## Mocking and Test Doubles

### When to Mock

**Mock External Dependencies**:
- ✅ HTTP APIs (Context7, Ollama)
- ✅ File system operations (in unit tests)
- ✅ MCP client (in unit tests)
- ✅ Database connections (in unit tests)

**Don't Mock Internal Logic**:
- ❌ Pure functions (test directly)
- ❌ Business logic (test directly)
- ❌ Data transformations (test directly)

### Mock Examples

**Mock Ollama Client**:
```python
from unittest.mock import Mock

# Mock embedding generation
mock_ollama = Mock()
mock_ollama.generate_embedding = Mock(return_value=[0.1] * 768)

# Use in test
embedding = mock_ollama.generate_embedding("test content")
assert len(embedding) == 768
```

**Mock MCP Client**:
```python
from unittest.mock import AsyncMock

# Mock MCP tool call
mock_mcp = AsyncMock()
mock_mcp.call_tool = AsyncMock(return_value={
    "success": True,
    "memory_id": "MEM-123"
})

# Use in test
result = await mock_mcp.call_tool("devstream_store_memory", {...})
assert result["memory_id"] == "MEM-123"
```

**Mock Context7 Client**:
```python
from unittest.mock import Mock, AsyncMock

# Mock Context7
mock_context7 = Mock()
mock_context7.should_trigger_context7 = AsyncMock(return_value=True)
mock_context7.search_and_retrieve = AsyncMock(return_value=Mock(
    success=True,
    library_id="/fastapi/fastapi",
    docs="# FastAPI Documentation\n...",
    error=None
))

# Use in test
result = await mock_context7.search_and_retrieve("fastapi")
assert result.success is True
```

## Continuous Integration

### CI Pipeline Configuration

**File**: `.github/workflows/test.yml`

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m venv .devstream
          .devstream/bin/python -m pip install --upgrade pip
          .devstream/bin/python -m pip install -r requirements.txt

      - name: Run unit tests
        run: |
          .devstream/bin/python -m pytest tests/unit/ -v --cov=.claude/hooks/devstream --cov-report=xml

      - name: Run integration tests
        run: |
          .devstream/bin/python -m pytest tests/integration/ -v

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: true
```

### Pre-Commit Hooks

**File**: `.pre-commit-config.yaml`

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: Run unit tests
        entry: .devstream/bin/python -m pytest tests/unit/ -v
        language: system
        pass_filenames: false
        always_run: true

      - id: mypy
        name: Type checking with mypy
        entry: .devstream/bin/python -m mypy .claude/hooks/devstream --strict
        language: system
        types: [python]
```

## Best Practices

### Test Naming

```python
# Good test names (descriptive)
def test_extract_keywords_python_file()
def test_store_in_memory_when_mcp_fails()
def test_hybrid_search_with_empty_results()

# Bad test names (vague)
def test_keywords()
def test_store()
def test_search()
```

### Test Structure (AAA Pattern)

```python
def test_example():
    # Arrange (setup)
    hook = PostToolUseHook()
    file_path = "/test.py"
    content = "print('hello')"

    # Act (execute)
    result = hook.extract_keywords(file_path, content)

    # Assert (verify)
    assert "python" in result
    assert "implementation" in result
```

### Parametrized Tests

```python
@pytest.mark.parametrize("file_path,expected_lang", [
    ("/test.py", "python"),
    ("/test.ts", "typescript"),
    ("/test.tsx", "react"),
    ("/test.rs", "rust"),
    ("/test.go", "golang"),
])
def test_extract_keywords_languages(file_path, expected_lang):
    """Test keyword extraction for different languages."""
    hook = PostToolUseHook()
    keywords = hook.extract_keywords(file_path, "content")
    assert expected_lang in keywords
```

### Async Test Best Practices

```python
# Good: Use pytest-asyncio
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None

# Bad: Missing pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()  # Won't run properly
    assert result is not None
```

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-01
**Testing Framework**: pytest 7.4+
