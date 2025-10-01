"""
Pytest configuration e fixtures per testing DevStream.

CONTEXT7-VALIDATED PATTERNS IMPLEMENTATION:
- pytest-asyncio event loop configuration con uvloop optimization
- SQLAlchemy 2.0 async testing fixtures con in-memory database
- pytest-httpx per Ollama mocking con realistic response patterns
- pybreaker circuit breaker testing patterns
- Performance testing con uvloop e benchmarking

Fixtures disponibili:
- event_loop_policy: uvloop optimization per performance testing
- test_engine: SQLAlchemy async engine con test database
- test_connection: Transaction-scoped connection con rollback
- mock_ollama_*: pytest-httpx mocking per Ollama API
- circuit_breaker_config: Circuit breaker testing configuration
- performance_test_config: Performance benchmarking setup
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator, List, Dict, Any

import pytest
import pytest_asyncio
import uvloop
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncConnection
from sqlalchemy import text

# Add .claude/hooks to sys.path for importing devstream modules
project_root = Path(__file__).parent.parent
hooks_dir = project_root / ".claude" / "hooks"
if str(hooks_dir) not in sys.path:
    sys.path.insert(0, str(hooks_dir))

# NOTE: DevStreamConfig imports disabled - these modules don't exist yet
# Agent tests don't need these fixtures - they use their own setup
# from devstream.core.config import DevStreamConfig
# from devstream.core.exceptions import DevStreamError


# ============================================================================
# CONTEXT7-VALIDATED: pytest-asyncio + uvloop configuration
# ============================================================================

@pytest.fixture(scope="session")
def event_loop_policy():
    """
    Use uvloop for high-performance async testing.
    Context7-validated pattern from /pytest-dev/pytest-asyncio research.
    """
    if os.name != "nt":  # Unix systems only
        return uvloop.EventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="session")
async def session_event_loop(event_loop_policy) -> AsyncGenerator[asyncio.AbstractEventLoop, None]:
    """
    Session-scoped event loop for shared resources.
    Context7 pattern: module/session scope for database tests.
    """
    asyncio.set_event_loop_policy(event_loop_policy)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        yield loop
    finally:
        loop.close()


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Legacy event loop fixture for backward compatibility."""
    if os.name != "nt":
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db_path() -> Generator[str, None, None]:
    """Provide temporary database path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    yield db_path

    # Cleanup
    db_file = Path(db_path)
    if db_file.exists():
        db_file.unlink()

    # Cleanup SQLite auxiliary files
    for suffix in ["-journal", "-wal", "-shm"]:
        aux_file = Path(f"{db_path}{suffix}")
        if aux_file.exists():
            aux_file.unlink()


# @pytest.fixture
# def test_config(temp_db_path: str) -> DevStreamConfig:
#     """Provide test configuration."""
#     # NOTE: Disabled - DevStreamConfig doesn't exist yet
#     # Agent tests don't use this fixture
#     pass


# ============================================================================
# CONTEXT7-VALIDATED: pytest-httpx Ollama mocking patterns
# ============================================================================

@pytest.fixture
def ollama_mock_responses() -> Dict[str, Any]:
    """
    Standard Ollama API mock responses.
    Context7-validated pattern: realistic response patterns for testing.
    """
    return {
        "embed_success": {
            "method": "POST",
            "url": "http://localhost:11434/api/embed",
            "json": {
                "model": "nomic-embed-text",
                "embeddings": [[0.1, 0.2, 0.3, 0.4, 0.5]]
            },
            "status_code": 200
        },
        "embed_batch_success": {
            "method": "POST",
            "url": "http://localhost:11434/api/embed",
            "json": {
                "model": "nomic-embed-text",
                "embeddings": [
                    [0.1, 0.2, 0.3, 0.4, 0.5],
                    [0.6, 0.7, 0.8, 0.9, 1.0]
                ]
            },
            "status_code": 200
        },
        "embed_error": {
            "method": "POST",
            "url": "http://localhost:11434/api/embed",
            "json": {"error": "Model not found"},
            "status_code": 404
        },
        "embed_timeout": {
            "method": "POST",
            "url": "http://localhost:11434/api/embed",
            "json": {"error": "Request timeout"},
            "status_code": 408
        }
    }


@pytest.fixture
def mock_ollama_healthy(httpx_mock, ollama_mock_responses):
    """
    Mock healthy Ollama server responses.
    Context7 pattern: pytest-httpx setup for integration testing.
    """
    httpx_mock.add_response(**ollama_mock_responses["embed_success"])
    return httpx_mock


@pytest.fixture
def mock_ollama_error(httpx_mock, ollama_mock_responses):
    """Mock Ollama server error responses for error boundary testing."""
    httpx_mock.add_response(**ollama_mock_responses["embed_error"])
    return httpx_mock


@pytest.fixture
def mock_ollama_client() -> AsyncMock:
    """Legacy Ollama client mock for backward compatibility."""
    mock_client = AsyncMock()

    # Mock embedding response
    mock_client.embed.return_value = {
        "embedding": [0.1, 0.2, 0.3] * 128  # 384 dimensions mock
    }

    # Mock model list response
    mock_client.list.return_value = {
        "models": [
            {"name": "nomic-embed-text", "size": 274301056},
            {"name": "embeddinggemma", "size": 274301056},
        ]
    }

    return mock_client


# ============================================================================
# CONTEXT7-VALIDATED: Circuit breaker testing fixtures
# ============================================================================

@pytest.fixture
def circuit_breaker_config() -> Dict[str, Any]:
    """
    Circuit breaker configuration for testing.
    Context7-validated pattern: configurable thresholds for testing.
    """
    return {
        "fail_max": 2,  # Trip after 2 failures (fast for testing)
        "reset_timeout": 1,  # Quick reset for testing
        "success_threshold": 1,  # Single success to close
        "exclude": []  # No exclusions by default
    }


@pytest.fixture
def sample_text_data() -> List[str]:
    """Provide sample text data for testing."""
    return [
        "def create_user(name: str, email: str) -> User: pass",
        "# API Documentation for user creation endpoint",
        "SELECT * FROM users WHERE email = ? AND active = 1",
        "class UserRepository: def save(self, user): pass",
        "POST /api/users - Creates new user with validation",
    ]


@pytest.fixture
def sample_memory_items() -> List[dict]:
    """Provide sample memory items for testing."""
    return [
        {
            "content": "def authenticate_user(username, password): pass",
            "content_type": "code",
            "keywords": ["authentication", "user", "password"],
            "entities": ["authenticate_user", "username", "password"],
        },
        {
            "content": "# Authentication API\nEndpoint for user login with JWT tokens",
            "content_type": "documentation",
            "keywords": ["authentication", "api", "jwt", "login"],
            "entities": ["JWT", "API"],
        },
        {
            "content": "Task completed: Implemented user authentication with JWT",
            "content_type": "output",
            "keywords": ["task", "user", "authentication", "jwt"],
            "entities": ["JWT"],
        },
    ]


# NOTE: Database fixtures disabled - dependencies don't exist yet
# Agent tests don't use these fixtures

# @pytest_asyncio.fixture
# async def temp_database(test_config: DevStreamConfig) -> AsyncGenerator[str, None]:
#     """Provide temporary database with schema."""
#     pass

# @pytest_asyncio.fixture
# async def connection_pool(test_config: DevStreamConfig) -> AsyncGenerator:
#     """Provide connection pool for testing."""
#     pass

# @pytest_asyncio.fixture
# async def db_manager(test_config: DevStreamConfig) -> AsyncGenerator:
#     """Provide database manager for testing."""
#     pass


# @pytest_asyncio.fixture
# async def query_manager(db_manager) -> AsyncGenerator:
#     """Provide query manager for testing."""
#     pass

# @pytest_asyncio.fixture
# async def sample_plan(query_manager) -> str:
#     """Create sample intervention plan for testing."""
#     pass

# @pytest_asyncio.fixture
# async def sample_task(query_manager, sample_plan: str) -> str:
#     """Create sample micro task for testing."""
#     pass


class DatabaseTestHelper:
    """Helper class for database testing utilities."""

    def __init__(self, query_manager):
        self.query_manager = query_manager

    async def count_records(self, table_name: str) -> int:
        """Count records in a table."""
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        async with self.query_manager.read_transaction() as conn:
            result = await conn.execute(text(query))
            row = await result.fetchone()
            return row[0] if row else 0

    async def clear_table(self, table_name: str) -> None:
        """Clear all records from a table."""
        async with self.query_manager.write_transaction() as conn:
            await conn.execute(text(f"DELETE FROM {table_name}"))

    async def get_table_info(self, table_name: str) -> list:
        """Get table schema information."""
        query = f"PRAGMA table_info({table_name})"
        async with self.query_manager.read_transaction() as conn:
            result = await conn.execute(text(query))
            return await result.fetchall()


# @pytest.fixture
# def db_helper(query_manager) -> DatabaseTestHelper:
#     """Create database test helper."""
#     pass


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup test environment variables."""
    # Disable external calls in tests
    monkeypatch.setenv("DEVSTREAM_OLLAMA_ENDPOINT", "http://mock-ollama:11434")
    monkeypatch.setenv("DEVSTREAM_DB_WAL_MODE", "false")
    monkeypatch.setenv("DEVSTREAM_LOG_TO_FILE", "false")


# ============================================================================
# CONTEXT7-VALIDATED: Performance testing configuration
# ============================================================================

@pytest.fixture
def performance_test_config() -> Dict[str, Any]:
    """
    Configuration for performance benchmarks.
    Context7-validated pattern: uvloop optimization validation.
    """
    return {
        "benchmark_rounds": 10,
        "max_response_time_ms": 500,  # 500ms max for task creation
        "max_memory_search_time_ms": 200,  # 200ms max for memory search
        "concurrent_operations": 5  # Test concurrency
    }


# ============================================================================
# PYTEST CONFIGURATION AND MARKERS
# ============================================================================

# Context7-validated pytest markers
pytest_markers = [
    "unit: marks tests as unit tests (fast, isolated)",
    "integration: marks tests as integration tests (slower, external deps)",
    "e2e: marks tests as end-to-end tests (slowest, full system)",
    "performance: marks tests as performance tests (Context7-validated)",
    "circuit_breaker: marks tests as circuit breaker tests (Context7-validated)",
    "requires_ollama: marks tests that require Ollama server",
    "requires_docker: marks tests that require Docker",
    "slow: marks tests as slow (can be skipped with -m 'not slow')",
    "memory_intensive: marks tests that use significant memory",
    "tasks: marks tests as task management tests",
    "memory: marks tests as memory system tests",
]


def pytest_configure(config):
    """Configure pytest with Context7-validated markers."""
    for marker in pytest_markers:
        config.addinivalue_line("markers", marker)

    # Add markers for database tests
    config.addinivalue_line("markers", "database: marks tests as database tests")


def pytest_collection_modifyitems(config, items):
    """
    Automatically mark tests based on their location.
    Context7-validated pattern: test categorization for selective execution.
    """
    for item in items:
        # Mark tests based on directory structure
        if "/unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "/e2e/" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        elif "/performance/" in str(item.fspath):
            item.add_marker(pytest.mark.performance)

        # Mark tests requiring external services
        if "ollama" in str(item.fspath).lower():
            item.add_marker(pytest.mark.requires_ollama)
        if "circuit" in item.name.lower():
            item.add_marker(pytest.mark.circuit_breaker)


@pytest.fixture(scope="session", autouse=True)
def setup_test_logging():
    """Configure logging for tests."""
    import structlog

    # Minimal logging for tests
    structlog.configure(
        processors=[
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Helper functions for tests
class TestHelpers:
    """Helper functions per testing."""

    @staticmethod
    def create_mock_embedding(dimension: int = 384) -> List[float]:
        """Create mock embedding vector."""
        import random
        return [random.random() for _ in range(dimension)]

    @staticmethod
    def create_sample_plan_data() -> dict:
        """Create sample intervention plan data."""
        return {
            "title": "Test Plan",
            "objectives": ["Objective 1", "Objective 2"],
            "technical_specs": {"language": "python", "framework": "fastapi"},
            "expected_outcome": "Working API implementation",
        }

    @staticmethod
    def create_sample_task_data() -> dict:
        """Create sample micro-task data."""
        return {
            "title": "Test Task",
            "description": "Implement test functionality",
            "task_type": "coding",
            "max_duration_minutes": 10,
        }


@pytest.fixture
def test_helpers() -> TestHelpers:
    """Provide test helper functions."""
    return TestHelpers()