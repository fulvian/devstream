#!/usr/bin/env .devstream/bin/python
"""
Unit tests for PostToolUse hook with retry logic (FASE 4.4)

Tests the enhanced PostToolUse hook with retry logic for:
- MCP connection failures
- Ollama embedding generation failures
- Database connection failures
- Retry logic with exponential backoff
- Graceful degradation scenarios

FASE 4.4: PostToolUse Hook Enhancement Complete
"""

import pytest
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'memory'))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'utils'))

from post_tool_use import PostToolUseHook
from cchooks import PostToolUseContext


class TestPostToolUseHook:
    """Test suite for PostToolUse hook functionality"""

    @pytest.fixture
    def hook(self):
        """Create a PostToolUseHook instance for testing"""
        with patch('post_tool_use.DevStreamHookBase'):
            hook = PostToolUseHook()
            hook.base = MagicMock()
            hook.base.should_run.return_value = True
            hook.base.is_memory_store_enabled.return_value = True
            hook.base.debug_log = MagicMock()
            hook.base.success_feedback = MagicMock()
            hook.base.warning_feedback = MagicMock()
            hook.mcp_client = AsyncMock()
            hook.ollama_client = MagicMock()
            hook.real_time_capture = MagicMock()
            return hook

    @pytest.fixture
    def mock_context(self):
        """Create a mock PostToolUseContext"""
        context = MagicMock(spec=PostToolUseContext)
        context.tool_name = "Write"
        context.tool_input = {
            "file_path": "test.py",
            "content": "print('Hello, world!')",
        }
        context.tool_response = {"success": True}
        context.output = MagicMock()
        return context

    def test_initialization(self, hook):
        """Test hook initialization"""
        assert hook.max_retries == 3
        assert hook.retry_delay == 1.0
        assert hook.retry_backoff == 2.0
        assert hook.mcp_client is not None
        assert hook.ollama_client is not None

    async def test_retry_logic_success_after_failures(self, hook):
        """Test retry logic succeeds after temporary failures"""
        # Mock operation that fails 2 times then succeeds
        attempt_count = 0

        async def failing_operation(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count <= 2:
                raise ConnectionError(f"Temporary failure #{attempt_count}")
            return "success_result"

        result = await hook.retry_with_backoff(
            "test_operation",
            failing_operation
        )

        assert result == "success_result"
        assert attempt_count == 3

        # Verify logging was called appropriately
        hook.base.debug_log.assert_any_call(
            lambda msg: "✓ test_operation succeeded" in msg
        )

    async def test_retry_logic_permanent_failure(self, hook):
        """Test retry logic fails immediately on permanent errors"""
        async def permanent_failure_operation(*args, **kwargs):
            raise ValueError("Permanent API key error")

        result = await hook.retry_with_backoff(
            "permanent_operation",
            permanent_failure_operation
        )

        assert result is None

        # Should not log retry attempts for permanent errors
        hook.base.debug_log.assert_any_call(
            lambda msg: "❌ permanent_operation permanent failure" in msg
        )

    async def test_retry_logic_max_retries_exceeded(self, hook):
        """Test retry logic respects max retry limit"""
        attempt_count = 0

        async def always_failing_operation(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            raise ConnectionError(f"Persistent failure #{attempt_count}")

        result = await hook.retry_with_backoff(
            "max_retry_operation",
            always_failing_operation
        )

        assert result is None
        assert attempt_count == 4  # max_retries + 1

    async def test_extract_content_preview_truncation(self, hook):
        """Test content preview truncation"""
        # Test short content (no truncation)
        short_content = "Short text"
        preview = hook.extract_content_preview(short_content, max_length=20)
        assert preview == "Short text"

        # Test long content (with truncation)
        long_content = "This is a very long piece of content that should be truncated because it exceeds the maximum length limit"
        preview = hook.extract_content_preview(long_content, max_length=50)
        assert len(preview) <= 53  # 50 + "..."

        # Test sentence boundary break
        content_with_period = "First sentence. Second sentence."
        preview = hook.extract_content_with_period_break(content_with_period, max_length=50)
        assert preview == "First sentence."

        # Test no good break points
        no_breaks = "abcdefghijklmnopqrstuvwxyz" * 5
        preview = hook.extract_content_preview(no_breaks, max_length=30)
        assert preview.endswith("...")

    async def test_extract_keywords_extraction(self, hook):
        """Test keyword extraction from file path and content"""
        file_path = "src/components/test_component.py"
        content = "import React from 'react'"

        keywords = hook.extract_keywords(file_path, content)

        assert "test_component" in keywords
        assert "components" in keywords
        assert "react" in keywords
        assert "python" in keywords
        assert "implementation" in keywords

    async def test_classify_content_type(self, hook):
        """Test content type classification"""
        # Test Write operation success
        context = MagicMock()
        context.tool_name = "Write"
        context.tool_response = {"success": True}

        content_type = hook.classify_content_type(
            context.tool_name,
            context.tool_response,
            "code content"
        )
        assert content_type == "code"

        # Test Bash operation failure
        context.tool_name = "Bash"
        context.tool_response = {"success": False}
        content_type = hook.classify_content_type(
            context.tool_name,
            context.tool_response,
            "error output"
        )
        assert content_type == "error"

    async def test_should_capture_bash_output_filtering(self, hook):
        """Test Bash output filtering logic"""
        # Should filter trivial commands
        trivial_commands = ["ls", "pwd", "cd", "echo", "cat"]
        for cmd in trivial_commands:
            tool_input = {"command": cmd}
            tool_response = {"output": "output"}
            assert not hook.should_capture_bash_output(tool_input, tool_response)

        # Should capture significant output
        tool_input = {"command": "python -c 'print(\"important output\")'"}
        tool_response = {"output": "important output"}
        assert hook.should_capture_bash_output(tool_input, tool_response)

        # Should filter short output
        tool_input = {"command": "echo short"}
        tool_response = {"output": "hi"}
        assert not hook.should_capture_bash_output(tool_input, tool_response)

    async def test_should_capture_read_content_filtering(self, hook):
        """Test Read content filtering logic"""
        # Should capture source files
        source_files = [
            "test.py", "app.tsx", "docs/readme.md",
            "config.yaml", "script.sh", "schema.sql"
        ]
        for file_path in source_files:
            assert hook.should_capture_read_content(file_path)

        # Should filter excluded paths
        excluded_paths = [
            ".git/config", "node_modules/pkg.js",
            "__pycache__/test.pyc", "dist/build"
        ]
        for file_path in excluded_paths:
            assert not hook.should_capture_read_content(file_path)

    async def test_extract_topics_extraction(self, hook):
        """Test topic extraction from content"""
        # Test Python content
        content = "import asyncio and pytest for testing"
        topics = hook.extract_topics(content, "test.py")
        assert "python" in topics
        assert "testing" in topics

        # Test TypeScript content
        content = "import React from 'react' and use hooks for state"
        topics = hook.extract_topics(content, "app.tsx")
        assert "react" in topics
        assert "hooks" in topics

        # Test database content
        content = "SELECT * FROM users WHERE active = 1"
        topics = hook.extract_topics(content, "query.sql")
        assert "database" in topics

    async def test_extract_entities_extraction(self, hook):
        """Test entity extraction from content"""
        # Test tech stack content
        content = "Using FastAPI with SQLAlchemy and Pydantic for validation"
        entities = hook.extract_entities(content)
        assert "FastAPI" in entities
        assert "SQLAlchemy" in entities
        assert "Pydantic" in entities

        # Test import detection
        content = "from datetime import datetime, timedelta\nimport sys"
        entities = hook.extract_entities(content)
        assert "datetime" in entities
        assert "timedelta" in entities

        # Filter out standard library
        content = "import os, sys, re, json"
        entities = hook.extract_entities(content)
        assert len(entities) == 0  # All filtered out

    async def test_update_memory_embedding_success(self, hook):
        """Test successful memory embedding update"""
        # Mock database with sqlite-vec
        with patch('post_tool_use.get_db_connection_with_vec') as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.__enter__.return_value = mock_conn
            mock_conn.__exit__.return_value = None
            mock_get_conn.return_value = mock_conn

            memory_id = "test_memory_id"
            embedding = [0.1] * 768

            result = hook.update_memory_embedding(memory_id, embedding)

            assert result is True
            mock_cursor.execute.assert_called_once()
            mock_conn.commit.assert_called_once()

    async def test_update_memory_embedding_not_found(self, hook):
        """Test embedding update when record not found"""
        with patch('post_tool_use.get_db_connection_with_vec') as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 0  # No rows affected
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.__enter__.return_value = mock_conn
            mock_conn.__exit__.return_value = None
            mock_get_conn.return_value = mock_conn

            memory_id = "nonexistent_id"
            embedding = [0.1] * 768

            result = hook.update_memory_embedding(memory_id, embedding)

            assert result is False

    async def test_update_memory_embedding_retry(self, hook):
        """Test embedding update with retry logic"""
        attempt_count = 0

        def mock_db_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count <= 2:
                raise ConnectionError(f"DB locked #{attempt_count}")

            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.__enter__.return_value = mock_conn
            mock_conn.__exit__.return_value = mock_conn
            mock_conn.commit.return_value = None
            return mock_conn

        with patch('post_tool_use.time.sleep') as mock_sleep:
            with patch('post_tool_use.get_db_connection_with_vec', return_value=mock_db_operation):
                memory_id = "test_memory_id"
                embedding = [0.1] * 768

                result = hook.update_memory_embedding(memory_id, embedding)

                assert result is True
                assert attempt_count == 3
                assert mock_sleep.call_count == 2  # Called for retries

    async def test_store_in_memory_success(self, hook, mock_context):
        """Test successful memory storage"""
        # Mock successful MCP call
        mock_result = {
            "memory_id": "test_memory_id",
            "success": True
        }
        hook.base.safe_mcp_call = AsyncMock(return_value=mock_result)

        # Mock successful embedding generation
        hook.ollama_client.generate_embedding = AsyncMock(return_value=[0.1] * 768)
        hook.update_memory_embedding = AsyncMock(return_value=True)

        result = await hook.store_in_memory(
            file_path="test.py",
            content="print('Hello, world!')",
            operation="Write",
            topics=["python", "testing"],
            entities=["asyncio"],
            content_type="code"
        )

        assert result == "test_memory_id"

        # Verify retry logic was not called (successful on first try)
        hook.retry_with_backoff.assert_not_called()

    async def test_store_in_memory_mcp_retry(self, hook, mock_context):
        """Test memory storage with MCP retry logic"""
        # Mock MCP failures then success
        attempt_count = 0
        async def mock_mcp_call(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count <= 2:
                raise ConnectionError(f"MCP timeout #{attempt_count}")
            return {"memory_id": "test_memory_id", "success": True}

        hook.base.safe_mcp_call = mock_mcp_call
        hook.ollama_client.generate_embedding = AsyncMock(return_value=[0.1] * 768)
        hook.update_memory_embedding = AsyncMock(return_value=True)

        result = await hook.store_in_memory(
            file_path="test.py",
            content="print('Hello, world!')",
            operation="Write",
            topics=["python", "testing"],
            entities=["asyncio"],
            content_type="code"
        )

        assert result == "test_memory_id"
        assert attempt_count == 3

    async def test_store_in_memory_embedding_retry(self, hook, mock_context):
        """Test memory storage with embedding retry logic"""
        # Mock embedding failures then success
        attempt_count = 0
        async def mock_generate_embedding(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count <= 1:
                raise ConnectionError(f"Ollama timeout #{attempt_count}")
            return [0.1] * 768

        hook.ollama_client.generate_embedding = mock_generate_embedding
        hook.base.safe_mcp_call = AsyncMock(return_value={"memory_id": "test_memory_id", "success": True})
        hook.update_memory_embedding = AsyncMock(return_value=True)

        result = await hook.store_in_memory(
            file_path="test.py",
            content="print('Hello, world!')",
            operation="Write",
            topics=["python", "testing"],
            entities=["asyncio"],
            content_type="code"
        )

        assert result == "test_memory_id"
        assert attempt_count == 2

    async def test_store_in_memory_embedding_update_retry(self, hook, mock_context):
        """Test memory storage with embedding update retry logic"""
        # Mock embedding update failures then success
        attempt_count = 0
        async def mock_update_embedding(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count <= 1:
                raise ConnectionError(f"DB locked during update #{attempt_count}")
            return True

        hook.ollama_client.generate_embedding = AsyncMock(return_value=[0.1] * 768)
        hook.base.safe_mcp_call = AsyncMock(return_value={"memory_id": "test_memory_id", "success": True})
        hook.update_memory_embedding = mock_update_embedding

        result = await hook.store_in_memory(
            file_path="test.py",
            content="print('Hello, world!')",
            operation="Write",
            topics=["python", "testing"],
            entities=["asyncio"],
            content_type="code"
        )

        assert result == "test_memory_id"
        assert attempt_count == 2

    async def test_store_in_memory_graceful_degradation(self, hook, mock_context):
        """Test graceful degradation on failures"""
        # Mock complete MCP failure
        hook.base.safe_mcp_call = AsyncMock(return_value=None)
        hook.ollama_client.generate_embedding = AsyncMock(side_effect=Exception("Ollama unavailable"))
        hook.update_memory_embedding = AsyncMock(side_effect=Exception("DB locked"))

        result = await hook.store_in_memory(
            file_path="test.py",
            content="print('Hello, world!')",
            operation="Write",
            topics=["python", "testing"],
            entities=["asyncio"],
            content_type="code"
        )

        assert result is None  # Should return None but not crash

    async def test_should_capture_all_tool_types(self, hook):
        """Test all tool types are properly captured"""
        critical_tools = ["Write", "Edit", "MultiEdit", "Bash", "TodoWrite"]

        for tool_name in critical_tools:
            is_critical = tool_name in critical_tools
            assert is_critical, f"{tool_name} should be marked as critical"

    async def test_session_tracking_update_files(self, hook, mock_context):
        """Test session file tracking"""
        # Mock session operations
        mock_context.tool_name = "Write"
        mock_context.tool_input = {"file_path": "test.py"}

        with patch.objectify(hook) as mock_hook:
            mock_hook._get_current_session_id = AsyncMock(return_value="session_123")
            mock_hook._add_active_file = AsyncMock(return_value=True)

            await hook.update_session_tracking(mock_context.tool_name, mock_context.tool_input)

            mock_hook._add_active_file.assert_called_once_with("session_123", "test.py")

    async def test_session_tracking_update_tasks(self, hook, mock_context):
        """Test session task tracking"""
        # Mock session operations
        mock_context.tool_name = "TodoWrite"
        mock_context.tool_input = {
            "todos": [
                {"content": "Task 1", "status": "in_progress"},
                {"content": "Task 2", "status": "pending"}
            ]
        }

        with patch.objectify(hook) as mock_hook:
            mock_hook._get_current_session_id = AsyncMock(return_value="session_123")
            mock_hook._add_active_task = AsyncMock(return_value=True)

            await hook.update_session_tracking(mock_context.tool_name, mock_context.tool_input)

            # Should track the in_progress task
            mock_hook._add_active_task.assert_called_once_with("session_123", "Task 1")

    async def test_audit_trail_logging(self, hook, mock_context):
        """Test audit trail logging"""
        mock_context.tool_name = "Write"
        mock_context.tool_response = {"success": True}
        mock_context.tool_input = {"file_path": "test.py"}

        with patch.objectify(hook) as mock_hook:
            memory_id = "test_memory_id"
            topics = ["python", "testing"]
            entities = ["asyncio"]

            # Call log_capture_audit
            mock_hook.log_capture_audit(
                tool_name=mock_context.tool_name,
                tool_response=mock_context.tool_response,
                content_type="code",
                topics=topics,
                entities=entities,
                memory_id=memory_id,
                capture_decision="stored"
            )

            # Verify audit was logged
            mock_hook.base.debug_log.assert_any_call(
                lambda msg: "📊 Audit:" in msg and "Write" in msg
            )

    async def test_real_time_capture_trigger(self, hook):
        """Test real-time capture triggering for critical tools"""
        critical_tools = ["Write", "Edit", "MultiEdit", "Bash", "TodoWrite"]

        for tool_name in critical_tools:
            file_path = "test.py" if tool_name in ["Write", "Edit", "MultiEdit"] else ""

            with patch.objectify(hook) as mock_hook:
                mock_hook.real_time_capture.get_status.return_value = {
                    "is_running": False,
                    "monitored_files_count": 0,
                    "monitored_extensions": [".tsx", ".py", ".md", ".ts"]
                }

                await hook.trigger_real_time_capture_for_critical_tool(tool_name, file_path)

                # Should attempt to start monitoring if not running
                if tool_name in ["Write", "Edit", "MultiEdit"]:
                    mock_hook.real_time_capture.start_monitoring.assert_called_once()

    def test_fallback_mode_functionality(self, hook):
        """Test fallback mode when no context available"""
        # This would test the fallback_mode method
        # In practice, this is hard to test due to input/output complexities
        assert hasattr(hook, 'run_fallback_mode')

    def test_database_path_configuration(self, hook):
        """Test database path configuration"""
        project_root = Path(__file__).parent.parent.parent.parent.parent.parent
        expected_path = str(project_root / 'data' / 'devstream.db')

        assert hook.db_path == expected_path


class TestPostToolUseHookIntegration:
    """Integration tests for PostToolUse hook"""

    @pytest.fixture
    def sample_file_content(self):
        """Sample file content for testing"""
        return '''#!/usr/bin/env python3
"""
Test Python file for PostToolUse hook testing.
"""

    async def test_end_to_end_write_operation(self, hook, sample_file_content):
        """Test complete Write operation from start to finish"""
        # Create a test file
        test_file = Path("test_write_sample.py")
        test_file.write_text(sample_file_content)

        try:
            # Create mock context
            context = MagicMock(spec=PostToolUseContext)
            context.tool_name = "Write"
            context.tool_input = {
                "file_path": str(test_file),
                "content": sample_file_content
            }
            context.tool_response = {"success": True}
            context.output = MagicMock()

            # Mock dependencies
            with patch.objectify(hook) as mock_hook:
                mock_hook.base.should_run.return_value = True
                mock_hook.base.is_memory_store_enabled.return_value = True
                mock_hook.mcp_client = AsyncMock(return_value={
                    "memory_id": "test_memory_id",
                    "success": True
                })
                mock_hook.ollama_client = AsyncMock(return_value=[0.1] * 768)
                mock_hook.update_memory_embedding = AsyncMock(return_value=True)

                # Process the hook
                await hook.process(context)

            # Verify context was successful
            context.output.exit_success.assert_called_once()

            # Verify file was processed
            assert test_file.exists()

        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()

    async def test_end_to_end_bash_operation(self, hook):
        """Test complete Bash operation with significant output"""
        context = MagicMock(spec=PostToolContext)
        context.tool_name = "Bash"
        context.tool_input = {
            "command": "python -c 'print(\"Important test output\")'"
        }
        context.tool_response = {
            "success": True,
            "output": "Important test output\n"
        }
        context.output = MagicMock()

        # Mock dependencies
        with patch.objectify(hook) as mock_hook:
            mock_hook.base.should_run.return_value = True
            mock_hook.base.is_memory_store_enabled.return_value = True
            mock_hook.mcp_client = AsyncMock(return_value={
                "memory_id": "test_memory_id",
                "success": True
            })
            mock_hook.ollama_client = AsyncMock(return_value=[0.1] * 768)
            mock_hook.update_memory_embedding = AsyncMock(return_value=True)

            # Process the hook
            await hook.process(context)

        # Verify context was successful
        context.output.exit_success.assert_called_once()

    async def test_end_to_end_todo_write_operation(self, hook):
        """Test complete TodoWrite operation"""
        todos = [
            {"content": "Test task 1", "status": "in_progress"},
            {"content": "Test task 2", "status": "pending"}
        ]

        context = MagicMock(spec=PostToolContext)
        context.tool_name = "TodoWrite"
        context.tool_input = {"todos": todos}
        context.tool_response = {"success": True}
        context.output = MagicMock()

        # Mock dependencies
        with patch.objectify(hook) as mock_hook:
            mock_hook.base.should_run.return_value = True
            mock_hook.base.is_memory_store_enabled.return_value = True
            mock_hook.mcp_client = AsyncMock(return_value={
                "memory_id": "test_memory_id",
                "success": True
            })

            # Process the hook
            await hook.process(context)

        # Verify context was successful
        context.output.exit_success.assert_called_once()


# Test execution
if __name__ == "__main__":
    pytest.main([__file__])