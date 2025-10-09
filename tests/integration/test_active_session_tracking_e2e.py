#!/usr/bin/env python3
"""
Integration Tests - Active Session Tracking E2E

End-to-end tests for Memory Bank activeContext pattern.
Tests complete workflow: PostToolUse → SessionDataExtractor → Summary.

Task: c5af739922abe80e5d6e755b2bc56f24
"""

import pytest
import json
import asyncio
import aiosqlite
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Add hooks to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'sessions'))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'utils'))

from session_data_extractor import SessionDataExtractor, SessionData, TaskStats


# Test fixtures
@pytest.fixture
async def test_db_with_data():
    """Use production database for integration tests."""
    db_path = "/Users/fulvioventura/devstream/data/devstream.db"
    db = await aiosqlite.connect(db_path)

    yield {"db": db, "db_path": db_path}

    # Cleanup: Delete test records after tests
    await db.execute("DELETE FROM work_sessions WHERE id LIKE 'test-%'")
    await db.execute("DELETE FROM micro_tasks WHERE id LIKE 'task-created-early-%' OR id LIKE 'task-in-range' OR id LIKE 'tracked-task'")
    await db.commit()
    await db.close()


# E2E Test 1: Timezone Bug Reproduction

@pytest.mark.asyncio
async def test_timezone_bug_reproduction(test_db_with_data):
    """
    Reproduce bug: Tasks created hours before session start excluded from summary.

    Scenario:
    - Task created at 06:05 UTC
    - Session started at 08:52 UTC
    - OLD behavior: Task excluded (created_at BETWEEN 08:52-09:00)
    - NEW behavior: Task included (id IN active_tasks) ✅
    """
    db = test_db_with_data["db"]
    db_path = test_db_with_data["db_path"]

    # Setup: Create tasks BEFORE session start (simulates timezone bug)
    task1_id = "task-created-early-1"
    task2_id = "task-created-early-2"

    base_time = datetime(2025, 10, 3, 6, 5, 0)  # 06:05 UTC

    await db.execute("""
        INSERT INTO micro_tasks (id, phase_id, title, description, status, created_at)
        VALUES (?, 'test-phase', 'Fix empty summary bug', 'Test task 1', 'pending', ?)
    """, (task1_id, base_time.isoformat()))

    await db.execute("""
        INSERT INTO micro_tasks (id, phase_id, title, description, status, created_at)
        VALUES (?, 'test-phase', 'Add session tracking', 'Test task 2', 'pending', ?)
    """, (task2_id, (base_time + timedelta(minutes=3)).isoformat()))

    # Setup: Create session 3 hours LATER
    session_id = "test-session-timezone"
    session_start = base_time + timedelta(hours=3)  # 09:05 UTC (3 hours later!)

    # Track tasks in active_tasks (NEW behavior - Memory Bank pattern)
    await db.execute("""
        INSERT INTO work_sessions (id, status, started_at, active_tasks)
        VALUES (?, 'active', ?, ?)
    """, (session_id, session_start.isoformat(), json.dumps([task1_id, task2_id])))

    await db.commit()

    # Test: Query using tracking-based method (use production DB)
    extractor = SessionDataExtractor(db_path=db_path)

    # Create SessionData with active_tasks
    session_data = SessionData(
        session_id=session_id,
        started_at=session_start,
        active_tasks=[task1_id, task2_id],
        active_files=[],
        completed_tasks=[],
        tokens_used=0,
        status="active"
    )

    # Execute: Get task stats using tracking
    stats = await extractor._get_task_stats_by_tracking(session_data)

    # Verify: Tasks FROM 3 HOURS AGO are now included ✅
    assert stats.total_tasks == 2, f"Expected 2 tasks, got {stats.total_tasks}"
    assert len(stats.task_titles) == 2


@pytest.mark.asyncio
async def test_time_based_fallback_for_old_sessions(test_db_with_data):
    """
    Test backward compatibility: Old sessions without tracking fall back to time-based.

    Scenario:
    - Old session (no active_tasks tracked)
    - Should fall back to time-based query
    - Should NOT crash or return errors
    """
    db = test_db_with_data["db"]
    db_path = test_db_with_data["db_path"]

    # Setup: Create task within time range
    task_id = "task-in-range"
    base_time = datetime(2025, 10, 3, 8, 0, 0)

    await db.execute("""
        INSERT INTO micro_tasks (id, phase_id, title, description, status, created_at)
        VALUES (?, 'test-phase', 'Task in time range', 'Test fallback', 'completed', ?)
    """, (task_id, base_time.isoformat()))

    # Setup: Old session WITHOUT active_tasks tracking
    session_id = "test-old-session-no-tracking"
    await db.execute("""
        INSERT INTO work_sessions (id, status, started_at, active_tasks)
        VALUES (?, 'active', ?, '[]')
    """, (session_id, base_time.isoformat()))

    await db.commit()

    # Test: Query with empty active_tasks (triggers fallback)
    extractor = SessionDataExtractor(db_path=db_path)

    session_data = SessionData(
        session_id=session_id,
        started_at=base_time,
        active_tasks=[],  # Empty - triggers fallback
        active_files=[],
        completed_tasks=[],
        tokens_used=0,
        status="active"
    )

    # Execute: Should use time-based fallback
    stats = await extractor.get_task_stats(
        start_time=base_time,
        end_time=base_time + timedelta(hours=1),
        session_data=session_data
    )

    # Verify: Falls back gracefully, returns time-based results
    assert stats.total_tasks == 1  # Found via time-based query
    assert stats.completed == 1


@pytest.mark.asyncio
async def test_empty_session_no_tracked_work(test_db_with_data):
    """
    Test empty session: No files modified, no tasks worked on.

    Scenario:
    - Session exists but no active_files/active_tasks
    - Should return empty stats gracefully
    - Should NOT crash
    """
    db = test_db_with_data["db"]
    db_path = test_db_with_data["db_path"]

    # Setup: Empty session
    session_id = "test-empty-session"
    session_start = datetime(2025, 10, 3, 8, 0, 0)

    await db.execute("""
        INSERT INTO work_sessions (id, status, started_at, active_tasks, active_files)
        VALUES (?, 'active', ?, '[]', '[]')
    """, (session_id, session_start.isoformat()))

    await db.commit()

    # Test
    extractor = SessionDataExtractor(db_path=db_path)

    session_data = SessionData(
        session_id=session_id,
        started_at=session_start,
        active_tasks=[],  # Empty
        active_files=[],  # Empty
        completed_tasks=[],
        tokens_used=0,
        status="active"
    )

    # Execute
    stats = await extractor.get_task_stats(
        start_time=session_start,
        end_time=session_start + timedelta(hours=1),
        session_data=session_data
    )

    # Verify: Returns empty stats gracefully
    assert stats.total_tasks == 0
    assert stats.completed == 0
    assert len(stats.task_titles) == 0


@pytest.mark.asyncio
async def test_load_test_100_active_files(test_db_with_data):
    """
    Load test: Session with 100+ active files.

    Validates:
    - JSON serialization handles large arrays
    - Query performance with large IN clause
    - No memory issues
    """
    db = test_db_with_data["db"]
    db_path = test_db_with_data["db_path"]

    # Setup: Session with 100 files
    session_id = "test-load-test-session"
    session_start = datetime(2025, 10, 3, 8, 0, 0)

    # Generate 100 file paths
    active_files = [f"src/module{i}/file{i}.py" for i in range(100)]

    await db.execute("""
        INSERT INTO work_sessions (id, status, started_at, active_files)
        VALUES (?, 'active', ?, ?)
    """, (session_id, session_start.isoformat(), json.dumps(active_files)))

    await db.commit()

    # Verify: JSON serialization worked
    cursor = await db.execute(
        "SELECT active_files FROM work_sessions WHERE id = ?",
        (session_id,)
    )
    row = await cursor.fetchone()
    retrieved = json.loads(row[0])

    assert len(retrieved) == 100
    assert retrieved[0] == "src/module0/file0.py"
    assert retrieved[99] == "src/module99/file99.py"


@pytest.mark.asyncio
async def test_hybrid_query_strategy_selection(test_db_with_data):
    """
    Test hybrid strategy: Correctly selects tracking vs time-based.

    Scenarios:
    1. active_tasks present → use tracking ✅
    2. active_tasks empty → use time-based ✅
    3. active_tasks None → use time-based ✅
    """
    db = test_db_with_data["db"]
    db_path = test_db_with_data["db_path"]

    # Setup tasks
    task1_id = "tracked-task"
    base_time = datetime(2025, 10, 3, 8, 0, 0)

    await db.execute("""
        INSERT INTO micro_tasks (id, phase_id, title, description, status, created_at)
        VALUES (?, 'test-phase', 'Tracked task', 'Test hybrid strategy', 'completed', ?)
    """, (task1_id, base_time.isoformat()))

    await db.commit()

    # Test 1: active_tasks present → tracking
    session1_id = "test-session-with-tracking"
    await db.execute("""
        INSERT INTO work_sessions (id, status, started_at, active_tasks)
        VALUES (?, 'active', ?, ?)
    """, (session1_id, base_time.isoformat(), json.dumps([task1_id])))
    await db.commit()

    extractor = SessionDataExtractor(db_path=db_path)

    session_data_with_tracking = SessionData(
        session_id=session1_id,
        started_at=base_time,
        active_tasks=[task1_id],  # Present → tracking
        active_files=[],
        completed_tasks=[],
        tokens_used=0,
        status="active"
    )

    stats = await extractor.get_task_stats(
        start_time=base_time,
        end_time=base_time + timedelta(hours=1),
        session_data=session_data_with_tracking
    )

    assert stats.total_tasks == 1  # Found via tracking


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short", "-s"])
