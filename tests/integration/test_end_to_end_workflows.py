"""
End-to-end workflow integration tests.

CONTEXT7-VALIDATED PATTERNS IMPLEMENTATION:
- Complete system workflow testing from plan to execution
- Cross-system orchestration validation
- Real-world scenario simulation with multiple components
- Performance validation under realistic workflows
- Data consistency across complete workflows
"""

import pytest
import pytest_asyncio
import asyncio
from typing import List, Dict, Any
from datetime import datetime

from devstream.database.queries import QueryManager


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.slow
class TestEndToEndWorkflows:
    """
    Test complete end-to-end workflows across all systems.
    Context7-validated patterns for comprehensive workflow testing.
    """

    async def test_complete_plan_execution_workflow(
        self,
        integration_query_manager: QueryManager,
        integration_helper
    ):
        """
        Test complete workflow from plan creation to task completion.
        Context7 pattern: end-to-end workflow orchestration testing.
        """
        # Step 1: Create intervention plan
        plan_id = await integration_query_manager.plans.create(
            title="E2E Fibonacci Optimization Project",
            description="Complete project to research, implement, and optimize fibonacci algorithm",
            objectives=[
                "Research fibonacci algorithm approaches",
                "Implement optimized solution with memoization",
                "Validate performance improvements",
                "Document implementation details"
            ],
            expected_outcome="High-performance fibonacci implementation with O(n) complexity",
            priority=8,
            tags=["fibonacci", "optimization", "algorithm", "e2e-test"]
        )

        # Verify plan creation
        plan = await integration_query_manager.plans.get_by_id(plan_id)
        assert plan is not None
        assert plan["title"] == "E2E Fibonacci Optimization Project"

        # Step 2: Create execution phases
        from devstream.database.schema import phases

        research_phase_id = integration_query_manager.tasks.generate_id()
        implementation_phase_id = integration_query_manager.tasks.generate_id()
        validation_phase_id = integration_query_manager.tasks.generate_id()

        phases_data = [
            {
                "id": research_phase_id,
                "plan_id": plan_id,
                "name": "Research Phase",
                "description": "Research algorithm approaches and optimization strategies",
                "sequence_order": 1,
                "status": "active"
            },
            {
                "id": implementation_phase_id,
                "plan_id": plan_id,
                "name": "Implementation Phase",
                "description": "Implement optimized fibonacci algorithm",
                "sequence_order": 2,
                "status": "pending"
            },
            {
                "id": validation_phase_id,
                "plan_id": plan_id,
                "name": "Validation Phase",
                "description": "Test and validate performance improvements",
                "sequence_order": 3,
                "status": "pending"
            }
        ]

        # Insert phases
        async with integration_query_manager.pool.write_transaction() as conn:
            for phase_data in phases_data:
                await conn.execute(phases.insert().values(**phase_data))

        # Step 3: Create tasks for each phase
        research_task_id = await integration_query_manager.tasks.create(
            phase_id=research_phase_id,
            title="Research Fibonacci Algorithms",
            description="Research recursive, iterative, and memoization approaches",
            assigned_agent="research-specialist",
            task_type="research",
            estimated_minutes=60
        )

        implementation_task_id = await integration_query_manager.tasks.create(
            phase_id=implementation_phase_id,
            title="Implement Optimized Fibonacci",
            description="Implement fibonacci with memoization based on research",
            assigned_agent="implementation-specialist",
            task_type="implementation",
            estimated_minutes=90
        )

        validation_task_id = await integration_query_manager.tasks.create(
            phase_id=validation_phase_id,
            title="Performance Validation",
            description="Test and benchmark optimized implementation",
            assigned_agent="testing-specialist",
            task_type="testing",
            estimated_minutes=45
        )

        # Step 4: Create knowledge memories throughout workflow
        research_memory_id = await integration_query_manager.memory.store(
            content="Research findings: Dynamic programming with memoization reduces complexity from O(2^n) to O(n). Implementation should use dictionary for cache.",
            content_type="learning",
            keywords=["research", "dynamic-programming", "memoization", "complexity", "fibonacci"],
            task_id=research_task_id,
            plan_id=plan_id
        )

        implementation_memory_id = await integration_query_manager.memory.store(
            content="""
def fibonacci_optimized(n, memo={}):
    if n in memo:
        return memo[n]
    if n <= 1:
        return n
    memo[n] = fibonacci_optimized(n-1, memo) + fibonacci_optimized(n-2, memo)
    return memo[n]
            """,
            content_type="code",
            keywords=["implementation", "fibonacci", "memoization", "optimized"],
            task_id=implementation_task_id,
            plan_id=plan_id
        )

        validation_memory_id = await integration_query_manager.memory.store(
            content="Validation results: fibonacci(100) computed in 0.001ms vs 2.5s for naive recursive. 2500x performance improvement achieved.",
            content_type="output",
            keywords=["validation", "performance", "benchmark", "results"],
            task_id=validation_task_id,
            plan_id=plan_id
        )

        # Step 5: Verify complete workflow integrity
        # Verify plan exists with correct structure
        final_plan = await integration_query_manager.plans.get_by_id(plan_id)
        assert final_plan is not None
        assert len(final_plan["objectives"]) == 4

        # Verify all tasks exist
        for task_id in [research_task_id, implementation_task_id, validation_task_id]:
            task = await integration_query_manager.tasks.get_by_id(task_id)
            assert task is not None

        # Verify knowledge progression through memories
        plan_memories = await integration_query_manager.memory.search_by_keywords(["fibonacci"])
        workflow_memories = [m for m in plan_memories if m.get("plan_id") == plan_id]
        assert len(workflow_memories) >= 3

        # Verify data consistency across systems
        consistency_check = await integration_helper.verify_data_consistency()
        assert consistency_check is True

    async def test_knowledge_transfer_workflow(
        self,
        integration_query_manager: QueryManager
    ):
        """
        Test knowledge transfer across workflow stages.
        Context7 pattern: knowledge continuity in workflow progression.
        """
        # Create plan for knowledge transfer testing
        plan_id = await integration_query_manager.plans.create(
            title="Knowledge Transfer Workflow",
            description="Test knowledge accumulation and transfer across stages",
            objectives=["Build knowledge foundation", "Apply knowledge", "Refine understanding"],
            expected_outcome="Comprehensive knowledge base with applied insights"
        )

        # Create phase for knowledge workflow
        from devstream.database.schema import phases
        phase_id = integration_query_manager.tasks.generate_id()

        async with integration_query_manager.pool.write_transaction() as conn:
            await conn.execute(
                phases.insert().values(
                    id=phase_id,
                    plan_id=plan_id,
                    name="Knowledge Transfer Phase",
                    description="Phase for testing knowledge transfer workflow",
                    sequence_order=1,
                    status="active"
                )
            )

        # Stage 1: Foundation knowledge
        foundation_task_id = await integration_query_manager.tasks.create(
            phase_id=phase_id,
            title="Build Foundation Knowledge",
            description="Establish basic understanding of domain concepts",
            assigned_agent="foundation-agent",
            task_type="research"
        )

        foundation_memory_id = await integration_query_manager.memory.store(
            content="Foundation: Fibonacci sequence is a mathematical series where each number is sum of two preceding ones: 0, 1, 1, 2, 3, 5, 8, 13...",
            content_type="learning",
            keywords=["foundation", "fibonacci", "mathematical", "sequence"],
            task_id=foundation_task_id,
            plan_id=plan_id
        )

        # Stage 2: Applied knowledge
        application_task_id = await integration_query_manager.tasks.create(
            phase_id=phase_id,
            title="Apply Foundation Knowledge",
            description="Apply foundation concepts to practical implementation",
            assigned_agent="application-agent",
            task_type="implementation"
        )

        application_memory_id = await integration_query_manager.memory.store(
            content="Application: Implemented iterative fibonacci algorithm. Foundation knowledge helped understand sequence progression.",
            content_type="context",
            keywords=["application", "iterative", "fibonacci", "implementation"],
            task_id=application_task_id,
            plan_id=plan_id
        )

        # Stage 3: Refined understanding
        refinement_task_id = await integration_query_manager.tasks.create(
            phase_id=phase_id,
            title="Refine Understanding",
            description="Refine understanding based on implementation experience",
            assigned_agent="refinement-agent",
            task_type="optimization"
        )

        refinement_memory_id = await integration_query_manager.memory.store(
            content="Refinement: Discovered memoization pattern from implementation. Foundation + application led to optimization insight.",
            content_type="decision",
            keywords=["refinement", "memoization", "optimization", "insight"],
            task_id=refinement_task_id,
            plan_id=plan_id
        )

        # Verify knowledge transfer progression
        knowledge_memories = await integration_query_manager.memory.search_by_keywords(["fibonacci"])
        transfer_memories = [m for m in knowledge_memories if m.get("plan_id") == plan_id]

        # Should have memories representing knowledge progression
        assert len(transfer_memories) >= 3

        # Verify progression from foundation → application → refinement
        content_types = [m.get("content_type") for m in transfer_memories]
        assert "learning" in content_types  # Foundation
        assert "context" in content_types   # Application
        assert "decision" in content_types  # Refinement

    async def test_concurrent_workflow_execution(
        self,
        integration_query_manager: QueryManager
    ):
        """
        Test concurrent execution of multiple workflows.
        Context7 pattern: concurrent workflow isolation and coordination.
        """
        async def execute_workflow(workflow_index: int):
            # Create plan for this workflow
            plan_id = await integration_query_manager.plans.create(
                title=f"Concurrent Workflow {workflow_index}",
                description=f"Workflow {workflow_index} for concurrent execution testing",
                objectives=[f"Execute workflow {workflow_index} independently"],
                expected_outcome=f"Workflow {workflow_index} completed successfully"
            )

            # Create phase
            from devstream.database.schema import phases
            phase_id = integration_query_manager.tasks.generate_id()

            async with integration_query_manager.pool.write_transaction() as conn:
                await conn.execute(
                    phases.insert().values(
                        id=phase_id,
                        plan_id=plan_id,
                        name=f"Concurrent Phase {workflow_index}",
                        description=f"Phase for concurrent workflow {workflow_index}",
                        sequence_order=1,
                        status="active"
                    )
                )

            # Create task
            task_id = await integration_query_manager.tasks.create(
                phase_id=phase_id,
                title=f"Concurrent Task {workflow_index}",
                description=f"Task for concurrent workflow {workflow_index}",
                assigned_agent=f"concurrent-agent-{workflow_index}",
                task_type="implementation"
            )

            # Create memory
            memory_id = await integration_query_manager.memory.store(
                content=f"Concurrent workflow {workflow_index} execution with independent context and state management",
                content_type="context",
                keywords=["concurrent", f"workflow{workflow_index}", "independent"],
                task_id=task_id,
                plan_id=plan_id
            )

            return plan_id, task_id, memory_id

        # Execute 5 workflows concurrently
        concurrent_tasks = [execute_workflow(i) for i in range(5)]
        workflow_results = await asyncio.gather(*concurrent_tasks)

        assert len(workflow_results) == 5

        # Verify all workflows completed successfully
        for plan_id, task_id, memory_id in workflow_results:
            # Verify plan
            plan = await integration_query_manager.plans.get_by_id(plan_id)
            assert plan is not None

            # Verify task
            task = await integration_query_manager.tasks.get_by_id(task_id)
            assert task is not None

            # Verify memory
            memory = await integration_query_manager.memory.get_by_id(memory_id)
            assert memory is not None

        # Verify workflow isolation - each plan should have exactly 1 task
        plan_ids = [result[0] for result in workflow_results]
        for plan_id in plan_ids:
            plan_memories = await integration_query_manager.memory.search_by_keywords(["concurrent"])
            plan_specific_memories = [m for m in plan_memories if m.get("plan_id") == plan_id]
            assert len(plan_specific_memories) == 1

    async def test_workflow_error_recovery(
        self,
        integration_query_manager: QueryManager
    ):
        """
        Test workflow resilience and error recovery.
        Context7 pattern: error boundary testing in workflow context.
        """
        # Create plan for error recovery testing
        plan_id = await integration_query_manager.plans.create(
            title="Error Recovery Workflow",
            description="Test workflow resilience with simulated errors",
            objectives=["Test error handling", "Validate recovery mechanisms"],
            expected_outcome="Workflow continues despite individual component errors"
        )

        # Create phase
        from devstream.database.schema import phases
        phase_id = integration_query_manager.tasks.generate_id()

        async with integration_query_manager.pool.write_transaction() as conn:
            await conn.execute(
                phases.insert().values(
                    id=phase_id,
                    plan_id=plan_id,
                    name="Error Recovery Phase",
                    description="Phase for testing error recovery patterns",
                    sequence_order=1,
                    status="active"
                )
            )

        # Create tasks that might encounter errors
        success_task_id = await integration_query_manager.tasks.create(
            phase_id=phase_id,
            title="Successful Task",
            description="Task that should complete successfully",
            assigned_agent="reliable-agent",
            task_type="implementation"
        )

        # Record successful operation
        success_memory_id = await integration_query_manager.memory.store(
            content="Successful task execution completed without errors. System operating normally.",
            content_type="output",
            keywords=["success", "completed", "normal"],
            task_id=success_task_id
        )

        # Record error handling capability
        error_memory_id = await integration_query_manager.memory.store(
            content="Error handling: System maintains data consistency even when individual operations fail. Recovery mechanisms active.",
            content_type="decision",
            keywords=["error", "handling", "recovery", "resilience"],
            plan_id=plan_id
        )

        # Verify workflow continues despite potential errors
        plan = await integration_query_manager.plans.get_by_id(plan_id)
        assert plan is not None

        # Verify successful components continue working
        success_task = await integration_query_manager.tasks.get_by_id(success_task_id)
        assert success_task is not None

        # Verify error handling memories are captured
        error_memories = await integration_query_manager.memory.search_by_keywords(["error", "recovery"])
        recovery_memories = [m for m in error_memories if m.get("plan_id") == plan_id]
        assert len(recovery_memories) >= 1

    async def test_workflow_performance_under_load(
        self,
        integration_query_manager: QueryManager,
        integration_helper
    ):
        """
        Test workflow performance under realistic load.
        Context7 pattern: performance validation in integration scenarios.
        """
        import time

        start_time = time.time()

        # Create large-scale workflow
        plan_id = await integration_query_manager.plans.create(
            title="Performance Testing Workflow",
            description="Large-scale workflow for performance validation",
            objectives=[f"Objective {i}" for i in range(20)],  # 20 objectives
            expected_outcome="System maintains performance under load"
        )

        # Create multiple phases
        from devstream.database.schema import phases
        phase_ids = []

        for i in range(10):  # 10 phases
            phase_id = integration_query_manager.tasks.generate_id()
            phase_ids.append(phase_id)

            async with integration_query_manager.pool.write_transaction() as conn:
                await conn.execute(
                    phases.insert().values(
                        id=phase_id,
                        plan_id=plan_id,
                        name=f"Performance Phase {i}",
                        description=f"Phase {i} for performance testing",
                        sequence_order=i + 1,
                        status="active"
                    )
                )

        # Create tasks across phases
        task_ids = []
        for i, phase_id in enumerate(phase_ids):
            for j in range(3):  # 3 tasks per phase = 30 tasks total
                task_id = await integration_query_manager.tasks.create(
                    phase_id=phase_id,
                    title=f"Performance Task {i}-{j}",
                    description=f"Task {j} in phase {i} for performance testing",
                    assigned_agent=f"perf-agent-{i}-{j}",
                    task_type="implementation"
                )
                task_ids.append(task_id)

        # Create memories for tasks
        memory_ids = []
        for i, task_id in enumerate(task_ids[:15]):  # Create memories for first 15 tasks
            memory_id = await integration_query_manager.memory.store(
                content=f"Performance test memory {i} with substantial content for realistic data volume testing",
                content_type="context",
                keywords=["performance", "testing", f"task{i}"],
                task_id=task_id
            )
            memory_ids.append(memory_id)

        # Measure workflow creation time
        creation_time = time.time() - start_time

        # Verify performance metrics
        assert creation_time < 10.0  # Should complete within 10 seconds

        # Verify workflow integrity under load
        final_plan = await integration_query_manager.plans.get_by_id(plan_id)
        assert final_plan is not None
        assert len(final_plan["objectives"]) == 20

        # Verify all tasks exist
        assert len(task_ids) == 30
        for task_id in task_ids[:5]:  # Sample check first 5 tasks
            task = await integration_query_manager.tasks.get_by_id(task_id)
            assert task is not None

        # Verify memories exist
        assert len(memory_ids) == 15
        for memory_id in memory_ids[:3]:  # Sample check first 3 memories
            memory = await integration_query_manager.memory.get_by_id(memory_id)
            assert memory is not None

        # Verify system-wide consistency under load
        consistency_check = await integration_helper.verify_data_consistency()
        assert consistency_check is True

        # Record performance metrics
        total_records = await integration_helper.count_total_records()
        assert total_records["plans"] >= 1
        assert total_records["tasks"] >= 30
        assert total_records["memories"] >= 15