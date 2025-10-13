#!/usr/bin/env python3
"""
Unit tests for DevStream Direct Database Client

Tests direct database functionality replacing MCP server.
"""

import pytest
import asyncio
import tempfile
import os
import sys
from pathlib import Path

# Add hooks to path
sys.path.append(str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'utils'))

from direct_client import DevStreamDirectClient, DatabaseException


@pytest.fixture
async def test_client():
    """Create a test direct client with temporary database."""
    # Use a database path within the project directory
    test_db_dir = Path(__file__).parent.parent.parent / "data" / "test"
    test_db_dir.mkdir(parents=True, exist_ok=True)
    db_path = test_db_dir / "test_direct_client.db"

    # Remove existing test database
    if db_path.exists():
        os.unlink(db_path)

    client = DevStreamDirectClient(str(db_path))
    yield client

    # Cleanup
    if db_path.exists():
        os.unlink(db_path)


@pytest.mark.asyncio
async def test_store_memory(test_client):
    """Test memory storage functionality."""
    result = await test_client.store_memory(
        content="Test memory content",
        content_type="context",
        keywords=["test", "memory"],
        session_id="test-session-123"
    )

    assert result is not None
    assert result["success"] is True
    assert "memory_id" in result
    assert result["content_type"] == "context"


@pytest.mark.asyncio
async def test_search_memory(test_client):
    """Test memory search functionality."""
    # First store some test data
    await test_client.store_memory(
        content="Python code for testing database operations",
        content_type="code",
        keywords=["python", "testing", "database"],
        session_id="test-session-123"
    )

    await test_client.store_memory(
        content="Documentation about direct client implementation",
        content_type="documentation",
        keywords=["docs", "direct-client", "implementation"],
        session_id="test-session-123"
    )

    # Test search
    result = await test_client.search_memory(
        query="python testing",
        limit=5
    )

    assert result is not None
    assert result["success"] is True
    assert "results" in result
    assert result["count"] >= 0


@pytest.mark.asyncio
async def test_create_task(test_client):
    """Test task creation functionality."""
    result = await test_client.create_task(
        title="Test Direct Client Task",
        description="Testing task creation via direct client",
        task_type="testing",
        priority=5,
        phase_name="Direct Client Testing",
        project="Test Project"
    )

    assert result is not None
    assert result["success"] is True
    assert "task_id" in result
    assert result["status"] == "pending"


@pytest.mark.asyncio
async def test_list_tasks(test_client):
    """Test task listing functionality."""
    # Create a test task first
    await test_client.create_task(
        title="List Test Task",
        description="Task for testing list functionality",
        task_type="testing",
        priority=3,
        phase_name="Testing Phase"
    )

    # List tasks
    result = await test_client.list_tasks()

    assert result is not None
    assert result["success"] is True
    assert "tasks" in result
    assert result["count"] >= 0


@pytest.mark.asyncio
async def test_update_task(test_client):
    """Test task update functionality."""
    # Create a task first
    create_result = await test_client.create_task(
        title="Update Test Task",
        description="Task for testing update functionality",
        task_type="testing",
        priority=4,
        phase_name="Testing Phase"
    )

    task_id = create_result["task_id"]

    # Update the task
    result = await test_client.update_task(
        task_id=task_id,
        status="completed"
    )

    assert result is not None
    assert result["success"] is True
    assert result["task_id"] == task_id
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_health_check(test_client):
    """Test health check functionality."""
    result = await test_client.health_check()

    assert result is True


def test_get_stats(test_client):
    """Test statistics retrieval."""
    stats = test_client.get_stats()

    assert stats is not None
    assert stats["client_type"] == "direct"
    assert "features" in stats
    assert stats["features"]["memory_storage"] is True
    assert stats["features"]["task_management"] is True


@pytest.mark.asyncio
async def test_trigger_checkpoint(test_client):
    """Test checkpoint trigger functionality."""
    result = await test_client.trigger_checkpoint(reason="test")

    assert result is not None
    assert result["success"] is True
    assert "checkpoint_id" in result
    assert result["reason"] == "test"


def test_error_handling():
    """Test error handling with invalid database path."""
    # Reset ConnectionManager singleton to force path validation
    import connection_manager
    connection_manager.ConnectionManager._instance = None

    # Use a path outside the project directory
    invalid_path = "/tmp/nonexistent_deep_path/test.db"

    # Debug: Check what exceptions are raised
    try:
        DevStreamDirectClient(invalid_path)
        assert False, "Expected DatabaseException but no exception was raised"
    except DatabaseException:
        # Expected exception
        pass
    except Exception as e:
        assert False, f"Expected DatabaseException but got {type(e).__name__}: {e}"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])