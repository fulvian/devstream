"""
Comprehensive unit tests for task repository layer.

Tests repository CRUD operations, dependency management, search functionality,
and database integration with Context7-validated patterns.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4
from typing import List, Dict, Optional

from devstream.tasks.repository import (
    TaskRepository,
    TaskRepositoryError,
    TaskNotFoundError,
    DependencyCycleError
)
from devstream.tasks.models import (
    InterventionPlan, Phase, MicroTask, TaskDependencyGraph,
    TaskStatus, TaskPriority, TaskType, TaskComplexity
)
from devstream.database.connection import ConnectionPool


@pytest.mark.unit
@pytest.mark.tasks
class TestTaskRepository:
    """Test task repository core functionality."""

    @pytest.fixture
    async def mock_engine(self):
        """Create mock database engine."""
        engine = AsyncMock()
        mock_conn = AsyncMock()
        mock_transaction = AsyncMock()

        # Setup context managers
        engine.connect.return_value.__aenter__.return_value = mock_conn
        engine.begin.return_value.__aenter__.return_value = mock_transaction

        return engine, mock_conn, mock_transaction

    @pytest.fixture
    def task_repository(self, mock_engine):
        """Create task repository with mocked engine."""
        engine, mock_conn, mock_transaction = mock_engine
        return TaskRepository(engine=engine), mock_conn, mock_transaction

    @pytest.fixture
    def sample_intervention_plan(self):
        """Create sample intervention plan for testing."""
        return InterventionPlan(
            title="User Authentication System",
            description="Implement JWT-based user authentication",
            objective="Secure user access to the application",
            category="security",
            tags=["authentication", "jwt", "security"],
            stakeholders=["dev-team", "security-team"],
            estimated_hours=20.0,
            success_criteria=["JWT tokens working", "Password hashing secure"],
            key_deliverables=["Login endpoint", "Token validation"]
        )

    @pytest.fixture
    def sample_phase(self):
        """Create sample phase for testing."""
        return Phase(
            name="Authentication Implementation",
            description="Implement core authentication features",
            objective="Working authentication system",
            order_index=1,
            estimated_hours=8.0
        )

    @pytest.fixture
    def sample_micro_task(self):
        """Create sample micro task for testing."""
        return MicroTask(
            title="Create JWT utilities",
            description="Implement JWT token generation and validation",
            task_type=TaskType.IMPLEMENTATION,
            complexity=TaskComplexity.MODERATE,
            priority=TaskPriority.HIGH,
            estimated_minutes=30,
            keywords=["jwt", "security", "tokens"],
            acceptance_criteria=["Token generation works", "Validation is secure"]
        )


@pytest.mark.unit
@pytest.mark.tasks
class TestInterventionPlanOperations:
    """Test intervention plan CRUD operations."""

    async def test_create_intervention_plan(self, task_repository, sample_intervention_plan):
        """Test creating intervention plan."""
        repo, mock_conn, mock_transaction = task_repository

        # Mock database insert
        mock_transaction.execute = AsyncMock()

        result = await repo.create_intervention_plan(sample_intervention_plan)

        assert result == sample_intervention_plan
        assert mock_transaction.execute.called

        # Verify insert data structure
        call_args = mock_transaction.execute.call_args
        insert_values = call_args[0][0].compile().params
        assert insert_values["title"] == "User Authentication System"
        assert insert_values["status"] == "pending"
        assert "authentication" in insert_values["tags"]

    async def test_get_intervention_plan_found(self, task_repository, sample_intervention_plan):
        """Test retrieving existing intervention plan."""
        repo, mock_conn, mock_transaction = task_repository

        # Mock database result
        mock_row = MagicMock()
        mock_row.id = str(sample_intervention_plan.id)
        mock_row.title = sample_intervention_plan.title
        mock_row.description = sample_intervention_plan.description
        mock_row.objectives = [sample_intervention_plan.objective]
        mock_row.status = "pending"
        mock_row.estimated_hours = 20.0
        mock_row.actual_hours = 0.0
        mock_row.created_at = sample_intervention_plan.created_at
        mock_row.updated_at = sample_intervention_plan.updated_at
        mock_row.completed_at = None
        mock_row.tags = ["authentication", "jwt"]
        mock_row.expected_outcome = "Working auth system"
        mock_row.metadata = {"success_criteria": ["JWT tokens working"]}
        mock_row.technical_specs = {"category": "security", "ai_generated": False}

        mock_result = AsyncMock()
        mock_result.fetchone.return_value = mock_row
        mock_conn.execute.return_value = mock_result

        result = await repo.get_intervention_plan(sample_intervention_plan.id)

        assert result is not None
        assert result.id == sample_intervention_plan.id
        assert result.title == sample_intervention_plan.title
        assert result.status == TaskStatus.PENDING

    async def test_get_intervention_plan_not_found(self, task_repository):
        """Test retrieving non-existent intervention plan."""
        repo, mock_conn, mock_transaction = task_repository

        # Mock empty result
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = None
        mock_conn.execute.return_value = mock_result

        result = await repo.get_intervention_plan(uuid4())

        assert result is None

    async def test_update_intervention_plan(self, task_repository, sample_intervention_plan):
        """Test updating intervention plan."""
        repo, mock_conn, mock_transaction = task_repository

        # Update plan properties
        sample_intervention_plan.title = "Updated Authentication System"
        sample_intervention_plan.actual_hours = 5.0
        sample_intervention_plan.status = TaskStatus.IN_PROGRESS

        mock_transaction.execute = AsyncMock()

        result = await repo.update_intervention_plan(sample_intervention_plan)

        assert result.title == "Updated Authentication System"
        assert result.actual_hours == 5.0
        assert result.updated_at is not None
        assert mock_transaction.execute.called

    async def test_delete_intervention_plan(self, task_repository):
        """Test deleting intervention plan."""
        repo, mock_conn, mock_transaction = task_repository

        # Mock successful deletion
        mock_result = AsyncMock()
        mock_result.rowcount = 1
        mock_transaction.execute.return_value = mock_result

        plan_id = uuid4()
        result = await repo.delete_intervention_plan(plan_id)

        assert result is True
        assert mock_transaction.execute.called

    async def test_list_intervention_plans(self, task_repository):
        """Test listing intervention plans with filtering."""
        repo, mock_conn, mock_transaction = task_repository

        # Mock multiple plans result
        mock_rows = []
        for i in range(3):
            mock_row = MagicMock()
            mock_row.id = str(uuid4())
            mock_row.title = f"Plan {i+1}"
            mock_row.description = f"Description {i+1}"
            mock_row.objectives = [f"Objective {i+1}"]
            mock_row.status = "pending" if i < 2 else "completed"
            mock_row.estimated_hours = 10.0
            mock_row.actual_hours = 0.0
            mock_row.created_at = datetime.now()
            mock_row.updated_at = datetime.now()
            mock_row.completed_at = None
            mock_row.tags = []
            mock_row.expected_outcome = f"Outcome {i+1}"
            mock_row.metadata = {}
            mock_row.technical_specs = {}
            mock_rows.append(mock_row)

        mock_result = AsyncMock()
        mock_result.fetchall.return_value = mock_rows
        mock_conn.execute.return_value = mock_result

        # Test without filtering
        plans = await repo.list_intervention_plans()
        assert len(plans) == 3

        # Test with status filtering
        plans = await repo.list_intervention_plans(status=TaskStatus.PENDING)
        assert mock_conn.execute.called


@pytest.mark.unit
@pytest.mark.tasks
class TestPhaseOperations:
    """Test phase CRUD operations."""

    async def test_create_phase(self, task_repository, sample_phase):
        """Test creating phase."""
        repo, mock_conn, mock_transaction = task_repository

        mock_transaction.execute = AsyncMock()
        plan_id = uuid4()

        result = await repo.create_phase(sample_phase, plan_id)

        assert result == sample_phase
        assert mock_transaction.execute.called

        # Verify phase data structure
        call_args = mock_transaction.execute.call_args
        insert_values = call_args[0][0].compile().params
        assert insert_values["name"] == "Authentication Implementation"
        assert insert_values["plan_id"] == str(plan_id)
        assert insert_values["sequence_order"] == 1

    async def test_get_phase(self, task_repository, sample_phase):
        """Test retrieving phase by ID."""
        repo, mock_conn, mock_transaction = task_repository

        # Mock phase result
        mock_row = MagicMock()
        mock_row.id = str(sample_phase.id)
        mock_row.name = sample_phase.name
        mock_row.description = sample_phase.description
        mock_row.completion_criteria = sample_phase.objective
        mock_row.sequence_order = sample_phase.order_index
        mock_row.status = "pending"
        mock_row.estimated_minutes = 480  # 8 hours * 60
        mock_row.actual_minutes = 0
        mock_row.created_at = sample_phase.created_at
        mock_row.started_at = None
        mock_row.completed_at = None
        mock_row.dependencies = []

        mock_result = AsyncMock()
        mock_result.fetchone.return_value = mock_row
        mock_conn.execute.return_value = mock_result

        result = await repo.get_phase(sample_phase.id)

        assert result is not None
        assert result.id == sample_phase.id
        assert result.name == sample_phase.name
        assert result.order_index == 1
        assert result.estimated_hours == 8.0

    async def test_get_phases_for_plan(self, task_repository):
        """Test retrieving all phases for a plan."""
        repo, mock_conn, mock_transaction = task_repository

        # Mock multiple phases
        mock_rows = []
        for i in range(3):
            mock_row = MagicMock()
            mock_row.id = str(uuid4())
            mock_row.name = f"Phase {i+1}"
            mock_row.description = f"Description {i+1}"
            mock_row.completion_criteria = f"Objective {i+1}"
            mock_row.sequence_order = i + 1
            mock_row.status = "pending"
            mock_row.estimated_minutes = 240
            mock_row.actual_minutes = 0
            mock_row.created_at = datetime.now()
            mock_row.started_at = None
            mock_row.completed_at = None
            mock_row.dependencies = []
            mock_rows.append(mock_row)

        mock_result = AsyncMock()
        mock_result.fetchall.return_value = mock_rows
        mock_conn.execute.return_value = mock_result

        plan_id = uuid4()
        phases = await repo.get_phases_for_plan(plan_id)

        assert len(phases) == 3
        assert all(phase.order_index == i+1 for i, phase in enumerate(phases))

    async def test_update_phase(self, task_repository, sample_phase):
        """Test updating phase."""
        repo, mock_conn, mock_transaction = task_repository

        # Update phase properties
        sample_phase.name = "Updated Authentication Phase"
        sample_phase.status = TaskStatus.IN_PROGRESS
        sample_phase.actual_hours = 2.0

        mock_transaction.execute = AsyncMock()

        result = await repo.update_phase(sample_phase)

        assert result.name == "Updated Authentication Phase"
        assert result.status == TaskStatus.IN_PROGRESS
        assert result.updated_at is not None
        assert mock_transaction.execute.called


@pytest.mark.unit
@pytest.mark.tasks
class TestMicroTaskOperations:
    """Test micro task CRUD operations."""

    async def test_create_micro_task(self, task_repository, sample_micro_task):
        """Test creating micro task."""
        repo, mock_conn, mock_transaction = task_repository

        mock_transaction.execute = AsyncMock()
        phase_id = uuid4()

        result = await repo.create_micro_task(sample_micro_task, phase_id)

        assert result == sample_micro_task
        assert mock_transaction.execute.called

        # Verify task data structure
        call_args = mock_transaction.execute.call_args
        insert_values = call_args[0][0].compile().params
        assert insert_values["title"] == "Create JWT utilities"
        assert insert_values["phase_id"] == str(phase_id)
        assert insert_values["task_type"] == "coding"
        assert insert_values["priority"] == 7  # HIGH priority maps to 7

    async def test_get_micro_task(self, task_repository, sample_micro_task):
        """Test retrieving micro task by ID."""
        repo, mock_conn, mock_transaction = task_repository

        # Mock task result
        mock_row = MagicMock()
        mock_row.id = str(sample_micro_task.id)
        mock_row.title = sample_micro_task.title
        mock_row.description = sample_micro_task.description
        mock_row.task_type = "coding"
        mock_row.priority = 7
        mock_row.status = "pending"
        mock_row.max_duration_minutes = 30
        mock_row.actual_duration_minutes = 0
        mock_row.assigned_agent = None
        mock_row.created_at = sample_micro_task.created_at
        mock_row.started_at = None
        mock_row.completed_at = None
        mock_row.documentation = ""
        mock_row.output_files = []
        mock_row.validation_metadata = {
            "complexity": "moderate",
            "validation_passed": False,
            "ai_generated": False,
            "context_tags": [],
            "related_memory_ids": []
        }
        # Add missing attributes
        mock_row.dependencies = []
        mock_row.keywords = ["jwt", "security"]
        mock_row.acceptance_criteria = ["Token generation works"]
        mock_row.ai_suggestions = None
        mock_row.updated_at = None

        mock_result = AsyncMock()
        mock_result.fetchone.return_value = mock_row
        mock_conn.execute.return_value = mock_result

        result = await repo.get_micro_task(sample_micro_task.id)

        assert result is not None
        assert result.id == sample_micro_task.id
        assert result.title == sample_micro_task.title
        assert result.task_type == TaskType.IMPLEMENTATION
        assert result.priority == TaskPriority.HIGH
        assert result.complexity == TaskComplexity.MODERATE

    async def test_get_tasks_for_phase(self, task_repository):
        """Test retrieving all tasks for a phase."""
        repo, mock_conn, mock_transaction = task_repository

        # Mock multiple tasks
        mock_rows = []
        for i in range(4):
            mock_row = MagicMock()
            mock_row.id = str(uuid4())
            mock_row.title = f"Task {i+1}"
            mock_row.description = f"Description {i+1}"
            mock_row.task_type = "coding"
            mock_row.priority = 5
            mock_row.status = "pending"
            mock_row.max_duration_minutes = 15
            mock_row.actual_duration_minutes = 0
            mock_row.assigned_agent = None
            mock_row.created_at = datetime.now()
            mock_row.started_at = None
            mock_row.completed_at = None
            mock_row.documentation = ""
            mock_row.output_files = []
            mock_row.validation_metadata = {"complexity": "simple"}
            mock_row.dependencies = []
            mock_row.keywords = []
            mock_row.acceptance_criteria = []
            mock_row.ai_suggestions = None
            mock_row.updated_at = None
            mock_rows.append(mock_row)

        mock_result = AsyncMock()
        mock_result.fetchall.return_value = mock_rows
        mock_conn.execute.return_value = mock_result

        phase_id = uuid4()
        tasks = await repo.get_tasks_for_phase(phase_id)

        assert len(tasks) == 4
        assert all(task.title.startswith("Task") for task in tasks)

    async def test_update_micro_task(self, task_repository, sample_micro_task):
        """Test updating micro task."""
        repo, mock_conn, mock_transaction = task_repository

        # Update task properties
        sample_micro_task.title = "Updated JWT utilities"
        sample_micro_task.status = TaskStatus.IN_PROGRESS
        sample_micro_task.actual_minutes = 15

        mock_transaction.execute = AsyncMock()

        result = await repo.update_micro_task(sample_micro_task)

        assert result.title == "Updated JWT utilities"
        assert result.status == TaskStatus.IN_PROGRESS
        assert result.actual_minutes == 15
        assert result.updated_at is not None
        assert mock_transaction.execute.called


@pytest.mark.unit
@pytest.mark.tasks
class TestDependencyGraphOperations:
    """Test dependency graph and task relationship operations."""

    async def test_build_dependency_graph(self, task_repository):
        """Test building complete dependency graph for a plan."""
        repo, mock_conn, mock_transaction = task_repository

        # Mock tasks with dependencies
        task1_id = uuid4()
        task2_id = uuid4()
        task3_id = uuid4()

        mock_rows = []
        for i, task_id in enumerate([task1_id, task2_id, task3_id]):
            mock_row = MagicMock()
            mock_row.id = str(task_id)
            mock_row.title = f"Task {i+1}"
            mock_row.description = f"Description {i+1}"
            mock_row.task_type = "coding"
            mock_row.priority = 5
            mock_row.status = "pending"
            mock_row.max_duration_minutes = 10
            mock_row.actual_duration_minutes = 0
            mock_row.assigned_agent = None
            mock_row.created_at = datetime.now()
            mock_row.started_at = None
            mock_row.completed_at = None
            mock_row.documentation = ""
            mock_row.output_files = []
            mock_row.validation_metadata = {"complexity": "simple"}
            mock_row.keywords = []
            mock_row.acceptance_criteria = []
            mock_row.ai_suggestions = None
            mock_row.updated_at = None

            # Set up dependencies: task2 depends on task1, task3 depends on task2
            if i == 1:  # task2
                mock_row.dependencies = [str(task1_id)]
            elif i == 2:  # task3
                mock_row.dependencies = [str(task2_id)]
            else:
                mock_row.dependencies = []

            mock_rows.append(mock_row)

        mock_result = AsyncMock()
        mock_result.fetchall.return_value = mock_rows
        mock_conn.execute.return_value = mock_result

        plan_id = uuid4()
        graph = await repo.build_dependency_graph(plan_id)

        assert isinstance(graph, TaskDependencyGraph)
        assert len(graph.tasks) == 3

    async def test_get_ready_tasks(self, task_repository):
        """Test getting tasks ready for execution."""
        repo, mock_conn, mock_transaction = task_repository

        # Mock with patch to avoid complex graph building
        with patch.object(repo, 'build_dependency_graph') as mock_build_graph:
            # Create mock graph
            mock_graph = MagicMock()
            mock_ready_tasks = [
                MagicMock(id=uuid4(), title="Ready Task 1"),
                MagicMock(id=uuid4(), title="Ready Task 2")
            ]
            mock_graph.get_ready_tasks.return_value = mock_ready_tasks
            mock_build_graph.return_value = mock_graph

            # Mock completed tasks query
            mock_result = AsyncMock()
            mock_result.fetchall.return_value = [(str(uuid4()),), (str(uuid4()),)]
            mock_conn.execute.return_value = mock_result

            plan_id = uuid4()
            ready_tasks = await repo.get_ready_tasks(plan_id)

            assert len(ready_tasks) == 2
            assert mock_build_graph.called
            assert mock_graph.get_ready_tasks.called

    async def test_validate_dependencies_valid(self, task_repository):
        """Test dependency validation without cycles."""
        repo, mock_conn, mock_transaction = task_repository

        # Mock task lookup
        task_id = uuid4()
        phase_id = uuid4()
        plan_id = uuid4()

        mock_conn.execute = AsyncMock()
        mock_conn.execute.side_effect = [
            # First call - get phase_id
            AsyncMock(scalar=lambda: str(phase_id)),
            # Second call - get plan_id
            AsyncMock(scalar=lambda: str(plan_id))
        ]

        # Mock dependency graph
        with patch.object(repo, 'build_dependency_graph') as mock_build_graph:
            mock_graph = MagicMock()
            mock_graph._would_create_cycle.return_value = False
            mock_build_graph.return_value = mock_graph

            dependency_ids = [uuid4(), uuid4()]
            result = await repo.validate_dependencies(task_id, dependency_ids)

            assert result is True
            assert mock_graph._would_create_cycle.call_count == 2

    async def test_validate_dependencies_cycle_detected(self, task_repository):
        """Test dependency validation with cycle detection."""
        repo, mock_conn, mock_transaction = task_repository

        # Mock task lookup
        task_id = uuid4()
        phase_id = uuid4()
        plan_id = uuid4()

        mock_conn.execute = AsyncMock()
        mock_conn.execute.side_effect = [
            AsyncMock(scalar=lambda: str(phase_id)),
            AsyncMock(scalar=lambda: str(plan_id))
        ]

        # Mock dependency graph with cycle
        with patch.object(repo, 'build_dependency_graph') as mock_build_graph:
            mock_graph = MagicMock()
            mock_graph._would_create_cycle.return_value = True
            mock_build_graph.return_value = mock_graph

            dependency_ids = [uuid4()]
            result = await repo.validate_dependencies(task_id, dependency_ids)

            assert result is False
            assert mock_graph._would_create_cycle.called

    async def test_validate_dependencies_task_not_found(self, task_repository):
        """Test dependency validation with non-existent task."""
        repo, mock_conn, mock_transaction = task_repository

        # Mock empty task lookup
        mock_conn.execute = AsyncMock()
        mock_conn.execute.return_value = AsyncMock(scalar=lambda: None)

        task_id = uuid4()
        dependency_ids = [uuid4()]

        with pytest.raises(TaskNotFoundError):
            await repo.validate_dependencies(task_id, dependency_ids)


@pytest.mark.unit
@pytest.mark.tasks
class TestSearchAndQueryOperations:
    """Test search and query functionality."""

    async def test_search_tasks_by_query(self, task_repository):
        """Test searching tasks by text query."""
        repo, mock_conn, mock_transaction = task_repository

        # Mock search results
        mock_rows = []
        for i in range(3):
            mock_row = MagicMock()
            mock_row.id = str(uuid4())
            mock_row.title = f"Authentication Task {i+1}"
            mock_row.description = f"JWT authentication implementation {i+1}"
            mock_row.task_type = "coding"
            mock_row.priority = 5
            mock_row.status = "pending"
            mock_row.max_duration_minutes = 20
            mock_row.actual_duration_minutes = 0
            mock_row.assigned_agent = None
            mock_row.created_at = datetime.now()
            mock_row.started_at = None
            mock_row.completed_at = None
            mock_row.documentation = ""
            mock_row.output_files = []
            mock_row.validation_metadata = {"complexity": "simple"}
            mock_row.dependencies = []
            mock_row.keywords = ["jwt", "auth"]
            mock_row.acceptance_criteria = []
            mock_row.ai_suggestions = None
            mock_row.updated_at = None
            mock_rows.append(mock_row)

        mock_result = AsyncMock()
        mock_result.fetchall.return_value = mock_rows
        mock_conn.execute.return_value = mock_result

        tasks = await repo.search_tasks(query="authentication")

        assert len(tasks) == 3
        assert all("Authentication" in task.title for task in tasks)
        assert mock_conn.execute.called

    async def test_search_tasks_with_filters(self, task_repository):
        """Test searching tasks with type and status filters."""
        repo, mock_conn, mock_transaction = task_repository

        # Mock filtered results
        mock_rows = []
        for i in range(2):
            mock_row = MagicMock()
            mock_row.id = str(uuid4())
            mock_row.title = f"Testing Task {i+1}"
            mock_row.description = f"Unit test implementation {i+1}"
            mock_row.task_type = "testing"
            mock_row.priority = 5
            mock_row.status = "completed"
            mock_row.max_duration_minutes = 15
            mock_row.actual_duration_minutes = 12
            mock_row.assigned_agent = "test-agent"
            mock_row.created_at = datetime.now()
            mock_row.started_at = datetime.now()
            mock_row.completed_at = datetime.now()
            mock_row.documentation = "Test documentation"
            mock_row.output_files = []
            mock_row.validation_metadata = {"complexity": "simple"}
            mock_row.dependencies = []
            mock_row.keywords = ["testing", "unit"]
            mock_row.acceptance_criteria = []
            mock_row.ai_suggestions = None
            mock_row.updated_at = None
            mock_rows.append(mock_row)

        mock_result = AsyncMock()
        mock_result.fetchall.return_value = mock_rows
        mock_conn.execute.return_value = mock_result

        tasks = await repo.search_tasks(
            query="testing",
            task_types=[TaskType.TESTING],
            statuses=[TaskStatus.COMPLETED]
        )

        assert len(tasks) == 2
        assert all(task.task_type == TaskType.TESTING for task in tasks)
        assert all(task.status == TaskStatus.COMPLETED for task in tasks)

    async def test_get_task_statistics(self, task_repository):
        """Test getting task statistics for a plan."""
        repo, mock_conn, mock_transaction = task_repository

        # Mock statistics query result
        mock_stats_data = [
            ("pending", 5),
            ("active", 2),
            ("completed", 8),
            ("failed", 1)
        ]

        mock_result = AsyncMock()
        mock_result.fetchall.return_value = mock_stats_data
        mock_conn.execute.return_value = mock_result

        plan_id = uuid4()
        stats = await repo.get_task_statistics(plan_id)

        assert stats["pending"] == 5
        assert stats["active"] == 2
        assert stats["completed"] == 8
        assert stats["failed"] == 1
        assert stats["skipped"] == 0  # Default value for missing status
        assert mock_conn.execute.called


@pytest.mark.unit
@pytest.mark.tasks
class TestRepositoryHelperMethods:
    """Test repository helper and mapping methods."""

    def test_status_mapping_to_db(self, task_repository):
        """Test status mapping to database values."""
        repo, _, _ = task_repository

        assert repo._map_status_to_db(TaskStatus.PENDING) == "pending"
        assert repo._map_status_to_db(TaskStatus.IN_PROGRESS) == "active"
        assert repo._map_status_to_db(TaskStatus.COMPLETED) == "completed"
        assert repo._map_status_to_db(TaskStatus.BLOCKED) == "blocked"
        assert repo._map_status_to_db(TaskStatus.CANCELLED) == "cancelled"

    def test_status_mapping_from_db(self, task_repository):
        """Test status mapping from database values."""
        repo, _, _ = task_repository

        assert repo._map_status_from_db("pending") == TaskStatus.PENDING
        assert repo._map_status_from_db("active") == TaskStatus.IN_PROGRESS
        assert repo._map_status_from_db("completed") == TaskStatus.COMPLETED
        assert repo._map_status_from_db("failed") == TaskStatus.CANCELLED
        assert repo._map_status_from_db("unknown") == TaskStatus.PENDING  # Default

    def test_priority_mapping_to_db(self, task_repository):
        """Test priority mapping to database values."""
        repo, _, _ = task_repository

        assert repo._map_priority_to_db(TaskPriority.LOW) == 3
        assert repo._map_priority_to_db(TaskPriority.MEDIUM) == 5
        assert repo._map_priority_to_db(TaskPriority.HIGH) == 7
        assert repo._map_priority_to_db(TaskPriority.CRITICAL) == 10

    def test_priority_mapping_from_db(self, task_repository):
        """Test priority mapping from database values."""
        repo, _, _ = task_repository

        assert repo._map_priority_from_db(1) == TaskPriority.LOW
        assert repo._map_priority_from_db(5) == TaskPriority.MEDIUM
        assert repo._map_priority_from_db(7) == TaskPriority.HIGH
        assert repo._map_priority_from_db(10) == TaskPriority.CRITICAL

    def test_task_type_mapping_to_db(self, task_repository):
        """Test task type mapping to database values."""
        repo, _, _ = task_repository

        assert repo._map_task_type_to_db(TaskType.RESEARCH) == "research"
        assert repo._map_task_type_to_db(TaskType.IMPLEMENTATION) == "coding"
        assert repo._map_task_type_to_db(TaskType.TESTING) == "testing"
        assert repo._map_task_type_to_db(TaskType.DOCUMENTATION) == "documentation"
        assert repo._map_task_type_to_db(TaskType.REFACTORING) == "coding"

    def test_task_type_mapping_from_db(self, task_repository):
        """Test task type mapping from database values."""
        repo, _, _ = task_repository

        assert repo._map_task_type_from_db("research") == TaskType.RESEARCH
        assert repo._map_task_type_from_db("coding") == TaskType.IMPLEMENTATION
        assert repo._map_task_type_from_db("testing") == TaskType.TESTING
        assert repo._map_task_type_from_db("documentation") == TaskType.DOCUMENTATION
        assert repo._map_task_type_from_db("unknown") == TaskType.IMPLEMENTATION  # Default


@pytest.mark.unit
@pytest.mark.tasks
class TestRepositoryErrorHandling:
    """Test repository error handling and edge cases."""

    async def test_repository_with_default_engine(self):
        """Test repository initialization with default engine."""
        with patch('devstream.tasks.repository.ConnectionPool') as mock_pool:
            mock_engine = AsyncMock()
            mock_pool.return_value.engine = mock_engine

            repo = TaskRepository()

            assert repo.engine == mock_engine
            mock_pool.assert_called_once_with("test.db")

    async def test_repository_error_inheritance(self):
        """Test repository error inheritance hierarchy."""
        base_error = TaskRepositoryError("Base error")
        assert isinstance(base_error, Exception)

        not_found_error = TaskNotFoundError("Task not found")
        assert isinstance(not_found_error, TaskRepositoryError)

        cycle_error = DependencyCycleError("Cycle detected")
        assert isinstance(cycle_error, TaskRepositoryError)

    async def test_create_plan_with_integrity_error(self, task_repository, sample_intervention_plan):
        """Test handling database integrity errors during plan creation."""
        repo, mock_conn, mock_transaction = task_repository

        # Mock integrity error
        mock_transaction.execute.side_effect = IntegrityError("Duplicate key", None, None)

        with pytest.raises(IntegrityError):
            await repo.create_intervention_plan(sample_intervention_plan)

    async def test_row_conversion_with_missing_data(self, task_repository):
        """Test row conversion with missing or None data."""
        repo, _, _ = task_repository

        # Mock minimal row data
        mock_row = MagicMock()
        mock_row.id = str(uuid4())
        mock_row.title = "Minimal Task"
        mock_row.description = None  # Missing description
        mock_row.task_type = "coding"
        mock_row.priority = 5
        mock_row.status = "pending"
        mock_row.max_duration_minutes = None  # Missing duration
        mock_row.actual_duration_minutes = None
        mock_row.assigned_agent = None
        mock_row.created_at = datetime.now()
        mock_row.started_at = None
        mock_row.completed_at = None
        mock_row.documentation = None
        mock_row.output_files = None
        mock_row.validation_metadata = None
        mock_row.dependencies = None
        mock_row.keywords = None
        mock_row.acceptance_criteria = None
        mock_row.ai_suggestions = None
        mock_row.updated_at = None

        task = repo._row_to_micro_task(mock_row)

        assert task.title == "Minimal Task"
        assert task.description is None
        assert task.estimated_minutes == 5  # Default value
        assert task.keywords == []  # Default empty list
        assert task.depends_on == set()  # Default empty set