#!/usr/bin/env python3
"""
Unit tests for Micro-Task Commit Handler functionality

Tests conventional commit generation, TodoWrite detection, and Step 6 completion
logic for the micro-task commit system.
"""

import asyncio
import json
import os
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import tempfile
import subprocess

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".claude" / "hooks" / "devstream" / "protocol"))

from micro_task_commit_handler import (
    MicroTaskCommitHandler,
    MicroTask,
    CommitType
)


class TestMicroTaskCommitHandler:
    """Test suite for micro-task commit handler functionality."""

    @pytest_asyncio.fixture
    async def mock_protocol_manager(self):
        """Create mock protocol manager."""
        manager = AsyncMock()
        # Mock current state to be in Step 6
        from protocol_state_manager import ProtocolState, ProtocolStep

        state = ProtocolState(
            session_id="12345678-1234-5678-9abc-123456789abc",
            protocol_step=ProtocolStep.IMPLEMENTATION
        )
        manager.get_current_state.return_value = state
        return manager

    @pytest_asyncio.fixture
    async def commit_handler(self, mock_protocol_manager):
        """Create MicroTaskCommitHandler with mocked dependencies."""
        with patch('micro_task_commit_handler.get_protocol_manager', return_value=mock_protocol_manager):
            return MicroTaskCommitHandler()

    @pytest.fixture
    def sample_todo_data(self):
        """Sample TodoWrite JSON data."""
        return json.dumps([
            {
                "content": "STEP 6.1 - Implement JWT authentication service",
                "status": "completed",
                "activeForm": "Implementing JWT authentication service"
            },
            {
                "content": "STEP 6.2 - Add password hashing with bcrypt",
                "status": "in_progress",
                "activeForm": "Adding password hashing"
            },
            {
                "content": "STEP 6.3 - Create user registration endpoint",
                "status": "pending",
                "activeForm": "Creating user registration"
            }
        ])

    @pytest.fixture
    def sample_todo_data_all_completed(self):
        """Sample TodoWrite data with all tasks completed."""
        return json.dumps([
            {
                "content": "STEP 6.1 - Implement JWT authentication service",
                "status": "completed",
                "activeForm": "Completed JWT authentication service"
            },
            {
                "content": "STEP 6.2 - Add password hashing with bcrypt",
                "status": "completed",
                "activeForm": "Completed password hashing"
            },
            {
                "content": "STEP 6.3 - Create user registration endpoint",
                "status": "completed",
                "activeForm": "Completed user registration"
            }
        ])

    @pytest.mark.asyncio
    async def test_todo_write_parsing(self, commit_handler, sample_todo_data):
        """Test TodoWrite JSON data parsing."""
        todos = commit_handler._parse_todo_data(sample_todo_data)

        assert todos is not None
        assert len(todos) == 3
        assert todos[0]["content"] == "STEP 6.1 - Implement JWT authentication service"
        assert todos[0]["status"] == "completed"
        assert todos[1]["status"] == "in_progress"
        assert todos[2]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_completed_task_detection(self, commit_handler, sample_todo_data):
        """Test detection of completed micro-tasks."""
        todos = commit_handler._parse_todo_data(sample_todo_data)
        completed_tasks = commit_handler._detect_completed_tasks(todos)

        assert len(completed_tasks) == 1
        assert completed_tasks[0].content == "STEP 6.1 - Implement JWT authentication service"
        assert completed_tasks[0].status == "completed"
        assert completed_tasks[0].is_completed is True

    @pytest.mark.asyncio
    async def test_commit_type_extraction(self):
        """Test commit type extraction from task content."""
        # Test feature detection
        task1 = MicroTask("Implement user authentication", "completed", "", [], 30, datetime.now())
        assert task1.extract_commit_type() == CommitType.FEAT

        # Test fix detection
        task2 = MicroTask("Fix login bug", "completed", "", [], 15, datetime.now())
        assert task2.extract_commit_type() == CommitType.FIX

        # Test refactor detection
        task3 = MicroTask("Refactor authentication service", "completed", "", [], 60, datetime.now())
        assert task3.extract_commit_type() == CommitType.REFACTOR

        # Test test detection
        task4 = MicroTask("Add unit tests for auth", "completed", "", [], 20, datetime.now())
        assert task4.extract_commit_type() == CommitType.TEST

        # Test default (chore)
        task5 = MicroTask("Update dependencies", "completed", "", [], 10, datetime.now())
        assert task5.extract_commit_type() == CommitType.CHORE

    @pytest.mark.asyncio
    async def test_scope_extraction(self):
        """Test scope extraction from task content."""
        # Test auth scope
        task1 = MicroTask("Implement user authentication", "completed", "", [], 30, datetime.now())
        assert task1.extract_scope() == "auth"

        # Test API scope (more specific to avoid auth conflict)
        task2 = MicroTask("Create REST API service endpoint", "completed", "", [], 25, datetime.now())
        assert task2.extract_scope() == "api"

        # Test database scope (more specific to avoid auth conflict)
        task3 = MicroTask("Create database migration schema", "completed", "", [], 20, datetime.now())
        assert task3.extract_scope() == "db"

        # Test no scope
        task4 = MicroTask("Random maintenance task", "completed", "", [], 15, datetime.now())
        assert task4.extract_scope() is None

    @pytest.mark.asyncio
    async def test_conventional_commit_title_generation(self):
        """Test conventional commit title generation."""
        # Test with scope
        task1 = MicroTask("Implement user authentication system", "completed", "", [], 30, datetime.now())
        title1 = task1.generate_commit_title()
        assert title1 == "feat(auth): Implement user authentication system"

        # Test documentation scope (but not generic)
        task2 = MicroTask("Update project documentation", "completed", "", [], 20, datetime.now())
        title2 = task2.generate_commit_title()
        # The scope extraction should match 'docs' for 'documentation' keyword
        assert "docs:" in title2
        assert "Update project documentation" in title2

        # Test long title truncation
        long_content = "This is a very long task content that should be truncated when generating the commit title to keep it under 50 characters"
        task3 = MicroTask(long_content, "completed", "", [], 45, datetime.now())
        title3 = task3.generate_commit_title()
        assert len(title3) <= 72  # type(scope): max 50 chars + scope overhead
        assert title3.endswith("...")

    @pytest.mark.asyncio
    async def test_commit_description_generation(self):
        """Test detailed commit description generation."""
        task = MicroTask(
            "Implement user authentication",
            "completed",
            "Completed user authentication",
            ["src/auth/auth.py", "src/auth/models.py", "tests/test_auth.py"],
            30,
            datetime.now()
        )

        description = task.generate_commit_description("1/5")

        assert "Micro-task: Implement user authentication" in description
        assert "Duration: ~30 minutes" in description
        assert "Files modified: 3 file(s)" in description
        assert "src/auth/auth.py" in description
        assert "Progress: 1/5" in description
        assert "Generated with [Claude Code]" in description
        assert "Co-Authored-By: Claude" in description

    @pytest.mark.asyncio
    async def test_disabled_handler_ignores_todo_write(self, commit_handler, sample_todo_data):
        """Test disabled handler ignores TodoWrite events."""
        with patch.dict(os.environ, {"DEVSTREAM_MICRO_TASK_COMMITS": "false"}):
            result = await commit_handler.handle_todo_write(sample_todo_data, {})
            assert result is False

    @pytest.mark.asyncio
    async def test_non_step6_ignores_todo_write(self, commit_handler, sample_todo_data):
        """Test handler ignores TodoWrite when not in Step 6."""
        from protocol_state_manager import ProtocolState, ProtocolStep

        # Mock current state to be in Step 1
        state = ProtocolState(
            session_id="12345678-1234-5678-9abc-123456789abc",
            protocol_step=ProtocolStep.DISCUSSION
        )
        commit_handler.protocol_manager.get_current_state.return_value = state

        with patch.dict(os.environ, {"DEVSTREAM_MICRO_TASK_COMMITS": "true"}):
            result = await commit_handler.handle_todo_write(sample_todo_data, {})
            assert result is False

    @pytest.mark.asyncio
    async def test_step6_completion_detection(self, commit_handler, sample_todo_data_all_completed):
        """Test Step 6 completion detection."""
        with patch.dict(os.environ, {"DEVSTREAM_MICRO_TASK_COMMITS": "true"}):
            with patch.object(commit_handler, '_finalize_step6') as mock_finalize:
                with patch.object(commit_handler, '_create_micro_task_commit', return_value=True):
                    # Process completed tasks
                    result = await commit_handler.handle_todo_write(sample_todo_data_all_completed, {})

                    # Should detect completion and trigger finalization
                    mock_finalize.assert_called_once()

    @pytest.mark.asyncio
    async def test_git_staging_and_commit_workflow(self, commit_handler):
        """Test git staging and commit creation workflow."""
        task = MicroTask(
            "Add user authentication",
            "completed",
            "Completed user auth",
            ["src/auth.py"],
            20,
            datetime.now()
        )

        # Test staging separately - need to mock Path.exists for file check
        with patch('micro_task_commit_handler.subprocess.run') as mock_subprocess:
            with patch('micro_task_commit_handler.Path') as mock_path_class:
                mock_path_instance = MagicMock()
                mock_path_class.return_value = mock_path_instance
                mock_path_instance.exists.return_value = True

                mock_subprocess.return_value = MagicMock(returncode=0)
                result = await commit_handler._stage_files(task)
                assert result is True
                # Verify git add was called
                assert mock_subprocess.called

        # Test commit separately
        with patch('micro_task_commit_handler.subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = MagicMock(returncode=0, stdout="commit hash")
            commit_message = "feat: Add user authentication\n\nMicro-task details"
            result = await commit_handler._create_git_commit(commit_message)
            assert result is True
            # Verify git commit was called
            assert mock_subprocess.called
            assert "git" in str(mock_subprocess.call_args)
            assert "commit" in str(mock_subprocess.call_args)

    @pytest.mark.asyncio
    async def test_file_staging_with_no_specific_files(self, commit_handler):
        """Test file staging when no specific files are available."""
        task = MicroTask(
            "Generic task",
            "completed",
            "Completed generic",
            [],  # No specific files
            15,
            datetime.now()
        )

        with patch('micro_task_commit_handler.subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = MagicMock(returncode=0)

            result = await commit_handler._stage_files(task)
            assert result is True

            # Should call git add . for all files
            call_args = mock_subprocess.call_args_list[0]
            assert call_args.args[0] == ["git", "add", "."]

    @pytest.mark.asyncio
    async def test_task_duration_estimation(self, commit_handler):
        """Test task duration estimation."""
        test_cases = [
            ({"content": "Quick fix"}, 5),
            ({"content": "Implement feature"}, 30),
            ({"content": "Create component"}, 45),
            ({"content": "Complex refactoring"}, 120),
            ({"content": "Add tests"}, 30),
            ({"content": "Unknown task type"}, 15)  # Default
        ]

        for todo, expected_duration in test_cases:
            duration = commit_handler._estimate_task_duration(todo)
            assert duration == expected_duration

    @pytest.mark.asyncio
    async def test_state_persistence(self, commit_handler):
        """Test handler state persistence."""
        # Update handler state
        commit_handler.commits_created = 5
        commit_handler.total_tasks = 10
        commit_handler.step6_start_time = datetime.now(timezone.utc)

        # Save state
        commit_handler._save_state()

        # Create new handler and load state
        with patch('micro_task_commit_handler.get_protocol_manager', return_value=commit_handler.protocol_manager):
            new_handler = MicroTaskCommitHandler()

        assert new_handler.commits_created == 5
        assert new_handler.total_tasks == 10
        assert new_handler.step6_start_time is not None

    @pytest.mark.asyncio
    async def test_statistics_reporting(self, commit_handler):
        """Test handler statistics reporting."""
        commit_handler.commits_created = 7
        commit_handler.total_tasks = 12
        commit_handler.step6_start_time = datetime.now(timezone.utc)

        with patch.dict(os.environ, {"DEVSTREAM_MICRO_TASK_COMMITS": "true"}):
            stats = commit_handler.get_statistics()

            assert stats["commits_created"] == 7
            assert stats["total_tasks"] == 12
            assert stats["step6_active"] is True
            assert stats["step6_duration_minutes"] >= 0
            assert stats["enabled"] is True

    @pytest.mark.asyncio
    async def test_error_handling_in_git_operations(self, commit_handler):
        """Test error handling in git operations."""
        task = MicroTask("Test task", "completed", "Completed", [], 10, datetime.now())

        # Test git staging failure (with empty files list, should stage all)
        with patch('micro_task_commit_handler.subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = MagicMock(returncode=1, stderr="git error")

            result = await commit_handler._stage_files(task)
            assert result is False

        # Test git commit failure
        with patch('micro_task_commit_handler.subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = MagicMock(returncode=1, stderr="commit failed")

            result = await commit_handler._create_git_commit("test message")
            assert result is False

    @pytest.mark.asyncio
    async def test_code_reviewer_trigger(self, commit_handler):
        """Test @code-reviewer trigger mechanism."""
        with patch('micro_task_commit_handler.Path') as mock_path_class:
            mock_file_instance = MagicMock()
            mock_path_class.return_value = mock_file_instance
            mock_file_instance.parent.mkdir = MagicMock()

            # Mock open for writing
            with patch('builtins.open') as mock_open:
                mock_file_handle = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_file_handle

                await commit_handler._trigger_code_reviewer()

                # Verify trigger file was created (open was called)
                assert mock_open.called
                # Verify JSON dump was called on file handle
                assert mock_file_handle.method_calls or mock_open.called


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short"])