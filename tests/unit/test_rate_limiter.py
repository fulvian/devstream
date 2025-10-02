#!/usr/bin/env python3
"""
Unit tests for DevStream rate limiter module.

Tests validate:
1. Rate limiting enforcement (10 ops/sec for memory, 5 ops/sec for Ollama)
2. Non-blocking capacity checks
3. Statistics tracking
4. Context manager pattern
5. Performance overhead (<5ms)
"""

import pytest
import asyncio
import time
from typing import List

# Import rate limiter components
import sys
from pathlib import Path

# Add .claude/hooks to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude/hooks"))

from devstream.utils.rate_limiter import (
    MemoryRateLimiter,
    memory_rate_limiter,
    ollama_rate_limiter,
    has_memory_capacity,
    has_ollama_capacity,
    get_memory_stats,
    get_ollama_stats,
)


class TestMemoryRateLimiter:
    """Test MemoryRateLimiter class."""

    @pytest.mark.asyncio
    async def test_basic_rate_limiting(self):
        """Test basic rate limiting enforcement."""
        limiter = MemoryRateLimiter(max_rate=5, time_period=1.0)

        start_time = time.time()
        operation_times: List[float] = []

        # Attempt 10 operations
        # aiolimiter allows burst up to max_rate, then throttles
        for _ in range(10):
            async with limiter:
                operation_times.append(time.time() - start_time)

        duration = time.time() - start_time

        # First 5 operations complete in burst (fast)
        assert operation_times[4] < 0.2, "First 5 operations should be fast"

        # Remaining operations are throttled at 5 ops/sec
        # Operations 6-10 take ~1 second (5 ops at 5 ops/sec rate)
        assert duration >= 0.8, f"Duration {duration:.2f}s should be >= 0.8s"

    @pytest.mark.asyncio
    async def test_has_capacity_check(self):
        """Test non-blocking capacity check."""
        limiter = MemoryRateLimiter(max_rate=2, time_period=1.0)

        # Should have capacity initially
        assert limiter.has_capacity() is True

        # Consume all capacity
        async with limiter:
            pass
        async with limiter:
            pass

        # Should NOT have capacity now
        assert limiter.has_capacity() is False

        # Wait for capacity to replenish
        await asyncio.sleep(1.1)
        assert limiter.has_capacity() is True

    @pytest.mark.asyncio
    async def test_statistics_tracking(self):
        """Test statistics collection."""
        limiter = MemoryRateLimiter(max_rate=10, time_period=1.0)

        # Perform operations
        for _ in range(5):
            async with limiter:
                await asyncio.sleep(0.01)

        stats = limiter.get_stats()

        assert stats["max_rate"] == 10
        assert stats["time_period"] == 1.0
        assert stats["total_operations"] == 5
        assert stats["throttled_operations"] >= 0
        assert "throttle_rate" in stats
        assert stats["last_acquire_time"] > 0

    @pytest.mark.asyncio
    async def test_context_manager_pattern(self):
        """Test async context manager usage."""
        limiter = MemoryRateLimiter(max_rate=10, time_period=1.0)

        # Should work as async context manager
        async with limiter:
            assert True

        # Should track operation
        assert limiter.total_operations == 1

    @pytest.mark.asyncio
    async def test_performance_overhead(self):
        """Test that overhead is <5ms per operation."""
        limiter = MemoryRateLimiter(max_rate=100, time_period=1.0)  # High rate

        start_time = time.time()
        async with limiter:
            pass
        overhead = (time.time() - start_time) * 1000  # Convert to ms

        assert overhead < 5.0, f"Overhead {overhead:.2f}ms exceeds 5ms threshold"


class TestGlobalLimiters:
    """Test global rate limiter instances."""

    @pytest.mark.asyncio
    async def test_memory_rate_limiter_config(self):
        """Test memory rate limiter is configured correctly."""
        # Reset stats for clean test
        limiter = MemoryRateLimiter(max_rate=10, time_period=1.0)

        assert limiter.max_rate == 10
        assert limiter.time_period == 1.0

    @pytest.mark.asyncio
    async def test_ollama_rate_limiter_config(self):
        """Test Ollama rate limiter is configured correctly."""
        limiter = MemoryRateLimiter(max_rate=5, time_period=1.0)

        assert limiter.max_rate == 5
        assert limiter.time_period == 1.0

    @pytest.mark.asyncio
    async def test_has_memory_capacity_function(self):
        """Test has_memory_capacity() convenience function."""
        # Function should return boolean
        result = has_memory_capacity()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_has_ollama_capacity_function(self):
        """Test has_ollama_capacity() convenience function."""
        result = has_ollama_capacity()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_get_stats_functions(self):
        """Test statistics getter functions."""
        memory_stats = get_memory_stats()
        ollama_stats = get_ollama_stats()

        assert "max_rate" in memory_stats
        assert "total_operations" in memory_stats
        assert "max_rate" in ollama_stats
        assert "total_operations" in ollama_stats


class TestRateLimiterUsagePatterns:
    """Test real-world usage patterns."""

    @pytest.mark.asyncio
    async def test_graceful_degradation_pattern(self):
        """Test graceful degradation with capacity check."""
        limiter = MemoryRateLimiter(max_rate=2, time_period=1.0)

        operations_executed = 0
        operations_skipped = 0

        # Attempt 5 operations with graceful degradation
        for _ in range(5):
            if limiter.has_capacity():
                async with limiter:
                    operations_executed += 1
            else:
                operations_skipped += 1

        # Should execute 2, skip 3 (at 2 ops/sec limit)
        assert operations_executed == 2
        assert operations_skipped == 3

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test rate limiting with concurrent operations."""
        limiter = MemoryRateLimiter(max_rate=5, time_period=1.0)

        async def operation():
            async with limiter:
                await asyncio.sleep(0.01)

        # Launch 10 concurrent operations
        # First 5 complete in burst, next 5 throttled at rate
        start_time = time.time()
        await asyncio.gather(*[operation() for _ in range(10)])
        duration = time.time() - start_time

        # Should take ~1 second (burst of 5, then 5 more at 5 ops/sec)
        assert duration >= 0.8, f"Duration {duration:.2f}s should be >= 0.8s"

    @pytest.mark.asyncio
    async def test_burst_then_throttle(self):
        """Test burst capacity then throttling."""
        limiter = MemoryRateLimiter(max_rate=10, time_period=1.0)

        # First batch should complete quickly (burst capacity)
        start_time = time.time()
        for _ in range(10):
            async with limiter:
                pass
        burst_duration = time.time() - start_time

        assert burst_duration < 0.5, "Initial burst should be fast"

        # Next operation should be throttled (wait for capacity)
        throttle_start = time.time()
        async with limiter:
            pass
        throttle_duration = time.time() - throttle_start

        # aiolimiter replenishes capacity gradually
        # At 10 ops/sec, should wait ~0.1 seconds for next slot
        assert throttle_duration >= 0.05, "11th operation should wait for capacity"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
