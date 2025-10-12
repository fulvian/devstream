#!/usr/bin/env python3
"""
Test Implementation for DevStream Concurrency Solutions
======================================================

Comprehensive test suite for the Context7-compliant concurrency solutions.
Validates:
1. Concurrency guard functionality
2. Retry mechanism with exponential backoff
3. Sequential tool execution
4. Integration with DevStream hooks

Based on Context7 testing best practices and Claude Code MCP Enhanced patterns.
"""

import asyncio
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List
import pytest
from unittest.mock import Mock, AsyncMock

# Add hooks directory to path for testing
sys.path.insert(0, str(Path(__file__).parent / ".claude" / "hooks" / "devstream"))

# Import our implementations
from utils.mcp_retry_handler import (
    MCPRetryHandler, RetryConfig, ErrorType, get_retry_handler,
    retry_mcp_call
)
from utils.sequential_executor import (
    SequentialExecutor, ToolExecution, ToolPriority, ExecutionPlan,
    execute_mcp_tools_sequentially
)

class TestConcurrencyGuard:
    """Test suite for concurrency guard functionality"""

    def test_concurrency_guard_initialization(self):
        """Test concurrency guard can be initialized"""
        from concurrency_guard import ConcurrencyGuard

        guard = ConcurrencyGuard()
        assert guard.max_retries == 3
        assert guard.base_delay == 0.5
        assert guard.max_delay == 10.0
        assert guard.backoff_factor == 2.0

    def test_error_classification(self):
        """Test error classification works correctly"""
        from concurrency_guard import ConcurrencyGuard

        guard = ConcurrencyGuard()

        # Test retryable errors
        assert guard.is_retryable_error("400 concurrency error") == True
        assert guard.is_retryable_error("connection timeout") == True
        assert guard.is_retryable_error("rate limit exceeded") == True
        assert guard.is_retryable_error("500 server error") == True

        # Test non-retryable errors
        assert guard.is_retryable_error("401 unauthorized") == False
        assert guard.is_retryable_error("404 not found") == False
        assert guard.is_retryable_error("400 bad request") == False

    def test_delay_calculation_with_jitter(self):
        """Test exponential backoff with jitter"""
        from concurrency_guard import ConcurrencyGuard

        guard = ConcurrencyGuard()

        # Test multiple attempts to ensure jitter is working
        delays = [guard.calculate_delay_with_jitter(i) for i in range(5)]

        # Should be increasing (exponential backoff)
        assert delays[0] >= 0
        assert delays[1] > delays[0]
        assert delays[2] > delays[1]

        # Should not exceed max delay
        for delay in delays:
            assert delay <= guard.max_delay

    def test_lock_management(self):
        """Test file-based lock management"""
        from concurrency_guard import ConcurrencyGuard

        guard = ConcurrencyGuard()

        # Test lock acquisition and release
        tool_name = "test_tool"
        assert guard.acquire_lock(tool_name, timeout=1.0) == True
        assert guard.get_lock_file_path(tool_name).exists()

        # Second acquisition should fail
        assert guard.acquire_lock(tool_name, timeout=0.1) == False

        # Release and try again
        guard.release_lock(tool_name)
        assert guard.acquire_lock(tool_name, timeout=1.0) == True
        guard.release_lock(tool_name)


class TestRetryHandler:
    """Test suite for retry mechanism"""

    def test_retry_handler_initialization(self):
        """Test retry handler initialization"""
        config = RetryConfig(max_retries=5, base_delay=0.1)
        handler = MCPRetryHandler(config)

        assert handler.config.max_retries == 5
        assert handler.config.base_delay == 0.1
        assert len(handler.circuit_breakers) == 0
        assert len(handler.metrics) == 0

    def test_error_type_classification(self):
        """Test error type classification"""
        handler = MCPRetryHandler()

        # Network errors
        assert handler.classify_error("connection reset") == ErrorType.NETWORK
        assert handler.classify_error("ECONNREFUSED") == ErrorType.NETWORK

        # Timeout errors
        assert handler.classify_error("operation timed out") == ErrorType.TIMEOUT
        assert handler.classify_error("timeout exceeded") == ErrorType.TIMEOUT

        # Concurrency errors
        assert handler.classify_error("400 concurrency") == ErrorType.CONCURRENCY
        assert handler.classify_error("429 rate limit") == ErrorType.RATE_LIMIT

        # Authentication errors
        assert handler.classify_error("401 unauthorized") == ErrorType.AUTHENTICATION
        assert handler.classify_error("403 forbidden") == ErrorType.AUTHORIZATION

        # Server errors
        assert handler.classify_error("500 internal server") == ErrorType.SERVER_ERROR

        # Client errors
        assert handler.classify_error("400 bad request") == ErrorType.NON_RETRYABLE
        assert handler.classify_error("404 not found") == ErrorType.NON_RETRYABLE

    def test_retryable_error_classification(self):
        """Test retryable vs non-retryable classification"""
        handler = MCPRetryHandler()

        retryable_types = [
            ErrorType.RETRYABLE, ErrorType.NETWORK, ErrorType.TIMEOUT,
            ErrorType.RATE_LIMIT, ErrorType.CONCURRENCY, ErrorType.SERVER_ERROR
        ]

        non_retryable_types = [
            ErrorType.NON_RETRYABLE, ErrorType.AUTHENTICATION, ErrorType.AUTHORIZATION
        ]

        for error_type in retryable_types:
            assert handler.is_retryable(error_type) == True

        for error_type in non_retryable_types:
            assert handler.is_retryable(error_type) == False

    async def test_successful_retry_execution(self):
        """Test successful operation with retry"""
        handler = MCPRetryHandler(RetryConfig(max_retries=2, base_delay=0.01))

        call_count = 0
        async def mock_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First attempt fails")
            return "success"

        result = await handler.execute_with_retry(mock_operation, "test_operation")

        assert result.success == True
        assert result.total_attempts == 2
        assert call_count == 2

    async def test_failed_retry_execution(self):
        """Test failed operation after all retries"""
        handler = MCPRetryHandler(RetryConfig(max_retries=2, base_delay=0.01))

        async def mock_operation():
            raise Exception("Always fails")

        result = await handler.execute_with_retry(mock_operation, "test_operation")

        assert result.success == False
        assert result.total_attempts == 3  # Initial + 2 retries
        assert result.final_error == "Always fails"

    async def test_non_retryable_error(self):
        """Test non-retryable error fails immediately"""
        handler = MCPRetryHandler(RetryConfig(max_retries=3, base_delay=0.01))

        call_count = 0
        async def mock_operation():
            nonlocal call_count
            call_count += 1
            raise Exception("401 unauthorized")

        result = await handler.execute_with_retry(mock_operation, "test_operation")

        assert result.success == False
        assert result.total_attempts == 1  # Only initial attempt
        assert call_count == 1

    def test_circuit_breaker_functionality(self):
        """Test circuit breaker pattern"""
        handler = MCPRetryHandler(RetryConfig(
            max_retries=0,
            circuit_breaker_threshold=2,
            circuit_breaker_timeout=0.1
        ))

        circuit_breaker = handler.get_circuit_breaker("test_operation")

        # Initially closed
        assert circuit_breaker.call_allowed() == True

        # Record failures
        circuit_breaker.record_failure()
        assert circuit_breaker.call_allowed() == True

        circuit_breaker.record_failure()
        assert circuit_breaker.call_allowed() == False  # Should be open

        # Test timeout (wait for circuit to close)
        time.sleep(0.2)
        assert circuit_breaker.call_allowed() == True  # Should be half-open


class TestSequentialExecutor:
    """Test suite for sequential tool execution"""

    def test_sequential_executor_initialization(self):
        """Test sequential executor initialization"""
        executor = SequentialExecutor()
        assert len(executor.execution_history) == 0
        assert len(executor.active_executions) == 0

    def test_execution_plan_creation(self):
        """Test execution plan creation"""
        executor = SequentialExecutor()

        tools_data = [
            {"tool_name": "tool1", "args": {"param": "value1"}},
            {"tool_name": "tool2", "args": {"param": "value2"}}
        ]

        priorities = {"tool1": ToolPriority.HIGH}
        dependencies = {"tool2": ["tool1"]}

        plan = executor.create_execution_plan(tools_data, priorities, dependencies)

        assert len(plan.tools) == 2
        assert plan.tools[0].tool_name == "tool1"  # Should come first due to dependency
        assert plan.tools[0].priority == ToolPriority.HIGH
        assert plan.tools[1].tool_name == "tool2"
        assert "tool1" in plan.tools[1].dependencies

    def test_dependency_sorting(self):
        """Test topological sorting with dependencies"""
        executor = SequentialExecutor()

        # Create tools with complex dependencies
        tools = [
            ToolExecution("tool_c", {}, dependencies=["tool_a", "tool_b"]),
            ToolExecution("tool_a", {}),
            ToolExecution("tool_b", {}, dependencies=["tool_a"])
        ]

        sorted_tools = executor._topological_sort(tools)

        # Should be in order: tool_a, tool_b, tool_c
        assert sorted_tools[0].tool_name == "tool_a"
        assert sorted_tools[1].tool_name == "tool_b"
        assert sorted_tools[2].tool_name == "tool_c"

    def test_circular_dependency_detection(self):
        """Test circular dependency detection"""
        executor = SequentialExecutor()

        # Create circular dependency: a -> b -> a
        tools = [
            ToolExecution("tool_a", {}, dependencies=["tool_b"]),
            ToolExecution("tool_b", {}, dependencies=["tool_a"])
        ]

        with pytest.raises(ValueError, match="Circular dependency"):
            executor._topological_sort(tools)

    async def test_sequential_execution_success(self):
        """Test successful sequential execution"""
        executor = SequentialExecutor()

        # Mock tool executor
        call_order = []
        async def mock_tool_executor(tool_name: str, args: Dict[str, Any]):
            call_order.append(tool_name)
            await asyncio.sleep(0.01)
            return f"result_{tool_name}"

        tools_data = [
            {"tool_name": "tool1", "args": {}},
            {"tool_name": "tool2", "args": {}},
            {"tool_name": "tool3", "args": {}}
        ]

        plan = executor.create_execution_plan(tools_data)
        result = await executor.execute_plan(plan, mock_tool_executor)

        assert result.success == True
        assert result.completed_tools == 3
        assert result.failed_tools == 0
        assert call_order == ["tool1", "tool2", "tool3"]

    async def test_sequential_execution_with_failure(self):
        """Test sequential execution with tool failure"""
        executor = SequentialExecutor()

        async def mock_tool_executor(tool_name: str, args: Dict[str, Any]):
            if tool_name == "tool2":
                raise Exception("Tool2 failed")
            return f"result_{tool_name}"

        tools_data = [
            {"tool_name": "tool1", "args": {}},
            {"tool_name": "tool2", "args": {}},
            {"tool_name": "tool3", "args": {}}
        ]

        plan = executor.create_execution_plan(tools_data)
        result = await executor.execute_plan(plan, mock_tool_executor)

        assert result.success == False
        assert result.completed_tools == 2
        assert result.failed_tools == 1
        assert len(result.errors) == 1

    async def test_dependency_failure_skip(self):
        """Test that tools are skipped when dependencies fail"""
        executor = SequentialExecutor()

        async def mock_tool_executor(tool_name: str, args: Dict[str, Any]):
            if tool_name == "dependency":
                raise Exception("Dependency failed")
            return f"result_{tool_name}"

        tools_data = [
            {"tool_name": "dependency", "args": {}},
            {"tool_name": "dependent_tool", "args": {}, "dependencies": ["dependency"]}
        ]

        dependencies = {"dependent_tool": ["dependency"]}
        plan = executor.create_execution_plan(tools_data, dependencies=dependencies)
        result = await executor.execute_plan(plan, mock_tool_executor)

        assert result.success == False
        assert result.completed_tools == 0
        assert result.failed_tools == 1
        assert result.skipped_tools == 1

        # Check that dependent tool was skipped
        dependent_tool = next(t for t in plan.tools if t.tool_name == "dependent_tool")
        assert dependent_tool.status.value == "skipped"


class TestIntegration:
    """Integration tests for all components"""

    async def test_full_workflow_with_retry_and_sequential_execution(self):
        """Test full workflow combining retry and sequential execution"""

        # Create retry handler
        retry_config = RetryConfig(max_retries=2, base_delay=0.01)
        retry_handler = MCPRetryHandler(retry_config)

        # Create sequential executor
        executor = SequentialExecutor()

        # Mock tool executor with some failures
        call_count = {"tool1": 0, "tool2": 0}

        async def mock_tool_executor(tool_name: str, args: Dict[str, Any]):
            call_count[tool_name] += 1

            if tool_name == "tool1" and call_count[tool_name] == 1:
                raise Exception("tool1 first attempt fails")

            if tool_name == "tool2":
                raise Exception("tool2 always fails")

            await asyncio.sleep(0.01)
            return f"result_{tool_name}"

        tools_data = [
            {"tool_name": "tool1", "args": {}},
            {"tool_name": "tool2", "args": {}}
        ]

        plan = executor.create_execution_plan(tools_data)

        # Execute with retry logic
        async def tool_with_retry(tool_name: str, args: Dict[str, Any]):
            async def operation():
                return await mock_tool_executor(tool_name, args)

            result = await retry_handler.execute_with_retry(operation, tool_name)
            if result.success:
                return result.attempts[-1].result if result.attempts else None
            else:
                raise Exception(result.final_error)

        result = await executor.execute_plan(plan, tool_with_retry)

        # tool1 should succeed after retry, tool2 should fail
        assert result.success == False
        assert result.completed_tools == 1
        assert result.failed_tools == 1
        assert call_count["tool1"] == 2  # Initial + 1 retry
        assert call_count["tool2"] == 1  # Only initial attempt

    def test_context7_compliance(self):
        """Test that implementation follows Context7 best practices"""

        # Test retry handler follows Context7 patterns
        config = RetryConfig(
            max_retries=3,
            base_delay=0.5,
            max_delay=30.0,
            backoff_factor=2.0,
            jitter_factor=0.1
        )
        handler = MCPRetryHandler(config)

        # Verify Context7-compliant error classification
        assert handler.classify_error("400 concurrency") == ErrorType.CONCURRENCY
        assert handler.classify_error("429 rate limit") == ErrorType.RATE_LIMIT
        assert handler.classify_error("500 server error") == ErrorType.SERVER_ERROR

        # Verify retryable classification
        assert handler.is_retryable(ErrorType.CONCURRENCY) == True
        assert handler.is_retryable(ErrorType.RATE_LIMIT) == True
        assert handler.is_retryable(ErrorType.SERVER_ERROR) == True
        assert handler.is_retryable(ErrorType.AUTHENTICATION) == False

        # Test sequential executor follows Context7 patterns
        executor = SequentialExecutor()
        tools_data = [
            {"tool_name": "memory_operation", "args": {}, "priority": "critical"},
            {"tool_name": "context_search", "args": {}, "priority": "high"},
            {"tool_name": "documentation", "args": {}, "priority": "normal"}
        ]

        priorities = {
            "memory_operation": ToolPriority.CRITICAL,
            "context_search": ToolPriority.HIGH,
            "documentation": ToolPriority.NORMAL
        }

        plan = executor.create_execution_plan(tools_data, priorities)

        # Verify priority ordering
        assert plan.tools[0].priority == ToolPriority.CRITICAL
        assert plan.tools[1].priority == ToolPriority.HIGH
        assert plan.tools[2].priority == ToolPriority.NORMAL


# Test runner
async def run_all_tests():
    """Run all test suites"""
    print("🧪 Running Context7-Compliant Concurrency Implementation Tests")
    print("=" * 60)

    test_classes = [
        TestConcurrencyGuard,
        TestRetryHandler,
        TestSequentialExecutor,
        TestIntegration
    ]

    total_tests = 0
    passed_tests = 0

    for test_class in test_classes:
        print(f"\n📋 Running {test_class.__name__}")
        print("-" * 40)

        instance = test_class()
        test_methods = [method for method in dir(instance) if method.startswith('test_')]

        for test_method in test_methods:
            total_tests += 1
            try:
                method = getattr(instance, test_method)
                if asyncio.iscoroutinefunction(method):
                    await method()
                else:
                    method()
                print(f"  ✅ {test_method}")
                passed_tests += 1
            except Exception as e:
                print(f"  ❌ {test_method}: {e}")

    print(f"\n📊 Test Results")
    print("=" * 60)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success rate: {(passed_tests/total_tests*100):.1f}%")

    if passed_tests == total_tests:
        print("\n🎉 All tests passed! Implementation is Context7 compliant.")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} tests failed. Please review implementation.")


if __name__ == "__main__":
    asyncio.run(run_all_tests())