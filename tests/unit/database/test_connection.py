"""
Unit tests for database connection and pool management.

Context7-validated patterns for SQLAlchemy 2.0 async testing:
- Transaction rollback patterns
- Connection pool management
- Performance monitoring
- Error boundary testing
"""

import pytest
import pytest_asyncio
from pathlib import Path
from sqlalchemy import text

from devstream.database.connection import ConnectionPool
from devstream.core.exceptions import DatabaseError


@pytest.mark.unit
@pytest.mark.database
class TestConnectionPool:
    """Test connection pool functionality with Context7-validated patterns."""

    @pytest_asyncio.fixture
    async def pool(self, temp_db_path: str):
        """Create connection pool for testing."""
        pool = ConnectionPool(
            db_path=temp_db_path,
            max_connections=3
        )
        await pool.initialize()
        yield pool
        await pool.close()

    async def test_pool_initialization(self, pool: ConnectionPool):
        """Test pool initializes correctly with Context7-validated patterns."""
        assert pool.engine is not None
        assert pool.max_connections == 3
        assert pool.stats["connections_created"] == 0
        assert isinstance(pool.db_path, Path)

    async def test_read_transaction_context(self, pool: ConnectionPool):
        """Test read transaction context manager pattern (Context7-validated)."""
        async with pool.read_transaction() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.fetchone()
            assert row[0] == 1

        # Verify stats tracking
        assert pool.stats["read_queries"] == 1

    async def test_write_transaction_context(self, pool: ConnectionPool):
        """Test write transaction context manager with rollback (Context7-validated)."""
        # Test successful write transaction
        async with pool.write_transaction() as conn:
            await conn.execute(text("CREATE TABLE test_table (id INTEGER, name TEXT)"))
            await conn.execute(text("INSERT INTO test_table (id, name) VALUES (1, 'test')"))

        # Verify data was committed
        async with pool.read_transaction() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM test_table"))
            count = result.fetchone()[0]
            assert count == 1

        # Verify stats tracking
        assert pool.stats["write_queries"] == 1

    async def test_write_transaction_rollback(self, pool: ConnectionPool):
        """Test write transaction rollback on exception (Context7-validated)."""
        # Create table first
        async with pool.write_transaction() as conn:
            await conn.execute(text("CREATE TABLE rollback_test (id INTEGER, name TEXT)"))

        # Test rollback on exception
        with pytest.raises(Exception):
            async with pool.write_transaction() as conn:
                await conn.execute(text("INSERT INTO rollback_test (id, name) VALUES (1, 'test')"))
                # Force rollback by raising exception
                raise Exception("Test rollback")

        # Verify data was rolled back
        async with pool.read_transaction() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM rollback_test"))
            count = result.fetchone()[0]
            assert count == 0

    async def test_read_convenience_method(self, pool: ConnectionPool):
        """Test read transaction convenience usage."""
        async with pool.read_transaction() as conn:
            result = await conn.execute(text("SELECT 42 as answer"))
            row = result.fetchone()
            assert row[0] == 42
        assert pool.stats["read_queries"] >= 1

    async def test_write_convenience_method(self, pool: ConnectionPool):
        """Test write transaction convenience usage."""
        async with pool.write_transaction() as conn:
            await conn.execute(text("CREATE TABLE write_test (id INTEGER)"))
            await conn.execute(text("INSERT INTO write_test (id) VALUES (123)"))

        async with pool.read_transaction() as conn:
            result = await conn.execute(text("SELECT id FROM write_test"))
            row = result.fetchone()
            assert row[0] == 123
        assert pool.stats["write_queries"] >= 1

    async def test_pool_stats(self, pool: ConnectionPool):
        """Test pool statistics tracking."""
        initial_stats = pool.stats.copy()

        # Execute some operations
        async with pool.read_transaction() as conn:
            await conn.execute(text("SELECT 1"))
        async with pool.write_transaction() as conn:
            await conn.execute(text("CREATE TABLE stats_test (id INTEGER)"))

        # Verify stats increased
        assert pool.stats["read_queries"] > initial_stats["read_queries"]
        assert pool.stats["write_queries"] > initial_stats["write_queries"]

    async def test_connection_recycling(self, pool: ConnectionPool):
        """Test connection recycling behavior."""
        # Perform multiple operations to test connection reuse
        for i in range(5):
            async with pool.read_transaction() as conn:
                result = await conn.execute(text(f"SELECT {i}"))
                row = result.fetchone()
                assert row[0] == i

        # Stats should show connection reuse
        assert pool.stats["read_queries"] == 5

    async def test_nested_transaction_savepoint(self, pool: ConnectionPool):
        """Test nested transaction with savepoint (Context7-validated pattern)."""
        async with pool.write_transaction() as conn:
            # Create table in outer transaction
            await conn.execute(text("CREATE TABLE nested_test (id INTEGER, value TEXT)"))

            # Start nested transaction (savepoint)
            savepoint = await conn.begin_nested()
            try:
                await conn.execute(text("INSERT INTO nested_test VALUES (1, 'good')"))
                await conn.execute(text("INSERT INTO nested_test VALUES (2, 'bad')"))

                # Simulate error and rollback savepoint
                await savepoint.rollback()
            except Exception:
                await savepoint.rollback()
                raise

            # Insert valid data after savepoint rollback
            await conn.execute(text("INSERT INTO nested_test VALUES (3, 'final')"))

        # Verify only final insert survived
        async with pool.read_transaction() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM nested_test"))
            count = result.fetchone()[0]
            assert count == 1

            result = await conn.execute(text("SELECT value FROM nested_test"))
            value = result.fetchone()[0]
            assert value == "final"

    async def test_database_error_handling(self, pool: ConnectionPool):
        """Test database error handling and connection recovery."""
        # Test invalid SQL handling
        with pytest.raises(Exception):  # Will be a SQLAlchemy exception
            async with pool.read_transaction() as conn:
                await conn.execute(text("INVALID SQL SYNTAX"))

        # Pool should still work after error
        async with pool.read_transaction() as conn:
            result = await conn.execute(text("SELECT 'recovery_test'"))
            row = result.fetchone()
            assert row[0] == "recovery_test"

    async def test_concurrent_transactions(self, pool: ConnectionPool):
        """Test concurrent transaction handling."""
        import asyncio

        async def read_operation():
            async with pool.read_transaction() as conn:
                result = await conn.execute(text("SELECT 'concurrent_read'"))
                return result.fetchone()[0]

        async def write_operation():
            async with pool.write_transaction() as conn:
                await conn.execute(text("CREATE TABLE IF NOT EXISTS concurrent_test (id INTEGER)"))
                await conn.execute(text("INSERT INTO concurrent_test VALUES (1)"))
                return "write_complete"

        # Run operations concurrently
        results = await asyncio.gather(
            read_operation(),
            write_operation(),
            read_operation()
        )

        assert results[0] == "concurrent_read"
        assert results[1] == "write_complete"
        assert results[2] == "concurrent_read"


@pytest.mark.unit
@pytest.mark.database
class TestConnectionPoolPerformance:
    """Test connection pool performance characteristics."""

    @pytest_asyncio.fixture
    async def pool(self, temp_db_path: str):
        """Create connection pool for performance testing."""
        pool = ConnectionPool(db_path=temp_db_path, max_connections=5)
        await pool.initialize()
        yield pool
        await pool.close()

    @pytest.mark.performance
    async def test_connection_pool_performance(self, pool: ConnectionPool):
        """Test connection pool performance under load."""
        import time

        # Warm up the pool
        async with pool.read_transaction() as conn:
            await conn.execute(text("SELECT 1"))

        start_time = time.time()

        # Perform multiple operations
        for i in range(10):
            async with pool.read_transaction() as conn:
                result = await conn.execute(text(f"SELECT {i}"))
                result.fetchone()

        execution_time = time.time() - start_time

        # Should complete within reasonable time (adjust threshold as needed)
        assert execution_time < 1.0  # 1 second for 10 operations
        assert pool.stats["read_queries"] >= 10

    @pytest.mark.performance
    async def test_stats_tracking_performance(self, pool: ConnectionPool):
        """Test that stats tracking doesn't significantly impact performance."""
        import time\n        iterations = 50

        start_time = time.time()
        for i in range(iterations):
            async with pool.read_transaction() as conn:
                await conn.execute(text("SELECT 1"))
        execution_time = time.time() - start_time

        # Stats should be accurately tracked
        assert pool.stats["read_queries"] >= iterations

        # Performance should be reasonable
        avg_time_per_query = execution_time / iterations
        assert avg_time_per_query < 0.1  # Less than 100ms per query


@pytest.mark.unit
@pytest.mark.database
class TestDatabaseManager:
    """Test database manager functionality (legacy compatibility)."""

    @pytest_asyncio.fixture
    async def pool(self, temp_db_path: str):
        """Create connection pool for testing."""
        pool = ConnectionPool(db_path=temp_db_path, max_connections=2)
        await pool.initialize()
        yield pool
        await pool.close()

    async def test_manager_initialization(self, pool: ConnectionPool):
        """Test manager initializes correctly."""
        assert pool.engine is not None
        assert str(pool.db_path).endswith(".db")

    async def test_manager_properties(self, pool: ConnectionPool):
        """Test manager properties access."""
        assert pool.max_connections >= 1
        assert isinstance(pool.stats, dict)
        assert "connections_created" in pool.stats

    async def test_health_check_integration(self, pool: ConnectionPool):
        """Test health check functionality."""
        # Simple health check via engine
        async with pool.read_transaction() as conn:
            result = await conn.execute(text("SELECT 1 as health_check"))
            row = result.fetchone()
            assert row[0] == 1