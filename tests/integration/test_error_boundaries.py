"""
Error boundary integration tests.

CONTEXT7-VALIDATED PATTERNS IMPLEMENTATION:
- System resilience testing across component failures
- Graceful degradation validation under error conditions
- Transaction rollback and data consistency during failures
- Circuit breaker and retry mechanism testing
- Cross-system error propagation and isolation
"""

import pytest
import pytest_asyncio
import asyncio
from typing import List, Dict, Any
from unittest.mock import AsyncMock, patch

from devstream.database.queries import QueryManager
from devstream.core.exceptions import DatabaseError, DevStreamError


@pytest.mark.integration
@pytest.mark.error_boundary
@pytest.mark.slow
class TestErrorBoundaries:
    """
    Test system error boundaries and resilience patterns.
    Context7-validated patterns for error boundary testing.
    """

    async def test_database_connection_failure_recovery(
        self,
        integration_config
    ):
        """
        Test system behavior during database connection failures.
        Context7 pattern: connection failure resilience testing.
        """
        from devstream.database.connection import ConnectionPool

        # Test with invalid database path
        invalid_pool = ConnectionPool(
            db_path="/invalid/path/to/database.db",
            max_connections=3
        )

        # Should handle initialization failure gracefully
        with pytest.raises((DatabaseError, Exception)):
            await invalid_pool.initialize()

        # Verify pool remains in safe state after failure
        assert invalid_pool.engine is None

    async def test_transaction_rollback_on_error(
        self,
        integration_query_manager: QueryManager
    ):
        """
        Test transaction rollback during operation failures.
        Context7 pattern: transaction isolation during errors.
        """
        # Count initial plans
        initial_plans = await integration_query_manager.plans.list_active()
        initial_count = len(initial_plans)

        # Attempt operation that should fail and rollback
        with pytest.raises(Exception):
            async with integration_query_manager.pool.write_transaction() as conn:
                # Insert valid plan data
                plan_id = integration_query_manager.plans.generate_id()
                from devstream.database.schema import intervention_plans
                import json

                await conn.execute(
                    intervention_plans.insert().values(
                        id=plan_id,
                        title="Rollback Test Plan",
                        description="This should be rolled back",
                        objectives=json.dumps(["Test rollback"]),
                        expected_outcome="Should not exist after rollback",
                        status="active",
                        priority=5
                    )
                )

                # Force error to trigger rollback
                raise Exception("Simulated error to test rollback")

        # Verify rollback occurred - no new plans should exist
        final_plans = await integration_query_manager.plans.list_active()
        final_count = len(final_plans)

        assert final_count == initial_count, "Transaction rollback failed"

    async def test_concurrent_operation_error_isolation(
        self,
        integration_query_manager: QueryManager
    ):
        """
        Test error isolation during concurrent operations.
        Context7 pattern: concurrent operation error isolation.
        """
        async def operation_with_error(should_error: bool, index: int):
            if should_error and index == 2:  # Error in operation 3
                raise Exception(f"Simulated error in operation {index}")

            # Normal operation
            plan_id = await integration_query_manager.plans.create(
                title=f"Concurrent Plan {index}",
                description=f"Plan {index} for concurrent error testing",
                objectives=[f"Objective {index}"],
                expected_outcome=f"Plan {index} should succeed despite other errors"
            )
            return plan_id

        # Run concurrent operations where some will error
        operations = [
            operation_with_error(True, 0),   # Success
            operation_with_error(True, 1),   # Success
            operation_with_error(True, 2),   # Error
            operation_with_error(True, 3),   # Success
            operation_with_error(True, 4),   # Success
        ]

        # Gather results, allowing some to fail
        results = await asyncio.gather(*operations, return_exceptions=True)

        # Verify error isolation - successful operations should complete
        successful_plans = [r for r in results if isinstance(r, str)]
        errors = [r for r in results if isinstance(r, Exception)]

        assert len(successful_plans) == 4, "Successful operations should complete"
        assert len(errors) == 1, "Should have exactly one error"

        # Verify successful plans exist in database
        for plan_id in successful_plans:
            plan = await integration_query_manager.plans.get_by_id(plan_id)
            assert plan is not None, f"Plan {plan_id} should exist despite concurrent error"

    async def test_memory_operation_error_recovery(
        self,
        integration_query_manager: QueryManager
    ):
        """
        Test memory operation error handling and recovery.
        Context7 pattern: memory system error boundary testing.
        """
        # Test with invalid memory data that should be handled gracefully
        try:
            # Attempt to store memory with invalid content type
            memory_id = await integration_query_manager.memory.store(
                content="Test memory for error handling",
                content_type="invalid_type",  # Invalid content type
                keywords=["error", "testing"]
            )

            # If no error, verify memory was stored with fallback handling
            if memory_id:
                memory = await integration_query_manager.memory.get_by_id(memory_id)
                assert memory is not None

        except Exception as e:
            # Error handling is expected for invalid data
            assert "invalid_type" in str(e).lower() or "constraint" in str(e).lower()

        # Verify system remains functional after error
        valid_memory_id = await integration_query_manager.memory.store(
            content="Valid memory after error recovery test",
            content_type="context",
            keywords=["recovery", "valid"]
        )

        assert valid_memory_id is not None
        valid_memory = await integration_query_manager.memory.get_by_id(valid_memory_id)
        assert valid_memory is not None

    async def test_task_creation_error_handling(
        self,
        integration_query_manager: QueryManager,
        integration_sample_plan: str
    ):
        """
        Test task creation error handling and validation.
        Context7 pattern: task system error boundary validation.
        """
        # Create valid phase for testing
        from devstream.database.schema import phases
        phase_id = integration_query_manager.tasks.generate_id()

        async with integration_query_manager.pool.write_transaction() as conn:
            await conn.execute(
                phases.insert().values(
                    id=phase_id,
                    plan_id=integration_sample_plan,
                    name="Error Testing Phase",
                    description="Phase for error boundary testing",
                    sequence_order=1,
                    status="active"
                )
            )

        # Test task creation with invalid phase_id
        with pytest.raises(Exception):
            await integration_query_manager.tasks.create(
                phase_id="nonexistent_phase_id",
                title="Invalid Task",
                description="This should fail due to invalid phase",
                assigned_agent="test-agent",
                task_type="testing"
            )

        # Verify valid task creation still works after error
        valid_task_id = await integration_query_manager.tasks.create(
            phase_id=phase_id,
            title="Valid Task After Error",
            description="This should succeed after previous error",
            assigned_agent="recovery-agent",
            task_type="implementation"
        )

        assert valid_task_id is not None
        valid_task = await integration_query_manager.tasks.get_by_id(valid_task_id)
        assert valid_task is not None

    async def test_cross_system_error_propagation(
        self,
        integration_query_manager: QueryManager,
        integration_sample_plan: str
    ):
        """
        Test error propagation across system boundaries.
        Context7 pattern: cross-system error handling validation.
        """
        # Create phase for cross-system testing
        from devstream.database.schema import phases
        phase_id = integration_query_manager.tasks.generate_id()

        async with integration_query_manager.pool.write_transaction() as conn:
            await conn.execute(
                phases.insert().values(
                    id=phase_id,
                    plan_id=integration_sample_plan,
                    name="Cross-System Error Phase",
                    description="Phase for cross-system error testing",
                    sequence_order=1,
                    status="active"
                )
            )

        # Create task successfully
        task_id = await integration_query_manager.tasks.create(
            phase_id=phase_id,
            title="Cross-System Task",
            description="Task for cross-system error testing",
            assigned_agent="cross-system-agent",
            task_type="implementation"
        )

        # Verify task exists
        task = await integration_query_manager.tasks.get_by_id(task_id)
        assert task is not None

        # Test memory operation linked to task with potential error
        try:
            memory_id = await integration_query_manager.memory.store(
                content="Memory linked to task for error propagation testing",
                content_type="context",
                keywords=["cross-system", "error", "propagation"],
                task_id=task_id
            )

            # If successful, verify the memory exists
            if memory_id:
                memory = await integration_query_manager.memory.get_by_id(memory_id)
                assert memory is not None
                assert memory.get("task_id") == task_id

        except Exception as e:
            # Handle memory operation error gracefully
            print(f"Expected error in memory operation: {e}")

        # Verify task still exists despite potential memory error
        final_task = await integration_query_manager.tasks.get_by_id(task_id)
        assert final_task is not None, "Task should remain valid despite memory errors"

    async def test_connection_pool_exhaustion_handling(
        self,
        integration_config
    ):
        """
        Test system behavior under connection pool exhaustion.
        Context7 pattern: resource exhaustion error handling.
        """
        from devstream.database.connection import ConnectionPool

        # Create pool with very limited connections
        limited_pool = ConnectionPool(
            db_path=integration_config.database.db_path,
            max_connections=2  # Very limited
        )

        await limited_pool.initialize()

        try:
            # Simulate connection exhaustion scenario
            connections = []

            # Try to exhaust connection pool
            for i in range(5):  # More than max_connections
                try:
                    # Each operation should either succeed or handle exhaustion gracefully
                    async with limited_pool.read_transaction() as conn:
                        # Simple query to use connection
                        from sqlalchemy import text
                        result = await conn.execute(text("SELECT 1"))
                        result.fetchone()

                        # Simulate some work
                        await asyncio.sleep(0.1)

                except Exception as e:
                    # Connection exhaustion should be handled gracefully
                    assert "timeout" in str(e).lower() or "pool" in str(e).lower()

        finally:
            await limited_pool.close()

    async def test_data_consistency_during_errors(
        self,
        integration_query_manager: QueryManager,
        integration_helper
    ):
        """
        Test data consistency maintenance during error scenarios.
        Context7 pattern: data consistency under error conditions.
        """
        # Record initial state
        initial_counts = await integration_helper.count_total_records()

        # Perform operations that might error
        operations_attempted = 0
        operations_successful = 0

        for i in range(10):
            try:
                operations_attempted += 1

                # Create plan
                plan_id = await integration_query_manager.plans.create(
                    title=f"Consistency Test Plan {i}",
                    description=f"Plan {i} for consistency testing under errors",
                    objectives=[f"Objective {i}"],
                    expected_outcome=f"Plan {i} outcome"
                )

                # Simulate potential error condition
                if i == 5:  # Simulate error in middle of operations
                    raise Exception("Simulated error to test consistency")

                operations_successful += 1

            except Exception:
                # Expected error - continue testing
                continue

        # Verify data consistency despite errors
        final_counts = await integration_helper.count_total_records()

        # Should have gained exactly the number of successful operations
        expected_plan_increase = operations_successful
        actual_plan_increase = final_counts["plans"] - initial_counts["plans"]

        assert actual_plan_increase == expected_plan_increase, \
            f"Data consistency error: expected {expected_plan_increase}, got {actual_plan_increase}"

        # Verify overall system consistency
        consistency_check = await integration_helper.verify_data_consistency()
        assert consistency_check is True, "System consistency compromised after errors"

    async def test_graceful_degradation_under_load(
        self,
        integration_query_manager: QueryManager
    ):
        """
        Test graceful system degradation under heavy load with errors.
        Context7 pattern: graceful degradation testing under stress.
        """
        import time

        start_time = time.time()
        successful_operations = 0
        failed_operations = 0

        async def stress_operation(index: int):
            nonlocal successful_operations, failed_operations

            try:
                # Simulate varying load conditions
                if index % 7 == 0:  # Simulate periodic errors
                    raise Exception(f"Simulated load error {index}")

                # Normal operation under load
                plan_id = await integration_query_manager.plans.create(
                    title=f"Load Test Plan {index}",
                    description=f"Plan {index} under load testing",
                    objectives=[f"Load objective {index}"],
                    expected_outcome=f"Load outcome {index}"
                )

                successful_operations += 1
                return plan_id

            except Exception:
                failed_operations += 1
                raise

        # Generate high load with errors
        stress_tasks = [stress_operation(i) for i in range(50)]
        results = await asyncio.gather(*stress_tasks, return_exceptions=True)

        # Measure performance under stress
        total_time = time.time() - start_time

        # Verify graceful degradation
        success_rate = successful_operations / (successful_operations + failed_operations)
        assert success_rate >= 0.7, f"Success rate too low: {success_rate:.2f}"

        # Verify performance doesn't degrade catastrophically
        assert total_time < 30.0, f"Operations took too long under load: {total_time:.2f}s"

        # Verify system remains functional after stress
        post_stress_plan_id = await integration_query_manager.plans.create(
            title="Post-Stress Recovery Plan",
            description="Plan created after stress testing to verify recovery",
            objectives=["Verify system recovery"],
            expected_outcome="System functional after stress"
        )

        assert post_stress_plan_id is not None
        recovery_plan = await integration_query_manager.plans.get_by_id(post_stress_plan_id)
        assert recovery_plan is not None, "System should remain functional after stress testing"