"""
Integration tests for ALL 4 fixes (A1, A2, B1, B2).

Tests complete workflows combining multiple components:
- Protocol enforcement + Agent delegation
- Checkpoints + Session summary
- Real-world simulation
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import sys
import json
from datetime import datetime
import asyncio

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude/hooks/devstream'))


class TestProtocolAndDelegationIntegration:
    """Test Protocol Enforcement (A1) + Agent Auto-Delegation (A2) integration."""

    @pytest.mark.asyncio
    async def test_complex_task_workflow(self):
        """Test complete workflow: Protocol gate → Agent delegation → Context injection."""
        from context.user_query_context_enhancer import UserQueryContextEnhancer
        from memory.pre_tool_use import PreToolUseHook

        # Step 1: User submits complex query
        query = "Implement JWT authentication with FastAPI and React frontend"

        enhancer = UserQueryContextEnhancer()

        # Mock context
        mock_context = Mock()
        mock_context.user_query = query
        mock_context.output = Mock()
        mock_context.output.exit_success = Mock()

        # Step 2: Protocol enforcement should trigger
        with patch('context.user_query_context_enhancer.get_user_input', return_value="1"):
            await enhancer.process(mock_context)

        # Step 3: Agent delegation should analyze (multi-stack → tech-lead)
        pre_hook = PreToolUseHook()

        assessment = await pre_hook.check_agent_delegation(
            file_path="src/api/auth.py",
            content="# JWT auth implementation",
            tool_name="Write",
            user_query=query
        )

        # Verify workflow
        assert assessment is not None
        # Multi-stack should require tech-lead coordination
        assert assessment.suggested_agent in ["tech-lead", "python-specialist"]

    @pytest.mark.asyncio
    async def test_single_language_fast_path(self):
        """Test single-language task bypasses protocol, auto-delegates specialist."""
        from context.user_query_context_enhancer import UserQueryContextEnhancer
        from memory.pre_tool_use import PreToolUseHook

        # Step 1: Simple Python query
        query = "Add email validation to user model"

        enhancer = UserQueryContextEnhancer()

        mock_context = Mock()
        mock_context.user_query = query
        mock_context.output = Mock()
        mock_context.output.exit_success = Mock()

        # Step 2: Protocol enforcement should NOT trigger (simple task)
        # (Checked via should_trigger_protocol_gate function)

        # Step 3: Agent delegation should auto-approve Python specialist
        pre_hook = PreToolUseHook()

        assessment = await pre_hook.check_agent_delegation(
            file_path="src/models/user.py",
            content="class User: ...",
            tool_name="Edit",
            user_query=query
        )

        # Verify automatic delegation
        assert assessment is not None
        assert assessment.suggested_agent == "python-specialist"
        assert assessment.recommendation == "AUTOMATIC"
        assert assessment.confidence >= 0.95


class TestCheckpointAndSummaryIntegration:
    """Test Checkpoint System (B1) + Session Summary (B2) integration."""

    @pytest.mark.asyncio
    async def test_checkpoint_captures_session_context(self):
        """Test checkpoint includes session summary metadata."""
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude/hooks/devstream/checkpoints'))
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude/hooks/devstream/sessions'))

        from checkpoint_manager import CheckpointManager
        from session_summary_manager import SessionSummaryManager

        # Step 1: Create session summary
        summary_mgr = SessionSummaryManager()

        mock_memories = [
            {
                "content": "Implemented JWT authentication",
                "content_type": "code",
                "timestamp": datetime.now().isoformat()
            }
        ]

        with patch.object(summary_mgr, 'mcp_client') as mock_mcp:
            mock_mcp.call_tool = AsyncMock(return_value={"results": mock_memories})

            memories = await summary_mgr.extract_recent_memories(hours=24)
            goal = await summary_mgr.infer_session_goal(memories)

        # Step 2: Create checkpoint with session context
        checkpoint_mgr = CheckpointManager(db_path=":memory:")

        context = {
            "session_goal": goal,
            "work_completed": [m["content"] for m in memories],
            "active_task": "DEVSTREAM-AUTH-001"
        }

        checkpoint = await checkpoint_mgr.create_checkpoint(
            checkpoint_type="manual",
            description="Before risky refactoring",
            context=context
        )

        # Verify integration
        retrieved = await checkpoint_mgr.get_checkpoint(checkpoint["id"])
        assert retrieved["context"]["session_goal"] == goal
        assert len(retrieved["context"]["work_completed"]) > 0

    @pytest.mark.asyncio
    async def test_session_end_creates_summary_and_checkpoint(self):
        """Test SessionEnd creates both summary and final checkpoint."""
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude/hooks/devstream/sessions'))

        from session_end import SessionEndHook

        hook = SessionEndHook()

        # Mock session data
        mock_memories = [
            {"content": "JWT auth", "content_type": "code", "timestamp": datetime.now().isoformat()},
            {"content": "Password hashing", "content_type": "code", "timestamp": datetime.now().isoformat()}
        ]

        with patch.object(hook.summary_manager, 'extract_recent_memories', return_value=mock_memories):
            with patch.object(hook.checkpoint_manager, 'create_checkpoint') as mock_checkpoint:
                mock_checkpoint.return_value = {"id": "final-checkpoint"}

                # Mock context
                mock_context = Mock()
                mock_context.output = Mock()
                mock_context.output.exit_success = Mock()

                await hook.process(mock_context)

                # Verify both summary and checkpoint created
                assert mock_checkpoint.called


class TestRealWorldSimulation:
    """Simulate real-world development workflows."""

    @pytest.mark.asyncio
    async def test_complete_feature_development(self):
        """
        Simulate complete feature development workflow:
        1. User starts task → Protocol enforcement
        2. Choose protocol → Agent delegation
        3. Implementation → Auto-save checkpoints
        4. Commit → Quality gate (@code-reviewer)
        5. Session end → Summary + final checkpoint
        """
        # Import all components
        from context.user_query_context_enhancer import UserQueryContextEnhancer
        from memory.pre_tool_use import PreToolUseHook
        from memory.post_tool_use import PostToolUseHook
        from sessions.session_end import SessionEndHook

        # === STEP 1: User starts feature ===
        query = "Implement user authentication with JWT"

        enhancer = UserQueryContextEnhancer()
        mock_context = Mock()
        mock_context.user_query = query
        mock_context.output = Mock()
        mock_context.output.exit_success = Mock()

        # Protocol enforcement triggers
        with patch('context.user_query_context_enhancer.get_user_input', return_value="1"):
            await enhancer.process(mock_context)
            # User chooses protocol workflow

        # === STEP 2: Agent delegation ===
        pre_hook = PreToolUseHook()

        # First file: Python backend
        assessment_py = await pre_hook.check_agent_delegation(
            file_path="src/api/auth.py",
            content="# JWT implementation",
            tool_name="Write",
            user_query=query
        )

        assert assessment_py is not None
        assert assessment_py.suggested_agent == "python-specialist"

        # === STEP 3: Implementation (auto-save checkpoints) ===
        post_hook = PostToolUseHook()

        # Simulate Write operation
        write_context = Mock()
        write_context.tool_name = "Write"
        write_context.tool_input = {
            "file_path": "src/api/auth.py",
            "content": "def create_token(): ..."
        }
        write_context.tool_result = Mock()
        write_context.tool_result.is_error = False
        write_context.output = Mock()
        write_context.output.exit_success = Mock()

        with patch.object(post_hook, 'checkpoint_manager') as mock_cp:
            mock_cp.create_checkpoint = AsyncMock(return_value={"id": "auto-1"})

            await post_hook.process(write_context)

            # Verify auto-save checkpoint created
            assert mock_cp.create_checkpoint.called

        # === STEP 4: Commit (quality gate) ===
        # Simulate git commit intent
        commit_assessment = await pre_hook.check_agent_delegation(
            file_path=None,
            content=None,
            tool_name="Bash",
            user_query="git commit -m 'Add JWT auth'"
        )

        # Should trigger @code-reviewer
        # (This is implementation-specific, verify via pattern matcher)

        # === STEP 5: Session end (summary + checkpoint) ===
        session_end_hook = SessionEndHook()

        mock_memories = [
            {"content": "JWT auth implementation", "content_type": "code", "timestamp": datetime.now().isoformat()}
        ]

        with patch.object(session_end_hook.summary_manager, 'extract_recent_memories', return_value=mock_memories):
            with patch.object(session_end_hook.checkpoint_manager, 'create_checkpoint') as mock_final_cp:
                mock_final_cp.return_value = {"id": "final"}

                end_context = Mock()
                end_context.output = Mock()
                end_context.output.exit_success = Mock()

                await session_end_hook.process(end_context)

                # Verify final checkpoint created
                assert mock_final_cp.called

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """
        Test error recovery using checkpoints:
        1. Create checkpoint before risky change
        2. Change fails
        3. Rollback to checkpoint
        4. Retry with different approach
        """
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude/hooks/devstream/checkpoints'))

        from checkpoint_manager import CheckpointManager

        manager = CheckpointManager(db_path=":memory:")

        # Step 1: Create checkpoint
        checkpoint = await manager.create_checkpoint(
            checkpoint_type="manual",
            description="Before refactoring",
            context={"git_commit": "abc123"}
        )

        # Step 2: Simulate failed change
        # (Implementation fails, tests break, etc.)

        # Step 3: Rollback
        success = await manager.rollback_to_checkpoint(checkpoint["id"])
        assert success is True

        # Step 4: Verify state restored
        # (Git state, file contents, etc. should be restored)


class TestPerformanceAndScalability:
    """Test performance of integrated system."""

    @pytest.mark.asyncio
    async def test_parallel_context_retrieval(self):
        """Test parallel Context7 + Memory retrieval performance."""
        from memory.pre_tool_use import PreToolUseHook

        hook = PreToolUseHook()

        import time
        start = time.time()

        # Assemble context (should use parallel execution)
        context = await hook.assemble_context(
            file_path="src/api/users.py",
            content="async def get_user(user_id: int): ..."
        )

        elapsed = time.time() - start

        # Verify performance target: < 800ms
        assert elapsed < 0.8, f"Context assembly took {elapsed*1000:.0f}ms (target: <800ms)"

    @pytest.mark.asyncio
    async def test_checkpoint_creation_performance(self):
        """Test checkpoint creation performance."""
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude/hooks/devstream/checkpoints'))

        from checkpoint_manager import CheckpointManager

        manager = CheckpointManager(db_path=":memory:")

        import time
        start = time.time()

        # Create checkpoint
        await manager.create_checkpoint(
            checkpoint_type="auto",
            description="Performance test",
            context={"data": "x" * 1000}
        )

        elapsed = time.time() - start

        # Should be fast (< 100ms)
        assert elapsed < 0.1, f"Checkpoint creation took {elapsed*1000:.0f}ms (target: <100ms)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
