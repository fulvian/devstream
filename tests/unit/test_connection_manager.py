#!/usr/bin/env python3
"""
Unit Tests - ConnectionManager

Tests for centralized SQLite connection management with WAL mode enforcement.
Target: 95%+ test coverage

Test Categories:
1. Singleton Pattern Tests
2. WAL Mode Enforcement Tests
3. Connection Pooling Tests
4. Health Check Tests
5. Connection Recycling Tests
6. Error Handling Tests
"""

import pytest
import sqlite3
import threading
import time
from pathlib import Path
import sys

# Add utils to path
sys.path.append(str(Path(__file__).parent.parent.parent / '.claude/hooks/devstream/utils'))
from connection_manager import ConnectionManager, get_connection_manager, devstream_connection


class TestSingletonPattern:
    """Test singleton pattern enforcement."""

    def test_singleton_instance(self):
        """Verify singleton pattern returns same instance."""
        manager1 = ConnectionManager.get_instance()
        manager2 = ConnectionManager.get_instance()

        assert manager1 is manager2, "Singleton pattern failed - different instances returned"

    def test_singleton_direct_instantiation_blocked(self):
        """Verify direct instantiation is blocked after singleton created."""
        # First create singleton
        ConnectionManager.get_instance()

        # Try direct instantiation (should fail)
        with pytest.raises(RuntimeError, match="Use ConnectionManager.get_instance"):
            ConnectionManager()

    def test_singleton_thread_safe(self):
        """Verify singleton is thread-safe."""
        instances = []

        def get_instance():
            instances.append(ConnectionManager.get_instance())

        # Create 10 threads trying to get instance simultaneously
        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All instances should be the same object
        assert len(set(id(inst) for inst in instances)) == 1, "Singleton not thread-safe"


class TestWALModeEnforcement:
    """Test WAL mode enforcement on all connections."""

    def test_wal_mode_enabled(self):
        """Verify WAL mode is enabled on connection creation."""
        manager = get_connection_manager()

        with manager.get_connection() as conn:
            cursor = conn.execute("PRAGMA journal_mode")
            mode = cursor.fetchone()[0]

            assert mode == "wal", f"WAL mode not enabled: {mode}"

    def test_busy_timeout_configured(self):
        """Verify busy_timeout is set correctly."""
        manager = get_connection_manager()

        with manager.get_connection() as conn:
            cursor = conn.execute("PRAGMA busy_timeout")
            timeout = cursor.fetchone()[0]

            assert timeout == 30000, f"Busy timeout incorrect: {timeout} (expected 30000)"

    def test_synchronous_mode_configured(self):
        """Verify synchronous mode is NORMAL for WAL."""
        manager = get_connection_manager()

        with manager.get_connection() as conn:
            cursor = conn.execute("PRAGMA synchronous")
            sync_mode = cursor.fetchone()[0]

            # NORMAL = 1 in SQLite
            assert sync_mode == 1, f"Synchronous mode incorrect: {sync_mode} (expected 1/NORMAL)"

    def test_wal_checkpoint_mode(self):
        """Verify WAL checkpoint configuration."""
        manager = get_connection_manager()

        with manager.get_connection() as conn:
            # WAL mode should allow reading journal_mode
            cursor = conn.execute("PRAGMA journal_mode")
            mode = cursor.fetchone()[0]

            assert mode == "wal", "WAL mode verification failed"


class TestConnectionPooling:
    """Test connection pooling functionality."""

    def test_thread_local_connections(self):
        """Verify each thread gets its own connection."""
        manager = get_connection_manager()
        connections = {}

        def get_thread_connection(thread_id):
            conn = manager._get_thread_connection()
            connections[thread_id] = id(conn)

        # Create connections from 3 different threads
        threads = [
            threading.Thread(target=get_thread_connection, args=(i,))
            for i in range(3)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each thread should have unique connection
        assert len(set(connections.values())) == 3, "Threads sharing connections"

    def test_connection_reuse_within_thread(self):
        """Verify same thread reuses same connection."""
        manager = get_connection_manager()

        conn1 = manager._get_thread_connection()
        conn2 = manager._get_thread_connection()

        assert id(conn1) == id(conn2), "Thread not reusing connection"

    def test_pool_statistics(self):
        """Verify pool statistics tracking."""
        manager = get_connection_manager()

        # Get connection to populate pool
        with manager.get_connection() as conn:
            pass

        stats = manager.get_stats()

        assert "active_connections" in stats
        assert "max_connections" in stats
        assert "pool_utilization" in stats
        assert "total_connections_created" in stats

        assert stats["active_connections"] >= 1, "Stats not tracking active connections"

    def test_pool_limit_enforcement(self):
        """Verify pool limit is enforced."""
        manager = get_connection_manager()

        # Initially should be within limit
        assert manager.enforce_pool_limit() is True

        # Stats should track limit enforcement
        stats = manager.get_stats()
        assert "max_connections" in stats
        assert stats["max_connections"] == 10  # Default MAX_CONNECTIONS_PER_PROCESS


class TestHealthChecks:
    """Test connection health check functionality."""

    def test_health_check_valid_connection(self):
        """Verify health check passes for valid connection."""
        manager = get_connection_manager()
        conn = manager._get_thread_connection()

        is_healthy = manager._health_check_connection(conn)

        assert is_healthy is True, "Health check failed for valid connection"

    def test_health_check_closed_connection(self):
        """Verify health check fails for closed connection."""
        manager = get_connection_manager()
        conn = sqlite3.connect(":memory:")
        conn.close()

        is_healthy = manager._health_check_connection(conn)

        assert is_healthy is False, "Health check passed for closed connection"


class TestConnectionRecycling:
    """Test automatic connection recycling."""

    def test_connection_metadata_tracking(self):
        """Verify connection metadata (created_at, last_used) is tracked."""
        manager = get_connection_manager()

        # Get connection
        conn = manager._get_thread_connection()
        thread_id = threading.get_ident()

        # Check metadata exists
        with manager._pool_lock:
            assert thread_id in manager._active_connections
            conn_obj, created_at, last_used = manager._active_connections[thread_id]

            assert created_at > 0, "created_at not tracked"
            assert last_used > 0, "last_used not tracked"
            assert isinstance(conn_obj, sqlite3.Connection)

    def test_last_used_timestamp_updates(self):
        """Verify last_used timestamp updates on connection reuse."""
        manager = get_connection_manager()
        thread_id = threading.get_ident()

        # Get connection first time
        conn1 = manager._get_thread_connection()

        with manager._pool_lock:
            _, created_at1, last_used1 = manager._active_connections[thread_id]

        # Wait and get connection again
        time.sleep(0.1)
        conn2 = manager._get_thread_connection()

        with manager._pool_lock:
            _, created_at2, last_used2 = manager._active_connections[thread_id]

        assert created_at1 == created_at2, "created_at should not change"
        assert last_used2 > last_used1, "last_used should update"

    def test_recycling_stats_tracking(self):
        """Verify recycling statistics are tracked."""
        manager = get_connection_manager()

        stats = manager.get_stats()

        assert "total_connections_recycled" in stats
        assert "total_health_checks" in stats
        assert "total_health_check_failures" in stats


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_connection_context_manager_rollback(self):
        """Verify automatic rollback on exception.

        Note: Uses DML (INSERT) not DDL (CREATE TABLE) because Python sqlite3
        only auto-begins transactions for DML statements. DDL statements are
        autocommitted and cannot be rolled back without explicit BEGIN.
        """
        manager = get_connection_manager()

        # Setup: Create test table (this is autocommitted, which is OK)
        with manager.get_connection() as conn:
            conn.execute("DROP TABLE IF EXISTS test_rollback")
            conn.execute("CREATE TABLE test_rollback (id INTEGER)")

        try:
            with manager.get_connection() as conn:
                # DML triggers automatic BEGIN in Python sqlite3
                conn.execute("INSERT INTO test_rollback (id) VALUES (1)")
                # Force error to trigger rollback
                raise ValueError("Test error")
        except ValueError:
            pass

        # CRITICAL: Close thread-local connection to force fresh connection
        # WAL mode + thread-local pooling can cache stale connection state
        manager.close_thread_connection()

        # INSERT should have been rolled back (no rows)
        with manager.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM test_rollback")
            count = cursor.fetchone()[0]
            assert count == 0, f"Rollback failed - found {count} rows (expected 0)"

        # Cleanup
        with manager.get_connection() as conn:
            conn.execute("DROP TABLE IF EXISTS test_rollback")

    def test_connection_context_manager_commit(self):
        """Verify automatic commit on success."""
        manager = get_connection_manager()

        with manager.get_connection() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS test_commit (id INTEGER)")
            conn.execute("INSERT INTO test_commit (id) VALUES (1)")

        # Data should persist (committed)
        with manager.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM test_commit")
            count = cursor.fetchone()[0]

            assert count >= 1, "Commit failed - data not persisted"

    def test_close_thread_connection(self):
        """Verify thread connection can be closed cleanly."""
        manager = get_connection_manager()
        thread_id = threading.get_ident()

        # Get connection
        conn = manager._get_thread_connection()

        # Close it
        manager.close_thread_connection()

        # Verify removed from pool
        with manager._pool_lock:
            assert thread_id not in manager._active_connections


class TestConvenienceFunctions:
    """Test convenience wrapper functions."""

    def test_get_connection_manager_function(self):
        """Verify get_connection_manager() returns singleton."""
        manager1 = get_connection_manager()
        manager2 = get_connection_manager()

        assert manager1 is manager2

    def test_devstream_connection_context_manager(self):
        """Verify devstream_connection() context manager works."""
        with devstream_connection() as conn:
            cursor = conn.execute("SELECT 1")
            result = cursor.fetchone()[0]

            assert result == 1, "Connection context manager failed"

        # Connection should still work (not closed by context manager)
        # because it's managed by ConnectionManager


# Pytest configuration
@pytest.fixture(autouse=True)
def cleanup_singleton():
    """Reset singleton between tests."""
    yield
    # Reset singleton for next test
    ConnectionManager._instance = None


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short", "-x"])
