"""Unit tests for simplified SessionStart hook."""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import pytest
import tempfile

# Add project root to path
import sys
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / ".claude"))

from hooks.devstream.sessions.session_start_simplified import SimplifiedSessionStartHook
from hooks.devstream.sessions.session_manager import SessionManager


@pytest.fixture
async def test_db(tmp_path: Path) -> str:
    """Create a test database with sessions table."""
    db_path = tmp_path / "test_session_start.db"
    manager = SessionManager(str(db_path))
    await manager._ensure_tables()
    yield str(db_path)
    await manager.close()


@pytest.fixture
async def session_start_hook(test_db: str) -> SimplifiedSessionStartHook:
    """Get SimplifiedSessionStartHook instance for testing."""
    hook = SimplifiedSessionStartHook()

    # Override the database path to use test database
    # Monkey patch the project_root to use test directory
    import hooks.devstream.sessions.session_start_simplified as hook_module
    original_project_root = hook_module.project_root
    hook_module.project_root = Path(test_db[:test_db.rfind('/')])

    try:
        await hook._initialize_components()
    finally:
        # Restore original project root
        hook_module.project_root = original_project_root

    return hook


@pytest.fixture
def mock_hook_data() -> Dict[str, Any]:
    """Mock hook input data."""
    return {
        "session_id": "test-session-start",
        "transcript_path": "/tmp/test_transcript.jsonl",
        "cwd": "/tmp",
        "hook_event_name": "SessionStart"
    }


class TestSimplifiedSessionStartHook:
    """Test simplified SessionStart hook functionality."""

    @pytest.mark.asyncio
    async def test_hook_initialization(self, session_start_hook: SimplifiedSessionStartHook) -> None:
        """Test hook initialization."""
        assert session_start_hook.session_manager is not None
        assert session_start_hook.session_tracker is not None
        assert session_start_hook.session_summary is not None

    @pytest.mark.asyncio
    async def test_parse_hook_input_with_cchooks(self, session_start_hook: SimplifiedSessionStartHook, monkeypatch) -> None:
        """Test hook input parsing with cchooks simulation."""
        # Mock cchooks availability
        monkeypatch.setattr("hooks.devstream.sessions.session_start_simplified.CCHOOKS_AVAILABLE", True)

        # Mock cchooks context
        class MockContext:
            def __init__(self):
                self.session_id = "mock-session-id"
                self.transcript_path = "/mock/transcript.jsonl"
                self.cwd = "/mock"
                self.hook_event_name = "SessionStart"

        def mock_create_context():
            return MockContext()

        monkeypatch.setattr("hooks.devstream.sessions.session_start_simplified.create_context", mock_create_context)

        hook_data = session_start_hook._parse_hook_input()

        assert hook_data["session_id"] == "mock-session-id"
        assert hook_data["hook_event_name"] == "SessionStart"
        assert hook_data["transcript_path"] == "/mock/transcript.jsonl"
        assert hook_data["cwd"] == "/mock"

    @pytest.mark.asyncio
    async def test_parse_hook_input_fallback(self, session_start_hook: SimplifiedSessionStartHook, monkeypatch) -> None:
        """Test hook input parsing fallback method."""
        # Mock cchooks unavailable
        monkeypatch.setattr("hooks.devstream.sessions.session_start_simplified.CCHOOKS_AVAILABLE", False)

        # Mock stdin input
        mock_input = {
            "session_id": "fallback-session",
            "hook_event_name": "SessionStart"
        }

        # Replace sys.stdin
        mock_stdin_content = json.dumps(mock_input)
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write(mock_stdin_content)
            temp_file_path = f.name

        # Mock sys.stdin
        original_stdin = sys.stdin
        with open(temp_file_path, 'r') as f:
            sys.stdin = f
            try:
                hook_data = session_start_hook._parse_hook_input()
                assert hook_data["session_id"] == "fallback-session"
                assert hook_data["hook_event_name"] == "SessionStart"
            finally:
                sys.stdin = original_stdin
                os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_get_session_id_from_hook_data(self, session_start_hook: SimplifiedSessionStartHook) -> None:
        """Test session ID extraction from hook data."""
        hook_data = {"session_id": "existing-session-id"}
        session_id = session_start_hook._get_session_id(hook_data)
        assert session_id == "existing-session-id"

    @pytest.mark.asyncio
    async def test_get_session_id_from_environment(self, session_start_hook: SimplifiedSessionStartHook, monkeypatch) -> None:
        """Test session ID extraction from environment variable."""
        # Set environment variable
        monkeypatch.setenv("CLAUDE_SESSION_ID", "env-session-id")

        hook_data = {}
        session_id = session_start_hook._get_session_id(hook_data)
        assert session_id == "env-session-id"

    @pytest.mark.asyncio
    async def test_get_session_id_generate_new(self, session_start_hook: SimplifiedSessionStartHook, monkeypatch) -> None:
        """Test session ID generation when none exists."""
        # Ensure no environment variable
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)

        hook_data = {}
        session_id = session_start_hook._get_session_id(hook_data)
        assert session_id.startswith("sess-")
        assert len(session_id) == 21  # "sess-" + 16 hex chars

    @pytest.mark.asyncio
    async def test_initialize_new_session(self, session_start_hook: SimplifiedSessionStartHook) -> None:
        """Test initializing a new session."""
        session_id = "test-new-session"

        results = await session_start_hook._initialize_session(session_id)

        assert results["success"] is True
        assert results["session_id"] == session_id
        assert results["session_created"] is True
        assert results["tracking_started"] is True
        assert results["error"] is None

        # Verify session exists
        session = await session_start_hook.session_manager.get_session(session_id)
        assert session is not None
        assert session.id == session_id
        assert session.status == "active"

        # Clean up tracking
        await session_start_hook.session_tracker.stop_tracking(session_id)

    @pytest.mark.asyncio
    async def test_resume_existing_session(self, session_start_hook: SimplifiedSessionStartHook) -> None:
        """Test resuming an existing active session."""
        session_id = "test-resume-session"

        # Create session first
        await session_start_hook.session_manager.create_session(session_id)

        # Initialize again (should resume)
        results = await session_start_hook._initialize_session(session_id)

        assert results["success"] is True
        assert results["session_id"] == session_id
        assert results.get("session_resumed") is True
        assert results["tracking_started"] is True
        assert results["error"] is None

        # Clean up tracking
        await session_start_hook.session_tracker.stop_tracking(session_id)

    @pytest.mark.asyncio
    async def test_run_hook_success(self, session_start_hook: SimplifiedSessionStartHook, mock_hook_data: Dict[str, Any], monkeypatch) -> None:
        """Test successful hook execution."""
        # Mock hook input parsing
        def mock_parse_hook_input():
            return mock_hook_data

        session_start_hook._parse_hook_input = mock_parse_hook_input

        results = await session_start_hook.run_hook()

        assert results["success"] is True
        assert results["session_id"] == mock_hook_data["session_id"]
        assert results["session_created"] is True
        assert results["tracking_started"] is True

        # Clean up
        await session_start_hook.session_tracker.stop_tracking(mock_hook_data["session_id"])

    @pytest.mark.asyncio
    async def test_session_context_binding(self, session_start_hook: SimplifiedSessionStartHook, mock_hook_data: Dict[str, Any], monkeypatch) -> None:
        """Test structlog context binding."""
        # Mock hook input parsing
        def mock_parse_hook_input():
            return mock_hook_data

        session_start_hook._parse_hook_input = mock_parse_hook_input

        # Run hook
        await session_start_hook.run_hook()

        # Context should be bound during execution
        # Note: We can't directly test context binding here as it's cleared in finally block
        # But we can verify the session was created successfully
        session = await session_start_hook.session_manager.get_session(mock_hook_data["session_id"])
        assert session is not None

        # Clean up
        await session_start_hook.session_tracker.stop_tracking(mock_hook_data["session_id"])

    @pytest.mark.asyncio
    async def test_error_handling_invalid_session(self, session_start_hook: SimplifiedSessionStartHook) -> None:
        """Test error handling for invalid session operations."""
        # Use invalid session ID (empty string)
        results = await session_start_hook._initialize_session("")

        # Should handle gracefully
        assert results["success"] is False
        assert results["error"] is not None

    @pytest.mark.asyncio
    async def test_metadata_storage(self, session_start_hook: SimplifiedSessionStartHook) -> None:
        """Test that session metadata is stored correctly."""
        session_id = "test-metadata-session"

        await session_start_hook._initialize_session(session_id)

        # Verify metadata was stored
        session = await session_start_hook.session_manager.get_session(session_id)
        assert session is not None
        assert session.metadata is not None

        # Parse metadata
        import json
        metadata = json.loads(session.metadata)
        assert metadata["hook_type"] == "SessionStart"
        assert "started_at" in metadata
        assert "project_root" in metadata

        # Clean up
        await session_start_hook.session_tracker.stop_tracking(session_id)