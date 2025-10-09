#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pytest>=7.0.0",
#     "pytest-asyncio>=0.21.0",
#     "pytest-cov>=4.0.0",
#     "cchooks>=0.1.4",
#     "aiohttp>=3.8.0",
#     "structlog>=23.0.0",
# ]
# ///

"""
Integration tests for DevStream Protocol with existing hook system.

Tests the integration between the new protocol components and the existing
PreToolUse and PostToolUse hooks to ensure seamless enforcement of the
7-step protocol workflow.

Key Integration Points Tested:
1. PreToolUse hook integration with task creation enforcement
2. PostToolUse hook integration with state synchronization
3. Context7 integration through existing memory system
4. MCP tool integration for task management
5. Hook chaining and error handling
"""

import asyncio
import json
import pytest
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

# Import cchooks for integration testing
from cchooks import safe_create_context, PreToolUseContext, PostToolUseContext

# Import protocol components
from claude.hooks.devstream.protocol.protocol_state_manager import ProtocolStep, get_protocol_manager
from claude.hooks.devstream.protocol.enforcement_gate import get_enforcement_gate
from claude.hooks.devstream.protocol.task_first_handler import get_task_first_handler
from claude.hooks.devstream.protocol.task_state_sync import get_task_state_sync


@pytest.fixture
async def hook_integration_setup(temp_directory):
    """Set up complete hook integration environment."""
    temp_dir = Path(temp_directory)

    # Create temporary state file
    state_file = temp_dir / "protocol_state.json"

    # Create mock environment
    mock_env = {
        "DEVSTREAM_MEMORY_ENABLED": "true",
        "DEVSTREAM_PROTOCOL_ENFORCEMENT": "true",
        "DEVSTREAM_CONTEXT_INJECTION_ENABLED": "true"
    }

    # Create mock MCP client
    mock_mcp_client = AsyncMock()
    mock_mcp_client.search_memory.return_value = {"results": []}
    mock_mcp_client.store_memory = AsyncMock()
    mock_mcp_client.create_task.return_value = {"task_id": "hook-task-123"}

    # Initialize protocol components with mocked dependencies
    with patch.dict('os.environ', mock_env):
        protocol_manager = get_protocol_manager()
        protocol_manager.state_file = state_file

        # Reinitialize with new state file
        protocol_manager = ProtocolStateManager(state_file)

        task_first_handler = get_task_first_handler()
        task_first_handler.memory_client = mock_mcp_client

        task_state_sync = get_task_state_sync()
        task_state_sync.memory_client = mock_mcp_client
        task_state_sync.protocol_manager = protocol_manager

        enforcement_gate = get_enforcement_gate()

        yield {
            "protocol_manager": protocol_manager,
            "task_first_handler": task_first_handler,
            "task_state_sync": task_state_sync,
            "enforcement_gate": enforcement_gate,
            "mcp_client": mock_mcp_client,
            "state_file": state_file,
            "temp_dir": temp_dir
        }


class MockPreToolUseContext:
    """Mock PreToolUseContext for testing."""

    def __init__(self, tool_name: str, tool_input: dict):
        self.tool_name = tool_name
        self.tool_input = tool_input
        self.output = MagicMock()
        self.output.exit_success = MagicMock()
        self.output.exit_non_block = MagicMock()


class MockPostToolUseContext:
    """Mock PostToolUseContext for testing."""

    def __init__(self, tool_name: str, tool_input: dict, result: dict):
        self.tool_name = tool_name
        self.tool_input = tool_input
        self.result = result
        self.output = MagicMock()
        self.output.exit_success = MagicMock()


@pytest.mark.asyncio
async def test_prettooluse_protocol_enforcement(hook_integration_setup):
    """Test PreToolUse hook integration with protocol enforcement."""
    setup = hook_integration_setup
    task_first_handler = setup["task_first_handler"]

    # Initialize session
    initial_state = await setup["protocol_manager"].initialize_session()
    session_id = initial_state.session_id

    # Test 1: Simple task (no enforcement)
    simple_context = MockPreToolUseContext(
        tool_name="Edit",
        tool_input={
            "file_path": "README.md",
            "new_string": "Fixed typo"
        }
    )

    should_create, task_info = await task_first_handler.should_create_task(
        user_prompt="Fix typo in README",
        tool_name=simple_context.tool_name,
        tool_input=simple_context.tool_input
    )

    assert should_create == False
    assert task_info.complexity.value == "simple"

    # Test 2: Complex task (enforcement required)
    complex_context = MockPreToolUseContext(
        tool_name="Write",
        tool_input={
            "file_path": "src/auth.py",
            "content": "def authenticate_user():\n    pass"
        }
    )

    should_create, task_info = await task_first_handler.should_create_task(
        user_prompt="Implement comprehensive user authentication system",
        tool_name=complex_context.tool_name,
        tool_input=complex_context.tool_input
    )

    assert should_create == True
    assert task_info.complexity.value in ["complex", "critical"]

    # Mock enforcement gate to choose protocol
    with patch('claude.hooks.devstream.protocol.enforcement_gate.PYINQUIRER_AVAILABLE', False):
        success, task_id = await task_first_handler.enforce_task_creation(
            user_prompt="Implement comprehensive user authentication system",
            tool_name=complex_context.tool_name,
            tool_input=complex_context.tool_input,
            session_id=session_id
        )

        assert success == True
        assert task_id is not None

    # Verify protocol state was updated
    current_state = await setup["protocol_manager"].get_current_state()
    assert current_state.protocol_step == ProtocolStep.DISCUSSION
    assert current_state.task_id == task_id


@pytest.mark.asyncio
async def test_posttooluse_state_synchronization(hook_integration_setup):
    """Test PostToolUse hook integration with state synchronization."""
    setup = hook_integration_setup
    task_state_sync = setup["task_state_sync"]

    # Initialize session
    initial_state = await setup["protocol_manager"].initialize_session()
    session_id = initial_state.session_id

    # Simulate PostToolUse execution
    post_context = MockPostToolUseContext(
        tool_name="Write",
        tool_input={
            "file_path": "src/api.py",
            "content": """
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "healthy"}
"""
        },
        result={"success": True, "lines_written": 8}
    )

    # Trigger synchronization
    success = await task_state_sync.synchronize_on_tool_execution(
        tool_name=post_context.tool_name,
        tool_input=post_context.tool_input,
        execution_result=post_context.result,
        session_id=session_id
    )

    assert success == True

    # Verify metrics were updated
    session_summary = task_state_sync.get_session_summary(session_id)
    assert session_summary["files_modified"] == 1
    assert session_summary["lines_written"] >= 8
    assert session_summary["tools_used"]["Write"] == 1

    # Test memory storage synchronization
    memory_success = await task_state_sync.synchronize_on_memory_storage(
        content="Created FastAPI health check endpoint",
        content_type="code",
        keywords=["fastapi", "api", "endpoint"],
        session_id=session_id
    )

    assert memory_success == True

    # Verify memory metrics updated
    updated_summary = task_state_sync.get_session_summary(session_id)
    assert updated_summary["memory_entries"] == 1


@pytest.mark.asyncio
async def test_hook_workflow_integration(hook_integration_setup):
    """Test complete workflow integrating PreToolUse and PostToolUse hooks."""
    setup = hook_integration_setup
    task_first_handler = setup["task_first_handler"]
    task_state_sync = setup["task_state_sync"]
    mcp_client = setup["mcp_client"]

    # Initialize session
    initial_state = await setup["protocol_manager"].initialize_session()
    session_id = initial_state.session_id

    # Step 1: PreToolUse - Complex task triggers enforcement
    user_prompt = "Build REST API for user management with authentication"

    with patch('claude.hooks.devstream.protocol.enforcement_gate.PYINQUIRER_AVAILABLE', False):
        success, task_id = await task_first_handler.enforce_task_creation(
            user_prompt=user_prompt,
            tool_name="Write",
            session_id=session_id
        )

        assert success == True
        assert task_id is not None

    # Step 2: Multiple PostToolUse executions (simulating development)
    operations = [
        {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "src/models.py",
                "content": "from pydantic import BaseModel\n\nclass User(BaseModel):\n    id: int\n    username: str\n    email: str"
            },
            "result": {"success": True}
        },
        {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "src/auth.py",
                "content": "import jwt\nfrom datetime import datetime, timedelta\n\ndef create_token(user_id: int) -> str:\n    return jwt.encode({'user_id': user_id}, 'secret', algorithm='HS256')"
            },
            "result": {"success": True}
        },
        {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "src/api.py",
                "content": "from fastapi import FastAPI, Depends\nfrom .models import User\nfrom .auth import create_token\n\napp = FastAPI()"
            },
            "result": {"success": True}
        }
    ]

    # Execute all operations
    for op in operations:
        await task_state_sync.synchronize_on_tool_execution(
            tool_name=op["tool_name"],
            tool_input=op["tool_input"],
            execution_result=op["result"],
            session_id=session_id
        )

    # Step 3: Memory operations throughout development
    memory_operations = [
        ("Discussed API architecture and authentication flow", "decision", ["architecture", "api"]),
        ("Researched FastAPI best practices and JWT implementation", "context", ["context7", "fastapi", "jwt"]),
        ("Created TodoWrite list with implementation tasks", "context", ["todowrite", "planning"]),
        ("Documented learning about FastAPI dependency injection", "learning", ["learning", "fastapi"])
    ]

    for content, content_type, keywords in memory_operations:
        await task_state_sync.synchronize_on_memory_storage(
            content=content,
            content_type=content_type,
            keywords=keywords,
            session_id=session_id
        )

    # Step 4: Verify complete integration
    final_summary = task_state_sync.get_session_summary(session_id)
    sync_stats = task_state_sync.get_sync_statistics()

    # Verify comprehensive tracking
    assert final_summary["session_id"] == session_id
    assert final_summary["files_modified"] == len(operations)
    assert final_summary["memory_entries"] == len(memory_operations)
    assert final_summary["tools_used"]["Write"] == len(operations)

    # Verify MCP integration
    assert mcp_client.create_task.call_count >= 1
    assert mcp_client.store_memory.call_count >= len(memory_operations)

    # Verify sync statistics
    assert sync_stats["total_syncs"] >= len(operations) + len(memory_operations)
    assert sync_stats["active_sessions"] >= 1


@pytest.mark.asyncio
async def test_error_handling_in_hook_integration(hook_integration_setup):
    """Test error handling and graceful degradation in hook integration."""
    setup = hook_integration_setup
    task_first_handler = setup["task_first_handler"]
    task_state_sync = setup["task_state_sync"]
    mcp_client = setup["mcp_client"]

    # Initialize session
    initial_state = await setup["protocol_manager"].initialize_session()
    session_id = initial_state.session_id

    # Test 1: Memory client failure during task creation
    mcp_client.create_task.side_effect = Exception("MCP client unavailable")

    with patch('claude.hooks.devstream.protocol.enforcement_gate.PYINQUIRER_AVAILABLE', False):
        # Should handle gracefully and continue
        success, task_id = await task_first_handler.enforce_task_creation(
            user_prompt="Implement user authentication",
            tool_name="Write",
            session_id=session_id
        )

        # Should still succeed but without task creation
        assert success == True
        assert task_id is None

    # Reset side effect
    mcp_client.create_task.side_effect = None

    # Test 2: Memory client failure during synchronization
    mcp_client.store_memory.side_effect = Exception("Memory storage failed")

    sync_success = await task_state_sync.synchronize_on_memory_storage(
        content="Test content",
        content_type="context",
        keywords=["test"],
        session_id=session_id
    )

    # Should handle gracefully (memory failures are non-blocking)
    assert sync_success == True

    # Test 3: Protocol manager failure
    with patch.object(setup["protocol_manager"], 'get_current_state',
                     side_effect=Exception("State manager failed")):
        sync_success = await task_state_sync.synchronize_on_tool_execution(
            tool_name="Write",
            tool_input={"file_path": "test.py", "content": "test"},
            execution_result={"success": True},
            session_id=session_id
        )

        # Should handle gracefully
        assert sync_success == False  # Expected to fail without state


@pytest.mark.asyncio
async def test_context7_integration_through_hooks(hook_integration_setup):
    """Test Context7 integration through the hook system."""
    setup = hook_integration_setup
    task_state_sync = setup["task_state_sync"]
    mcp_client = setup["mcp_client"]

    # Initialize session
    initial_state = await setup["protocol_manager"].initialize_session()
    session_id = initial_state.session_id

    # Simulate Context7 research through memory storage
    context7_operations = [
        {
            "content": "Context7 research on FastAPI authentication patterns",
            "content_type": "context",
            "keywords": ["context7", "fastapi", "authentication", "research"],
            "contains_context7": True
        },
        {
            "content": "Library documentation for JWT token implementation",
            "content_type": "context",
            "keywords": ["context7", "jwt", "library", "docs"],
            "contains_context7": True
        },
        {
            "content": "General discussion about API design",
            "content_type": "decision",
            "keywords": ["api", "design", "discussion"],
            "contains_context7": False
        }
    ]

    # Execute Context7 operations
    for op in context7_operations:
        await task_state_sync.synchronize_on_memory_storage(
            content=op["content"],
            content_type=op["content_type"],
            keywords=op["keywords"],
            session_id=session_id
        )

    # Verify Context7 tracking
    session_summary = task_state_sync.get_session_summary(session_id)
    assert session_summary["memory_entries"] == len(context7_operations)

    # Count Context7 queries (content containing "context7")
    context7_count = sum(1 for op in context7_operations if op["contains_context7"])
    assert session_summary["context7_queries"] >= context7_count

    # Verify memory client was called appropriately
    assert mcp_client.store_memory.call_count >= len(context7_operations)


@pytest.mark.asyncio
async def test_concurrent_hook_execution(hook_integration_setup):
    """Test concurrent hook execution with multiple sessions."""
    setup = hook_integration_setup
    task_state_sync = setup["task_state_sync"]

    # Create multiple sessions
    sessions = []
    for i in range(3):
        state = await setup["protocol_manager"].initialize_session()
        sessions.append(state)

    # Simulate concurrent hook executions
    async def simulate_session_work(session, session_id):
        # Simulate PreToolUse -> PostToolUse workflow
        await task_state_sync.synchronize_on_tool_execution(
            tool_name="Write",
            tool_input={"file_path": f"session_{session_id}_file.py", "content": f"Code for {session_id}"},
            execution_result={"success": True},
            session_id=session_id
        )

        await task_state_sync.synchronize_on_memory_storage(
            content=f"Memory entry for {session_id}",
            content_type="context",
            keywords=[session_id],
            session_id=session_id
        )

        return session_id

    # Execute concurrent work
    tasks = []
    for i, session in enumerate(sessions):
        session_id = f"concurrent-session-{i}"
        task = simulate_session_work(session, session_id)
        tasks.append(task)

    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify all sessions completed successfully
    for result in results:
        assert not isinstance(result, Exception)
        assert result.startswith("concurrent-session-")

    # Verify session isolation
    sync_stats = task_state_sync.get_sync_statistics()
    assert sync_stats["active_sessions"] >= 3

    # Check each session maintains independent state
    for i, session in enumerate(sessions):
        session_id = f"concurrent-session-{i}"
        summary = task_state_sync.get_session_summary(session_id)
        assert summary["files_modified"] == 1
        assert summary["memory_entries"] == 1


@pytest.mark.asyncio
async def test_hook_chaining_and_ordering(hook_integration_setup):
    """Test that hooks are properly chained and execute in correct order."""
    setup = hook_integration_setup
    task_first_handler = setup["task_first_handler"]
    task_state_sync = setup["task_state_sync"]

    # Initialize session
    initial_state = await setup["protocol_manager"].initialize_session()
    session_id = initial_state.session_id

    # Track execution order
    execution_log = []

    # Mock enforcement gate to track calls
    original_show_gate = setup["enforcement_gate"].show_enforcement_gate
    async def mock_show_gate(context, memory_client):
        execution_log.append("enforcement_gate")
        # Default to protocol in non-interactive mode
        from claude.hooks.devstream.protocol.enforcement_gate import EnforcementDecision
        return EnforcementDecision.PROTOCOL

    setup["enforcement_gate"].show_enforcement_gate = mock_show_gate

    # Mock state sync to track calls
    original_sync = task_state_sync.synchronize_on_tool_execution
    async def mock_sync(tool_name, tool_input, execution_result, session_id):
        execution_log.append(f"sync_{tool_name}")
        return await original_sync(tool_name, tool_input, execution_result, session_id)

    task_state_sync.synchronize_on_tool_execution = mock_sync

    # Execute complete workflow
    user_prompt = "Implement user authentication system"

    # Step 1: PreToolUse (task creation enforcement)
    with patch('claude.hooks.devstream.protocol.enforcement_gate.PYINQUIRER_AVAILABLE', False):
        success, task_id = await task_first_handler.enforce_task_creation(
            user_prompt=user_prompt,
            tool_name="Write",
            session_id=session_id
        )

    # Step 2: PostToolUse (state synchronization)
    await task_state_sync.synchronize_on_tool_execution(
        tool_name="Write",
        tool_input={"file_path": "auth.py", "content": "auth code"},
        execution_result={"success": True},
        session_id=session_id
    )

    # Verify execution order
    # Should be: enforcement_gate -> sync_Write
    assert len(execution_log) >= 2
    assert execution_log[0] == "enforcement_gate"
    assert "sync_Write" in execution_log[1]


@pytest.mark.asyncio
async def test_performance_under_load(hook_integration_setup):
    """Test hook system performance under realistic load."""
    setup = hook_integration_setup
    task_state_sync = setup["task_state_sync"]

    # Initialize session
    initial_state = await setup["protocol_manager"].initialize_session()
    session_id = initial_state.session_id

    # Simulate high-frequency operations
    operation_count = 50
    start_time = asyncio.get_event_loop().time()

    # Execute many operations rapidly
    tasks = []
    for i in range(operation_count):
        # Tool execution sync
        task1 = task_state_sync.synchronize_on_tool_execution(
            tool_name="Write",
            tool_input={"file_path": f"file_{i}.py", "content": f"Code {i}"},
            execution_result={"success": True},
            session_id=session_id
        )

        # Memory storage sync
        task2 = task_state_sync.synchronize_on_memory_storage(
            content=f"Memory entry {i}",
            content_type="context",
            keywords=[f"entry_{i}"],
            session_id=session_id
        )

        tasks.extend([task1, task2])

    # Wait for all operations to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)

    end_time = asyncio.get_event_loop().time()
    duration = end_time - start_time

    # Verify performance
    successful_operations = sum(1 for r in results if r is True)
    total_operations = len(results)

    assert successful_operations >= total_operations * 0.95  # 95% success rate
    assert duration < 10.0  # Should complete within 10 seconds

    # Verify metrics accuracy
    session_summary = task_state_sync.get_session_summary(session_id)
    assert session_summary["files_modified"] == operation_count
    assert session_summary["memory_entries"] == operation_count

    sync_stats = task_state_sync.get_sync_statistics()
    assert sync_stats["total_syncs"] >= total_operations


if __name__ == "__main__":
    # Run tests directly
    import subprocess
    result = subprocess.run([
        "pytest", __file__, "-v", "-s",
        "--tb=short"
    ], capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print(f"Hook integration tests completed with exit code: {result.returncode}")