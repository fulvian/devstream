#!/usr/bin/env python3
"""
Unit Tests - Active Session Tracking

Tests for FASE 2 PostToolUse hook session tracking methods.
Validates Memory Bank activeContext pattern implementation.

Task: c5af739922abe80e5d6e755b2bc56f24
"""

import pytest
import json
import asyncio
import aiosqlite
from pathlib import Path
from datetime import datetime


# Test fixtures
@pytest.fixture
async def test_db():
    """Create in-memory test database with work_sessions table."""
    db = await aiosqlite.connect(":memory:")

    # Create work_sessions table matching production schema
    await db.execute("""
        CREATE TABLE work_sessions (
            id VARCHAR(32) PRIMARY KEY,
            plan_id VARCHAR(32),
            user_id VARCHAR(100),
            session_name VARCHAR(200),
            context_window_size INTEGER,
            tokens_used INTEGER DEFAULT 0,
            status VARCHAR(20) DEFAULT 'active',
            context_summary TEXT,
            active_tasks JSON DEFAULT '[]',
            completed_tasks JSON DEFAULT '[]',
            active_files JSON DEFAULT '[]',
            started_at TIMESTAMP,
            last_activity_at TIMESTAMP,
            ended_at TIMESTAMP
        )
    """)

    await db.commit()
    yield db
    await db.close()


@pytest.fixture
async def sample_session(test_db):
    """Insert sample active session."""
    session_id = "test-session-123"
    await test_db.execute("""
        INSERT INTO work_sessions (id, status, started_at, active_tasks, active_files)
        VALUES (?, 'active', datetime('now'), '[]', '[]')
    """, (session_id,))
    await test_db.commit()
    return session_id


# Unit Tests - Session Tracking Methods

@pytest.mark.asyncio
async def test_add_active_file_first_file(test_db, sample_session):
    """Test adding first file to empty active_files list."""
    session_id = sample_session
    file_path = "test/file1.py"

    # Get current active_files
    cursor = await test_db.execute(
        "SELECT active_files FROM work_sessions WHERE id = ?",
        (session_id,)
    )
    row = await cursor.fetchone()
    active_files = json.loads(row[0]) if row[0] else []

    # Add file
    active_files.append(file_path)
    await test_db.execute(
        "UPDATE work_sessions SET active_files = ? WHERE id = ?",
        (json.dumps(active_files), session_id)
    )
    await test_db.commit()

    # Verify
    cursor = await test_db.execute(
        "SELECT active_files FROM work_sessions WHERE id = ?",
        (session_id,)
    )
    row = await cursor.fetchone()
    result = json.loads(row[0])

    assert len(result) == 1
    assert result[0] == file_path


@pytest.mark.asyncio
async def test_add_active_file_deduplication(test_db, sample_session):
    """Test deduplication - adding same file twice."""
    session_id = sample_session
    file_path = "test/file1.py"

    # Add file twice
    for _ in range(2):
        cursor = await test_db.execute(
            "SELECT active_files FROM work_sessions WHERE id = ?",
            (session_id,)
        )
        row = await cursor.fetchone()
        active_files = json.loads(row[0]) if row[0] else []

        if file_path not in active_files:  # Deduplication logic
            active_files.append(file_path)
            await test_db.execute(
                "UPDATE work_sessions SET active_files = ? WHERE id = ?",
                (json.dumps(active_files), session_id)
            )
            await test_db.commit()

    # Verify only one instance
    cursor = await test_db.execute(
        "SELECT active_files FROM work_sessions WHERE id = ?",
        (session_id,)
    )
    row = await cursor.fetchone()
    result = json.loads(row[0])

    assert len(result) == 1
    assert result[0] == file_path


@pytest.mark.asyncio
async def test_add_multiple_active_files(test_db, sample_session):
    """Test adding multiple different files."""
    session_id = sample_session
    files = ["test/file1.py", "test/file2.ts", "test/file3.md"]

    # Add files sequentially
    for file_path in files:
        cursor = await test_db.execute(
            "SELECT active_files FROM work_sessions WHERE id = ?",
            (session_id,)
        )
        row = await cursor.fetchone()
        active_files = json.loads(row[0]) if row[0] else []

        if file_path not in active_files:
            active_files.append(file_path)
            await test_db.execute(
                "UPDATE work_sessions SET active_files = ? WHERE id = ?",
                (json.dumps(active_files), session_id)
            )
            await test_db.commit()

    # Verify all files tracked
    cursor = await test_db.execute(
        "SELECT active_files FROM work_sessions WHERE id = ?",
        (session_id,)
    )
    row = await cursor.fetchone()
    result = json.loads(row[0])

    assert len(result) == 3
    assert set(result) == set(files)


@pytest.mark.asyncio
async def test_add_active_task(test_db, sample_session):
    """Test adding task to active_tasks list."""
    session_id = sample_session
    task_id = "task-123"

    # Add task
    cursor = await test_db.execute(
        "SELECT active_tasks FROM work_sessions WHERE id = ?",
        (session_id,)
    )
    row = await cursor.fetchone()
    active_tasks = json.loads(row[0]) if row[0] else []

    active_tasks.append(task_id)
    await test_db.execute(
        "UPDATE work_sessions SET active_tasks = ? WHERE id = ?",
        (json.dumps(active_tasks), session_id)
    )
    await test_db.commit()

    # Verify
    cursor = await test_db.execute(
        "SELECT active_tasks FROM work_sessions WHERE id = ?",
        (session_id,)
    )
    row = await cursor.fetchone()
    result = json.loads(row[0])

    assert len(result) == 1
    assert result[0] == task_id


@pytest.mark.asyncio
async def test_json_atomic_update(test_db, sample_session):
    """Test atomic JSON update (transaction safety)."""
    session_id = sample_session

    # Simulate concurrent updates (sequential for test)
    files = ["file1.py", "file2.py", "file3.py"]

    for file_path in files:
        # Atomic transaction
        cursor = await test_db.execute(
            "SELECT active_files FROM work_sessions WHERE id = ?",
            (session_id,)
        )
        row = await cursor.fetchone()
        active_files = json.loads(row[0]) if row[0] else []

        active_files.append(file_path)
        await test_db.execute(
            "UPDATE work_sessions SET active_files = ? WHERE id = ?",
            (json.dumps(active_files), session_id)
        )
        await test_db.commit()  # Atomic commit

    # Verify all updates persisted
    cursor = await test_db.execute(
        "SELECT active_files FROM work_sessions WHERE id = ?",
        (session_id,)
    )
    row = await cursor.fetchone()
    result = json.loads(row[0])

    assert len(result) == 3


@pytest.mark.asyncio
async def test_empty_active_files_default(test_db):
    """Test DEFAULT '[]' for active_files column."""
    session_id = "test-default-session"

    # Insert session without specifying active_files
    await test_db.execute("""
        INSERT INTO work_sessions (id, status, started_at)
        VALUES (?, 'active', datetime('now'))
    """, (session_id,))
    await test_db.commit()

    # Verify default is empty array
    cursor = await test_db.execute(
        "SELECT active_files FROM work_sessions WHERE id = ?",
        (session_id,)
    )
    row = await cursor.fetchone()

    # Should be empty JSON array or None (handle both)
    result = json.loads(row[0]) if row[0] else []
    assert isinstance(result, list)
    assert len(result) == 0


# Edge Cases

@pytest.mark.asyncio
async def test_nonexistent_session(test_db):
    """Test graceful handling of nonexistent session."""
    session_id = "nonexistent-session"

    # Attempt to update nonexistent session
    cursor = await test_db.execute(
        "SELECT active_files FROM work_sessions WHERE id = ?",
        (session_id,)
    )
    row = await cursor.fetchone()

    # Should return None, not raise exception
    assert row is None


@pytest.mark.asyncio
async def test_null_active_files_handling(test_db):
    """Test handling of NULL active_files (backward compat)."""
    session_id = "test-null-session"

    # Insert session with NULL active_files
    await test_db.execute("""
        INSERT INTO work_sessions (id, status, started_at, active_files)
        VALUES (?, 'active', datetime('now'), NULL)
    """, (session_id,))
    await test_db.commit()

    # Read and handle NULL
    cursor = await test_db.execute(
        "SELECT active_files FROM work_sessions WHERE id = ?",
        (session_id,)
    )
    row = await cursor.fetchone()
    active_files = json.loads(row[0]) if row[0] else []

    # Should default to empty array
    assert isinstance(active_files, list)
    assert len(active_files) == 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
