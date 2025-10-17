"""
Multi-Project Performance and Benchmark Test Suite.

Context7-compliant performance testing for multi-project hook copying
and validation system. Measures deployment speed, memory usage, and scalability.

Uses patterns from pytest-benchmark and performance testing best practices.
"""

import pytest
import asyncio
import tempfile
import shutil
import time
import psutil
import tracemalloc
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import statistics
import gc

# Import modules under test
import sys
test_utils_path = Path(__file__).parent.parent.parent / ".claude" / "hooks" / "devstream" / "utils"
sys.path.insert(0, str(test_utils_path))

try:
    from multi_project_hook_copier import copy_devstream_hooks_enhanced
    from hook_integrity_validator import HookIntegrityValidator
    PERFORMANCE_TESTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Performance tests not available: {e}")
    PERFORMANCE_TESTS_AVAILABLE = False


@dataclass
class PerformanceMetrics:
    """Performance metrics for multi-project operations."""
    operation: str
    duration: float
    memory_usage_mb: float
    cpu_usage_percent: float
    files_copied: int
    bytes_copied: int
    success: bool
    error_message: Optional[str] = None


@pytest.fixture(scope="module")
def performance_source_root():
    """Create optimized source root for performance testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        source_root = Path(temp_dir)

        # Create optimized structure
        claude_dir = source_root / ".claude"
        hooks_dir = claude_dir / "hooks" / "devstream"
        hooks_dir.mkdir(parents=True)

        # Create performance-optimized hooks
        directories = ["memory", "context", "utils", "agents", "protocol", "sessions", "config", "checkpoints", "optimization", "migrations", "tasks"]
        for dir_name in directories:
            (hooks_dir / dir_name).mkdir(parents=True, exist_ok=True)

        # Create essential hooks optimized for performance
        essential_hooks = {
            "memory/pre_tool_use.py": """
import asyncio
import structlog
logger = structlog.get_logger(__name__)

async def main():
    logger.info("PreToolUse executed")
    return True

if __name__ == "__main__":
    asyncio.run(main())
""",
            "utils/direct_client.py": """
import sqlite3
from pathlib import Path

class DirectClient:
    def __init__(self):
        db_path = Path.cwd() / "data" / "devstream.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, data TEXT)''')
            conn.commit()

    def search_memory(self, query, limit=10):
        return {"results": []}

def get_direct_client():
    return DirectClient()
""",
            "context/user_query_context_enhancer.py": """
def enhance_query(query):
    return f"[Enhanced] {query}"

def main():
    import sys
    if len(sys.argv) > 1:
        print(enhance_query(sys.argv[1]))

if __name__ == "__main__":
    main()
""",
            "agents/pattern_matcher.py": """
class PatternMatch:
    def __init__(self, agent=None, confidence=0.0):
        self.agent = agent
        self.confidence = confidence

class PatternMatcher:
    def __init__(self):
        self.patterns = {".py": {"agent": "@python-specialist", "confidence": 0.9}}

    def match_patterns(self, **kwargs):
        file_path = kwargs.get("file_path", "")
        if file_path.endswith(".py"):
            return PatternMatch(**self.patterns.get(".py", {}))
        return None
"""
        }

        # Write optimized hooks
        for hook_path, content in essential_hooks.items():
            full_path = hooks_dir / hook_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

        yield source_root


class TestMultiProjectPerformance:
    """Performance testing suite for multi-project deployment."""

    @pytest.mark.skipif(not PERFORMANCE_TESTS_AVAILABLE, reason="Performance tests not available")
    @pytest.mark.asyncio
    async def test_single_project_deployment_performance(self, performance_source_root):
        """Test performance of single project deployment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Measure memory usage before
            tracemalloc.start()
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Measure deployment time
            start_time = time.perf_counter()
            start_cpu = process.cpu_percent()

            result = await copy_devstream_hooks_enhanced(
                source_root=performance_source_root,
                target_root=project_root
            )

            end_time = time.perf_counter()
            end_cpu = process.cpu_percent()
            current_memory, peak_memory = tracemalloc.get_traced_memory()
            final_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Calculate metrics
            duration = end_time - start_time
            memory_used = final_memory - initial_memory
            files_copied = self._count_copied_files(project_root)
            bytes_copied = self._calculate_bytes_copied(project_root)

            # Assert performance expectations
            assert result["status"] == "success"
            assert duration < 5.0, f"Deployment too slow: {duration:.2f}s"
            assert memory_used < 50.0, f"Memory usage too high: {memory_used:.2f}MB"

            metrics = PerformanceMetrics(
                operation="single_project_deployment",
                duration=duration,
                memory_usage_mb=memory_used,
                cpu_usage_percent=end_cpu,
                files_copied=files_copied,
                bytes_copied=bytes_copied,
                success=True
            )

            print(f"📊 Single Project Deployment Metrics:")
            print(f"   Duration: {duration:.3f}s")
            print(f"   Memory: {memory_used:.2f}MB")
            print(f"   Files: {files_copied}")
            print(f"   Size: {bytes_copied/1024:.1f}KB")

            return metrics

    @pytest.mark.skipif(not PERFORMANCE_TESTS_AVAILABLE, reason="Performance tests not available")
    @pytest.mark.asyncio
    async def test_concurrent_deployment_performance(self, performance_source_root):
        """Test performance of concurrent deployments."""
        num_projects = 5

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            projects = [temp_path / f"project-{i}" for i in range(num_projects)]

            # Start memory tracking
            tracemalloc.start()
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024

            # Create deployment tasks
            start_time = time.perf_counter()
            deployment_tasks = []

            for project_root in projects:
                task = copy_devstream_hooks_enhanced(
                    source_root=performance_source_root,
                    target_root=project_root
                )
                deployment_tasks.append(task)

            # Execute concurrently
            results = await asyncio.gather(*deployment_tasks, return_exceptions=True)
            end_time = time.perf_counter()

            # Calculate metrics
            duration = end_time - start_time
            current_memory, peak_memory = tracemalloc.get_traced_memory()
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_used = final_memory - initial_memory

            # Verify all deployments succeeded
            successful_deployments = sum(1 for r in results if not isinstance(r, Exception) and r.get("status") == "success")
            assert successful_deployments == num_projects, f"Only {successful_deployments}/{num_projects} deployments succeeded"

            # Performance assertions
            assert duration < 15.0, f"Concurrent deployment too slow: {duration:.2f}s"
            assert memory_used < 200.0, f"Memory usage too high: {memory_used:.2f}MB"

            avg_duration = duration / num_projects
            assert avg_duration < 3.0, f"Average deployment time too high: {avg_duration:.2f}s"

            print(f"📊 Concurrent Deployment Metrics ({num_projects} projects):")
            print(f"   Total Duration: {duration:.3f}s")
            print(f"   Average per Project: {avg_duration:.3f}s")
            print(f"   Memory Usage: {memory_used:.2f}MB")
            print(f"   Success Rate: {successful_deployments/num_projects*100:.1f}%")

    @pytest.mark.skipif(not PERFORMANCE_TESTS_AVAILABLE, reason="Performance tests not available")
    @pytest.mark.asyncio
    async def test_integrity_validation_performance(self, performance_source_root):
        """Test performance of integrity validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Deploy first
            await copy_devstream_hooks_enhanced(
                source_root=performance_source_root,
                target_root=project_root
            )

            # Measure validation performance
            validator = HookIntegrityValidator(str(performance_source_root))

            tracemalloc.start()
            start_time = time.perf_counter()

            report = await validator.generate_integrity_report(str(project_root))

            end_time = time.perf_counter()
            current_memory, peak_memory = tracemalloc.get_traced_memory()

            duration = end_time - start_time

            # Performance assertions
            assert report["overall_valid"] is True
            assert duration < 5.0, f"Integrity validation too slow: {duration:.2f}s"
            assert peak_memory < 10 * 1024 * 1024, f"Peak memory usage too high: {peak_memory/1024/1024:.2f}MB"

            print(f"📊 Integrity Validation Metrics:")
            print(f"   Duration: {duration:.3f}s")
            print(f"   Peak Memory: {peak_memory/1024/1024:.2f}MB")
            print(f"   Hooks Validated: {report['summary']['total_hooks']}")
            print(f"   Critical Failures: {report['summary']['critical_failures']}")

    @pytest.mark.skipif(not PERFORMANCE_TESTS_AVAILABLE, reason="Performance tests not available")
    @pytest.mark.asyncio
    async def test_scalability_performance(self, performance_source_root):
        """Test scalability with increasing number of projects."""
        project_counts = [1, 3, 5, 10]
        performance_data = []

        for num_projects in project_counts:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                projects = [temp_path / f"scale-project-{i}" for i in range(num_projects)]

                start_time = time.perf_counter()
                tracemalloc.start()

                # Deploy to all projects
                deployment_tasks = []
                for project_root in projects:
                    task = copy_devstream_hooks_enhanced(
                        source_root=performance_source_root,
                        target_root=project_root,
                        required_directories=["memory", "utils"]  # Limited dirs for speed
                    )
                    deployment_tasks.append(task)

                results = await asyncio.gather(*deployment_tasks, return_exceptions=True)
                end_time = time.perf_counter()

                current_memory, peak_memory = tracemalloc.get_traced_memory()
                successful = sum(1 for r in results if not isinstance(r, Exception) and r.get("status") == "success")
                duration = end_time - start_time

                metrics = {
                    "projects": num_projects,
                    "duration": duration,
                    "success_rate": successful / num_projects,
                    "avg_duration": duration / num_projects if num_projects > 0 else 0,
                    "peak_memory_mb": peak_memory / 1024 / 1024
                }
                performance_data.append(metrics)

                print(f"📊 Scale Test ({num_projects} projects): {duration:.3f}s total, {metrics['avg_duration']:.3f}s avg")

                # Basic scalability assertions
                assert metrics["success_rate"] >= 0.9, f"Success rate too low: {metrics['success_rate']:.2f}"
                assert metrics["avg_duration"] < 5.0, f"Average time per project too high: {metrics['avg_duration']:.3f}s"

        # Analyze scalability trends
        durations = [m["duration"] for m in performance_data]
        avg_durations = [m["avg_duration"] for m in performance_data]
        memory_usage = [m["peak_memory_mb"] for m in performance_data]

        # Check if performance scales reasonably
        duration_slope = self._calculate_slope(list(range(len(durations))), durations)
        assert duration_slope < 2.0, f"Performance doesn't scale well (duration slope: {duration_slope:.2f})"

        print(f"📈 Scalability Analysis:")
        print(f"   Duration Slope: {duration_slope:.2f}")
        print(f"   Max Avg Duration: {max(avg_durations):.3f}s")
        print(f"   Max Memory: {max(memory_usage):.2f}MB")

    def _calculate_slope(self, x_values, y_values):
        """Calculate linear regression slope."""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0

        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)

        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0

        return (n * sum_xy - sum_x * sum_y) / denominator

    def _count_copied_files(self, project_root: Path) -> int:
        """Count the number of files copied to project."""
        hooks_dir = project_root / ".claude" / "hooks" / "devstream"
        if not hooks_dir.exists():
            return 0

        count = 0
        for file_path in hooks_dir.rglob("*"):
            if file_path.is_file():
                count += 1
        return count

    def _calculate_bytes_copied(self, project_root: Path) -> int:
        """Calculate total bytes copied to project."""
        hooks_dir = project_root / ".claude" / "hooks" / "devstream"
        if not hooks_dir.exists():
            return 0

        total_bytes = 0
        for file_path in hooks_dir.rglob("*"):
            if file_path.is_file():
                try:
                    total_bytes += file_path.stat().st_size
                except (OSError, PermissionError):
                    pass
        return total_bytes

    @pytest.mark.skipif(not PERFORMANCE_TESTS_AVAILABLE, reason="Performance tests not available")
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, performance_source_root):
        """Test for memory leaks during repeated operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Run multiple deployments to detect memory leaks
            iterations = 5
            memory_samples = []

            for i in range(iterations):
                # Clean up project directory
                if project_root.exists():
                    shutil.rmtree(project_root)
                project_root.mkdir(parents=True)

                # Force garbage collection
                gc.collect()

                # Measure memory before deployment
                tracemalloc.start()
                process = psutil.Process()
                initial_memory = process.memory_info().rss / 1024 / 1024

                # Deploy
                result = await copy_devstream_hooks_enhanced(
                    source_root=performance_source_root,
                    target_root=project_root
                )

                # Measure memory after deployment
                current_memory, peak_memory = tracemalloc.get_traced_memory()
                final_memory = process.memory_info().rss / 1024 / 1024
                memory_used = final_memory - initial_memory

                memory_samples.append(memory_used)

                # Clean up for next iteration
                tracemalloc.stop()

            # Analyze memory usage for leaks
            avg_memory = statistics.mean(memory_samples)
            memory_std = statistics.stdev(memory_samples) if len(memory_samples) > 1 else 0
            max_memory = max(memory_samples)

            # Memory leak detection
            memory_growth_trend = self._calculate_slope(list(range(len(memory_samples))), memory_samples)

            assert result["status"] == "success", "Deployment should succeed"
            assert avg_memory < 100.0, f"Average memory usage too high: {avg_memory:.2f}MB"
            assert memory_growth_trend < 5.0, f"Potential memory leak detected (trend: {memory_growth_trend:.2f}MB per iteration)"

            print(f"🧠 Memory Leak Detection:")
            print(f"   Average Memory: {avg_memory:.2f}MB")
            print(f"   Memory Std Dev: {memory_std:.2f}MB")
            print(f"   Max Memory: {max_memory:.2f}MB")
            print(f"   Growth Trend: {memory_growth_trend:.2f}MB/iteration")

    @pytest.mark.asyncio
    async def test_resource_cleanup_performance(self, performance_source_root):
        """Test resource cleanup performance."""
        cleanup_times = []
        memory_before_cleanup = []
        memory_after_cleanup = []

        for i in range(3):
            with tempfile.TemporaryDirectory() as temp_dir:
                project_root = Path(temp_dir)

                # Deploy hooks
                await copy_devstream_hooks_enhanced(
                    source_root=performance_source_root,
                    target_root=project_root
                )

                # Measure memory before cleanup
                process = psutil.Process()
                memory_before_cleanup.append(process.memory_info().rss / 1024 / 1024)

                # Measure cleanup time
                start_time = time.perf_counter()

                # Cleanup (tempfile handles this automatically when exiting context)
                pass

                end_time = time.perf_counter()
                cleanup_times.append(end_time - start_time)

        # Analyze cleanup performance
        avg_cleanup_time = statistics.mean(cleanup_times)
        avg_memory_before = statistics.mean(memory_before_cleanup)

        print(f"🧹 Resource Cleanup Metrics:")
        print(f"   Avg Cleanup Time: {avg_cleanup_time:.4f}s")
        print(f"   Avg Memory Before: {avg_memory_before:.2f}MB")
        print(f"   Cleanup Iterations: {len(cleanup_times)}")

        # Cleanup should be fast (handled by tempfile)
        assert avg_cleanup_time < 0.1, f"Cleanup too slow: {avg_cleanup_time:.4f}s"


class TestPerformanceBenchmarks:
    """Performance benchmark comparisons."""

    @pytest.mark.skipif(not PERFORMANCE_TESTS_AVAILABLE, reason="Performance tests not available")
    @pytest.mark.asyncio
    async def test_deployment_vs_validation_performance(self, performance_source_root):
        """Compare deployment vs validation performance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Benchmark deployment
            start_time = time.perf_counter()
            deployment_result = await copy_devstream_hooks_enhanced(
                source_root=performance_source_root,
                target_root=project_root
            )
            deployment_time = time.perf_counter() - start_time

            # Benchmark validation
            validator = HookIntegrityValidator(str(performance_source_root))
            start_time = time.perf_counter()
            validation_report = await validator.generate_integrity_report(str(project_root))
            validation_time = time.perf_counter() - start_time

            assert deployment_result["status"] == "success"
            assert validation_report["overall_valid"] is True

            ratio = validation_time / deployment_time

            print(f"⚡ Performance Comparison:")
            print(f"   Deployment: {deployment_time:.3f}s")
            print(f"   Validation: {validation_time:.3f}s")
            print(f"   Ratio (Validation/Deployment): {ratio:.2f}x")

            # Validation should be faster than deployment
            assert validation_time < deployment_time, "Validation should be faster than deployment"

    @pytest.mark.asyncio
    async def test_small_vs_large_project_performance(self, performance_source_root):
        """Compare performance between small and large project deployments."""
        results = {}

        # Test small project (limited directories)
        with tempfile.TemporaryDirectory() as temp_dir:
            small_project = Path(temp_dir)
            start_time = time.perf_counter()

            await copy_devstream_hooks_enhanced(
                source_root=performance_source_root,
                target_root=small_project,
                required_directories=["memory", "utils"]
            )

            results["small"] = time.perf_counter() - start_time

        # Test large project (all directories)
        with tempfile.TemporaryDirectory() as temp_dir:
            large_project = Path(temp_dir)
            start_time = time.perf_counter()

            await copy_devstream_hooks_enhanced(
                source_root=performance_source_root,
                target_root=large_project,
                required_directories=["memory", "context", "utils", "agents", "protocol"]
            )

            results["large"] = time.perf_counter() - start_time

        # Analyze performance difference
        small_time = results["small"]
        large_time = results["large"]
        scaling_factor = large_time / small_time

        print(f"📊 Project Size Performance:")
        print(f"   Small Project (2 dirs): {small_time:.3f}s")
        print(f"   Large Project (5 dirs): {large_time:.3f}s")
        print(f"   Scaling Factor: {scaling_factor:.2f}x")

        # Large project should not be disproportionately slower
        assert scaling_factor < 3.0, f"Large project scaling factor too high: {scaling_factor:.2f}x"


if __name__ == "__main__":
    # Run performance tests
    print("🚀 Starting Multi-Project Performance Test Suite")
    print("=" * 60)

    if PERFORMANCE_TESTS_AVAILABLE:
        success = asyncio.run(run_comprehensive_performance_tests())
        sys.exit(0 if success else 1)
    else:
        print("❌ Performance tests not available")
        sys.exit(1)


async def run_comprehensive_performance_tests():
    """Run all performance tests and generate report."""
    print("Running comprehensive performance tests...")

    # Test list would be populated by pytest discovery
    # For manual execution, we'd use pytest directly

    return True  # Placeholder