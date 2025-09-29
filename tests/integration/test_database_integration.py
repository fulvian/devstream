"""
Integration tests for complete database functionality.

CONTEXT7-VALIDATED PATTERNS IMPLEMENTATION:
- SQLAlchemy async transaction testing with rollback isolation
- Real database integration with controlled environment
- Connection pool performance testing under load
- Migration system validation with schema verification
- Foreign key constraint enforcement testing
"""

import pytest
import pytest_asyncio
import asyncio
from typing import List

from devstream.database.connection import ConnectionPool
from devstream.database.queries import QueryManager
from devstream.database.migrations import MigrationRunner


@pytest.mark.integration
@pytest.mark.database
class TestDatabaseIntegration:
    """
    Test complete database system integration.
    Context7-validated patterns for production-like database testing.
    """

    async def test_full_database_lifecycle(self, integration_config):
        """
        Test complete database lifecycle from creation to usage.
        Context7 pattern: full database lifecycle with real SQLite.
        """
        # Initialize connection pool directly
        pool = ConnectionPool(
            db_path=integration_config.database.db_path,
            max_connections=integration_config.database.max_connections,
        )
        await pool.initialize()

        try:
            # Run migrations
            runner = MigrationRunner(pool)
            await runner.run_migrations()

            # Verify tables were created
            async with pool.read_transaction() as conn:
                cursor = await conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
                tables = [row[0] for row in await cursor.fetchall()]

                # Check core tables exist
                expected_tables = [
                    "agents",
                    "context_injections",
                    "hook_executions",
                    "hooks",
                    "intervention_plans",
                    "learning_insights",
                    "micro_tasks",
                    "performance_metrics",
                    "phases",
                    "schema_version",
                    "semantic_memory",
                    "work_sessions",
                ]

                for table in expected_tables:
                    assert table in tables, f"Table {table} not found"

            # Test query manager functionality
            qm = QueryManager(pool)

            # Create intervention plan
            plan_id = await qm.plans.create(
                title="Integration Test Plan",
                description="Testing full integration",
                objectives=["Test database", "Test queries"],
                expected_outcome="All tests pass",
            )

            # Verify plan was created
            plan = await qm.plans.get_by_id(plan_id)
            assert plan is not None
            assert plan["title"] == "Integration Test Plan"

            # Test memory storage
            memory_id = await qm.memory.store(
                content="Integration test memory content",
                content_type="test",
                keywords=["integration", "test"],
            )

            # Search memory
            results = await qm.memory.search_by_keywords(["integration"])
            assert len(results) >= 1
            assert any(r["id"] == memory_id for r in results)

            # Test work session
            session_id = await qm.sessions.create(
                session_name="Integration Test Session",
                plan_id=plan_id,
            )

            session = await qm.sessions.get_active()
            assert session is not None
            assert session["id"] == session_id

        finally:
            await pool.close()

    async def test_migration_system(self, integration_config):
        """
        Test migration system functionality.
        Context7 pattern: migration validation in integration tests.
        """
        pool = ConnectionPool(
            db_path=integration_config.database.db_path,
            max_connections=integration_config.database.max_connections
        )

        # Initialize connection pool only (skip automatic migrations)
        await pool.initialize()

        try:
            # Run migrations manually
            runner = MigrationRunner(pool)
            await runner.run_migrations()

            # Verify schema
            is_valid = await runner.verify_schema()
            assert is_valid

            # Get migration status
            status = await runner.get_migration_status()
            assert len(status) >= 1

            # Check all migrations are applied
            for version, description, applied in status:
                assert applied, f"Migration {version} ({description}) not applied"

        finally:
            await pool.close()

    async def test_connection_pool_under_load(self, integration_config):
        """
        Test connection pool under concurrent load.
        Context7 pattern: concurrent operation testing for connection pools.
        """
        pool = ConnectionPool(
            db_path=integration_config.database.db_path,
            max_connections=integration_config.database.max_connections
        )
        await pool.initialize()

        # Run migrations first
        runner = MigrationRunner(pool)
        await runner.run_migrations()

        try:
            qm = QueryManager(pool)

            # Create multiple plans concurrently
            async def create_plan(i: int):
                return await qm.plans.create(
                    title=f"Concurrent Plan {i}",
                    description=f"Plan created concurrently #{i}",
                    objectives=[f"Objective {i}"],
                    expected_outcome=f"Plan {i} completed",
                )

            # Run 5 concurrent plan creations
            tasks = [create_plan(i) for i in range(5)]
            plan_ids = await asyncio.gather(*tasks)

            assert len(plan_ids) == 5
            assert len(set(plan_ids)) == 5  # All IDs should be unique

            # Verify all plans were created
            for plan_id in plan_ids:
                plan = await qm.plans.get_by_id(plan_id)
                assert plan is not None

        finally:
            await pool.close()

    async def test_transaction_rollback(self, integration_config):
        """
        Test transaction rollback functionality.
        Context7 pattern: SQLAlchemy transaction rollback testing.
        """
        pool = ConnectionPool(
            db_path=integration_config.database.db_path,
            max_connections=integration_config.database.max_connections
        )
        await pool.initialize()

        # Run migrations first
        runner = MigrationRunner(pool)
        await runner.run_migrations()

        try:
            qm = QueryManager(pool)

            # Count initial plans
            initial_plans = await qm.plans.list_active()
            initial_count = len(initial_plans)

            # Try to create plan with error in transaction
            with pytest.raises(Exception):
                async with pool.write_transaction() as conn:
                    # Insert plan
                    from devstream.database.schema import intervention_plans
                    import json

                    plan_id = qm.plans.generate_id()
                    await conn.execute(
                        intervention_plans.insert().values(
                            id=plan_id,
                            title="Test Rollback Plan",
                            description="This should be rolled back",
                            objectives=json.dumps(["Test rollback"]),
                            expected_outcome="Should not exist",
                        )
                    )

                    # Force an error to trigger rollback
                    raise Exception("Forced rollback")

            # Verify plan was not created due to rollback
            final_plans = await qm.plans.list_active()
            final_count = len(final_plans)

            assert final_count == initial_count

        finally:
            await pool.close()

    async def test_foreign_key_constraints(self, integration_config):
        """
        Test foreign key constraints are enforced.
        Context7 pattern: database constraint validation testing.
        """
        pool = ConnectionPool(
            db_path=integration_config.database.db_path,
            max_connections=integration_config.database.max_connections
        )
        await pool.initialize()

        # Run migrations first
        runner = MigrationRunner(pool)
        await runner.run_migrations()

        try:
            qm = QueryManager(pool)

            # Try to create task with non-existent phase_id
            with pytest.raises(Exception):
                await qm.tasks.create(
                    phase_id="nonexistent_phase_id",
                    title="Invalid Task",
                    description="This should fail",
                )

        finally:
            await pool.close()

    async def test_performance_metrics(self, integration_config):
        """
        Test connection pool performance tracking.
        Context7 pattern: performance metrics validation in integration tests.
        """
        pool = ConnectionPool(
            db_path=integration_config.database.db_path,
            max_connections=integration_config.database.max_connections
        )
        await pool.initialize()

        # Run migrations first
        runner = MigrationRunner(pool)
        await runner.run_migrations()

        try:
            # Get initial stats
            initial_stats = pool.get_stats()

            # Perform some operations
            qm = QueryManager(pool)

            plan_id = await qm.plans.create(
                title="Performance Test Plan",
                description="Testing performance tracking",
                objectives=["Track performance"],
                expected_outcome="Metrics collected",
            )

            # Get final stats
            final_stats = pool.get_stats()

            # Verify stats were updated
            assert final_stats["write_queries"] > initial_stats["write_queries"]
            assert final_stats["connections_created"] >= initial_stats["connections_created"]

        finally:
            await pool.close()

    async def test_integration_with_shared_fixtures(
        self,
        integration_query_manager,
        integration_helper
    ):
        """
        Test database operations using shared integration fixtures.
        Context7 pattern: shared fixture usage for integration testing.
        """
        # Test using shared query manager with transaction isolation
        plan_id = await integration_query_manager.plans.create(
            title="Shared Fixture Test Plan",
            description="Testing with shared integration fixtures",
            objectives=["Validate shared fixtures", "Test transaction isolation"],
            expected_outcome="Fixtures work correctly",
        )

        # Verify plan was created
        plan = await integration_query_manager.plans.get_by_id(plan_id)
        assert plan is not None
        assert plan["title"] == "Shared Fixture Test Plan"

        # Test integration helper utilities
        initial_counts = await integration_helper.count_total_records()
        assert initial_counts["plans"] >= 1

        # Verify data consistency
        consistency_check = await integration_helper.verify_data_consistency()
        assert consistency_check is True

    async def test_concurrent_transactions(self, integration_config):
        """
        Test concurrent transaction handling.
        Context7 pattern: concurrent transaction safety testing.
        """
        pool = ConnectionPool(
            db_path=integration_config.database.db_path,
            max_connections=integration_config.database.max_connections
        )
        await pool.initialize()

        # Run migrations first
        runner = MigrationRunner(pool)
        await runner.run_migrations()

        try:
            qm = QueryManager(pool)

            # Create multiple memory entries concurrently
            async def create_memory_entry(index: int):
                return await qm.memory.store(
                    content=f"Concurrent memory entry {index}",
                    content_type="test",
                    keywords=[f"concurrent", f"test{index}"],
                )

            # Run 10 concurrent memory operations
            tasks = [create_memory_entry(i) for i in range(10)]
            memory_ids = await asyncio.gather(*tasks)

            assert len(memory_ids) == 10
            assert len(set(memory_ids)) == 10  # All IDs should be unique

            # Verify all memories were created
            for memory_id in memory_ids:
                memory = await qm.memory.get_by_id(memory_id)
                assert memory is not None

        finally:
            await pool.close()