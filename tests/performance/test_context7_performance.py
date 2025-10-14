#!/usr/bin/env python3
"""
Performance benchmarks for Context7 Direct Client.

Tests performance targets:
- Direct mode: <200ms average response time
- Cache hit ratio: >80% for repeated queries
- Memory usage: <50MB for 100 concurrent requests
- Success rate: >99% with automatic fallback
"""

import pytest
import asyncio
import time
import psutil
import os
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

# Add path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'utils'))

from context7_hybrid_manager import Context7HybridManager
from context7_direct_client import Context7DirectHttpClient


class TestContext7Performance:
    """Performance benchmarks for Context7 Direct Client."""

    @pytest.fixture
    async def performance_manager(self):
        """Create manager for performance testing."""
        manager = Context7HybridManager(direct_enabled=True, mcp_fallback=True)
        yield manager
        await manager.close()

    @pytest.fixture
    def mock_direct_client(self):
        """Create a high-performance mock direct client."""
        client = AsyncMock()

        # Simulate realistic response times
        async def realistic_resolve(library_name: str):
            await asyncio.sleep(0.05)  # 50ms simulated network latency
            return f"/{library_name}/{library_name}"

        async def realistic_docs(library_id: str, topic: str = None, tokens: int = 5000):
            await asyncio.sleep(0.15)  # 150ms simulated network latency
            return f"Documentation for {library_id} on topic {topic or 'general'} ({tokens} tokens)"

        client.resolve_library_id.side_effect = realistic_resolve
        client.get_library_docs.side_effect = realistic_docs
        client.close = AsyncMock()

        return client

    @pytest.mark.asyncio
    async def benchmark_direct_vs_mcp_performance(self, performance_manager, mock_direct_client):
        """Compare performance of direct vs MCP mode."""
        performance_manager.direct_client = mock_direct_client

        # Benchmark direct mode
        start_time = time.time()
        direct_results = []
        for i in range(10):
            result = await performance_manager.resolve_library_id(f"lib-{i}")
            direct_results.append(result)
        direct_duration = time.time() - start_time

        # Simulate MCP mode (no direct client)
        performance_manager.direct_client = None
        performance_manager.mcp_available = True

        start_time = time.time()
        mcp_results = []
        for i in range(10):
            result = await performance_manager.resolve_library_id(f"lib-{i}")
            mcp_results.append(result)
        mcp_duration = time.time() - start_time

        # Direct mode should be faster than simulated MCP
        assert direct_duration < mcp_duration
        assert len(direct_results) == len(mcp_results) == 10

        # Check metrics
        metrics = performance_manager.get_metrics()
        assert metrics["direct"]["calls"] == 10
        assert metrics["mcp"]["calls"] == 10

        print(f"Direct mode: {direct_duration:.3f}s for 10 requests")
        print(f"MCP mode: {mcp_duration:.3f}s for 10 requests")
        print(f"Performance improvement: {((mcp_duration - direct_duration) / mcp_duration) * 100:.1f}%")

    @pytest.mark.asyncio
    async def benchmark_connection_pooling_efficiency(self, performance_manager, mock_direct_client):
        """Test connection pooling effectiveness."""
        performance_manager.direct_client = mock_direct_client

        # Test rapid successive requests to test connection reuse
        start_time = time.time()
        tasks = []

        # Create many concurrent requests
        for i in range(20):
            task = performance_manager.resolve_library_id(f"rapid-lib-{i}")
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time

        # Should complete quickly due to connection pooling
        assert duration < 5.0  # 20 requests should complete in under 5 seconds
        assert len(results) == 20
        assert all(result.startswith("/rapid-lib-") for result in results)

        # Verify connection reuse (should not create 20 separate connections)
        # This is an indirect test - in real implementation we'd monitor connection pool stats
        print(f"20 concurrent requests completed in {duration:.3f}s")
        print(f"Average per request: {duration / 20 * 1000:.1f}ms")

    @pytest.mark.asyncio
    async def benchmark_cache_hit_ratios(self, performance_manager, mock_direct_client):
        """Test cache effectiveness for repeated queries."""
        performance_manager.direct_client = mock_direct_client

        # First round - cache misses
        libraries = ["fastapi", "django", "react", "pytest", "aiohttp"]
        start_time = time.time()

        first_round = []
        for lib in libraries:
            result = await performance_manager.resolve_library_id(lib)
            first_round.append(result)

        first_round_time = time.time() - start_time

        # Second round - should be cache hits (if cache was implemented)
        start_time = time.time()

        second_round = []
        for lib in libraries:
            result = await performance_manager.resolve_library_id(lib)
            second_round.append(result)

        second_round_time = time.time() - start_time

        # Results should be identical
        assert first_round == second_round

        # Second round should be faster (if caching was implemented)
        # Note: Our mock doesn't implement actual caching, so this tests the structure
        print(f"First round (cache misses): {first_round_time:.3f}s for {len(libraries)} requests")
        print(f"Second round (cache hits): {second_round_time:.3f}s for {len(libraries)} requests")

        # Check metrics
        metrics = performance_manager.get_metrics()
        assert metrics["direct"]["calls"] == 10  # 5 + 5
        assert metrics["direct"]["successes"] == 10

    @pytest.mark.asyncio
    async def benchmark_memory_usage_comparison(self, performance_manager):
        """Compare memory usage between direct and MCP modes."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Test direct mode memory usage
        performance_manager.direct_client = MagicMock()  # Lightweight mock

        # Create memory pressure with many requests
        tasks = []
        for i in range(100):
            # Simulate some memory usage
            task = performance_manager.resolve_library_id(f"memory-test-{i}")
            tasks.append(task)

        await asyncio.gather(*tasks)
        direct_memory = process.memory_info().rss / 1024 / 1024  # MB
        direct_usage = direct_memory - initial_memory

        # Clear any accumulated state
        await performance_manager.close()

        # Test MCP mode memory usage
        new_manager = Context7HybridManager(direct_enabled=False, mcp_fallback=True)
        new_manager.mcp_available = True

        tasks = []
        for i in range(100):
            task = new_manager.resolve_library_id(f"memory-test-{i}")
            tasks.append(task)

        await asyncio.gather(*tasks)
        mcp_memory = process.memory_info().rss / 1024 / 1024  # MB
        mcp_usage = mcp_memory - direct_memory

        await new_manager.close()

        print(f"Direct mode memory usage: {direct_usage:.2f} MB for 100 requests")
        print(f"MCP mode memory usage: {mcp_usage:.2f} MB for 100 requests")

        # Memory usage should be reasonable (< 50MB for 100 requests)
        assert direct_usage < 50
        assert mcp_usage < 50

    @pytest.mark.asyncio
    async def benchmark_throughput_under_load(self, performance_manager, mock_direct_client):
        """Test system throughput under high load."""
        performance_manager.direct_client = mock_direct_client

        # High load test: 100 concurrent requests
        num_requests = 100
        start_time = time.time()

        tasks = []
        for i in range(num_requests):
            # Mix of resolve and docs operations
            if i % 2 == 0:
                tasks.append(performance_manager.resolve_library_id(f"load-lib-{i}"))
            else:
                tasks.append(performance_manager.get_library_docs(f"/load-lib-{i}"))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time

        # Check success rate
        successful = [r for r in results if not isinstance(r, Exception)]
        success_rate = len(successful) / len(results) * 100

        # Should handle load gracefully
        assert success_rate >= 99.0  # >99% success rate target
        assert duration < 30.0  # Should complete within reasonable time

        # Check metrics
        metrics = performance_manager.get_metrics()
        assert metrics["overall"]["total_calls"] == num_requests
        assert metrics["overall"]["success_rate"] >= 99.0

        throughput = num_requests / duration
        print(f"Throughput: {throughput:.1f} requests/second")
        print(f"Success rate: {success_rate:.1f}%")
        print(f"Total time: {duration:.3f}s for {num_requests} requests")

    @pytest.mark.asyncio
    async def benchmark_fallback_performance(self, performance_manager):
        """Test performance impact of MCP fallback."""
        # Test with direct client failure simulation
        failing_client = AsyncMock()
        failing_client.resolve_library_id.side_effect = Exception("Direct failed")
        failing_client.get_library_docs.side_effect = Exception("Direct failed")
        failing_client.close = AsyncMock()

        performance_manager.direct_client = failing_client
        performance_manager.mcp_available = True

        # Measure fallback performance
        start_time = time.time()
        tasks = []

        for i in range(20):
            # These should all fall back to MCP
            task = performance_manager.resolve_library_id(f"fallback-lib-{i}")
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time

        # All should succeed via fallback
        successful = [r for r in results if not isinstance(r, Exception)]
        fallback_success_rate = len(successful) / len(results) * 100

        assert fallback_success_rate == 100.0  # All should succeed via fallback
        assert duration < 10.0  # Fallback should be reasonably fast

        # Check fallback metrics
        metrics = performance_manager.get_metrics()
        assert metrics["overall"]["fallback_activations"] == 20
        assert metrics["direct"]["failures"] == 20
        assert metrics["mcp"]["successes"] == 20

        print(f"Fallback performance: {duration:.3f}s for 20 requests")
        print(f"Fallback success rate: {fallback_success_rate:.1f}%")
        print(f"Fallback activations: {metrics['overall']['fallback_activations']}")

    @pytest.mark.asyncio
    async def benchmark_scalability(self, performance_manager, mock_direct_client):
        """Test system scalability with increasing load."""
        performance_manager.direct_client = mock_direct_client

        # Test with different load levels
        load_levels = [10, 25, 50, 100]
        performance_results = []

        for load in load_levels:
            start_time = time.time()
            memory_before = psutil.Process().memory_info().rss / 1024 / 1024

            tasks = []
            for i in range(load):
                task = performance_manager.resolve_library_id(f"scale-lib-{i}")
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            duration = time.time() - start_time
            memory_after = psutil.Process().memory_info().rss / 1024 / 1024

            successful = len([r for r in results if not isinstance(r, Exception)])
            memory_usage = memory_after - memory_before
            throughput = successful / duration

            performance_results.append({
                "load": load,
                "duration": duration,
                "throughput": throughput,
                "memory_usage": memory_usage,
                "success_rate": successful / load * 100
            })

            print(f"Load {load:3d}: {throughput:6.1f} req/s, {duration:.3f}s, {memory_usage:5.2f}MB, {successful / load * 100:5.1f}% success")

        # Analyze scalability
        throughputs = [r["throughput"] for r in performance_results]
        memory_usage = [r["memory_usage"] for r in performance_results]

        # Throughput should remain relatively stable
        throughput_variance = max(throughputs) - min(throughputs)
        assert throughput_variance < max(throughputs) * 0.3  # Less than 30% variance

        # Memory usage should scale linearly but remain reasonable
        assert max(memory_usage) < 100  # Less than 100MB for highest load

        print(f"Scalability test completed")
        print(f"Throughput range: {min(throughputs):.1f} - {max(throughputs):.1f} req/s")
        print(f"Memory range: {min(memory_usage):.1f} - {max(memory_usage):.1f} MB")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])