"""Simplified unit tests for SessionTracker using AnyIO task groups."""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import pytest

# Add project root to path
import sys
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / ".claude"))

from hooks.devstream.sessions.session_tracker import (
    SessionTracker,
    SessionMetrics,
    TrackingException
)
from hooks.devstream.sessions.session_manager import SessionManager


@pytest.fixture
async def test_db(tmp_path: Path) -> str:
    """Create a test database with sessions table."""
    db_path = tmp_path / "test_tracker_simple.db"
    manager = SessionManager(str(db_path))
    await manager._ensure_tables()
    yield str(db_path)
    await manager.close()


@pytest.fixture
async def session_manager(test_db: str) -> SessionManager:
    """Get SessionManager instance for testing."""
    return await SessionManager.get_instance(test_db)


@pytest.fixture
async def session_tracker(session_manager: SessionManager) -> SessionTracker:
    """Get SessionTracker instance for testing."""
    tracker = SessionTracker(session_manager)
    yield tracker
    await tracker.shutdown()


@pytest.fixture
async def test_session(session_manager: SessionManager) -> str:
    """Create a test session."""
    session = await session_manager.create_session("test-session-tracker")
    return session.id


class TestSessionTrackerSimple:
    """Simplified tests for SessionTracker functionality."""

    @pytest.mark.asyncio
    async def test_tracker_initialization(self, session_tracker: SessionTracker) -> None:
        """Test SessionTracker initialization."""
        assert session_tracker.session_manager is not None
        assert len(session_tracker._active_trackers) == 0
        assert len(session_tracker._metrics_cache) == 0
        assert len(session_tracker._operation_times) == 0

    @pytest.mark.asyncio
    async def test_start_tracking(self, session_tracker: SessionTracker, test_session: str) -> None:
        """Test starting session tracking."""
        await session_tracker.start_tracking(test_session)

        assert test_session in session_tracker._active_trackers
        assert test_session in session_tracker._metrics_cache
        assert test_session in session_tracker._operation_times

        metrics = await session_tracker.get_metrics(test_session)
        assert metrics is not None
        assert metrics.session_id == test_session
        assert metrics.tokens_used == 0
        assert metrics.files_modified == 0
        assert metrics.tasks_completed == 0

        # Cleanup
        await session_tracker.stop_tracking(test_session)

    @pytest.mark.asyncio
    async def test_start_tracking_nonexistent_session(self, session_tracker: SessionTracker) -> None:
        """Test starting tracking for non-existent session raises exception."""
        with pytest.raises(TrackingException, match="not found"):
            await session_tracker.start_tracking("nonexistent-session")

    @pytest.mark.asyncio
    async def test_start_duplicate_tracking(self, session_tracker: SessionTracker, test_session: str) -> None:
        """Test starting duplicate tracking raises exception."""
        await session_tracker.start_tracking(test_session)

        with pytest.raises(TrackingException, match="Already tracking"):
            await session_tracker.start_tracking(test_session)

        # Cleanup
        await session_tracker.stop_tracking(test_session)

    @pytest.mark.asyncio
    async def test_stop_tracking(self, session_tracker: SessionTracker, test_session: str) -> None:
        """Test stopping session tracking."""
        await session_tracker.start_tracking(test_session)
        assert test_session in session_tracker._active_trackers

        await session_tracker.stop_tracking(test_session)
        assert test_session not in session_tracker._active_trackers
        assert test_session not in session_tracker._metrics_cache
        assert test_session not in session_tracker._operation_times

    @pytest.mark.asyncio
    async def test_stop_nonexistent_tracking(self, session_tracker: SessionTracker) -> None:
        """Test stopping non-existent tracking should not raise exception."""
        # Should not raise exception
        await session_tracker.stop_tracking("nonexistent-tracking")

    @pytest.mark.asyncio
    async def test_update_progress(self, session_tracker: SessionTracker, test_session: str) -> None:
        """Test updating session progress."""
        await session_tracker.start_tracking(test_session)

        # Update progress
        await session_tracker.update_progress(
            test_session,
            tokens_used=100,
            files_modified=5,
            tasks_completed=2
        )

        # Verify metrics updated
        metrics = await session_tracker.get_metrics(test_session)
        assert metrics.tokens_used == 100
        assert metrics.files_modified == 5
        assert metrics.tasks_completed == 2

        # Cleanup
        await session_tracker.stop_tracking(test_session)

    @pytest.mark.asyncio
    async def test_update_progress_untracked_session(self, session_tracker: SessionTracker) -> None:
        """Test updating progress for untracked session should not raise exception."""
        # Should not raise exception, just log warning
        await session_tracker.update_progress("untracked-session", tokens_used=50)

    @pytest.mark.asyncio
    async def test_get_metrics_nonexistent(self, session_tracker: SessionTracker) -> None:
        """Test getting metrics for non-existent session returns None."""
        metrics = await session_tracker.get_metrics("nonexistent")
        assert metrics is None

    @pytest.mark.asyncio
    async def test_get_all_metrics(self, session_tracker: SessionTracker, session_manager: SessionManager) -> None:
        """Test getting metrics for all tracked sessions."""
        # Create multiple sessions
        session1 = await session_manager.create_session("session-1")
        session2 = await session_manager.create_session("session-2")

        # Start tracking
        await session_tracker.start_tracking(session1.id)
        await session_tracker.start_tracking(session2.id)

        # Get all metrics
        all_metrics = await session_tracker.get_all_metrics()
        assert len(all_metrics) == 2
        session_ids = {m.session_id for m in all_metrics}
        assert session1.id in session_ids
        assert session2.id in session_ids

        # Cleanup
        await session_tracker.stop_tracking(session1.id)
        await session_tracker.stop_tracking(session2.id)

    @pytest.mark.asyncio
    async def test_cleanup_inactive_sessions(self, session_tracker: SessionTracker, session_manager: SessionManager) -> None:
        """Test cleaning up inactive sessions."""
        # Create session first
        session = await session_manager.create_session("inactive-session")
        session_id = session.id

        # Start tracking
        await session_tracker.start_tracking(session_id)

        # Manually set last activity to be old
        metrics = session_tracker._metrics_cache[session_id]
        metrics.last_activity = datetime.now() - timedelta(minutes=45)

        # Run cleanup with 30 minute threshold
        cleanup_count = await session_tracker.cleanup_inactive_sessions(max_inactive_minutes=30)

        assert cleanup_count == 1
        assert session_id not in session_tracker._active_trackers

    @pytest.mark.asyncio
    async def test_track_operation_context_manager(self, session_tracker: SessionTracker, test_session: str) -> None:
        """Test track_operation context manager."""
        await session_tracker.start_tracking(test_session)

        # Use context manager
        async with session_tracker.track_operation(test_session, "test_operation"):
            await asyncio.sleep(0.001)  # Very short delay

        # Verify operation time was tracked
        assert len(session_tracker._operation_times[test_session]) > 0

        # Cleanup
        await session_tracker.stop_tracking(test_session)

    @pytest.mark.asyncio
    async def test_track_operation_untracked_session(self, session_tracker: SessionTracker) -> None:
        """Test track_operation for untracked session should work but not track."""
        # Should not raise exception
        async with session_tracker.track_operation("untracked", "test_op"):
            await asyncio.sleep(0.001)

        # Should not have been tracked
        assert "untracked" not in session_tracker._operation_times

    @pytest.mark.asyncio
    async def test_shutdown(self, session_tracker: SessionTracker, session_manager: SessionManager) -> None:
        """Test tracker shutdown."""
        # Create and track multiple sessions
        sessions = []
        for i in range(2):  # Reduced number for faster test
            session = await session_manager.create_session(f"shutdown-session-{i}")
            sessions.append(session)
            await session_tracker.start_tracking(session.id)

        assert len(session_tracker._active_trackers) == 2

        # Shutdown tracker
        await session_tracker.shutdown()

        # Verify all tracking stopped
        assert len(session_tracker._active_trackers) == 0
        assert len(session_tracker._metrics_cache) == 0
        assert len(session_tracker._operation_times) == 0
        assert session_tracker._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_metrics_to_dict(self, session_tracker: SessionTracker, test_session: str) -> None:
        """Test SessionMetrics.to_dict method."""
        await session_tracker.start_tracking(test_session)

        metrics = await session_tracker.get_metrics(test_session)
        metrics_dict = metrics.to_dict()

        assert isinstance(metrics_dict, dict)
        assert metrics_dict["session_id"] == test_session
        assert "tokens_used" in metrics_dict
        assert "files_modified" in metrics_dict
        assert "tasks_completed" in metrics_dict
        assert "last_activity" in metrics_dict
        assert "operations_per_second" in metrics_dict
        assert "average_operation_time" in metrics_dict

        # Cleanup
        await session_tracker.stop_tracking(test_session)

    @pytest.mark.asyncio
    async def test_operation_time_tracking(self, session_tracker: SessionTracker, test_session: str) -> None:
        """Test operation time tracking and cleanup."""
        await session_tracker.start_tracking(test_session)

        # Track multiple operations
        for i in range(5):  # Reduced number for faster test
            async with session_tracker.track_operation(test_session, f"operation-{i}"):
                await asyncio.sleep(0.001)  # Very small delay

        # Verify operation times tracked
        operation_times = session_tracker._operation_times[test_session]
        assert len(operation_times) == 5

        # Cleanup
        await session_tracker.stop_tracking(test_session)

    @pytest.mark.asyncio
    async def test_completed_session_tracking(self, session_tracker: SessionTracker, session_manager: SessionManager) -> None:
        """Test that completed sessions cannot be tracked."""
        # Create and end session
        session = await session_manager.create_session("completed-session")
        await session_manager.end_session(session.id)

        # Try to start tracking
        with pytest.raises(TrackingException, match="not active"):
            await session_tracker.start_tracking(session.id)