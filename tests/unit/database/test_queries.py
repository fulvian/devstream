"""
Unit tests for database query operations.
"""

import pytest
import pytest_asyncio
from datetime import datetime

from devstream.database.queries import (
    InterventionPlanQueries,
    MicroTaskQueries,
    SemanticMemoryQueries,
    WorkSessionQueries,
    QueryManager,
)


@pytest.mark.unit
@pytest.mark.database
class TestInterventionPlanQueries:
    """Test intervention plan query operations."""

    async def test_create_plan(self, query_manager: QueryManager):
        """Test creating intervention plan."""
        plan_id = await query_manager.plans.create(
            title="Test Plan",
            description="Test description",
            objectives=["Objective 1", "Objective 2"],
            expected_outcome="Test outcome",
            priority=5,
            tags=["test", "unit"],
        )

        assert plan_id is not None
        assert len(plan_id) == 32  # UUID hex without dashes

    async def test_get_plan_by_id(self, query_manager: QueryManager, sample_plan: str):
        """Test retrieving plan by ID."""
        plan = await query_manager.plans.get_by_id(sample_plan)

        assert plan is not None
        assert plan["id"] == sample_plan
        assert plan["title"] == "Test Plan"
        assert isinstance(plan["objectives"], list)
        assert len(plan["objectives"]) == 2

    async def test_get_nonexistent_plan(self, query_manager: QueryManager):
        """Test retrieving non-existent plan."""
        plan = await query_manager.plans.get_by_id("nonexistent_id")
        assert plan is None

    async def test_list_active_plans(self, query_manager: QueryManager, sample_plan: str):
        """Test listing active plans."""
        plans = await query_manager.plans.list_active(limit=10)

        assert len(plans) >= 1
        assert any(plan["id"] == sample_plan for plan in plans)

    async def test_update_plan_status(self, query_manager: QueryManager, sample_plan: str):
        """Test updating plan status."""
        success = await query_manager.plans.update_status(
            sample_plan, "completed", datetime.utcnow()
        )

        assert success is True

        # Verify update
        plan = await query_manager.plans.get_by_id(sample_plan)
        assert plan["status"] == "completed"
        assert plan["completed_at"] is not None


@pytest.mark.unit
@pytest.mark.database
class TestMicroTaskQueries:
    """Test micro task query operations."""

    async def test_create_task(self, query_manager: QueryManager, sample_plan: str):
        """Test creating micro task."""
        from devstream.database.schema import phases

        # Create phase first
        phase_id = query_manager.tasks.generate_id()

        async with query_manager.pool.write_transaction() as conn:
            await conn.execute(
                phases.insert().values(
                    id=phase_id,
                    plan_id=sample_plan,
                    name="Test Phase",
                    description="Test phase",
                    sequence_order=1,
                    status="pending",
                )
            )

        task_id = await query_manager.tasks.create(
            phase_id=phase_id,
            title="Test Task",
            description="Test task description",
            assigned_agent="test-agent",
            task_type="coding",
            priority=7,
        )

        assert task_id is not None
        assert len(task_id) == 32

    async def test_get_pending_tasks(self, query_manager: QueryManager, sample_task: str):
        """Test retrieving pending tasks for a phase."""
        # Get task to find phase_id
        from devstream.database.schema import micro_tasks
        from sqlalchemy import select

        query = select(micro_tasks).where(micro_tasks.c.id == sample_task)
        results = await query_manager.execute_read(query)
        phase_id = results[0]["phase_id"]

        tasks = await query_manager.tasks.get_pending_by_phase(phase_id)

        assert len(tasks) >= 1
        assert any(task["id"] == sample_task for task in tasks)

    async def test_update_task_execution(self, query_manager: QueryManager, sample_task: str):
        """Test updating task execution results."""
        success = await query_manager.tasks.update_execution(
            sample_task,
            status="completed",
            duration_minutes=5.5,
            tokens_used=1000,
            generated_code="print('Hello World')",
        )

        assert success is True


@pytest.mark.unit
@pytest.mark.database
class TestSemanticMemoryQueries:
    """Test semantic memory query operations."""

    async def test_store_memory(self, query_manager: QueryManager):
        """Test storing semantic memory."""
        memory_id = await query_manager.memory.store(
            content="def test_function(): pass",
            content_type="code",
            keywords=["test", "function"],
            entities=["test_function"],
        )

        assert memory_id is not None
        assert len(memory_id) == 32

    async def test_search_by_keywords(self, query_manager: QueryManager):
        """Test searching memory by keywords."""
        # Store some memory entries
        await query_manager.memory.store(
            content="Authentication implementation with JWT tokens",
            content_type="code",
            keywords=["auth", "jwt", "token"],
        )

        await query_manager.memory.store(
            content="User authentication API documentation",
            content_type="documentation",
            keywords=["auth", "api", "user"],
        )

        # Search for memories
        results = await query_manager.memory.search_by_keywords(
            keywords=["auth"], limit=10
        )

        assert len(results) >= 2
        assert all("auth" in result["content"].lower() for result in results)

    async def test_update_memory_access(self, query_manager: QueryManager):
        """Test updating memory access statistics."""
        memory_id = await query_manager.memory.store(
            content="Test memory for access tracking",
            content_type="test",
        )

        success = await query_manager.memory.update_access(memory_id)
        assert success is True


@pytest.mark.unit
@pytest.mark.database
class TestWorkSessionQueries:
    """Test work session query operations."""

    async def test_create_session(self, query_manager: QueryManager, sample_plan: str):
        """Test creating work session."""
        session_id = await query_manager.sessions.create(
            session_name="Test Session",
            plan_id=sample_plan,
            user_id="test_user",
        )

        assert session_id is not None
        assert len(session_id) == 32

    async def test_get_active_session(self, query_manager: QueryManager, sample_plan: str):
        """Test retrieving active session."""
        # Create active session
        session_id = await query_manager.sessions.create(
            session_name="Active Session",
            plan_id=sample_plan,
        )

        session = await query_manager.sessions.get_active()

        assert session is not None
        assert session["id"] == session_id
        assert session["status"] == "active"

    async def test_update_session_tasks(self, query_manager: QueryManager, sample_plan: str, sample_task: str):
        """Test updating session task lists."""
        session_id = await query_manager.sessions.create(
            session_name="Task Session",
            plan_id=sample_plan,
        )

        # Add task to active list
        success = await query_manager.sessions.update_tasks(
            session_id, sample_task, completed=False
        )
        assert success is True

        # Move task to completed
        success = await query_manager.sessions.update_tasks(
            session_id, sample_task, completed=True
        )
        assert success is True


@pytest.mark.unit
@pytest.mark.database
class TestQueryManager:
    """Test query manager integration."""

    async def test_query_manager_initialization(self, db_manager):
        """Test query manager initialization."""
        qm = QueryManager(db_manager.pool)

        assert qm.plans is not None
        assert qm.tasks is not None
        assert qm.memory is not None
        assert qm.sessions is not None

    async def test_health_check(self, query_manager: QueryManager):
        """Test database health check."""
        health = await query_manager.health_check()
        assert health is True

    async def test_base_query_methods(self, query_manager: QueryManager):
        """Test base query functionality."""
        # Test ID generation
        id1 = query_manager.plans.generate_id()
        id2 = query_manager.plans.generate_id()

        assert len(id1) == 32
        assert len(id2) == 32
        assert id1 != id2  # Should be unique