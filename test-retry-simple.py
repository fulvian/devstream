#!/usr/bin/env .devstream/bin/python
"""
Simple test for PostToolUse hook retry logic (FASE 4.4)

Tests the retry_with_backoff method directly with simulated failures.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add hook to path
sys.path.insert(0, str(Path(__file__).parent / '.claude' / 'hooks' / 'devstream' / 'memory'))

from post_tool_use import PostToolUseHook


class SimpleRetryTest:
    """Simple test for retry logic"""

    def __init__(self):
        self.hook = PostToolUseHook()
        self.attempt_count = 0

    async def failing_operation(self, fail_times=2, final_result="success"):
        """Operation that fails specified times, then succeeds"""
        self.attempt_count += 1

        if self.attempt_count <= fail_times:
            error_type = "connection" if self.attempt_count <= 1 else "timeout"
            raise ConnectionError(f"Simulated {error_type} error #{self.attempt_count}")

        return final_result

    async def permanent_failure_operation(self):
        """Operation that always fails with permanent error"""
        raise ValueError("Invalid API key - permanent failure")

    async def test_retry_success_after_failures(self):
        """Test retry logic succeeds after temporary failures"""
        print("🧪 Testing retry logic with temporary failures...")

        self.attempt_count = 0
        start_time = time.time()

        try:
            result = await self.hook.retry_with_backoff(
                "test_operation",
                self.failing_operation,
                fail_times=2,
                final_result="retry_success"
            )

            elapsed = time.time() - start_time

            # Expected: 3 attempts (2 failures + 1 success)
            success = (
                result == "retry_success" and
                self.attempt_count == 3 and
                elapsed >= 3.0  # Should wait 1s + 2s = 3s minimum
            )

            print(f"   ✅ Retry test: {self.attempt_count} attempts, {elapsed:.1f}s elapsed, Success: {success}")
            return success

        except Exception as e:
            print(f"   ❌ Retry test failed: {e}")
            return False

    async def test_permanent_failure_no_retry(self):
        """Test that permanent failures don't trigger retries"""
        print("🧪 Testing permanent failure handling...")

        start_time = time.time()

        try:
            result = await self.hook.retry_with_backoff(
                "permanent_fail_operation",
                self.permanent_failure_operation
            )

            elapsed = time.time() - start_time
            success = result is None and elapsed < 1.0  # Should fail immediately

            print(f"   ✅ Permanent failure test: {elapsed:.1f}s elapsed, No retry: {success}")
            return success

        except Exception as e:
            print(f"   ❌ Permanent failure test failed: {e}")
            return False

    async def test_max_retries_exceeded(self):
        """Test behavior when max retries are exceeded"""
        print("🧪 Testing max retries exceeded...")

        self.attempt_count = 0
        start_time = time.time()

        try:
            result = await self.hook.retry_with_backoff(
                "max_retry_operation",
                self.failing_operation,
                fail_times=10,  # More than max_retries (3)
                final_result="wont_reach"
            )

            elapsed = time.time() - start_time

            # Expected: 4 attempts (max_retries + 1) and None result
            success = (
                result is None and
                self.attempt_count == 4 and
                elapsed >= 7.0  # Should wait 1s + 2s + 4s = 7s minimum
            )

            print(f"   ✅ Max retries test: {self.attempt_count} attempts, {elapsed:.1f}s elapsed, Success: {success}")
            return success

        except Exception as e:
            print(f"   ❌ Max retries test failed: {e}")
            return False

    def print_summary(self, results):
        """Print test summary"""
        print("\n" + "="*60)
        print("🧪 POSTTOOLUSE RETRY LOGIC TEST SUMMARY")
        print("="*60)

        passed = sum(results)
        total = len(results)

        test_names = [
            "Temporary failures with retry",
            "Permanent failure (no retry)",
            "Max retries exceeded"
        ]

        for i, (name, result) in enumerate(zip(test_names, results)):
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {name}")

        print(f"\n📊 Results: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All retry logic tests PASSED!")
            print("\n✅ PostToolUse hook retry logic is working correctly:")
            print("   • Retries temporary failures with exponential backoff")
            print("   • Backoff sequence: 1s, 2s, 4s (max 3 retries)")
            print("   • Identifies permanent failures (no retries)")
            print("   • Returns None when max retries exceeded")
        else:
            print("⚠️ Some retry logic tests FAILED!")
            print("   Review the implementation")

        print("="*60)


async def main():
    """Main test function"""
    print("🚀 Starting PostToolUse Retry Logic Tests (Simple)")
    print("Testing FASE 4.4 retry_with_backoff method...\n")

    tester = SimpleRetryTest()
    results = []

    # Run all tests
    results.append(await tester.test_retry_success_after_failures())
    results.append(await tester.test_permanent_failure_no_retry())
    results.append(await tester.test_max_retries_exceeded())

    # Print summary
    tester.print_summary(results)

    return results


if __name__ == "__main__":
    results = asyncio.run(main())
    sys.exit(0 if all(results) else 1)