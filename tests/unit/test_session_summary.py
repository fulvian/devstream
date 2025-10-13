"""Unit tests for SessionSummary generator with structlog context."""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import pytest
import json

# Add project root to path
import sys
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / ".claude"))

from hooks.devstream.sessions.session_summary import (
    SessionSummary,
    SummaryException
)
from hooks.devstream.sessions.session_manager import SessionManager


@pytest.fixture
async def test_db(tmp_path: Path) -> str:
    """Create a test database with sessions table."""
    db_path = tmp_path / "test_session_summary.db"
    manager = SessionManager(str(db_path))
    await manager._ensure_tables()
    yield str(db_path)
    await manager.close()


@pytest.fixture
async def session_manager(test_db: str) -> SessionManager:
    """Get SessionManager instance for testing."""
    return await SessionManager.get_instance(test_db)


@pytest.fixture
async def session_summary(session_manager: SessionManager) -> SessionSummary:
    """Get SessionSummary instance for testing."""
    return SessionSummary(session_manager)


@pytest.fixture
async def test_session(session_manager: SessionManager) -> str:
    """Create a test session."""
    session = await session_manager.create_session("test-session-summary")
    return session.id


@pytest.fixture
async def completed_session(session_manager: SessionManager) -> str:
    """Create a completed test session."""
    session = await session_manager.create_session("completed-session-summary")
    # Add some data
    await session_manager.update_session(
        session.id,
        tokens_used=500,
        files_modified=10,
        tasks_completed=3,
        metadata='{"test": "data", "project": "devstream"}'
    )
    await session_manager.end_session(session.id)
    return session.id


class TestSessionSummary:
    """Test SessionSummary functionality."""

    @pytest.mark.asyncio
    async def test_summary_initialization(self, session_summary: SessionSummary) -> None:
        """Test SessionSummary initialization."""
        assert session_summary.session_manager is not None
        assert session_summary._logger is not None

    @pytest.mark.asyncio
    async def test_generate_summary_active_session(
        self, session_summary: SessionSummary, test_session: str
    ) -> None:
        """Test generating summary for active session."""
        # Add some data
        await session_summary.session_manager.update_session(
            test_session,
            tokens_used=100,
            files_modified=3,
            tasks_completed=1
        )

        summary = await session_summary.generate_summary(test_session)

        # Verify summary contains expected sections
        assert summary is not None
        assert len(summary) > 100  # Should be substantial
        assert "Session Summary:" in summary
        assert test_session in summary
        assert "**Status:**" in summary
        assert "### Performance Metrics" in summary
        assert "### Usage Statistics" in summary
        assert "100 tokens" in summary

    @pytest.mark.asyncio
    async def test_generate_summary_completed_session(
        self, session_summary: SessionSummary, completed_session: str
    ) -> None:
        """Test generating summary for completed session."""
        summary = await session_summary.generate_summary(completed_session)

        # Verify summary contains completed status
        assert "✅ Session Summary:" in summary
        assert "**Status:** Completed" in summary
        assert "500 tokens" in summary
        assert "10 files" in summary
        assert "3 tasks" in summary

        # Should contain completion timestamp
        assert "Session completed successfully" in summary

    @pytest.mark.asyncio
    async def test_generate_summary_nonexistent_session(self, session_summary: SessionSummary) -> None:
        """Test generating summary for non-existent session raises exception."""
        with pytest.raises(SummaryException, match="not found"):
            await session_summary.generate_summary("nonexistent-session")

    @pytest.mark.asyncio
    async def test_context_binding(
        self, session_summary: SessionSummary, test_session: str
    ) -> None:
        """Test session context binding."""
        # Test binding context
        session_summary.bind_session_context(test_session)

        # Should not raise exception
        # Context binding is internal - we verify it works by generating summary
        summary = await session_summary.generate_summary(test_session)
        assert summary is not None

        # Clear context
        session_summary._clear_session_context()

    @pytest.mark.asyncio
    async def test_duration_calculation(
        self, session_summary: SessionSummary, session_manager: SessionManager
    ) -> None:
        """Test duration calculation."""
        # Create session with known start time
        session = await session_manager.create_session("duration-test")
        # Manually set started_at to a known time
        await session_manager._ensure_tables()
        async with session_manager._get_connection() as db:
            await db.execute(
                "UPDATE sessions SET started_at = ? WHERE id = ?",
                (datetime.now() - timedelta(minutes=5), session.id)
            )
            await db.commit()

        # Update some data
        await session_manager.update_session(session.id, tokens_used=50)

        # Generate summary
        summary_generator = SessionSummary(session_manager)
        summary = await summary_generator.generate_summary(session.id)

        # Should contain duration (approximately 5 minutes)
        assert "5m" in summary or "4m" in summary or "6m" in summary

    @pytest.mark.asyncio
    async def test_performance_rating(
        self, session_summary: SessionSummary, session_manager: SessionManager
    ) -> None:
        """Test performance rating calculation."""
        # Create high-performance session
        session = await session_manager.create_session("performance-test")
        await session_manager.update_session(
            session.id,
            tokens_used=200,
            files_modified=8,
            tasks_completed=5
        )
        # Short duration for higher rating
        async with session_manager._get_connection() as db:
            await db.execute(
                "UPDATE sessions SET started_at = ? WHERE id = ?",
                (datetime.now() - timedelta(minutes=2), session.id)
            )
            await db.commit()

        summary_generator = SessionSummary(session_manager)
        summary = await summary_generator.generate_summary(session.id)

        # Should have good performance rating
        assert "Performance Rating:" in summary
        assert "⭐" in summary or "🏆" in summary

    @pytest.mark.asyncio
    async def test_insights_generation(
        self, session_summary: SessionSummary, session_manager: SessionManager
    ) -> None:
        """Test insights generation."""
        # Create session with various metrics
        session = await session_manager.create_session("insights-test")
        await session_manager.update_session(
            session.id,
            tokens_used=3000,
            files_modified=2,
            tasks_completed=0,
            metadata='{"complex": "data"}'
        )

        summary = await session_summary.generate_summary(session.id)

        # Should contain insights
        assert "### Insights" in summary
        assert "File modifications without task completions" in summary

    @pytest.mark.asyncio
    async def test_metadata_handling(
        self, session_summary: SessionSummary, session_manager: SessionManager
    ) -> None:
        """Test metadata handling in summary."""
        # Create session with JSON metadata
        session = await session_manager.create_session("metadata-test")
        metadata = {"user": "test", "project": "devstream", "features": ["session_tracking", "aiosqlite"]}
        await session_manager.update_session(
            session.id,
            metadata=json.dumps(metadata)
        )

        summary = await session_summary.generate_summary(session.id)

        # Should contain formatted metadata
        assert "### Session Metadata" in summary
        assert '"user": "test"' in summary
        assert '"project": "devstream"' in summary

    @pytest.mark.asyncio
    async def test_invalid_metadata_handling(
        self, session_summary: SessionSummary, session_manager: SessionManager
    ) -> None:
        """Test handling of invalid JSON metadata."""
        # Create session with invalid JSON metadata
        session = await session_manager.create_session("invalid-metadata-test")
        await session_manager.update_session(
            session.id,
            metadata='{"invalid": json'  # Invalid JSON
        )

        summary = await session_summary.generate_summary(session.id)

        # Should handle gracefully
        assert "### Session Metadata" in summary
        assert "Raw Metadata:" in summary

    @pytest.mark.asyncio
    async def test_store_summary_in_memory(
        self, session_summary: SessionSummary, test_session: str
    ) -> None:
        """Test storing summary in memory (placeholder for MCP integration)."""
        # Generate summary
        summary = await session_summary.generate_summary(test_session)

        # Store in memory
        success = await session_summary.store_summary_in_memory(test_session, summary)

        # Should succeed (placeholder implementation)
        assert success is True

    @pytest.mark.asyncio
    async def test_get_multiple_summaries(
        self, session_summary: SessionSummary, session_manager: SessionManager
    ) -> None:
        """Test getting summaries for multiple sessions."""
        # Create multiple sessions
        sessions = []
        for i in range(3):
            session = await session_manager.create_session(f"multi-summary-{i}")
            await session_manager.update_session(
                session.id,
                tokens_used=(i + 1) * 100,
                files_modified=(i + 1) * 2,
                tasks_completed=i + 1
            )
            sessions.append(session)

        # Get all summaries
        session_ids = [s.id for s in sessions]
        summaries = await session_summary.get_session_summaries(session_ids)

        # Verify all summaries generated
        assert len(summaries) == 3
        for session_id in session_ids:
            assert session_id in summaries
            assert summaries[session_id] is not None
            assert len(summaries[session_id]) > 100

    @pytest.mark.asyncio
    async def test_summary_structure_validation(
        self, session_summary: SessionSummary, completed_session: str
    ) -> None:
        """Test summary structure and required sections."""
        summary = await session_summary.generate_summary(completed_session)

        # Check for required sections
        required_sections = [
            "Session Summary:",
            "**Status:**",
            "### Activity Timeline",
            "### Performance Metrics",
            "### Key Events",
            "### Usage Statistics",
            "---",
            "Summary generated on"
        ]

        for section in required_sections:
            assert section in summary, f"Missing required section: {section}"

    @pytest.mark.asyncio
    async def test_emoji_ratings(
        self, session_summary: SessionSummary, session_manager: SessionManager
    ) -> None:
        """Test emoji ratings in summaries."""
        # Create session with good performance
        session = await session_manager.create_session("emoji-test")
        await session_manager.update_session(
            session.id,
            tokens_used=100,
            files_modified=5,
            tasks_completed=3
        )

        summary = await session_summary.generate_summary(session.id)

        # Should contain performance rating with emoji
        assert "Performance Rating:" in summary

        # Check for rating emoji
        has_rating_emoji = any(emoji in summary for emoji in ["🏆", "⭐", "✓", "⚠️", "❌"])
        assert has_rating_emoji, "Missing rating emoji"

    @pytest.mark.asyncio
    async def test_context_binding_isolation(
        self, session_summary: SessionSummary, session_manager: SessionManager
    ) -> None:
        """Test that context binding doesn't interfere between sessions."""
        # Create two sessions
        session1 = await session_manager.create_session("context-test-1")
        session2 = await session_manager.create_session("context-test-2")

        # Bind context for first session
        session_summary.bind_session_context(session1.id)
        summary1 = await session_summary.generate_summary(session1.id)
        session_summary._clear_session_context()

        # Bind context for second session
        session_summary.bind_session_context(session2.id)
        summary2 = await session_summary.generate_summary(session2.id)
        session_summary._clear_session_context()

        # Both summaries should be generated successfully
        assert summary1 is not None
        assert summary2 is not None
        assert session1.id in summary1
        assert session2.id in summary2