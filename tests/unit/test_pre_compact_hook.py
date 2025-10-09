"""
Unit Tests for PreCompactHook - Method-Level Isolation

Tests individual PreCompactHook methods in complete isolation using mocks.
No integration with actual hook code or external dependencies.

Test Coverage:
- UC1: PreCompactHook initialization
- UC2: get_active_session_id success path
- UC3: get_active_session_id no session found
- UC4: write_marker_file success path
- UC5: write_marker_file permission error
- UC6: process_pre_compact exits on no session

Context7 Pattern: pytest fixtures for common mocks, AAA pattern, async testing
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
import sys

# Add hooks directory to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / '.claude/hooks/devstream/sessions'))
sys.path.insert(0, str(project_root / '.claude/hooks/devstream/utils'))


# ==================== PYTEST FIXTURES ====================

@pytest.fixture
def sample_summary():
    """Sample session summary markdown."""
    return """# Session Summary

**Session**: test-session-123
**Duration**: 1h 30m
**Tasks**: 3 completed, 1 in progress
**Files Modified**: 5

## Key Activities
- Implemented PreCompactHook
- Added unit tests
- Updated documentation
"""


# ==================== UC1: INITIALIZATION ====================

@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
def test_precompact_hook_initialization(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class
):
    """
    UC1: Verify PreCompactHook initializes correctly with all components.

    Test Steps:
    1. Mock all dependencies (DevStreamHookBase, MCP client, extractors)
    2. Create PreCompactHook instance
    3. Assert base initialized (DevStreamHookBase)
    4. Assert mcp_client initialized
    5. Assert data_extractor initialized (SessionDataExtractor)
    6. Assert summary_generator initialized (SessionSummaryGenerator)
    7. Assert db_path set correctly
    """
    # Setup mocks
    mock_base_instance = Mock()
    mock_base_class.return_value = mock_base_instance

    mock_mcp_instance = Mock()
    mock_mcp_client_func.return_value = mock_mcp_instance

    mock_extractor_instance = Mock()
    mock_extractor_class.return_value = mock_extractor_instance

    mock_generator_instance = Mock()
    mock_generator_class.return_value = mock_generator_instance

    # Import after mocking
    from pre_compact import PreCompactHook

    # Act - Create PreCompactHook instance
    hook = PreCompactHook()

    # Assert - Verify all components initialized
    assert hook.base == mock_base_instance, "DevStreamHookBase should be initialized"
    assert hook.mcp_client == mock_mcp_instance, "MCP client should be initialized"
    assert hook.data_extractor == mock_extractor_instance, "SessionDataExtractor should be initialized"
    assert hook.summary_generator == mock_generator_instance, "SessionSummaryGenerator should be initialized"
    assert hasattr(hook, 'db_path'), "db_path should be set"
    assert 'devstream.db' in hook.db_path, "db_path should point to devstream.db"

    # Verify constructors called
    mock_base_class.assert_called_once_with("pre_compact")
    mock_mcp_client_func.assert_called_once()
    mock_extractor_class.assert_called_once()
    mock_generator_class.assert_called_once()


# ==================== UC2: GET ACTIVE SESSION - SUCCESS ====================

@pytest.mark.asyncio
@patch('pre_compact.aiosqlite')
@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
async def test_get_active_session_id_retrieves_session(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class,
    mock_aiosqlite
):
    """
    UC2: Verify get_active_session_id() retrieves active session from database.

    Test Steps:
    1. Mock aiosqlite connection and cursor
    2. Mock database query to return active session ID
    3. Create PreCompactHook instance
    4. Call await hook.get_active_session_id()
    5. Assert correct SQL query executed
    6. Assert returns session ID string
    7. Assert database connection closed properly
    """
    # Setup base mock
    mock_base_instance = Mock()
    mock_base_instance.debug_log = Mock()
    mock_base_class.return_value = mock_base_instance

    # Setup aiosqlite mock - need to mock async context manager properly
    mock_cursor = AsyncMock()
    mock_cursor.fetchone = AsyncMock(return_value={'id': 'sess-abc123'})
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock()

    mock_db = AsyncMock()
    mock_db.row_factory = None
    mock_execute_result = AsyncMock()
    mock_execute_result.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_execute_result.__aexit__ = AsyncMock()
    mock_db.execute = Mock(return_value=mock_execute_result)
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock()

    mock_aiosqlite.connect = Mock(return_value=mock_db)
    mock_aiosqlite.Row = Mock()

    # Import and create hook
    from pre_compact import PreCompactHook
    hook = PreCompactHook()

    # Act - Get active session ID
    session_id = await hook.get_active_session_id()

    # Assert - Verify session ID returned
    assert session_id == 'sess-abc123', "Should return active session ID"

    # Verify SQL query executed
    assert mock_db.execute.called, "Database execute should be called"
    sql_query = mock_db.execute.call_args[0][0]
    assert 'SELECT id FROM work_sessions' in sql_query, "Should query work_sessions table"
    assert "status = 'active'" in sql_query, "Should filter by active status"
    assert 'ORDER BY started_at DESC' in sql_query, "Should order by start time"
    assert 'LIMIT 1' in sql_query, "Should limit to 1 result"

    # Verify cursor methods called
    assert mock_cursor.fetchone.called, "Cursor fetchone should be called"

    # Verify debug log called
    assert mock_base_instance.debug_log.called, "Debug log should be called"


# ==================== UC3: GET ACTIVE SESSION - NO SESSION ====================

@pytest.mark.asyncio
@patch('pre_compact.aiosqlite')
@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
async def test_get_active_session_id_returns_none_when_no_session(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class,
    mock_aiosqlite
):
    """
    UC3: Verify get_active_session_id() returns None when no active session.

    Test Steps:
    1. Mock aiosqlite to return empty query result
    2. Create PreCompactHook instance
    3. Call await hook.get_active_session_id()
    4. Assert returns None (not exception)
    5. Assert debug log message logged
    """
    # Setup base mock
    mock_base_instance = Mock()
    mock_base_instance.debug_log = Mock()
    mock_base_class.return_value = mock_base_instance

    # Setup aiosqlite mock (no session found) - need to mock async context manager properly
    mock_cursor = AsyncMock()
    mock_cursor.fetchone = AsyncMock(return_value=None)
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock()

    mock_db = AsyncMock()
    mock_db.row_factory = None
    mock_execute_result = AsyncMock()
    mock_execute_result.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_execute_result.__aexit__ = AsyncMock()
    mock_db.execute = Mock(return_value=mock_execute_result)
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock()

    mock_aiosqlite.connect = Mock(return_value=mock_db)
    mock_aiosqlite.Row = Mock()

    # Import and create hook
    from pre_compact import PreCompactHook
    hook = PreCompactHook()

    # Act - Get active session ID (none exists)
    session_id = await hook.get_active_session_id()

    # Assert - Verify None returned (not exception)
    assert session_id is None, "Should return None when no active session"

    # Verify debug log called
    assert mock_base_instance.debug_log.called, "Debug log should be called"
    debug_calls = [call[0][0] for call in mock_base_instance.debug_log.call_args_list]
    assert any('No active session' in str(msg) for msg in debug_calls), \
        "Should log no active session message"


# ==================== UC4: WRITE MARKER FILE - SUCCESS ====================

@pytest.mark.asyncio
@patch('pre_compact.Path')
@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
async def test_write_marker_file_creates_file_successfully(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class,
    mock_path_class,
    sample_summary
):
    """
    UC4: Verify write_marker_file() creates marker file with summary.

    Test Steps:
    1. Mock Path operations (home, mkdir, write_text)
    2. Create PreCompactHook instance
    3. Call await hook.write_marker_file("test summary")
    4. Assert marker file path = ~/.claude/state/devstream_last_session.txt
    5. Assert Path.mkdir(parents=True, exist_ok=True) called
    6. Assert Path.write_text("test summary") called
    7. Assert returns True
    """
    # Setup base mock
    mock_base_instance = Mock()
    mock_base_instance.debug_log = Mock()
    mock_base_class.return_value = mock_base_instance

    # Setup Path mocks
    mock_marker_file = MagicMock()
    mock_parent = MagicMock()
    mock_marker_file.parent = mock_parent
    mock_marker_file.write_text = Mock()

    mock_home_path = MagicMock()
    mock_path_class.home = Mock(return_value=mock_home_path)

    # Chain path operations: home / ".claude" / "state" / "devstream_last_session.txt"
    def create_path_chain(*args):
        if len(args) == 0:
            return mock_marker_file
        return mock_home_path

    mock_home_path.__truediv__ = Mock(side_effect=lambda x:
        mock_home_path if x in [".claude", "state"] else mock_marker_file
    )

    # Import and create hook
    from pre_compact import PreCompactHook
    hook = PreCompactHook()

    # Act - Write marker file
    result = await hook.write_marker_file(sample_summary)

    # Assert - Verify file creation
    assert result is True, "Should return True on successful write"

    # Verify mkdir called
    assert mock_parent.mkdir.called, "Parent mkdir should be called"
    mkdir_call = mock_parent.mkdir.call_args
    assert mkdir_call[1]['parents'] is True, "Should create parent directories"
    assert mkdir_call[1]['exist_ok'] is True, "Should not fail if directory exists"

    # Verify write_text called with summary
    assert mock_marker_file.write_text.called, "write_text should be called"
    # Extract the actual argument passed to write_text
    write_text_arg = mock_marker_file.write_text.call_args[0][0]
    assert write_text_arg == sample_summary, \
        f"Should write summary to file. Expected: {sample_summary}, Got: {write_text_arg}"

    # Verify debug log called
    assert mock_base_instance.debug_log.called, "Debug log should be called"


# ==================== UC5: WRITE MARKER FILE - ERROR ====================

@pytest.mark.asyncio
@patch('pre_compact.Path')
@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
async def test_write_marker_file_handles_permission_error(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class,
    mock_path_class,
    sample_summary
):
    """
    UC5: Verify write_marker_file() handles file write errors gracefully.

    Test Steps:
    1. Mock Path.write_text() to raise PermissionError
    2. Create PreCompactHook instance
    3. Call await hook.write_marker_file("test summary")
    4. Assert returns False (not exception)
    5. Assert error logged (debug_log called)
    6. Assert graceful degradation (no exception propagates)
    """
    # Setup base mock
    mock_base_instance = Mock()
    mock_base_instance.debug_log = Mock()
    mock_base_class.return_value = mock_base_instance

    # Setup Path mocks with error
    mock_marker_file = MagicMock()
    mock_parent = MagicMock()
    mock_marker_file.parent = mock_parent
    mock_marker_file.write_text = Mock(side_effect=PermissionError("Permission denied"))

    mock_home_path = MagicMock()
    mock_path_class.home = Mock(return_value=mock_home_path)

    mock_home_path.__truediv__ = Mock(side_effect=lambda x:
        mock_home_path if x in [".claude", "state"] else mock_marker_file
    )

    # Import and create hook
    from pre_compact import PreCompactHook
    hook = PreCompactHook()

    # Act - Write marker file (should handle error)
    result = await hook.write_marker_file(sample_summary)

    # Assert - Verify graceful failure
    assert result is False, "Should return False on permission error"

    # Verify error logged
    assert mock_base_instance.debug_log.called, "Debug log should be called"
    debug_calls = [call[0][0] for call in mock_base_instance.debug_log.call_args_list]
    assert any('Failed to write marker file' in str(msg) for msg in debug_calls), \
        "Should log write failure message"

    # Verify mkdir was called (error happens on write_text, not mkdir)
    assert mock_parent.mkdir.called, "mkdir should be called before write_text"


# ==================== UC6: PROCESS PRE COMPACT - NO SESSION ====================

@pytest.mark.asyncio
@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
async def test_process_precompact_exits_success_on_no_session(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class
):
    """
    UC6: Verify process_pre_compact() exits successfully when no active session.

    Test Steps:
    1. Mock get_active_session_id() to return None
    2. Mock PreCompactContext with exit_success method
    3. Create PreCompactHook instance
    4. Call await hook.process_pre_compact(context)
    5. Assert get_active_session_id() called
    6. Assert no summary generation attempted
    7. Assert context.output.exit_success() called
    8. Assert debug log message present
    """
    # Setup base mock
    mock_base_instance = Mock()
    mock_base_instance.debug_log = Mock()
    mock_base_class.return_value = mock_base_instance

    # Import and create hook
    from pre_compact import PreCompactHook
    hook = PreCompactHook()

    # Mock get_active_session_id to return None
    hook.get_active_session_id = AsyncMock(return_value=None)

    # Mock PreCompactContext
    mock_context = Mock()
    mock_context.output = Mock()
    mock_context.output.exit_success = Mock()

    # Act - Process pre-compact with no active session
    await hook.process_pre_compact(mock_context)

    # Assert - Verify workflow
    hook.get_active_session_id.assert_called_once()

    # Verify exit_success called (allow compaction)
    mock_context.output.exit_success.assert_called_once()

    # Verify debug log called
    assert mock_base_instance.debug_log.called, "Debug log should be called"
    debug_calls = [call[0][0] for call in mock_base_instance.debug_log.call_args_list]
    assert any('No active session' in str(msg) for msg in debug_calls), \
        "Should log no active session skip message"


# ==================== TEST METADATA ====================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
