#!/usr/bin/env python3
"""Performance validation for ResourceMonitor (<25ms requirement)."""

import sys
from pathlib import Path
from datetime import datetime
import statistics

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / '.claude' / 'hooks'))

from devstream.monitoring import ResourceMonitor


def benchmark_check_stability(iterations: int = 10) -> list[float]:
    """Benchmark check_stability() performance."""
    monitor = ResourceMonitor()
    timings = []

    for i in range(iterations):
        # Force fresh check by invalidating cache
        monitor._cached_health = None
        monitor._cache_timestamp = None

        start = datetime.now()
        health = monitor.check_stability()
        elapsed_ms = (datetime.now() - start).total_seconds() * 1000
        timings.append(elapsed_ms)

        print(f"  Iteration {i+1}: {elapsed_ms:.2f}ms ({health.status.value})")

    return timings


def main():
    print("ResourceMonitor Performance Benchmark")
    print("=" * 50)
    print("Requirement: <25ms per check (95th percentile)\n")

    timings = benchmark_check_stability(iterations=20)

    # Calculate statistics
    mean = statistics.mean(timings)
    median = statistics.median(timings)
    p95 = sorted(timings)[int(len(timings) * 0.95)]
    min_time = min(timings)
    max_time = max(timings)

    print("\nStatistics:")
    print(f"  Mean:   {mean:.2f}ms")
    print(f"  Median: {median:.2f}ms")
    print(f"  Min:    {min_time:.2f}ms")
    print(f"  Max:    {max_time:.2f}ms")
    print(f"  P95:    {p95:.2f}ms")

    # Validation
    if p95 < 25:
        print(f"\n✅ PASS: P95 ({p95:.2f}ms) < 25ms requirement")
        return 0
    else:
        print(f"\n❌ FAIL: P95 ({p95:.2f}ms) exceeds 25ms requirement")
        return 1


if __name__ == "__main__":
    sys.exit(main())
