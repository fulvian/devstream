#!/usr/bin/env python3
"""
Integration test: ResourceMonitor integration with PreToolUse hook.

Validates:
- ResourceMonitor initialization in hook
- Health check execution in hook flow
- Non-blocking behavior on monitor failure
- CRITICAL status triggers skip_heavy_injection optimization
"""

import sys
import asyncio
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add hook paths
hooks_base = Path(__file__).parent.parent.parent / '.claude/hooks/devstream'
sys.path.insert(0, str(hooks_base / 'utils'))
sys.path.insert(0, str(hooks_base / 'memory'))
sys.path.insert(0, str(hooks_base / 'monitoring'))
sys.path.insert(0, str(hooks_base))

from pre_tool_use import PreToolUseHook
from resource_monitor import ResourceHealth, HealthStatus, ResourceMetric


def create_mock_context(tool_name: str = "Write", file_path: str = "test.py"):
    """Create mock PreToolUseContext for testing."""
    mock_ctx = Mock()
    mock_ctx.tool_name = tool_name
    mock_ctx.tool_input = {
        "file_path": file_path,
        "content": "import fastapi\n\nclass TestAPI:\n    pass"
    }
    mock_ctx.output = Mock()
    mock_ctx.output.exit_success = Mock()
    mock_ctx.output.exit_non_block = Mock()
    return mock_ctx


async def test_healthy_status():
    """Test hook behavior with HEALTHY resource status."""
    print("\n=== TEST: HEALTHY Status ===")

    hook = PreToolUseHook()

    # Mock healthy resource check
    from datetime import datetime
    healthy_health = ResourceHealth(
        healthy=True,
        status=HealthStatus.HEALTHY,
        metrics={
            "memory_percent": ResourceMetric(
                name="memory_percent",
                value=45.0,
                threshold=80.0,
                status=HealthStatus.HEALTHY,
                message="Memory usage normal"
            )
        },
        warnings=[],
        timestamp=datetime.now(),
        cache_age_seconds=0.1
    )

    with patch.object(hook.resource_monitor, 'check_stability', return_value=healthy_health):
        # Mock should_run to return True
        with patch.object(hook.base, 'should_run', return_value=True):
            # Mock assemble_context to avoid actual MCP calls
            with patch.object(hook, 'assemble_context', return_value="# Mock Context"):
                ctx = create_mock_context()
                await hook.process(ctx)

                # Verify context injection was NOT skipped
                print("✅ HEALTHY status - context injection executed normally")
                ctx.output.exit_success.assert_called()


async def test_warning_status():
    """Test hook behavior with WARNING resource status."""
    print("\n=== TEST: WARNING Status ===")

    hook = PreToolUseHook()

    # Mock warning resource check
    from datetime import datetime
    warning_health = ResourceHealth(
        healthy=False,
        status=HealthStatus.WARNING,
        metrics={
            "memory_percent": ResourceMetric(
                name="memory_percent",
                value=85.0,
                threshold=80.0,
                status=HealthStatus.WARNING,
                message="Memory usage at 85%"
            )
        },
        warnings=["Memory usage at 85% (threshold: 80%)"],
        timestamp=datetime.now(),
        cache_age_seconds=0.1
    )

    with patch.object(hook.resource_monitor, 'check_stability', return_value=warning_health):
        with patch.object(hook.base, 'should_run', return_value=True):
            with patch.object(hook, 'assemble_context', return_value="# Mock Context") as mock_assemble:
                ctx = create_mock_context()
                await hook.process(ctx)

                # WARNING should still allow context injection (not CRITICAL)
                print("✅ WARNING status - context injection executed (not skipped)")
                mock_assemble.assert_called_once()
                ctx.output.exit_success.assert_called()


async def test_critical_status():
    """Test hook behavior with CRITICAL resource status."""
    print("\n=== TEST: CRITICAL Status ===")

    hook = PreToolUseHook()

    # Mock critical resource check
    from datetime import datetime
    critical_health = ResourceHealth(
        healthy=False,
        status=HealthStatus.CRITICAL,
        metrics={
            "memory_percent": ResourceMetric(
                name="memory_percent",
                value=95.0,
                threshold=90.0,
                status=HealthStatus.CRITICAL,
                message="Memory usage at 95%"
            )
        },
        warnings=["Memory usage at 95% (threshold: 90%)"],
        timestamp=datetime.now(),
        cache_age_seconds=0.1
    )

    with patch.object(hook.resource_monitor, 'check_stability', return_value=critical_health):
        with patch.object(hook.base, 'should_run', return_value=True):
            with patch.object(hook, 'assemble_context', return_value="# Mock Context") as mock_assemble:
                ctx = create_mock_context()
                await hook.process(ctx)

                # CRITICAL should skip heavy context injection
                print("✅ CRITICAL status - heavy context injection SKIPPED (optimization)")
                mock_assemble.assert_not_called()  # Should be skipped
                ctx.output.exit_success.assert_called()


async def test_monitor_failure_non_blocking():
    """Test that monitor failures don't block hook execution."""
    print("\n=== TEST: Monitor Failure (Non-Blocking) ===")

    hook = PreToolUseHook()

    # Mock monitor failure
    with patch.object(hook.resource_monitor, 'check_stability', side_effect=Exception("Monitor failure")):
        with patch.object(hook.base, 'should_run', return_value=True):
            with patch.object(hook, 'assemble_context', return_value="# Mock Context") as mock_assemble:
                ctx = create_mock_context()
                await hook.process(ctx)

                # Hook should continue execution despite monitor failure
                print("✅ Monitor failure - hook execution continued (non-blocking)")
                mock_assemble.assert_called_once()
                ctx.output.exit_success.assert_called()


async def test_monitor_unavailable():
    """Test hook behavior when ResourceMonitor is unavailable."""
    print("\n=== TEST: ResourceMonitor Unavailable ===")

    hook = PreToolUseHook()

    # Simulate ResourceMonitor unavailable
    original_monitor = hook.resource_monitor
    hook.resource_monitor = None

    try:
        with patch.object(hook.base, 'should_run', return_value=True):
            with patch.object(hook, 'assemble_context', return_value="# Mock Context") as mock_assemble:
                ctx = create_mock_context()
                await hook.process(ctx)

                # Hook should work normally without ResourceMonitor
                print("✅ ResourceMonitor unavailable - hook execution continued normally")
                mock_assemble.assert_called_once()
                ctx.output.exit_success.assert_called()
    finally:
        hook.resource_monitor = original_monitor


async def main():
    """Run all integration tests."""
    print("=" * 60)
    print("ResourceMonitor Integration Tests - PreToolUse Hook")
    print("=" * 60)

    tests = [
        ("Healthy Status", test_healthy_status),
        ("Warning Status", test_warning_status),
        ("Critical Status (Skip Heavy Injection)", test_critical_status),
        ("Monitor Failure (Non-Blocking)", test_monitor_failure_non_blocking),
        ("ResourceMonitor Unavailable", test_monitor_unavailable)
    ]

    results = []

    for test_name, test_func in tests:
        try:
            await test_func()
            results.append((test_name, "PASS"))
        except Exception as e:
            results.append((test_name, f"FAIL: {e}"))
            print(f"❌ {test_name} FAILED: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, status in results if status == "PASS")
    total = len(results)

    for test_name, status in results:
        emoji = "✅" if status == "PASS" else "❌"
        print(f"{emoji} {test_name}: {status}")

    print(f"\n{passed}/{total} tests passed")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
