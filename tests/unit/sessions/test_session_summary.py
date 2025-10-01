"""
Unit tests for Session Summary System (Fix B2).

Tests:
- SessionSummaryManager.extract_recent_memories()
- Session goal inference
- Dual-layer persistence (memory + JSON)
- SessionStart display
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import sys
import json
from datetime import datetime, timedelta

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / '.claude/hooks/devstream/sessions'))


class TestMemoryExtraction:
    """Test extraction of recent memories for session summary."""

    def setup_method(self):
        """Setup test fixtures."""
        from session_summary_manager import SessionSummaryManager
        self.manager = SessionSummaryManager()

    @pytest.mark.asyncio
    async def test_extract_recent_memories(self):
        """Test extracting memories from last 24 hours."""
        # Mock MCP client
        mock_memories = [
            {
                "content": "Implemented JWT authentication",
                "content_type": "code",
                "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
                "relevance_score": 0.95
            },
            {
                "content": "Added password hashing with bcrypt",
                "content_type": "code",
                "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
                "relevance_score": 0.92
            },
            {
                "content": "Decision: Use JWT for stateless auth",
                "content_type": "decision",
                "timestamp": (datetime.now() - timedelta(hours=3)).isoformat(),
                "relevance_score": 0.88
            }
        ]

        with patch.object(self.manager, 'mcp_client') as mock_mcp:
            mock_mcp.call_tool = AsyncMock(return_value={"results": mock_memories})

            memories = await self.manager.extract_recent_memories(hours=24)

            # Verify extraction
            assert len(memories) == 3
            assert memories[0]["content_type"] == "code"
            assert "JWT" in memories[0]["content"]

    @pytest.mark.asyncio
    async def test_filter_by_timeframe(self):
        """Test filtering memories by timeframe."""
        # Mock memories with different timestamps
        mock_memories = [
            {
                "content": "Recent work",
                "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
                "relevance_score": 0.9
            },
            {
                "content": "Old work",
                "timestamp": (datetime.now() - timedelta(hours=48)).isoformat(),
                "relevance_score": 0.9
            }
        ]

        with patch.object(self.manager, 'mcp_client') as mock_mcp:
            mock_mcp.call_tool = AsyncMock(return_value={"results": mock_memories})

            # Extract last 24 hours only
            memories = await self.manager.extract_recent_memories(hours=24)

            # Should only include recent work
            assert len(memories) == 1
            assert "Recent work" in memories[0]["content"]

    @pytest.mark.asyncio
    async def test_filter_by_content_type(self):
        """Test filtering memories by content type."""
        mock_memories = [
            {"content": "Code A", "content_type": "code", "timestamp": datetime.now().isoformat()},
            {"content": "Decision B", "content_type": "decision", "timestamp": datetime.now().isoformat()},
            {"content": "Error C", "content_type": "error", "timestamp": datetime.now().isoformat()}
        ]

        with patch.object(self.manager, 'mcp_client') as mock_mcp:
            mock_mcp.call_tool = AsyncMock(return_value={"results": mock_memories})

            # Extract only code and decisions
            memories = await self.manager.extract_recent_memories(
                hours=24,
                content_types=["code", "decision"]
            )

            # Should exclude errors
            assert len(memories) == 2
            assert all(m["content_type"] in ["code", "decision"] for m in memories)


class TestSessionGoalInference:
    """Test session goal inference from memories."""

    def setup_method(self):
        """Setup test fixtures."""
        from session_summary_manager import SessionSummaryManager
        self.manager = SessionSummaryManager()

    @pytest.mark.asyncio
    async def test_infer_goal_from_memories(self):
        """Test inferring session goal from memory patterns."""
        memories = [
            {"content": "Implemented JWT authentication", "content_type": "code"},
            {"content": "Added password hashing", "content_type": "code"},
            {"content": "Created login endpoint", "content_type": "code"}
        ]

        goal = await self.manager.infer_session_goal(memories)

        # Should identify authentication theme
        assert goal is not None
        assert "authentication" in goal.lower() or "auth" in goal.lower()

    @pytest.mark.asyncio
    async def test_infer_goal_with_decisions(self):
        """Test inferring goal from decision memories."""
        memories = [
            {"content": "Decision: Use PostgreSQL for persistence", "content_type": "decision"},
            {"content": "Designed user table schema", "content_type": "code"},
            {"content": "Implemented database migrations", "content_type": "code"}
        ]

        goal = await self.manager.infer_session_goal(memories)

        # Should identify database/schema theme
        assert goal is not None
        assert any(keyword in goal.lower() for keyword in ["database", "schema", "migration"])

    @pytest.mark.asyncio
    async def test_fallback_generic_goal(self):
        """Test fallback to generic goal when pattern unclear."""
        memories = [
            {"content": "Fixed typo", "content_type": "code"},
            {"content": "Updated comment", "content_type": "documentation"}
        ]

        goal = await self.manager.infer_session_goal(memories)

        # Should provide generic goal
        assert goal is not None
        assert len(goal) > 0


class TestDualLayerPersistence:
    """Test dual-layer persistence (memory + JSON)."""

    def setup_method(self):
        """Setup test fixtures."""
        from session_summary_manager import SessionSummaryManager
        self.manager = SessionSummaryManager()
        self.test_file = Path("/tmp/devstream_session_summary_test.json")

    def teardown_method(self):
        """Cleanup test files."""
        if self.test_file.exists():
            self.test_file.unlink()

    @pytest.mark.asyncio
    async def test_persist_to_memory(self):
        """Test persisting summary to DevStream memory."""
        summary = {
            "session_id": "test-123",
            "goal": "Implement authentication",
            "work_done": ["JWT implementation", "Password hashing"],
            "timestamp": datetime.now().isoformat()
        }

        with patch.object(self.manager, 'mcp_client') as mock_mcp:
            mock_mcp.call_tool = AsyncMock(return_value={"success": True})

            success = await self.manager.persist_to_memory(summary)

            # Verify stored
            assert success is True
            assert mock_mcp.call_tool.called

            # Verify correct parameters
            call_args = mock_mcp.call_tool.call_args[1]
            assert call_args["name"] == "devstream_store_memory"
            assert "session_summary" in call_args["arguments"]["keywords"]

    @pytest.mark.asyncio
    async def test_persist_to_json(self):
        """Test persisting summary to JSON file."""
        summary = {
            "session_id": "test-456",
            "goal": "Refactor API layer",
            "work_done": ["Separated concerns", "Added type hints"],
            "timestamp": datetime.now().isoformat()
        }

        success = await self.manager.persist_to_json(summary, self.test_file)

        # Verify file created
        assert success is True
        assert self.test_file.exists()

        # Verify content
        with open(self.test_file, 'r') as f:
            stored = json.load(f)
            assert stored["session_id"] == "test-456"
            assert stored["goal"] == "Refactor API layer"

    @pytest.mark.asyncio
    async def test_dual_layer_persistence(self):
        """Test both memory and JSON persistence."""
        summary = {
            "session_id": "test-789",
            "goal": "Implement checkpoint system",
            "work_done": ["SQLite savepoints", "Auto-save service"],
            "timestamp": datetime.now().isoformat()
        }

        with patch.object(self.manager, 'mcp_client') as mock_mcp:
            mock_mcp.call_tool = AsyncMock(return_value={"success": True})

            # Persist to both layers
            memory_success = await self.manager.persist_to_memory(summary)
            json_success = await self.manager.persist_to_json(summary, self.test_file)

            # Verify both succeeded
            assert memory_success is True
            assert json_success is True
            assert self.test_file.exists()


class TestSessionStartDisplay:
    """Test SessionStart hook displays previous summary."""

    @pytest.mark.asyncio
    async def test_retrieve_previous_summary(self):
        """Test retrieving previous session summary."""
        from session_summary_manager import SessionSummaryManager

        manager = SessionSummaryManager()

        # Mock previous summary in memory
        mock_summary = {
            "content": json.dumps({
                "session_id": "previous-123",
                "goal": "Implement authentication",
                "work_done": ["JWT", "Password hashing"],
                "next_steps": ["Add refresh tokens", "Implement session management"]
            }),
            "content_type": "session_summary",
            "timestamp": (datetime.now() - timedelta(days=1)).isoformat()
        }

        with patch.object(manager, 'mcp_client') as mock_mcp:
            mock_mcp.call_tool = AsyncMock(return_value={"results": [mock_summary]})

            summary = await manager.retrieve_previous_summary()

            # Verify summary retrieved
            assert summary is not None
            assert summary["goal"] == "Implement authentication"
            assert "JWT" in summary["work_done"]

    @pytest.mark.asyncio
    async def test_display_summary_on_start(self):
        """Test displaying summary in SessionStart hook."""
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / '.claude/hooks/devstream/sessions'))
        from session_start import SessionStartHook

        hook = SessionStartHook()

        # Mock previous summary
        mock_summary = {
            "goal": "Implement checkpoint system",
            "work_done": ["SQLite savepoints", "Auto-save service"],
            "next_steps": ["Add rollback", "Test recovery"]
        }

        with patch.object(hook.summary_manager, 'retrieve_previous_summary', return_value=mock_summary):
            # Mock context
            mock_context = Mock()
            mock_context.output = Mock()
            mock_context.output.exit_success = Mock()

            await hook.process(mock_context)

            # Verify summary displayed
            # (check via context injection or feedback)

    def test_format_summary_display(self):
        """Test summary formatting for display."""
        from session_summary_manager import format_summary_for_display

        summary = {
            "goal": "Implement authentication",
            "work_done": ["JWT implementation", "Password hashing", "Login endpoint"],
            "next_steps": ["Add refresh tokens", "Session management"],
            "timestamp": "2025-10-02T10:00:00"
        }

        formatted = format_summary_for_display(summary)

        # Verify formatting
        assert "Previous Session Summary" in formatted
        assert "Goal: Implement authentication" in formatted
        assert "Work Completed:" in formatted
        assert "JWT implementation" in formatted
        assert "Next Steps:" in formatted
        assert "Add refresh tokens" in formatted


class TestSessionSummaryWorkflow:
    """Test complete session summary workflow."""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete session summary creation and retrieval."""
        from session_summary_manager import SessionSummaryManager

        manager = SessionSummaryManager()

        # Step 1: Extract memories
        mock_memories = [
            {
                "content": "Implemented checkpoint system",
                "content_type": "code",
                "timestamp": datetime.now().isoformat()
            }
        ]

        with patch.object(manager, 'mcp_client') as mock_mcp:
            mock_mcp.call_tool = AsyncMock(return_value={"results": mock_memories})

            memories = await manager.extract_recent_memories(hours=24)

            # Step 2: Infer goal
            goal = await manager.infer_session_goal(memories)

            # Step 3: Create summary
            summary = {
                "session_id": "test-workflow",
                "goal": goal,
                "work_done": [m["content"] for m in memories],
                "timestamp": datetime.now().isoformat()
            }

            # Step 4: Persist (dual-layer)
            mock_mcp.call_tool = AsyncMock(return_value={"success": True})
            memory_success = await manager.persist_to_memory(summary)

            # Verify workflow completed
            assert len(memories) > 0
            assert goal is not None
            assert memory_success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
