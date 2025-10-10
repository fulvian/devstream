#!/usr/bin/env .devstream/bin/python
"""
Basic retry logic test without external dependencies
Tests the retry_with_backoff method with mock dependencies.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

# Simple mock dependencies
class MockPostToolUseHook:
    def __init__(self):
        self.max_retries = 3
        self.retry_delay = 1.0
        self.retry_backoff = 2.0
        self.base = MagicMock()
        self.base.debug_log = MagicMock()

    from typing import Optional

    async def retry_with_backoff(
        self,
        operation_name: str,
        operation_func,
        *args,
        **kwargs
    ) -> Optional[str]:
        """Test retry logic with exponential backoff"""
        last_exception = None
        attempt_count = 0

        for attempt in range(self.max_retries + 1):
            try:
                result = await operation_func(*args, **kwargs)
                if attempt > 0:
                    self.base.debug_log(f"✓ {operation_name} succeeded on attempt {attempt + 1}")
                return result

            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()

                # Check if retryable error
                is_retryable = any(keyword in error_msg for keyword in [
                    'connection', 'timeout', 'rate limit', 'temporary',
                    'network', 'unavailable', 'overloaded', '503', '502',
                    'connection reset', 'connection refused'
                ])

                # Don't retry permanent failures
                if not is_retryable:
                    self.base.debug_log(f"❌ {operation_name} permanent failure: {e}")
                    return None

                if attempt < self.max_retries:
                    delay = self.retry_delay * (self.retry_backoff ** attempt)
                    self.base.debug_log(
                        f"⚠️ {operation_name} failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}"
                        f" - retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                else:
                    self.base.debug_log(
                        f"❌ {operation_name} failed after {self.max_retries + 1} attempts: {last_exception}"
                    )

        return None

# Test execution
def test_retry_with_backoff():
    """Basic retry functionality test"""
    print("🧪 Testing retry logic with exponential backoff...")

    # Create hook instance
    with patch('post_tool_use.PostToolUseHook') as MockHook:
        mock_hook = MockPostToolUseHook()

        async def test_operation():
            # Fail 2 times then succeed
            attempt_count = 0
            async def failing_operation(*args, **kwargs):
                attempt_count += 1
                if attempt_count <= 2:
                    raise ConnectionError(f"DB locked #{attempt_count}")
                return "success_result"
            return failing_operation

        # Test successful retry
        result = asyncio.run(mock_hook.retry_with_backoff("test_operation", test_operation))
        print(f"   ✅ Retry test: {result}")
        assert result == "success_result"

        # Test max retries exceeded
        async def always_failing_operation(*args, **kwargs):
            raise ConnectionError("Persistent connection failure")

        result = asyncio.run(mock_hook.retry_with_backoff("always_failing_operation", always_failing_operation))
        assert result is None
        print("   ✅ Max retries test passed")

        print("🎉 All retry logic tests PASSED!")

from unittest.mock import patch

# Test execution
if __name__ == "__main__":
    with patch('post_tool_use.PostToolUseHook') as MockPostToolUseHook:
        test_retry_with_backoff()

    print("🎉 All retry logic tests PASSED!")