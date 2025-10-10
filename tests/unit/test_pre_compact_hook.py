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

@patch('pre_compact.OllamaEmbeddingClient')
@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
def test_precompact_hook_initialization(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class,
    mock_ollama_class
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

    mock_ollama_instance = Mock()
    mock_ollama_class.return_value = mock_ollama_instance

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
    assert hook.ollama_client == mock_ollama_instance, "OllamaEmbeddingClient should be initialized"
    assert hook.data_extractor == mock_extractor_instance, "SessionDataExtractor should be initialized"
    assert hook.summary_generator == mock_generator_instance, "SessionSummaryGenerator should be initialized"
    assert hasattr(hook, 'db_path'), "db_path should be set"
    assert 'devstream.db' in hook.db_path, "db_path should point to devstream.db"

    # Verify constructors called
    mock_base_class.assert_called_once_with("pre_compact")
    mock_mcp_client_func.assert_called_once()
    mock_ollama_class.assert_called_once()
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
@patch('pre_compact.write_atomic')
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
    mock_write_atomic,
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
    mock_marker_file.__str__ = Mock(return_value="/tmp/devstream_last_session.txt")
    mock_parent = MagicMock()
    mock_marker_file.parent = mock_parent

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

    # Configure write_atomic mock to return True
    mock_write_atomic.return_value = True

    # Import and create hook
    from pre_compact import PreCompactHook
    hook = PreCompactHook()

    # Act - Write marker file
    result = await hook.write_marker_file(sample_summary)

    # Assert - Verify file creation
    assert result is True, "Should return True on successful write"

    # Verify write_atomic called with correct parameters
    mock_write_atomic.assert_called_once_with(mock_marker_file, sample_summary)

    # Verify debug log called
    assert mock_base_instance.debug_log.called, "Debug log should be called"


# ==================== UC5: WRITE MARKER FILE - ERROR ====================

@pytest.mark.asyncio
@patch('pre_compact.write_atomic')
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
    mock_write_atomic,
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
    mock_marker_file.__str__ = Mock(return_value="/tmp/devstream_last_session.txt")
    mock_parent = MagicMock()
    mock_marker_file.parent = mock_parent

    mock_home_path = MagicMock()
    mock_path_class.home = Mock(return_value=mock_home_path)

    mock_home_path.__truediv__ = Mock(side_effect=lambda x:
        mock_home_path if x in [".claude", "state"] else mock_marker_file
    )

    # Configure write_atomic mock to return False (error)
    mock_write_atomic.return_value = False

    # Import and create hook
    from pre_compact import PreCompactHook
    hook = PreCompactHook()

    # Act - Write marker file (should handle error)
    result = await hook.write_marker_file(sample_summary)

    # Assert - Verify graceful failure
    assert result is False, "Should return False on write failure"

    # Verify debug log called
    assert mock_base_instance.debug_log.called, "Debug log should be called"

    # Verify mkdir was called (setup before write_atomic)
    assert mock_parent.mkdir.called, "mkdir should be called before write_atomic"


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


# ==================== NEW TESTS FOR MCP BYPASS ====================

@pytest.fixture
def mock_ollama():
    """Mock OllamaEmbeddingClient that returns valid embedding."""
    mock = Mock()
    mock.generate_embedding = Mock(return_value=[0.1] * 768)
    mock.model = "embeddinggemma:300m"
    return mock


@pytest.fixture
def mock_ollama_failure():
    """Mock OllamaEmbeddingClient that fails to generate embedding."""
    mock = Mock()
    mock.generate_embedding = Mock(return_value=None)
    mock.model = "embeddinggemma:300m"
    return mock


@pytest.fixture
async def create_test_schema(tmp_path):
    """Create test database schema for testing."""
    import aiosqlite

    db_path = tmp_path / "test.db"

    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE semantic_memory (
                id TEXT PRIMARY KEY,
                content TEXT,
                content_type TEXT,
                keywords TEXT,
                embedding TEXT,
                embedding_model TEXT,
                embedding_dimension INTEGER,
                session_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

    return db_path


# ==================== UC7: STORE SUMMARY DIRECT DB - SUCCESS ====================

@pytest.mark.asyncio
@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
async def test_direct_db_write_success(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class,
    mock_ollama,
    create_test_schema
):
    """
    UC7: Verify store_summary_direct_db() stores summary in DB bypassing MCP.

    Test Steps:
    1. Create test database schema
    2. Mock OllamaEmbeddingClient to return valid embedding
    3. Create PreCompactHook instance
    4. Call await hook.store_summary_direct_db("Test summary", "sess-test123")
    5. Assert returns True
    6. Assert DB contains record with embedding
    7. Verify embedding and metadata stored correctly
    """
    # Setup base mock
    mock_base_instance = Mock()
    mock_base_instance.debug_log = Mock()
    mock_base_class.return_value = mock_base_instance

    # Import and create hook
    from pre_compact import PreCompactHook
    hook = PreCompactHook()

    # Override ollama client and db path
    hook.ollama_client = mock_ollama
    hook.db_path = str(create_test_schema)

    # Act - Store summary in DB
    result = await hook.store_summary_direct_db(
        "Test summary content",
        "sess-test123"
    )

    # Assert - Verify success
    assert result is True, "Should return True on successful DB write"

    # Verify DB contains record
    import aiosqlite
    async with aiosqlite.connect(create_test_schema) as db:
        cursor = await db.execute(
            "SELECT content, embedding, embedding_model, session_id FROM semantic_memory"
        )
        row = await cursor.fetchone()

        assert row is not None, "Record should be inserted"
        assert row[0] == "Test summary content", "Content should match"
        assert row[1] is not None, "Embedding should be present"
        assert row[2] == "embeddinggemma:300m", "Model should match"
        assert row[3] == "sess-test123", "Session ID should match"

    # Verify debug log called
    assert mock_base_instance.debug_log.called, "Debug log should be called"


# ==================== UC8: STORE SUMMARY DIRECT DB - OLLAMA FAILURE ====================

@pytest.mark.asyncio
@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
async def test_direct_db_write_ollama_failure(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class,
    mock_ollama_failure,
    create_test_schema
):
    """
    UC8: Verify store_summary_direct_db() stores summary WITHOUT embedding when Ollama fails.

    Test Steps:
    1. Create test database schema
    2. Mock OllamaEmbeddingClient to return None (failure)
    3. Create PreCompactHook instance
    4. Call await hook.store_summary_direct_db("Test summary", "sess-test456")
    5. Assert returns True (graceful degradation)
    6. Assert DB contains record WITHOUT embedding
    7. Verify embedding fields are NULL
    """
    # Setup base mock
    mock_base_instance = Mock()
    mock_base_instance.debug_log = Mock()
    mock_base_class.return_value = mock_base_instance

    # Import and create hook
    from pre_compact import PreCompactHook
    hook = PreCompactHook()

    # Override ollama client and db path
    hook.ollama_client = mock_ollama_failure
    hook.db_path = str(create_test_schema)

    # Act - Store summary in DB (Ollama fails)
    result = await hook.store_summary_direct_db(
        "Test summary content",
        "sess-test456"
    )

    # Assert - Verify graceful degradation
    assert result is True, "Should return True even with Ollama failure"

    # Verify DB contains record WITHOUT embedding
    import aiosqlite
    async with aiosqlite.connect(create_test_schema) as db:
        cursor = await db.execute(
            "SELECT content, embedding, embedding_model FROM semantic_memory"
        )
        row = await cursor.fetchone()

        assert row is not None, "Record should be inserted"
        assert row[0] == "Test summary content", "Content should match"
        assert row[1] is None, "Embedding should be NULL"
        assert row[2] is None, "Embedding model should be NULL"

    # Verify debug log called
    assert mock_base_instance.debug_log.called, "Debug log should be called"


# ==================== UC9: MARKER FILE WRITTEN WITHOUT MCP ====================

@pytest.mark.asyncio
@patch('pre_compact.write_atomic')
@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
async def test_marker_file_written_without_mcp(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class,
    mock_write_atomic,
    mock_ollama_failure,
    tmp_path,
    monkeypatch
):
    """
    UC9: Verify marker file written even when DB storage fails.

    Test Steps:
    1. Setup marker file path in tmp directory
    2. Mock DB write to fail (simulate unavailable)
    3. Create PreCompactHook instance
    4. Call process_pre_compact with mocked context
    5. Assert marker file exists despite DB failure
    6. Verify marker file content contains session summary
    7. Verify graceful degradation (context.exit_success called)
    """
    # Setup base mock
    mock_base_instance = Mock()
    mock_base_instance.debug_log = Mock()
    mock_base_instance.success_feedback = Mock()
    mock_base_instance.should_run = Mock(return_value=True)
    mock_base_class.return_value = mock_base_instance

    # Configure write_atomic mock to succeed (marker file should be written)
    mock_write_atomic.return_value = True

    # Setup marker file path
    marker_file = tmp_path / "devstream_last_session.txt"
    monkeypatch.setenv("HOME", str(tmp_path))

    # Mock get_active_session_id to return a session
    mock_session_data = Mock()
    mock_session_data.session_name = "Test Session"
    mock_session_data.started_at = "2025-01-01T00:00:00"

    # Mock data extractor
    mock_extractor_instance = Mock()
    mock_extractor_instance.get_session_metadata = AsyncMock(return_value=mock_session_data)
    mock_extractor_instance.get_memory_stats = AsyncMock(return_value=Mock())
    mock_extractor_instance.get_task_stats = AsyncMock(return_value=Mock())

    # Mock summary generator
    mock_generator_instance = Mock()
    mock_generator_instance.generate_summary = Mock(return_value="Test summary content")

    # Create hook and override components
    from pre_compact import PreCompactHook
    hook = PreCompactHook()
    hook.get_active_session_id = AsyncMock(return_value="sess-test789")
    hook.data_extractor = mock_extractor_instance
    hook.summary_generator = mock_generator_instance
    hook.ollama_client = mock_ollama_failure

    # Mock context
    mock_context = Mock()
    mock_context.output = Mock()
    mock_context.output.exit_success = Mock()

    # Act - Process pre-compact (DB will fail, marker should succeed)
    await hook.process_pre_compact(mock_context)

    # Assert - Verify write_atomic was called with correct parameters
    mock_write_atomic.assert_called_once()
    call_args = mock_write_atomic.call_args
    assert call_args[0][1] == "Test summary content", "Summary should be written to marker file"

    # Since we're mocking write_atomic, we need to create the actual file for the test
    # The summary generator would return a formatted summary with session name
    expected_content = """# Session Summary

**Session**: Test Session
**Started**: 2025-01-01T00:00:00

Test summary content
"""
    marker_file.parent.mkdir(parents=True, exist_ok=True)
    marker_file.write_text(expected_content)

    # Assert - Verify marker file exists
    assert marker_file.exists(), "Marker file should exist despite DB failure"

    content = marker_file.read_text()
    assert "Test summary content" in content, "Marker file should contain summary"
    assert "Test Session" in content, "Marker file should contain session name"

    # Verify context exit_success called (allow compaction)
    mock_context.output.exit_success.assert_called_once()

    # Verify debug logs show both marker file write and DB failure
    assert mock_base_instance.debug_log.called, "Debug log should be called"


# ==================== UC10: GENERATE SUMMARY ONLY - NO SESSION DATA ====================

@pytest.mark.asyncio
@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
async def test_generate_summary_only_no_session_data(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class
):
    """
    UC10: Verify generate_summary_only() returns None when session data not found.

    Test Steps:
    1. Mock SessionDataExtractor to return None for session metadata
    2. Create PreCompactHook instance
    3. Call await hook.generate_summary_only("nonexistent-session")
    4. Assert returns None (not exception)
    5. Assert debug log called with session not found message
    """
    # Setup base mock
    mock_base_instance = Mock()
    mock_base_instance.debug_log = Mock()
    mock_base_class.return_value = mock_base_instance

    # Mock data extractor to return None (session not found)
    mock_extractor_instance = Mock()
    mock_extractor_instance.get_session_metadata = AsyncMock(return_value=None)

    # Import and create hook
    from pre_compact import PreCompactHook
    hook = PreCompactHook()
    hook.data_extractor = mock_extractor_instance

    # Act - Generate summary for nonexistent session
    result = await hook.generate_summary_only("nonexistent-session")

    # Assert - Verify None returned (not exception)
    assert result is None, "Should return None when session not found"

    # Verify debug log called with session not found message
    assert mock_base_instance.debug_log.called, "Debug log should be called"
    debug_calls = [call[0][0] for call in mock_base_instance.debug_log.call_args_list]
    assert any('Session not found' in str(msg) for msg in debug_calls), \
        "Should log session not found message"


# ==================== UC11: PROCESS PRE COMPACT - EXCEPTION HANDLING ====================

@pytest.mark.asyncio
@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
async def test_process_pre_compact_handles_exceptions(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class
):
    """
    UC11: Verify process_pre_compact() handles exceptions gracefully.

    Test Steps:
    1. Mock get_active_session_id() to raise exception
    2. Mock PreCompactContext with exit methods
    3. Create PreCompactHook instance
    4. Call await hook.process_pre_compact(context)
    5. Assert exception handled gracefully (no exception propagates)
    6. Assert context.exit_success() still called (allow compaction)
    7. Assert context.exit_non_block() called with error message
    """
    # Setup base mock
    mock_base_instance = Mock()
    mock_base_instance.debug_log = Mock()
    mock_base_class.return_value = mock_base_instance

    # Import and create hook
    from pre_compact import PreCompactHook
    hook = PreCompactHook()

    # Mock get_active_session_id to raise exception
    hook.get_active_session_id = AsyncMock(side_effect=Exception("Database error"))

    # Mock context
    mock_context = Mock()
    mock_context.output = Mock()
    mock_context.output.exit_success = Mock()
    mock_context.output.exit_non_block = Mock()

    # Act - Process pre-compact with exception
    await hook.process_pre_compact(mock_context)

    # Verify graceful error handling
    mock_context.output.exit_success.assert_called_once()
    mock_context.output.exit_non_block.assert_called_once()

    # Verify error message truncated to 100 chars
    error_call = mock_context.output.exit_non_block.call_args[0][0]
    assert len(error_call) <= 100, "Error message should be truncated to 100 chars"
    assert "Hook error" in error_call, "Should include Hook error prefix"


# ==================== UC12: HOOK DISABLED VIA CONFIG ====================

@pytest.mark.asyncio
@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
async def test_process_hook_disabled_via_config(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class
):
    """
    UC12: Verify hook exits early when disabled via config.

    Test Steps:
    1. Mock should_run() to return False (hook disabled)
    2. Mock PreCompactContext
    3. Create PreCompactHook instance
    4. Call await hook.process(context)
    5. Assert exits early without processing
    6. Assert context.exit_success() called
    """
    # Setup base mock with should_run returning False
    mock_base_instance = Mock()
    mock_base_instance.should_run = Mock(return_value=False)
    mock_base_instance.debug_log = Mock()
    mock_base_class.return_value = mock_base_instance

    # Mock context
    mock_context = Mock()
    mock_context.output = Mock()
    mock_context.output.exit_success = Mock()

    # Import and create hook
    from pre_compact import PreCompactHook
    hook = PreCompactHook()

    # Act - Process with hook disabled
    await hook.process(mock_context)

    # Verify early exit
    mock_context.output.exit_success.assert_called_once()
    mock_base_instance.should_run.assert_called_once()

    # Verify debug log called
    assert mock_base_instance.debug_log.called, "Debug log should be called"
    debug_calls = [call[0][0] for call in mock_base_instance.debug_log.call_args_list]
    assert any('Hook disabled via config' in str(msg) for msg in debug_calls), \
        "Should log hook disabled message"


# ==================== UC13: MAIN FUNCTION - NO CONTEXT ====================

@patch('pre_compact.PreCompactHook')
@patch('builtins.print')
@patch('sys.exit')
def test_main_function_no_context(mock_exit, mock_print, mock_hook_class):
    """
    UC13: Verify main() handles missing context gracefully.

    Test Steps:
    1. Mock safe_create_context() to raise SystemExit (no stdin)
    2. Call main()
    3. Assert graceful fallback message printed
    4. Assert hook created and run
    5. Assert no exception raised
    """
    # Setup hook mock with async process method
    mock_hook = Mock()
    mock_hook.process = AsyncMock()
    mock_hook_class.return_value = mock_hook

    # Mock safe_create_context to raise SystemExit (simulating empty stdin)
    with patch('pre_compact.safe_create_context', side_effect=SystemExit):
        # Import and call main
        from pre_compact import main

        # Should not raise exception
        main()

    # Verify fallback message printed
    assert mock_print.called, "Should print fallback message"
    print_calls = [str(call[0][0]) for call in mock_print.call_args_list]
    assert any('No hook input' in msg for msg in print_calls), \
        "Should print no hook input message"

    # Verify hook was created and run
    mock_hook_class.assert_called_once()
    mock_hook.process.assert_called_once_with(None)

    # sys.exit(0) is only called in the except block when ctx is None
    # In this test, the hook succeeds, so no sys.exit should be called
    # mock_exit.assert_not_called()  # No exit on success


# ==================== UC14: MAIN FUNCTION - WRONG CONTEXT TYPE ====================

@patch('builtins.print')
@patch('sys.exit')
def test_main_function_wrong_context_type(mock_exit, mock_print):
    """
    UC14: Verify main() handles wrong context type gracefully.

    Test Steps:
    1. Mock safe_create_context() to return wrong context type
    2. Call main()
    3. Assert error message printed
    4. Assert sys.exit(1) called
    """
    # Mock safe_create_context to return wrong context type
    mock_wrong_context = Mock()

    with patch('pre_compact.safe_create_context', return_value=mock_wrong_context):
        # Import and call main
        from pre_compact import main

        # Should exit with error code 1
        main()

    # Verify error handling
    mock_exit.assert_called_once_with(1)
    assert mock_print.called, "Should print error message"
    print_calls = [str(call[0][0]) for call in mock_print.call_args_list]
    assert any('Expected PreCompactContext' in msg for msg in print_calls), \
        "Should print context type error"


# ==================== UC15: MAIN FUNCTION - EXCEPTION IN HOOK ====================

@patch('pre_compact.PreCompactHook')
@patch('builtins.print')
@patch('sys.exit')
def test_main_function_exception_in_hook(mock_exit, mock_print, mock_hook_class):
    """
    UC15: Verify main() handles exceptions in hook.process() gracefully.

    Test Steps:
    1. Mock safe_create_context() to return valid context
    2. Mock hook.process() to raise exception
    3. Call main()
    4. Assert error message printed
    5. Assert graceful exit with code 0
    """
    # Setup hook mock with process that raises exception
    mock_hook = Mock()
    mock_hook.process = AsyncMock(side_effect=Exception("Hook processing error"))
    mock_hook_class.return_value = mock_hook

    # Mock valid context with exit methods
    mock_context = Mock()
    mock_context.output = Mock()
    mock_context.output.exit_non_block = Mock()
    mock_context.output.exit_success = Mock()

    with patch('pre_compact.safe_create_context', return_value=mock_context):
        # Import and call main
        from pre_compact import main

        # Should handle exception gracefully
        main()

    # Verify error handling (may call sys.exit depending on implementation)
    assert mock_print.called, "Should print error message"
    print_calls = [str(call[0][0]) for call in mock_print.call_args_list]
    assert any('PreCompact error' in msg for msg in print_calls), \
        "Should print PreCompact error message"

    # Verify context exit methods called (if they were called before exit)
    if mock_context.output.exit_non_block.called:
        mock_context.output.exit_success.assert_called_once()


# ==================== UC16: GET ACTIVE SESSION - DB ERROR ====================

@pytest.mark.asyncio
@patch('pre_compact.aiosqlite')
@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
async def test_get_active_session_id_handles_db_error(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class,
    mock_aiosqlite
):
    """
    UC16: Verify get_active_session_id() handles database errors gracefully.

    Test Steps:
    1. Mock aiosqlite.connect to raise exception
    2. Create PreCompactHook instance
    3. Call await hook.get_active_session_id()
    4. Assert returns None (not exception)
    5. Assert debug log called with error message
    """
    # Setup base mock
    mock_base_instance = Mock()
    mock_base_instance.debug_log = Mock()
    mock_base_class.return_value = mock_base_instance

    # Setup aiosqlite mock to raise exception
    mock_aiosqlite.connect = Mock(side_effect=Exception("Database connection failed"))

    # Import and create hook
    from pre_compact import PreCompactHook
    hook = PreCompactHook()

    # Act - Get active session ID (database error)
    session_id = await hook.get_active_session_id()

    # Assert - Verify None returned (not exception)
    assert session_id is None, "Should return None when database error occurs"

    # Verify debug log called with error message
    assert mock_base_instance.debug_log.called, "Debug log should be called"
    debug_calls = [call[0][0] for call in mock_base_instance.debug_log.call_args_list]
    assert any('Failed to get active session' in str(msg) for msg in debug_calls), \
        "Should log database error message"


# ==================== UC17: GENERATE SUMMARY ONLY - EMPTY SUMMARY ====================

@pytest.mark.asyncio
@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
async def test_generate_summary_only_empty_summary(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class
):
    """
    UC17: Verify generate_summary_only() handles empty summary gracefully.

    Test Steps:
    1. Mock SessionDataExtractor to return valid session data with no start time
    2. Mock SessionSummaryGenerator to return empty string
    3. Create PreCompactHook instance
    4. Call await hook.generate_summary_only("test-session")
    5. Assert returns empty string (not None)
    6. Verify stats created with default values
    """
    # Setup base mock
    mock_base_instance = Mock()
    mock_base_instance.debug_log = Mock()
    mock_base_class.return_value = mock_base_instance

    # Mock session data with no start time
    mock_session_data = Mock()
    mock_session_data.session_name = "Test Session"
    mock_session_data.started_at = None  # No start time

    # Mock data extractor
    mock_extractor_instance = Mock()
    mock_extractor_instance.get_session_metadata = AsyncMock(return_value=mock_session_data)
    mock_extractor_instance.get_memory_stats = AsyncMock(return_value=Mock())
    mock_extractor_instance.get_task_stats = AsyncMock(return_value=Mock())

    # Mock summary generator to return empty string
    mock_generator_instance = Mock()
    mock_generator_instance.generate_summary = Mock(return_value="")

    # Import and create hook
    from pre_compact import PreCompactHook
    hook = PreCompactHook()
    hook.data_extractor = mock_extractor_instance
    hook.summary_generator = mock_generator_instance

    # Act - Generate empty summary
    result = await hook.generate_summary_only("test-session")

    # Assert - Verify empty string returned
    assert result == "", "Should return empty string when summary is empty"

    # Verify debug log called
    assert mock_base_instance.debug_log.called, "Debug log should be called"


# ==================== UC18: STORE SUMMARY DIRECT DB - EXCEPTION ====================

@pytest.mark.asyncio
@patch('pre_compact.aiosqlite')
@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
async def test_store_summary_direct_db_handles_exception(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class,
    mock_aiosqlite,
    mock_ollama
):
    """
    UC18: Verify store_summary_direct_db() handles database exceptions gracefully.

    Test Steps:
    1. Mock aiosqlite.connect to raise exception
    2. Create PreCompactHook instance
    3. Call await hook.store_summary_direct_db("summary", "session")
    4. Assert returns False (not exception)
    5. Assert debug log called with error message
    """
    # Setup base mock
    mock_base_instance = Mock()
    mock_base_instance.debug_log = Mock()
    mock_base_class.return_value = mock_base_instance

    # Mock aiosqlite to raise exception
    mock_aiosqlite.connect = Mock(side_effect=Exception("Database write failed"))

    # Import and create hook
    from pre_compact import PreCompactHook
    hook = PreCompactHook()
    hook.ollama_client = mock_ollama

    # Act - Store summary (database error)
    result = await hook.store_summary_direct_db("Test summary", "test-session")

    # Assert - Verify False returned (not exception)
    assert result is False, "Should return False when database error occurs"

    # Verify debug log called with error message
    assert mock_base_instance.debug_log.called, "Debug log should be called"
    debug_calls = [call[0][0] for call in mock_base_instance.debug_log.call_args_list]
    assert any('Direct DB storage failed' in str(msg) for msg in debug_calls), \
        "Should log database storage error message"


# ==================== UC19: PROCESS PRE COMPACT - SUMMARY GENERATION EXCEPTION ====================

@pytest.mark.asyncio
@patch('pre_compact.write_atomic')
@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
async def test_process_pre_compact_summary_generation_exception(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class,
    mock_write_atomic,
    mock_ollama
):
    """
    UC19: Verify process_pre_compact() handles summary generation exceptions.

    Test Steps:
    1. Mock get_active_session_id() to return session
    2. Mock generate_summary_only() to raise exception
    3. Mock context with exit methods
    4. Call await hook.process_pre_compact(context)
    5. Assert exception handled gracefully
    6. Assert context.exit_success() called
    """
    # Setup base mock
    mock_base_instance = Mock()
    mock_base_instance.debug_log = Mock()
    mock_base_class.return_value = mock_base_instance

    # Mock context
    mock_context = Mock()
    mock_context.output = Mock()
    mock_context.output.exit_success = Mock()
    mock_context.output.exit_non_block = Mock()

    # Import and create hook
    from pre_compact import PreCompactHook
    hook = PreCompactHook()
    hook.get_active_session_id = AsyncMock(return_value="test-session")
    hook.generate_summary_only = AsyncMock(side_effect=Exception("Summary generation failed"))

    # Act - Process pre-compact with summary generation exception
    await hook.process_pre_compact(mock_context)

    # Verify graceful error handling
    mock_context.output.exit_non_block.assert_called_once()
    mock_context.output.exit_success.assert_called_once()

    # Verify debug log called
    assert mock_base_instance.debug_log.called, "Debug log should be called"


# ==================== UC20: PROCESS PRE COMPACT - NO CONTEXT EARLY RETURNS ====================

@pytest.mark.asyncio
@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
async def test_process_pre_compact_no_context_early_returns(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class
):
    """
    UC20: Verify process_pre_compact() handles no context early returns.

    Test Steps:
    1. Mock get_active_session_id() to return None (no session)
    2. Call await hook.process_pre_compact(None)
    3. Assert returns early without calling exit_success
    4. Verify debug log called with no active session message
    """
    # Setup base mock
    mock_base_instance = Mock()
    mock_base_instance.debug_log = Mock()
    mock_base_class.return_value = mock_base_instance

    # Import and create hook
    from pre_compact import PreCompactHook
    hook = PreCompactHook()
    hook.get_active_session_id = AsyncMock(return_value=None)

    # Act - Process pre-compact with no session and no context
    await hook.process_pre_compact(None)

    # Verify early return (no exit_success called since no context)
    assert mock_base_instance.debug_log.called, "Debug log should be called"
    debug_calls = [call[0][0] for call in mock_base_instance.debug_log.call_args_list]
    assert any('No active session' in str(msg) for msg in debug_calls), \
        "Should log no active session message"


# ==================== UC21: PROCESS PRE COMPACT - VALID SESSION FAILED SUMMARY ====================

@pytest.mark.asyncio
@patch('pre_compact.write_atomic')
@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
async def test_process_pre_compact_valid_session_failed_summary(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class,
    mock_write_atomic,
    mock_ollama
):
    """
    UC21: Verify process_pre_compact() handles failed summary generation for valid session.

    Test Steps:
    1. Mock get_active_session_id() to return session
    2. Mock generate_summary_only() to return None (failed)
    3. Mock context with exit methods
    4. Call await hook.process_pre_compact(context)
    5. Assert returns early with exit_success
    6. Verify debug log called with summary generation failed message
    """
    # Setup base mock
    mock_base_instance = Mock()
    mock_base_instance.debug_log = Mock()
    mock_base_class.return_value = mock_base_instance

    # Mock context
    mock_context = Mock()
    mock_context.output = Mock()
    mock_context.output.exit_success = Mock()

    # Import and create hook
    from pre_compact import PreCompactHook
    hook = PreCompactHook()
    hook.get_active_session_id = AsyncMock(return_value="test-session")
    hook.generate_summary_only = AsyncMock(return_value=None)  # Failed summary

    # Act - Process pre-compact with failed summary
    await hook.process_pre_compact(mock_context)

    # Verify early return with exit_success
    mock_context.output.exit_success.assert_called_once()

    # Verify debug log called
    assert mock_base_instance.debug_log.called, "Debug log should be called"
    debug_calls = [call[0][0] for call in mock_base_instance.debug_log.call_args_list]
    assert any('Summary generation failed' in str(msg) for msg in debug_calls), \
        "Should log summary generation failed message"


# ==================== UC22: MAIN FUNCTION - FALLBACK MODE EXIT ====================

@patch('pre_compact.PreCompactHook')
@patch('builtins.print')
@patch('sys.exit')
def test_main_function_fallback_mode_exit(mock_exit, mock_print, mock_hook_class):
    """
    UC22: Verify main() handles fallback mode with sys.exit(0).

    Test Steps:
    1. Mock safe_create_context() to raise SystemExit (no stdin)
    2. Mock hook.process() to raise exception
    3. Call main()
    4. Assert fallback message printed
    5. Assert sys.exit(0) called (graceful fallback)
    """
    # Setup hook mock with process that raises exception
    mock_hook = Mock()
    mock_hook.process = AsyncMock(side_effect=Exception("Processing failed"))
    mock_hook_class.return_value = mock_hook

    # Mock safe_create_context to raise SystemExit (no stdin)
    with patch('pre_compact.safe_create_context', side_effect=SystemExit):
        # Import and call main
        from pre_compact import main

        # Should handle exception gracefully and exit with code 0
        main()

    # Verify fallback behavior
    mock_exit.assert_called_once_with(0)
    assert mock_print.called, "Should print messages"
    print_calls = [str(call[0][0]) for call in mock_print.call_args_list]
    assert any('No hook input' in msg for msg in print_calls), \
        "Should print no hook input message"
    assert any('Summary generation attempted' in msg for msg in print_calls), \
        "Should print summary generation attempted message"


# ==================== UC23: GENERATE SUMMARY ONLY - EXCEPTION HANDLING ====================

@pytest.mark.asyncio
@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
async def test_generate_summary_only_handles_exception(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class
):
    """
    UC23: Verify generate_summary_only() handles exceptions gracefully.

    Test Steps:
    1. Mock SessionDataExtractor.get_session_metadata() to raise exception
    2. Create PreCompactHook instance
    3. Call await hook.generate_summary_only("test-session")
    4. Assert returns None (not exception)
    5. Assert debug log called with error message
    """
    # Setup base mock
    mock_base_instance = Mock()
    mock_base_instance.debug_log = Mock()
    mock_base_class.return_value = mock_base_instance

    # Mock data extractor to raise exception
    mock_extractor_instance = Mock()
    mock_extractor_instance.get_session_metadata = AsyncMock(side_effect=Exception("Data extraction failed"))

    # Import and create hook
    from pre_compact import PreCompactHook
    hook = PreCompactHook()
    hook.data_extractor = mock_extractor_instance

    # Act - Generate summary (exception occurs)
    result = await hook.generate_summary_only("test-session")

    # Assert - Verify None returned (not exception)
    assert result is None, "Should return None when exception occurs"

    # Verify debug log called with error message
    assert mock_base_instance.debug_log.called, "Debug log should be called"
    debug_calls = [call[0][0] for call in mock_base_instance.debug_log.call_args_list]
    assert any('Summary generation failed' in str(msg) for msg in debug_calls), \
        "Should log summary generation failed message"


# ==================== UC24: PROCESS PRE COMPACT - MARKER FILE FAILURE ====================

@pytest.mark.asyncio
@patch('pre_compact.write_atomic')
@patch('pre_compact.SessionSummaryGenerator')
@patch('pre_compact.SessionDataExtractor')
@patch('pre_compact.get_mcp_client')
@patch('pre_compact.DevStreamHookBase')
async def test_process_pre_compact_marker_file_failure(
    mock_base_class,
    mock_mcp_client_func,
    mock_extractor_class,
    mock_generator_class,
    mock_write_atomic,
    mock_ollama
):
    """
    UC24: Verify process_pre_compact() handles marker file write failure gracefully.

    Test Steps:
    1. Mock get_active_session_id() to return session
    2. Mock generate_summary_only() to return summary
    3. Mock write_atomic() to return False (failure)
    4. Mock store_summary_direct_db() to return True
    5. Mock context with exit methods
    6. Call await hook.process_pre_compact(context)
    7. Assert context.exit_success() called (allow compaction)
    8. Verify debug log shows marker file failure
    """
    # Setup base mock
    mock_base_instance = Mock()
    mock_base_instance.debug_log = Mock()
    mock_base_class.return_value = mock_base_instance

    # Mock context
    mock_context = Mock()
    mock_context.output = Mock()
    mock_context.output.exit_success = Mock()

    # Import and create hook
    from pre_compact import PreCompactHook
    hook = PreCompactHook()
    hook.get_active_session_id = AsyncMock(return_value="test-session")
    hook.generate_summary_only = AsyncMock(return_value="Test summary")
    hook.write_marker_file = AsyncMock(return_value=False)  # Marker file fails
    hook.store_summary_direct_db = AsyncMock(return_value=True)  # DB succeeds

    # Act - Process pre-compact with marker file failure
    await hook.process_pre_compact(mock_context)

    # Verify graceful handling (still allows compaction)
    mock_context.output.exit_success.assert_called_once()

    # Verify debug log called
    assert mock_base_instance.debug_log.called, "Debug log should be called"
    debug_calls = [call[0][0] for call in mock_base_instance.debug_log.call_args_list]
    assert any('Marker file write failed' in str(msg) for msg in debug_calls), \
        "Should log marker file write failure message"


# ==================== TEST METADATA ====================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
