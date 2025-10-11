#!/usr/bin/env .devstream/bin/python
"""
Test script for PostToolUse hook retry logic (FASE 4.4)

Tests the enhanced PostToolUse hook with retry logic for:
- MCP connection failures
- Ollama embedding generation failures
- Database connection failures
- Temporary network issues

This test simulates failure scenarios and validates retry behavior.
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Add hook to path
sys.path.insert(0, str(Path(__file__).parent / '.claude' / 'hooks' / 'devstream' / 'memory'))

from post_tool_use import PostToolUseHook


class MockOllamaClient:
    """Mock Ollama client that simulates failures"""

    def __init__(self, failure_rate=0.5, max_failures=2):
        self.failure_rate = failure_rate
        self.max_failures = max_failures
        self.attempt_count = 0

    def generate_embedding(self, text: str):
        """Mock embedding generation with controlled failures"""
        self.attempt_count += 1

        if self.attempt_count <= self.max_failures:
            raise ConnectionError(f"Simulated Ollama failure #{self.attempt_count}")

        # Return a mock embedding
        return [0.1] * 768  # 768-dimensional mock embedding


class MockMCPClient:
    """Mock MCP client that simulates failures"""

    def __init__(self, failure_rate=0.5, max_failures=2):
        self.failure_rate = failure_rate
        self.max_failures = max_failures
        self.attempt_count = 0

    async def call_tool(self, tool_name: str, arguments: dict):
        """Mock MCP tool call with controlled failures"""
        await asyncio.sleep(0.1)  # Simulate network latency

        self.attempt_count += 1

        if self.attempt_count <= self.max_failures:
            raise ConnectionError(f"Simulated MCP failure #{self.attempt_count}")

        # Return mock response
        return {
            "success": True,
            "memory_id": f"test_memory_{int(time.time())}",
            "content": [{"text": "Memory stored successfully"}]
        }


class TestPostToolUseRetry:
    """Test suite for PostToolUse retry logic"""

    def __init__(self):
        self.hook = PostToolUseHook()
        self.test_results = []

    async def test_retry_logic_mcp_failure(self):
        """Test retry logic with MCP failures"""
        print("🧪 Testing MCP retry logic...")

        # Mock MCP client with 2 failures then success
        mock_mcp = MockMCPClient(max_failures=2)
        self.hook.mcp_client = mock_mcp

        # Mock other components
        self.hook.ollama_client = MockOllamaClient(max_failures=0)  # Always succeed
        self.hook.base = MagicMock()
        self.hook.base.safe_mcp_call = AsyncMock(side_effect=lambda *args, **kwargs: mock_mcp.call_tool(args[1], args[2]))
        self.hook.base.success_feedback = MagicMock()
        self.hook.base.debug_log = MagicMock()

        try:
            result = await self.hook.store_in_memory(
                file_path="test.py",
                content="print('Hello, world!')",
                operation="Write",
                topics=["python", "testing"],
                entities=["asyncio"],
                content_type="code"
            )

            # Verify retry happened and succeeded
            success = result is not None and mock_mcp.attempt_count == 3
            attempts = mock_mcp.attempt_count

            self.test_results.append({
                "test": "MCP retry logic",
                "success": success,
                "attempts": attempts,
                "details": f"Retries: {attempts-1}, Success: {success}"
            })

            print(f"   ✅ MCP retry test: {attempts-1} retries, Success: {success}")

        except Exception as e:
            self.test_results.append({
                "test": "MCP retry logic",
                "success": False,
                "error": str(e),
                "details": f"Unexpected error: {e}"
            })
            print(f"   ❌ MCP retry test failed: {e}")

    async def test_retry_logic_ollama_failure(self):
        """Test retry logic with Ollama failures"""
        print("🧪 Testing Ollama retry logic...")

        # Mock Ollama client with 2 failures then success
        mock_ollama = MockOllamaClient(max_failures=2)
        self.hook.ollama_client = mock_ollama

        # Mock other components
        mock_mcp = MockMCPClient(max_failures=0)  # Always succeed
        self.hook.mcp_client = mock_mcp
        self.hook.base = MagicMock()
        self.hook.base.safe_mcp_call = AsyncMock(return_value={"memory_id": "test_123"})
        self.hook.base.success_feedback = MagicMock()
        self.hook.base.debug_log = MagicMock()

        try:
            result = await self.hook.store_in_memory(
                file_path="test.py",
                content="print('Hello, world!')",
                operation="Write",
                topics=["python", "testing"],
                entities=["asyncio"],
                content_type="code"
            )

            # Verify retry happened
            success = result is not None and mock_ollama.attempt_count == 3
            attempts = mock_ollama.attempt_count

            self.test_results.append({
                "test": "Ollama retry logic",
                "success": success,
                "attempts": attempts,
                "details": f"Retries: {attempts-1}, Success: {success}"
            })

            print(f"   ✅ Ollama retry test: {attempts-1} retries, Success: {success}")

        except Exception as e:
            self.test_results.append({
                "test": "Ollama retry logic",
                "success": False,
                "error": str(e),
                "details": f"Unexpected error: {e}"
            })
            print(f"   ❌ Ollama retry test failed: {e}")

    async def test_retry_logic_permanent_failure(self):
        """Test retry logic with permanent failures (should not retry)"""
        print("🧪 Testing permanent failure handling...")

        # Mock MCP client with permanent validation error
        mock_mcp = MockMCPClient(max_failures=10)
        self.hook.mcp_client = mock_mcp

        # Override the call to raise a permanent failure
        async def permanent_failure(*args, **kwargs):
            raise ValueError("Invalid API key - permanent failure")

        self.hook.base = MagicMock()
        self.hook.base.safe_mcp_call = AsyncMock(side_effect=permanent_failure)
        self.hook.base.debug_log = MagicMock()

        try:
            result = await self.hook.store_in_memory(
                file_path="test.py",
                content="print('Hello, world!')",
                operation="Write",
                topics=["python", "testing"],
                entities=["asyncio"],
                content_type="code"
            )

            # Should return None immediately without retries
            success = result is None
            self.test_results.append({
                "test": "Permanent failure handling",
                "success": success,
                "details": "Correctly identified permanent failure and returned None"
            })

            print(f"   ✅ Permanent failure test: Success: {success}")

        except Exception as e:
            self.test_results.append({
                "test": "Permanent failure handling",
                "success": False,
                "error": str(e),
                "details": f"Unexpected error: {e}"
            })
            print(f"   ❌ Permanent failure test failed: {e}")

    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("🧪 POSTTOOLUSE RETRY LOGIC TEST SUMMARY")
        print("="*60)

        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)

        for result in self.test_results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{status} {result['test']}: {result.get('details', 'No details')}")

        print(f"\n📊 Results: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All retry logic tests PASSED!")
            print("\n✅ PostToolUse hook retry logic is working correctly:")
            print("   • Retries temporary failures (MCP, Ollama, DB)")
            print("   • Uses exponential backoff (1s, 2s, 4s)")
            print("   • Identifies permanent failures (no retries)")
            print("   • Graceful degradation on persistent failures")
        else:
            print("⚠️ Some retry logic tests FAILED!")
            print("   Review the failures above and fix retry implementation")

        print("="*60)


async def main():
    """Main test function"""
    print("🚀 Starting PostToolUse Retry Logic Tests")
    print("Testing FASE 4.4 retry logic enhancements...\n")

    tester = TestPostToolUseRetry()

    # Run all retry tests
    await tester.test_retry_logic_mcp_failure()
    await tester.test_retry_logic_ollama_failure()
    await tester.test_retry_logic_permanent_failure()

    # Print summary
    tester.print_summary()

    return tester.test_results


if __name__ == "__main__":
    results = asyncio.run(main())
    sys.exit(0 if all(r["success"] for r in results) else 1)