"""
Integration tests for task service layer.

Tests service workflows, AI integration, template management,
and complex business logic with Context7-validated patterns.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4
from typing import List, Dict, Optional, Any

from devstream.tasks.service import (
    TaskService,
    TaskServiceError,
    WorkflowError,
    PlanningError,
    TaskWorkflowTemplate
)
from devstream.tasks.engine import TaskEngine, TaskEngineConfig
from devstream.tasks.repository import TaskRepository
from devstream.tasks.models import (
    InterventionPlan, Phase, MicroTask, TaskDependencyGraph,
    TaskStatus, TaskPriority, TaskType, TaskComplexity
)
from devstream.memory.storage import MemoryStorage


@pytest.mark.unit
@pytest.mark.tasks
class TestTaskServiceCore:
    """Test core task service functionality."""

    @pytest.fixture
    def mock_engine(self):
        """Create mock task engine."""
        engine = AsyncMock(spec=TaskEngine)
        engine.repository = AsyncMock(spec=TaskRepository)
        engine.memory_storage = AsyncMock(spec=MemoryStorage)
        return engine

    @pytest.fixture
    def mock_ai_planner(self):
        """Create mock AI planner."""
        planner = AsyncMock()
        return planner

    @pytest.fixture
    def task_service(self, mock_engine, mock_ai_planner):
        """Create task service with mocked dependencies."""
        return TaskService(
            engine=mock_engine,
            ai_planner=mock_ai_planner
        )

    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for testing."""
        return [
            {
                "title": "Setup authentication",
                "description": "Setup JWT authentication system",
                "estimated_minutes": 10,
                "task_type": "implementation",
                "complexity": "moderate",
                "priority": "high",
                "keywords": ["auth", "jwt"],
                "acceptance_criteria": ["JWT tokens work", "Login endpoint ready"]
            },
            {
                "title": "Write authentication tests",
                "description": "Create unit tests for authentication",
                "estimated_minutes": 8,
                "task_type": "testing",
                "complexity": "simple",
                "priority": "medium",
                "keywords": ["testing", "auth"],
                "acceptance_criteria": ["All tests pass", "Coverage > 90%"]
            }
        ]

    async def test_service_initialization(self, mock_engine, mock_ai_planner):
        """Test service initialization with dependencies."""
        service = TaskService(
            engine=mock_engine,
            ai_planner=mock_ai_planner
        )

        assert service.engine == mock_engine
        assert service.repository == mock_engine.repository
        assert service.memory_storage == mock_engine.memory_storage
        assert service.ai_planner == mock_ai_planner
        assert len(service._workflow_templates) >= 2  # Default templates loaded

    async def test_service_initialization_with_defaults(self):
        """Test service initialization with default dependencies."""
        with patch('devstream.tasks.service.TaskEngine') as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine.repository = AsyncMock()
            mock_engine.memory_storage = AsyncMock()
            mock_engine_class.return_value = mock_engine

            service = TaskService()

            assert service.engine == mock_engine
            mock_engine_class.assert_called_once_with(None, None, None)

    async def test_service_statistics(self, task_service):
        """Test service statistics tracking."""
        stats = task_service.get_service_statistics()

        assert "plans_created" in stats
        assert "tasks_created" in stats
        assert "tasks_completed" in stats
        assert "workflows_executed" in stats
        assert "templates_available" in stats
        assert stats["plans_created"] == 0  # Initial state


@pytest.mark.unit
@pytest.mark.tasks
class TestQuickStartOperations:
    """Test quick start workflow operations."""

    async def test_create_simple_plan(self, task_service, sample_task_data):
        """Test creating simple plan with tasks."""
        # Mock engine responses
        mock_plan = MagicMock()
        mock_plan.id = uuid4()
        mock_phase = MagicMock()
        mock_phase.id = uuid4()
        mock_tasks = [MagicMock(id=uuid4()) for _ in sample_task_data]
        mock_ready_tasks = [mock_tasks[0]]

        task_service.engine.create_intervention_plan.return_value = mock_plan
        task_service.engine.create_phase.return_value = mock_phase
        task_service.engine.create_micro_task.side_effect = mock_tasks
        task_service.engine.get_ready_tasks.return_value = mock_ready_tasks

        result = await task_service.create_simple_plan(
            title="Authentication System",
            objective="Implement user authentication",
            tasks=sample_task_data,
            estimated_hours=2.0
        )

        # Verify plan creation
        task_service.engine.create_intervention_plan.assert_called_once()
        call_args = task_service.engine.create_intervention_plan.call_args
        assert call_args[1]["title"] == "Authentication System"
        assert call_args[1]["estimated_hours"] == 2.0

        # Verify phase creation
        task_service.engine.create_phase.assert_called_once()
        phase_args = task_service.engine.create_phase.call_args
        assert phase_args[1]["name"] == "Implementation"

        # Verify task creation
        assert task_service.engine.create_micro_task.call_count == 2

        # Verify result structure
        assert result["plan"] == mock_plan
        assert result["phase"] == mock_phase
        assert len(result["tasks"]) == 2
        assert result["ready_tasks"] == mock_ready_tasks

        # Verify statistics update
        assert task_service._operation_stats["plans_created"] == 1
        assert task_service._operation_stats["tasks_created"] == 2

    async def test_create_simple_plan_auto_estimation(self, task_service, sample_task_data):
        """Test automatic estimation when hours not provided."""
        mock_plan = MagicMock()
        mock_plan.id = uuid4()
        mock_phase = MagicMock()
        mock_tasks = [MagicMock() for _ in sample_task_data]

        task_service.engine.create_intervention_plan.return_value = mock_plan
        task_service.engine.create_phase.return_value = mock_phase
        task_service.engine.create_micro_task.side_effect = mock_tasks
        task_service.engine.get_ready_tasks.return_value = []

        result = await task_service.create_simple_plan(
            title="Test Plan",
            objective="Test objective",
            tasks=sample_task_data
            # No estimated_hours provided
        )

        # Verify auto-calculated hours
        call_args = task_service.engine.create_intervention_plan.call_args
        expected_hours = (10 + 8) / 60.0  # Task minutes converted to hours
        assert call_args[1]["estimated_hours"] == expected_hours

    async def test_create_from_template(self, task_service):
        """Test creating plan from workflow template."""
        # Setup template
        template = TaskWorkflowTemplate(
            name="test_template",
            description="Test template",
            phases=[
                {
                    "name": "Phase 1",
                    "description": "Test phase",
                    "objective": "Test objective",
                    "order_index": 1,
                    "estimated_hours": 2.0
                }
            ],
            default_tasks=[
                {
                    "title": "Test task",
                    "description": "Test task description",
                    "task_type": "implementation",
                    "phase_index": 1,
                    "estimated_minutes": 5,
                    "complexity": "simple",
                    "priority": "medium",
                    "keywords": ["test"]
                }
            ]
        )
        task_service.register_workflow_template(template)

        # Mock engine responses
        mock_plan = MagicMock()
        mock_plan.id = uuid4()
        mock_phase = MagicMock()
        mock_phase.order_index = 1
        mock_task = MagicMock()

        task_service.engine.create_intervention_plan.return_value = mock_plan
        task_service.engine.create_phase.return_value = mock_phase
        task_service.engine.create_micro_task.return_value = mock_task

        result = await task_service.create_from_template(
            template_name="test_template",
            title="Template Plan",
            objective="Template objective"
        )

        # Verify template usage
        assert result["template_used"] == "test_template"
        assert result["plan"] == mock_plan
        assert len(result["phases"]) == 1
        assert len(result["tasks"]) == 1

        # Verify statistics
        assert task_service._operation_stats["workflows_executed"] == 1

    async def test_create_from_invalid_template(self, task_service):
        """Test error handling for invalid template."""
        with pytest.raises(WorkflowError, match="Template 'invalid' not found"):
            await task_service.create_from_template(
                template_name="invalid",
                title="Test",
                objective="Test"
            )

    async def test_create_from_template_with_customizations(self, task_service):
        """Test template creation with customizations."""
        # Register minimal template
        template = TaskWorkflowTemplate(
            name="custom_test",
            description="Default description",
            phases=[],
            default_tasks=[]
        )
        task_service.register_workflow_template(template)

        mock_plan = MagicMock()
        task_service.engine.create_intervention_plan.return_value = mock_plan

        customizations = {
            "description": "Custom description",
            "estimated_hours": 5.0,
            "category": "research"
        }

        await task_service.create_from_template(
            template_name="custom_test",
            title="Custom Plan",
            objective="Custom objective",
            customizations=customizations
        )

        # Verify customizations applied
        call_args = task_service.engine.create_intervention_plan.call_args
        assert call_args[1]["description"] == "Custom description"
        assert call_args[1]["estimated_hours"] == 5.0
        assert call_args[1]["category"] == "research"


@pytest.mark.unit
@pytest.mark.tasks
class TestWorkflowExecution:
    """Test workflow execution operations."""

    async def test_execute_next_ready_task(self, task_service):
        """Test executing next ready task."""
        task_id = uuid4()
        mock_ready_task = MagicMock()
        mock_ready_task.id = task_id
        mock_ready_task.title = "Ready Task"
        mock_ready_task.estimated_minutes = 5

        mock_started_task = MagicMock()
        mock_started_task.id = task_id
        mock_started_task.estimated_minutes = 5

        plan_id = uuid4()

        # Mock engine responses
        task_service.engine.get_ready_tasks.return_value = [mock_ready_task]
        task_service.engine.start_task.return_value = mock_started_task

        result = await task_service.execute_next_ready_task(
            plan_id=plan_id,
            assignee="test-agent"
        )

        # Verify execution
        task_service.engine.get_ready_tasks.assert_called_once_with(plan_id)
        task_service.engine.start_task.assert_called_once_with(task_id, "test-agent")
        assert result == mock_started_task

    async def test_execute_next_ready_task_no_tasks(self, task_service):
        """Test execution when no ready tasks available."""
        plan_id = uuid4()
        task_service.engine.get_ready_tasks.return_value = []

        result = await task_service.execute_next_ready_task(plan_id)

        assert result is None

    async def test_execute_next_ready_task_auto_complete(self, task_service):
        """Test auto-completion of ready task."""
        task_id = uuid4()
        mock_ready_task = MagicMock()
        mock_ready_task.id = task_id
        mock_ready_task.estimated_minutes = 5

        mock_started_task = MagicMock()
        mock_started_task.id = task_id
        mock_started_task.estimated_minutes = 5

        mock_completed_task = MagicMock()
        mock_completed_task.id = task_id

        plan_id = uuid4()

        # Mock engine responses
        task_service.engine.get_ready_tasks.return_value = [mock_ready_task]
        task_service.engine.start_task.return_value = mock_started_task
        task_service.engine.complete_task.return_value = mock_completed_task

        result = await task_service.execute_next_ready_task(
            plan_id=plan_id,
            auto_complete=True
        )

        # Verify completion
        task_service.engine.complete_task.assert_called_once_with(
            task_id,
            actual_minutes=5,
            completion_notes="Auto-completed by task service"
        )
        assert result == mock_completed_task
        assert task_service._operation_stats["tasks_completed"] == 1

    async def test_execute_task_sequence_sequential(self, task_service):
        """Test sequential task execution."""
        task_ids = [uuid4(), uuid4()]
        mock_tasks = [MagicMock() for _ in task_ids]

        with patch.object(task_service, '_execute_single_task') as mock_execute:
            mock_execute.side_effect = mock_tasks

            result = await task_service.execute_task_sequence(
                task_ids=task_ids,
                assignee="test-agent",
                parallel=False
            )

            assert len(result) == 2
            assert mock_execute.call_count == 2
            assert task_service._operation_stats["tasks_completed"] == 2

    async def test_execute_task_sequence_parallel(self, task_service):
        """Test parallel task execution."""
        task_ids = [uuid4(), uuid4()]
        mock_tasks = [MagicMock() for _ in task_ids]

        with patch.object(task_service, '_execute_single_task') as mock_execute:
            mock_execute.side_effect = mock_tasks

            result = await task_service.execute_task_sequence(
                task_ids=task_ids,
                assignee="test-agent",
                parallel=True
            )

            assert len(result) == 2
            assert mock_execute.call_count == 2

    async def test_auto_execute_plan(self, task_service):
        """Test automatic plan execution."""
        plan_id = uuid4()

        # Mock ready tasks that become empty after one iteration
        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.estimated_minutes = 2

        call_count = 0
        async def mock_get_ready_tasks(pid):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [mock_task]
            return []

        task_service.engine.get_ready_tasks.side_effect = mock_get_ready_tasks
        task_service.engine.start_task.return_value = mock_task

        # Mock progress response
        mock_progress = {"overall_progress": 100.0}
        task_service.engine.get_plan_progress.return_value = mock_progress

        result = await task_service.auto_execute_plan(
            plan_id=plan_id,
            max_parallel_tasks=2,
            simulation_mode=True
        )

        # Verify execution
        assert "execution_log" in result
        assert "final_progress" in result
        assert result["final_progress"] == mock_progress

        # Should have at least one task started
        started_actions = [log for log in result["execution_log"] if log["action"] == "started"]
        assert len(started_actions) >= 1

    async def test_auto_execute_plan_with_errors(self, task_service):
        """Test auto execution with task start errors."""
        plan_id = uuid4()
        mock_task = MagicMock()
        mock_task.id = uuid4()

        call_count = 0
        async def mock_get_ready_tasks(pid):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [mock_task]
            return []

        task_service.engine.get_ready_tasks.side_effect = mock_get_ready_tasks
        task_service.engine.start_task.side_effect = Exception("Task start failed")
        task_service.engine.get_plan_progress.return_value = {"overall_progress": 0.0}

        result = await task_service.auto_execute_plan(plan_id)

        # Verify error handling
        error_actions = [log for log in result["execution_log"] if log["action"] == "error"]
        assert len(error_actions) >= 1
        assert "Task start failed" in error_actions[0]["error"]


@pytest.mark.unit
@pytest.mark.tasks
class TestPlanningAndAnalysis:
    """Test planning and analysis operations."""

    async def test_analyze_plan_feasibility(self, task_service):
        """Test plan feasibility analysis."""
        plan_id = uuid4()

        # Mock progress data
        mock_progress = {
            "plan": MagicMock(title="Test Plan"),
            "overall_progress": 45.0,
            "ready_tasks": [
                MagicMock(task_type=TaskType.IMPLEMENTATION, complexity=TaskComplexity.SIMPLE),
                MagicMock(task_type=TaskType.TESTING, complexity=TaskComplexity.COMPLEX)
            ],
            "active_tasks": [
                MagicMock(task_type=TaskType.IMPLEMENTATION, complexity=TaskComplexity.MODERATE)
            ]
        }

        # Mock metrics data
        mock_metrics = {
            "bottleneck_tasks": [
                {"task_title": "Bottleneck Task", "dependent_task_count": 5}
            ],
            "dependency_violations": [],
            "completion_estimates": {
                "estimated_completion": datetime.now() + timedelta(hours=8)
            }
        }

        task_service.engine.get_plan_progress.return_value = mock_progress
        task_service.engine.get_task_execution_metrics.return_value = mock_metrics

        result = await task_service.analyze_plan_feasibility(plan_id)

        # Verify analysis structure
        assert "plan" in result
        assert "feasibility_score" in result
        assert "task_distribution" in result
        assert "complexity_distribution" in result
        assert "estimated_completion" in result
        assert "issues" in result
        assert "recommendations" in result

        # Verify task distribution
        assert result["task_distribution"]["implementation"] == 2
        assert result["task_distribution"]["testing"] == 1

        # Verify complexity distribution
        assert result["complexity_distribution"]["simple"] == 1
        assert result["complexity_distribution"]["complex"] == 1
        assert result["complexity_distribution"]["moderate"] == 1

        # Verify bottleneck issue detected
        bottleneck_issues = [issue for issue in result["issues"] if issue["type"] == "bottleneck"]
        assert len(bottleneck_issues) == 1

    async def test_analyze_plan_complexity_imbalance(self, task_service):
        """Test detection of complexity imbalance issues."""
        plan_id = uuid4()

        # Mock progress with too many complex tasks
        mock_progress = {
            "plan": MagicMock(),
            "overall_progress": 20.0,
            "ready_tasks": [
                MagicMock(task_type=TaskType.IMPLEMENTATION, complexity=TaskComplexity.COMPLEX),
                MagicMock(task_type=TaskType.IMPLEMENTATION, complexity=TaskComplexity.COMPLEX)
            ],
            "active_tasks": [
                MagicMock(task_type=TaskType.IMPLEMENTATION, complexity=TaskComplexity.SIMPLE)
            ]
        }

        mock_metrics = {
            "bottleneck_tasks": [],
            "dependency_violations": [],
            "completion_estimates": {"estimated_completion": datetime.now()}
        }

        task_service.engine.get_plan_progress.return_value = mock_progress
        task_service.engine.get_task_execution_metrics.return_value = mock_metrics

        result = await task_service.analyze_plan_feasibility(plan_id)

        # Verify complexity imbalance detected (2/3 = 66% complex tasks)
        complexity_issues = [issue for issue in result["issues"] if issue["type"] == "complexity_imbalance"]
        assert len(complexity_issues) == 1
        assert "breaking down complex tasks" in complexity_issues[0]["recommendation"]

    async def test_suggest_task_breakdown_implementation(self, task_service):
        """Test task breakdown suggestions for implementation tasks."""
        complex_task = MagicMock()
        complex_task.title = "Implement authentication system"
        complex_task.description = "Complete JWT authentication implementation"
        complex_task.task_type = TaskType.IMPLEMENTATION
        complex_task.complexity = TaskComplexity.COMPLEX

        suggestions = await task_service.suggest_task_breakdown(
            task=complex_task,
            target_complexity=TaskComplexity.SIMPLE
        )

        assert len(suggestions) == 3

        # Verify design phase
        design_task = suggestions[0]
        assert "Design" in design_task["title"]
        assert design_task["task_type"] == "research"
        assert design_task["complexity"] == "simple"

        # Verify implementation phase
        impl_task = suggestions[1]
        assert "core" in impl_task["title"].lower()
        assert impl_task["task_type"] == "implementation"
        assert impl_task["complexity"] == "moderate"

        # Verify testing phase
        test_task = suggestions[2]
        assert "Test" in test_task["title"]
        assert test_task["task_type"] == "testing"
        assert test_task["complexity"] == "simple"

        # Verify dependencies
        assert suggestions[1].get("depends_on_previous") is True
        assert suggestions[2].get("depends_on_previous") is True

    async def test_suggest_task_breakdown_research(self, task_service):
        """Test task breakdown suggestions for research tasks."""
        research_task = MagicMock()
        research_task.title = "Research authentication patterns"
        research_task.description = "Research best practices for authentication"
        research_task.task_type = TaskType.RESEARCH
        research_task.complexity = TaskComplexity.COMPLEX

        suggestions = await task_service.suggest_task_breakdown(research_task)

        assert len(suggestions) == 2

        # Verify initial research
        initial_task = suggestions[0]
        assert "Initial" in initial_task["title"]
        assert initial_task["task_type"] == "research"

        # Verify deep dive research
        deep_task = suggestions[1]
        assert "Deep dive" in deep_task["title"]
        assert deep_task["task_type"] == "research"

    async def test_suggest_task_breakdown_simple_task(self, task_service):
        """Test no breakdown needed for simple tasks."""
        simple_task = MagicMock()
        simple_task.task_type = TaskType.IMPLEMENTATION
        simple_task.complexity = TaskComplexity.SIMPLE

        suggestions = await task_service.suggest_task_breakdown(simple_task)

        assert len(suggestions) == 0

    async def test_optimize_task_dependencies(self, task_service):
        """Test task dependency optimization."""
        plan_id = uuid4()

        # Mock dependency graph
        mock_graph = MagicMock()

        # Create mock tasks with keywords
        task1 = MagicMock()
        task1.id = uuid4()
        task1.title = "Task 1"
        task1.keywords = ["auth", "jwt"]
        task1.depends_on = set()

        task2 = MagicMock()
        task2.id = uuid4()
        task2.title = "Task 2"
        task2.keywords = ["database", "user"]
        task2.depends_on = {task1.id}

        task3 = MagicMock()
        task3.id = uuid4()
        task3.title = "Task 3"
        task3.keywords = ["auth", "jwt", "security"]  # High overlap with task1
        task3.depends_on = set()

        mock_graph.tasks = {
            task1.id: task1,
            task2.id: task2,
            task3.id: task3
        }
        mock_graph.get_critical_path.return_value = [task1.id, task2.id]

        task_service.engine.build_dependency_graph.return_value = mock_graph

        result = await task_service.optimize_task_dependencies(plan_id)

        # Verify optimization analysis
        assert "current_dependencies" in result
        assert "optimization_suggestions" in result
        assert "critical_path_length" in result
        assert "potential_parallelism" in result

        # Should suggest removing unnecessary dependency (task2 -> task1)
        remove_suggestions = [
            s for s in result["optimization_suggestions"]
            if s["type"] == "remove_dependency"
        ]
        assert len(remove_suggestions) >= 1

        # Should suggest adding dependency (task3 -> task1 due to keyword overlap)
        add_suggestions = [
            s for s in result["optimization_suggestions"]
            if s["type"] == "add_dependency"
        ]
        assert len(add_suggestions) >= 1


@pytest.mark.unit
@pytest.mark.tasks
class TestAIPoweredPlanning:
    """Test AI-powered planning operations."""

    async def test_create_ai_powered_plan(self, task_service):
        """Test AI-powered plan creation."""
        # Mock AI planner response
        mock_planning_result = MagicMock()
        mock_planning_result.total_estimated_minutes = 120
        mock_planning_result.suggested_phases = ["Analysis", "Implementation"]
        mock_planning_result.planning_confidence = 0.85
        mock_planning_result.completeness_score = 0.90
        mock_planning_result.average_complexity = 5.5
        mock_planning_result.planning_reasoning = "AI reasoning text"

        # Mock AI tasks
        mock_ai_task1 = MagicMock()
        mock_ai_task1.id = "ai-task-1"
        mock_ai_task1.title = "Analyze requirements"
        mock_ai_task1.description = "Analyze user requirements"
        mock_ai_task1.task_type = "research"
        mock_ai_task1.complexity_score = 4
        mock_ai_task1.estimated_minutes = 30
        mock_ai_task1.priority_score = 0.8
        mock_ai_task1.confidence_score = 0.85
        mock_ai_task1.suggested_phase = "Analysis"

        mock_ai_task2 = MagicMock()
        mock_ai_task2.id = "ai-task-2"
        mock_ai_task2.title = "Implement core logic"
        mock_ai_task2.description = "Implement main functionality"
        mock_ai_task2.task_type = "implementation"
        mock_ai_task2.complexity_score = 7
        mock_ai_task2.estimated_minutes = 90
        mock_ai_task2.priority_score = 0.9
        mock_ai_task2.confidence_score = 0.75
        mock_ai_task2.suggested_phase = "Implementation"

        mock_planning_result.suggested_tasks = [mock_ai_task1, mock_ai_task2]

        # Mock AI dependencies
        mock_dependency = MagicMock()
        mock_dependency.prerequisite_task_id = "ai-task-1"
        mock_dependency.dependent_task_id = "ai-task-2"
        mock_dependency.reasoning = "Analysis must complete before implementation"
        mock_dependency.confidence_score = 0.95

        mock_planning_result.suggested_dependencies = [mock_dependency]

        task_service.ai_planner.generate_plan.return_value = mock_planning_result

        # Mock engine responses
        mock_plan = MagicMock()
        mock_plan.id = uuid4()
        mock_phase1 = MagicMock()
        mock_phase1.id = uuid4()
        mock_phase2 = MagicMock()
        mock_phase2.id = uuid4()
        mock_task1 = MagicMock()
        mock_task1.id = uuid4()
        mock_task2 = MagicMock()
        mock_task2.id = uuid4()

        task_service.engine.create_intervention_plan.return_value = mock_plan
        task_service.engine.create_phase.side_effect = [mock_phase1, mock_phase2]
        task_service.engine.create_micro_task.side_effect = [mock_task1, mock_task2]

        result = await task_service.create_ai_powered_plan(
            title="AI Generated Plan",
            description="Plan created with AI assistance",
            objectives=["Objective 1", "Objective 2"],
            context="Project context information"
        )

        # Verify AI planner was called
        task_service.ai_planner.generate_plan.assert_called_once()

        # Verify plan creation
        task_service.engine.create_intervention_plan.assert_called_once()
        plan_args = task_service.engine.create_intervention_plan.call_args
        assert plan_args[1]["title"] == "AI Generated Plan"
        assert plan_args[1]["estimated_hours"] == 2.0  # 120 minutes / 60
        assert plan_args[1]["category"] == "ai_generated"

        # Verify phases created
        assert task_service.engine.create_phase.call_count == 2

        # Verify tasks created
        assert task_service.engine.create_micro_task.call_count == 2

        # Verify dependencies added
        task_service.engine.add_task_dependency.assert_called_once()

        # Verify result structure
        assert result["plan"] == mock_plan
        assert len(result["phases"]) == 2
        assert len(result["tasks"]) == 2
        assert len(result["dependencies"]) == 1
        assert "ai_analysis" in result
        assert result["ai_analysis"]["planning_confidence"] == 0.85

    async def test_create_ai_powered_plan_no_planner(self, task_service):
        """Test error when AI planner not available."""
        task_service.ai_planner = None

        with pytest.raises(PlanningError, match="AI Planner not available"):
            await task_service.create_ai_powered_plan(
                title="Test",
                description="Test",
                objectives=["Test"]
            )

    async def test_ai_task_breakdown(self, task_service):
        """Test AI-powered task breakdown."""
        # Mock AI planning result
        mock_planning_result = MagicMock()

        mock_ai_task = MagicMock()
        mock_ai_task.title = "Setup database"
        mock_ai_task.description = "Configure database connection"
        mock_ai_task.estimated_minutes = 15
        mock_ai_task.task_type = "implementation"
        mock_ai_task.complexity_score = 5
        mock_ai_task.priority_score = 0.7
        mock_ai_task.confidence_score = 0.8
        mock_ai_task.reasoning = "Database setup is foundational"

        mock_planning_result.suggested_tasks = [mock_ai_task]

        task_service.ai_planner.generate_task_breakdown.return_value = mock_planning_result

        result = await task_service.ai_task_breakdown(
            objective="Setup database connection",
            context="Using PostgreSQL",
            max_tasks=10,
            target_duration=15
        )

        # Verify AI planner called
        task_service.ai_planner.generate_task_breakdown.assert_called_once()

        # Verify result format
        assert len(result) == 1
        task_data = result[0]
        assert task_data["title"] == "Setup database"
        assert task_data["estimated_minutes"] == 15
        assert task_data["task_type"] == "implementation"
        assert task_data["complexity"] == "moderate"  # Score 5 maps to moderate
        assert task_data["priority"] == "high"  # Score 0.7 maps to high
        assert task_data["ai_confidence"] == 0.8

    async def test_estimate_task_complexity(self, task_service):
        """Test AI-powered complexity estimation."""
        # Mock AI estimation result
        mock_estimation = MagicMock()
        mock_estimation.estimated_minutes = 25
        mock_estimation.complexity_score = 7
        mock_estimation.uncertainty_factor = 0.3
        mock_estimation.confidence_score = 0.75
        mock_estimation.analysis_factors = ["Database interaction", "Error handling"]
        mock_estimation.risk_factors = ["External dependency"]
        mock_estimation.assumptions = ["Database is available"]
        mock_estimation.estimation_reasoning = "Complex due to error handling"
        mock_estimation.approach_used = MagicMock()
        mock_estimation.approach_used.value = "detailed"

        task_service.ai_planner.estimate_complexity.return_value = mock_estimation

        result = await task_service.estimate_task_complexity(
            task_title="Database migration",
            task_description="Migrate user data to new schema",
            project_context="Legacy system upgrade"
        )

        # Verify AI planner called
        task_service.ai_planner.estimate_complexity.assert_called_once()

        # Verify result structure
        assert result["estimated_minutes"] == 25
        assert result["complexity_score"] == 7
        assert result["uncertainty_factor"] == 0.3
        assert result["confidence_score"] == 0.75
        assert "Database interaction" in result["analysis_factors"]
        assert "External dependency" in result["risk_factors"]
        assert result["approach_used"] == "detailed"

    async def test_ai_planning_error_handling(self, task_service):
        """Test error handling in AI planning methods."""
        # Mock AI planner to raise exception
        task_service.ai_planner.generate_plan.side_effect = Exception("AI service unavailable")

        with pytest.raises(PlanningError, match="AI-powered plan creation failed"):
            await task_service.create_ai_powered_plan(
                title="Test",
                description="Test",
                objectives=["Test"]
            )

    async def test_ai_task_type_mapping(self, task_service):
        """Test AI task type mapping."""
        # Test various AI task types
        assert task_service._map_ai_task_type("implementation") == TaskType.IMPLEMENTATION
        assert task_service._map_ai_task_type("testing") == TaskType.TESTING
        assert task_service._map_ai_task_type("research") == TaskType.RESEARCH
        assert task_service._map_ai_task_type("review") == TaskType.TESTING
        assert task_service._map_ai_task_type("setup") == TaskType.IMPLEMENTATION
        assert task_service._map_ai_task_type("unknown") == TaskType.IMPLEMENTATION  # Default

    async def test_ai_complexity_mapping(self, task_service):
        """Test AI complexity score mapping."""
        assert task_service._map_ai_complexity(1) == TaskComplexity.SIMPLE
        assert task_service._map_ai_complexity(3) == TaskComplexity.SIMPLE
        assert task_service._map_ai_complexity(5) == TaskComplexity.MODERATE
        assert task_service._map_ai_complexity(7) == TaskComplexity.COMPLEX
        assert task_service._map_ai_complexity(10) == TaskComplexity.VERY_COMPLEX

    async def test_ai_priority_mapping(self, task_service):
        """Test AI priority score mapping."""
        assert task_service._map_ai_priority(0.1) == TaskPriority.LOW
        assert task_service._map_ai_priority(0.5) == TaskPriority.MEDIUM
        assert task_service._map_ai_priority(0.7) == TaskPriority.HIGH
        assert task_service._map_ai_priority(0.9) == TaskPriority.URGENT


@pytest.mark.unit
@pytest.mark.tasks
class TestMonitoringAndReporting:
    """Test monitoring and reporting functionality."""

    async def test_get_execution_dashboard(self, task_service):
        """Test execution dashboard data generation."""
        plan_id = uuid4()

        # Mock progress data
        mock_plan = MagicMock()
        mock_plan.title = "Dashboard Test Plan"
        mock_plan.status = TaskStatus.IN_PROGRESS

        mock_progress = {
            "plan": mock_plan,
            "overall_progress": 65.0,
            "task_statistics": {
                "completed": 8,
                "active": 2,
                "pending": 5
            },
            "ready_tasks": [MagicMock(), MagicMock()]
        }

        # Mock metrics data
        mock_metrics = {
            "completion_estimates": {
                "estimated_completion": datetime.now() + timedelta(hours=4)
            },
            "bottleneck_tasks": [
                {"task_title": "Bottleneck Task", "dependent_task_count": 3}
            ]
        }

        task_service.engine.get_plan_progress.return_value = mock_progress
        task_service.engine.get_task_execution_metrics.return_value = mock_metrics

        # Mock helper methods
        with patch.multiple(
            task_service,
            _calculate_velocity=AsyncMock(return_value={"tasks_per_hour": 2.5}),
            _get_recent_activity=AsyncMock(return_value=[{"action": "completed"}]),
            _suggest_next_actions=AsyncMock(return_value=[{"action": "start_task"}]),
            _calculate_health_score=AsyncMock(return_value=7.5)
        ):
            result = await task_service.get_execution_dashboard(plan_id)

        # Verify dashboard structure
        assert "plan_overview" in result
        assert "task_summary" in result
        assert "velocity" in result
        assert "bottlenecks" in result
        assert "recent_activity" in result
        assert "next_actions" in result
        assert "health_score" in result

        # Verify plan overview
        assert result["plan_overview"]["title"] == "Dashboard Test Plan"
        assert result["plan_overview"]["status"] == "in_progress"
        assert result["plan_overview"]["overall_progress"] == 65.0

        # Verify task summary
        assert result["task_summary"]["total"] == 15  # 8 + 2 + 5
        assert result["task_summary"]["completed"] == 8
        assert result["task_summary"]["ready"] == 2

    async def test_generate_progress_report(self, task_service):
        """Test progress report generation."""
        plan_id = uuid4()

        # Mock dashboard data
        mock_dashboard = {
            "plan_overview": {
                "title": "Test Progress Report",
                "status": "in_progress",
                "overall_progress": 75.0,
                "estimated_completion": datetime(2024, 12, 31, 15, 30)
            },
            "task_summary": {
                "total": 20,
                "completed": 15,
                "active": 3,
                "ready": 2,
                "pending": 0
            },
            "velocity": {
                "tasks_per_hour": 3.2,
                "avg_duration_minutes": 8.5
            },
            "bottlenecks": [
                {"task_title": "Database migration", "dependent_task_count": 5},
                {"task_title": "API setup", "dependent_task_count": 2}
            ],
            "next_actions": [
                {"action": "start_task", "description": "Start authentication setup"},
                {"action": "resolve_bottleneck", "description": "Complete database migration"}
            ],
            "health_score": 8.2
        }

        with patch.object(task_service, 'get_execution_dashboard') as mock_dashboard_method:
            mock_dashboard_method.return_value = mock_dashboard

            report = await task_service.generate_progress_report(plan_id)

        # Verify report content
        assert "Test Progress Report" in report
        assert "75.0%" in report
        assert "Health Score: 8.2/10" in report
        assert "Total Tasks: 20" in report
        assert "Completed: 15" in report
        assert "Velocity: 3.2 tasks/hour" in report
        assert "Database migration" in report
        assert "Start authentication setup" in report
        assert "2024-12-31 15:30" in report

    async def test_get_historical_metrics(self, task_service):
        """Test historical metrics retrieval."""
        plan_id = uuid4()

        mock_progress = {"overall_progress": 80.0}
        task_service.engine.get_plan_progress.return_value = mock_progress

        result = await task_service.get_historical_metrics(plan_id, days=14)

        # Verify metrics structure
        assert result["plan_id"] == str(plan_id)
        assert result["period_days"] == 14
        assert result["current_snapshot"] == mock_progress
        assert "historical_data" in result


@pytest.mark.unit
@pytest.mark.tasks
class TestTemplateManagement:
    """Test workflow template management."""

    async def test_register_workflow_template(self, task_service):
        """Test template registration."""
        template = TaskWorkflowTemplate(
            name="custom_template",
            description="Custom workflow template",
            phases=[],
            default_tasks=[]
        )

        initial_count = len(task_service.get_available_templates())
        task_service.register_workflow_template(template)

        assert len(task_service.get_available_templates()) == initial_count + 1
        assert "custom_template" in task_service.get_available_templates()

    async def test_get_template_details(self, task_service):
        """Test getting template details."""
        # Test existing default template
        template = task_service.get_template_details("software_development")
        assert template is not None
        assert template.name == "software_development"
        assert len(template.phases) > 0
        assert len(template.default_tasks) > 0

        # Test non-existent template
        template = task_service.get_template_details("non_existent")
        assert template is None

    async def test_get_available_templates(self, task_service):
        """Test getting available templates list."""
        templates = task_service.get_available_templates()

        # Should have default templates
        assert "software_development" in templates
        assert "research_project" in templates
        assert len(templates) >= 2

    async def test_default_templates_loaded(self, task_service):
        """Test that default templates are properly loaded."""
        # Software development template
        dev_template = task_service.get_template_details("software_development")
        assert dev_template is not None
        assert len(dev_template.phases) == 3
        assert any("Planning" in phase["name"] for phase in dev_template.phases)
        assert any("Implementation" in phase["name"] for phase in dev_template.phases)
        assert any("Testing" in phase["name"] for phase in dev_template.phases)

        # Research template
        research_template = task_service.get_template_details("research_project")
        assert research_template is not None
        assert len(research_template.phases) == 3
        assert any("Literature" in phase["name"] for phase in research_template.phases)


@pytest.mark.unit
@pytest.mark.tasks
class TestServiceHelperMethods:
    """Test service helper and utility methods."""

    async def test_execute_single_task(self, task_service):
        """Test single task execution helper."""
        task_id = uuid4()

        mock_started_task = MagicMock()
        mock_started_task.id = task_id
        mock_started_task.estimated_minutes = 10

        mock_completed_task = MagicMock()
        mock_completed_task.id = task_id

        task_service.engine.start_task.return_value = mock_started_task
        task_service.engine.complete_task.return_value = mock_completed_task

        result = await task_service._execute_single_task(task_id, "test-agent")

        # Verify task started and completed
        task_service.engine.start_task.assert_called_once_with(task_id, "test-agent")
        task_service.engine.complete_task.assert_called_once_with(
            task_id,
            actual_minutes=10,
            completion_notes="Completed by task service"
        )
        assert result == mock_completed_task

    async def test_simulate_task_completion(self, task_service):
        """Test task completion simulation."""
        task_id = uuid4()
        active_tasks = {task_id}
        execution_log = []

        mock_task = MagicMock()
        mock_task.estimated_minutes = 5

        mock_completed_task = MagicMock()
        mock_completed_task.id = task_id

        task_service.engine.get_micro_task.return_value = mock_task
        task_service.engine.complete_task.return_value = mock_completed_task

        await task_service._simulate_task_completion(task_id, active_tasks, execution_log)

        # Verify task was completed
        task_service.engine.complete_task.assert_called_once_with(
            task_id,
            actual_minutes=5,
            completion_notes="Auto-completed by simulation"
        )

        # Verify task removed from active set
        assert task_id not in active_tasks

        # Verify execution log updated
        completed_logs = [log for log in execution_log if log["action"] == "completed"]
        assert len(completed_logs) == 1

    async def test_calculate_feasibility_score(self, task_service):
        """Test feasibility score calculation."""
        # Test with no issues
        score = task_service._calculate_feasibility_score({}, {}, [])
        assert score == 10.0

        # Test with critical issue
        issues = [{"severity": "critical"}]
        score = task_service._calculate_feasibility_score({}, {}, issues)
        assert score == 7.0  # 10 - 3

        # Test with bottlenecks
        metrics = {"bottleneck_tasks": [1, 2, 3]}
        score = task_service._calculate_feasibility_score({}, metrics, [])
        assert score == 8.5  # 10 - (3 * 0.5)

        # Test with dependency violations
        metrics = {"dependency_violations": [1, 2]}
        score = task_service._calculate_feasibility_score({}, metrics, [])
        assert score == 8.0  # 10 - (2 * 1.0)

        # Test minimum score
        issues = [{"severity": "critical"}, {"severity": "critical"}, {"severity": "critical"}, {"severity": "critical"}]
        score = task_service._calculate_feasibility_score({}, {}, issues)
        assert score == 0.0  # Can't go below 0

    async def test_generate_recommendations(self, task_service):
        """Test recommendation generation."""
        # Test bottleneck recommendation
        issues = [{"type": "bottleneck"}]
        recommendations = task_service._generate_recommendations(issues, {})
        assert any("parallelizing" in rec for rec in recommendations)

        # Test dependency violation recommendation
        issues = [{"type": "dependency_violation"}]
        recommendations = task_service._generate_recommendations(issues, {})
        assert any("dependency violations" in rec for rec in recommendations)

        # Test complexity imbalance recommendation
        issues = [{"type": "complexity_imbalance"}]
        recommendations = task_service._generate_recommendations(issues, {})
        assert any("Break down complex tasks" in rec for rec in recommendations)

        # Test many ready tasks recommendation
        progress = {"ready_tasks": [1, 2, 3, 4, 5, 6]}  # 6 ready tasks
        recommendations = task_service._generate_recommendations([], progress)
        assert any("parallel execution" in rec for rec in recommendations)

    async def test_calculate_potential_parallelism(self, task_service):
        """Test potential parallelism calculation."""
        # Mock dependency graph
        mock_graph = MagicMock()

        # Mock tasks with different dependency patterns
        task1 = MagicMock()
        task1.depends_on = set()  # Independent

        task2 = MagicMock()
        task2.depends_on = set()  # Independent

        task3 = MagicMock()
        task3.depends_on = {uuid4()}  # Has dependency

        mock_graph.tasks = {"t1": task1, "t2": task2, "t3": task3}

        parallelism = task_service._calculate_potential_parallelism(mock_graph)
        assert parallelism == 2  # Two independent tasks