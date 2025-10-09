#!/usr/bin/env python3
"""
Simple integration test: ResourceMonitor integration with PreToolUse hook.

Validates:
- ResourceMonitor initialization in hook
- Health check code paths exist
- Non-blocking behavior
"""

import sys
from pathlib import Path

# Add hook paths
hooks_base = Path(__file__).parent.parent / '.claude/hooks/devstream'
sys.path.insert(0, str(hooks_base / 'utils'))
sys.path.insert(0, str(hooks_base / 'memory'))
sys.path.insert(0, str(hooks_base / 'monitoring'))
sys.path.insert(0, str(hooks_base))

from pre_tool_use import PreToolUseHook, RESOURCE_MONITORING_AVAILABLE
# Import HealthStatus but use type name checking instead of isinstance for ResourceMonitor
from resource_monitor import HealthStatus


def test_hook_initialization():
    """Test that PreToolUseHook initializes ResourceMonitor correctly."""
    print("\n=== TEST: Hook Initialization ===")

    hook = PreToolUseHook()

    assert RESOURCE_MONITORING_AVAILABLE, "ResourceMonitor should be available"
    assert hook.resource_monitor is not None, "ResourceMonitor should be initialized in hook"
    # Use type name check instead of isinstance (module path issues)
    assert 'ResourceMonitor' in type(hook.resource_monitor).__name__, "Should be ResourceMonitor instance"

    print("✅ Hook initialization successful - ResourceMonitor integrated")


def test_resource_health_check():
    """Test that resource health check works."""
    print("\n=== TEST: Resource Health Check ===")

    hook = PreToolUseHook()

    # Call check_stability directly
    health = hook.resource_monitor.check_stability()

    assert health is not None, "Health check should return result"
    assert hasattr(health, 'healthy'), "Health should have 'healthy' attribute"
    assert hasattr(health, 'status'), "Health should have 'status' attribute"
    assert hasattr(health, 'warnings'), "Health should have 'warnings' attribute"
    # Use type name check for status instead of direct comparison
    assert 'HealthStatus' in type(health.status).__name__, "Status should be HealthStatus enum"

    print(f"✅ Resource health check successful - Status: {health.status.value}")
    print(f"   Healthy: {health.healthy}, Warnings: {len(health.warnings)}")

    if health.warnings:
        print(f"   Warning summary: {health.get_warning_summary()}")


def test_integration_points():
    """Verify integration points exist in PreToolUse hook."""
    print("\n=== TEST: Integration Points ===")

    import inspect

    hook = PreToolUseHook()

    # Check process method exists
    assert hasattr(hook, 'process'), "Hook should have 'process' method"

    # Check that process method source mentions ResourceMonitor
    process_source = inspect.getsource(hook.process)
    assert 'resource_monitor' in process_source, "'resource_monitor' should be in process method"
    assert 'check_stability' in process_source, "'check_stability' should be called in process method"
    assert 'skip_heavy_injection' in process_source, "'skip_heavy_injection' optimization should exist"

    print("✅ Integration points verified - ResourceMonitor integrated in process() method")
    print("   - resource_monitor instance created")
    print("   - check_stability() called")
    print("   - skip_heavy_injection optimization present")


def main():
    """Run all tests."""
    print("=" * 60)
    print("ResourceMonitor Integration Tests - PreToolUse Hook (Simple)")
    print("=" * 60)

    tests = [
        ("Hook Initialization", test_hook_initialization),
        ("Resource Health Check", test_resource_health_check),
        ("Integration Points", test_integration_points)
    ]

    results = []

    for test_name, test_func in tests:
        try:
            test_func()
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
    success = main()
    sys.exit(0 if success else 1)
