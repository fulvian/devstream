"""Unit tests for SessionManager using aiosqlite patterns."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import pytest

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import directly from absolute path
sys.path.insert(0, str(project_root / ".claude"))

from hooks.devstream.sessions.session_manager import (
    SessionManager,
    Session,
    SessionException
)


@pytest.fixture
async def test_db(tmp_path: Path) -> str:
    """Create a test database with sessions table."""
    db_path = tmp_path / "test_session_manager.db"
    manager = SessionManager(str(db_path))
    await manager._ensure_tables()
    yield str(db_path)
    await manager.close()


@pytest.fixture
async def session_manager(test_db: str) -> SessionManager:
    """Get SessionManager instance for testing."""
    return await SessionManager.get_instance(test_db)


class TestSessionManager:
    """Test SessionManager functionality."""

    @pytest.mark.asyncio
    async def test_singleton_pattern(self, test_db: str) -> None:
        """Test that SessionManager follows singleton pattern."""
        manager1 = await SessionManager.get_instance(test_db)
        manager2 = await SessionManager.get_instance(test_db)

        assert manager1 is manager2, "SessionManager should be singleton for same db_path"
        assert manager1.db_path == test_db

    @pytest.mark.asyncio
    async def test_create_session(self, session_manager: SessionManager) -> None:
        """Test session creation."""
        session_id = "test-session-1"

        session = await session_manager.create_session(session_id)

        assert session is not None
        assert session.id == session_id
        assert session.status == "active"
        assert session.started_at is not None
        assert session.ended_at is None
        assert session.tokens_used == 0
        assert session.files_modified == 0
        assert session.tasks_completed == 0

    @pytest.mark.asyncio
    async def test_create_duplicate_session(self, session_manager: SessionManager) -> None:
        """Test creating duplicate session raises exception."""
        session_id = "test-session-duplicate"

        # Create first session
        await session_manager.create_session(session_id)

        # Try to create duplicate
        with pytest.raises(SessionException, match="already exists"):
            await session_manager.create_session(session_id)

    @pytest.mark.asyncio
    async def test_get_session(self, session_manager: SessionManager) -> None:
        """Test retrieving session by ID."""
        session_id = "test-session-get"

        # Create session
        created = await session_manager.create_session(session_id)

        # Retrieve session
        retrieved = await session_manager.get_session(session_id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.status == created.status
        assert retrieved.started_at == created.started_at

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, session_manager: SessionManager) -> None:
        """Test retrieving non-existent session returns None."""
        result = await session_manager.get_session("non-existent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_session_metrics(self, session_manager: SessionManager) -> None:
        """Test updating session metrics."""
        session_id = "test-session-update"

        # Create session
        await session_manager.create_session(session_id)

        # Update metrics
        success = await session_manager.update_session(
            session_id,
            tokens_used=100,
            files_modified=5,
            tasks_completed=2
        )
        assert success is True

        # Verify updates
        session = await session_manager.get_session(session_id)
        assert session.tokens_used == 100
        assert session.files_modified == 5
        assert session.tasks_completed == 2

    @pytest.mark.asyncio
    async def test_update_session_metadata(self, session_manager: SessionManager) -> None:
        """Test updating session metadata."""
        session_id = "test-session-metadata"

        # Create session
        await session_manager.create_session(session_id)

        # Update metadata
        metadata = {"user": "test", "project": "devstream"}
        success = await session_manager.update_session(
            session_id,
            metadata=metadata
        )
        assert success is True

        # Verify metadata
        session = await session_manager.get_session(session_id)
        assert session.metadata is not None
        stored_metadata = json.loads(session.metadata)
        assert stored_metadata == metadata

    @pytest.mark.asyncio
    async def test_update_invalid_fields(self, session_manager: SessionManager) -> None:
        """Test updating with invalid fields raises error."""
        session_id = "test-session-invalid"

        await session_manager.create_session(session_id)

        with pytest.raises(ValueError, match="Invalid fields"):
            await session_manager.update_session(
                session_id,
                invalid_field="value"
            )

    @pytest.mark.asyncio
    async def test_end_session(self, session_manager: SessionManager) -> None:
        """Test ending a session."""
        session_id = "test-session-end"

        # Create session
        await session_manager.create_session(session_id)

        # End session
        success = await session_manager.end_session(session_id)
        assert success is True

        # Verify session ended
        session = await session_manager.get_session(session_id)
        assert session.status == "completed"
        assert session.ended_at is not None

    @pytest.mark.asyncio
    async def test_end_nonexistent_session(self, session_manager: SessionManager) -> None:
        """Test ending non-existent session returns False."""
        success = await session_manager.end_session("non-existent")
        assert success is False

    @pytest.mark.asyncio
    async def test_end_already_completed_session(self, session_manager: SessionManager) -> None:
        """Test ending already completed session returns False."""
        session_id = "test-session-already-ended"

        # Create and end session
        await session_manager.create_session(session_id)
        await session_manager.end_session(session_id)

        # Try to end again
        success = await session_manager.end_session(session_id)
        assert success is False

    @pytest.mark.asyncio
    async def test_list_active_sessions(self, session_manager: SessionManager) -> None:
        """Test listing active sessions."""
        # Create multiple sessions
        session_ids = ["active-1", "active-2", "active-3"]
        for sid in session_ids:
            await session_manager.create_session(sid)

        # End one session
        await session_manager.end_session("active-2")

        # List active sessions
        active_sessions = await session_manager.list_active_sessions()
        active_ids = [s.id for s in active_sessions]

        assert len(active_sessions) == 2
        assert "active-1" in active_ids
        assert "active-3" in active_ids
        assert "active-2" not in active_ids

    @pytest.mark.asyncio
    async def test_cleanup_zombie_sessions(self, session_manager: SessionManager) -> None:
        """Test cleaning up zombie sessions."""
        # Create session
        session_id = "zombie-session"
        await session_manager.create_session(session_id)

        # Manually update started_at to simulate old session
        async with session_manager._get_connection() as db:
            await db.execute("""
                UPDATE sessions
                SET started_at = datetime('now', '-25 hours')
                WHERE id = ?
            """, (session_id,))
            await db.commit()

        # Cleanup zombie sessions (older than 24 hours)
        cleaned_count = await session_manager.cleanup_zombie_sessions(max_age_hours=24)
        assert cleaned_count == 1

        # Verify session was marked as completed
        session = await session_manager.get_session(session_id)
        assert session.status == "completed"
        assert session.ended_at is not None

    @pytest.mark.asyncio
    async def test_session_to_dict(self, session_manager: SessionManager) -> None:
        """Test Session.to_dict method."""
        session_id = "test-session-dict"
        metadata = {"test": "data"}

        # Create session with metadata
        await session_manager.create_session(session_id)
        await session_manager.update_session(session_id, metadata=metadata)

        session = await session_manager.get_session(session_id)
        session_dict = session.to_dict()

        assert isinstance(session_dict, dict)
        assert session_dict["id"] == session_id
        assert session_dict["status"] == "active"
        assert session_dict["metadata"] == json.dumps(metadata)
        assert "started_at" in session_dict

    @pytest.mark.asyncio
    async def test_database_error_handling(self, tmp_path: Path) -> None:
        """Test database error handling."""
        # Try to connect to invalid path
        invalid_path = "/nonexistent/path/test.db"

        with pytest.raises(SessionException, match="Failed to connect"):
            manager = SessionManager(invalid_path)
            async with manager._get_connection():
                pass

    @pytest.mark.asyncio
    async def test_empty_session_id_validation(self, session_manager: SessionManager) -> None:
        """Test validation of empty session ID."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await session_manager.create_session("")

        with pytest.raises(ValueError, match="cannot be empty"):
            await session_manager.create_session(None)

    @pytest.mark.asyncio
    async def test_concurrent_session_operations(self, session_manager: SessionManager) -> None:
        """Test concurrent session operations."""
        session_id = "concurrent-session"

        # Create session concurrently
        create_task = asyncio.create_task(session_manager.create_session(session_id))

        # Try to update concurrently (should wait for creation)
        update_task = asyncio.create_task(
            session_manager.update_session(session_id, tokens_used=50)
        )

        # Wait for both operations
        session = await create_task
        update_success = await update_task

        assert session.id == session_id
        assert update_success is True

        # Verify update applied
        updated_session = await session_manager.get_session(session_id)
        assert updated_session.tokens_used == 50

    @pytest.mark.asyncio
    async def test_connection_context_manager_cleanup(self, session_manager: SessionManager) -> None:
        """Test that database connections are properly cleaned up."""
        # This test verifies that the context manager pattern works
        # by ensuring we can perform multiple operations
        session_id = "cleanup-test"

        # Create session
        await session_manager.create_session(session_id)

        # Update session multiple times
        for i in range(3):
            await session_manager.update_session(session_id, tokens_used=i * 10)

        # Verify final state
        session = await session_manager.get_session(session_id)
        assert session.tokens_used == 20