#!/usr/bin/env python3
"""Basic validation test for ResourceMonitor."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import from absolute path
sys.path.insert(0, str(project_root / '.claude' / 'hooks'))
from devstream.monitoring import ResourceMonitor, HealthStatus


def test_basic_functionality():
    """Test basic ResourceMonitor functionality."""
    print("Testing ResourceMonitor...")

    # Initialize monitor
    monitor = ResourceMonitor()

    # First check (fresh)
    health1 = monitor.check_stability()
    print(f"✓ First check completed: {health1.status.value}")
    print(f"  Metrics: {list(health1.metrics.keys())}")
    print(f"  Warnings: {health1.warnings if health1.warnings else 'None'}")
    print(f"  Cache age: {health1.cache_age_seconds}s")

    # Second check (should use cache)
    health2 = monitor.check_stability()
    print(f"✓ Second check (cached): cache_age={monitor._get_cache_age():.2f}s")

    # Verify caching works
    assert health1.timestamp == health2.timestamp, "Cache should return same timestamp"

    # Verify all expected metrics
    expected_metrics = {'memory', 'cpu', 'swap'}
    actual_metrics = set(health2.metrics.keys())
    assert expected_metrics.issubset(actual_metrics), f"Missing metrics: {expected_metrics - actual_metrics}"

    # Verify ResourceHealth methods
    summary = health2.get_warning_summary()
    print(f"✓ Warning summary: {summary}")

    is_critical = health2.is_critical()
    print(f"✓ Critical status: {is_critical}")

    # Display detailed metrics
    print("\nDetailed Metrics:")
    for name, metric in health2.metrics.items():
        print(f"  {name}: {metric.current:.1f}{metric.unit} "
              f"(warn={metric.warning_threshold}, crit={metric.critical_threshold}) "
              f"→ {metric.status.value}")

    print("\n✅ All tests passed!")
    return True


if __name__ == "__main__":
    try:
        test_basic_functionality()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
