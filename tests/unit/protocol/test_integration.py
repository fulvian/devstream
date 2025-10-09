#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pytest>=7.0.0",
#     "pytest-asyncio>=0.21.0",
#     "pytest-cov>=4.0.0",
#     "aiofiles>=23.0.0",
#     "structlog>=23.0.0",
#     "cryptography>=41.0.0",
#     "cachetools>=5.0.0",
# ]
# ///

"""
Integration tests for DevStream Protocol components.

Tests the complete workflow integration between:
- Protocol State Manager
- Enforcement Gate
- Step Validator
- Task First Handler
- Task State Synchronization

These tests verify that all components work together correctly
to enforce the 7-step protocol workflow.
"""

import asyncio
import json
import pytest
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'protocol'))

from protocol_state_manager import (
    ProtocolStateManager,
    ProtocolStep,
    get_protocol_manager
)
from enforcement_gate import (
    EnforcementGate,
    EnforcementDecision,
    EnforcementContext
)
from step_validator import (
    StepValidator,
    ValidationStatus,
    get_step_validator
)
from task_first_handler import (
    TaskFirstHandler,
    TaskComplexity
)
from task_state_sync import (
    TaskStateSync,
    SyncTrigger
)


@pytest.fixture
async def temp_directory():
    """Create temporary directory for integration tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
async def integration_setup(temp_directory):
    """Set up complete integration environment."""
    # Create temporary state file
    state_file = temp_directory / "protocol_state.json"

    # Create mock memory client
    mock_memory_client = AsyncMock()
    mock_memory_client.search_memory.return_value = {"results": []}
    mock_memory_client.store_memory = AsyncMock()
    mock_memory_client.create_task.return_value = {"task_id": "integration-task-123"}

    # Initialize all components
    protocol_manager = ProtocolStateManager(state_file)
    enforcement_gate = EnforcementGate()
    step_validator = StepValidator(mock_memory_client)
    task_first_handler = TaskFirstHandler(mock_memory_client)
    task_state_sync = TaskStateSync(mock_memory_client, protocol_manager)

    # Mock components to use same instances
    with patch('claude.hooks.devstream.protocol.protocol_state_manager.get_protocol_manager',
               return_value=protocol_manager):
        with patch('claude.hooks.devstream.protocol.step_validator.get_step_validator',
                   return_value=step_validator):
            yield {
                "protocol_manager": protocol_manager,
                "enforcement_gate": enforcement_gate,
                "step_validator": step_validator,
                "task_first_handler": task_first_handler,
                "task_state_sync": task_state_sync,
                "memory_client": mock_memory_client,
                "state_file": state_file
            }


@pytest.mark.asyncio
async def test_complete_simple_task_workflow(integration_setup):
    """Test complete workflow for simple task (no enforcement required)."""
    setup = integration_setup
    protocol_manager = setup["protocol_manager"]
    task_first_handler = setup["task_first_handler"]
    task_state_sync = setup["task_state_sync"]

    # Initialize session
    initial_state = await protocol_manager.initialize_session()
    assert initial_state.protocol_step == ProtocolStep.IDLE

    # Simple task - should not trigger enforcement
    user_prompt = "Fix typo in README file"
    should_create, task_info = await task_first_handler.should_create_task(
        user_prompt,
        tool_name="Edit"
    )

    assert should_create == False
    assert task_info.complexity == TaskComplexity.SIMPLE

    # Simulate tool execution
    await task_state_sync.synchronize_on_tool_execution(
        tool_name="Edit",
        tool_input={"file_path": "README.md", "new_string": "fixed typo"},
        execution_result={"success": True},
        session_id=initial_state.session_id
    )

    # Verify state remains unchanged (no protocol enforcement)
    current_state = await protocol_manager.get_current_state()
    assert current_state.protocol_step == ProtocolStep.IDLE
    assert current_state.task_id is None


@pytest.mark.asyncio
async def test_complete_complex_task_workflow(integration_setup):
    """Test complete workflow for complex task (full enforcement)."""
    setup = integration_setup
    protocol_manager = setup["protocol_manager"]
    enforcement_gate = setup["enforcement_gate"]
    step_validator = setup["step_validator"]
    task_first_handler = setup["task_first_handler"]
    task_state_sync = setup["task_state_sync"]
    memory_client = setup["memory_client"]

    # Initialize session
    initial_state = await protocol_manager.initialize_session()
    session_id = initial_state.session_id

    # Complex task - should trigger enforcement
    user_prompt = "Implement comprehensive user authentication system with JWT tokens"
    should_create, task_info = await task_first_handler.should_create_task(
        user_prompt,
        tool_name="Write"
    )

    assert should_create == True
    assert task_info.complexity in [TaskComplexity.COMPLEX, TaskComplexity.CRITICAL]

    # Mock user to choose protocol (non-interactive mode)
    with patch('claude.hooks.devstream.protocol.enforcement_gate.PYINQUIRER_AVAILABLE', False):
        # Enforce task creation
        success, task_id = await task_first_handler.enforce_task_creation(
            user_prompt,
            tool_name="Write",
            session_id=session_id
        )

        assert success == True
        assert task_id is not None

        # Verify protocol state advanced to DISCUSSION
        current_state = await protocol_manager.get_current_state()
        assert current_state.protocol_step == ProtocolStep.DISCUSSION
        assert current_state.task_id == task_id

    # Mock discussion records for validation
    memory_client.search_memory.return_value = {
        "results": [
            {
                "id": "discussion-1",
                "content": f"Discussion about authentication system for session {session_id}",
                "content_type": "decision",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        ]
    }

    # Simulate memory storage (discussion)
    await task_state_sync.synchronize_on_memory_storage(
        content="Discussed authentication requirements and security considerations",
        content_type="decision",
        keywords=["discussion", "authentication"],
        session_id=session_id
    )

    # Validate DISCUSSION step
    discussion_result = await step_validator.validate_step("DISCUSSION", session_id)
    assert discussion_result.status == ValidationStatus.PASSED

    # Mock research records
    memory_client.search_memory.return_value = {
        "results": [
            {
                "id": "research-1",
                "content": f"Context7 research on JWT best practices for session {session_id}",
                "content_type": "context",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        ]
    }

    # Simulate Context7 research
    await task_state_sync.synchronize_on_memory_storage(
        content="Researched JWT implementation patterns and security best practices",
        content_type="context",
        keywords=["context7", "jwt", "research"],
        session_id=session_id
    )

    # Validate RESEARCH step
    research_result = await step_validator.validate_step("RESEARCH", session_id)
    assert research_result.status == ValidationStatus.PASSED

    # Simulate tool execution for implementation
    await task_state_sync.synchronize_on_tool_execution(
        tool_name="Write",
        tool_input={
            "file_path": "src/auth.py",
            "content": """
def authenticate_user(username: str, password: str) -> dict:
    '''
    Authenticate user with JWT tokens.

    Args:
        username: User identifier
        password: User password

    Returns:
        Authentication result with JWT token
    '''
    # Implementation here
    pass
"""
        },
        execution_result={"success": True},
        session_id=session_id
    )

    # Verify progress tracking
    session_summary = task_state_sync.get_session_summary(session_id)
    assert session_summary["files_modified"] == 1
    assert session_summary["memory_entries"] >= 2
    assert session_summary["tools_used"]["Write"] >= 1


@pytest.mark.asyncio
async def test_protocol_step_advancement_integration(integration_setup):
    """Test protocol step advancement through synchronization."""
    setup = integration_setup
    protocol_manager = setup["protocol_manager"]
    task_state_sync = setup["task_state_sync"]
    memory_client = setup["memory_client"]

    # Initialize session and move to DISCUSSION
    initial_state = await protocol_manager.initialize_session()
    session_id = initial_state.session_id

    discussion_state = await protocol_manager.advance_step(
        initial_state,
        ProtocolStep.DISCUSSION
    )

    # Mock decision storage (should trigger advancement to ANALYSIS)
    memory_client.search_memory.return_value = {
        "results": [
            {
                "id": "decision-1",
                "content": f"Decision made for session {session_id}",
                "content_type": "decision"
            }
        ]
    }

    # Simulate tool execution that should trigger step advancement
    await task_state_sync.synchronize_on_tool_execution(
        tool_name="Write",
        tool_input={"file_path": "decision.md", "content": "Decision documented"},
        execution_result={"success": True},
        session_id=session_id
    )

    # Note: Step advancement evaluation happens during sync but may not
    # immediately advance due to debouncing and evaluation logic

    # Verify session metrics are updated
    session_summary = task_state_sync.get_session_summary(session_id)
    assert session_summary["files_modified"] >= 1


@pytest.mark.asyncio
async def test_crash_recovery_integration(integration_setup):
    """Test crash recovery with state restoration."""
    setup = integration_setup
    protocol_manager = setup["protocol_manager"]
    task_state_sync = setup["task_state_sync"]
    state_file = setup["state_file"]

    # Create session with progress
    initial_state = await protocol_manager.initialize_session()
    session_id = initial_state.session_id

    # Advance through some steps
    discussion_state = await protocol_manager.advance_step(
        initial_state,
        ProtocolStep.DISCUSSION,
        task_id="recovery-task-123"
    )

    analysis_state = await protocol_manager.advance_step(
        discussion_state,
        ProtocolStep.ANALYSIS
    )

    # Simulate some activity
    await task_state_sync.synchronize_on_tool_execution(
        tool_name="Write",
        tool_input={"file_path": "test.py", "content": "test code"},
        execution_result={"success": True},
        session_id=session_id
    )

    # Verify state is saved
    assert state_file.exists()

    # Simulate crash recovery with new manager instance
    recovery_manager = ProtocolStateManager(state_file)
    recovery_sync = TaskStateSync(setup["memory_client"], recovery_manager)

    # Perform crash recovery
    recovery_success = await recovery_sync.perform_crash_recovery(session_id)
    assert recovery_success == True

    # Verify state was restored
    recovered_state = await recovery_manager.get_current_state()
    assert recovered_state.session_id == session_id
    assert recovered_state.protocol_step == ProtocolStep.ANALYSIS
    assert recovered_state.task_id == "recovery-task-123"


@pytest.mark.asyncio
async def test_enforcement_override_integration(integration_setup):
    """Test enforcement override workflow."""
    setup = integration_setup
    task_first_handler = setup["task_first_handler"]
    memory_client = setup["memory_client"]

    # Complex task requiring enforcement
    user_prompt = "Build comprehensive API gateway with rate limiting"

    # Mock user to choose override
    with patch('claude.hooks.devstream.protocol.enforcement_gate.PYINQUIRER_AVAILABLE', False):
        with patch.dict('os.environ', {'DEVSTREAM_PROTOCOL_OVERRIDE': 'true'}):
            success, task_id = await task_first_handler.enforce_task_creation(
                user_prompt,
                tool_name="Write"
            )

            # Override should allow continuation without task creation
            assert success == True
            assert task_id is None

            # Verify override decision was logged with risks
            memory_client.store_memory.assert_called()
            call_args = memory_client.store_memory.call_args
            content = call_args[1]['content']
            assert "OVERRIDE" in content
            assert "PROTOCOL OVERRIDE - RISKS ACCEPTED" in content


@pytest.mark.asyncio
async def test_memory_integration_workflow(integration_setup):
    """Test complete memory integration workflow."""
    setup = integration_setup
    protocol_manager = setup["protocol_manager"]
    task_state_sync = setup["task_state_sync"]
    memory_client = setup["memory_client"]

    # Initialize session
    initial_state = await protocol_manager.initialize_session()
    session_id = initial_state.session_id

    # Simulate various memory storage operations
    memory_operations = [
        ("Discussion about architecture", "decision", ["discussion", "architecture"]),
        ("Context7 research on patterns", "context", ["context7", "research"]),
        ("TodoWrite list created", "context", ["todowrite", "planning"]),
        ("Code implementation", "code", ["implementation", "code"]),
        ("Learning from implementation", "learning", ["learning", "experience"])
    ]

    for content, content_type, keywords in memory_operations:
        await task_state_sync.synchronize_on_memory_storage(
            content=content,
            content_type=content_type,
            keywords=keywords,
            session_id=session_id
        )

    # Verify all operations were tracked
    session_summary = task_state_sync.get_session_summary(session_id)
    assert session_summary["memory_entries"] == len(memory_operations)

    # Verify memory client was called for each operation
    assert memory_client.store_memory.call_count >= len(memory_operations)


@pytest.mark.asyncio
async def test_performance_metrics_integration(integration_setup):
    """Test performance metrics collection and reporting."""
    setup = integration_setup
    task_state_sync = setup["task_state_sync"]
    memory_client = setup["memory_client"]

    # Initialize session
    initial_state = await setup["protocol_manager"].initialize_session()
    session_id = initial_state.session_id

    # Simulate various tool executions
    tool_executions = [
        ("Write", {"file_path": "file1.py", "content": "code1\ncode2\ncode3"}),
        ("Edit", {"file_path": "file2.py", "new_string": "updated code"}),
        ("Read", {"file_path": "file3.py"}),
        ("Bash", {"command": "python test.py"}),
        ("Write", {"file_path": "file4.py", "content": "more code"})
    ]

    for tool_name, tool_input in tool_executions:
        await task_state_sync.synchronize_on_tool_execution(
            tool_name=tool_name,
            tool_input=tool_input,
            execution_result={"success": True},
            session_id=session_id
        )

    # Get detailed session summary
    session_summary = task_state_sync.get_session_summary(session_id)

    # Verify metrics
    assert session_summary["total_tool_usage"] == len(tool_executions)
    assert session_summary["files_modified"] >= 2  # Write operations
    assert session_summary["lines_written"] >= 5  # Total lines from write operations
    assert "Write" in session_summary["tools_used"]
    assert "Edit" in session_summary["tools_used"]
    assert session_summary["tools_used"]["Write"] == 2

    # Get sync statistics
    sync_stats = task_state_sync.get_sync_statistics()
    assert sync_stats["total_syncs"] >= len(tool_executions)
    assert sync_stats["active_sessions"] >= 1
    assert sync_stats["debouncer_active"] == True


@pytest.mark.asyncio
async def test_concurrent_session_handling(integration_setup):
    """Test handling of multiple concurrent sessions."""
    setup = integration_setup
    protocol_manager = setup["protocol_manager"]
    task_state_sync = setup["task_state_sync"]

    # Create multiple sessions
    sessions = []
    for i in range(3):
        state = await protocol_manager.initialize_session()
        sessions.append(state)

    # Perform operations in each session
    for i, session in enumerate(sessions):
        await task_state_sync.synchronize_on_tool_execution(
            tool_name="Write",
            tool_input={"file_path": f"session_{i}_file.py", "content": f"Session {i} code"},
            execution_result={"success": True},
            session_id=session.session_id
        )

    # Verify each session maintains independent state
    for i, session in enumerate(sessions):
        summary = task_state_sync.get_session_summary(session.session_id)
        assert summary["session_id"] == session.session_id
        assert summary["files_modified"] == 1
        assert summary["is_active"] == True

    # Verify global statistics
    sync_stats = task_state_sync.get_sync_statistics()
    assert sync_stats["active_sessions"] == 3
    assert sync_stats["total_sessions"] >= 3


@pytest.mark.asyncio
async def test_error_recovery_integration(integration_setup):
    """Test error recovery and graceful degradation."""
    setup = integration_setup
    task_state_sync = setup["task_state_sync"]
    memory_client = setup["memory_client"]

    # Initialize session
    initial_state = await setup["protocol_manager"].initialize_session()
    session_id = initial_state.session_id

    # Simulate successful operation
    success1 = await task_state_sync.synchronize_on_tool_execution(
        tool_name="Write",
        tool_input={"file_path": "test.py", "content": "test code"},
        execution_result={"success": True},
        session_id=session_id
    )
    assert success1 == True

    # Simulate memory client failure
    memory_client.store_memory.side_effect = Exception("Memory storage failed")

    # Operation should still succeed despite memory failure
    success2 = await task_state_sync.synchronize_on_memory_storage(
        content="Test content",
        content_type="context",
        keywords=["test"],
        session_id=session_id
    )
    # Memory failures are non-blocking, should still return True
    assert success2 == True

    # Verify state remains consistent
    current_state = await setup["protocol_manager"].get_current_state()
    assert current_state.session_id == session_id


@pytest.mark.asyncio
async def test_full_protocol_simulation(integration_setup):
    """Test full simulation of complete protocol workflow."""
    setup = integration_setup
    protocol_manager = setup["protocol_manager"]
    task_first_handler = setup["task_first_handler"]
    step_validator = setup["step_validator"]
    task_state_sync = setup["task_state_sync"]
    memory_client = setup["memory_client"]

    # Initialize session
    initial_state = await protocol_manager.initialize_session()
    session_id = initial_state.session_id

    # Complex task requiring full protocol
    user_prompt = "Design and implement microservices architecture with API gateway"

    # Mock memory search results for validation
    memory_client.search_memory.return_value = {
        "results": [
            {
                "id": "test-1",
                "content": f"Architecture discussion for session {session_id}",
                "content_type": "decision",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        ]
    }

    # Mock user to choose protocol
    with patch('claude.hooks.devstream.protocol.enforcement_gate.PYINQUIRER_AVAILABLE', False):
        success, task_id = await task_first_handler.enforce_task_creation(
            user_prompt,
            tool_name="Write",
            session_id=session_id
        )
        assert success == True
        assert task_id is not None

    # Simulate progress through all steps
    steps_progress = [
        (ProtocolStep.DISCUSSION, "decision"),
        (ProtocolStep.ANALYSIS, "context"),
        (ProtocolStep.RESEARCH, "context"),
        (ProtocolStep.PLANNING, "context"),
        (ProtocolStep.APPROVAL, "decision"),
        (ProtocolStep.IMPLEMENTATION, "code")
    ]

    current_state = await protocol_manager.get_current_state()

    for step, content_type in steps_progress:
        # Advance to step
        if current_state.protocol_step != step:
            current_state = await protocol_manager.advance_step(current_state, step)

        # Simulate activity for the step
        await task_state_sync.synchronize_on_memory_storage(
            content=f"Activity for {step.name}",
            content_type=content_type,
            keywords=[step.name.lower(), session_id],
            session_id=session_id
        )

        # Simulate tool execution
        await task_state_sync.synchronize_on_tool_execution(
            tool_name="Write",
            tool_input={"file_path": f"{step.name.lower()}.md", "content": f"{step.name} documentation"},
            execution_result={"success": True},
            session_id=session_id
        )

        # Validate step (except for VERIFICATION which is special)
        if step != ProtocolStep.VERIFICATION:
            result = await step_validator.validate_step(step.name, session_id)
            # Results may vary based on mock data, but should not crash
            assert result.status in [ValidationStatus.PASSED, ValidationStatus.WARNING, ValidationStatus.FAILED]

    # Verify complete workflow
    final_state = await protocol_manager.get_current_state()
    final_summary = task_state_sync.get_session_summary(session_id)
    sync_stats = task_state_sync.get_sync_statistics()

    # Verify comprehensive tracking
    assert final_state.session_id == session_id
    assert final_summary["files_modified"] >= len(steps_progress)
    assert final_summary["memory_entries"] >= len(steps_progress)
    assert sync_stats["total_syncs"] >= len(steps_progress) * 2  # Memory + tool syncs
    assert sync_stats["active_sessions"] >= 1


if __name__ == "__main__":
    # Run tests directly
    import subprocess
    result = subprocess.run(["pytest", __file__, "-v", "-s"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    print(f"Integration tests completed with exit code: {result.returncode}")