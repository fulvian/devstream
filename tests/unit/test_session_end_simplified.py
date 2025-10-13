"""
Tests for simplified SessionEnd hook implementation.

Validates session termination, summary generation, and cleanup functionality.
"""

import asyncio
import json
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys

# Add hooks path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / ".claude"))

from hooks.devstream.sessions.session_manager import SessionManager, Session
from hooks.devstream.sessions.session_tracker import SessionTracker
from hooks.devstream.sessions.session_summary import SessionSummary
from hooks.devstream.sessions.session_end_simplified import SimplifiedSessionEndHook


@pytest.fixture
async def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    # Initialize SessionManager to create tables
    sm = await SessionManager.get_instance(db_path)
    yield db_path

    # Cleanup
    sm.close()


@pytest.fixture
async def session_end_hook(temp_db):
    """Create SessionEnd hook instance for testing."""
    hook = SimplifiedSessionEndHook()
    await hook._initialize_components()
    hook.session_manager = await SessionManager.get_instance(temp_db)
    hook.session_tracker = SessionTracker(hook.session_manager)
    hook.session_summary = SessionSummary(hook.session_manager)
    return hook


@pytest.fixture
async def sample_session(temp_db):
    """Create a sample session for testing."""
    sm = await SessionManager.get_instance(temp_db)
    session = await sm.create_session("test-session-123")

    # Update session with some test data
    await sm.update_session(
        "test-session-123",
        tokens_used=1500,
        files_modified=5,
        tasks_completed=3
    )

    return session


class TestSimplifiedSessionEndHook:
    """Test cases for SimplifiedSessionEndHook."""

    @pytest.mark.asyncio
    async def test_initialize_components(self, temp_db):
        """Test component initialization."""
        hook = SimplifiedSessionEndHook()

        await hook._initialize_components()

        assert hook.session_manager is not None
        assert hook.session_tracker is not None
        assert hook.session_summary is not None

    @pytest.mark.asyncio
    async def test_parse_hook_input_with_cchooks(self, session_end_hook):
        """Test hook input parsing with cchooks available."""
        mock_context = Mock()
        mock_context.session_id = "test-session-456"
        mock_context.transcript_path = "/path/to/transcript"
        mock_context.cwd = "/working/directory"
        mock_context.hook_event_name = "SessionEnd"

        with patch('hooks.devstream.sessions.session_end_simplified.CCHOOKS_AVAILABLE', True):
            with patch('hooks.devstream.sessions.session_end_simplified.create_context', return_value=mock_context):
                hook_data = session_end_hook._parse_hook_input()

                assert hook_data["session_id"] == "test-session-456"
                assert hook_data["transcript_path"] == "/path/to/transcript"
                assert hook_data["cwd"] == "/working/directory"
                assert hook_data["hook_event_name"] == "SessionEnd"

    @pytest.mark.asyncio
    async def test_parse_hook_input_fallback(self, session_end_hook, monkeypatch):
        """Test hook input parsing fallback method."""
        test_input = {
            "session_id": "fallback-session-789",
            "transcript_path": "/fallback/path"
        }

        with patch('hooks.devstream.sessions.session_end_simplified.CCHOOKS_AVAILABLE', False):
            with patch('sys.stdin', new_callable=Mock) as mock_stdin:
                mock_stdin.read = Mock(return_value=json.dumps(test_input))

                hook_data = session_end_hook._parse_hook_input()

                assert hook_data["session_id"] == "fallback-session-789"
                assert hook_data["transcript_path"] == "/fallback/path"

    @pytest.mark.asyncio
    async def test_get_active_session_id_from_hook_data(self, session_end_hook):
        """Test getting session ID from hook data."""
        hook_data = {"session_id": "explicit-session-123"}

        session_id = await session_end_hook._get_active_session_id(hook_data)

        assert session_id == "explicit-session-123"

    @pytest.mark.asyncio
    async def test_get_active_session_id_from_database(self, session_end_hook, sample_session):
        """Test getting session ID from active sessions."""
        hook_data = {}

        session_id = await session_end_hook._get_active_session_id(hook_data)

        assert session_id == "test-session-123"

    @pytest.mark.asyncio
    async def test_get_active_session_id_none_found(self, session_end_hook):
        """Test when no active session is found."""
        hook_data = {}

        session_id = await session_end_hook._get_active_session_id(hook_data)

        assert session_id is None

    @pytest.mark.asyncio
    async def test_end_session_success(self, session_end_hook, sample_session):
        """Test successful session ending."""
        session_id = "test-session-123"

        # Start tracking first
        await session_end_hook.session_tracker.start_tracking(session_id)

        results = await session_end_hook._end_session(session_id)

        assert results["success"] is True
        assert results["session_id"] == session_id
        assert results["session_ended"] is True
        assert results["tracking_stopped"] is True
        assert results["summary_generated"] is True
        assert results["summary_stored"] is True
        assert results["error"] is None
        assert "summary_preview" in results

        # Verify session is actually ended
        session = await session_end_hook.session_manager.get_session(session_id)
        assert session.status == "completed"
        assert session.ended_at is not None

    @pytest.mark.asyncio
    async def test_end_session_not_found(self, session_end_hook):
        """Test ending a session that doesn't exist."""
        session_id = "non-existent-session"

        results = await session_end_hook._end_session(session_id)

        assert results["success"] is False
        assert results["session_id"] == session_id
        assert results["session_ended"] is False
        assert "not found" in results["error"]

    @pytest.mark.asyncio
    async def test_end_session_tracking_failure_non_blocking(self, session_end_hook, sample_session):
        """Test session ending continues despite tracking failure."""
        session_id = "test-session-123"

        # Mock tracker to fail
        session_end_hook.session_tracker.stop_tracking = AsyncMock(side_effect=Exception("Tracking failed"))

        results = await session_end_hook._end_session(session_id)

        # Should still succeed despite tracking failure
        assert results["success"] is True
        assert results["session_ended"] is True
        assert results["tracking_stopped"] is False
        assert len(results["warnings"]) == 1
        assert "Tracking failed" in results["warnings"][0]

    @pytest.mark.asyncio
    async def test_end_session_summary_failure_non_blocking(self, session_end_hook, sample_session):
        """Test session ending continues despite summary failure."""
        session_id = "test-session-123"

        # Mock summary to fail
        session_end_hook.session_summary.generate_summary = AsyncMock(side_effect=Exception("Summary failed"))

        results = await session_end_hook._end_session(session_id)

        # Should still succeed despite summary failure
        assert results["success"] is True
        assert results["session_ended"] is True
        assert results["summary_generated"] is False
        assert len(results["warnings"]) == 1
        assert "Summary failed" in results["warnings"][0]

    @pytest.mark.asyncio
    async def test_end_session_manager_failure_blocks(self, session_end_hook, sample_session):
        """Test session ending fails if manager end_session fails."""
        session_id = "test-session-123"

        # Mock manager to fail
        session_end_hook.session_manager.end_session = AsyncMock(side_effect=Exception("Manager failed"))

        results = await session_end_hook._end_session(session_id)

        # Should fail if manager fails
        assert results["success"] is False
        assert results["session_ended"] is False
        assert "Manager failed" in results["error"]

    @pytest.mark.asyncio
    async def test_run_hook_success(self, session_end_hook, sample_session):
        """Test successful hook execution."""
        mock_hook_data = {"session_id": sample_session.id}

        with patch.object(session_end_hook, '_parse_hook_input', return_value=mock_hook_data):
            with patch.object(session_end_hook, '_get_active_session_id', return_value=sample_session.id):
                results = await session_end_hook.run_hook()

                assert results["success"] is True
                assert results["session_id"] == sample_session.id

    @pytest.mark.asyncio
    async def test_run_hook_no_session_found(self, session_end_hook):
        """Test hook execution when no session found."""
        mock_hook_data = {}

        with patch.object(session_end_hook, '_parse_hook_input', return_value=mock_hook_data):
            with patch.object(session_end_hook, '_get_active_session_id', return_value=None):
                results = await session_end_hook.run_hook()

                assert results["success"] is False
                assert "No active session found" in results["error"]

    @pytest.mark.asyncio
    async def test_run_hook_with_warnings(self, session_end_hook, sample_session):
        """Test hook execution with warnings."""
        mock_hook_data = {"session_id": sample_session.id}

        # Mock tracker to generate warning
        session_end_hook.session_tracker.stop_tracking = AsyncMock(side_effect=Exception("Tracking warning"))

        with patch.object(session_end_hook, '_parse_hook_input', return_value=mock_hook_data):
            with patch.object(session_end_hook, '_get_active_session_id', return_value=sample_session.id):
                results = await session_end_hook.run_hook()

                assert results["success"] is True
                assert len(results["warnings"]) == 1

    @pytest.mark.asyncio
    async def test_main_function_success(self, session_end_hook, sample_session, monkeypatch):
        """Test main function success path."""
        mock_results = {
            "success": True,
            "session_id": sample_session.id,
            "session_ended": True,
            "tracking_stopped": True,
            "summary_generated": True,
            "summary_stored": True,
            "summary_preview": "Test summary preview..."
        }

        with patch('hooks.devstream.sessions.session_end_simplified.CCHOOKS_AVAILABLE', False):
            with patch.object(session_end_hook, 'run_hook', return_value=mock_results):
                with patch('sys.exit') as mock_exit:
                    with patch('sys.stdin', new_callable=Mock) as mock_stdin:
                        # Mock stdin to avoid pytest capture issues
                        mock_stdin.read.return_value = "{}"

                        # Import the module to get the main function
                        from hooks.devstream.sessions.session_end_simplified import main
                        await main()

                        mock_exit.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_main_function_failure(self, session_end_hook, monkeypatch):
        """Test main function failure path."""
        mock_results = {
            "success": False,
            "error": "Test error"
        }

        with patch('hooks.devstream.sessions.session_end_simplified.CCHOOKS_AVAILABLE', False):
            with patch.object(session_end_hook, 'run_hook', return_value=mock_results):
                with patch('sys.exit') as mock_exit:
                    with patch('sys.stdin', new_callable=Mock) as mock_stdin:
                        # Mock stdin to avoid pytest capture issues
                        mock_stdin.read.return_value = "{}"

                        # Import the module to get the main function
                        from hooks.devstream.sessions.session_end_simplified import main
                        await main()

                        mock_exit.assert_called_once_with(2)

    @pytest.mark.asyncio
    async def test_structlog_context_binding(self, session_end_hook, sample_session):
        """Test structlog context binding during session ending."""
        session_id = "test-session-123"

        with patch('structlog.contextvars.bind_contextvars') as mock_bind:
            with patch('structlog.contextvars.clear_contextvars') as mock_clear:
                await session_end_hook._end_session(session_id)

                # Verify context was bound and cleared
                mock_bind.assert_called()
                mock_clear.assert_called()

    @pytest.mark.asyncio
    async def test_multiple_failures_accumulate_warnings(self, session_end_hook, sample_session):
        """Test that multiple non-critical failures accumulate warnings."""
        session_id = "test-session-123"

        # Mock both tracker and summary to fail
        session_end_hook.session_tracker.stop_tracking = AsyncMock(side_effect=Exception("Tracking failed"))
        session_end_hook.session_summary.generate_summary = AsyncMock(side_effect=Exception("Summary failed"))

        results = await session_end_hook._end_session(session_id)

        # Should succeed with multiple warnings
        assert results["success"] is True
        assert results["session_ended"] is True
        assert len(results["warnings"]) == 2
        warning_messages = " ".join(results["warnings"])
        assert "Tracking failed" in warning_messages
        assert "Summary failed" in warning_messages

    @pytest.mark.asyncio
    async def test_summary_preview_generation(self, session_end_hook, sample_session):
        """Test summary preview generation."""
        session_id = "test-session-123"

        results = await session_end_hook._end_session(session_id)

        assert "summary_preview" in results
        preview = results["summary_preview"]
        assert isinstance(preview, str)
        assert len(preview) > 0

        # Preview should be truncated if summary is long
        if len(preview) < 200:
            assert "..." not in preview
        else:
            assert preview.endswith("...")

    @pytest.mark.asyncio
    async def test_session_duration_calculation(self, session_end_hook, temp_db):
        """Test session duration calculation in logs."""
        sm = await SessionManager.get_instance(temp_db)

        # Create session with known start time
        session_id = "duration-test-session"
        session = await sm.create_session(session_id)

        # Mock current time to be 5 minutes later
        future_time = session.started_at + timedelta(minutes=5)

        with patch('hooks.devstream.sessions.session_end_simplified.datetime') as mock_datetime:
            mock_datetime.now.return_value = future_time

            results = await session_end_hook._end_session(session_id)

            assert results["success"] is True
            assert results["session_ended"] is True