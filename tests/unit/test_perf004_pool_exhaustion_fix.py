#!/usr/bin/env python3
"""
Unit Test - PERF-004 Pool Exhaustion Fix Verification

This test specifically validates the PERF-004 fix for connection pool exhaustion.
It tests that the ConnectionManager gracefully handles scenarios where the pool
reaches its maximum limit under high concurrency.

PERF-004 Bug: Pool Exhaustion - Connection rejection
Location: connection_manager.py:250-256 (originally)
Status: FIXED with enhanced ConnectionManager
"""

import pytest
import sqlite3
import threading
import time
import os
from pathlib import Path
import sys

# Add utils to path
sys.path.append(str(Path(__file__).parent.parent.parent / '.claude/hooks/devstream/utils'))
from connection_manager import ConnectionManager


class TestPERF004PoolExhaustion:
    """Test PERF-004 Pool Exhaustion fix."""

    def test_pool_exhaustion_under_high_concurrency(self):
        """
        Test that ConnectionManager gracefully handles pool exhaustion.

        This test creates multiple threads that each try to get connections
        simultaneously, potentially exceeding the pool limit. The system should
        handle this gracefully without crashes.
        """
        # Use test database within project directory for isolated testing
        test_db_path = "data/test_perf004_exhaustion.db"

        # Ensure test directory exists
        os.makedirs(os.path.dirname(test_db_path), exist_ok=True)

        try:
            # Reset singleton for clean test
            ConnectionManager._instance = None

            # Create manager with test database
            manager = ConnectionManager.get_instance(test_db_path)

            # Track successful and failed connection attempts
            results = {"successful": 0, "failed": 0, "errors": []}
            results_lock = threading.Lock()

            def worker_thread(thread_id):
                """Worker that tries to get a connection and use it."""
                try:
                    with manager.get_connection() as conn:
                        # Verify connection works
                        cursor = conn.execute("SELECT 1")
                        result = cursor.fetchone()
                        assert result[0] == 1, "Connection not working"

                        # Simulate some work
                        time.sleep(0.01)

                    # Connection successful
                    with results_lock:
                        results["successful"] += 1

                except sqlite3.Error as e:
                    # Expected: some threads may fail due to pool limits
                    with results_lock:
                        results["failed"] += 1
                        results["errors"].append(f"Thread {thread_id}: {e}")

                except Exception as e:
                    # Unexpected errors
                    with results_lock:
                        results["errors"].append(f"Thread {thread_id} unexpected error: {e}")

            # Create more threads than typical pool size
            # Dynamic pool size is usually 10-20, so 25 threads should test limits
            num_threads = 25
            threads = []

            start_time = time.time()

            # Start all threads simultaneously
            for i in range(num_threads):
                thread = threading.Thread(target=worker_thread, args=(i,))
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            total_time = time.time() - start_time

            # Verify results
            print(f"\nPool Exhaustion Test Results:")
            print(f"  Total threads: {num_threads}")
            print(f"  Successful connections: {results['successful']}")
            print(f"  Failed connections: {results['failed']}")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Success rate: {results['successful']/num_threads:.1%}")

            # Check that system handled pool exhaustion gracefully
            assert results["successful"] > 0, "No connections succeeded - system broken"
            assert results["successful"] + results["failed"] == num_threads, "Some threads didn't complete"

            # Most operations should succeed (pool should handle concurrency well)
            success_rate = results["successful"] / num_threads
            assert success_rate >= 0.6, f"Success rate too low: {success_rate:.1%} (expected >= 60%)"

            # Verify pool statistics
            stats = manager.get_stats()
            print(f"  Pool stats: {stats['active_connections']}/{stats['max_connections']} active")
            print(f"  Pool utilization: {stats['pool_utilization']:.1%}")
            print(f"  Pool limit hits: {stats.get('pool_limit_hits', 0)}")

            # Pool should have reasonable utilization
            assert stats["pool_utilization"] <= 1.0, "Pool utilization exceeded 100%"

            # Test should complete in reasonable time
            assert total_time < 10.0, f"Test took too long: {total_time:.2f}s (expected < 10s)"

            # No unexpected errors should have occurred
            unexpected_errors = [e for e in results["errors"] if "unexpected error" in e]
            assert len(unexpected_errors) == 0, f"Unexpected errors occurred: {unexpected_errors}"

        finally:
            # Cleanup
            if os.path.exists(test_db_path):
                os.unlink(test_db_path)
            ConnectionManager._instance = None

    def test_pool_limit_enforcement_mechanism(self):
        """
        Test the specific mechanism that enforces pool limits.
        """
        # Use test database within project directory for isolated testing
        test_db_path = "data/test_perf004_limits.db"

        # Ensure test directory exists
        os.makedirs(os.path.dirname(test_db_path), exist_ok=True)

        try:
            # Reset singleton for clean test
            ConnectionManager._instance = None

            # Create manager with test database
            manager = ConnectionManager.get_instance(test_db_path)

            # Test the enforcement method directly
            initial_check = manager.enforce_pool_limit()
            assert initial_check is True, "Pool limit enforcement failed initially"

            # Get pool configuration
            config = manager.get_dynamic_pool_config()
            max_connections = config["current_max_connections"]
            print(f"Dynamic pool size: {max_connections} connections")

            # Verify dynamic sizing is working
            assert 10 <= max_connections <= 20, f"Pool size out of expected range: {max_connections}"

            # Create connections up to near the limit
            connections = []
            for i in range(max_connections - 1):
                conn = manager._get_thread_connection()
                connections.append(conn)
                print(f"Created connection {i+1}/{max_connections-1}")

            # Pool should still allow one more connection
            final_check = manager.enforce_pool_limit()
            assert final_check is True, "Pool should still allow connections before limit"

            # Verify pool statistics
            stats = manager.get_stats()
            assert stats["active_connections"] <= max_connections, "Active connections exceeded max"

            print(f"Pool utilization before limit: {stats['pool_utilization']:.1%}")

            # Cleanup connections
            for conn in connections:
                conn.close()

        finally:
            # Cleanup
            if os.path.exists(test_db_path):
                os.unlink(test_db_path)
            ConnectionManager._instance = None

    def test_pool_health_monitoring_under_stress(self):
        """
        Test that pool health monitoring works under stress conditions.
        """
        # Use test database within project directory for isolated testing
        test_db_path = "data/test_perf004_health.db"

        # Ensure test directory exists
        os.makedirs(os.path.dirname(test_db_path), exist_ok=True)

        try:
            # Reset singleton for clean test
            ConnectionManager._instance = None

            # Create manager with test database
            manager = ConnectionManager.get_instance(test_db_path)

            # Simulate stress with rapid connection creation and usage
            def stress_worker(thread_id):
                try:
                    for i in range(3):  # Multiple rounds per thread
                        with manager.get_connection() as conn:
                            cursor = conn.execute("SELECT 1, sqlite_version()")
                            result = cursor.fetchone()
                            assert result[0] == 1, "Query failed"
                            time.sleep(0.001)  # Brief work simulation
                except Exception as e:
                    print(f"Stress worker {thread_id} error: {e}")

            # Run stress test
            threads = []
            start_time = time.time()

            for i in range(15):  # Moderate concurrent stress
                thread = threading.Thread(target=stress_worker, args=(i,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            stress_time = time.time() - start_time

            # Verify pool health after stress
            stats = manager.get_stats()
            health_status = stats["health_status"]
            recommendations = stats["recommendations"]

            print(f"\nStress Test Results:")
            print(f"  Stress time: {stress_time:.2f}s")
            print(f"  Health status: {health_status}")
            print(f"  Connections created: {stats.get('total_connections_created', 0)}")
            print(f"  Health checks: {stats.get('total_health_checks', 0)}")
            print(f"  Health failures: {stats.get('total_health_check_failures', 0)}")

            # Health should be reasonable after normal stress
            assert health_status in ["HEALTHY", "WARNING"], f"Pool health critical: {health_status}"

            # Recommendations should provide useful guidance
            assert isinstance(recommendations, list), "Recommendations should be a list"
            assert len(recommendations) > 0, "Should have at least one recommendation"

            # Test should complete quickly
            assert stress_time < 5.0, f"Stress test took too long: {stress_time:.2f}s"

        finally:
            # Cleanup
            if os.path.exists(test_db_path):
                os.unlink(test_db_path)
            ConnectionManager._instance = None


# Pytest configuration
@pytest.fixture(autouse=True)
def cleanup_singleton():
    """Reset singleton between tests."""
    yield
    # Reset singleton for next test
    ConnectionManager._instance = None


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short", "-x"])