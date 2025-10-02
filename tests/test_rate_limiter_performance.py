#!/usr/bin/env python3
"""
Performance validation for rate limiter.

Validates:
1. Overhead <5ms per operation
2. Accurate rate enforcement
3. Statistics tracking accuracy
"""

import asyncio
import time
import sys
from pathlib import Path

# Add .claude/hooks to path
sys.path.insert(0, str(Path(__file__).parent.parent / ".claude/hooks"))

from devstream.utils.rate_limiter import (
    memory_rate_limiter,
    ollama_rate_limiter,
    MemoryRateLimiter,
)


async def measure_overhead():
    """Measure rate limiter overhead."""
    print("=" * 60)
    print("PERFORMANCE TEST: Rate Limiter Overhead")
    print("=" * 60)

    limiter = MemoryRateLimiter(max_rate=1000, time_period=1.0)  # High rate
    overhead_samples = []

    for i in range(100):
        start = time.time()
        async with limiter:
            pass
        overhead = (time.time() - start) * 1000  # ms
        overhead_samples.append(overhead)

    avg_overhead = sum(overhead_samples) / len(overhead_samples)
    max_overhead = max(overhead_samples)
    min_overhead = min(overhead_samples)

    print(f"\nOverhead Statistics (100 operations):")
    print(f"  Average: {avg_overhead:.3f}ms")
    print(f"  Minimum: {min_overhead:.3f}ms")
    print(f"  Maximum: {max_overhead:.3f}ms")
    print(f"  Target:  <5ms")
    print(f"  Status:  {'✅ PASS' if avg_overhead < 5.0 else '❌ FAIL'}")


async def measure_rate_accuracy():
    """Measure rate limiting accuracy."""
    print("\n" + "=" * 60)
    print("PERFORMANCE TEST: Rate Accuracy")
    print("=" * 60)

    limiter = MemoryRateLimiter(max_rate=10, time_period=1.0)

    start_time = time.time()
    for _ in range(20):
        async with limiter:
            pass
    duration = time.time() - start_time

    expected_duration = 1.0  # 20 ops at 10 ops/sec after initial burst
    deviation = abs(duration - expected_duration)
    accuracy = (1 - deviation / expected_duration) * 100

    print(f"\nRate Limiting Accuracy (20 operations at 10 ops/sec):")
    print(f"  Expected: {expected_duration:.2f}s")
    print(f"  Actual:   {duration:.2f}s")
    print(f"  Deviation: {deviation:.2f}s")
    print(f"  Accuracy: {accuracy:.1f}%")
    print(f"  Status:  {'✅ PASS' if accuracy > 80 else '❌ FAIL'}")


async def measure_statistics_accuracy():
    """Validate statistics tracking."""
    print("\n" + "=" * 60)
    print("PERFORMANCE TEST: Statistics Tracking")
    print("=" * 60)

    limiter = MemoryRateLimiter(max_rate=5, time_period=1.0)

    # Perform operations
    for _ in range(10):
        async with limiter:
            await asyncio.sleep(0.01)

    stats = limiter.get_stats()

    print(f"\nStatistics After 10 Operations:")
    print(f"  Total Operations:     {stats['total_operations']}")
    print(f"  Throttled Operations: {stats['throttled_operations']}")
    print(f"  Throttle Rate:        {stats['throttle_rate']}")
    print(f"  Max Rate:             {stats['max_rate']} ops/sec")
    print(f"  Time Period:          {stats['time_period']}s")
    print(f"  Status: ✅ PASS" if stats['total_operations'] == 10 else "  Status: ❌ FAIL")


async def measure_global_limiter_config():
    """Validate global limiter configuration."""
    print("\n" + "=" * 60)
    print("CONFIGURATION TEST: Global Limiters")
    print("=" * 60)

    memory_stats = memory_rate_limiter.get_stats()
    ollama_stats = ollama_rate_limiter.get_stats()

    print(f"\nMemory Rate Limiter:")
    print(f"  Max Rate: {memory_stats['max_rate']} ops/sec")
    print(f"  Expected: 10 ops/sec")
    print(f"  Status: {'✅ PASS' if memory_stats['max_rate'] == 10 else '❌ FAIL'}")

    print(f"\nOllama Rate Limiter:")
    print(f"  Max Rate: {ollama_stats['max_rate']} ops/sec")
    print(f"  Expected: 5 ops/sec")
    print(f"  Status: {'✅ PASS' if ollama_stats['max_rate'] == 5 else '❌ FAIL'}")


async def main():
    """Run all performance tests."""
    print("\n🚀 DevStream Rate Limiter Performance Validation")
    print("Based on Context7 research: /mjpieters/aiolimiter (Trust Score 9.6)\n")

    await measure_overhead()
    await measure_rate_accuracy()
    await measure_statistics_accuracy()
    await measure_global_limiter_config()

    print("\n" + "=" * 60)
    print("✅ ALL PERFORMANCE TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
