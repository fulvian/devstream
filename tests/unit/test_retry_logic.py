#!/usr/bin/env .devstream/bin/python
"""
Simplified retry logic test for PostToolUse hook (FASE 4.4)

Tests only the retry_with_backoff method directly without dependencies.
"""

import sys
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'memory'))

from post_tool_use import PostToolUseHook


class TestRetryLogicOnly:
    """Test suite for retry logic functionality"""

    @pytest.fixture
    def hook(self):
        """Create a PostToolUseHook instance for testing"""
        with patch('post_tool_use.DevStreamHookBase'):
            hook = PostToolUseHook()
            hook.base = MagicMock()
            hook.base.should_run.return_value = True
            hook.base.is_memory_store_enabled.return_value = True
            hook.base.debug_log = MagicMock()
            hook.base.success_feedback = MagicMock()
            hook.base.warning_feedback = MagicMock()
            return hook

    async def test_retry_logic_with_exponential_backoff(self, hook):
        """Test exponential backoff timing calculation"""
        attempt_count = 0
        delays = []

        async def failing_operation(*args, **kwargs):
            nonlocal attempt_count, delays
            attempt_count += 1
            delays.append(hook.retry_delay * (hook.retry_backoff ** (attempt_count - 1)))
            raise ConnectionError(f"Attempt {attempt_count}")

        result = await hook.retry_with_backoff(
            "test_backoff",
            failing_operation
        )

        # Verify delays: should be 1s, 2s (2 attempts failed)
        assert len(delays) == 2
        assert delays[0] == 1.0  # First delay
        assert delays[1] == 2.0  # Second delay (1.0 * 2.0)

        # Should fail after 4 attempts (3 retries + 1 initial)
        assert result is None

    async def test_retry_logic_permanent_failure_no_retry(self, hook):
        """Test permanent failure detection"""
        attempt_count = 0

        async def permanent_failure(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Permanent failure")

        result = await hook.retry_with_backoff(
            "permanent_operation",
            permanent_failure
        )

        # Should not retry for permanent failures
        assert result is None
        assert attempt_count == 1

    async def test_retry_logic_successful_on_first_try(self, hook):
        """Test successful operation without retries"""
        async def successful_operation(*args, **kwargs):
            return "success_result"

        result = await hook.retry_with_backoff(
            "successful_operation",
            successful_operation
        )

        assert result == "success_result"
        # Should not trigger retries for successful operation
        assert attempt_count == 1

    async def test_retry_logic_retry_count_tracking(self, hook):
        """Test retry count tracking"""
        attempt_count = 0

        async def failing_operation(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 4:
                raise ConnectionError(f"Retry attempt {attempt_count}")
            return "success_result"

        result = await hook.retry_with_backoff(
            "retry_count_tracking",
            failing_operation
        )

        assert result == "success_result"
        assert attempt_count == 4  # 3 retries + 1 initial try

    def test_retry_configuration(self, hook):
        """Test retry configuration values"""
        assert hook.max_retries == 3
        assert hook.retry_delay == 1.0
        assert hook.retry_backoff == 2.0

    async def test_retry_error_logging(self, hook):
        """Test retry error logging"""
        attempt_count = 0

        async def failing_operation(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            raise ConnectionError(f"Failure #{attempt_count}")

        with patch.objectify(hook) as mock_hook:
            mock_hook.base.debug_log.assert_any_call(
                lambda msg: "test_retry_logging failed" in msg
            )

        result = await hook.retry_with_backoff(
            "error_logging",
            failing_operation
        )

        assert result is None
        assert attempt_count == 4


# Test execution
if __name__ == "__main__":
    pytest.main([__file__])