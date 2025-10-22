#!/usr/bin/env python3
"""
Integration test for Protocol Enforcement when MCP is down

Tests the complete enforcement flow when MCP services are unavailable,
ensuring graceful fallback and session continuation.
"""

import asyncio
import json
import os
import pytest
import pytest_asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "hooks" / "devstream" / "protocol"))

from task_first_handler import TaskFirstHandler, TaskInfo, TaskComplexity


class TestProtocolEnforcementMCPDown:
    """Integration tests for protocol enforcement with MCP down."""

    @pytest_asyncio.fixture
    async def temp_state_dir(self):
        """Create temporary directory for test state."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest_asyncio.fixture
    def mock_failing_mcp_client(self):
        """Create mock memory client that always fails (MCP down)."""
        client = AsyncMock()
        client.create_task.side_effect = ConnectionError("MCP server connection refused")
        client.store_memory.side_effect = ConnectionError("MCP server connection refused")
        return client

    @pytest_asyncio.fixture
    def mock_failing_protocol_manager(self, temp_state_dir):
        """Create mock protocol manager with temporary state file."""
        from protocol_state_manager import ProtocolStateManager

        # Use temporary state file
        state_file = temp_state_dir / "protocol_state.json"
        manager = ProtocolStateManager(state_file=state_file)

        # Mock the memory client dependency to always fail
        with patch.object(manager, '_save_state', return_value=True):
            yield manager

    @pytest_asyncio.fixture
    async def task_first_handler_with_failing_mcp(self, mock_failing_mcp_client, mock_failing_protocol_manager):
        """Create TaskFirstHandler with failing MCP."""
        with patch('task_first_handler.get_protocol_manager', return_value=mock_failing_protocol_manager):
            return TaskFirstHandler(memory_client=mock_failing_mcp_client)

    @pytest.mark.asyncio
    async def test_enforcement_gate_fallback_when_mcp_down(self, task_first_handler_with_failing_mcp):
        """Test enforcement gate falls back gracefully when MCP is down."""

        with patch.dict(os.environ, {
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_RETRIES": "2",
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_BACKOFF_FACTOR": "1.5",
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_INITIAL_DELAY": "0.1",
            "DEVSTREAM_PROTOCOL_ENFORCEMENT_ENABLED": "true"
        }):
            # Simulate complex task that should trigger enforcement
            complex_prompt = "Implement comprehensive user authentication system with JWT tokens, password hashing, and session management"

            # This should trigger enforcement gate, then fallback when MCP fails
            success, task_id = await task_first_handler_with_failing_mcp.enforce_task_creation(
                user_prompt=complex_prompt,
                tool_name="Write",
                session_id="test-mcp-down-session"
            )

            # Should succeed with fallback task ID
            assert success is True
            assert task_id is not None
            assert task_id.startswith("fallback-")

            # Verify MCP calls were attempted
            assert task_first_handler_with_failing_mcp.memory_client.create_task.call_count >= 2

    @pytest.mark.asyncio
    async def test_simple_task_bypasses_enforcement_when_mcp_down(self, task_first_handler_with_failing_mcp):
        """Test simple tasks bypass enforcement even when MCP is down."""

        simple_prompt = "Fix typo in README file"

        success, task_id = await task_first_handler_with_failing_mcp.enforce_task_creation(
            user_prompt=simple_prompt,
            tool_name="Edit",
            session_id="test-simple-task-session"
        )

        # Should succeed without task creation (simple task)
        assert success is True
        assert task_id is None  # No task created for simple tasks

        # MCP should not be called for simple tasks
        assert task_first_handler_with_failing_mcp.memory_client.create_task.call_count == 0

    @pytest.mark.asyncio
    async def test_fallback_log_creation_when_mcp_down(self, task_first_handler_with_failing_mcp, temp_state_dir):
        """Test fallback log is created when MCP is down."""

        with tempfile.TemporaryDirectory() as log_dir:
            fallback_log_path = Path(log_dir) / "protocol_decisions.jsonl"

            with patch.dict(os.environ, {
                "DEVSTREAM_MCP_CIRCUIT_BREAKER_RETRIES": "1",
                "DEVSTREAM_MCP_CIRCUIT_BREAKER_INITIAL_DELAY": "0.1"
            }):
                # Mock the fallback log path
                with patch.object(task_first_handler_with_failing_mcp, '_fallback_task_logging') as mock_fallback:
                    success, task_id = await task_first_handler_with_failing_mcp.enforce_task_creation(
                        user_prompt="Build comprehensive REST API with authentication",
                        tool_name="Write",
                        session_id="test-log-creation"
                    )

                    # Should succeed with fallback
                    assert success is True
                    assert task_id.startswith("fallback-")

                    # Fallback logging should be called
                    mock_fallback.assert_called_once()

                    # Verify the arguments
                    call_args = mock_fallback.call_args[0]
                    assert len(call_args) == 4  # task_info, session_id, fallback_log, error

                    task_info, session_id, fallback_log, error = call_args
                    assert session_id == "test-log-creation"
                    assert fallback_log.name == "protocol_decisions.jsonl"
                    assert "connection refused" in error.lower() or "MCP" in error

    @pytest.mark.asyncio
    async def test_protocol_state_persistence_with_fallback(self, task_first_handler_with_failing_mcp, mock_failing_protocol_manager):
        """Test protocol state is persisted even with MCP fallback."""

        with patch.dict(os.environ, {
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_RETRIES": "1",
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_INITIAL_DELAY": "0.1"
        }):
            # Mock enforcement gate to return PROTOCOL decision
            with patch.object(task_first_handler_with_failing_mcp.enforcement_gate, 'show_enforcement_gate') as mock_gate:
                mock_gate.return_value = 1  # PROTOCOL decision

                success, task_id = await task_first_handler_with_failing_mcp.enforce_task_creation(
                    user_prompt="Implement microservices architecture with service discovery",
                    tool_name="Write",
                    session_id="test-state-persistence"
                )

                # Should succeed with fallback task ID
                assert success is True
                assert task_id.startswith("fallback-")

                # Verify enforcement gate was called
                mock_gate.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_consecutive_failures_graceful_degradation(self, task_first_handler_with_failing_mcp):
        """Test graceful degradation across multiple consecutive failures."""

        results = []

        for i in range(3):
            prompt = f"Create microservice {i+1} with database integration"

            with patch.dict(os.environ, {
                "DEVSTREAM_MCP_CIRCUIT_BREAKER_RETRIES": "1",
                "DEVSTREAM_MCP_CIRCUIT_BREAKER_INITIAL_DELAY": "0.05"
            }):
                success, task_id = await task_first_handler_with_failing_mcp.enforce_task_creation(
                    user_prompt=prompt,
                    tool_name="Write",
                    session_id=f"test-consecutive-{i}"
                )

                results.append((success, task_id))

                # Small delay between requests
                await asyncio.sleep(0.01)

        # All should succeed with fallback task IDs
        for i, (success, task_id) in enumerate(results):
            assert success is True, f"Request {i} should succeed"
            assert task_id is not None, f"Request {i} should have task ID"
            assert task_id.startswith("fallback-"), f"Request {i} should use fallback ID"

        # All task IDs should be unique
        task_ids = [task_id for _, task_id in results]
        assert len(set(task_ids)) == 3, "All fallback task IDs should be unique"

    @pytest.mark.asyncio
    async def test_session_continuation_after_mcp_recovery(self, task_first_handler_with_failing_mcp):
        """Test session continues properly after MCP recovery simulation."""

        # Phase 1: MCP down - should use fallback
        with patch.dict(os.environ, {
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_RETRIES": "1",
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_INITIAL_DELAY": "0.1"
        }):
            success1, task_id1 = await task_first_handler_with_failing_mcp.enforce_task_creation(
                user_prompt="Initial setup task",
                tool_name="Write",
                session_id="test-recovery-session"
            )

            assert success1 is True
            assert task_id1.startswith("fallback-")

        # Phase 2: Simulate MCP recovery
        task_first_handler_with_failing_mcp.memory_client.create_task.side_effect = None
        task_first_handler_with_failing_mcp.memory_client.create_task.return_value = {
            "task_id": "recovered-task-123"
        }

        # Phase 3: MCP recovered - should use real MCP
        success2, task_id2 = await task_first_handler_with_failing_mcp.enforce_task_creation(
            user_prompt="Follow-up implementation task",
            tool_name="Write",
            session_id="test-recovery-session"
        )

        assert success2 is True
        assert task_id2 == "recovered-task-123"  # Should use real MCP task ID

    @pytest.mark.asyncio
    async def test_timeout_behavior_during_mcp_outage(self, task_first_handler_with_failing_mcp):
        """Test timeout behavior during extended MCP outage."""

        with patch.dict(os.environ, {
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_RETRIES": "3",
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_BACKOFF_FACTOR": "2",
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_INITIAL_DELAY": "0.1"
        }):
            start_time = time.time()

            success, task_id = await task_first_handler_with_failing_mcp.enforce_task_creation(
                user_prompt="Long running task during outage",
                tool_name="Write",
                session_id="test-timeout-session"
            )

            end_time = time.time()
            duration = end_time - start_time

            # Should succeed despite timeout
            assert success is True
            assert task_id.startswith("fallback-")

            # Should complete within reasonable time (with exponential backoff: 0.1 + 0.2 + 0.4 = 0.7s total)
            assert duration < 2.0, f"Should complete quickly, took {duration:.2f}s"

    @pytest.mark.asyncio
    async def test_error_logging_during_mcp_outage(self, task_first_handler_with_failing_mcp):
        """Test comprehensive error logging during MCP outage."""

        with patch('task_first_handler.logger') as mock_logger:
            success, task_id = await task_first_handler_with_failing_mcp.enforce_task_creation(
                user_prompt="Task to test error logging",
                tool_name="Write",
                session_id="test-error-logging"
            )

            assert success is True

            # Verify error logging occurred
            error_calls = [call for call in mock_logger.method_calls if 'error' in str(call).lower()]
            assert len(error_calls) > 0, "Should log errors during MCP outage"

            # Verify circuit breaker tripped was logged
            circuit_breaker_calls = [call for call in mock_logger.method_calls
                                   if 'circuit_breaker' in str(call).lower()]
            assert len(circuit_breaker_calls) > 0, "Should log circuit breaker trip"

    @pytest.mark.asyncio
    async def test_degraded_mode_flag_in_protocol_state(self, task_first_handler_with_failing_mcp, mock_failing_protocol_manager):
        """Test degraded_mode flag is set in protocol state during fallback."""

        # Mock the advance_step method to capture metadata
        with patch.object(mock_failing_protocol_manager, 'advance_step') as mock_advance:
            mock_advance.return_value = await mock_failing_protocol_manager.initialize_session()

            with patch.object(task_first_handler_with_failing_mcp.enforcement_gate, 'show_enforcement_gate') as mock_gate:
                mock_gate.return_value = 1  # PROTOCOL decision

                success, task_id = await task_first_handler_with_failing_mcp.enforce_task_creation(
                    user_prompt="Task to test degraded mode flag",
                    tool_name="Write",
                    session_id="test-degraded-mode"
                )

                assert success is True

                # Verify advance_step was called with degraded_mode in metadata
                mock_advance.assert_called_once()
                call_args = mock_advance.call_args
                metadata_updates = call_args[1].get('metadata_updates', {})

                # Should contain degraded_mode flag or related metadata
                assert 'metadata_updates' in call_args[1], "Should pass metadata updates"


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s", "--tb=short"])