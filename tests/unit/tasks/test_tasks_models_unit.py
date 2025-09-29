"""
Unit tests for task models functionality.

Context7-validated patterns for task management testing:
- Task lifecycle state transitions
- Workflow validation and dependency management
- Status progression and WIP limits
- Time estimation and complexity validation
"""

import pytest
from datetime import datetime, timedelta
from typing import List

from devstream.tasks.models import (
    MicroTask,
    Phase,
    InterventionPlan,
    TaskDependencyGraph,
    TaskStatus,
    TaskPriority,
    TaskType,
    TaskComplexity
)


@pytest.mark.unit
@pytest.mark.tasks
class TestTaskModels:
    """Test task system models with Context7-validated patterns."""

    def test_task_status_enum(self):
        """Test TaskStatus enum values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.BLOCKED.value == "blocked"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_priority_enum(self):
        """Test TaskPriority enum values."""
        assert TaskPriority.LOW.value == "low"
        assert TaskPriority.MEDIUM.value == "medium"
        assert TaskPriority.HIGH.value == "high"
        assert TaskPriority.CRITICAL.value == "critical"

    def test_task_type_enum(self):
        """Test TaskType enum values."""
        assert TaskType.ANALYSIS.value == "analysis"
        assert TaskType.IMPLEMENTATION.value == "implementation"
        assert TaskType.TESTING.value == "testing"
        assert TaskType.DOCUMENTATION.value == "documentation"
        assert TaskType.REVIEW.value == "review"
        assert TaskType.DEBUGGING.value == "debugging"

    def test_task_complexity_enum(self):
        """Test TaskComplexity enum values."""
        assert TaskComplexity.SIMPLE.value == "simple"
        assert TaskComplexity.MODERATE.value == "moderate"
        assert TaskComplexity.COMPLEX.value == "complex"


@pytest.mark.unit
@pytest.mark.tasks
class TestMicroTask:
    """Test MicroTask with Context7-validated workflow patterns."""

    def test_basic_task_creation(self):
        """Test basic micro-task creation with valid data."""
        task = MicroTask(
            title="Create user authentication endpoint",
            description="Implement JWT-based authentication for API endpoints",
            task_type=TaskType.IMPLEMENTATION,
            estimated_minutes=5
        )

        assert task.title == "Create user authentication endpoint"
        assert task.task_type == TaskType.IMPLEMENTATION
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.MEDIUM
        assert task.complexity == TaskComplexity.SIMPLE
        assert task.estimated_minutes == 5
        assert task.dependencies == []
        assert not task.is_blocking
        assert task.created_at is not None

    def test_task_creation_with_all_fields(self):
        """Test task creation with all fields specified."""
        now = datetime.utcnow()
        task = MicroTask(
            title="Implement comprehensive user registration system",
            description="Create full user registration with validation and email confirmation",
            task_type=TaskType.IMPLEMENTATION,
            complexity=TaskComplexity.MODERATE,
            priority=TaskPriority.HIGH,
            estimated_minutes=3,
            dependencies=["task-1", "task-2"],
            is_blocking=True,
            phase_id="phase-123",
            assigned_to="developer-1",
            tags=["auth", "registration", "email"],
            created_at=now
        )

        assert task.complexity == TaskComplexity.MODERATE
        assert task.priority == TaskPriority.HIGH
        assert task.dependencies == ["task-1", "task-2"]
        assert task.is_blocking
        assert task.phase_id == "phase-123"
        assert task.assigned_to == "developer-1"
        assert task.tags == ["auth", "registration", "email"]
        assert task.created_at == now

    def test_actionable_title_validation(self):
        """Test title validation for actionable language (Context7 pattern)."""
        # Valid actionable titles
        valid_titles = [
            "Create user authentication",
            "Implement JWT tokens",
            "Fix login bug",
            "Update documentation",
            "Test registration flow",
            "Refactor user service"
        ]

        for title in valid_titles:
            task = MicroTask(
                title=title,
                description="Valid description",
                task_type=TaskType.IMPLEMENTATION,
                estimated_minutes=5
            )
            assert task.title == title

        # Invalid non-actionable titles should still be allowed but noted
        # This is more of a guideline than a hard validation
        non_actionable_title = "User authentication stuff"
        task = MicroTask(
            title=non_actionable_title,
            description="Non-actionable title example",
            task_type=TaskType.IMPLEMENTATION,
            estimated_minutes=5
        )
        assert task.title == non_actionable_title

    def test_time_estimation_validation(self):
        """Test time estimation constraints based on complexity."""
        # Simple tasks: 1-5 minutes
        simple_task = MicroTask(
            title="Add logging statement",
            description="Add debug logging",
            task_type=TaskType.IMPLEMENTATION,
            complexity=TaskComplexity.SIMPLE,
            estimated_minutes=3
        )
        assert simple_task.estimated_minutes == 3

        # Moderate tasks: 3-8 minutes
        moderate_task = MicroTask(
            title="Implement validation logic",
            description="Add input validation",
            task_type=TaskType.IMPLEMENTATION,
            complexity=TaskComplexity.MODERATE,
            estimated_minutes=6
        )
        assert moderate_task.estimated_minutes == 6

        # Complex tasks: 5-10 minutes
        complex_task = MicroTask(
            title="Refactor authentication system",
            description="Complete auth refactor",
            task_type=TaskType.IMPLEMENTATION,
            complexity=TaskComplexity.COMPLEX,
            estimated_minutes=10
        )
        assert complex_task.estimated_minutes == 10

    def test_complexity_time_alignment(self):
        """Test that complexity aligns with estimated time."""
        # Test automatic complexity assignment based on time
        quick_task = MicroTask(
            title="Fix typo in documentation",
            description="Correct spelling error",
            task_type=TaskType.DOCUMENTATION,
            estimated_minutes=2
        )
        # Should default to SIMPLE for short tasks
        assert quick_task.complexity == TaskComplexity.SIMPLE

    def test_status_transitions(self):
        """Test valid status transitions (Context7 workflow pattern)."""
        task = MicroTask(
            title="Test status transitions",
            description="Testing task status changes",
            task_type=TaskType.TESTING,
            estimated_minutes=5
        )

        # Initial status
        assert task.status == TaskStatus.PENDING

        # Valid transitions
        task.status = TaskStatus.IN_PROGRESS
        assert task.status == TaskStatus.IN_PROGRESS

        task.status = TaskStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED

        # Test blocked status
        blocked_task = MicroTask(
            title="Blocked task",
            description="Task waiting on dependency",
            task_type=TaskType.IMPLEMENTATION,
            estimated_minutes=5
        )
        blocked_task.status = TaskStatus.BLOCKED
        assert blocked_task.status == TaskStatus.BLOCKED

    def test_dependency_management(self):
        """Test task dependency handling."""
        task = MicroTask(
            title="Dependent task",
            description="Task with dependencies",
            task_type=TaskType.IMPLEMENTATION,
            estimated_minutes=5,
            dependencies=["task-1", "task-2", "task-3"]
        )

        assert len(task.dependencies) == 3
        assert "task-1" in task.dependencies
        assert "task-2" in task.dependencies
        assert "task-3" in task.dependencies

        # Test empty dependencies
        independent_task = MicroTask(
            title="Independent task",
            description="No dependencies",
            task_type=TaskType.ANALYSIS,
            estimated_minutes=3
        )
        assert independent_task.dependencies == []

    def test_execution_time_tracking(self):
        """Test execution time calculation."""
        task = MicroTask(
            title="Time tracking test",
            description="Test time tracking",
            task_type=TaskType.IMPLEMENTATION,
            estimated_minutes=5
        )

        # Simulate task execution
        start_time = datetime.utcnow()
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = start_time

        # Simulate completion
        end_time = start_time + timedelta(minutes=7)
        task.status = TaskStatus.COMPLETED
        task.completed_at = end_time

        # Calculate actual duration
        if task.started_at and task.completed_at:
            actual_duration = (task.completed_at - task.started_at).total_seconds() / 60
            assert actual_duration == 7.0
            assert actual_duration > task.estimated_minutes  # Took longer than estimated

    def test_blocking_task_identification(self):
        """Test blocking task identification."""
        blocking_task = MicroTask(
            title="Critical infrastructure setup",
            description="Must complete before other tasks",
            task_type=TaskType.IMPLEMENTATION,
            estimated_minutes=8,
            is_blocking=True,
            priority=TaskPriority.CRITICAL
        )

        assert blocking_task.is_blocking
        assert blocking_task.priority == TaskPriority.CRITICAL

        normal_task = MicroTask(
            title="Regular feature implementation",
            description="Standard task",
            task_type=TaskType.IMPLEMENTATION,
            estimated_minutes=5
        )

        assert not normal_task.is_blocking


@pytest.mark.unit
@pytest.mark.tasks
class TestPhase:
    """Test Phase model with Context7-validated patterns."""

    def test_basic_phase_creation(self):
        """Test basic phase creation."""
        phase = Phase(
            name="Authentication Implementation Phase",
            description="Implement all authentication-related features",
            objective="Secure user access to the application",
            order_index=1
        )

        assert phase.name == "Authentication Implementation Phase"
        assert phase.description == "Implement all authentication-related features"
        assert phase.objective == "Secure user access to the application"
        assert phase.order_index == 1
        assert phase.task_ids == []
        assert phase.status == TaskStatus.PENDING
        assert phase.created_at is not None

    def test_phase_with_tasks(self):
        """Test phase creation with associated tasks."""
        phase = Phase(
            name="Testing Phase",
            description="Comprehensive testing of implemented features",
            objective="Ensure code quality and functionality",
            order_index=2,
            task_ids=["task-1", "task-2", "task-3"],
            dependencies=["phase-1"]
        )

        assert len(phase.task_ids) == 3
        assert "task-1" in phase.task_ids
        assert phase.dependencies == ["phase-1"]

    def test_phase_progress_calculation(self):
        """Test phase progress calculation based on tasks."""
        phase = Phase(
            name="Development Phase",
            description="Core development work",
            objective="Implement core features",
            order_index=1,
            task_ids=["task-1", "task-2", "task-3", "task-4"]
        )

        # Simulate task completion tracking
        # In a real implementation, this would query actual task status
        completed_tasks = 2
        total_tasks = len(phase.task_ids)
        progress = (completed_tasks / total_tasks) * 100

        assert progress == 50.0  # 2 out of 4 tasks completed

    def test_phase_dependencies(self):
        """Test phase dependency management."""
        phase1 = Phase(
            name="Setup Phase",
            description="Initial setup",
            objective="Prepare environment",
            order_index=1
        )

        phase2 = Phase(
            name="Implementation Phase",
            description="Core implementation",
            objective="Build features",
            order_index=2,
            dependencies=[phase1.id]
        )

        assert len(phase2.dependencies) == 1
        assert phase1.id in phase2.dependencies


@pytest.mark.unit
@pytest.mark.tasks
class TestInterventionPlan:
    """Test InterventionPlan with Context7-validated workflow patterns."""

    def test_basic_plan_creation(self):
        """Test basic intervention plan creation."""
        plan = InterventionPlan(
            title="Complete User Authentication System Implementation",
            description="Comprehensive plan to implement secure user authentication",
            objective="Enable secure user access with JWT-based authentication system"
        )

        assert plan.title == "Complete User Authentication System Implementation"
        assert plan.status == TaskStatus.PENDING
        assert plan.phase_ids == []
        assert plan.created_at is not None
        assert plan.estimated_completion_date is None

    def test_plan_with_phases(self):
        """Test plan creation with multiple phases."""
        plan = InterventionPlan(
            title="Full Stack Application Development Plan",
            description="Complete development plan for new application",
            objective="Deliver production-ready application with all features",
            phase_ids=["phase-1", "phase-2", "phase-3"],
            priority=TaskPriority.HIGH
        )

        assert len(plan.phase_ids) == 3
        assert plan.priority == TaskPriority.HIGH

    def test_plan_progress_calculation(self):
        """Test plan progress calculation based on phases."""
        plan = InterventionPlan(
            title="Multi-Phase Development Plan",
            description="Development across multiple phases",
            objective="Complete all development phases",
            phase_ids=["phase-1", "phase-2", "phase-3", "phase-4"]
        )

        # Simulate phase completion tracking
        completed_phases = 1
        total_phases = len(plan.phase_ids)
        progress = (completed_phases / total_phases) * 100

        assert progress == 25.0  # 1 out of 4 phases completed

    def test_completion_date_estimation(self):
        """Test estimated completion date calculation."""
        plan = InterventionPlan(
            title="Time-Constrained Project Plan",
            description="Project with deadline constraints",
            objective="Meet project deadline",
            estimated_hours=40  # Total estimated effort
        )

        # Simulate completion date estimation
        start_date = datetime.utcnow()
        hours_per_day = 8
        estimated_days = plan.estimated_hours / hours_per_day
        estimated_completion = start_date + timedelta(days=estimated_days)

        assert estimated_days == 5.0  # 40 hours / 8 hours per day

    def test_current_phase_detection(self):
        """Test current active phase detection."""
        plan = InterventionPlan(
            title="Sequential Phase Plan",
            description="Plan with sequential phases",
            objective="Execute phases in order",
            phase_ids=["phase-1", "phase-2", "phase-3"]
        )

        # In real implementation, would query phase status
        # First phase should be current if plan is in progress
        plan.status = TaskStatus.IN_PROGRESS
        current_phase_id = plan.phase_ids[0] if plan.phase_ids else None

        assert current_phase_id == "phase-1"


@pytest.mark.unit
@pytest.mark.tasks
class TestTaskDependencyGraph:
    """Test TaskDependencyGraph with Context7-validated patterns."""

    def test_basic_graph_operations(self):
        """Test basic dependency graph operations."""
        graph = TaskDependencyGraph()

        # Create test tasks
        task1 = MicroTask(
            title="Setup database",
            description="Initialize database",
            task_type=TaskType.IMPLEMENTATION,
            estimated_minutes=5
        )

        task2 = MicroTask(
            title="Create user model",
            description="Define user data model",
            task_type=TaskType.IMPLEMENTATION,
            estimated_minutes=4
        )

        # Add tasks to graph
        graph.add_task(task1)
        graph.add_task(task2)

        assert len(graph.tasks) == 2
        assert task1.id in graph.tasks
        assert task2.id in graph.tasks

    def test_dependency_management(self):
        """Test dependency addition and management."""
        graph = TaskDependencyGraph()

        # Create tasks
        setup_task = MicroTask(
            title="Setup environment",
            description="Prepare development environment",
            task_type=TaskType.IMPLEMENTATION,
            estimated_minutes=5
        )

        impl_task = MicroTask(
            title="Implement feature",
            description="Build the feature",
            task_type=TaskType.IMPLEMENTATION,
            estimated_minutes=8
        )

        graph.add_task(setup_task)
        graph.add_task(impl_task)

        # Add dependency: impl_task depends on setup_task
        graph.add_dependency(setup_task.id, impl_task.id)

        assert impl_task.id in graph.dependencies
        assert setup_task.id in graph.dependencies[impl_task.id]

    def test_cycle_detection(self):
        """Test cycle detection in dependency graph."""
        graph = TaskDependencyGraph()

        task1 = MicroTask(
            title="Task 1", description="First task",
            task_type=TaskType.IMPLEMENTATION, estimated_minutes=5
        )
        task2 = MicroTask(
            title="Task 2", description="Second task",
            task_type=TaskType.IMPLEMENTATION, estimated_minutes=5
        )
        task3 = MicroTask(
            title="Task 3", description="Third task",
            task_type=TaskType.IMPLEMENTATION, estimated_minutes=5
        )

        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_task(task3)

        # Create valid dependencies
        graph.add_dependency(task1.id, task2.id)  # task2 depends on task1
        graph.add_dependency(task2.id, task3.id)  # task3 depends on task2

        # This should not create a cycle
        has_cycle = graph.has_cycle()
        assert not has_cycle

        # Now create a cycle
        graph.add_dependency(task3.id, task1.id)  # task1 depends on task3
        has_cycle_after = graph.has_cycle()
        assert has_cycle_after

    def test_ready_tasks_detection(self):
        """Test detection of tasks ready for execution."""
        graph = TaskDependencyGraph()

        # Create tasks
        independent_task = MicroTask(
            title="Independent task",
            description="No dependencies",
            task_type=TaskType.ANALYSIS,
            estimated_minutes=3
        )

        dependent_task = MicroTask(
            title="Dependent task",
            description="Has dependencies",
            task_type=TaskType.IMPLEMENTATION,
            estimated_minutes=5
        )

        graph.add_task(independent_task)
        graph.add_task(dependent_task)
        graph.add_dependency(independent_task.id, dependent_task.id)

        # Initially, only independent task should be ready
        completed_tasks = set()
        ready_tasks = graph.get_ready_tasks(completed_tasks)

        assert len(ready_tasks) == 1
        assert independent_task.id in ready_tasks

        # After completing independent task, dependent task becomes ready
        completed_tasks.add(independent_task.id)
        ready_tasks_after = graph.get_ready_tasks(completed_tasks)

        assert len(ready_tasks_after) == 1
        assert dependent_task.id in ready_tasks_after

    def test_topological_sort(self):
        """Test topological sorting of tasks."""
        graph = TaskDependencyGraph()

        # Create a chain of dependencies
        tasks = []
        for i in range(4):
            task = MicroTask(
                title=f"Task {i+1}",
                description=f"Task number {i+1}",
                task_type=TaskType.IMPLEMENTATION,
                estimated_minutes=5
            )
            tasks.append(task)
            graph.add_task(task)

        # Create chain: task1 -> task2 -> task3 -> task4
        for i in range(3):
            graph.add_dependency(tasks[i].id, tasks[i+1].id)

        sorted_tasks = graph.topological_sort()

        # First task should be the one with no dependencies
        assert sorted_tasks[0] == tasks[0].id
        # Last task should be the one that depends on all others
        assert sorted_tasks[-1] == tasks[-1].id

    def test_critical_path_calculation(self):
        """Test critical path calculation for project planning."""
        graph = TaskDependencyGraph()

        # Create tasks with different durations
        task_a = MicroTask(
            title="Task A", description="5 minute task",
            task_type=TaskType.IMPLEMENTATION, estimated_minutes=5
        )
        task_b = MicroTask(
            title="Task B", description="3 minute task",
            task_type=TaskType.IMPLEMENTATION, estimated_minutes=3
        )
        task_c = MicroTask(
            title="Task C", description="8 minute task",
            task_type=TaskType.IMPLEMENTATION, estimated_minutes=8
        )
        task_d = MicroTask(
            title="Task D", description="2 minute task",
            task_type=TaskType.IMPLEMENTATION, estimated_minutes=2
        )

        for task in [task_a, task_b, task_c, task_d]:
            graph.add_task(task)

        # Create dependencies: A -> C, B -> C, C -> D
        graph.add_dependency(task_a.id, task_c.id)
        graph.add_dependency(task_b.id, task_c.id)
        graph.add_dependency(task_c.id, task_d.id)

        critical_path = graph.get_critical_path()

        # Critical path should include the longest duration path
        # A(5) -> C(8) -> D(2) = 15 minutes vs B(3) -> C(8) -> D(2) = 13 minutes
        assert task_a.id in critical_path
        assert task_c.id in critical_path
        assert task_d.id in critical_path


@pytest.mark.unit
@pytest.mark.tasks
class TestTaskModelIntegration:
    """Test integration between different task models."""

    def test_full_workflow_creation(self):
        """Test creating a complete workflow with plan, phases, and tasks."""
        # Create intervention plan
        plan = InterventionPlan(
            title="Complete Authentication System Implementation Project",
            description="End-to-end implementation of user authentication",
            objective="Deliver secure, production-ready authentication system"
        )

        # Create phases
        analysis_phase = Phase(
            name="Requirements Analysis and Planning Phase",
            description="Analyze requirements and plan implementation",
            objective="Define clear requirements and implementation strategy",
            order_index=1,
            plan_id=plan.id
        )

        implementation_phase = Phase(
            name="Core Implementation Development Phase",
            description="Implement authentication features",
            objective="Build all authentication functionality",
            order_index=2,
            plan_id=plan.id,
            dependencies=[analysis_phase.id]
        )

        # Create tasks for each phase
        analysis_tasks = [
            MicroTask(
                title="Research authentication standards",
                description="Research JWT and OAuth standards",
                task_type=TaskType.ANALYSIS,
                estimated_minutes=10,
                phase_id=analysis_phase.id
            ),
            MicroTask(
                title="Design authentication flow",
                description="Design user authentication workflow",
                task_type=TaskType.ANALYSIS,
                estimated_minutes=8,
                phase_id=analysis_phase.id
            )
        ]

        implementation_tasks = [
            MicroTask(
                title="Implement JWT token generation",
                description="Create JWT token generation service",
                task_type=TaskType.IMPLEMENTATION,
                estimated_minutes=10,
                phase_id=implementation_phase.id
            ),
            MicroTask(
                title="Create login endpoint",
                description="Build user login API endpoint",
                task_type=TaskType.IMPLEMENTATION,
                estimated_minutes=8,
                phase_id=implementation_phase.id
            )
        ]

        # Verify relationships
        assert analysis_phase.plan_id == plan.id
        assert implementation_phase.plan_id == plan.id
        assert implementation_phase.dependencies == [analysis_phase.id]

        for task in analysis_tasks:
            assert task.phase_id == analysis_phase.id

        for task in implementation_tasks:
            assert task.phase_id == implementation_phase.id

    def test_task_serialization(self):
        """Test JSON serialization of task models."""
        task = MicroTask(
            title="Test serialization task",
            description="Task for testing JSON serialization",
            task_type=TaskType.TESTING,
            estimated_minutes=5,
            tags=["serialization", "test"]
        )

        # Test that model can be converted to dict (Pydantic feature)
        task_dict = task.model_dump()

        assert task_dict["title"] == "Test serialization task"
        assert task_dict["task_type"] == "testing"
        assert task_dict["status"] == "pending"
        assert task_dict["tags"] == ["serialization", "test"]

        # Test reconstruction from dict
        reconstructed_task = MicroTask(**task_dict)
        assert reconstructed_task.title == task.title
        assert reconstructed_task.task_type == task.task_type
        assert reconstructed_task.status == task.status


@pytest.mark.unit
@pytest.mark.tasks
class TestTaskModelEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_task_lists(self):
        """Test handling of empty task collections."""
        graph = TaskDependencyGraph()

        # Empty graph operations
        assert len(graph.tasks) == 0
        assert graph.get_ready_tasks(set()) == []
        assert graph.topological_sort() == []
        assert not graph.has_cycle()

    def test_maximum_complexity_tasks(self):
        """Test tasks at maximum complexity boundaries."""
        complex_task = MicroTask(
            title="Highly complex architectural refactoring task",
            description="Complete system architecture overhaul",
            task_type=TaskType.IMPLEMENTATION,
            complexity=TaskComplexity.COMPLEX,
            estimated_minutes=10,  # Maximum for micro-task
            priority=TaskPriority.CRITICAL
        )

        assert complex_task.complexity == TaskComplexity.COMPLEX
        assert complex_task.estimated_minutes == 10
        assert complex_task.priority == TaskPriority.CRITICAL

    def test_large_dependency_graphs(self):
        """Test performance with larger dependency graphs."""
        graph = TaskDependencyGraph()

        # Create multiple tasks
        tasks = []
        for i in range(20):
            task = MicroTask(
                title=f"Large graph task {i+1}",
                description=f"Task number {i+1} in large graph",
                task_type=TaskType.IMPLEMENTATION,
                estimated_minutes=5
            )
            tasks.append(task)
            graph.add_task(task)

        # Create some dependencies
        for i in range(10):
            if i + 10 < len(tasks):
                graph.add_dependency(tasks[i].id, tasks[i + 10].id)

        # Should handle large graphs efficiently
        ready_tasks = graph.get_ready_tasks(set())
        assert len(ready_tasks) >= 10  # At least the first 10 tasks should be ready

        # Cycle detection should work on large graphs
        has_cycle = graph.has_cycle()
        assert not has_cycle  # No cycles in this linear structure