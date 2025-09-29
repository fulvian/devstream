"""
Tasks-Memory integration tests.

CONTEXT7-VALIDATED PATTERNS IMPLEMENTATION:
- Task system integration with memory context injection
- Memory capture during task execution workflows
- Cross-system state consistency validation
- Task-memory relationship integrity testing
- Workflow progression with memory persistence
"""

import pytest
import pytest_asyncio
import asyncio
from typing import List, Dict, Any

from devstream.tasks.models import MicroTask, TaskStatus, TaskType, TaskPriority
from devstream.memory.models import MemoryEntry, ContentType, ContentFormat
from devstream.database.queries import QueryManager


@pytest.mark.integration
@pytest.mark.tasks
@pytest.mark.memory
class TestTasksMemoryIntegration:
    """
    Test tasks system integration with memory context.
    Context7-validated patterns for cross-system integration testing.
    """

    async def test_task_creation_with_memory_context(
        self,
        integration_query_manager: QueryManager,
        integration_sample_plan: str,
        integration_memory_entries: List[str]
    ):
        """
        Test task creation using memory context.
        Context7 pattern: task initialization with memory-based context.
        """
        # Create phase for task
        from devstream.database.schema import phases
        phase_id = integration_query_manager.tasks.generate_id()

        async with integration_query_manager.pool.write_transaction() as conn:
            await conn.execute(
                phases.insert().values(
                    id=phase_id,
                    plan_id=integration_sample_plan,
                    name="Memory Context Test Phase",
                    description="Phase for testing task-memory integration",
                    objective="Execute tasks with memory context",
                    sequence_order=1,
                    status="active",
                )
            )

        # Create task with memory context references
        task_id = await integration_query_manager.tasks.create(
            phase_id=phase_id,
            title="Task with Memory Context",
            description="Task that should leverage memory context for implementation",
            assigned_agent="context-aware-agent",
            task_type="implementation",
            estimated_minutes=45,
        )

        # Verify task was created
        task = await integration_query_manager.tasks.get_by_id(task_id)
        assert task is not None
        assert task["title"] == "Task with Memory Context"
        assert task["phase_id"] == phase_id

    async def test_memory_injection_during_task_execution(
        self,
        integration_query_manager: QueryManager,
        integration_sample_task: str,
        integration_memory_entries: List[str]
    ):
        """
        Test memory injection during task execution workflow.
        Context7 pattern: context assembly for task execution.
        """
        # Simulate task execution workflow with memory context
        task = await integration_query_manager.tasks.get_by_id(integration_sample_task)
        assert task is not None

        # Create memory entry representing task context
        context_memory = MemoryEntry(
            id="task-context-001",
            content=f"Context for task execution: {task['title']}. Implementation approach should consider fibonacci algorithm optimizations.",
            content_type=ContentType.CONTEXT,
            task_id=integration_sample_task,
            keywords=["context", "execution", "fibonacci", "optimization"]
        )

        # Store context memory
        context_id = await integration_query_manager.memory.store(
            content=context_memory.content,
            content_type=context_memory.content_type.value,
            keywords=context_memory.keywords,
            task_id=context_memory.task_id
        )

        # Verify memory was linked to task
        assert context_id is not None

        # Retrieve task-related memories
        task_memories = await integration_query_manager.memory.search_by_keywords(["context"])
        task_related = [m for m in task_memories if m.get("task_id") == integration_sample_task]

        assert len(task_related) >= 1

    async def test_task_output_capture_to_memory(
        self,
        integration_query_manager: QueryManager,
        integration_sample_task: str
    ):
        """
        Test capturing task output to memory system.
        Context7 pattern: task output persistence for future context.
        """
        # Simulate task completion with output
        task_output = """
        Task completed successfully. Implemented fibonacci calculation with memoization:

        def fibonacci_memo(n, memo={}):
            if n in memo:
                return memo[n]
            if n <= 1:
                return n
            memo[n] = fibonacci_memo(n-1, memo) + fibonacci_memo(n-2, memo)
            return memo[n]

        Performance improvement: O(n) instead of O(2^n)
        """

        # Create memory entry for task output
        output_memory = MemoryEntry(
            id="task-output-001",
            content=task_output,
            content_type=ContentType.OUTPUT,
            content_format=ContentFormat.MARKDOWN,
            task_id=integration_sample_task,
            keywords=["fibonacci", "memoization", "optimization", "output", "completed"]
        )

        # Store task output in memory
        output_id = await integration_query_manager.memory.store(
            content=output_memory.content,
            content_type=output_memory.content_type.value,
            keywords=output_memory.keywords,
            task_id=output_memory.task_id
        )

        # Verify output was captured
        assert output_id is not None

        # Test retrieval of task outputs
        output_memories = await integration_query_manager.memory.search_by_keywords(["output", "completed"])
        task_outputs = [m for m in output_memories if m.get("task_id") == integration_sample_task]

        assert len(task_outputs) >= 1

    async def test_cross_task_memory_sharing(
        self,
        integration_query_manager: QueryManager,
        integration_sample_plan: str
    ):
        """
        Test memory sharing across related tasks.
        Context7 pattern: cross-task knowledge transfer through memory.
        """
        # Create two related tasks in same plan
        from devstream.database.schema import phases
        phase_id = integration_query_manager.tasks.generate_id()

        async with integration_query_manager.pool.write_transaction() as conn:
            await conn.execute(
                phases.insert().values(
                    id=phase_id,
                    plan_id=integration_sample_plan,
                    name="Cross-Task Memory Phase",
                    description="Phase for testing cross-task memory sharing",
                    objective="Share knowledge between related tasks",
                    sequence_order=1,
                    status="active",
                )
            )

        # Task 1: Research task
        task1_id = await integration_query_manager.tasks.create(
            phase_id=phase_id,
            title="Research Algorithm Approaches",
            description="Research different algorithm implementation approaches",
            assigned_agent="research-agent",
            task_type="research",
            estimated_minutes=30,
        )

        # Task 2: Implementation task
        task2_id = await integration_query_manager.tasks.create(
            phase_id=phase_id,
            title="Implement Optimized Algorithm",
            description="Implement algorithm based on research findings",
            assigned_agent="implementation-agent",
            task_type="implementation",
            estimated_minutes=60,
        )

        # Create shared memory from Task 1
        research_memory = MemoryEntry(
            id="shared-research-001",
            content="Research findings: Dynamic programming approach with memoization provides O(n) complexity. Iterative approach also viable for space optimization.",
            content_type=ContentType.LEARNING,
            task_id=task1_id,
            plan_id=integration_sample_plan,
            keywords=["research", "dynamic-programming", "memoization", "optimization"]
        )

        # Store research findings
        research_id = await integration_query_manager.memory.store(
            content=research_memory.content,
            content_type=research_memory.content_type.value,
            keywords=research_memory.keywords,
            task_id=research_memory.task_id
        )

        # Task 2 should be able to access Task 1's memory
        plan_memories = await integration_query_manager.memory.search_by_keywords(["research", "optimization"])
        shared_knowledge = [m for m in plan_memories if "dynamic-programming" in str(m.get("keywords", []))]

        assert len(shared_knowledge) >= 1

        # Verify cross-task knowledge transfer
        research_content = shared_knowledge[0].get("content", "")
        assert "memoization" in research_content.lower()
        assert "O(n)" in research_content

    async def test_task_memory_consistency_validation(
        self,
        integration_query_manager: QueryManager,
        integration_sample_task: str,
        integration_helper
    ):
        """
        Test consistency between task and memory systems.
        Context7 pattern: cross-system data consistency validation.
        """
        # Create multiple memory entries for same task
        memory_entries = []
        for i in range(3):
            memory = MemoryEntry(
                id=f"consistency-test-{i:03d}",
                content=f"Memory entry {i} for consistency testing with detailed implementation notes",
                content_type=ContentType.CONTEXT if i % 2 == 0 else ContentType.OUTPUT,
                task_id=integration_sample_task,
                keywords=["consistency", "testing", f"entry{i}"]
            )

            memory_id = await integration_query_manager.memory.store(
                content=memory.content,
                content_type=memory.content_type.value,
                keywords=memory.keywords,
                task_id=memory.task_id
            )
            memory_entries.append(memory_id)

        # Verify all memories reference valid task
        task = await integration_query_manager.tasks.get_by_id(integration_sample_task)
        assert task is not None

        # Verify memory-task relationships
        for memory_id in memory_entries:
            memory = await integration_query_manager.memory.get_by_id(memory_id)
            assert memory is not None
            assert memory.get("task_id") == integration_sample_task

        # Test cross-system consistency using helper
        consistency_check = await integration_helper.verify_data_consistency()
        assert consistency_check is True

    async def test_concurrent_task_memory_operations(
        self,
        integration_query_manager: QueryManager,
        integration_sample_plan: str
    ):
        """
        Test concurrent task and memory operations.
        Context7 pattern: concurrent operation safety across systems.
        """
        # Create phase for concurrent testing
        from devstream.database.schema import phases
        phase_id = integration_query_manager.tasks.generate_id()

        async with integration_query_manager.pool.write_transaction() as conn:
            await conn.execute(
                phases.insert().values(
                    id=phase_id,
                    plan_id=integration_sample_plan,
                    name="Concurrent Operations Phase",
                    description="Phase for testing concurrent task-memory operations",
                    objective="Validate concurrent operation safety",
                    sequence_order=1,
                    status="active",
                )
            )

        async def create_task_with_memory(index: int):
            # Create task
            task_id = await integration_query_manager.tasks.create(
                phase_id=phase_id,
                title=f"Concurrent Task {index}",
                description=f"Task {index} for concurrent testing",
                assigned_agent=f"agent-{index}",
                task_type="implementation",
                estimated_minutes=20,
            )

            # Create associated memory
            memory_id = await integration_query_manager.memory.store(
                content=f"Memory for concurrent task {index} with implementation details and context",
                content_type="context",
                keywords=["concurrent", f"task{index}", "implementation"],
                task_id=task_id
            )

            return task_id, memory_id

        # Run 8 concurrent task+memory creations
        tasks = [create_task_with_memory(i) for i in range(8)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 8

        # Verify all task-memory pairs were created correctly
        for task_id, memory_id in results:
            task = await integration_query_manager.tasks.get_by_id(task_id)
            memory = await integration_query_manager.memory.get_by_id(memory_id)

            assert task is not None
            assert memory is not None
            assert memory.get("task_id") == task_id

    async def test_task_workflow_memory_progression(
        self,
        integration_query_manager: QueryManager,
        integration_sample_plan: str
    ):
        """
        Test memory progression through task workflow stages.
        Context7 pattern: workflow state management with memory persistence.
        """
        # Create phase for workflow testing
        from devstream.database.schema import phases
        phase_id = integration_query_manager.tasks.generate_id()

        async with integration_query_manager.pool.write_transaction() as conn:
            await conn.execute(
                phases.insert().values(
                    id=phase_id,
                    plan_id=integration_sample_plan,
                    name="Workflow Memory Phase",
                    description="Phase for testing workflow memory progression",
                    objective="Track memory evolution through workflow",
                    sequence_order=1,
                    status="active",
                )
            )

        # Create task for workflow testing
        task_id = await integration_query_manager.tasks.create(
            phase_id=phase_id,
            title="Workflow Memory Progression Task",
            description="Task to test memory progression through workflow stages",
            assigned_agent="workflow-agent",
            task_type="implementation",
            estimated_minutes=90,
        )

        # Stage 1: Planning memory
        planning_id = await integration_query_manager.memory.store(
            content="Planning stage: Analyzing requirements and designing approach for fibonacci implementation",
            content_type="context",
            keywords=["planning", "requirements", "design", "fibonacci"],
            task_id=task_id
        )

        # Stage 2: Implementation memory
        implementation_id = await integration_query_manager.memory.store(
            content="Implementation stage: Coding recursive fibonacci with memoization optimization",
            content_type="code",
            keywords=["implementation", "coding", "recursive", "memoization"],
            task_id=task_id
        )

        # Stage 3: Testing memory
        testing_id = await integration_query_manager.memory.store(
            content="Testing stage: Validated fibonacci(10)=55, fibonacci(20)=6765. Performance meets O(n) target.",
            content_type="output",
            keywords=["testing", "validation", "performance", "results"],
            task_id=task_id
        )

        # Verify workflow memory progression
        task_memories = await integration_query_manager.memory.search_by_keywords(["fibonacci"])
        workflow_memories = [m for m in task_memories if m.get("task_id") == task_id]

        assert len(workflow_memories) >= 3

        # Verify progression stages are captured
        stages = set()
        for memory in workflow_memories:
            keywords = memory.get("keywords", [])
            if "planning" in keywords:
                stages.add("planning")
            elif "implementation" in keywords:
                stages.add("implementation")
            elif "testing" in keywords:
                stages.add("testing")

        assert "planning" in stages
        assert "implementation" in stages
        assert "testing" in stages

    async def test_memory_driven_task_prioritization(
        self,
        integration_query_manager: QueryManager,
        integration_sample_plan: str
    ):
        """
        Test task prioritization based on memory insights.
        Context7 pattern: memory-informed decision making for task management.
        """
        # Create phase for prioritization testing
        from devstream.database.schema import phases
        phase_id = integration_query_manager.tasks.generate_id()

        async with integration_query_manager.pool.write_transaction() as conn:
            await conn.execute(
                phases.insert().values(
                    id=phase_id,
                    plan_id=integration_sample_plan,
                    name="Memory-Driven Prioritization Phase",
                    description="Phase for testing memory-driven task prioritization",
                    objective="Optimize task order based on memory insights",
                    sequence_order=1,
                    status="active",
                )
            )

        # Create high-priority insights memory
        priority_memory_id = await integration_query_manager.memory.store(
            content="Critical insight: Algorithm optimization should be prioritized due to performance bottleneck in fibonacci calculation",
            content_type="decision",
            keywords=["critical", "optimization", "priority", "bottleneck", "fibonacci"],
            complexity_score=9
        )

        # Create tasks that could benefit from memory insights
        optimization_task_id = await integration_query_manager.tasks.create(
            phase_id=phase_id,
            title="Optimize Algorithm Performance",
            description="Task to optimize fibonacci algorithm based on performance analysis",
            assigned_agent="optimization-agent",
            task_type="optimization",
            estimated_minutes=120,
        )

        documentation_task_id = await integration_query_manager.tasks.create(
            phase_id=phase_id,
            title="Update Documentation",
            description="Task to update algorithm documentation",
            assigned_agent="documentation-agent",
            task_type="documentation",
            estimated_minutes=30,
        )

        # Verify memory insights can inform prioritization
        critical_memories = await integration_query_manager.memory.search_by_keywords(["critical", "priority"])

        assert len(critical_memories) >= 1

        # Verify optimization task exists for high-priority insight
        optimization_task = await integration_query_manager.tasks.get_by_id(optimization_task_id)
        assert optimization_task is not None
        assert "optimize" in optimization_task["title"].lower()

        # Verify memory-task relationship can guide prioritization
        priority_insight = critical_memories[0]
        assert "optimization" in str(priority_insight.get("keywords", []))
        assert priority_insight.get("complexity_score", 0) >= 8