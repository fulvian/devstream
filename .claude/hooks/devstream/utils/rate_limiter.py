#!/usr/bin/env python3
"""
Rate limiter utilities for DevStream memory operations.

This module provides async rate limiting to prevent SQLite lock contention
and API rate limit violations using the aiolimiter library (GCRA algorithm).

Context7 Research:
- Library: /mjpieters/aiolimiter (Trust Score 9.6)
- Algorithm: Leaky bucket (Generic Cell Rate Algorithm)
- Performance: <5ms overhead per operation

Usage:
    async with memory_rate_limiter:
        await mcp_client.store_memory(content)

    # Non-blocking check:
    if memory_rate_limiter.has_capacity():
        async with memory_rate_limiter:
            await mcp_client.store_memory(content)
"""

# /// script
# dependencies = [
#     "aiolimiter>=1.0.0",
# ]
# ///

from typing import Dict, Any
import time
from aiolimiter import AsyncLimiter


class MemoryRateLimiter:
    """
    Rate limiter wrapper for DevStream memory operations.

    Provides both blocking and non-blocking rate limiting patterns
    to prevent SQLite lock contention from excessive memory operations.

    Attributes:
        limiter: AsyncLimiter instance from aiolimiter
        max_rate: Maximum operations per time period
        time_period: Time period in seconds
        total_operations: Total operations attempted
        throttled_operations: Operations delayed by rate limiter
    """

    def __init__(self, max_rate: int, time_period: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            max_rate: Maximum number of operations per time period
            time_period: Time period in seconds (default: 1.0)

        Note:
            Uses aiolimiter's AsyncLimiter with GCRA (Generic Cell Rate Algorithm).
            This provides precise rate control with minimal overhead (<5ms).
        """
        self.limiter = AsyncLimiter(max_rate, time_period)
        self.max_rate = max_rate
        self.time_period = time_period
        self.total_operations = 0
        self.throttled_operations = 0
        self._last_acquire_time = 0.0

    async def __aenter__(self):
        """
        Async context manager entry - acquire rate limiter capacity.

        Blocks until capacity is available. Tracks statistics.

        Returns:
            Self for context manager pattern
        """
        start_time = time.time()
        await self.limiter.acquire()
        acquire_duration = time.time() - start_time

        self.total_operations += 1
        self._last_acquire_time = time.time()

        # Track throttled operations (if we waited >10ms, we were throttled)
        if acquire_duration > 0.01:
            self.throttled_operations += 1

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - no cleanup needed."""
        return False

    def has_capacity(self) -> bool:
        """
        Check if rate limiter has capacity without blocking.

        Returns:
            True if capacity available, False if at limit

        Note:
            Uses aiolimiter's internal state to check capacity.
            Does NOT consume capacity - use with async context manager.
        """
        # aiolimiter's has_capacity checks if we can acquire without blocking
        return self.limiter.has_capacity()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get rate limiter statistics.

        Returns:
            Dictionary with utilization metrics:
                - max_rate: Maximum operations per time period
                - time_period: Time period in seconds
                - total_operations: Total operations attempted
                - throttled_operations: Operations delayed by rate limiter
                - throttle_rate: Percentage of throttled operations
                - last_acquire_time: Timestamp of last acquire
        """
        throttle_rate = (
            (self.throttled_operations / self.total_operations * 100)
            if self.total_operations > 0
            else 0.0
        )

        return {
            "max_rate": self.max_rate,
            "time_period": self.time_period,
            "total_operations": self.total_operations,
            "throttled_operations": self.throttled_operations,
            "throttle_rate": f"{throttle_rate:.1f}%",
            "last_acquire_time": self._last_acquire_time,
        }


# Global rate limiter instances

# Memory operations rate limiter
# Limit: 10 operations/second
# Rationale: SQLite handles ~50-100 concurrent writes/sec in WAL mode,
# but memory operations involve complex queries (semantic search, RRF).
# 10 ops/sec provides 5-10x safety margin to prevent lock contention.
memory_rate_limiter = MemoryRateLimiter(max_rate=10, time_period=1.0)

# Ollama embedding rate limiter
# Limit: 5 operations/second
# Rationale: Ollama API typically rate-limits at 10-20 req/sec.
# 5 ops/sec provides 2-4x safety margin for embedding generation.
# Embedding generation is CPU-intensive (~100-200ms per request).
ollama_rate_limiter = MemoryRateLimiter(max_rate=5, time_period=1.0)


# Convenience functions for direct usage

async def acquire_memory_capacity() -> MemoryRateLimiter:
    """
    Acquire memory operation capacity (blocking).

    Usage:
        async with await acquire_memory_capacity():
            await mcp_client.store_memory(content)

    Returns:
        MemoryRateLimiter context manager
    """
    return memory_rate_limiter


async def acquire_ollama_capacity() -> MemoryRateLimiter:
    """
    Acquire Ollama embedding capacity (blocking).

    Usage:
        async with await acquire_ollama_capacity():
            embedding = await ollama_client.generate_embedding(text)

    Returns:
        MemoryRateLimiter context manager
    """
    return ollama_rate_limiter


def has_memory_capacity() -> bool:
    """
    Check if memory operations have capacity (non-blocking).

    Returns:
        True if capacity available, False if at limit

    Usage:
        if has_memory_capacity():
            async with memory_rate_limiter:
                await mcp_client.store_memory(content)
        else:
            logger.warning("Memory rate limit exceeded, skipping storage")
    """
    return memory_rate_limiter.has_capacity()


def has_ollama_capacity() -> bool:
    """
    Check if Ollama operations have capacity (non-blocking).

    Returns:
        True if capacity available, False if at limit
    """
    return ollama_rate_limiter.has_capacity()


def get_memory_stats() -> Dict[str, Any]:
    """
    Get memory rate limiter statistics.

    Returns:
        Dictionary with utilization metrics
    """
    return memory_rate_limiter.get_stats()


def get_ollama_stats() -> Dict[str, Any]:
    """
    Get Ollama rate limiter statistics.

    Returns:
        Dictionary with utilization metrics
    """
    return ollama_rate_limiter.get_stats()
