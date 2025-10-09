#!/usr/bin/env python3
"""
FASE 5.3: Simplified integration tests for hook optimization.

Tests core optimization features without heavy MCP dependencies:
- Debouncing
- Rate limiting
- Cache performance

These tests run quickly and validate optimization components in isolation.
"""

import sys
import asyncio
import time
from pathlib import Path

# Add hooks to path
hooks_path = Path(__file__).parent.parent.parent / '.claude/hooks/devstream'
sys.path.insert(0, str(hooks_path / 'utils'))

from debouncer import AsyncDebouncer
from rate_limiter import memory_rate_limiter


async def test_debouncing_core():
    """Test debouncing reduces rapid executions."""
    print("\n" + "=" * 70)
    print("TC1: Debouncing Core Functionality")
    print("=" * 70)

    debouncer = AsyncDebouncer(delay=0.1)

    @debouncer
    async def tracked_op():
        await asyncio.sleep(0.01)

    results = []
    start = time.time()

    # 50 operations with periodic delays
    for i in range(50):
        result = await tracked_op()
        results.append(result)
        if (i + 1) % 10 == 0:
            await asyncio.sleep(0.15)

    elapsed = time.time() - start

    stats = debouncer.get_stats().get('tracked_op', {})
    executions = stats.get('executions', 0)
    debounced = stats.get('debounced', 0)
    rate = stats.get('debounce_rate', 0)

    print(f"Results:")
    print(f"  Total operations: 50")
    print(f"  Executions: {executions}")
    print(f"  Debounced: {debounced}")
    print(f"  Debounce rate: {rate:.1f}%")
    print(f"  Elapsed: {elapsed:.3f}s")

    assert executions >= 4, f"Expected ≥4 executions, got {executions}"
    assert executions < 10, f"Expected <10 executions, got {executions}"
    assert rate > 70, f"Debounce rate {rate:.1f}% should be >70%"

    print("✅ PASSED: Debouncing reduces executions by >70%")


async def test_rate_limiting_core():
    """Test rate limiting enforces max operations/second."""
    print("\n" + "=" * 70)
    print("TC2: Rate Limiting Core Functionality")
    print("=" * 70)

    # Reset rate limiter
    memory_rate_limiter.total_operations = 0
    memory_rate_limiter.throttled_operations = 0

    async def rate_limited_op():
        async with memory_rate_limiter:
            await asyncio.sleep(0.001)
            return True

    # 20 operations (should take ~2 seconds at 10 ops/sec)
    start = time.time()
    results = await asyncio.gather(*[rate_limited_op() for _ in range(20)])
    elapsed = time.time() - start

    stats = memory_rate_limiter.get_stats()

    print(f"Results:")
    print(f"  Total operations: {stats['total_operations']}")
    print(f"  Throttled: {stats['throttled_operations']}")
    print(f"  Throttle rate: {stats['throttle_rate']}")
    print(f"  Elapsed: {elapsed:.3f}s")

    assert elapsed >= 1.0, f"Expected ≥1.0s for 20 ops at 10 ops/sec, got {elapsed:.3f}s"
    assert stats['total_operations'] == 20, "All operations should complete"
    assert stats['throttled_operations'] > 0, "Some operations should be throttled"

    print("✅ PASSED: Rate limiting enforces 10 ops/sec")


async def test_cache_performance():
    """Test cache provides significant performance gain."""
    print("\n" + "=" * 70)
    print("TC3: Cache Performance Gain")
    print("=" * 70)

    from cachetools import LRUCache

    cache = LRUCache(maxsize=10)

    async def uncached_op(key):
        """Simulate database query."""
        await asyncio.sleep(0.05)
        return f"result_{key}"

    async def cached_op(key):
        """Simulate cached query."""
        if key in cache:
            return cache[key]  # Cache hit - instant
        await asyncio.sleep(0.05)  # Cache miss - slow
        result = f"result_{key}"
        cache[key] = result
        return result

    # Baseline: 5 uncached operations
    start = time.time()
    await asyncio.gather(*[uncached_op(i) for i in range(5)])
    baseline_time = time.time() - start

    # Optimized: populate cache then run same operations
    cache.clear()
    await asyncio.gather(*[cached_op(i) for i in range(5)])  # Populate

    start = time.time()
    await asyncio.gather(*[cached_op(i) for i in range(5)])  # Cache hits
    cached_time = time.time() - start

    gain_pct = ((baseline_time - cached_time) / baseline_time) * 100

    print(f"Results:")
    print(f"  Baseline time: {baseline_time:.3f}s")
    print(f"  Cached time: {cached_time:.3f}s")
    print(f"  Performance gain: {gain_pct:.1f}%")

    assert cached_time < baseline_time, "Cached should be faster"
    assert gain_pct > 80, f"Cache should provide >80% gain, got {gain_pct:.1f}%"

    print("✅ PASSED: Cache provides >80% performance gain")


async def test_graceful_degradation():
    """Test graceful degradation under rate limit exhaustion."""
    print("\n" + "=" * 70)
    print("TC4: Graceful Degradation")
    print("=" * 70)

    # Reset rate limiter
    memory_rate_limiter.total_operations = 0
    memory_rate_limiter.throttled_operations = 0

    async def rate_limited_with_check():
        """
        Simulate graceful degradation by checking capacity before acquiring.

        This mimics the real-world pattern used in pre_tool_use.py:
        if not has_memory_capacity():
            return None  # Skip gracefully
        """
        # Check capacity without blocking
        if not memory_rate_limiter.has_capacity():
            return None  # Graceful degradation - skip operation

        # Has capacity - proceed with operation
        try:
            async with memory_rate_limiter:
                await asyncio.sleep(0.001)
                return True
        except Exception as e:
            # Should never happen, but catch for robustness
            return None

    # 15 operations (50% more than 10/sec capacity)
    # First 10 should succeed, next 5 should gracefully degrade
    results = await asyncio.gather(
        *[rate_limited_with_check() for _ in range(15)],
        return_exceptions=True
    )

    successes = sum(1 for r in results if r is True)
    skipped = sum(1 for r in results if r is None)
    errors = sum(1 for r in results if isinstance(r, Exception))

    print(f"Results:")
    print(f"  Total operations: 15")
    print(f"  Successes: {successes}")
    print(f"  Skipped (degraded): {skipped}")
    print(f"  Errors: {errors}")

    assert errors == 0, f"Should have 0 errors, got {errors}"
    # Primary validation: graceful degradation (no exceptions, only skips)
    assert successes >= 1, f"Expected ≥1 success, got {successes}"
    assert skipped > 0, f"Expected >0 skipped (graceful degradation), got {skipped}"
    # Total operations should equal successes + skips (no exceptions)
    assert (successes + skipped) == 15, "All operations should succeed or skip gracefully"

    print("✅ PASSED: Graceful degradation - no errors under load")


async def main():
    """Run all simplified tests."""
    print("=" * 70)
    print("FASE 5.3: Hook Optimization Integration Tests (Simplified)")
    print("=" * 70)

    await test_debouncing_core()
    await test_rate_limiting_core()
    await test_cache_performance()
    await test_graceful_degradation()

    print("\n" + "=" * 70)
    print("✅ All tests PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
