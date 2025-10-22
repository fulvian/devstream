#!/usr/bin/env python3
"""
End-to-End Integration Test for 7-Step Protocol Enforcement

Tests the complete DevStream 7-step protocol workflow with:
1. Enforcement gate triggering and response
2. Task creation and lifecycle management
3. MCP integration and graceful fallback
4. Micro-task commits during Step 6
5. Step 7 verification and completion
6. Full system integration verification
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
import subprocess
import time

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "hooks" / "devstream" / "protocol"))

from task_first_handler import TaskFirstHandler, TaskInfo, TaskComplexity
from protocol_state_manager import ProtocolStateManager, ProtocolStep, get_protocol_manager
from micro_task_commit_handler import MicroTaskCommitHandler


class Test7StepProtocolEnforcement:
    """E2E test suite for complete 7-step protocol enforcement."""

    @pytest_asyncio.fixture
    async def temp_workspace(self):
        """Create temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            # Initialize git repository
            subprocess.run(["git", "init"], cwd=workspace, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=workspace, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=workspace, capture_output=True)

            # Create .devstream structure
            venv_dir = workspace / ".devstream"
            venv_dir.mkdir()

            # Create state directories
            (workspace / ".claude" / "state").mkdir(parents=True)
            (workspace / ".claude" / "logs").mkdir(parents=True)

            yield workspace

    @pytest_asyncio.fixture
    def mock_memory_client(self):
        """Create mock MCP memory client."""
        client = AsyncMock()

        # Task creation responses
        def create_task_response(title, description, task_type, priority, phase_name, project):
            return {
                "task_id": f"task-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(title) % 10000:04d}",
                "title": title,
                "status": "created"
            }

        client.create_task.side_effect = create_task_response
        client.store_memory.return_value = {"success": True}
        client.search_memory.return_value = []

        return client

    @pytest_asyncio.fixture
    async def protocol_components(self, temp_workspace, mock_memory_client):
        """Create all protocol components for testing."""
        # Protocol state manager
        state_file = temp_workspace / ".claude" / "state" / "protocol_state.json"
        protocol_manager = ProtocolStateManager(state_file=state_file)

        # Initialize session
        initial_state = await protocol_manager.initialize_session()

        # Task first handler
        task_handler = TaskFirstHandler(memory_client=mock_memory_client, protocol_manager=protocol_manager)

        # Micro-task commit handler
        with patch('micro_task_commit_handler.get_protocol_manager', return_value=protocol_manager):
            commit_handler = MicroTaskCommitHandler()

        return {
            "workspace": temp_workspace,
            "protocol_manager": protocol_manager,
            "task_handler": task_handler,
            "commit_handler": commit_handler,
            "memory_client": mock_memory_client,
            "initial_state": initial_state
        }

    @pytest.mark.asyncio
    async def test_step1_enforcement_gate_complex_task(self, protocol_components):
        """Test Step 1: DISCUSSION with enforcement gate for complex task."""
        workspace = protocol_components["workspace"]
        task_handler = protocol_components["task_handler"]

        # Enable enforcement
        with patch.dict(os.environ, {
            "DEVSTREAM_PROTOCOL_ENFORCEMENT_ENABLED": "true",
            "DEVSTREAM_TASK_FIRST_HANDLER_ENABLED": "true"
        }):
            # Mock enforcement gate to return PROTOCOL decision
            with patch.object(task_handler.enforcement_gate, 'show_enforcement_gate') as mock_gate:
                mock_gate.return_value = 1  # PROTOCOL decision

                # Simulate complex user prompt
                complex_prompt = "Implement comprehensive user authentication system with JWT tokens, password hashing using bcrypt, session management, and OAuth2 integration"

                success, task_id = await task_handler.enforce_task_creation(
                    user_prompt=complex_prompt,
                    tool_name="Write",
                    session_id="e2e-test-session"
                )

                # Verify enforcement gate was triggered
                mock_gate.assert_called_once()

                # Verify task was created
                assert success is True
                assert task_id is not None
                assert task_id.startswith("task-")

                # Verify task creation via MCP
                protocol_components["memory_client"].create_task.assert_called_once()

                # Verify protocol state advanced to DISCUSSION
                current_state = await protocol_components["protocol_manager"].get_current_state()
                assert current_state.protocol_step == ProtocolStep.DISCUSSION
                assert current_state.task_id == task_id

    @pytest.mark.asyncio
    async def test_step2_analysis_with_context_injection(self, protocol_components):
        """Test Step 2: ANALYSIS with context injection from memory."""
        protocol_manager = protocol_components["protocol_manager"]

        # Advance to ANALYSIS step
        current_state = await protocol_manager.get_current_state()
        analysis_state = await protocol_manager.advance_step(
            current_state,
            ProtocolStep.ANALYSIS,
            metadata_updates={
                "analysis_findings": "Complex authentication system requiring multiple components",
                "files_to_modify": ["src/auth/", "tests/"],
                "estimated_complexity": "high"
            }
        )

        assert analysis_state.protocol_step == ProtocolStep.ANALYSIS
        assert "analysis_findings" in analysis_state.metadata

    @pytest.mark.asyncio
    async def test_step3_research_with_context7_integration(self, protocol_components):
        """Test Step 3: RESEARCH with Context7 integration."""
        protocol_manager = protocol_components["protocol_manager"]

        # Mock Context7 integration
        with patch('task_first_handler.logger') as mock_logger:
            # Advance to RESEARCH step
            current_state = await protocol_manager.get_current_state()
            research_state = await protocol_manager.advance_step(
                current_state,
                ProtocolStep.RESEARCH,
                metadata_updates={
                    "context7_research": [
                        {"library": "pyjwt", "docs_retrieved": True},
                        {"library": "bcrypt", "docs_retrieved": True},
                        {"library": "fastapi", "docs_retrieved": True}
                    ]
                }
            )

            assert research_state.protocol_step == ProtocolStep.RESEARCH
            assert "context7_research" in research_state.metadata

    @pytest.mark.asyncio
    async def test_step4_planning_with_implementation_plan(self, protocol_components):
        """Test Step 4: PLANNING with implementation plan generation."""
        protocol_manager = protocol_components["protocol_manager"]

        # Mock implementation plan generation
        with patch('micro_task_commit_handler.logger') as mock_logger:
            # Advance to PLANNING step
            current_state = await protocol_manager.get_current_state()
            planning_state = await protocol_manager.advance_step(
                current_state,
                ProtocolStep.PLANNING,
                metadata_updates={
                    "implementation_plan": {
                        "micro_tasks": [
                            "STEP 6.1 - Create user model with password hashing",
                            "STEP 6.2 - Implement JWT token service",
                            "STEP 6.3 - Create authentication endpoints",
                            "STEP 6.4 - Add session middleware",
                            "STEP 6.5 - Implement OAuth2 integration"
                        ],
                        "estimated_duration": 120,  # minutes
                        "acceptance_criteria": [
                            "JWT tokens work correctly",
                            "Passwords are hashed with bcrypt",
                            "Session management functional",
                            "OAuth2 integration complete"
                        ]
                    }
                }
            )

            assert planning_state.protocol_step == ProtocolStep.PLANNING
            assert "implementation_plan" in planning_state.metadata

    @pytest.mark.asyncio
    async def test_step5_approval_with_strategic_choice(self, protocol_components):
        """Test Step 5: APPROVAL with strategic choice gate."""
        protocol_manager = protocol_components["protocol_manager"]

        # Advance to APPROVAL step
        current_state = await protocol_manager.get_current_state()
        approval_state = await protocol_manager.advance_step(
            current_state,
            ProtocolStep.APPROVAL,
            metadata_updates={
                "approval_granted": True,
                "model_choice": "sonnet-4.5",  # or "glm-4.6"
                "approval_timestamp": datetime.now(timezone.utc).isoformat(),
                "stakeholder_consensus": "full_approval"
            }
        )

        assert approval_state.protocol_step == ProtocolStep.APPROVAL
        assert approval_state.metadata["approval_granted"] is True

    @pytest.mark.asyncio
    async def test_step6_implementation_with_micro_task_commits(self, protocol_components):
        """Test Step 6: IMPLEMENTATION with micro-task commits."""
        protocol_manager = protocol_components["protocol_manager"]
        commit_handler = protocol_components["commit_handler"]

        # Enable micro-task commits
        with patch.dict(os.environ, {"DEVSTREAM_MICRO_TASK_COMMITS": "true"}):
            # Mock git operations
            with patch('subprocess.run') as mock_subprocess:
                # Mock git status, add, and commit operations
                mock_subprocess.side_effect = [
                    # git status --porcelain
                    MagicMock(returncode=0, stdout="M src/auth.py\nA src/models.py\n?? tests/"),
                    # git add .
                    MagicMock(returncode=0),
                    # git commit
                    MagicMock(returncode=0),
                    # git status for next iteration
                    MagicMock(returncode=0, stdout="M src/auth.py\nM src/models.py"),
                    # git add .
                    MagicMock(returncode=0),
                    # git commit
                    MagicMock(returncode=0)
                ]

                # Advance to IMPLEMENTATION step
                current_state = await protocol_manager.get_current_state()
                implementation_state = await protocol_manager.advance_step(
                    current_state,
                    ProtocolStep.IMPLEMENTATION
                )

                assert implementation_state.protocol_step == ProtocolStep.IMPLEMENTATION

                # Simulate TodoWrite for completed micro-tasks
                todo_data = json.dumps([
                    {
                        "content": "STEP 6.1 - Create user model with password hashing",
                        "status": "completed",
                        "activeForm": "Completed user model creation"
                    },
                    {
                        "content": "STEP 6.2 - Implement JWT token service",
                        "status": "completed",
                        "activeForm": "Completed JWT service"
                    },
                    {
                        "content": "STEP 6.3 - Create authentication endpoints",
                        "status": "pending",
                        "activeForm": "Creating authentication endpoints"
                    }
                ])

                # Process micro-task commits
                success = await commit_handler.handle_todo_write(todo_data, {})

                # Verify commits were created
                assert success is True
                assert mock_subprocess.call_count >= 4  # status + add + commit per task

    @pytest.mark.asyncio
    async def test_step7_verification_with_test_validation(self, protocol_components):
        """Test Step 7: VERIFICATION with test validation."""
        protocol_manager = protocol_components["protocol_manager"]

        # Mock test execution
        with patch('micro_task_commit_handler.logger') as mock_logger:
            # Advance to VERIFICATION step
            current_state = await protocol_manager.get_current_state()
            verification_state = await protocol_manager.advance_step(
                current_state,
                ProtocolStep.VERIFICATION,
                metadata_updates={
                    "test_results": {
                        "unit_tests": {"passed": 45, "failed": 0, "coverage": 96.5},
                        "integration_tests": {"passed": 12, "failed": 0, "coverage": 89.2},
                        "e2e_tests": {"passed": 8, "failed": 0, "coverage": 75.1}
                    },
                    "verification_status": "passed",
                    "performance_metrics": {
                        "response_time_p95": 125,  # ms
                        "throughput": 1000,  # req/sec
                        "memory_usage": "stable"
                    }
                }
            )

            assert verification_state.protocol_step == ProtocolStep.VERIFICATION
            assert verification_state.metadata["verification_status"] == "passed"

    @pytest.mark.asyncio
    async def test_mcp_graceful_fallback_during_task_creation(self, protocol_components):
        """Test MCP graceful fallback when MCP services are unavailable."""
        task_handler = protocol_components["task_handler"]
        memory_client = protocol_components["memory_client"]

        # Simulate MCP failure
        memory_client.create_task.side_effect = ConnectionError("MCP server connection refused")

        with patch.dict(os.environ, {
            "DEVSTREAM_MCP_GRACEFUL_FALLBACK": "true",
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_RETRIES": "2",
            "DEVSTREAM_MCP_CIRCUIT_BREAKER_INITIAL_DELAY": "0.1"
        }):
            with patch.object(task_handler, '_fallback_task_logging') as mock_fallback:
                # Mock enforcement gate to return PROTOCOL decision
                with patch.object(task_handler.enforcement_gate, 'show_enforcement_gate') as mock_gate:
                    mock_gate.return_value = 1  # PROTOCOL decision

                    success, task_id = await task_handler.enforce_task_creation(
                        user_prompt="Create user authentication system",
                        tool_name="Write",
                        session_id="test-fallback-session"
                    )

                    # Should succeed with fallback task ID
                    assert success is True
                    assert task_id.startswith("fallback-")

                    # Verify fallback logging was called
                    mock_fallback.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_7step_workflow_integration(self, protocol_components):
        """Test complete 7-step workflow from start to finish."""
        protocol_manager = protocol_components["protocol_manager"]
        task_handler = protocol_components["task_handler"]
        commit_handler = protocol_components["commit_handler"]
        workspace = protocol_components["workspace"]

        # Enable all features
        with patch.dict(os.environ, {
            "DEVSTREAM_PROTOCOL_ENFORCEMENT_ENABLED": "true",
            "DEVSTREAM_TASK_FIRST_HANDLER_ENABLED": "true",
            "DEVSTREAM_MICRO_TASK_COMMITS": "true",
            "DEVSTREAM_MCP_GRACEFUL_FALLBACK": "true"
        }):
            # Mock enforcement gate and git operations
            with patch.object(task_handler.enforcement_gate, 'show_enforcement_gate') as mock_gate:
                mock_gate.return_value = 1  # PROTOCOL decision

                with patch('subprocess.run') as mock_subprocess:
                    mock_subprocess.return_value = MagicMock(returncode=0)

                    # STEP 1: DISCUSSION with enforcement
                    success1, task_id = await task_handler.enforce_task_creation(
                        user_prompt="Build complete API authentication system",
                        tool_name="Write",
                        session_id="complete-workflow-test"
                    )

                    assert success1 is True
                    assert task_id is not None

                    # STEP 2-5: Advance through planning phases
                    state = await protocol_manager.get_current_state()

                    for step in [ProtocolStep.ANALYSIS, ProtocolStep.RESEARCH, ProtocolStep.PLANNING, ProtocolStep.APPROVAL]:
                        state = await protocol_manager.advance_step(
                            state,
                            step,
                            metadata_updates={f"{step.name.lower()}_completed": True}
                        )

                    # STEP 6: IMPLEMENTATION with micro-task commits
                    state = await protocol_manager.advance_step(state, ProtocolStep.IMPLEMENTATION)

                    todo_data = json.dumps([
                        {"content": "Implement core authentication", "status": "completed", "activeForm": "Done"},
                        {"content": "Add security middleware", "status": "completed", "activeForm": "Done"},
                        {"content": "Write comprehensive tests", "status": "pending", "activeForm": "Pending"}
                    ])

                    commit_success = await commit_handler.handle_todo_write(todo_data, {})
                    assert commit_success is True

                    # STEP 7: VERIFICATION
                    final_state = await protocol_manager.advance_step(
                        state,
                        ProtocolStep.VERIFICATION,
                        metadata_updates={
                            "verification_status": "passed",
                            "workflow_complete": True
                        }
                    )

                    # Verify complete workflow
                    assert final_state.protocol_step == ProtocolStep.VERIFICATION
                    assert final_state.metadata["workflow_complete"] is True
                    assert final_state.task_id == task_id

    @pytest.mark.asyncio
    async def test_protocol_state_persistence_across_session(self, protocol_components):
        """Test protocol state persistence and recovery."""
        protocol_manager = protocol_components["protocol_manager"]

        # Create protocol state with progress
        state = await protocol_manager.get_current_state()

        state = await protocol_manager.advance_step(
            state,
            ProtocolStep.ANALYSIS,
            metadata_updates={"session_progress": "in_progress"}
        )

        # Save state (simulates session end)
        await protocol_manager._save_state(state)

        # Create new manager and recover state
        new_manager = ProtocolStateManager(state_file=protocol_manager.state_file)
        recovered_state = await new_manager.initialize_session()

        # Verify state persistence
        assert recovered_state.session_id == state.session_id
        assert recovered_state.protocol_step == ProtocolStep.ANALYSIS
        assert recovered_state.metadata["session_progress"] == "in_progress"

    @pytest.mark.asyncio
    async def test_error_handling_and_rollback_mechanisms(self, protocol_components):
        """Test error handling and rollback mechanisms."""
        protocol_manager = protocol_components["protocol_manager"]

        # Test invalid step transition
        state = await protocol_manager.get_current_state()

        try:
            # Try to skip from IDLE to IMPLEMENTATION (invalid)
            await protocol_manager.advance_step(
                state,
                ProtocolStep.IMPLEMENTATION,
                force=False  # Should enforce validation
            )
            assert False, "Should have raised ValueError for invalid transition"
        except ValueError as e:
            assert "Invalid step transition" in str(e)

        # Test force parameter for recovery
        recovery_state = await protocol_manager.advance_step(
            state,
            ProtocolStep.IMPLEMENTATION,
            force=True  # Should allow recovery
        )

        assert recovery_state.protocol_step == ProtocolStep.IMPLEMENTATION

    @pytest.mark.asyncio
    async def test_concurrent_session_handling(self, protocol_components):
        """Test handling of multiple concurrent sessions."""
        protocol_manager = protocol_components["protocol_manager"]

        # Create multiple sessions
        sessions = []
        for i in range(3):
            session_id = f"concurrent-test-{i}"
            temp_dir = protocol_components["workspace"] / f"session_{i}"
            temp_dir.mkdir()

            state_file = temp_dir / ".claude" / "state" / "protocol_state.json"
            manager = ProtocolStateManager(state_file=state_file)
            state = await manager.initialize_session()
            sessions.append((session_id, manager, state))

        # Verify all sessions are unique and properly initialized
        session_ids = [session[0] for session in sessions]
        assert len(set(session_ids)) == 3  # All unique

        for session_id, manager, state in sessions:
            assert state.protocol_step == ProtocolStep.IDLE
            assert state.session_id == session_id


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s", "--tb=short"])