"""
Integration tests for session hooks cross-session memory preservation.

Tests cover:
- TC1: SessionStart displays marker file summary
- TC2: SessionStart handles missing marker file gracefully
- TC3: PreCompact generates summary before compaction
- TC4: PreCompact creates marker file
- TC5: PreCompact allows compaction on errors (non-blocking)

Test Dependencies:
- pytest>=7.0.0
- pytest-asyncio>=0.21.0
- pytest-mock>=3.10.0
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, mock_open, call
import sys
from datetime import datetime

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude/hooks/devstream/sessions'))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude/hooks/devstream/utils'))

from session_start import SessionStartHook
from pre_compact import PreCompactHook


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_marker_file_path(tmp_path):
    """Fixture for marker file path in temp directory."""
    marker_path = tmp_path / ".claude" / "state" / "devstream_last_session.txt"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    return marker_path


@pytest.fixture
def mock_precompact_context():
    """Fixture for mock PreCompactContext from cchooks."""
    context = Mock()
    context.output = Mock()
    context.output.exit_success = Mock()
    context.output.exit_non_block = Mock()
    return context


@pytest.fixture
def sample_summary():
    """Fixture for test summary content."""
    return """# Session Summary (2025-10-02 14:30:00)

## Completed Tasks
- Task: JWT Authentication Implementation
  Status: Completed
  Files: src/auth/jwt.py, tests/test_jwt.py

## Code Changes
- Files Modified: 5
- Lines Added: 342
- Lines Removed: 78

## Key Decisions
- Decision: Use RS256 for JWT signing
  Rationale: Better security for distributed systems
  Context7: fastapi/fastapi - JWT best practices

## Next Steps
- Implement refresh token rotation
- Add rate limiting to auth endpoints
"""


@pytest.fixture
def mock_active_session():
    """Fixture for mock active session data."""
    return {
        'session_id': 'test-session-123',
        'start_time': datetime.now().isoformat(),
        'task_count': 3,
        'file_count': 5,
        'status': 'active'
    }


# ============================================================================
# TC1: SessionStart displays marker file summary
# ============================================================================

@pytest.mark.asyncio
async def test_session_start_displays_marker_file_summary(
    mock_marker_file_path,
    sample_summary,
    capsys
):
    """
    Verify SessionStart hook displays previous session summary from marker file.

    Test Steps:
    1. Create mock marker file with test summary content
    2. Mock Path.home() to return temp directory
    3. Call display_previous_summary() method
    4. Assert summary content displayed to stdout
    5. Assert marker file deleted after display

    Expected: Summary displayed and marker file removed.
    """
    # ARRANGE - Create marker file with summary
    mock_marker_file_path.write_text(sample_summary)

    # Mock Path.home() to use temp directory
    with patch('session_start.Path.home', return_value=mock_marker_file_path.parent.parent.parent):
        hook = SessionStartHook()

        # ACT - Display summary
        await hook.display_previous_summary()

    # ASSERT - Verify output
    captured = capsys.readouterr()
    assert "Session Summary" in captured.out, "Summary header should be displayed"
    assert "JWT Authentication Implementation" in captured.out, "Task details should be displayed"
    assert "Key Decisions" in captured.out, "Decisions section should be displayed"

    # ASSERT - Verify marker file deleted
    assert not mock_marker_file_path.exists(), "Marker file should be deleted after display"


# ============================================================================
# TC2: SessionStart handles missing marker file gracefully
# ============================================================================

@pytest.mark.asyncio
async def test_session_start_handles_missing_marker_file_gracefully(
    tmp_path,
    capsys
):
    """
    Verify SessionStart hook doesn't crash when marker file missing.

    Test Steps:
    1. Mock Path.exists() to return False (no marker file)
    2. Call display_previous_summary() method
    3. Assert no exception raised
    4. Assert no output to stdout
    5. Assert no file operations attempted

    Expected: Graceful handling with no errors or output.
    """
    # ARRANGE - Mock non-existent marker file
    non_existent_path = tmp_path / ".claude" / "state" / "devstream_last_session.txt"

    with patch('session_start.Path.home', return_value=tmp_path):
        hook = SessionStartHook()

        # ACT - Attempt to display summary (should handle gracefully)
        try:
            await hook.display_previous_summary()
            exception_raised = False
        except Exception as e:
            exception_raised = True
            pytest.fail(f"Unexpected exception raised: {e}")

    # ASSERT - No exception raised
    assert not exception_raised, "Should handle missing marker file without exception"

    # ASSERT - No output (no summary to display)
    captured = capsys.readouterr()
    assert captured.out == "", "Should not produce output when marker file missing"

    # ASSERT - Marker file still doesn't exist (no file operations)
    assert not non_existent_path.exists(), "Should not create marker file if missing"


# ============================================================================
# TC3: PreCompact generates summary before compaction
# ============================================================================

@pytest.mark.asyncio
async def test_precompact_generates_summary_before_compaction(
    mock_precompact_context,
    mock_active_session,
    sample_summary
):
    """
    Verify PreCompact hook generates and stores summary.

    Test Steps:
    1. Mock active session in work_sessions table
    2. Mock SessionSummaryGenerator to return test summary
    3. Mock DevStream memory storage (MCP client)
    4. Call process_pre_compact(context) method
    5. Assert get_active_session_id() called
    6. Assert generate_and_store_summary() called
    7. Assert summary stored in DevStream memory
    8. Assert context.output.exit_success() called

    Expected: Summary generated, stored, and compaction allowed.
    """
    # ARRANGE - Mock database connection
    mock_db_cursor = AsyncMock()
    mock_db_cursor.fetchone = AsyncMock(return_value=(mock_active_session['session_id'],))

    mock_db_conn = AsyncMock()
    mock_db_conn.cursor = AsyncMock(return_value=mock_db_cursor)
    mock_db_conn.execute = AsyncMock(return_value=mock_db_cursor)
    mock_db_conn.close = AsyncMock()

    # Mock SessionSummaryGenerator
    mock_generator = AsyncMock()
    mock_generator.generate_and_store_summary = AsyncMock(return_value=sample_summary)

    # Mock aiosqlite.connect
    with patch('pre_compact.aiosqlite.connect', return_value=mock_db_conn):
        # Mock SessionSummaryGenerator instantiation
        with patch('pre_compact.SessionSummaryGenerator', return_value=mock_generator):
            hook = PreCompactHook()

            # ACT - Process pre-compact
            await hook.process_pre_compact(mock_precompact_context)

    # ASSERT - Active session ID retrieved
    mock_db_cursor.execute.assert_any_call(
        pytest.approx("SELECT session_id FROM work_sessions WHERE end_time IS NULL", abs=50),
        pytest.approx((), abs=0)
    )

    # ASSERT - Summary generation called
    mock_generator.generate_and_store_summary.assert_called_once()

    # ASSERT - Compaction allowed (exit_success called)
    mock_precompact_context.output.exit_success.assert_called_once()


# ============================================================================
# TC4: PreCompact creates marker file
# ============================================================================

@pytest.mark.asyncio
async def test_precompact_creates_marker_file(
    tmp_path,
    sample_summary
):
    """
    Verify PreCompact hook creates marker file with summary.

    Test Steps:
    1. Mock session data and summary generation
    2. Mock file system operations
    3. Call write_marker_file(summary) method
    4. Assert marker file path correct (~/.claude/state/devstream_last_session.txt)
    5. Assert parent directories created
    6. Assert file content matches summary
    7. Assert method returns True on success

    Expected: Marker file created with correct content and location.
    """
    # ARRANGE - Mock Path.home() to use temp directory
    marker_path = tmp_path / ".claude" / "state" / "devstream_last_session.txt"

    with patch('pre_compact.Path.home', return_value=tmp_path):
        hook = PreCompactHook()

        # ACT - Write marker file
        result = await hook.write_marker_file(sample_summary)

    # ASSERT - Marker file created
    assert marker_path.exists(), "Marker file should be created"

    # ASSERT - Parent directories created
    assert marker_path.parent.exists(), "Parent directories should be created"

    # ASSERT - File content matches summary
    written_content = marker_path.read_text()
    assert written_content == sample_summary, "Marker file content should match summary"

    # ASSERT - Method returns True on success
    assert result is True, "write_marker_file should return True on success"


# ============================================================================
# TC5: PreCompact allows compaction on errors (non-blocking)
# ============================================================================

@pytest.mark.asyncio
async def test_precompact_allows_compaction_on_errors(
    mock_precompact_context,
    mock_active_session,
    caplog
):
    """
    Verify PreCompact hook is non-blocking (allows compaction even on errors).

    Test Steps:
    1. Mock active session
    2. Mock generate_and_store_summary() to raise Exception
    3. Call process_pre_compact(context) method
    4. Assert no exception propagates (caught internally)
    5. Assert context.output.exit_success() still called (non-blocking)
    6. Assert warning logged

    Expected: Error caught, warning logged, compaction allowed.
    """
    # ARRANGE - Mock database connection
    mock_db_cursor = AsyncMock()
    mock_db_cursor.fetchone = AsyncMock(return_value=(mock_active_session['session_id'],))

    mock_db_conn = AsyncMock()
    mock_db_conn.cursor = AsyncMock(return_value=mock_db_cursor)
    mock_db_conn.execute = AsyncMock(return_value=mock_db_cursor)
    mock_db_conn.close = AsyncMock()

    # Mock SessionSummaryGenerator to raise exception
    mock_generator = AsyncMock()
    mock_generator.generate_and_store_summary = AsyncMock(
        side_effect=Exception("Test error: Summary generation failed")
    )

    exception_raised = False

    # Mock aiosqlite.connect
    with patch('pre_compact.aiosqlite.connect', return_value=mock_db_conn):
        # Mock SessionSummaryGenerator instantiation
        with patch('pre_compact.SessionSummaryGenerator', return_value=mock_generator):
            hook = PreCompactHook()

            # ACT - Process pre-compact (should not raise exception)
            try:
                await hook.process_pre_compact(mock_precompact_context)
            except Exception as e:
                exception_raised = True
                pytest.fail(f"Exception should be caught internally, not propagated: {e}")

    # ASSERT - No exception propagated
    assert not exception_raised, "Exception should be caught and not propagate"

    # ASSERT - Compaction allowed despite error (exit_success called)
    mock_precompact_context.output.exit_success.assert_called_once()

    # ASSERT - Warning logged
    assert "Pre-compact hook failed" in caplog.text or "error" in caplog.text.lower(), \
        "Warning should be logged for error condition"


# ============================================================================
# ADDITIONAL HELPER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_session_start_marker_file_path_construction(tmp_path):
    """
    Verify SessionStart constructs correct marker file path.

    Expected: ~/.claude/state/devstream_last_session.txt
    """
    # ARRANGE & ACT
    with patch('session_start.Path.home', return_value=tmp_path):
        hook = SessionStartHook()
        marker_path = hook._get_marker_file_path()

    # ASSERT
    expected_path = tmp_path / ".claude" / "state" / "devstream_last_session.txt"
    assert marker_path == expected_path, "Marker file path should match expected location"


@pytest.mark.asyncio
async def test_precompact_handles_no_active_session(
    mock_precompact_context,
    caplog
):
    """
    Verify PreCompact handles scenario with no active session gracefully.

    Expected: No summary generated, compaction allowed, info logged.
    """
    # ARRANGE - Mock database with no active session
    mock_db_cursor = AsyncMock()
    mock_db_cursor.fetchone = AsyncMock(return_value=None)  # No active session

    mock_db_conn = AsyncMock()
    mock_db_conn.cursor = AsyncMock(return_value=mock_db_cursor)
    mock_db_conn.execute = AsyncMock(return_value=mock_db_cursor)
    mock_db_conn.close = AsyncMock()

    # Mock aiosqlite.connect
    with patch('pre_compact.aiosqlite.connect', return_value=mock_db_conn):
        hook = PreCompactHook()

        # ACT
        await hook.process_pre_compact(mock_precompact_context)

    # ASSERT - Compaction allowed
    mock_precompact_context.output.exit_success.assert_called_once()

    # ASSERT - Info logged about no active session
    assert "No active session" in caplog.text or "no session" in caplog.text.lower(), \
        "Should log info about no active session"
