#!/usr/bin/env python3
"""
Unit tests for MCP Graceful Fallback functionality

Tests the circuit breaker pattern, exponential backoff, and degraded mode
functionality when MCP services are unavailable.
"""

import asyncio
import json
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import tempfile
import os

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".claude" / "hooks" / "devstream" / "protocol"))

from task_first_handler import (
    TaskFirstHandler,
    TaskInfo,
    TaskComplexity
)


class TestMCPGracefulFallback:
    """Test suite for MCP graceful fallback functionality."""

    @pytest_asyncio.fixture
    async def mock_memory_client(self):
        """Create mock memory client that simulates MCP failures."""
        client = AsyncMock()

        # Simulate MCP failure on first attempts, success on retry
        call_count = 0

        async def failing_create_task(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first 2 attempts
                raise ConnectionError("MCP server unavailable")
            return {"task_id": f"success-task-{call_count}"}

        client.create_task.side_effect = failing_create_task
        return client

    @pytest_asyncio.fixture
    async def task_first_handler(self, mock_memory_client):
        """Create TaskFirstHandler with mock memory client."""
        return TaskFirstHandler(memory_client=mock_memory_client)

    @pytest_asyncio.fixture
    def sample_task_info(self):
        """Create sample task info for testing."""
        return TaskInfo(
            title="Implement JWT authentication",
            description="Add JWT authentication with password hashing",
            task_type="coding",
            priority=8,
            estimated_duration=45,
            complexity=TaskComplexity.COMPLEX,
            involves_code=True,
            involves_architecture=True,
            requires_context7=True,
            file_count=3,
            trigger_reasons=["Duration > 15min", "Code implementation required"],
            acceptance_criteria=["JWT tokens implemented", "Password hashing added"]
        )

    @pytest.mark.asyncio
    async def test_circuit_breaker_success_on_retry(self, task_first_handler, sample_task_info):
        """Test circuit breaker succeeds after retry attempts."""

        with patch.dict(os.environ, {
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_RETRIES": "3",
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_BACKOFF_FACTOR": "2",
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_INITIAL_DELAY": "0.1"  # Fast for testing
        }):
            task_id = await task_first_handler._create_task(
                sample_task_info,
                "test-session-123"
            )

            # Should succeed on 3rd attempt
            assert task_id is not None
            assert task_id.startswith("success-task-3")

            # Verify retry attempts were made
            assert task_first_handler.memory_client.create_task.call_count == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_fallback_after_max_retries(self, task_first_handler, sample_task_info):
        """Test fallback behavior when all retry attempts fail."""

        # Configure mock to always fail
        task_first_handler.memory_client.create_task.side_effect = ConnectionError("MCP server down")

        with patch.dict(os.environ, {
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_RETRIES": "2",
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_BACKOFF_FACTOR": "2",
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_INITIAL_DELAY": "0.1"
        }):
            with tempfile.TemporaryDirectory() as temp_dir:
                # Mock fallback log path
                fallback_log = Path(temp_dir) / "protocol_decisions.jsonl"

                with patch.object(task_first_handler, '_fallback_task_logging') as mock_fallback:
                    task_id = await task_first_handler._create_task(
                        sample_task_info,
                        "test-session-456"
                    )

                    # Should return fallback task ID
                    assert task_id is not None
                    assert task_id.startswith("fallback-")

                    # Verify fallback logging was called
                    mock_fallback.assert_called_once()

                    # Verify all retry attempts were made
                    assert task_first_handler.memory_client.create_task.call_count == 2

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self, task_first_handler, sample_task_info):
        """Test exponential backoff delays are correctly applied."""

        # Configure mock to always fail
        task_first_handler.memory_client.create_task.side_effect = ConnectionError("MCP server down")

        with patch.dict(os.environ, {
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_RETRIES": "3",
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_BACKOFF_FACTOR": "2",
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_INITIAL_DELAY": "0.1"
        }):
            start_time = datetime.now()

            await task_first_handler._create_task(
                sample_task_info,
                "test-session-timing"
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Should have delays: 0.1s (after 1st fail) + 0.2s (after 2nd fail)
            # Total should be at least 0.3 seconds plus processing time
            assert duration >= 0.25  # Allow some tolerance for processing time

    @pytest.mark.asyncio
    async def test_fallback_logging_structure(self, task_first_handler, sample_task_info):
        """Test fallback logging creates proper JSONL structure."""

        with tempfile.TemporaryDirectory() as temp_dir:
            fallback_log = Path(temp_dir) / "protocol_decisions.jsonl"

            await task_first_handler._fallback_task_logging(
                sample_task_info,
                "test-session-log",
                fallback_log,
                "MCP connection timeout"
            )

            # Verify log file was created
            assert fallback_log.exists()

            # Read and verify log entry
            log_content = fallback_log.read_text().strip()
            log_entry = json.loads(log_content)

            # Verify structure
            assert log_entry["event"] == "task_creation_fallback"
            assert log_entry["session_id"] == "test-session-log"
            assert log_entry["mcp_error"] == "MCP connection timeout"
            assert log_entry["fallback_reason"] == "MCP circuit breaker tripped"
            assert log_entry["degraded_mode"] is True

            # Verify task info structure
            task_info = log_entry["task_info"]
            assert task_info["title"] == sample_task_info.title
            assert task_info["task_type"] == sample_task_info.task_type
            assert task_info["complexity"] == sample_task_info.complexity.value

            # Verify timestamp format
            timestamp = datetime.fromisoformat(log_entry["timestamp"])
            assert isinstance(timestamp, datetime)

    @pytest.mark.asyncio
    async def test_environment_variable_defaults(self, task_first_handler, sample_task_info):
        """Test environment variable defaults are used when not set."""

        # Clear relevant environment variables
        env_vars_to_clear = [
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_RETRIES",
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_BACKOFF_FACTOR",
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_INITIAL_DELAY"
        ]

        original_values = {}
        for var in env_vars_to_clear:
            original_values[var] = os.environ.pop(var, None)

        try:
            # Configure mock to always fail
            task_first_handler.memory_client.create_task.side_effect = ConnectionError("MCP server down")

            with patch.object(task_first_handler, '_fallback_task_logging') as mock_fallback:
                await task_first_handler._create_task(
                    sample_task_info,
                    "test-session-defaults"
                )

                # Should use default values: 3 retries, factor 2, delay 1s
                assert task_first_handler.memory_client.create_task.call_count == 3
                mock_fallback.assert_called_once()

        finally:
            # Restore original environment values
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value

    @pytest.mark.asyncio
    async def test_fallback_task_id_generation(self, task_first_handler, sample_task_info):
        """Test fallback task IDs are unique and properly formatted."""

        # Configure mock to always fail
        task_first_handler.memory_client.create_task.side_effect = ConnectionError("MCP server down")

        task_ids = []

        # Create multiple fallback tasks
        for i in range(3):
            task_id = await task_first_handler._create_task(
                sample_task_info,
                f"test-session-{i}"
            )
            task_ids.append(task_id)

            # Small delay to ensure different timestamps
            await asyncio.sleep(0.01)

        # Verify all task IDs are unique
        assert len(set(task_ids)) == 3

        # Verify format: fallback-YYYYMMDD-HHMMSS-8hexchars
        for task_id in task_ids:
            assert task_id.startswith("fallback-")
            parts = task_id.split("-")
            assert len(parts) == 4  # ["fallback", "YYYYMMDD", "HHMMSS", "8hexchars"]
            assert len(parts[1]) == 8  # YYYYMMDD format
            assert len(parts[2]) == 6  # HHMMSS format
            assert len(parts[3]) == 8   # 8 hex characters

    @pytest.mark.asyncio
    async def test_mcp_partial_failure_handling(self, task_first_handler, sample_task_info):
        """Test handling of MCP returning None or invalid results."""

        # Configure mock to return invalid results
        task_first_handler.memory_client.create_task.return_value = None

        with patch.dict(os.environ, {
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_RETRIES": "2",
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_BACKOFF_FACTOR": "2",
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_INITIAL_DELAY": "0.1"
        }):
            with patch.object(task_first_handler, '_fallback_task_logging') as mock_fallback:
                task_id = await task_first_handler._create_task(
                    sample_task_info,
                    "test-session-partial-failure"
                )

                # Should fallback when MCP returns None
                assert task_id is not None
                assert task_id.startswith("fallback-")
                mock_fallback.assert_called_once()

    @pytest.mark.asyncio
    async def test_logging_during_retry_attempts(self, task_first_handler, sample_task_info):
        """Test appropriate logging during retry attempts."""

        # Configure mock to fail twice, then succeed
        call_count = 0

        async def failing_create_task(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError(f"MCP error {call_count}")
            return {"task_id": "success-after-retries"}

        task_first_handler.memory_client.create_task.side_effect = failing_create_task

        # Capture log messages
        with patch('task_first_handler.logger') as mock_logger:
            task_id = await task_first_handler._create_task(
                sample_task_info,
                "test-session-logging"
            )

            # Verify success
            assert task_id == "success-after-retries"

            # Verify retry warnings were logged
            warning_calls = [call for call in mock_logger.warning.call_args_list
                           if "mcp_task_creation_attempt_failed" in str(call)]
            assert len(warning_calls) == 2

            # Verify backoff info was logged
            info_calls = [call for call in mock_logger.info.call_args_list
                         if "mcp_circuit_backoff" in str(call)]
            assert len(info_calls) == 2

    @pytest.mark.asyncio
    async def test_fallback_log_directory_creation(self, task_first_handler, sample_task_info):
        """Test that fallback log directory is created when it doesn't exist."""

        # Use a non-existent directory
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_dir = Path(temp_dir) / "nonexistent" / "logs"
            fallback_log = nonexistent_dir / "protocol_decisions.jsonl"

            # Directory should not exist initially
            assert not nonexistent_dir.exists()

            await task_first_handler._fallback_task_logging(
                sample_task_info,
                "test-session-dir-creation",
                fallback_log,
                "Test error"
            )

            # Directory should be created
            assert nonexistent_dir.exists()
            assert fallback_log.exists()

            # Verify log content
            log_content = fallback_log.read_text()
            log_entry = json.loads(log_content.strip())
            assert log_entry["session_id"] == "test-session-dir-creation"


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short"])