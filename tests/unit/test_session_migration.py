"""Unit tests for session migration to simplified schema."""

import sqlite3
import pytest
from typing import Optional


@pytest.fixture
def test_db(tmp_path):
    """Create a test database with the new sessions schema."""
    db_path = tmp_path / "test_sessions.db"
    conn = sqlite3.connect(str(db_path))

    # Create the new simplified sessions table
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP NULL,
            status TEXT NOT NULL CHECK (status IN ('active', 'completed')),
            tokens_used INTEGER DEFAULT 0,
            files_modified INTEGER DEFAULT 0,
            tasks_completed INTEGER DEFAULT 0,
            metadata TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
        CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at DESC);
    """)

    conn.commit()
    yield str(db_path)
    conn.close()


class TestSimplifiedSessionsSchema:
    """Test the simplified sessions table schema."""

    def test_sessions_table_exists(self, test_db: str) -> None:
        """Test that sessions table exists with correct structure."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Check table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        )
        result = cursor.fetchone()
        assert result is not None, "Sessions table should exist"

        # Check table schema
        cursor.execute("PRAGMA table_info(sessions)")
        columns = {row[1] for row in cursor.fetchall()}
        expected_columns = {
            'id', 'started_at', 'ended_at', 'status',
            'tokens_used', 'files_modified', 'tasks_completed', 'metadata'
        }
        assert columns == expected_columns, f"Expected {expected_columns}, got {columns}"

        conn.close()

    def test_sessions_indexes_exist(self, test_db: str) -> None:
        """Test that required indexes are created."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Check indexes exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='sessions'"
        )
        indexes = {row[0] for row in cursor.fetchall()}
        expected_indexes = {
            'idx_sessions_status', 'idx_sessions_started_at'
        }
        assert expected_indexes.issubset(indexes), f"Missing indexes: {expected_indexes - indexes}"

        conn.close()

    def test_sessions_constraints(self, test_db: str) -> None:
        """Test that sessions table constraints work correctly."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Test valid insertion
        cursor.execute("""
            INSERT INTO sessions (id, status, tokens_used, files_modified, tasks_completed)
            VALUES ('test-session-1', 'active', 100, 5, 2)
        """)
        conn.commit()

        # Test status constraint
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO sessions (id, status)
                VALUES ('test-session-2', 'invalid_status')
            """)
            conn.commit()

        conn.close()

    def test_sessions_crud_operations(self, test_db: str) -> None:
        """Test basic CRUD operations on sessions table."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Create
        cursor.execute("""
            INSERT INTO sessions (id, status, tokens_used, files_modified, tasks_completed, metadata)
            VALUES ('test-session-3', 'active', 150, 8, 3, '{"test": "data"}')
        """)
        conn.commit()

        # Read
        cursor.execute("SELECT * FROM sessions WHERE id = 'test-session-3'")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 'test-session-3'  # id
        assert row[3] == 'active'  # status
        assert row[4] == 150  # tokens_used
        assert row[5] == 8  # files_modified
        assert row[6] == 3  # tasks_completed
        assert row[7] == '{"test": "data"}'  # metadata

        # Update
        cursor.execute("""
            UPDATE sessions
            SET status = 'completed', tokens_used = 200, ended_at = CURRENT_TIMESTAMP
            WHERE id = 'test-session-3'
        """)
        conn.commit()

        cursor.execute("SELECT status, tokens_used FROM sessions WHERE id = 'test-session-3'")
        updated = cursor.fetchone()
        assert updated[0] == 'completed'
        assert updated[1] == 200

        # Delete
        cursor.execute("DELETE FROM sessions WHERE id = 'test-session-3'")
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM sessions WHERE id = 'test-session-3'")
        count = cursor.fetchone()[0]
        assert count == 0

        conn.close()

    def test_sessions_performance_indexes(self, test_db: str) -> None:
        """Test that indexes improve query performance."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Insert test data
        test_sessions = [
            (f'session-{i}', 'active' if i % 2 == 0 else 'completed', i * 10)
            for i in range(100)
        ]

        cursor.executemany("""
            INSERT INTO sessions (id, status, tokens_used)
            VALUES (?, ?, ?)
        """, test_sessions)
        conn.commit()

        # Test index usage with EXPLAIN QUERY PLAN
        cursor.execute("EXPLAIN QUERY PLAN SELECT * FROM sessions WHERE status = 'active'")
        plan = cursor.fetchall()
        assert any('idx_sessions_status' in str(p) for p in plan), "Status index should be used"

        cursor.execute("EXPLAIN QUERY PLAN SELECT * FROM sessions ORDER BY started_at DESC")
        plan = cursor.fetchall()
        assert any('idx_sessions_started_at' in str(p) for p in plan), "Started_at index should be used"

        conn.close()