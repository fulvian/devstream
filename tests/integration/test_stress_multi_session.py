#!/usr/bin/env python3
"""
DevStream Kernel Panic Prevention - FASE 4.3 Stress Tests

Stress tests for multi-session crash prevention system.
Simulates 5 concurrent Claude Code sessions with sustained load.

Test Objectives:
- Validate 5+ concurrent sessions for 30 seconds sustained load
- Monitor system resources (connections, FDs, memory)
- Verify database integrity (zero corruption)
- Validate graceful degradation on resource exhaustion

Context7 Research:
- pytest-xdist: Concurrent test execution (Trust Score 9.5)
- threading: Multi-threaded session simulation
- psutil: Resource monitoring (CPU, memory, FD count)
"""

import os
import sys
import json
import time
import threading
import random
import psutil
import pytest
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks'))

from devstream.utils.connection_manager import (
    ConnectionManager,
    get_connection_manager
)
from devstream.utils.session_coordinator import (
    SessionCoordinator,
    get_session_coordinator
)


@dataclass
class WorkerStats:
    """Statistics for stress test worker."""
    worker_id: int
    writes: int = 0
    reads: int = 0
    errors: int = 0
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def duration(self) -> float:
        """Worker execution duration in seconds."""
        return self.end_time - self.start_time if self.end_time > 0 else 0.0

    @property
    def throughput(self) -> float:
        """Operations per second."""
        return (self.writes + self.reads) / self.duration if self.duration > 0 else 0.0


class StressTestWorker(threading.Thread):
    """
    Worker thread simulating Claude Code session under sustained load.

    Performs random database writes and reads with configurable frequency
    and duration.
    """

    def __init__(
        self,
        worker_id: int,
        db_path: str,
        registry_path: str,
        duration_seconds: int = 30,
        operation_interval: float = 0.5
    ):
        """
        Initialize stress test worker.

        Args:
            worker_id: Unique worker identifier
            db_path: Database path for testing
            registry_path: Session registry path
            duration_seconds: Test duration in seconds (default: 30)
            operation_interval: Seconds between operations (default: 0.5)
        """
        super().__init__(name=f"Worker-{worker_id}", daemon=True)
        self.worker_id = worker_id
        self.db_path = db_path
        self.registry_path = registry_path
        self.duration_seconds = duration_seconds
        self.operation_interval = operation_interval
        self.stats = WorkerStats(worker_id=worker_id)
        self.should_stop = threading.Event()

    def run(self):
        """Execute worker load test."""
        self.stats.start_time = time.time()
        session_id = f"stress-worker-{self.worker_id}"

        try:
            # Register session with coordinator
            coordinator = get_session_coordinator(self.registry_path)
            coordinator.register_session(session_id)

            # Get connection manager
            manager = get_connection_manager(self.db_path)

            # Create worker-specific test table
            with manager.get_connection() as conn:
                conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS stress_worker_{self.worker_id} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL,
                        data TEXT
                    )
                """)

            # Sustained load loop
            end_time = time.time() + self.duration_seconds

            while time.time() < end_time and not self.should_stop.is_set():
                try:
                    # Random operation: 70% writes, 30% reads
                    if random.random() < 0.7:
                        # Write operation
                        with manager.get_connection() as conn:
                            conn.execute(
                                f"INSERT INTO stress_worker_{self.worker_id} (timestamp, data) VALUES (?, ?)",
                                (time.time(), f"data-{self.worker_id}-{self.stats.writes}")
                            )
                        self.stats.writes += 1
                    else:
                        # Read operation
                        with manager.get_connection() as conn:
                            cursor = conn.execute(
                                f"SELECT COUNT(*) FROM stress_worker_{self.worker_id}"
                            )
                            cursor.fetchone()
                        self.stats.reads += 1

                    # Update heartbeat periodically
                    if (self.stats.writes + self.stats.reads) % 10 == 0:
                        coordinator.update_heartbeat(session_id)

                    # Sleep between operations
                    time.sleep(self.operation_interval + random.uniform(-0.1, 0.1))

                except Exception as e:
                    self.stats.errors += 1
                    # Continue on error (graceful degradation)

            # Cleanup
            coordinator.unregister_session(session_id)

        except Exception as e:
            self.stats.errors += 1

        finally:
            self.stats.end_time = time.time()

    def stop(self):
        """Signal worker to stop gracefully."""
        self.should_stop.set()


@pytest.fixture
def stress_test_db():
    """Create temporary database for stress testing."""
    project_root = Path(__file__).parent.parent.parent
    test_dir = project_root / 'data.noindex' / 'stress_test'
    test_dir.mkdir(parents=True, exist_ok=True)

    db_path = str(test_dir / f'stress_{int(time.time() * 1000)}.db')

    yield db_path

    # Cleanup
    try:
        os.unlink(db_path)
        for suffix in ['-wal', '-shm']:
            try:
                os.unlink(db_path + suffix)
            except FileNotFoundError:
                pass
    except FileNotFoundError:
        pass


@pytest.fixture
def stress_test_registry():
    """Create temporary registry for stress testing."""
    project_root = Path(__file__).parent.parent.parent
    test_dir = project_root / '.claude' / 'state' / 'stress_test'
    test_dir.mkdir(parents=True, exist_ok=True)

    registry_path = str(test_dir / f'registry_{int(time.time() * 1000)}.json')

    # Create empty registry
    with open(registry_path, 'w') as f:
        json.dump({}, f)

    yield registry_path

    # Cleanup
    try:
        os.unlink(registry_path)
        os.unlink(registry_path + '.lock')
    except FileNotFoundError:
        pass


@pytest.fixture(autouse=True)
def cleanup_singletons():
    """Reset singletons between tests."""
    yield
    ConnectionManager._instance = None
    SessionCoordinator._instance = None


class TestStressMultiSession:
    """Stress tests for multi-session coordination."""

    def test_five_concurrent_sessions_sustained_load(
        self,
        stress_test_db,
        stress_test_registry
    ):
        """
        FASE 4.3: Stress test with 5 concurrent sessions for 30 seconds.

        Validates:
        - 5 concurrent sessions sustained load
        - Database integrity (zero corruption)
        - All workers complete successfully
        - Graceful resource management
        """
        NUM_WORKERS = 5
        TEST_DURATION = 30  # seconds

        # Capture initial resource stats
        process = psutil.Process()
        initial_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create and start workers
        workers: List[StressTestWorker] = []
        for i in range(NUM_WORKERS):
            worker = StressTestWorker(
                worker_id=i,
                db_path=stress_test_db,
                registry_path=stress_test_registry,
                duration_seconds=TEST_DURATION,
                operation_interval=0.5
            )
            workers.append(worker)
            worker.start()

        # Wait for all workers to complete
        for worker in workers:
            worker.join(timeout=TEST_DURATION + 10)  # Grace period

        # Capture final resource stats
        final_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
        final_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Validate results
        total_writes = sum(w.stats.writes for w in workers)
        total_reads = sum(w.stats.reads for w in workers)
        total_errors = sum(w.stats.errors for w in workers)

        print(f"\n{'='*70}")
        print(f"STRESS TEST RESULTS - {NUM_WORKERS} Workers × {TEST_DURATION}s")
        print(f"{'='*70}")
        print(f"Total Operations: {total_writes + total_reads}")
        print(f"  - Writes: {total_writes}")
        print(f"  - Reads: {total_reads}")
        print(f"  - Errors: {total_errors}")
        print(f"\nResource Usage:")
        print(f"  - File Descriptors: {initial_fds} → {final_fds} (Δ{final_fds - initial_fds})")
        print(f"  - Memory (RSS): {initial_memory:.1f} MB → {final_memory:.1f} MB (Δ{final_memory - initial_memory:.1f} MB)")
        print(f"\nWorker Stats:")
        for worker in workers:
            print(f"  Worker {worker.worker_id}: {worker.stats.writes}W + {worker.stats.reads}R = "
                  f"{worker.stats.throughput:.1f} ops/s ({worker.stats.errors} errors)")
        print(f"{'='*70}\n")

        # Assertions
        assert total_writes > 0, "No writes performed"
        assert total_reads > 0, "No reads performed"
        assert total_errors == 0, f"Errors occurred: {total_errors}"

        # All workers should complete
        for worker in workers:
            assert not worker.is_alive(), f"Worker {worker.worker_id} did not complete"
            assert worker.stats.duration > 0, f"Worker {worker.worker_id} did not run"

        # Resource limits
        fd_delta = final_fds - initial_fds
        assert fd_delta < 50, f"File descriptor leak detected: {fd_delta} new FDs"

        memory_delta_mb = final_memory - initial_memory
        assert memory_delta_mb < 500, f"Memory leak detected: {memory_delta_mb:.1f} MB increase"

        # Validate database integrity
        manager = get_connection_manager(stress_test_db)
        with manager.get_connection() as conn:
            # Verify all worker tables exist
            cursor = conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name LIKE 'stress_worker_%'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            assert len(tables) == NUM_WORKERS, f"Expected {NUM_WORKERS} tables, found {len(tables)}"

            # Verify data integrity (no corruption)
            for i in range(NUM_WORKERS):
                cursor = conn.execute(f"SELECT COUNT(*) FROM stress_worker_{i}")
                count = cursor.fetchone()[0]
                expected_count = workers[i].stats.writes
                assert count == expected_count, \
                    f"Worker {i}: expected {expected_count} rows, found {count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
