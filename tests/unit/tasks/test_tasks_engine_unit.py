"""
Unit tests for task engine functionality.

Context7-validated patterns for workflow engine testing:
- AI-powered task breakdown with mocking
- Step execution and retry behavior
- Workflow state management and transitions
- Error handling and recovery patterns
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from typing import List, Dict, Any

from devstream.tasks.engine import TaskEngine
from devstream.tasks.models import (
    MicroTask,
    Phase,
    InterventionPlan,
    TaskStatus,
    TaskType,
    TaskComplexity,
    TaskPriority
)
from devstream.planning.models import (
    TaskBreakdownRequest,
    PlanGenerationRequest,
    AITaskSuggestion
)


@pytest.mark.unit
@pytest.mark.tasks
class TestTaskEngine:
    """Test task engine with Context7-validated workflow patterns."""

    @pytest.fixture
    def mock_ai_planner(self):
        """Create mock AI planner for testing."""
        planner = Mock()
        planner.generate_task_breakdown = AsyncMock()
        planner.generate_plan = AsyncMock()
        planner.health_check = AsyncMock(return_value={"status": "healthy"})
        return planner

    @pytest.fixture
    def mock_memory_system(self):
        """Create mock memory system."""
        memory = Mock()
        memory.store_context = AsyncMock()
        memory.retrieve_context = AsyncMock()
        memory.search_similar = AsyncMock(return_value=[])
        return memory

    @pytest.fixture
    def mock_repository(self):
        """Create mock task repository."""
        repo = Mock()
        repo.create_task = AsyncMock()
        repo.update_task = AsyncMock()
        repo.get_task = AsyncMock()
        repo.list_tasks = AsyncMock(return_value=[])
        repo.create_phase = AsyncMock()
        repo.create_plan = AsyncMock()
        return repo

    @pytest.fixture
    def task_engine(self, mock_ai_planner, mock_memory_system, mock_repository):
        """Create task engine with mocked dependencies."""
        return TaskEngine(
            ai_planner=mock_ai_planner,
            memory_system=mock_memory_system,
            repository=mock_repository
        )

    def test_engine_initialization(self, task_engine, mock_ai_planner, mock_memory_system, mock_repository):
        """Test task engine initializes correctly."""
        assert task_engine.ai_planner == mock_ai_planner
        assert task_engine.memory_system == mock_memory_system
        assert task_engine.repository == mock_repository
        assert task_engine.retry_config is not None

    @pytest.mark.asyncio
    async def test_basic_task_breakdown(self, task_engine, mock_ai_planner):
        """Test basic AI-powered task breakdown."""
        # Mock AI response
        ai_suggestions = [
            AITaskSuggestion(
                title="Setup authentication framework",
                description="Initialize JWT authentication system",
                task_type=TaskType.IMPLEMENTATION,
                estimated_minutes=8,
                complexity=TaskComplexity.MODERATE,
                priority=TaskPriority.HIGH
            ),
            AITaskSuggestion(
                title="Create login endpoint",
                description="Build user login API endpoint",
                task_type=TaskType.IMPLEMENTATION,
                estimated_minutes=6,
                complexity=TaskComplexity.MODERATE,
                priority=TaskPriority.MEDIUM
            ),
            AITaskSuggestion(
                title="Test authentication flow",
                description="Write tests for authentication",
                task_type=TaskType.TESTING,
                estimated_minutes=5,
                complexity=TaskComplexity.SIMPLE,
                priority=TaskPriority.MEDIUM
            )
        ]

        mock_ai_planner.generate_task_breakdown.return_value.tasks = ai_suggestions

        # Test breakdown request
        request = TaskBreakdownRequest(
            objective="Implement user authentication system",
            context="Building secure login for web application",
            max_tasks=5,
            target_complexity=TaskComplexity.MODERATE
        )

        result = await task_engine.breakdown_task(request)

        assert len(result.tasks) == 3
        assert all(isinstance(task, MicroTask) for task in result.tasks)
        assert result.tasks[0].title == "Setup authentication framework"
        assert result.tasks[0].task_type == TaskType.IMPLEMENTATION
        mock_ai_planner.generate_task_breakdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_breakdown_with_context_retrieval(self, task_engine, mock_ai_planner, mock_memory_system):
        """Test task breakdown with memory context retrieval."""
        # Mock memory context
        mock_memory_system.retrieve_context.return_value = """
        Previous authentication implementations:
        - Used JWT tokens for session management
        - Implemented password hashing with bcrypt
        - Added rate limiting for login attempts
        """

        # Mock AI suggestions
        ai_suggestions = [
            AITaskSuggestion(
                title="Implement JWT token service",
                description="Create JWT token generation and validation",
                task_type=TaskType.IMPLEMENTATION,
                estimated_minutes=7,
                complexity=TaskComplexity.MODERATE,
                priority=TaskPriority.HIGH
            )
        ]
        mock_ai_planner.generate_task_breakdown.return_value.tasks = ai_suggestions

        request = TaskBreakdownRequest(
            objective="Enhance authentication system",
            context="Improve existing authentication",
            use_memory_context=True
        )

        result = await task_engine.breakdown_task(request)

        # Should have retrieved context and used it
        mock_memory_system.retrieve_context.assert_called_once()
        assert len(result.tasks) == 1
        assert "JWT" in result.tasks[0].title

    @pytest.mark.asyncio
    async def test_task_execution_workflow(self, task_engine, mock_repository):
        """Test complete task execution workflow."""
        # Create test task
        task = MicroTask(
            title="Implement user validation",
            description="Add input validation for user data",
            task_type=TaskType.IMPLEMENTATION,
            estimated_minutes=6
        )

        mock_repository.get_task.return_value = task
        mock_repository.update_task.return_value = True

        # Start task execution
        result = await task_engine.start_task(task.id)

        assert result.success
        assert result.task_id == task.id
        mock_repository.update_task.assert_called()

        # Check that task status was updated to IN_PROGRESS
        update_call = mock_repository.update_task.call_args[0][0]
        assert update_call.status == TaskStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_task_completion_workflow(self, task_engine, mock_repository, mock_memory_system):
        """Test task completion workflow with memory storage."""
        # Create task in progress
        task = MicroTask(
            title="Create user model",
            description="Define user data structure",
            task_type=TaskType.IMPLEMENTATION,
            estimated_minutes=5,
            status=TaskStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )

        mock_repository.get_task.return_value = task
        mock_repository.update_task.return_value = True

        # Complete task
        completion_notes = "Implemented User model with validation and relationships"
        result = await task_engine.complete_task(task.id, completion_notes)

        assert result.success
        assert result.task_id == task.id

        # Verify task was updated to completed
        update_call = mock_repository.update_task.call_args[0][0]
        assert update_call.status == TaskStatus.COMPLETED
        assert update_call.completed_at is not None

        # Verify context was stored in memory
        mock_memory_system.store_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_retry_mechanism(self, task_engine, mock_repository):
        """Test task retry mechanism on failure."""
        # Create task that will fail
        task = MicroTask(
            title="Flaky task execution",
            description="Task that might fail",
            task_type=TaskType.IMPLEMENTATION,
            estimated_minutes=5
        )

        mock_repository.get_task.return_value = task

        # Mock failure then success
        mock_repository.update_task.side_effect = [
            Exception("Database connection failed"),  # First attempt fails
            True  # Second attempt succeeds
        ]

        # Execute with retry
        result = await task_engine.start_task(task.id, retry_on_failure=True)

        assert result.success
        assert mock_repository.update_task.call_count == 2

    @pytest.mark.asyncio
    async def test_phase_execution_coordination(self, task_engine, mock_repository):
        """Test coordinated execution of phase tasks."""
        # Create phase with multiple tasks
        phase = Phase(
            name="Authentication Implementation Phase",
            description="Implement authentication features",
            objective="Complete auth system",
            order_index=1
        )

        tasks = [
            MicroTask(
                title="Setup auth framework",
                description="Initialize authentication",
                task_type=TaskType.IMPLEMENTATION,
                estimated_minutes=8,
                phase_id=phase.id
            ),
            MicroTask(
                title="Create user model",
                description="Define user structure",
                task_type=TaskType.IMPLEMENTATION,
                estimated_minutes=5,
                phase_id=phase.id,
                dependencies=["task-1"]  # Depends on first task
            )
        ]

        mock_repository.get_phase.return_value = phase
        mock_repository.list_tasks.return_value = tasks
        mock_repository.update_task.return_value = True

        # Execute phase
        result = await task_engine.execute_phase(phase.id)

        assert result.success
        assert result.phase_id == phase.id
        assert len(result.completed_tasks) >= 0

    @pytest.mark.asyncio
    async def test_dependency_resolution(self, task_engine, mock_repository):
        """Test task dependency resolution and execution order."""
        # Create tasks with dependencies
        task1 = MicroTask(
            title="Setup database schema",
            description="Create database tables",
            task_type=TaskType.IMPLEMENTATION,
            estimated_minutes=6
        )

        task2 = MicroTask(
            title="Create user service",
            description="Implement user business logic",
            task_type=TaskType.IMPLEMENTATION,
            estimated_minutes=8,
            dependencies=[task1.id]
        )

        task3 = MicroTask(
            title="Add user validation",
            description="Implement input validation",
            task_type=TaskType.IMPLEMENTATION,
            estimated_minutes=4,
            dependencies=[task2.id]
        )

        tasks = [task1, task2, task3]
        mock_repository.list_tasks.return_value = tasks

        # Get execution order
        execution_order = await task_engine.get_execution_order(tasks)

        # Task1 should be first (no dependencies)
        assert execution_order[0] == task1.id
        # Task2 should be second (depends on task1)
        assert execution_order[1] == task2.id
        # Task3 should be last (depends on task2)
        assert execution_order[2] == task3.id

    @pytest.mark.asyncio
    async def test_plan_generation_workflow(self, task_engine, mock_ai_planner, mock_repository):
        """Test complete plan generation workflow."""
        # Mock AI plan generation
        mock_plan_result = Mock()
        mock_plan_result.phases = [
            Mock(
                name="Analysis Phase",
                description="Requirements analysis",
                tasks=[
                    AITaskSuggestion(
                        title="Analyze requirements",
                        description="Gather and analyze requirements",
                        task_type=TaskType.ANALYSIS,
                        estimated_minutes=10
                    )
                ]
            ),
            Mock(
                name="Implementation Phase",
                description="Core implementation",
                tasks=[
                    AITaskSuggestion(
                        title="Implement core features",
                        description="Build main functionality",
                        task_type=TaskType.IMPLEMENTATION,
                        estimated_minutes=15
                    )
                ]
            )
        ]
        mock_ai_planner.generate_plan.return_value = mock_plan_result

        # Mock repository operations
        mock_repository.create_plan.return_value = "plan-123"
        mock_repository.create_phase.return_value = "phase-123"
        mock_repository.create_task.return_value = "task-123"

        # Generate plan
        request = PlanGenerationRequest(
            objective="Build user management system",
            requirements=["User registration", "Login functionality", "Profile management"],
            constraints=["10 hours total", "Must be secure"]
        )

        result = await task_engine.generate_plan(request)

        assert result.success
        assert result.plan_id == "plan-123"
        assert len(result.phases) == 2

        # Verify AI planner was called
        mock_ai_planner.generate_plan.assert_called_once()

        # Verify repository operations
        mock_repository.create_plan.assert_called_once()
        assert mock_repository.create_phase.call_count == 2
        assert mock_repository.create_task.call_count == 2

    @pytest.mark.asyncio
    async def test_concurrent_task_execution(self, task_engine, mock_repository):
        """Test concurrent execution of independent tasks."""
        # Create independent tasks (no dependencies)
        tasks = [
            MicroTask(
                title=f"Independent task {i+1}",
                description=f"Task {i+1} with no dependencies",
                task_type=TaskType.IMPLEMENTATION,
                estimated_minutes=5
            )
            for i in range(3)
        ]

        mock_repository.get_task.side_effect = tasks
        mock_repository.update_task.return_value = True

        # Execute tasks concurrently
        task_ids = [task.id for task in tasks]
        results = await task_engine.execute_tasks_concurrently(task_ids)

        assert len(results) == 3
        assert all(result.success for result in results)

        # All tasks should have been updated to IN_PROGRESS
        assert mock_repository.update_task.call_count == len(tasks)

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, task_engine, mock_repository, mock_memory_system):
        """Test error handling and recovery mechanisms."""
        # Create task that will encounter an error
        task = MicroTask(
            title="Error-prone task",
            description="Task that might fail",
            task_type=TaskType.IMPLEMENTATION,
            estimated_minutes=5
        )

        mock_repository.get_task.return_value = task

        # Simulate database error
        mock_repository.update_task.side_effect = Exception("Database connection lost")

        # Execute task with error handling
        result = await task_engine.start_task(task.id, handle_errors=True)

        assert not result.success
        assert "Database connection lost" in result.error_message

        # Error should be logged to memory
        mock_memory_system.store_context.assert_called()
        error_context = mock_memory_system.store_context.call_args[1]["content"]
        assert "error" in error_context.lower()

    @pytest.mark.asyncio
    async def test_task_blocking_detection(self, task_engine, mock_repository):
        """Test detection of blocking tasks in workflow."""
        # Create tasks with blocking relationships
        blocking_task = MicroTask(
            title="Critical infrastructure setup",
            description="Must complete before others",
            task_type=TaskType.IMPLEMENTATION,
            estimated_minutes=10,
            is_blocking=True,
            priority=TaskPriority.CRITICAL
        )

        dependent_tasks = [
            MicroTask(
                title="Feature implementation",
                description="Depends on infrastructure",
                task_type=TaskType.IMPLEMENTATION,
                estimated_minutes=6,
                dependencies=[blocking_task.id]
            )
        ]

        all_tasks = [blocking_task] + dependent_tasks
        mock_repository.list_tasks.return_value = all_tasks

        # Analyze blocking relationships
        blocking_analysis = await task_engine.analyze_blocking_tasks(all_tasks)

        assert len(blocking_analysis.blocking_tasks) == 1
        assert blocking_analysis.blocking_tasks[0] == blocking_task.id
        assert len(blocking_analysis.blocked_tasks) == 1

    @pytest.mark.asyncio
    async def test_workflow_state_management(self, task_engine, mock_repository):
        """Test workflow state tracking and management."""
        # Create workflow with multiple phases
        plan = InterventionPlan(
            title="Multi-phase development plan",
            description="Complete development workflow",
            objective="Deliver working application"
        )

        phases = [
            Phase(
                name="Setup Phase",
                description="Initial setup",
                objective="Prepare environment",
                order_index=1,
                plan_id=plan.id
            ),
            Phase(
                name="Development Phase",
                description="Core development",
                objective="Build features",
                order_index=2,
                plan_id=plan.id
            )
        ]

        mock_repository.get_plan.return_value = plan
        mock_repository.list_phases.return_value = phases

        # Track workflow state
        state = await task_engine.get_workflow_state(plan.id)

        assert state.plan_id == plan.id
        assert len(state.phases) == 2
        assert state.current_phase_index >= 0

    @pytest.mark.asyncio
    async def test_ai_planner_health_monitoring(self, task_engine, mock_ai_planner):
        """Test AI planner health monitoring and fallback."""
        # Test healthy AI planner
        mock_ai_planner.health_check.return_value = {"status": "healthy", "models_available": True}

        health_status = await task_engine.check_ai_planner_health()
        assert health_status["status"] == "healthy"

        # Test unhealthy AI planner
        mock_ai_planner.health_check.side_effect = Exception("AI service unavailable")

        health_status_down = await task_engine.check_ai_planner_health()
        assert health_status_down["status"] == "unhealthy"
        assert "error" in health_status_down

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_task_engine_performance(self, task_engine, mock_repository, mock_ai_planner):
        """Test task engine performance under load."""
        import time

        # Create multiple tasks for performance testing
        tasks = [
            MicroTask(
                title=f"Performance test task {i+1}",
                description=f"Task {i+1} for performance testing",
                task_type=TaskType.IMPLEMENTATION,
                estimated_minutes=5
            )
            for i in range(10)
        ]

        mock_repository.list_tasks.return_value = tasks
        mock_repository.update_task.return_value = True

        # Measure execution time
        start_time = time.time()

        task_ids = [task.id for task in tasks]
        results = await task_engine.execute_tasks_concurrently(task_ids)

        execution_time = time.time() - start_time

        # Should complete within reasonable time
        assert execution_time < 2.0  # Less than 2 seconds for 10 tasks
        assert len(results) == 10
        assert all(result.success for result in results)

    @pytest.mark.asyncio
    async def test_memory_integration_workflow(self, task_engine, mock_memory_system):
        """Test integration with memory system for context storage."""
        # Test context storage
        context_data = {
            "task_id": "test-task-123",
            "action": "task_completed",
            "outcome": "Successfully implemented user authentication",
            "lessons_learned": "JWT implementation went smoothly",
            "execution_time": 8
        }

        await task_engine.store_execution_context(context_data)

        # Verify context was stored
        mock_memory_system.store_context.assert_called_once()
        stored_content = mock_memory_system.store_context.call_args[1]["content"]
        assert "task_completed" in stored_content

        # Test context retrieval
        mock_memory_system.retrieve_context.return_value = """
        Previous similar tasks:
        - Authentication implementation took 8 minutes
        - JWT tokens worked well for session management
        - Rate limiting was important for security
        """

        retrieved_context = await task_engine.get_execution_context("authentication implementation")
        assert "JWT tokens" in retrieved_context
        mock_memory_system.retrieve_context.assert_called_once()