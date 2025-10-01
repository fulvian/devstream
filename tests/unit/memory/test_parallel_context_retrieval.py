"""
Test suite for parallel context retrieval optimization.

Tests parallel execution of Context7 and DevStream memory retrieval,
verifying performance improvements and error handling.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path


class TestParallelContextRetrieval:
    """Test parallel context retrieval in pre_tool_use hook."""

    @pytest.fixture
    def mock_hook(self):
        """Create mock PreToolUseHook instance."""
        from unittest.mock import Mock

        hook = Mock()
        hook.base = Mock()
        hook.base.debug_log = Mock()
        hook.base.success_feedback = Mock()
        hook.context7 = Mock()
        hook.mcp_client = Mock()

        return hook

    @pytest.mark.asyncio
    async def test_parallel_execution_both_succeed(self, mock_hook):
        """Test parallel execution when both Context7 and memory succeed."""
        # Import the actual module to get assemble_context method
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".claude/hooks/devstream/memory"))

        from pre_tool_use import PreToolUseHook

        # Create real hook instance with mocked dependencies
        hook = PreToolUseHook()
        hook.base = mock_hook.base

        # Mock both retrieval methods to return successfully
        context7_result = "# Context7 Docs\nSample documentation"
        memory_result = "# DevStream Memory\nSample memory"

        hook.get_context7_docs = AsyncMock(return_value=context7_result)
        hook.get_devstream_memory = AsyncMock(return_value=memory_result)

        # Execute parallel retrieval
        result = await hook.assemble_context(
            file_path="/test/file.py",
            content="test content"
        )

        # Verify both methods were called
        hook.get_context7_docs.assert_called_once()
        hook.get_devstream_memory.assert_called_once()

        # Verify result contains both contexts
        assert context7_result in result
        assert memory_result in result
        assert "Enhanced Context for file.py" in result

        # Verify performance logging
        mock_hook.base.debug_log.assert_called()
        log_calls = [str(call) for call in mock_hook.base.debug_log.call_args_list]
        assert any("Parallel context retrieval completed" in call for call in log_calls)

    @pytest.mark.asyncio
    async def test_parallel_execution_context7_fails(self, mock_hook):
        """Test parallel execution when Context7 fails but memory succeeds."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".claude/hooks/devstream/memory"))

        from pre_tool_use import PreToolUseHook

        hook = PreToolUseHook()
        hook.base = mock_hook.base

        # Mock Context7 to fail, memory to succeed
        memory_result = "# DevStream Memory\nSample memory"

        hook.get_context7_docs = AsyncMock(return_value=None)  # Simulates failure
        hook.get_devstream_memory = AsyncMock(return_value=memory_result)

        result = await hook.assemble_context(
            file_path="/test/file.py",
            content="test content"
        )

        # Verify result contains only memory context
        assert result is not None
        assert memory_result in result
        assert "Context7" not in result

        # Verify both methods were called despite Context7 failure
        hook.get_context7_docs.assert_called_once()
        hook.get_devstream_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_parallel_execution_memory_fails(self, mock_hook):
        """Test parallel execution when memory fails but Context7 succeeds."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".claude/hooks/devstream/memory"))

        from pre_tool_use import PreToolUseHook

        hook = PreToolUseHook()
        hook.base = mock_hook.base

        # Mock Context7 to succeed, memory to fail
        context7_result = "# Context7 Docs\nSample documentation"

        hook.get_context7_docs = AsyncMock(return_value=context7_result)
        hook.get_devstream_memory = AsyncMock(return_value=None)  # Simulates failure

        result = await hook.assemble_context(
            file_path="/test/file.py",
            content="test content"
        )

        # Verify result contains only Context7 context
        assert result is not None
        assert context7_result in result
        assert "Memory" not in result

        # Verify both methods were called despite memory failure
        hook.get_context7_docs.assert_called_once()
        hook.get_devstream_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_parallel_execution_both_fail(self, mock_hook):
        """Test parallel execution when both Context7 and memory fail."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".claude/hooks/devstream/memory"))

        from pre_tool_use import PreToolUseHook

        hook = PreToolUseHook()
        hook.base = mock_hook.base

        # Mock both to fail
        hook.get_context7_docs = AsyncMock(return_value=None)
        hook.get_devstream_memory = AsyncMock(return_value=None)

        result = await hook.assemble_context(
            file_path="/test/file.py",
            content="test content"
        )

        # Verify result is None when both fail
        assert result is None

        # Verify both methods were called
        hook.get_context7_docs.assert_called_once()
        hook.get_devstream_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_performance_improvement(self, mock_hook):
        """Test that parallel execution is faster than sequential."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".claude/hooks/devstream/memory"))

        from pre_tool_use import PreToolUseHook

        hook = PreToolUseHook()
        hook.base = mock_hook.base

        # Mock methods with realistic delays
        async def slow_context7(*args, **kwargs):
            await asyncio.sleep(0.5)  # 500ms
            return "# Context7 Docs"

        async def slow_memory(*args, **kwargs):
            await asyncio.sleep(0.5)  # 500ms
            return "# Memory Context"

        hook.get_context7_docs = slow_context7
        hook.get_devstream_memory = slow_memory

        import time
        start = time.time()
        result = await hook.assemble_context(
            file_path="/test/file.py",
            content="test content"
        )
        elapsed = time.time() - start

        # Verify result exists
        assert result is not None

        # Parallel execution should take ~500ms (not 1000ms sequential)
        # Allow 200ms margin for overhead
        assert elapsed < 0.7, f"Parallel execution too slow: {elapsed:.2f}s (expected <0.7s)"

        # Sequential would take ~1000ms, parallel should be significantly faster
        print(f"Parallel execution completed in {elapsed:.2f}s (target: <0.7s)")

    @pytest.mark.asyncio
    async def test_performance_logging_format(self, mock_hook):
        """Test that performance metrics are logged correctly."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".claude/hooks/devstream/memory"))

        from pre_tool_use import PreToolUseHook

        hook = PreToolUseHook()
        hook.base = mock_hook.base

        # Mock both methods
        hook.get_context7_docs = AsyncMock(return_value="# Context7")
        hook.get_devstream_memory = AsyncMock(return_value="# Memory")

        result = await hook.assemble_context(
            file_path="/test/file.py",
            content="test content"
        )

        # Verify performance log format
        log_calls = [str(call) for call in mock_hook.base.debug_log.call_args_list]
        perf_logs = [log for log in log_calls if "Parallel context retrieval completed" in log]

        assert len(perf_logs) > 0, "Performance log not found"

        # Check log contains timing and status indicators
        perf_log = perf_logs[0]
        assert "ms" in perf_log, "Log missing timing information"
        assert "✓" in perf_log or "✗" in perf_log, "Log missing status indicators"
        assert "Context7" in perf_log, "Log missing Context7 status"
        assert "Memory" in perf_log, "Log missing Memory status"

    @pytest.mark.asyncio
    async def test_token_budget_preservation(self, mock_hook):
        """Test that token budgets are preserved (Context7: 5000, Memory: 2000)."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".claude/hooks/devstream/memory"))

        from pre_tool_use import PreToolUseHook

        hook = PreToolUseHook()
        hook.base = mock_hook.base

        # Create large responses to test token budgets
        large_context7 = "# Context7\n" + "x" * 10000  # Large response
        large_memory = "# Memory\n" + "y" * 10000     # Large response

        hook.get_context7_docs = AsyncMock(return_value=large_context7)
        hook.get_devstream_memory = AsyncMock(return_value=large_memory)

        result = await hook.assemble_context(
            file_path="/test/file.py",
            content="test content"
        )

        # Verify both contexts are included (budget enforcement happens in individual methods)
        assert result is not None
        assert "Context7" in result
        assert "Memory" in result

        # Note: Token budget enforcement is in get_context7_docs and get_devstream_memory
        # This test verifies parallel execution doesn't break that mechanism


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
