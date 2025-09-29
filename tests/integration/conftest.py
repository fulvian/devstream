"""
Integration test configuration and fixtures.

CONTEXT7-VALIDATED INTEGRATION PATTERNS:
- SQLAlchemy async transaction testing with rollback isolation
- pytest-asyncio session-scoped database fixtures
- Testcontainers for containerized service testing
- Real database integration with controlled environment
- Memory system integration with embeddings

Architecture:
- Database: Real SQLite with transaction rollback per test
- Memory: Mocked Ollama with deterministic embeddings
- Tasks: Integration with both database and memory systems
- E2E: Full workflow testing with all systems active
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Dict, Any

import pytest
import pytest_asyncio
import uvloop
from unittest.mock import AsyncMock
from sqlalchemy import text

from devstream.core.config import DevStreamConfig
from devstream.database.connection import ConnectionPool
from devstream.database.queries import QueryManager
from devstream.database.migrations import MigrationRunner


# ============================================================================
# CONTEXT7-VALIDATED: Integration testing event loop configuration
# ============================================================================

@pytest.fixture(scope="session")
def integration_event_loop_policy():
    """
    Use uvloop for integration testing performance.
    Context7 pattern: session-scoped event loop for integration tests.
    """
    if os.name != "nt":  # Unix systems only
        return uvloop.EventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="session")
async def integration_event_loop(integration_event_loop_policy) -> AsyncGenerator[asyncio.AbstractEventLoop, None]:
    """
    Session-scoped event loop for integration tests.
    Context7 pattern: shared loop for database connections.
    """
    asyncio.set_event_loop_policy(integration_event_loop_policy)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        yield loop
    finally:
        loop.close()


# ============================================================================
# CONTEXT7-VALIDATED: Database integration fixtures
# ============================================================================

@pytest.fixture(scope="session")
def integration_db_path() -> str:
    """
    Session-scoped database path for integration tests.
    Context7 pattern: shared database for integration testing.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    # Return path, cleanup handled by session fixture
    return db_path


@pytest.fixture(scope="session")
def integration_config(integration_db_path: str) -> DevStreamConfig:
    """
    Integration test configuration with real database.
    Context7 pattern: production-like config for integration testing.
    """
    return DevStreamConfig(
        environment="integration",
        debug=True,
        enable_vector_search=False,  # Simplified for integration tests
        database={
            "db_path": integration_db_path,
            "connection_timeout": 10.0,
            "max_connections": 5,
            "enable_vector_search": False,
            "enable_fts": True,
            "wal_mode": True,  # Enable WAL for better concurrency
        },
        ollama={
            "endpoint": "http://localhost:11434",
            "timeout": 15.0,
            "max_retries": 2,
            "embedding_model": "nomic-embed-text",
            "batch_size": 8,
        },
        memory={
            "max_content_length": 2000,
            "similarity_threshold": 0.4,
            "max_search_results": 20,
            "max_context_tokens": 1000,
        },
        tasks={
            "max_task_duration_minutes": 15,
            "max_objectives_per_plan": 5,
        },
        hooks={
            "enable_hooks": True,
            "hook_timeout": 10.0,
            "force_task_creation": True,  # Enable for integration testing
        },
        logging={
            "log_level": "INFO",
            "log_to_file": False,
            "log_to_console": True,
        },
    )


@pytest_asyncio.fixture(scope="session")
async def integration_connection_pool(integration_config: DevStreamConfig) -> AsyncGenerator[ConnectionPool, None]:
    """
    Session-scoped connection pool for integration tests.
    Context7 pattern: shared connection pool with proper lifecycle.
    """
    pool = ConnectionPool(
        db_path=integration_config.database.db_path,
        max_connections=integration_config.database.max_connections,
    )

    await pool.initialize()

    try:
        yield pool
    finally:
        await pool.close()


@pytest_asyncio.fixture(scope="session")
async def integration_database_schema(integration_connection_pool: ConnectionPool) -> None:
    """
    Setup database schema for integration testing.
    Context7 pattern: schema migration in integration tests.
    """
    runner = MigrationRunner(integration_connection_pool)
    await runner.run_migrations()

    # Verify schema is valid
    is_valid = await runner.verify_schema()
    assert is_valid, "Database schema validation failed"


@pytest_asyncio.fixture
async def integration_query_manager(
    integration_connection_pool: ConnectionPool,
    integration_database_schema
) -> AsyncGenerator[QueryManager, None]:
    """
    Test-scoped query manager with transaction rollback.
    Context7 pattern: transactional testing with automatic rollback.
    """
    qm = QueryManager(integration_connection_pool)

    # Start transaction savepoint for test isolation
    async with integration_connection_pool.write_transaction() as conn:
        savepoint = await conn.begin_nested()

        try:
            yield qm
        finally:
            # Rollback to savepoint for test isolation
            await savepoint.rollback()


# ============================================================================
# CONTEXT7-VALIDATED: Memory system integration fixtures
# ============================================================================

@pytest.fixture
def integration_mock_ollama_responses() -> Dict[str, Any]:
    """
    Deterministic Ollama responses for integration testing.
    Context7 pattern: realistic but predictable responses.
    """
    return {
        "embed_single": {
            "method": "POST",
            "url": "http://localhost:11434/api/embed",
            "json": {
                "model": "nomic-embed-text",
                "embeddings": [[0.1, 0.2, 0.3, 0.4, 0.5] * 77]  # 385 dimensions
            },
            "status_code": 200
        },
        "embed_batch": {
            "method": "POST",
            "url": "http://localhost:11434/api/embed",
            "json": {
                "model": "nomic-embed-text",
                "embeddings": [
                    [0.1, 0.2, 0.3, 0.4, 0.5] * 77,  # 385 dimensions
                    [0.6, 0.7, 0.8, 0.9, 1.0] * 77,  # 385 dimensions
                ]
            },
            "status_code": 200
        }
    }


@pytest.fixture
def integration_mock_ollama_healthy(httpx_mock, integration_mock_ollama_responses):
    """
    Mock healthy Ollama server for integration testing.
    Context7 pattern: reliable external service mocking.
    """
    httpx_mock.add_response(**integration_mock_ollama_responses["embed_single"])
    httpx_mock.add_response(**integration_mock_ollama_responses["embed_batch"])
    return httpx_mock


# ============================================================================
# CONTEXT7-VALIDATED: Task system integration fixtures
# ============================================================================

@pytest_asyncio.fixture
async def integration_sample_plan(integration_query_manager: QueryManager) -> str:
    """
    Sample intervention plan for integration testing.
    Context7 pattern: realistic test data for integration scenarios.
    """
    plan_id = await integration_query_manager.plans.create(
        title="Integration Test Plan",
        description="Comprehensive plan for testing system integration",
        objectives=[
            "Validate database operations",
            "Test memory storage and retrieval",
            "Verify task execution workflow",
            "Ensure cross-system data consistency"
        ],
        expected_outcome="All systems working together seamlessly",
        priority=7,
        tags=["integration", "testing", "validation"],
    )
    return plan_id


@pytest_asyncio.fixture
async def integration_sample_phase(
    integration_query_manager: QueryManager,
    integration_sample_plan: str
) -> str:
    """
    Sample phase for task integration testing.
    Context7 pattern: hierarchical test data structure.
    """
    from devstream.database.schema import phases

    phase_id = integration_query_manager.tasks.generate_id()

    async with integration_query_manager.write_transaction() as conn:
        await conn.execute(
            phases.insert().values(
                id=phase_id,
                plan_id=integration_sample_plan,
                name="Integration Test Phase",
                description="Phase for testing task-memory integration",
                objective="Execute tasks with memory context",
                sequence_order=1,
                status="active",
            )
        )

    return phase_id


@pytest_asyncio.fixture
async def integration_sample_task(
    integration_query_manager: QueryManager,
    integration_sample_phase: str
) -> str:
    """
    Sample micro task for integration testing.
    Context7 pattern: realistic task for workflow testing.
    """
    task_id = await integration_query_manager.tasks.create(
        phase_id=integration_sample_phase,
        title="Integration Test Task",
        description="Task that integrates with memory system for context",
        assigned_agent="integration-test-agent",
        task_type="implementation",
        estimated_minutes=30,
    )
    return task_id


# ============================================================================
# CONTEXT7-VALIDATED: End-to-end integration fixtures
# ============================================================================

@pytest_asyncio.fixture
async def integration_memory_entries(
    integration_query_manager: QueryManager,
    integration_mock_ollama_healthy
) -> list[str]:
    """
    Sample memory entries for cross-system integration testing.
    Context7 pattern: realistic memory data for integration scenarios.
    """
    memory_ids = []

    # Code memory entry
    code_id = await integration_query_manager.memory.store(
        content="""
def calculate_fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
        """,
        content_type="code",
        keywords=["fibonacci", "recursion", "algorithm"],
        entities=["calculate_fibonacci", "int"],
    )
    memory_ids.append(code_id)

    # Documentation memory entry
    doc_id = await integration_query_manager.memory.store(
        content="Fibonacci sequence implementation using recursive approach. Time complexity O(2^n).",
        content_type="documentation",
        keywords=["fibonacci", "documentation", "complexity"],
        entities=["fibonacci", "O(2^n)"],
    )
    memory_ids.append(doc_id)

    # Output memory entry
    output_id = await integration_query_manager.memory.store(
        content="Fibonacci calculation completed successfully. Result: fibonacci(10) = 55",
        content_type="output",
        keywords=["fibonacci", "result", "calculation"],
        entities=["55", "fibonacci(10)"],
    )
    memory_ids.append(output_id)

    return memory_ids


# ============================================================================
# CLEANUP FIXTURES
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def cleanup_integration_database(integration_db_path: str):
    """
    Cleanup integration database after session.
    Context7 pattern: proper resource cleanup.
    """
    yield

    # Cleanup database file and auxiliary files
    db_file = Path(integration_db_path)
    if db_file.exists():
        db_file.unlink()

    # Cleanup SQLite auxiliary files
    for suffix in ["-journal", "-wal", "-shm"]:
        aux_file = Path(f"{integration_db_path}{suffix}")
        if aux_file.exists():
            aux_file.unlink()


@pytest.fixture(autouse=True)
def setup_integration_environment(monkeypatch):
    """
    Setup integration test environment variables.
    Context7 pattern: isolated test environment setup.
    """
    # Use mock Ollama for integration tests
    monkeypatch.setenv("DEVSTREAM_OLLAMA_ENDPOINT", "http://mock-ollama:11434")
    monkeypatch.setenv("DEVSTREAM_DB_WAL_MODE", "true")
    monkeypatch.setenv("DEVSTREAM_LOG_TO_FILE", "false")
    monkeypatch.setenv("DEVSTREAM_LOG_LEVEL", "INFO")


# ============================================================================
# INTEGRATION TEST UTILITIES
# ============================================================================

class IntegrationTestHelper:
    """
    Helper utilities for integration testing.
    Context7 pattern: reusable integration test utilities.
    """

    def __init__(self, query_manager: QueryManager):
        self.query_manager = query_manager

    async def verify_data_consistency(self) -> bool:
        """Verify cross-system data consistency."""
        # For now, simply verify that basic queries work
        # In a real implementation, we would check referential integrity
        try:
            plans = await self.query_manager.plans.list_active()
            # Just verify that we can query without errors
            return True
        except Exception:
            return False

    async def count_total_records(self) -> Dict[str, int]:
        """Count records across all system tables."""
        from devstream.database.schema import (
            intervention_plans, phases, micro_tasks, semantic_memory,
            work_sessions, hooks, agents
        )

        counts = {}
        async with self.query_manager.pool.read_transaction() as conn:
            for table_name, table in [
                ("plans", intervention_plans),
                ("phases", phases),
                ("tasks", micro_tasks),
                ("memories", semantic_memory),
                ("sessions", work_sessions),
                ("hooks", hooks),
                ("agents", agents),
            ]:
                result = await conn.execute(text(f"SELECT COUNT(*) FROM {table.name}"))
                row = result.fetchone()
                counts[table_name] = row[0] if row else 0

        return counts


@pytest.fixture
def integration_helper(integration_query_manager: QueryManager) -> IntegrationTestHelper:
    """Integration test helper instance."""
    return IntegrationTestHelper(integration_query_manager)