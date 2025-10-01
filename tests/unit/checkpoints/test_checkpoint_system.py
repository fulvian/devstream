"""
Unit tests for Checkpoint & Auto-Save System (Fix B1).

Tests:
- SQLite savepoint (commit d6ef593)
- Auto-save service startup
- Critical tool trigger (Write, Edit)
- /save-progress slash command
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import sys
import json
from datetime import datetime

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / '.claude/hooks/devstream/checkpoints'))


class TestSavepointPersistence:
    """Test SQLite savepoint implementation."""

    def setup_method(self):
        """Setup test fixtures."""
        from checkpoint_manager import CheckpointManager
        # Use temporary file instead of :memory: for test isolation
        import tempfile
        self.db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.manager = CheckpointManager(db_path=self.db_file.name)

    def teardown_method(self):
        """Cleanup test database."""
        import os
        try:
            os.unlink(self.db_file.name)
        except:
            pass

    @pytest.mark.asyncio
    async def test_create_savepoint(self):
        """Test creating a savepoint in database."""
        # Create checkpoint
        checkpoint = await self.manager.create_checkpoint(
            checkpoint_type="manual",
            description="Test checkpoint",
            context={"test": "data"}
        )

        assert checkpoint["id"] is not None
        assert checkpoint["type"] == "manual"
        assert checkpoint["description"] == "Test checkpoint"
        assert checkpoint["context"]["test"] == "data"

    @pytest.mark.asyncio
    async def test_retrieve_savepoint(self):
        """Test retrieving specific savepoint."""
        # Create checkpoint
        created = await self.manager.create_checkpoint(
            checkpoint_type="auto",
            description="Auto-save",
            context={"session_id": "123"}
        )

        # Retrieve
        retrieved = await self.manager.get_checkpoint(created["id"])

        assert retrieved is not None
        assert retrieved["id"] == created["id"]
        assert retrieved["type"] == "auto"
        assert retrieved["context"]["session_id"] == "123"

    @pytest.mark.asyncio
    async def test_list_checkpoints(self):
        """Test listing all checkpoints."""
        # Create multiple checkpoints
        await self.manager.create_checkpoint("manual", "Checkpoint 1", {})
        await self.manager.create_checkpoint("auto", "Checkpoint 2", {})
        await self.manager.create_checkpoint("manual", "Checkpoint 3", {})

        # List
        checkpoints = await self.manager.list_checkpoints(limit=10)

        assert len(checkpoints) >= 3
        assert all("id" in cp for cp in checkpoints)

    @pytest.mark.asyncio
    async def test_rollback_to_savepoint(self):
        """Test rollback to specific savepoint."""
        # Create checkpoint
        checkpoint = await self.manager.create_checkpoint(
            checkpoint_type="manual",
            description="Before changes",
            context={"version": 1}
        )

        # Simulate changes
        # ...

        # Rollback
        success = await self.manager.rollback_to_checkpoint(checkpoint["id"])

        assert success is True

    @pytest.mark.asyncio
    async def test_checkpoint_metadata(self):
        """Test checkpoint stores complete metadata."""
        context = {
            "session_id": "test-123",
            "active_task": "DEVSTREAM-001",
            "file_changes": ["src/api/users.py"],
            "git_commit": "abc123"
        }

        checkpoint = await self.manager.create_checkpoint(
            checkpoint_type="manual",
            description="Test metadata",
            context=context
        )

        # Verify metadata preserved
        retrieved = await self.manager.get_checkpoint(checkpoint["id"])
        assert retrieved["context"]["session_id"] == "test-123"
        assert retrieved["context"]["active_task"] == "DEVSTREAM-001"
        assert "src/api/users.py" in retrieved["context"]["file_changes"]


class TestAutoSaveService:
    """Test auto-save service implementation."""

    def setup_method(self):
        """Setup test fixtures."""
        from auto_save_service import AutoSaveService
        self.service = AutoSaveService(interval_seconds=60)

    @pytest.mark.asyncio
    async def test_service_starts_on_init(self):
        """Test that auto-save service starts automatically."""
        # Service should start background task on init
        assert self.service.is_running() is True

    @pytest.mark.asyncio
    async def test_auto_save_interval(self):
        """Test auto-save executes at configured interval."""
        # Set short interval for testing
        service = AutoSaveService(interval_seconds=1)

        # Wait for auto-save
        import asyncio
        await asyncio.sleep(1.5)

        # Verify checkpoint created
        checkpoints = await service.manager.list_checkpoints(limit=5)
        auto_saves = [cp for cp in checkpoints if cp["type"] == "auto"]

        assert len(auto_saves) >= 1

    @pytest.mark.asyncio
    async def test_critical_tool_triggers_save(self):
        """Test that Write/Edit operations trigger auto-save."""
        from auto_save_service import should_trigger_save

        # Critical tools should trigger
        critical_tools = ["Write", "Edit", "MultiEdit"]
        for tool in critical_tools:
            assert should_trigger_save(tool) is True

        # Non-critical tools should not trigger
        assert should_trigger_save("Read") is False
        assert should_trigger_save("Grep") is False

    @pytest.mark.asyncio
    async def test_service_graceful_shutdown(self):
        """Test service shuts down gracefully."""
        await self.service.stop()

        assert self.service.is_running() is False


class TestSlashCommandIntegration:
    """Test /save-progress slash command."""

    @pytest.mark.asyncio
    async def test_slash_command_creates_checkpoint(self):
        """Test /save-progress creates manual checkpoint."""
        from slash_commands import handle_save_progress

        # Execute command
        result = await handle_save_progress()

        assert result["success"] is True
        assert "checkpoint_id" in result
        assert result["type"] == "manual"

    @pytest.mark.asyncio
    async def test_slash_command_with_description(self):
        """Test /save-progress with custom description."""
        from slash_commands import handle_save_progress

        # Execute with description
        result = await handle_save_progress(description="Before refactoring")

        assert result["success"] is True
        assert result["description"] == "Before refactoring"

    @pytest.mark.asyncio
    async def test_slash_command_feedback(self):
        """Test slash command provides user feedback."""
        from slash_commands import handle_save_progress

        # Mock feedback
        with patch('slash_commands.print') as mock_print:
            await handle_save_progress()

            # Verify feedback printed
            assert mock_print.called
            feedback = mock_print.call_args[0][0]
            assert "✅" in feedback or "Checkpoint created" in feedback


class TestPostToolUseHookIntegration:
    """Test PostToolUse hook integration with checkpoints."""

    @pytest.mark.asyncio
    async def test_write_tool_triggers_checkpoint(self):
        """Test that Write tool triggers automatic checkpoint."""
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / '.claude/hooks/devstream/memory'))
        from post_tool_use import PostToolUseHook

        hook = PostToolUseHook()

        # Mock context
        mock_context = Mock()
        mock_context.tool_name = "Write"
        mock_context.tool_input = {
            "file_path": "src/api/users.py",
            "content": "def get_user(): ..."
        }
        mock_context.tool_result = Mock()
        mock_context.tool_result.is_error = False
        mock_context.output = Mock()
        mock_context.output.exit_success = Mock()

        # Process
        with patch.object(hook, 'checkpoint_manager') as mock_manager:
            mock_manager.create_checkpoint = AsyncMock(return_value={"id": "test-123"})

            await hook.process(mock_context)

            # Verify checkpoint created
            assert mock_manager.create_checkpoint.called

    @pytest.mark.asyncio
    async def test_edit_tool_triggers_checkpoint(self):
        """Test that Edit tool triggers automatic checkpoint."""
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / '.claude/hooks/devstream/memory'))
        from post_tool_use import PostToolUseHook

        hook = PostToolUseHook()

        # Mock context
        mock_context = Mock()
        mock_context.tool_name = "Edit"
        mock_context.tool_input = {
            "file_path": "src/api/users.py",
            "old_string": "old code",
            "new_string": "new code"
        }
        mock_context.tool_result = Mock()
        mock_context.tool_result.is_error = False
        mock_context.output = Mock()
        mock_context.output.exit_success = Mock()

        # Process
        with patch.object(hook, 'checkpoint_manager') as mock_manager:
            mock_manager.create_checkpoint = AsyncMock(return_value={"id": "test-456"})

            await hook.process(mock_context)

            # Verify checkpoint created
            assert mock_manager.create_checkpoint.called


class TestCheckpointContextCapture:
    """Test checkpoint captures complete session context."""

    @pytest.mark.asyncio
    async def test_checkpoint_captures_active_task(self):
        """Test checkpoint captures active task."""
        from checkpoint_manager import CheckpointManager

        manager = CheckpointManager(db_path=":memory:")

        # Create checkpoint with task context
        context = {
            "active_task": "DEVSTREAM-001",
            "task_phase": "implementation",
            "progress": "50%"
        }

        checkpoint = await manager.create_checkpoint(
            checkpoint_type="auto",
            description="Auto-save during implementation",
            context=context
        )

        # Verify task context
        retrieved = await manager.get_checkpoint(checkpoint["id"])
        assert retrieved["context"]["active_task"] == "DEVSTREAM-001"
        assert retrieved["context"]["task_phase"] == "implementation"

    @pytest.mark.asyncio
    async def test_checkpoint_captures_file_changes(self):
        """Test checkpoint captures modified files."""
        from checkpoint_manager import CheckpointManager

        manager = CheckpointManager(db_path=":memory:")

        # Simulate file changes
        context = {
            "file_changes": [
                {"path": "src/api/users.py", "operation": "modified"},
                {"path": "tests/test_users.py", "operation": "created"}
            ]
        }

        checkpoint = await manager.create_checkpoint(
            checkpoint_type="auto",
            description="After file changes",
            context=context
        )

        # Verify file changes captured
        retrieved = await manager.get_checkpoint(checkpoint["id"])
        assert len(retrieved["context"]["file_changes"]) == 2

    @pytest.mark.asyncio
    async def test_checkpoint_captures_git_state(self):
        """Test checkpoint captures git commit reference."""
        from checkpoint_manager import CheckpointManager

        manager = CheckpointManager(db_path=":memory:")

        # Simulate git state
        context = {
            "git_commit": "abc123",
            "git_branch": "feature/checkpoint-system"
        }

        checkpoint = await manager.create_checkpoint(
            checkpoint_type="manual",
            description="Before risky changes",
            context=context
        )

        # Verify git state
        retrieved = await manager.get_checkpoint(checkpoint["id"])
        assert retrieved["context"]["git_commit"] == "abc123"
        assert retrieved["context"]["git_branch"] == "feature/checkpoint-system"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
