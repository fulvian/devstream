#!/usr/bin/env python3
"""
Integration Tests for Phase 3 SessionEnd Implementation

Tests complete workflow from data extraction to summary storage.
Validates triple-source architecture and Context7 compliance.
"""

import pytest
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / '.claude/hooks/devstream/sessions'))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / '.claude/hooks/devstream/utils'))

from session_data_extractor import SessionDataExtractor, SessionData, MemoryStats, TaskStats
from session_summary_generator import SessionSummaryGenerator, SessionSummary
from work_session_manager import WorkSessionManager
from sqlite_vec_helper import get_db_connection_with_vec


@pytest.fixture
def db_path():
    """Database path fixture."""
    return str(Path(__file__).parent.parent.parent.parent / 'data' / 'devstream.db')


@pytest.fixture
async def test_session(db_path):
    """Create test session with data."""
    session_id = f"test-session-{datetime.now().timestamp()}"
    session_start = datetime.now() - timedelta(hours=1)

    # Create session
    conn = get_db_connection_with_vec(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO work_sessions (
            id, session_name, status, tokens_used,
            active_tasks, completed_tasks, started_at, last_activity_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        session_id,
        "Integration Test Session",
        "active",
        5000,
        json.dumps(["TASK-001"]),
        json.dumps(["TASK-002", "TASK-003"]),
        session_start.isoformat(),
        datetime.now().isoformat()
    ))

    # Add memory records
    for i in range(3):
        cursor.execute('''
            INSERT INTO semantic_memory (id, content, content_type, keywords, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            f"{session_id}-code-{i}",
            f"File Modified: test_{i}.py\n\nTest implementation {i}",
            "code",
            json.dumps([f"test{i}", "integration"]),
            (session_start + timedelta(minutes=10*i)).isoformat(),
            (session_start + timedelta(minutes=10*i)).isoformat()
        ))

    # Add decision
    cursor.execute('''
        INSERT INTO semantic_memory (id, content, content_type, keywords, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        f"{session_id}-decision",
        "Test architectural decision",
        "decision",
        json.dumps(["decision", "test"]),
        (session_start + timedelta(minutes=20)).isoformat(),
        (session_start + timedelta(minutes=20)).isoformat()
    ))

    conn.commit()
    conn.close()

    yield session_id

    # Cleanup
    conn = get_db_connection_with_vec(db_path)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM work_sessions WHERE id = ?', (session_id,))
    cursor.execute('DELETE FROM semantic_memory WHERE id LIKE ?', (f"{session_id}%",))
    conn.commit()
    conn.close()


@pytest.mark.asyncio
async def test_session_data_extraction(db_path, test_session):
    """Test SessionDataExtractor with real data."""
    extractor = SessionDataExtractor(db_path)

    # Extract session metadata
    session_data = await extractor.get_session_metadata(test_session)

    assert session_data is not None
    assert session_data.session_id == test_session
    assert session_data.session_name == "Integration Test Session"
    assert session_data.status == "active"
    assert session_data.tokens_used == 5000
    assert len(session_data.completed_tasks) == 2

    # Extract memory stats
    memory_stats = await extractor.get_memory_stats(
        session_data.started_at,
        datetime.now()
    )

    assert memory_stats.total_records >= 4  # 3 code + 1 decision
    assert memory_stats.files_modified >= 3
    assert memory_stats.decisions_made >= 1


@pytest.mark.asyncio
async def test_summary_generation(db_path, test_session):
    """Test SessionSummaryGenerator with real data."""
    extractor = SessionDataExtractor(db_path)
    generator = SessionSummaryGenerator()

    # Extract data
    session_data = await extractor.get_session_metadata(test_session)
    memory_stats = await extractor.get_memory_stats(
        session_data.started_at,
        datetime.now()
    )
    task_stats = await extractor.get_task_stats(
        session_data.started_at,
        datetime.now()
    )

    # Generate summary
    summary_md = generator.generate_summary(
        session_data,
        memory_stats,
        task_stats
    )

    # Validate markdown
    assert len(summary_md) > 0
    assert "# DevStream Session Summary" in summary_md
    assert "Integration Test Session" in summary_md
    assert "## 📊 Work Accomplished" in summary_md
    assert "## 🎯 Key Decisions" in summary_md
    assert "## 💡 Lessons Learned" in summary_md


@pytest.mark.asyncio
async def test_complete_workflow(db_path, test_session):
    """Test complete SessionEnd workflow."""
    extractor = SessionDataExtractor(db_path)
    generator = SessionSummaryGenerator()

    # Step 1: Extract all data
    session_data = await extractor.get_session_metadata(test_session)
    assert session_data is not None

    memory_stats = await extractor.get_memory_stats(
        session_data.started_at,
        datetime.now()
    )

    task_stats = await extractor.get_task_stats(
        session_data.started_at,
        datetime.now()
    )

    # Step 2: Aggregate
    summary = generator.aggregate_session_data(
        session_data,
        memory_stats,
        task_stats
    )

    # Step 3: Validate aggregation
    assert summary.session_id == test_session
    assert summary.duration_minutes > 0
    assert summary.files_modified >= 3
    assert summary.tokens_used == 5000

    # Step 4: Generate markdown
    markdown = summary.to_markdown()
    assert len(markdown) > 500  # Reasonable summary length

    # Step 5: Validate summary
    assert generator.validate_summary(summary)


@pytest.mark.asyncio
async def test_time_range_filtering(db_path, test_session):
    """Test time-range query filtering."""
    extractor = SessionDataExtractor(db_path)

    session_data = await extractor.get_session_metadata(test_session)

    # Test with narrow time range (should get fewer results)
    narrow_start = datetime.now() - timedelta(minutes=5)
    narrow_stats = await extractor.get_memory_stats(narrow_start, datetime.now())

    # Test with wide time range (should get more results)
    wide_start = datetime.now() - timedelta(hours=2)
    wide_stats = await extractor.get_memory_stats(wide_start, datetime.now())

    # Wide range should have >= narrow range
    assert wide_stats.total_records >= narrow_stats.total_records


@pytest.mark.asyncio
async def test_empty_session_handling(db_path):
    """Test handling of session with no data."""
    extractor = SessionDataExtractor(db_path)
    generator = SessionSummaryGenerator()

    # Create minimal session
    session_data = SessionData(
        session_id="empty-test",
        session_name="Empty Session",
        started_at=datetime.now() - timedelta(minutes=5),
        ended_at=datetime.now(),
        tokens_used=0,
        active_tasks=[],
        completed_tasks=[],
        status="active"
    )

    memory_stats = MemoryStats()
    task_stats = TaskStats()

    # Should handle gracefully
    summary = generator.aggregate_session_data(
        session_data,
        memory_stats,
        task_stats
    )

    assert summary.session_id == "empty-test"
    assert summary.tasks_completed == 0
    assert summary.files_modified == 0

    # Markdown should still be valid
    markdown = summary.to_markdown()
    assert "No tasks completed this session" in markdown
    assert "No files modified this session" in markdown


@pytest.mark.asyncio
async def test_work_session_manager_integration(db_path):
    """Test WorkSessionManager integration."""
    manager = WorkSessionManager(db_path)

    # Create session
    session_id = f"test-wsm-{datetime.now().timestamp()}"
    session = await manager.create_session(session_id, session_name="WSM Test")

    assert session.id == session_id
    assert session.status == "active"
    assert session.started_at is not None

    # End session
    success = await manager.end_session(session_id, context_summary="Test summary")
    assert success

    # Verify status updated
    updated = await manager.get_session(session_id)
    assert updated.status == "completed"
    assert updated.ended_at is not None

    # Cleanup
    conn = get_db_connection_with_vec(db_path)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM work_sessions WHERE id = ?', (session_id,))
    conn.commit()
    conn.close()


def test_summary_validation():
    """Test SessionSummary validation."""
    generator = SessionSummaryGenerator()

    # Valid summary
    valid = SessionSummary(
        session_id="test",
        session_name="Test",
        started_at=datetime.now() - timedelta(hours=1),
        ended_at=datetime.now(),
        duration_minutes=60,
        tasks_completed=5,
        tasks_active=2,
        files_modified=10,
        tokens_used=5000,
        completed_task_titles=["Task 1"],
        modified_files=["file.py"],
        key_decisions=["Decision"],
        lessons_learned=["Learning"],
        status="completed"
    )

    assert generator.validate_summary(valid)

    # Invalid: negative duration
    invalid = SessionSummary(
        session_id="test",
        session_name="Test",
        started_at=datetime.now(),
        ended_at=datetime.now() - timedelta(hours=1),  # End before start!
        duration_minutes=-60,
        tasks_completed=0,
        tasks_active=0,
        files_modified=0,
        tokens_used=0,
        completed_task_titles=[],
        modified_files=[],
        key_decisions=[],
        lessons_learned=[],
        status="active"
    )

    assert not generator.validate_summary(invalid)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])