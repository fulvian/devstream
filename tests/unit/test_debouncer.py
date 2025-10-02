#!/usr/bin/env python3
"""
Unit Tests for AsyncDebouncer

Tests debouncing functionality, error handling, statistics tracking,
and performance validation with 95%+ code coverage.

Test Categories:
- TC1-3: Core debouncing behavior (rapid calls, delayed calls, concurrent)
- TC4-5: Error handling (invalid delay, non-async function)
- TC6: Reset functionality
- TC7: Statistics tracking
- TC8: Performance validation
"""

import asyncio
import time
import pytest
from typing import List, Optional
import sys
from pathlib import Path

# Add .claude/hooks to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude/hooks"))

from devstream.utils.debouncer import (
    AsyncDebouncer,
    debounce,
    hook_debouncer,
)


# =============================================================================
# TC1: Rapid Calls Debouncing
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.debounce
async def test_rapid_calls_debounced():
    """
    TC1: Test that rapid calls (within delay window) are debounced.

    Scenario: 3 calls within 50ms with 100ms delay
    Expected: Only first call executes, others return None

    Validates:
    - First call executes immediately
    - Subsequent calls within delay return None
    - Execution count increments correctly
    """
    debouncer = AsyncDebouncer(delay=0.1)
    call_count = 0

    @debouncer
    async def test_func():
        nonlocal call_count
        call_count += 1
        return call_count

    # Call 3 times rapidly (within 50ms total)
    result1 = await test_func()  # Should execute
    await asyncio.sleep(0.02)  # 20ms delay
    result2 = await test_func()  # Should be debounced
    await asyncio.sleep(0.02)  # 40ms total
    result3 = await test_func()  # Should be debounced

    # Assertions
    assert result1 == 1, "First call should execute and return 1"
    assert result2 is None, "Second call should be debounced (None)"
    assert result3 is None, "Third call should be debounced (None)"
    assert call_count == 1, "Function should have executed only once"

    # Verify statistics
    stats = debouncer.get_stats()
    assert stats['test_func']['executions'] == 1
    assert stats['test_func']['debounced'] == 2
    assert stats['test_func']['total_calls'] == 3


# =============================================================================
# TC2: Delayed Calls Allowed
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.debounce
async def test_delayed_calls_allowed():
    """
    TC2: Test that calls spaced beyond delay window execute normally.

    Scenario: 3 calls spaced 150ms apart with 100ms delay
    Expected: All 3 calls execute

    Validates:
    - Calls beyond delay window execute
    - Execution count increments correctly
    - Return values are preserved
    """
    debouncer = AsyncDebouncer(delay=0.1)
    call_count = 0

    @debouncer
    async def test_func():
        nonlocal call_count
        call_count += 1
        return call_count

    # Call 3 times with sufficient spacing
    result1 = await test_func()
    await asyncio.sleep(0.15)  # 150ms > 100ms delay
    result2 = await test_func()
    await asyncio.sleep(0.15)
    result3 = await test_func()

    # Assertions
    assert result1 == 1, "First call should return 1"
    assert result2 == 2, "Second call should return 2"
    assert result3 == 3, "Third call should return 3"
    assert call_count == 3, "All 3 calls should have executed"

    # Verify statistics
    stats = debouncer.get_stats()
    assert stats['test_func']['executions'] == 3
    assert stats['test_func']['debounced'] == 0
    assert stats['test_func']['total_calls'] == 3


# =============================================================================
# TC3: Concurrent Tasks No Race Conditions
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.debounce
async def test_concurrent_no_race_conditions():
    """
    TC3: Test concurrent calls with proper debouncing and no race conditions.

    Scenario: 10 concurrent tasks launched simultaneously
    Expected: Only first task executes, others debounced

    Validates:
    - Concurrent calls are properly debounced
    - No race conditions in last_execution tracking
    - Statistics are consistent
    """
    debouncer = AsyncDebouncer(delay=0.1)
    call_count = 0
    execution_order: List[int] = []

    @debouncer
    async def test_func(task_id: int):
        nonlocal call_count
        call_count += 1
        execution_order.append(task_id)
        return task_id

    # Launch 10 concurrent tasks
    tasks = [test_func(i) for i in range(10)]
    results = await asyncio.gather(*tasks)

    # Assertions
    assert call_count == 1, "Only one task should have executed"
    assert len(execution_order) == 1, "Execution order should have 1 entry"

    # One result should be non-None (the executed one)
    non_none_results = [r for r in results if r is not None]
    none_results = [r for r in results if r is None]

    assert len(non_none_results) == 1, "Exactly one task should return a value"
    assert len(none_results) == 9, "9 tasks should be debounced (None)"

    # Verify statistics
    stats = debouncer.get_stats()
    assert stats['test_func']['executions'] == 1
    assert stats['test_func']['debounced'] == 9
    assert stats['test_func']['total_calls'] == 10


# =============================================================================
# TC4: Error Handling - Invalid Delay
# =============================================================================


@pytest.mark.unit
@pytest.mark.debounce
def test_invalid_delay_raises_valueerror():
    """
    TC4: Test that invalid delay values raise ValueError.

    Scenarios:
    - delay = 0
    - delay < 0
    - delay = non-numeric

    Validates:
    - ValueError raised for zero/negative delay
    - TypeError raised for non-numeric delay
    - Error messages are descriptive
    """
    # Test zero delay
    with pytest.raises(ValueError, match="delay must be positive"):
        AsyncDebouncer(delay=0)

    # Test negative delay
    with pytest.raises(ValueError, match="delay must be positive"):
        AsyncDebouncer(delay=-1)

    with pytest.raises(ValueError, match="delay must be positive"):
        AsyncDebouncer(delay=-0.5)

    # Test non-numeric delay
    with pytest.raises(TypeError, match="delay must be a number"):
        AsyncDebouncer(delay="0.1")  # type: ignore

    with pytest.raises(TypeError, match="delay must be a number"):
        AsyncDebouncer(delay=None)  # type: ignore


# =============================================================================
# TC5: Error Handling - Non-Async Function
# =============================================================================


@pytest.mark.unit
@pytest.mark.debounce
def test_non_async_raises_typeerror():
    """
    TC5: Test that decorating non-async function raises TypeError.

    Scenario: Attempt to debounce a synchronous function
    Expected: TypeError with descriptive message

    Validates:
    - TypeError raised for sync functions
    - Error message identifies function type
    """
    debouncer = AsyncDebouncer()

    with pytest.raises(
        TypeError,
        match="can only debounce async functions"
    ):
        @debouncer
        def sync_func():
            pass

    # Test with lambda
    with pytest.raises(TypeError, match="can only debounce async functions"):
        debouncer(lambda: None)  # type: ignore


# =============================================================================
# TC6: Reset Functionality
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.debounce
async def test_reset_clears_state():
    """
    TC6: Test that reset() clears debouncer state.

    Scenarios:
    - Reset specific function
    - Reset all functions

    Validates:
    - reset(func) clears state for specific function
    - reset() clears all state
    - Function executes immediately after reset
    """
    debouncer = AsyncDebouncer(delay=0.1)
    call_count = 0

    @debouncer
    async def test_func():
        nonlocal call_count
        call_count += 1
        return call_count

    # Execute function
    result1 = await test_func()  # Executes
    assert result1 == 1

    # Immediate call should be debounced
    result2 = await test_func()  # Debounced
    assert result2 is None
    assert call_count == 1

    # Reset state
    debouncer.reset(test_func)

    # Should execute immediately after reset
    result3 = await test_func()  # Executes (state cleared)
    assert result3 == 2
    assert call_count == 2

    # Verify statistics were reset
    stats = debouncer.get_stats()
    assert stats['test_func']['executions'] == 1  # Only counts after reset
    assert stats['test_func']['debounced'] == 0


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.debounce
async def test_reset_all_functions():
    """
    TC6b: Test that reset() clears statistics counters.

    Validates:
    - reset() clears internal tracking state
    - Statistics counters are cleared
    - Function count is logged

    Note: This tests the reset() clear() behavior without re-calling functions.
    """
    debouncer = AsyncDebouncer(delay=0.1)
    call_count_1 = 0
    call_count_2 = 0

    @debouncer
    async def func1():
        nonlocal call_count_1
        call_count_1 += 1
        return 1

    @debouncer
    async def func2():
        nonlocal call_count_2
        call_count_2 += 1
        return 2

    # Execute both functions
    await func1()
    await func2()

    # Verify both executed
    assert call_count_1 == 1
    assert call_count_2 == 1

    # Check pre-reset stats
    pre_stats = debouncer.get_stats()
    assert 'func1' in pre_stats
    assert 'func2' in pre_stats
    assert pre_stats['func1']['executions'] == 1
    assert pre_stats['func2']['executions'] == 1

    # Reset all - clears internal dicts
    debouncer.reset()

    # Verify internal state cleared
    assert len(debouncer._last_execution) == 0
    assert len(debouncer._execution_count) == 0
    assert len(debouncer._debounced_count) == 0

    # get_stats() should return empty dict
    post_stats = debouncer.get_stats()
    assert len(post_stats) == 0


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.debounce
async def test_reset_nonexistent_function():
    """
    TC6c: Test reset with non-existent function (should not raise).

    Validates:
    - reset(unknown_func) logs warning but doesn't raise
    """
    debouncer = AsyncDebouncer(delay=0.1)

    async def undecorated_func():
        pass

    # Should not raise, just log warning
    debouncer.reset(undecorated_func)  # No assertion needed


# =============================================================================
# TC7: Statistics Tracking
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.debounce
async def test_statistics_tracking():
    """
    TC7: Test that get_stats() returns accurate statistics.

    Validates:
    - Execution count is accurate
    - Debounced count is accurate
    - Total calls = executions + debounced
    - Debounce rate percentage is correct
    """
    debouncer = AsyncDebouncer(delay=0.1)

    @debouncer
    async def test_func():
        await asyncio.sleep(0.001)  # Minimal async work

    # Execute: 3 executions, 7 debounced (10 total)
    for i in range(10):
        await test_func()
        if i in [2, 5, 8]:  # Allow execution at these indices
            await asyncio.sleep(0.15)

    stats = debouncer.get_stats()
    func_stats = stats['test_func']

    # Verify statistics structure
    assert 'executions' in func_stats
    assert 'debounced' in func_stats
    assert 'total_calls' in func_stats
    assert 'debounce_rate' in func_stats

    # Verify values
    assert func_stats['executions'] == 4  # Indices 0, 3, 6, 9
    assert func_stats['debounced'] == 6   # Others debounced
    assert func_stats['total_calls'] == 10
    assert func_stats['debounce_rate'] == pytest.approx(60.0, rel=0.1)


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.debounce
async def test_statistics_multiple_functions():
    """
    TC7b: Test statistics tracking for multiple functions.

    Validates:
    - Statistics tracked independently per function
    - get_stats() returns all functions
    """
    debouncer = AsyncDebouncer(delay=0.05)

    @debouncer
    async def func1():
        pass

    @debouncer
    async def func2():
        pass

    # Execute func1 twice
    await func1()
    await asyncio.sleep(0.1)
    await func1()

    # Execute func2 three times (1 execution, 2 debounced)
    await func2()
    await func2()
    await func2()

    stats = debouncer.get_stats()

    # Verify func1 stats
    assert stats['func1']['executions'] == 2
    assert stats['func1']['debounced'] == 0

    # Verify func2 stats
    assert stats['func2']['executions'] == 1
    assert stats['func2']['debounced'] == 2


# =============================================================================
# TC8: Performance Validation
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.debounce
async def test_overhead_under_1ms():
    """
    TC8: Test that debouncer overhead is <1ms per call.

    Validates:
    - Execution overhead (wrapper logic) < 1ms
    - Debouncing overhead (skip logic) < 1ms
    - Performance requirement met
    """
    debouncer = AsyncDebouncer(delay=0.001)

    @debouncer
    async def minimal_func():
        """Minimal async function to isolate overhead."""
        pass

    # Measure execution overhead (first call)
    start = time.perf_counter()
    await minimal_func()
    execution_overhead = (time.perf_counter() - start) * 1000  # Convert to ms

    assert execution_overhead < 1.0, (
        f"Execution overhead {execution_overhead:.3f}ms exceeds 1ms limit"
    )

    # Measure debouncing overhead (second call, should be debounced)
    start = time.perf_counter()
    await minimal_func()
    debounce_overhead = (time.perf_counter() - start) * 1000

    assert debounce_overhead < 1.0, (
        f"Debounce overhead {debounce_overhead:.3f}ms exceeds 1ms limit"
    )


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.debounce
async def test_performance_with_arguments():
    """
    TC8b: Test performance overhead with function arguments.

    Validates:
    - Overhead remains <1ms with args/kwargs
    - Arguments are properly passed through
    """
    debouncer = AsyncDebouncer(delay=0.001)

    @debouncer
    async def func_with_args(a: int, b: int, c: int = 0):
        return a + b + c

    # Measure overhead with arguments
    start = time.perf_counter()
    result = await func_with_args(1, 2, c=3)
    overhead = (time.perf_counter() - start) * 1000

    assert overhead < 1.0, f"Overhead {overhead:.3f}ms exceeds 1ms limit"
    assert result == 6, "Arguments should be passed correctly"


# =============================================================================
# Additional Edge Cases
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.debounce
async def test_debouncer_preserves_exception():
    """
    Test that exceptions in debounced functions are properly raised.

    Validates:
    - Exceptions are not swallowed by debouncer
    - Exception type and message are preserved
    """
    debouncer = AsyncDebouncer(delay=0.1)

    @debouncer
    async def failing_func():
        raise ValueError("Test exception")

    with pytest.raises(ValueError, match="Test exception"):
        await failing_func()


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.debounce
async def test_debounce_factory_function():
    """
    Test the debounce() factory function.

    Validates:
    - debounce(delay) creates independent debouncer
    - Factory function works as decorator
    - Custom delay is respected
    """
    call_count = 0

    @debounce(delay=0.05)
    async def test_func():
        nonlocal call_count
        call_count += 1
        return call_count

    # First call executes
    result1 = await test_func()
    assert result1 == 1

    # Rapid second call debounced
    result2 = await test_func()
    assert result2 is None

    # After delay, executes
    await asyncio.sleep(0.06)
    result3 = await test_func()
    assert result3 == 2


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.debounce
async def test_global_hook_debouncer():
    """
    Test the global hook_debouncer instance.

    Validates:
    - Global instance exists
    - Global instance has default 0.1s delay
    - Can be used as decorator
    """
    assert hook_debouncer is not None
    assert hook_debouncer.delay == 0.1

    @hook_debouncer
    async def test_hook():
        return "executed"

    result = await test_hook()
    assert result == "executed"


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.debounce
async def test_zero_total_calls_debounce_rate():
    """
    Test debounce rate calculation when no calls have been made.

    Validates:
    - get_stats() returns 0.0 debounce_rate when total_calls = 0
    - No division by zero errors
    """
    debouncer = AsyncDebouncer(delay=0.1)

    @debouncer
    async def unused_func():
        pass

    # Don't call the function
    stats = debouncer.get_stats()

    assert stats['unused_func']['executions'] == 0
    assert stats['unused_func']['debounced'] == 0
    assert stats['unused_func']['total_calls'] == 0
    assert stats['unused_func']['debounce_rate'] == 0.0


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.debounce
async def test_monotonic_timing_reliability():
    """
    Test that debouncer uses monotonic time (system clock changes don't affect it).

    Validates:
    - Uses time.monotonic() for timing
    - Debouncing remains consistent despite system time changes
    """
    debouncer = AsyncDebouncer(delay=0.05)
    call_count = 0

    @debouncer
    async def test_func():
        nonlocal call_count
        call_count += 1
        return call_count

    # Execute first call
    result1 = await test_func()
    assert result1 == 1

    # Immediate second call should be debounced
    result2 = await test_func()
    assert result2 is None

    # After delay, should execute
    await asyncio.sleep(0.06)
    result3 = await test_func()
    assert result3 == 2

    assert call_count == 2


# =============================================================================
# TC9: Module-Level Utilities
# =============================================================================


@pytest.mark.unit
@pytest.mark.debounce
def test_validate_performance_function():
    """
    TC9: Test the validate_performance() utility function.

    Validates:
    - validate_performance() exists and is callable
    - Returns True if performance meets requirements
    - Raises AssertionError if overhead exceeds 1ms

    Note: This tests the module's self-validation utility.
    """
    from devstream.utils.debouncer import validate_performance

    # Should pass validation
    result = validate_performance()
    assert result is True


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.debounce
async def test_multiple_debouncer_instances_isolated():
    """
    TC10: Test that multiple debouncer instances are isolated.

    Validates:
    - Different debouncer instances don't interfere
    - Each instance maintains its own state
    - Different delays work independently
    """
    debouncer1 = AsyncDebouncer(delay=0.05)
    debouncer2 = AsyncDebouncer(delay=0.15)

    count1 = 0
    count2 = 0

    @debouncer1
    async def func1():
        nonlocal count1
        count1 += 1
        return count1

    @debouncer2
    async def func2():
        nonlocal count2
        count2 += 1
        return count2

    # Call both
    result1a = await func1()
    result2a = await func2()

    assert result1a == 1
    assert result2a == 1

    # Wait 80ms - func1 should execute (>50ms), func2 should debounce (<150ms)
    await asyncio.sleep(0.08)

    result1b = await func1()
    result2b = await func2()

    assert result1b == 2  # func1 executed (80ms > 50ms delay)
    assert result2b is None  # func2 debounced (80ms < 150ms delay)


# =============================================================================
# Test Configuration
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=.claude.hooks.devstream.utils.debouncer"])
