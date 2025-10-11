#!/usr/bin/env -S .devstream/bin/python
# -*- coding: utf-8 -*-

"""
Integration Tests for SessionEnd v2 Event Sourcing Workflow

Tests complete end-to-end workflow:
1. Event capture via post_tool_use.py
2. Event aggregation via session_end_v2.py
3. Summary generation
4. Marker file creation
5. Event log cleanup

Validates that all components work together correctly.
"""

import asyncio
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, Any

import pytest
import sys

# Add the hooks directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../.claude/hooks/devstream'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../.claude/hooks/devstream/sessions'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../.claude/hooks/devstream/memory'))

from sessions.session_event_log import get_session_log, close_session_log, SessionEvent
from sessions.session_end_v2 import SessionEndHookV2
from memory.post_tool_use import PostToolUseHook
from cchooks import PostToolUseContext


class TestEventSourcingWorkflow:
    """Test complete Event Sourcing workflow."""

    @pytest.fixture
    async def temp_session_id(self):
        """Create temporary session ID for testing."""
        return f"test-workflow-{int(time.time())}"

    @pytest.fixture
    async def cleanup_session(self, temp_session_id):
        """Cleanup session after test."""
        yield
        # Clean up event log
        await close_session_log(temp_session_id)

    @staticmethod
    def create_mock_context(tool_name: str, tool_input: Dict[str, Any], tool_response: Dict[str, Any]):
        """Create mock PostToolUseContext for testing."""
        class MockOutput:
            def exit_success(self):
                pass
            def exit_non_block(self, message: str):
                pass

        class MockContext:
            def __init__(self, tool_name: str, tool_input: Dict[str, Any], tool_response: Dict[str, Any]):
                self.tool_name = tool_name
                self.tool_input = tool_input
                self.tool_response = tool_response
                self.output = MockOutput()

        return MockContext(tool_name, tool_input, tool_response)

    @pytest.mark.asyncio
    async def test_complete_file_modification_workflow(self, temp_session_id, cleanup_session):
        """Test complete workflow: file modification → session end → summary."""

        # Set up session environment
        os.environ["CLAUDE_SESSION_ID"] = temp_session_id

        # Step 1: Simulate file modification via PostToolUse
        post_hook = PostToolUseHook()

        file_path = "/tmp/test_integration.py"
        file_content = '''
def hello_world():
    """Test function for integration testing."""
    print("Hello, World!")
    return "success"
'''

        # Create mock context for file write
        context = self.create_mock_context(
            tool_name="Write",
            tool_input={
                "file_path": file_path,
                "content": file_content
            },
            tool_response={"success": True}
        )

        # Process the tool use (captures event)
        await post_hook.process(context)

        # Step 2: Verify event was captured
        event_log = await get_session_log(temp_session_id)
        events = event_log.get_all_events()

        assert len(events) == 1
        assert events[0].type == "file_modified"
        assert events[0].data["path"] == file_path
        assert events[0].data["tool"] == "Write"
        assert events[0].data["size_bytes"] == len(file_content)

        # Step 3: Process session end
        session_end_hook = SessionEndHookV2()
        success = await session_end_hook.process_session_end(temp_session_id)

        assert success

        # Step 4: Verify marker file was created
        marker_file = Path.home() / ".claude" / "state" / f"devstream_session_{temp_session_id}.txt"
        assert marker_file.exists()

        # Step 5: Verify marker file content
        with open(marker_file, "r") as f:
            content = f.read()

        assert "# DevStream Session Summary" in content
        assert temp_session_id in content
        assert "Files Modified: 1" in content
        assert file_path in content

        # Step 6: Cleanup
        if marker_file.exists():
            marker_file.unlink()

    @pytest.mark.asyncio
    async def test_complete_task_workflow(self, temp_session_id, cleanup_session):
        """Test complete workflow: task completion → session end → summary."""

        # Set up session environment
        os.environ["CLAUDE_SESSION_ID"] = temp_session_id

        # Step 1: Simulate task completion via PostToolUse
        post_hook = PostToolUseHook()

        # Create mock context for task completion
        context = self.create_mock_context(
            tool_name="TodoWrite",
            tool_input={
                "todos": [
                    {"content": "Implement feature X", "status": "in_progress"},
                    {"content": "Fix bug Y", "status": "completed"},
                    {"content": "Write tests", "status": "completed"}
                ]
            },
            tool_response={"success": True}
        )

        # Process the tool use (captures events)
        await post_hook.process(context)

        # Step 2: Verify events were captured
        event_log = await get_session_log(temp_session_id)
        events = event_log.get_all_events()

        assert len(events) == 3  # 1 task started + 2 tasks completed

        # Check event types
        event_types = [event.type for event in events]
        assert "task_started" in event_types
        assert "task_completed" in event_types
        assert event_types.count("task_completed") == 2

        # Step 3: Process session end
        session_end_hook = SessionEndHookV2()
        success = await session_end_hook.process_session_end(temp_session_id)

        assert success

        # Step 4: Verify marker file content
        marker_file = Path.home() / ".claude" / "state" / f"devstream_session_{temp_session_id}.txt"
        assert marker_file.exists()

        with open(marker_file, "r") as f:
            content = f.read()

        assert "# DevStream Session Summary" in content
        assert "Tasks Completed: 2" in content
        assert "Fix bug Y" in content
        assert "Write tests" in content

        # Step 5: Cleanup
        if marker_file.exists():
            marker_file.unlink()

    @pytest.mark.asyncio
    async def test_mixed_events_workflow(self, temp_session_id, cleanup_session):
        """Test workflow with mixed event types."""

        # Set up session environment
        os.environ["CLAUDE_SESSION_ID"] = temp_session_id

        post_hook = PostToolUseHook()

        # Step 1: Capture multiple events
        events_to_capture = [
            # File modification
            self.create_mock_context(
                tool_name="Edit",
                tool_input={
                    "file_path": "/tmp/test.py",
                    "new_string": "def new_function(): pass"
                },
                tool_response={"success": True}
            ),
            # Task started
            self.create_mock_context(
                tool_name="TodoWrite",
                tool_input={
                    "todos": [{"content": "Refactor code", "status": "in_progress"}]
                },
                tool_response={"success": True}
            ),
            # Another file modification
            self.create_mock_context(
                tool_name="Write",
                tool_input={
                    "file_path": "/tmp/test2.py",
                    "content": "# Another test file"
                },
                tool_response={"success": True}
            ),
            # Task completed
            self.create_mock_context(
                tool_name="TodoWrite",
                tool_input={
                    "todos": [{"content": "Refactor code", "status": "completed"}]
                },
                tool_response={"success": True}
            ),
            # Bash error
            self.create_mock_context(
                tool_name="Bash",
                tool_input={
                    "command": "python nonexistent_file.py"
                },
                tool_response={
                    "success": False,
                    "error": "FileNotFoundError: [Errno 2] No such file or directory"
                }
            )
        ]

        # Process all events
        for context in events_to_capture:
            await post_hook.process(context)

        # Step 2: Verify all events were captured
        event_log = await get_session_log(temp_session_id)
        events = event_log.get_all_events()

        assert len(events) == 5

        event_types = [event.type for event in events]
        assert "file_modified" in event_types
        assert "task_started" in event_types
        assert "task_completed" in event_types
        assert "error" in event_types

        # Step 3: Process session end
        session_end_hook = SessionEndHookV2()
        success = await session_end_hook.process_session_end(temp_session_id)

        assert success

        # Step 4: Verify comprehensive summary
        marker_file = Path.home() / ".claude" / "state" / f"devstream_session_{temp_session_id}.txt"
        assert marker_file.exists()

        with open(marker_file, "r") as f:
            content = f.read()

        # Check all sections are present
        assert "# DevStream Session Summary" in content
        assert "Files Modified: 2" in content
        assert "Tasks Completed: 1" in content
        assert "Errors Occurred: 1" in content
        assert "/tmp/test.py" in content
        assert "/tmp/test2.py" in content
        assert "Refactor code" in content
        assert "bash_command" in content

        # Step 5: Cleanup
        if marker_file.exists():
            marker_file.unlink()

    @pytest.mark.asyncio
    async def test_empty_session_workflow(self, temp_session_id, cleanup_session):
        """Test workflow with empty session (no events)."""

        # Set up session environment
        os.environ["CLAUDE_SESSION_ID"] = temp_session_id

        # Step 1: Don't capture any events - session is empty

        # Step 2: Process session end
        session_end_hook = SessionEndHookV2()
        success = await session_end_hook.process_session_end(temp_session_id)

        # Should return False for empty session
        assert not success

        # Step 3: Verify no marker file created
        marker_file = Path.home() / ".claude" / "state" / f"devstream_session_{temp_session_id}.txt"
        assert not marker_file.exists()

    @pytest.mark.asyncio
    async def test_concurrent_sessions_isolation(self, cleanup_session):
        """Test that concurrent sessions are properly isolated."""

        session_ids = [
            f"concurrent-test-1-{int(time.time())}",
            f"concurrent-test-2-{int(time.time())}",
            f"concurrent-test-3-{int(time.time())}"
        ]

        try:
            post_hook = PostToolUseHook()

            # Step 1: Capture events for different sessions
            for i, session_id in enumerate(session_ids):
                os.environ["CLAUDE_SESSION_ID"] = session_id

                context = self.create_mock_context(
                    tool_name="Write",
                    tool_input={
                        "file_path": f"/tmp/concurrent_test_{i}.py",
                        "content": f"# Session {i} content"
                    },
                    tool_response={"success": True}
                )

                await post_hook.process(context)

            # Step 2: Verify each session has only its own events
            for i, session_id in enumerate(session_ids):
                event_log = await get_session_log(session_id)
                events = event_log.get_all_events()

                assert len(events) == 1
                assert events[0].data["path"] == f"/tmp/concurrent_test_{i}.py"

            # Step 3: Process session ends for all sessions
            session_end_hook = SessionEndHookV2()
            marker_files = []

            for session_id in session_ids:
                success = await session_end_hook.process_session_end(session_id)
                assert success

                marker_file = Path.home() / ".claude" / "state" / f"devstream_session_{session_id}.txt"
                assert marker_file.exists()
                marker_files.append(marker_file)

            # Step 4: Verify each summary is correct
            for i, marker_file in enumerate(marker_files):
                with open(marker_file, "r") as f:
                    content = f.read()

                assert session_ids[i] in content
                assert f"concurrent_test_{i}.py" in content
                assert "Files Modified: 1" in content

            # Step 5: Cleanup marker files
            for marker_file in marker_files:
                if marker_file.exists():
                    marker_file.unlink()

        finally:
            # Clean up all sessions
            for session_id in session_ids:
                await close_session_log(session_id)

    @pytest.mark.asyncio
    async def test_error_handling_in_event_capture(self, temp_session_id, cleanup_session):
        """Test error handling in event capture doesn't break workflow."""

        # Set up session environment
        os.environ["CLAUDE_SESSION_ID"] = temp_session_id

        # Step 1: Simulate event capture with potential error
        post_hook = PostToolUseHook()

        # Create a context that might cause issues
        context = self.create_mock_context(
            tool_name="Write",
            tool_input={
                "file_path": "",  # Empty file path (edge case)
                "content": "test content"
            },
            tool_response={"success": True}
        )

        # Process should not fail even with edge cases
        await post_hook.process(context)

        # Step 2: Process session end (should handle gracefully)
        session_end_hook = SessionEndHookV2()
        success = await session_end_hook.process_session_end(temp_session_id)

        # Should succeed or fail gracefully
        # The important thing is that it doesn't crash

    @pytest.mark.asyncio
    async def test_large_content_handling(self, temp_session_id, cleanup_session):
        """Test handling of large content (files with many lines)."""

        # Set up session environment
        os.environ["CLAUDE_SESSION_ID"] = temp_session_id

        # Step 1: Create large file content
        large_content = "# Large test file\n" + "\n".join([f"line_{i}: content" for i in range(1000)])

        post_hook = PostToolUseHook()

        context = self.create_mock_context(
            tool_name="Write",
            tool_input={
                "file_path": "/tmp/large_test.py",
                "content": large_content
            },
            tool_response={"success": True}
        )

        # Step 2: Process large file
        await post_hook.process(context)

        # Step 3: Verify event was captured with correct size
        event_log = await get_session_log(temp_session_id)
        events = event_log.get_all_events()

        assert len(events) == 1
        assert events[0].data["size_bytes"] == len(large_content)

        # Step 4: Process session end
        session_end_hook = SessionEndHookV2()
        success = await session_end_hook.process_session_end(temp_session_id)

        assert success

        # Step 5: Verify summary
        marker_file = Path.home() / ".claude" / "state" / f"devstream_session_{temp_session_id}.txt"
        assert marker_file.exists()

        with open(marker_file, "r") as f:
            content = f.read()

        assert "# DevStream Session Summary" in content
        assert "Files Modified: 1" in content
        assert "/tmp/large_test.py" in content

        # Cleanup
        if marker_file.exists():
            marker_file.unlink()


class TestSessionEndHookDirect:
    """Test SessionEndHookV2 directly without full PostToolUse integration."""

    @pytest.mark.asyncio
    async def test_session_end_direct(self):
        """Test SessionEndHookV2 directly with manual events."""

        session_id = f"direct-test-{int(time.time())}"

        try:
            # Step 1: Manually create events in the log
            event_log = await get_session_log(session_id)

            await event_log.record_event("file_modified", {
                "path": "/tmp/direct_test.py",
                "tool": "Write",
                "size_bytes": 150,
                "session_id": session_id
            })

            await event_log.record_event("task_completed", {
                "task_id": "task-123",
                "title": "Direct test task",
                "session_id": session_id
            })

            # Step 2: Process session end directly
            hook = SessionEndHookV2()
            success = await hook.process_session_end(session_id)

            assert success

            # Step 3: Verify marker file
            marker_file = Path.home() / ".claude" / "state" / f"devstream_session_{session_id}.txt"
            assert marker_file.exists()

            with open(marker_file, "r") as f:
                content = f.read()

            assert "# DevStream Session Summary" in content
            assert session_id in content
            assert "Files Modified: 1" in content
            assert "Tasks Completed: 1" in content

            # Cleanup
            if marker_file.exists():
                marker_file.unlink()

        finally:
            await close_session_log(session_id)


if __name__ == "__main__":
    # Run a quick test when executed directly
    async def quick_test():
        test = TestEventSourcingWorkflow()
        session_id = f"quick-test-{int(time.time())}"

        try:
            print("🧪 Running quick integration test...")

            # Clean up function
            async def cleanup():
                await close_session_log(session_id)
                marker_file = Path.home() / ".claude" / "state" / f"devstream_session_{session_id}.txt"
                if marker_file.exists():
                    marker_file.unlink()

            # Test complete workflow
            await test.test_complete_file_modification_workflow(session_id, cleanup)

            print("✅ Quick integration test passed!")

        except Exception as e:
            print(f"❌ Quick test failed: {e}")
            import traceback
            traceback.print_exc()

    asyncio.run(quick_test())