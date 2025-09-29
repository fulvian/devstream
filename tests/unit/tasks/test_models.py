"""
Comprehensive unit tests for DevStream Task Models

Tests cover:
- Model validation and constraints
- Business logic methods
- Dependency graph operations
- Edge cases and error conditions

Based on Context7 research best practices for robust testing.
"""

import pytest
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from typing import Set

from devstream.tasks.models import (
    MicroTask, Phase, InterventionPlan, TaskDependencyGraph,
    TaskStatus, TaskPriority, TaskType, TaskComplexity
)


class TestMicroTask:
    """Test MicroTask model and its business logic"""

    def test_basic_task_creation(self):
        """Test basic task creation with required fields"""
        task = MicroTask(
            title="Implement user authentication",
            description="Add JWT-based user authentication to the API",
            task_type=TaskType.IMPLEMENTATION
        )

        assert task.id is not None
        assert isinstance(task.id, UUID)
        assert task.title == "Implement user authentication"
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.MEDIUM
        assert task.complexity == TaskComplexity.SIMPLE
        assert task.estimated_minutes == 5
        assert task.validation_passed is False
        assert task.ai_generated is False

    def test_title_validation_actionable(self):
        """Test that title must start with action verb"""
        # Valid titles
        valid_titles = [
            "Implement user login",
            "Create new database table",
            "Fix authentication bug",
            "Test user registration flow"
        ]

        for title in valid_titles:
            task = MicroTask(
                title=title,
                description="Valid task description",
                task_type=TaskType.IMPLEMENTATION
            )
            assert task.title == title

        # Invalid titles
        invalid_titles = [
            "User authentication needs work",
            "Database table for users",
            "Bug in authentication system"
        ]

        for title in invalid_titles:
            with pytest.raises(ValueError, match="Title must start with action verb"):
                MicroTask(
                    title=title,
                    description="Valid task description",
                    task_type=TaskType.IMPLEMENTATION
                )

    def test_time_constraint_validation(self):
        """Test micro-task time constraint (max 10 minutes)"""
        # Valid times
        valid_times = [1, 5, 8, 10]
        for time in valid_times:
            task = MicroTask(
                title="Implement feature",
                description="Valid task description",
                task_type=TaskType.IMPLEMENTATION,
                estimated_minutes=time
            )
            assert task.estimated_minutes == time

        # Invalid time
        with pytest.raises(ValueError, match="MicroTask must be completable in 10 minutes or less"):
            MicroTask(
                title="Implement feature",
                description="Valid task description",
                task_type=TaskType.IMPLEMENTATION,
                estimated_minutes=15
            )

    def test_complexity_time_alignment(self):
        """Test that estimated time aligns with complexity"""
        complexity_tests = [
            (TaskComplexity.TRIVIAL, 2, True),   # Valid
            (TaskComplexity.TRIVIAL, 3, False),  # Too long for trivial
            (TaskComplexity.SIMPLE, 5, True),    # Valid
            (TaskComplexity.SIMPLE, 6, False),   # Too long for simple
            (TaskComplexity.MODERATE, 8, True),  # Valid
            (TaskComplexity.MODERATE, 9, False), # Too long for moderate
            (TaskComplexity.COMPLEX, 10, True),  # Valid
        ]

        for complexity, minutes, should_pass in complexity_tests:
            if should_pass:
                task = MicroTask(
                    title="Implement feature",
                    description="Valid task description",
                    task_type=TaskType.IMPLEMENTATION,
                    complexity=complexity,
                    estimated_minutes=minutes
                )
                assert task.complexity == complexity
                assert task.estimated_minutes == minutes
            else:
                with pytest.raises(ValueError, match="exceeds.*complexity limit"):
                    MicroTask(
                        title="Implement feature",
                        description="Valid task description",
                        task_type=TaskType.IMPLEMENTATION,
                        complexity=complexity,
                        estimated_minutes=minutes
                    )

    def test_status_transitions(self):
        """Test task status lifecycle transitions"""
        task = MicroTask(
            title="Implement feature",
            description="Valid task description",
            task_type=TaskType.IMPLEMENTATION
        )

        # Initial state
        assert task.status == TaskStatus.PENDING
        assert task.started_at is None
        assert task.completed_at is None

        # Mark in progress
        start_time = datetime.now()
        task.mark_in_progress()
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.started_at is not None
        assert task.started_at >= start_time
        assert task.updated_at is not None

        # Mark completed
        complete_time = datetime.now()
        task.mark_completed(actual_minutes=7)
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert task.completed_at >= complete_time
        assert task.actual_minutes == 7

    def test_dependency_management(self):
        """Test task dependency operations"""
        task = MicroTask(
            title="Implement feature",
            description="Valid task description",
            task_type=TaskType.IMPLEMENTATION
        )

        dep1_id = uuid4()
        dep2_id = uuid4()

        # Add dependencies
        task.add_dependency(dep1_id)
        task.add_dependency(dep2_id)
        assert dep1_id in task.depends_on
        assert dep2_id in task.depends_on
        assert len(task.depends_on) == 2

        # Remove dependency
        task.remove_dependency(dep1_id)
        assert dep1_id not in task.depends_on
        assert dep2_id in task.depends_on
        assert len(task.depends_on) == 1

        # Test readiness
        completed_tasks = {dep2_id}
        assert task.is_ready_to_start(completed_tasks)

        completed_tasks = set()
        assert not task.is_ready_to_start(completed_tasks)

    def test_execution_time_calculation(self):
        """Test execution time calculation"""
        task = MicroTask(
            title="Implement feature",
            description="Valid task description",
            task_type=TaskType.IMPLEMENTATION
        )

        # No execution time if not started/completed
        assert task.get_execution_time() is None

        # Set start and completion times
        start_time = datetime.now()
        task.started_at = start_time
        task.completed_at = start_time + timedelta(minutes=7)

        execution_time = task.get_execution_time()
        assert execution_time is not None
        assert execution_time.total_seconds() == 420  # 7 minutes

    def test_blocking_task(self):
        """Test task blocking functionality"""
        task = MicroTask(
            title="Implement feature",
            description="Valid task description",
            task_type=TaskType.IMPLEMENTATION
        )

        task.mark_blocked("Waiting for API specification")
        assert task.status == TaskStatus.BLOCKED
        assert "BLOCKED" in task.implementation_notes


class TestPhase:
    """Test Phase model and its business logic"""

    def test_basic_phase_creation(self):
        """Test basic phase creation"""
        phase = Phase(
            name="Authentication Implementation",
            description="Implement user authentication system",
            objective="Secure user access to the application",
            order_index=1
        )

        assert phase.id is not None
        assert isinstance(phase.id, UUID)
        assert phase.name == "Authentication Implementation"
        assert phase.status == TaskStatus.PENDING
        assert phase.order_index == 1
        assert len(phase.tasks) == 0

    def test_task_management(self):
        """Test adding and removing tasks from phase"""
        phase = Phase(
            name="Test Phase",
            description="Test phase description",
            objective="Test phase objective",
            order_index=1
        )

        task1_id = uuid4()
        task2_id = uuid4()

        # Add tasks
        phase.add_task(task1_id)
        phase.add_task(task2_id)
        assert len(phase.tasks) == 2
        assert task1_id in phase.tasks
        assert task2_id in phase.tasks

        # Remove task
        phase.remove_task(task1_id)
        assert len(phase.tasks) == 1
        assert task1_id not in phase.tasks
        assert task2_id in phase.tasks

        # Try to add duplicate task
        phase.add_task(task2_id)
        assert len(phase.tasks) == 1  # Should not add duplicate

    def test_progress_calculation(self):
        """Test phase progress calculation"""
        phase = Phase(
            name="Test Phase",
            description="Test phase description",
            objective="Test phase objective",
            order_index=1
        )

        task1_id = uuid4()
        task2_id = uuid4()
        task3_id = uuid4()

        phase.add_task(task1_id)
        phase.add_task(task2_id)
        phase.add_task(task3_id)

        # No completed tasks
        task_statuses = {
            task1_id: TaskStatus.PENDING,
            task2_id: TaskStatus.PENDING,
            task3_id: TaskStatus.PENDING
        }
        assert phase.calculate_progress(task_statuses) == 0.0

        # One completed task
        task_statuses[task1_id] = TaskStatus.COMPLETED
        assert phase.calculate_progress(task_statuses) == pytest.approx(33.33, rel=1e-2)

        # All completed tasks
        task_statuses[task2_id] = TaskStatus.COMPLETED
        task_statuses[task3_id] = TaskStatus.COMPLETED
        assert phase.calculate_progress(task_statuses) == 100.0

    def test_phase_dependencies(self):
        """Test phase dependency management"""
        phase = Phase(
            name="Test Phase",
            description="Test phase description",
            objective="Test phase objective",
            order_index=2
        )

        dep_phase_id = uuid4()
        phase.depends_on_phases.add(dep_phase_id)

        # Not ready when dependency not completed
        completed_phases = set()
        assert not phase.is_ready_to_start(completed_phases)

        # Ready when dependency completed
        completed_phases.add(dep_phase_id)
        assert phase.is_ready_to_start(completed_phases)


class TestInterventionPlan:
    """Test InterventionPlan model and its business logic"""

    def test_basic_plan_creation(self):
        """Test basic intervention plan creation"""
        plan = InterventionPlan(
            title="User Authentication System",
            description="Implement complete user authentication with JWT tokens",
            objective="Secure user access and session management"
        )

        assert plan.id is not None
        assert isinstance(plan.id, UUID)
        assert plan.title == "User Authentication System"
        assert plan.status == TaskStatus.PENDING
        assert plan.progress_percentage == 0.0
        assert len(plan.phases) == 0

    def test_phase_management(self):
        """Test adding and removing phases from plan"""
        plan = InterventionPlan(
            title="Test Plan",
            description="Test plan description",
            objective="Test plan objective"
        )

        phase1_id = uuid4()
        phase2_id = uuid4()

        # Add phases
        plan.add_phase(phase1_id)
        plan.add_phase(phase2_id)
        assert len(plan.phases) == 2
        assert phase1_id in plan.phases
        assert phase2_id in plan.phases

        # Remove phase
        plan.remove_phase(phase1_id)
        assert len(plan.phases) == 1
        assert phase1_id not in plan.phases
        assert phase2_id in plan.phases

    def test_progress_calculation(self):
        """Test overall plan progress calculation"""
        plan = InterventionPlan(
            title="Test Plan",
            description="Test plan description",
            objective="Test plan objective"
        )

        phase1_id = uuid4()
        phase2_id = uuid4()
        phase3_id = uuid4()

        plan.add_phase(phase1_id)
        plan.add_phase(phase2_id)
        plan.add_phase(phase3_id)

        # Test progress calculation
        phase_progresses = {
            phase1_id: 100.0,  # Completed
            phase2_id: 50.0,   # Half done
            phase3_id: 0.0     # Not started
        }

        overall_progress = plan.calculate_overall_progress(phase_progresses)
        expected_progress = (100.0 + 50.0 + 0.0) / 3
        assert overall_progress == pytest.approx(expected_progress, rel=1e-2)
        assert plan.progress_percentage == pytest.approx(expected_progress, rel=1e-2)

    def test_current_phase_detection(self):
        """Test detection of current active phase"""
        plan = InterventionPlan(
            title="Test Plan",
            description="Test plan description",
            objective="Test plan objective"
        )

        phase1_id = uuid4()
        phase2_id = uuid4()
        phase3_id = uuid4()

        plan.add_phase(phase1_id)
        plan.add_phase(phase2_id)
        plan.add_phase(phase3_id)

        # First phase is current (pending)
        phase_statuses = {
            phase1_id: TaskStatus.PENDING,
            phase2_id: TaskStatus.PENDING,
            phase3_id: TaskStatus.PENDING
        }
        assert plan.get_current_phase(phase_statuses) == phase1_id

        # Second phase is current (in progress)
        phase_statuses = {
            phase1_id: TaskStatus.COMPLETED,
            phase2_id: TaskStatus.IN_PROGRESS,
            phase3_id: TaskStatus.PENDING
        }
        assert plan.get_current_phase(phase_statuses) == phase2_id

        # All phases completed
        phase_statuses = {
            phase1_id: TaskStatus.COMPLETED,
            phase2_id: TaskStatus.COMPLETED,
            phase3_id: TaskStatus.COMPLETED
        }
        assert plan.get_current_phase(phase_statuses) is None

    def test_completion_date_estimation(self):
        """Test completion date estimation"""
        plan = InterventionPlan(
            title="Test Plan",
            description="Test plan description",
            objective="Test plan objective",
            estimated_hours=24.0
        )

        # Set progress
        plan.progress_percentage = 50.0  # Half completed

        # Estimate completion (12 hours remaining / 6 hours per day = 2 days)
        estimated_date = plan.estimate_completion_date(hours_per_day=6.0)
        expected_date = datetime.now() + timedelta(days=2)

        assert estimated_date is not None
        assert abs((estimated_date - expected_date).total_seconds()) < 60  # Within 1 minute

        # Already completed
        plan.progress_percentage = 100.0
        plan.completed_at = datetime.now()
        estimated_date = plan.estimate_completion_date()
        assert estimated_date == plan.completed_at


class TestTaskDependencyGraph:
    """Test TaskDependencyGraph operations"""

    def test_basic_graph_operations(self):
        """Test basic graph operations"""
        graph = TaskDependencyGraph()

        task1 = MicroTask(
            title="Implement feature A",
            description="Feature A implementation",
            task_type=TaskType.IMPLEMENTATION
        )

        task2 = MicroTask(
            title="Test feature A",
            description="Test feature A implementation",
            task_type=TaskType.TESTING
        )

        # Add tasks
        graph.add_task(task1)
        graph.add_task(task2)

        assert task1.id in graph.tasks
        assert task2.id in graph.tasks
        assert len(graph.tasks) == 2

    def test_dependency_management(self):
        """Test dependency edge management"""
        graph = TaskDependencyGraph()

        task1 = MicroTask(
            title="Implement feature A",
            description="Feature A implementation",
            task_type=TaskType.IMPLEMENTATION
        )

        task2 = MicroTask(
            title="Test feature A",
            description="Test feature A implementation",
            task_type=TaskType.TESTING
        )

        graph.add_task(task1)
        graph.add_task(task2)

        # Add dependency: task2 depends on task1
        success = graph.add_dependency(task1.id, task2.id)
        assert success is True
        assert task2.id in graph.adjacency_list[task1.id]
        assert task1.id in graph.reverse_adjacency[task2.id]

        # Remove dependency
        graph.remove_dependency(task1.id, task2.id)
        assert task2.id not in graph.adjacency_list.get(task1.id, set())
        assert task1.id not in graph.reverse_adjacency.get(task2.id, set())

    def test_cycle_detection(self):
        """Test cycle detection in dependency graph"""
        graph = TaskDependencyGraph()

        task1 = MicroTask(
            title="Implement feature A",
            description="Feature A implementation",
            task_type=TaskType.IMPLEMENTATION
        )

        task2 = MicroTask(
            title="Implement feature B",
            description="Feature B implementation",
            task_type=TaskType.IMPLEMENTATION
        )

        task3 = MicroTask(
            title="Implement feature C",
            description="Feature C implementation",
            task_type=TaskType.IMPLEMENTATION
        )

        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_task(task3)

        # Create chain: task1 -> task2 -> task3
        assert graph.add_dependency(task1.id, task2.id) is True
        assert graph.add_dependency(task2.id, task3.id) is True

        # Try to create cycle: task3 -> task1 (should fail)
        assert graph.add_dependency(task3.id, task1.id) is False

        # Self-dependency should fail
        assert graph.add_dependency(task1.id, task1.id) is False

    def test_ready_tasks_detection(self):
        """Test detection of tasks ready to execute"""
        graph = TaskDependencyGraph()

        task1 = MicroTask(
            title="Implement base feature",
            description="Base feature implementation",
            task_type=TaskType.IMPLEMENTATION,
            priority=TaskPriority.HIGH
        )

        task2 = MicroTask(
            title="Implement dependent feature",
            description="Feature that depends on base",
            task_type=TaskType.IMPLEMENTATION,
            priority=TaskPriority.MEDIUM
        )

        task3 = MicroTask(
            title="Implement independent feature",
            description="Independent feature",
            task_type=TaskType.IMPLEMENTATION,
            priority=TaskPriority.CRITICAL
        )

        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_task(task3)

        # Add dependency: task2 depends on task1
        graph.add_dependency(task1.id, task2.id)

        # No tasks completed yet
        completed_tasks = set()
        ready_tasks = graph.get_ready_tasks(completed_tasks)

        # Should return task1 and task3 (no dependencies)
        ready_task_ids = {task.id for task in ready_tasks}
        assert task1.id in ready_task_ids
        assert task3.id in ready_task_ids
        assert task2.id not in ready_task_ids

        # Should be sorted by priority (CRITICAL first)
        assert ready_tasks[0].priority == TaskPriority.CRITICAL

        # Complete task1
        completed_tasks.add(task1.id)
        ready_tasks = graph.get_ready_tasks(completed_tasks)

        # Now task2 should also be ready
        ready_task_ids = {task.id for task in ready_tasks}
        assert task2.id in ready_task_ids

    def test_topological_sort(self):
        """Test topological sorting of tasks"""
        graph = TaskDependencyGraph()

        tasks = []
        for i in range(4):
            task = MicroTask(
                title=f"Implement feature {i}",
                description=f"Feature {i} implementation",
                task_type=TaskType.IMPLEMENTATION
            )
            tasks.append(task)
            graph.add_task(task)

        # Create dependencies: 0 -> 1 -> 3, 0 -> 2 -> 3
        graph.add_dependency(tasks[0].id, tasks[1].id)
        graph.add_dependency(tasks[1].id, tasks[3].id)
        graph.add_dependency(tasks[0].id, tasks[2].id)
        graph.add_dependency(tasks[2].id, tasks[3].id)

        sorted_tasks = graph.topological_sort()

        # Find positions in sorted order
        positions = {task_id: i for i, task_id in enumerate(sorted_tasks)}

        # Verify ordering constraints
        assert positions[tasks[0].id] < positions[tasks[1].id]
        assert positions[tasks[0].id] < positions[tasks[2].id]
        assert positions[tasks[1].id] < positions[tasks[3].id]
        assert positions[tasks[2].id] < positions[tasks[3].id]

    def test_critical_path_calculation(self):
        """Test critical path calculation"""
        graph = TaskDependencyGraph()

        tasks = []
        for i in range(4):
            task = MicroTask(
                title=f"Implement feature {i}",
                description=f"Feature {i} implementation",
                task_type=TaskType.IMPLEMENTATION
            )
            tasks.append(task)
            graph.add_task(task)

        # Create dependencies with different path lengths
        # Path 1: 0 -> 1 -> 3 (length 2)
        # Path 2: 0 -> 2 (length 1)
        graph.add_dependency(tasks[0].id, tasks[1].id)
        graph.add_dependency(tasks[1].id, tasks[3].id)
        graph.add_dependency(tasks[0].id, tasks[2].id)

        critical_path = graph.get_critical_path()

        # Tasks should be ordered by depth (longest dependency chain first)
        assert len(critical_path) == 4

        # Task 3 should have highest depth (depends on 0 -> 1)
        # Task 1 should have depth 1 (depends on 0)
        # Task 2 should have depth 1 (depends on 0)
        # Task 0 should have depth 0 (no dependencies)


class TestModelIntegration:
    """Test integration between different models"""

    def test_full_workflow_creation(self):
        """Test creating a complete workflow with plan, phases, and tasks"""
        # Create intervention plan
        plan = InterventionPlan(
            title="User Authentication System",
            description="Complete user authentication implementation",
            objective="Secure user access and session management",
            estimated_hours=16.0
        )

        # Create phases
        phase1 = Phase(
            name="Backend Implementation",
            description="Implement authentication backend",
            objective="Create secure authentication API",
            order_index=1,
            estimated_hours=8.0
        )

        phase2 = Phase(
            name="Frontend Integration",
            description="Integrate authentication with frontend",
            objective="Create user-friendly authentication UI",
            order_index=2,
            estimated_hours=6.0
        )

        phase3 = Phase(
            name="Testing and Documentation",
            description="Test and document authentication system",
            objective="Ensure system reliability and usability",
            order_index=3,
            estimated_hours=2.0
        )

        # Add phases to plan
        plan.add_phase(phase1.id)
        plan.add_phase(phase2.id)
        plan.add_phase(phase3.id)

        # Create tasks for phase 1
        task1 = MicroTask(
            title="Create user model",
            description="Create database model for user authentication",
            task_type=TaskType.IMPLEMENTATION,
            complexity=TaskComplexity.MODERATE,
            estimated_minutes=8
        )

        task2 = MicroTask(
            title="Implement JWT service",
            description="Create JWT token generation and validation service",
            task_type=TaskType.IMPLEMENTATION,
            complexity=TaskComplexity.COMPLEX,
            estimated_minutes=10
        )

        task3 = MicroTask(
            title="Create login endpoint",
            description="Implement login API endpoint with JWT response",
            task_type=TaskType.IMPLEMENTATION,
            complexity=TaskComplexity.MODERATE,
            estimated_minutes=7
        )

        # Add tasks to phase
        phase1.add_task(task1.id)
        phase1.add_task(task2.id)
        phase1.add_task(task3.id)

        # Create dependency graph
        graph = TaskDependencyGraph()
        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_task(task3)

        # Add dependencies: task3 depends on task1 and task2
        graph.add_dependency(task1.id, task3.id)
        graph.add_dependency(task2.id, task3.id)

        # Verify the complete workflow
        assert len(plan.phases) == 3
        assert len(phase1.tasks) == 3
        assert task1.id in graph.tasks
        assert task2.id in graph.tasks
        assert task3.id in graph.tasks

        # Verify dependencies
        completed_tasks = set()
        ready_tasks = graph.get_ready_tasks(completed_tasks)
        ready_task_ids = {task.id for task in ready_tasks}

        # Only task1 and task2 should be ready initially
        assert task1.id in ready_task_ids
        assert task2.id in ready_task_ids
        assert task3.id not in ready_task_ids

        # Complete task1 and task2
        completed_tasks.add(task1.id)
        completed_tasks.add(task2.id)
        ready_tasks = graph.get_ready_tasks(completed_tasks)
        ready_task_ids = {task.id for task in ready_tasks}

        # Now task3 should be ready
        assert task3.id in ready_task_ids

    def test_json_serialization(self):
        """Test JSON serialization/deserialization of all models"""
        # Create a task
        task = MicroTask(
            title="Implement feature",
            description="Feature implementation",
            task_type=TaskType.IMPLEMENTATION,
            keywords=["auth", "jwt", "security"]
        )

        # Serialize to JSON
        task_json = task.model_dump_json()
        assert isinstance(task_json, str)

        # Deserialize from JSON
        task_dict = task.model_dump()
        loaded_task = MicroTask.model_validate(task_dict)

        assert loaded_task.id == task.id
        assert loaded_task.title == task.title
        assert loaded_task.keywords == task.keywords

        # Test Phase serialization
        phase = Phase(
            name="Test Phase",
            description="Test phase",
            objective="Test objective",
            order_index=1
        )
        phase.add_task(task.id)

        phase_json = phase.model_dump_json()
        phase_dict = phase.model_dump()
        loaded_phase = Phase.model_validate(phase_dict)

        assert loaded_phase.id == phase.id
        assert loaded_phase.name == phase.name
        assert task.id in loaded_phase.tasks

        # Test InterventionPlan serialization
        plan = InterventionPlan(
            title="Test Plan",
            description="Test plan",
            objective="Test objective"
        )
        plan.add_phase(phase.id)

        plan_json = plan.model_dump_json()
        plan_dict = plan.model_dump()
        loaded_plan = InterventionPlan.model_validate(plan_dict)

        assert loaded_plan.id == plan.id
        assert loaded_plan.title == plan.title
        assert phase.id in loaded_plan.phases