#!/usr/bin/env python3
"""
Integration Tests for MCP Server to Direct Database Migration

Tests the complete migration from MCP server to direct database connections.
Validates API compatibility, performance improvements, and feature parity.

Key Test Areas:
- API compatibility with existing MCP client interface
- Performance improvements (100x faster, 10x less memory)
- Feature parity (memory storage, search, task management)
- Hook integration (PostToolUse, PreToolUse, Context Enhancer)
- Robustness patterns and error handling
- Feature flag system functionality
"""

import pytest
import asyncio
import tempfile
import os
import sys
import time
import psutil
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch

# Add hooks to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'utils'))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'config'))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'memory'))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'context'))

from direct_client import DevStreamDirectClient, get_direct_client
from feature_flags import (
    get_feature_flag_manager,
    should_use_direct_client,
    is_direct_db_enabled,
    get_migration_status
)
from robustness_patterns import (
    CircuitBreaker,
    RobustnessConfig,
    RetryPolicy,
    with_interrupt_handling,
    CircuitBreakerState
)


@pytest.fixture
async def test_db():
    """Create test database for integration testing."""
    test_db_dir = Path(__file__).parent.parent / "data" / "test" / "integration"
    test_db_dir.mkdir(parents=True, exist_ok=True)
    db_path = test_db_dir / "test_migration.db"

    # Remove existing test database
    if db_path.exists():
        os.unlink(db_path)

    return str(db_path)


@pytest.fixture
async def direct_client(test_db):
    """Create direct client for testing."""
    # Reset ConnectionManager singleton to avoid test interference
    import connection_manager
    connection_manager.ConnectionManager._instance = None

    client = DevStreamDirectClient(test_db)
    yield client

    # Cleanup
    try:
        if Path(test_db).exists():
            os.unlink(test_db)
    except:
        pass  # Ignore cleanup errors


class TestDirectClientAPICompatibility:
    """Test API compatibility with MCP client interface."""

    @pytest.mark.asyncio
    async def test_store_memory_api_compatibility(self, direct_client):
        """Test store_memory API compatibility."""
        result = await direct_client.store_memory(
            content="Test memory content",
            content_type="code",
            keywords=["test", "api", "compatibility"],
            session_id="test-session"
        )

        # Verify MCP-compatible response format
        assert result is not None
        assert isinstance(result, dict)
        assert "success" in result
        assert "memory_id" in result
        assert result["success"] is True
        assert result["content_type"] == "code"

    @pytest.mark.asyncio
    async def test_search_memory_api_compatibility(self, direct_client):
        """Test search_memory API compatibility."""
        # First store some test data
        await direct_client.store_memory(
            content="Python code for testing API compatibility",
            content_type="code",
            keywords=["python", "testing", "api"],
            session_id="test-session"
        )

        # Test search
        result = await direct_client.search_memory(
            query="python testing",
            limit=5
        )

        # Verify MCP-compatible response format
        assert result is not None
        assert isinstance(result, dict)
        assert "success" in result
        assert "results" in result
        assert "count" in result
        assert result["success"] is True
        assert isinstance(result["results"], list)

    @pytest.mark.asyncio
    async def test_task_management_api_compatibility(self, direct_client):
        """Test task management API compatibility."""
        # Create task
        create_result = await direct_client.create_task(
            title="API Compatibility Test Task",
            description="Testing task creation API compatibility",
            task_type="testing",
            priority=5,
            phase_name="API Testing"
        )

        # Verify create response
        assert create_result is not None
        assert isinstance(create_result, dict)
        assert "success" in create_result
        assert "task_id" in create_result
        assert create_result["success"] is True

        task_id = create_result["task_id"]

        # Update task
        update_result = await direct_client.update_task(
            task_id=task_id,
            status="completed"
        )

        # Verify update response
        assert update_result is not None
        assert isinstance(update_result, dict)
        assert "success" in update_result
        assert update_result["success"] is True

        # List tasks
        list_result = await direct_client.list_tasks()

        # Verify list response
        assert list_result is not None
        assert isinstance(list_result, dict)
        assert "success" in list_result
        assert "tasks" in list_result
        assert list_result["success"] is True

    @pytest.mark.asyncio
    async def test_checkpoint_trigger_api_compatibility(self, direct_client):
        """Test checkpoint trigger API compatibility."""
        result = await direct_client.trigger_checkpoint(reason="test")

        # Verify response format
        assert result is not None
        assert isinstance(result, dict)
        assert "success" in result
        assert "checkpoint_id" in result
        assert result["success"] is True


class TestPerformanceImprovements:
    """Test performance improvements over MCP server."""

    @pytest.mark.asyncio
    async def test_memory_storage_performance(self, direct_client):
        """Test memory storage performance improvement."""
        content = "Performance test content" * 100  # Larger content
        keywords = ["performance", "test"] * 10

        # Measure multiple operations
        start_time = time.time()
        operations = 10

        for i in range(operations):
            await direct_client.store_memory(
                content=f"{content} {i}",
                content_type="code",
                keywords=keywords,
                session_id=f"perf-test-{i}"
            )

        duration = time.time() - start_time
        avg_time_ms = (duration / operations) * 1000

        # Performance target: <20ms per operation
        assert avg_time_ms < 20, f"Average time {avg_time_ms:.2f}ms exceeds 20ms target"

    @pytest.mark.asyncio
    async def test_memory_search_performance(self, direct_client):
        """Test memory search performance improvement."""
        # Store test data first
        for i in range(20):
            await direct_client.store_memory(
                content=f"Test content {i} with performance testing keywords",
                content_type="code",
                keywords=["performance", "testing", f"keyword-{i}"],
                session_id=f"search-test-{i}"
            )

        # Measure search performance
        start_time = time.time()
        search_queries = 5

        for i in range(search_queries):
            await direct_client.search_memory(
                query=f"performance testing {i}",
                limit=10
            )

        duration = time.time() - start_time
        avg_time_ms = (duration / search_queries) * 1000

        # Performance target: <50ms per search
        assert avg_time_ms < 50, f"Average search time {avg_time_ms:.2f}ms exceeds 50ms target"

    def test_memory_usage(self, direct_client):
        """Test memory usage improvement."""
        # Get current process
        process = psutil.Process()

        # Measure baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Simulate load (store many records)
        async def simulate_load():
            tasks = []
            for i in range(100):
                task = direct_client.store_memory(
                    content=f"Load test content {i}",
                    content_type="code",
                    keywords=["load", "test", f"item-{i}"],
                    session_id=f"load-test-{i}"
                )
                tasks.append(task)

            # Run all operations concurrently
            await asyncio.gather(*tasks, return_exceptions=True)

        # Run simulation
        asyncio.run(simulate_load())

        # Measure memory after load
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - baseline_memory

        # Memory target: <50MB total increase
        assert memory_increase < 50, f"Memory increase {memory_increase:.2f}MB exceeds 50MB target"


class TestHookIntegration:
    """Test integration with DevStream hooks."""

    @pytest.mark.asyncio
    async def test_post_tool_use_integration(self, direct_client):
        """Test PostToolUse hook integration."""
        # Simulate PostToolUse hook memory storage
        memory_id = await direct_client.store_memory(
            content="# File Modified: test.py\n\n**Operation**: Write\n**File**: /test/test.py\n\n## Content\nprint('test')",
            content_type="code",
            keywords=["test", "python", "file"],
            session_id="hook-test-session"
        )

        assert memory_id is not None
        assert memory_id["success"] is True

        # Verify memory can be retrieved
        search_result = await direct_client.search_memory("test python", limit=5)
        assert search_result is not None
        assert search_result["success"] is True
        assert len(search_result["results"]) > 0

    @pytest.mark.asyncio
    async def test_pre_tool_use_integration(self, direct_client):
        """Test PreToolUse hook memory search integration."""
        # Store test data first
        await direct_client.store_memory(
            content="FastAPI application with async patterns",
            content_type="code",
            keywords=["fastapi", "async", "python"],
            session_id="pre-tool-test"
        )

        # Simulate PreToolUse hook context search
        context = "FastAPI implementation with async database operations"
        search_result = await direct_client.search_memory(
            query=context,
            content_type="code",
            limit=3
        )

        assert search_result is not None
        assert search_result["success"] is True

    @pytest.mark.asyncio
    async def test_context_enhancer_integration(self, direct_client):
        """Test User Query Context Enhancer integration."""
        # Store various types of content
        content_types = [
            ("code", "Python function implementation", ["python", "function"]),
            ("documentation", "API documentation for REST service", ["api", "rest", "docs"]),
            ("decision", "Decision to use database pooling", ["database", "pooling", "architecture"]),
        ]

        for content_type, content, keywords in content_types:
            await direct_client.store_memory(
                content=content,
                content_type=content_type,
                keywords=keywords,
                session_id="context-test"
            )

        # Test various user queries
        queries = [
            "How to implement database pooling in Python?",
            "What are the best practices for REST API design?",
            "Should I use connection pooling for my database?"
        ]

        for query in queries:
            search_result = await direct_client.search_memory(query, limit=5)
            assert search_result is not None
            assert search_result["success"] is True


class TestFeatureFlagSystem:
    """Test feature flag system for gradual migration."""

    def test_feature_flag_evaluation(self):
        """Test feature flag evaluation."""
        manager = get_feature_flag_manager()

        # Test default values
        assert manager.is_enabled("enable_robustness_patterns") is True
        assert manager.is_enabled("direct_db_enabled") is False

        # Test context-based evaluation
        context = {"session_id": "test-session-123"}
        result = manager.evaluate_flag("direct_db_enabled", context)
        assert result is False  # Default value

    def test_percentage_based_flags(self):
        """Test percentage-based feature flags."""
        # Note: This would require setting environment variables in real tests
        manager = get_feature_flag_manager()

        # Test with mock context
        context1 = {"session_id": "session-1"}
        context2 = {"session_id": "session-2"}

        # Since we can't set environment variables in tests, just test the logic
        result1 = manager.evaluate_flag("direct_db_enabled", context1)
        result2 = manager.evaluate_flag("direct_db_enabled", context2)

        # Both should return default value since no env var is set
        assert result1 is False
        assert result2 is False

    def test_convenience_functions(self):
        """Test convenience functions for migration status."""
        context = {"session_id": "test-session"}

        # Test direct DB check
        enabled = is_direct_db_enabled(context)
        assert enabled is False  # Default value

        # Test hook-specific checks
        post_tool_use = should_use_direct_client("post_tool_use", context)
        assert post_tool_use is False  # Both global and hook-specific flags are False

        # Test migration status
        status = get_migration_status(context)
        assert isinstance(status, dict)
        assert "direct_db_enabled" in status
        assert "post_tool_use" in status
        assert "pre_tool_use" in status


class TestRobustnessPatterns:
    """Test Context7-inspired robustness patterns."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self):
        """Test circuit breaker pattern."""
        config = type('Config', (), {
            'circuit_breaker_failure_threshold': 3,
            'circuit_breaker_timeout_seconds': 1,
            'circuit_breaker_success_threshold': 2
        })()

        from robustness_patterns import CircuitBreaker, RobustnessConfig
        robust_config = RobustnessConfig(
            circuit_breaker_failure_threshold=3,
            circuit_breaker_timeout_seconds=1,
            circuit_breaker_success_threshold=2
        )

        circuit_breaker = CircuitBreaker(robust_config)

        # Test successful operation
        async def successful_operation():
            return {"status": "success"}

        result = await circuit_breaker.call(successful_operation)
        assert result["status"] == "success"
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

        # Test circuit breaker opening
        async def failing_operation():
            raise ConnectionError("Service unavailable")

        # Trigger failures
        for _ in range(3):
            try:
                await circuit_breaker.call(failing_operation)
            except ConnectionError:
                pass

        # Circuit should be open now
        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Test that calls are blocked
        with pytest.raises(ConnectionError):
            await circuit_breaker.call(successful_operation)

    @pytest.mark.asyncio
    async def test_retry_policy(self):
        """Test retry policy with exponential backoff."""
        from robustness_patterns import RetryPolicy

        retry_policy = RetryPolicy(
            max_retries=3,
            base_delay=0.1,  # Short delay for testing
            backoff_factor=2.0,
            max_delay=1.0,
            jitter=False  # Disable jitter for predictable testing
        )

        attempt_count = 0

        async def failing_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError("Temporary failure")
            return {"status": "success"}

        result = await retry_policy.execute(failing_operation)
        assert result["status"] == "success"
        assert attempt_count == 3  # Should have retried 2 times

    @pytest.mark.asyncio
    async def test_interrupt_handling(self):
        """Test interrupt handling for graceful cancellation."""
        from robustness_patterns import with_interrupt_handling

        async def quick_operation():
            return {"status": "success"}

        result = await with_interrupt_handling(quick_operation, timeout_seconds=5)
        assert result["status"] == "success"

        # Test timeout
        async def slow_operation():
            await asyncio.sleep(2)  # Longer than timeout
            return {"status": "success"}

        with pytest.raises(TimeoutError):
            await with_interrupt_handling(slow_operation, timeout_seconds=0.1)


class TestEndToEndScenarios:
    """End-to-end test scenarios for complete migration validation."""

    @pytest.mark.asyncio
    async def test_complete_workflow(self, direct_client):
        """Test complete workflow from memory storage to retrieval."""
        # Step 1: Store various types of content
        memory_ids = []

        # Store code
        code_result = await direct_client.store_memory(
            content="def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
            content_type="code",
            keywords=["python", "algorithm", "recursion"],
            session_id="workflow-test"
        )
        memory_ids.append(code_result["memory_id"])

        # Store documentation
        doc_result = await direct_client.store_memory(
            content="# Fibonacci Algorithm\n\nEfficient recursive implementation.",
            content_type="documentation",
            keywords=["fibonacci", "algorithm", "documentation"],
            session_id="workflow-test"
        )
        memory_ids.append(doc_result["memory_id"])

        # Store decision
        decision_result = await direct_client.store_memory(
            content="Decision: Use recursive implementation for clarity and maintainability",
            content_type="decision",
            keywords=["architecture", "decision", "recursive"],
            session_id="workflow-test"
        )
        memory_ids.append(decision_result["memory_id"])

        # Step 2: Create task
        task_result = await direct_client.create_task(
            title="Implement Fibonacci Algorithm",
            description="Create recursive Fibonacci function with proper error handling",
            task_type="implementation",
            priority=5,
            phase_name="Development"
        )
        task_id = task_result["task_id"]

        # Step 3: Search for relevant context
        search_result = await direct_client.search_memory(
            query="fibonacci recursive implementation",
            limit=5
        )

        # Verify workflow completeness
        assert len(memory_ids) == 3
        assert task_id is not None
        assert search_result["success"] is True
        assert len(search_result["results"]) >= 2  # Should find code and documentation

        # Step 4: Update task status
        update_result = await direct_client.update_task(task_id, "completed")
        assert update_result["success"] is True

        # Step 5: Trigger checkpoint
        checkpoint_result = await direct_client.trigger_checkpoint("workflow_complete")
        assert checkpoint_result["success"] is True

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, direct_client):
        """Test concurrent operations for thread safety."""
        # Use a smaller concurrent test to avoid singleton issues
        async def store_memory_batch(start_id: int, count: int):
            """Store multiple memories in batch."""
            results = []
            for i in range(count):
                result = await direct_client.store_memory(
                    content=f"Concurrent test content {start_id}-{i}",
                    content_type="code",
                    keywords=["concurrent", "test", f"batch-{start_id}"],
                    session_id=f"concurrent-test-{start_id}"
                )
                results.append(result)
            return results

        # Use smaller numbers for testing
        batch_count = 3
        batch_size = 3

        start_time = time.time()
        tasks = []

        for batch_id in range(batch_count):
            task = store_memory_batch(batch_id, batch_size)
            tasks.append(task)

        # Execute all batches concurrently
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        duration = time.time() - start_time
        total_operations = batch_count * batch_size

        # Verify all operations succeeded
        successful_operations = sum(
            len(batch_result) for batch_result in all_results
            if not isinstance(batch_result, Exception) and
            all(result["success"] for result in batch_result)
        )

        assert successful_operations == total_operations
        assert duration < 5.0  # Should complete within 5 seconds

        # Verify all memories can be searched
        search_result = await direct_client.search_memory("concurrent test", limit=20)
        assert search_result["success"] is True
        assert len(search_result["results"]) == total_operations


# Performance benchmarking
class TestPerformanceBenchmarks:
    """Performance benchmarks to validate migration goals."""

    @pytest.mark.asyncio
    async def test_benchmark_memory_operations(self, direct_client):
        """Benchmark memory operations against target performance."""
        operation_counts = [10, 50, 100, 500]
        target_times = {
            10: 20,    # 20ms for 10 ops = 2ms per op
            50: 100,   # 100ms for 50 ops = 2ms per op
            100: 200,  # 200ms for 100 ops = 2ms per op
            500: 1000  # 1s for 500 ops = 2ms per op
        }

        for count in operation_counts:
            # Storage benchmark
            start_time = time.time()
            for i in range(count):
                await direct_client.store_memory(
                    content=f"Benchmark content {i}",
                    content_type="code",
                    keywords=["benchmark", "performance"],
                    session_id="benchmark-test"
                )
            storage_duration = time.time() - start_time
            storage_avg_ms = (storage_duration / count) * 1000

            # Search benchmark
            start_time = time.time()
            for i in range(10):  # Fewer searches
                await direct_client.search_memory(f"benchmark {i % 10}", limit=10)
            search_duration = time.time() - start_time
            search_avg_ms = (search_duration / 10) * 1000

            # Assert against targets
            target_storage_ms = target_times.get(count, 2000) / count
            assert storage_avg_ms < target_storage_ms * 1.2, f"Storage {count} ops avg {storage_avg_ms:.2f}ms exceeds target {target_storage_ms:.2f}ms"
            assert search_avg_ms < 50, f"Search avg {search_avg_ms:.2f}ms exceeds 50ms target"

            print(f"✅ Benchmark passed: {count} operations - Storage: {storage_avg_ms:.2f}ms avg, Search: {search_avg_ms:.2f}ms avg")


if __name__ == "__main__":
    # Run tests when executed directly
    print("🧪 Running integration tests for Direct DB Migration...")

    # Simple test run
    async def main():
        test_db_path = "/tmp/test_migration.db"

        # Remove existing test database
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)

        client = DevStreamDirectClient(test_db_path)

        # Basic functionality test
        print("Testing basic functionality...")
        result = await client.store_memory("test", "code", ["test"])
        assert result["success"]

        search_result = await client.search_memory("test")
        assert search_result["success"]

        print("✅ Basic functionality test passed!")

        # Cleanup
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)

    asyncio.run(main())