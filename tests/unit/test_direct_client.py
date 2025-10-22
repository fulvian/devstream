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
import sqlite3
from unittest.mock import patch, MagicMock
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


class TestGracefulDegradation:
    """Test graceful degradation architecture."""

    @pytest.fixture
    def client(self):
        """Create a DevStreamDirectClient instance for testing."""
        # Create a temporary in-memory database
        conn = sqlite3.connect(":memory:")

        # Initialize with required tables
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL,
                keywords TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                -- Vector column for embeddings
                embedding BLOB
            )
        """)

        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_memory_chunks USING fts5(
                content,
                keywords,
                content_type,
                created_at
            )
        """)

        conn.close()

        # Reset ConnectionManager singleton to avoid conflicts
        import connection_manager
        connection_manager.ConnectionManager._instance = None

        return DevStreamDirectClient()

    def test_method_signature_and_return_type(self, client):
        """Test that method signature matches specification."""
        # Check method exists
        assert hasattr(client, '_initialize_vector_search_with_fallback')

        # Check method is callable
        assert callable(getattr(client, '_initialize_vector_search_with_fallback'))

        # Check return type annotation (should be bool)
        import inspect
        sig = inspect.signature(client._initialize_vector_search_with_fallback)
        assert sig.return_annotation == bool

    def test_method_docstring_complete(self, client):
        """Test that method has complete docstring with example."""
        docstring = client._initialize_vector_search_with_fallback.__doc__

        # Check docstring exists and has required sections
        assert docstring is not None
        assert "Initialize vector search with graceful degradation" in docstring
        assert "Context7 research patterns" in docstring
        assert "Args:" in docstring
        assert "Returns:" in docstring
        assert "Raises:" in docstring
        assert "Example:" in docstring

    def test_vector_search_success_case(self, client):
        """Test successful vector search initialization."""
        with patch('sqlite_vec.load') as mock_load:
            with patch('sqlite3.connect') as mock_connect:
                # Setup mock connection
                mock_conn = MagicMock()
                mock_connect.return_value = mock_conn

                # Call the method
                result = client._initialize_vector_search_with_fallback()

                # Verify vector search is enabled
                assert result is True
                assert client.vector_search_available is True

                # Verify extension loading was attempted
                mock_load.assert_called_once_with(mock_conn)

    def test_import_error_fallback(self, client):
        """Test fallback to FTS-only mode when sqlite-vec not importable."""
        with patch.dict('sys.modules', {'sqlite_vec': None}):
            # Reset vector_search_available to test the method
            client.vector_search_available = False

            # Call method should handle ImportError gracefully
            result = client._initialize_vector_search_with_fallback()

            # Should fallback to FTS-only mode
            assert result is False
            assert client.vector_search_available is False

    def test_extension_load_error_fallback(self, client):
        """Test fallback when extension loading fails."""
        with patch('sqlite_vec.load', side_effect=Exception("Extension load failed")):
            # Reset vector_search_available
            client.vector_search_available = False

            # Call method should handle load error gracefully
            result = client._initialize_vector_search_with_fallback()

            # Should fallback to FTS-only mode
            assert result is False
            assert client.vector_search_available is False

    def test_database_connection_error_fallback(self, client):
        """Test fallback when database connection fails."""
        with patch('sqlite3.connect', side_effect=sqlite3.Error("Connection failed")):
            # Reset vector_search_available
            client.vector_search_available = False

            # Call method should handle connection error gracefully
            result = client._initialize_vector_search_with_fallback()

            # Should fallback to FTS-only mode
            assert result is False
            assert client.vector_search_available is False

    def test_logging_on_success(self, client):
        """Test proper logging on successful initialization."""
        with patch('sqlite_vec.load') as mock_load:
            with patch('sqlite3.connect') as mock_connect:
                mock_conn = MagicMock()
                mock_connect.return_value = mock_conn

                # Mock logger
                mock_logger = MagicMock()
                mock_logger.logger = MagicMock()
                client.logger = mock_logger

                # Call method
                result = client._initialize_vector_search_with_fallback()

                # Verify success logging
                assert result is True
                assert client.vector_search_available is True
                mock_logger.logger.info.assert_called_with("Vector search initialized successfully")

    def test_logging_on_fallback(self, client):
        """Test proper warning logging on fallback."""
        with patch('sqlite_vec.load', side_effect=Exception("Test error")):
            # Mock logger
            mock_logger = MagicMock()
            mock_logger.logger = MagicMock()
            client.logger = mock_logger

            # Call method
            result = client._initialize_vector_search_with_fallback()

            # Verify fallback logging
            assert result is False
            assert client.vector_search_available is False
            mock_logger.logger.warning.assert_called_with(
                "Vector search unavailable, using FTS-only mode",
                extra={"error": "Test error"}
            )

    def test_no_exception_raised_on_failure(self, client):
        """Test that method doesn't raise exceptions on failure."""
        with patch('sqlite_vec.load', side_effect=RuntimeError("Critical error")):
            # Should not raise any exception
            try:
                result = client._initialize_vector_search_with_fallback()
                assert result is False
                assert client.vector_search_available is False
            except Exception as e:
                pytest.fail(f"Method raised exception {e} when it should have handled gracefully")

    def test_context7_pattern_usage(self, client):
        """Test that Context7 patterns are properly implemented."""
        # Check that the implementation follows Context7 patterns
        with patch('sqlite_vec.load') as mock_load:
            with patch('sqlite3.connect') as mock_connect:
                mock_conn = MagicMock()
                mock_connect.return_value = mock_conn

                # Call method
                result = client._initialize_vector_search_with_fallback()

                # Verify Context7 pattern: enable_load_extension -> load -> disable_load_extension
                assert mock_conn.enable_load_extension.called
                assert mock_conn.enable_load_extension.call_count == 2

                # Check calls order: enable(True) -> load() -> enable(False)
                calls = mock_conn.enable_load_extension.call_args_list
                assert calls[0][0] == (True,)  # First call with True
                assert calls[1][0] == (False,)  # Second call with False

    def test_connection_cleanup_on_success(self, client):
        """Test that test connection is properly cleaned up on success."""
        with patch('sqlite_vec.load') as mock_load:
            mock_conn = MagicMock()
            with patch('sqlite3.connect', return_value=mock_conn):
                # Call method
                result = client._initialize_vector_search_with_fallback()

                # Verify connection was closed
                mock_conn.close.assert_called_once()

    def test_connection_cleanup_on_failure(self, client):
        """Test that test connection is properly cleaned up on failure."""
        with patch('sqlite_vec.load', side_effect=Exception("Load failed")):
            mock_conn = MagicMock()
            with patch('sqlite3.connect', return_value=mock_conn):
                # Call method
                result = client._initialize_vector_search_with_fallback()

                # Verify connection was still closed even on failure
                mock_conn.close.assert_called_once()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])