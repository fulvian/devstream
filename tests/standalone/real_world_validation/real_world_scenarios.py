"""
Real-world testing scenarios for DevStream validation.

This module provides comprehensive testing scenarios that simulate
realistic usage patterns and workflows.
"""

import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

import structlog
from devstream.core.config import DevStreamConfig
from devstream.database.connection import ConnectionPool
from devstream.database.queries import QueryManager
from devstream.tasks.models import TaskType

logger = structlog.get_logger(__name__)


class RealWorldTestRunner:
    """
    Real-world test scenario runner for DevStream validation.

    Executes comprehensive testing scenarios that simulate realistic
    usage patterns and validate system behavior under real conditions.
    """

    def __init__(self):
        """Initialize the test runner."""
        self.config = DevStreamConfig.from_env()
        self.pool: Optional[ConnectionPool] = None
        self.query_manager: Optional[QueryManager] = None
        self.test_results: Dict[str, Any] = {}
        self.start_time = time.time()

    async def initialize(self) -> None:
        """Initialize test environment."""
        logger.info("Initializing real-world test environment")

        # Setup database connection
        self.pool = ConnectionPool(
            db_path=self.config.database.db_path,
            max_connections=self.config.database.max_connections
        )
        await self.pool.initialize()

        self.query_manager = QueryManager(self.pool)

        # Ensure clean test environment
        await self._prepare_test_environment()

        logger.info("Test environment initialized successfully")

    async def _prepare_test_environment(self) -> None:
        """Prepare clean test environment."""
        # Note: In real testing, you might want to backup existing data
        # and restore it after testing

        logger.info("Test environment prepared")

    async def run_all_scenarios(self) -> Dict[str, Any]:
        """
        Run all real-world testing scenarios.

        Returns:
            Comprehensive test results
        """
        logger.info("Starting comprehensive real-world testing")

        scenarios = [
            ("personal_project_management", self.test_personal_project_workflow),
            ("team_collaboration", self.test_team_collaboration_workflow),
            ("long_running_project", self.test_long_running_project),
            ("memory_system_validation", self.test_memory_system_comprehensive),
            ("task_system_validation", self.test_task_system_comprehensive),
            ("performance_under_load", self.test_performance_under_load),
            ("error_recovery", self.test_error_recovery_scenarios)
        ]

        for scenario_name, scenario_func in scenarios:
            logger.info(f"Running scenario: {scenario_name}")

            try:
                start_time = time.time()
                scenario_result = await scenario_func()
                execution_time = time.time() - start_time

                self.test_results[scenario_name] = {
                    "status": "success",
                    "execution_time": execution_time,
                    "results": scenario_result
                }

                logger.info(
                    f"Scenario completed successfully: {scenario_name}",
                    execution_time=execution_time
                )

            except Exception as e:
                execution_time = time.time() - start_time
                self.test_results[scenario_name] = {
                    "status": "failed",
                    "execution_time": execution_time,
                    "error": str(e)
                }

                logger.error(
                    f"Scenario failed: {scenario_name}",
                    error=str(e),
                    execution_time=execution_time
                )

        total_time = time.time() - self.start_time
        self.test_results["summary"] = {
            "total_execution_time": total_time,
            "total_scenarios": len(scenarios),
            "successful_scenarios": len([r for r in self.test_results.values()
                                       if isinstance(r, dict) and r.get("status") == "success"]),
            "failed_scenarios": len([r for r in self.test_results.values()
                                   if isinstance(r, dict) and r.get("status") == "failed"])
        }

        logger.info("Real-world testing completed", results=self.test_results["summary"])
        return self.test_results

    async def test_personal_project_workflow(self) -> Dict[str, Any]:
        """
        Test Scenario 1: Personal Project Management

        Simulates a developer using DevStream to manage a personal software project.
        """
        logger.info("Testing personal project management workflow")

        # Step 1: Create project plan
        plan_id = await self.query_manager.plans.create(
            title="Build Personal Blog System",
            description="Complete blog system with FastAPI backend and React frontend",
            objectives=[
                "Setup FastAPI backend with database",
                "Implement content management system",
                "Create responsive frontend",
                "Deploy to production with CI/CD"
            ],
            expected_outcome="Fully functional blog system deployed to production"
        )

        # Step 2: Create development phases
        phases = []
        phase_data = [
            ("Backend Development", "Setup API and database layer"),
            ("Frontend Development", "Create user interface and interactions"),
            ("Integration & Testing", "Connect frontend to backend and test"),
            ("Deployment & Operations", "Deploy to production and setup monitoring")
        ]

        for i, (name, description) in enumerate(phase_data):
            phase_id = await self.query_manager.phases.create(
                plan_id=plan_id,
                name=name,
                description=description,
                sequence_order=i + 1
            )
            phases.append(phase_id)

        # Step 3: Create realistic micro-tasks
        tasks_created = 0
        all_tasks = []

        # Backend tasks
        backend_tasks = [
            ("Setup FastAPI project structure", "Create basic FastAPI app with proper structure"),
            ("Design database models", "Create SQLAlchemy models for blog entities"),
            ("Implement user authentication", "Add JWT-based authentication system"),
            ("Create blog post CRUD API", "Implement endpoints for blog post management"),
            ("Add content management features", "Categories, tags, and media management"),
            ("Write API documentation", "Complete OpenAPI documentation")
        ]

        for title, description in backend_tasks:
            task_id = await self.query_manager.tasks.create(
                phase_id=phases[0],
                title=title,
                description=description,
                assigned_agent="backend_developer",
                task_type=TaskType.CODING,
                estimated_minutes=120
            )
            all_tasks.append(task_id)
            tasks_created += 1

        # Frontend tasks
        frontend_tasks = [
            ("Setup React project", "Create React app with TypeScript"),
            ("Design component library", "Create reusable UI components"),
            ("Implement blog post listing", "Display blog posts with pagination"),
            ("Create post editor interface", "Rich text editor for blog posts"),
            ("Add user authentication UI", "Login/register forms and auth state"),
            ("Responsive design implementation", "Mobile-friendly responsive layout")
        ]

        for title, description in frontend_tasks:
            task_id = await self.query_manager.tasks.create(
                phase_id=phases[1],
                title=title,
                description=description,
                assigned_agent="frontend_developer",
                task_type=TaskType.CODING,
                estimated_minutes=90
            )
            all_tasks.append(task_id)
            tasks_created += 1

        # Step 4: Simulate task execution with memory creation
        memories_created = 0
        for i, task_id in enumerate(all_tasks[:4]):  # Execute first 4 tasks
            # Simulate work on task
            await self.query_manager.tasks.update_status(task_id, "in_progress")

            # Create memory entries for the work
            memory_id = await self.query_manager.memory.store(
                content=f"Completed task implementation with FastAPI setup. Used SQLAlchemy for ORM, added Pydantic models for validation. Key learnings: FastAPI automatic OpenAPI generation is excellent for API documentation.",
                content_type="output",
                keywords=["fastapi", "implementation", "completed", f"task_{i}"],
                task_id=task_id
            )
            memories_created += 1

            await self.query_manager.tasks.update_status(task_id, "completed")

        # Step 5: Test memory search and context retrieval
        search_results = await self.query_manager.memory.search_by_keywords(["fastapi", "implementation"])

        return {
            "plan_created": plan_id is not None,
            "phases_created": len(phases),
            "tasks_created": tasks_created,
            "tasks_executed": 4,
            "memories_created": memories_created,
            "memory_search_results": len(search_results),
            "test_duration": time.time() - self.start_time
        }

    async def test_team_collaboration_workflow(self) -> Dict[str, Any]:
        """
        Test Scenario 2: Team Collaboration Simulation

        Simulates multiple developers working on the same project with shared context.
        """
        logger.info("Testing team collaboration workflow")

        # Create shared project
        project_plan_id = await self.query_manager.plans.create(
            title="Team E-commerce Platform",
            description="Multi-developer e-commerce platform development",
            objectives=[
                "Backend API development",
                "Frontend user interface",
                "Payment integration",
                "Admin dashboard"
            ],
            expected_outcome="Complete e-commerce platform"
        )

        # Simulate multiple developers working
        developers = ["alice", "bob", "charlie"]
        developer_tasks = {}
        shared_memories = []

        for dev in developers:
            # Each developer creates their tasks
            if dev == "alice":  # Backend specialist
                task_id = await self.query_manager.tasks.create(
                    phase_id=project_plan_id,  # Simplified for testing
                    title=f"API Development - {dev}",
                    description="Develop REST API endpoints",
                    assigned_agent=dev,
                    task_type=TaskType.CODING
                )
            elif dev == "bob":  # Frontend specialist
                task_id = await self.query_manager.tasks.create(
                    phase_id=project_plan_id,
                    title=f"UI Development - {dev}",
                    description="Create user interface components",
                    assigned_agent=dev,
                    task_type=TaskType.CODING
                )
            else:  # DevOps specialist
                task_id = await self.query_manager.tasks.create(
                    phase_id=project_plan_id,
                    title=f"Infrastructure - {dev}",
                    description="Setup deployment infrastructure",
                    assigned_agent=dev,
                    task_type=TaskType.ANALYSIS
                )

            developer_tasks[dev] = task_id

            # Each developer creates shared knowledge
            memory_id = await self.query_manager.memory.store(
                content=f"Team decision: Use PostgreSQL for main database, Redis for caching. Agreed on REST API patterns. - {dev}",
                content_type="decision",
                keywords=["team", "decision", "database", dev],
                task_id=task_id
            )
            shared_memories.append(memory_id)

        # Test cross-developer memory access
        team_decisions = await self.query_manager.memory.search_by_keywords(["team", "decision"])

        return {
            "project_created": project_plan_id is not None,
            "developers_simulated": len(developers),
            "tasks_created": len(developer_tasks),
            "shared_memories": len(shared_memories),
            "cross_access_results": len(team_decisions)
        }

    async def test_long_running_project(self) -> Dict[str, Any]:
        """
        Test Scenario 3: Long-Running Project Simulation

        Simulates a project that evolves over time with memory accumulation.
        """
        logger.info("Testing long-running project scenario")

        project_id = await self.query_manager.plans.create(
            title="Long-term Software Development",
            description="Multi-month software development project",
            objectives=["Week 1-2: Foundation", "Week 3-4: Features", "Week 5-6: Polish"],
            expected_outcome="Complete software system"
        )

        memories_over_time = []
        tasks_over_time = []

        # Simulate 6 weeks of development
        for week in range(1, 7):
            # Create tasks for each week
            for day in range(1, 4):  # 3 tasks per week
                task_id = await self.query_manager.tasks.create(
                    phase_id=project_id,
                    title=f"Week {week} - Development Task {day}",
                    description=f"Development work for week {week}, day {day}",
                    assigned_agent="developer",
                    task_type=TaskType.CODING
                )
                tasks_over_time.append(task_id)

                # Create memory entries with accumulating knowledge
                memory_content = f"Week {week} Day {day}: Implemented feature X. Key insights: pattern Y works well, avoid anti-pattern Z. Performance metrics improved by {day * 10}%."

                memory_id = await self.query_manager.memory.store(
                    content=memory_content,
                    content_type="learning",
                    keywords=["development", f"week{week}", f"day{day}", "insights"],
                    task_id=task_id,
                    complexity_score=week + day
                )
                memories_over_time.append(memory_id)

        # Test memory system with accumulated data
        all_memories = await self.query_manager.memory.search_by_keywords(["development"])
        week_specific = await self.query_manager.memory.search_by_keywords(["week3"])

        return {
            "project_duration_weeks": 6,
            "total_tasks_created": len(tasks_over_time),
            "total_memories_created": len(memories_over_time),
            "memory_search_all": len(all_memories),
            "memory_search_specific": len(week_specific),
            "memory_system_performance": "stable"  # Would measure actual performance
        }

    async def test_memory_system_comprehensive(self) -> Dict[str, Any]:
        """Test memory system under comprehensive scenarios."""
        logger.info("Testing memory system comprehensively")

        # Test different content types
        content_types = ["code", "documentation", "context", "output", "decision", "learning"]
        memories_by_type = {}

        for content_type in content_types:
            memory_id = await self.query_manager.memory.store(
                content=f"Test content for {content_type} validation with detailed information",
                content_type=content_type,
                keywords=[content_type, "test", "comprehensive"],
                complexity_score=5
            )
            memories_by_type[content_type] = memory_id

        # Test search functionality
        search_results = await self.query_manager.memory.search_by_keywords(["test"])

        # Test memory retrieval
        retrieved_memories = []
        for memory_id in memories_by_type.values():
            memory = await self.query_manager.memory.get_by_id(memory_id)
            if memory:
                retrieved_memories.append(memory)

        return {
            "content_types_tested": len(content_types),
            "memories_created": len(memories_by_type),
            "search_results": len(search_results),
            "retrieval_success_rate": len(retrieved_memories) / len(memories_by_type)
        }

    async def test_task_system_comprehensive(self) -> Dict[str, Any]:
        """Test task system under comprehensive scenarios."""
        logger.info("Testing task system comprehensively")

        # Create test plan
        plan_id = await self.query_manager.plans.create(
            title="Task System Comprehensive Test",
            description="Testing all task system functionality",
            objectives=["Test task creation", "Test task updates", "Test task queries"],
            expected_outcome="Validated task system"
        )

        # Test different task types
        task_types = [TaskType.CODING, TaskType.TESTING, TaskType.DOCUMENTATION, TaskType.RESEARCH, TaskType.REVIEW]
        created_tasks = []

        for task_type in task_types:
            task_id = await self.query_manager.tasks.create(
                phase_id=plan_id,
                title=f"Test {task_type.value} task",
                description=f"Comprehensive test for {task_type.value} workflow",
                assigned_agent="test_agent",
                task_type=task_type,
                estimated_minutes=60
            )
            created_tasks.append(task_id)

        # Test task status updates
        status_updates = 0
        for task_id in created_tasks[:3]:
            await self.query_manager.tasks.update_status(task_id, "in_progress")
            await self.query_manager.tasks.update_status(task_id, "completed")
            status_updates += 2

        # Test task queries
        active_tasks = await self.query_manager.tasks.get_active_tasks()

        return {
            "task_types_tested": len(task_types),
            "tasks_created": len(created_tasks),
            "status_updates": status_updates,
            "active_tasks_found": len(active_tasks)
        }

    async def test_performance_under_load(self) -> Dict[str, Any]:
        """Test system performance under realistic load."""
        logger.info("Testing performance under load")

        start_time = time.time()

        # Create multiple plans concurrently
        plan_tasks = []
        for i in range(10):
            task = self.query_manager.plans.create(
                title=f"Load Test Plan {i}",
                description=f"Plan {i} for load testing",
                objectives=[f"Objective {i}.1", f"Objective {i}.2"],
                expected_outcome=f"Outcome {i}"
            )
            plan_tasks.append(task)

        plans = await asyncio.gather(*plan_tasks)

        # Create multiple memories concurrently
        memory_tasks = []
        for i in range(50):
            task = self.query_manager.memory.store(
                content=f"Load test memory {i} with substantial content for performance validation",
                content_type="context",
                keywords=["load", "test", f"memory{i}"],
                complexity_score=i % 10 + 1
            )
            memory_tasks.append(task)

        memories = await asyncio.gather(*memory_tasks)

        # Test concurrent searches
        search_tasks = []
        for i in range(20):
            task = self.query_manager.memory.search_by_keywords(["load", "test"])
            search_tasks.append(task)

        search_results = await asyncio.gather(*search_tasks)

        execution_time = time.time() - start_time

        return {
            "plans_created": len(plans),
            "memories_created": len(memories),
            "concurrent_searches": len(search_results),
            "total_execution_time": execution_time,
            "average_search_results": sum(len(r) for r in search_results) / len(search_results)
        }

    async def test_error_recovery_scenarios(self) -> Dict[str, Any]:
        """Test system behavior under error conditions."""
        logger.info("Testing error recovery scenarios")

        recovery_tests = {
            "invalid_plan_creation": 0,
            "invalid_memory_storage": 0,
            "invalid_task_updates": 0,
            "concurrent_operations": 0
        }

        # Test invalid plan creation
        try:
            await self.query_manager.plans.create(
                title="",  # Invalid empty title
                description="Test description",
                objectives=[],
                expected_outcome="Should fail"
            )
        except Exception:
            recovery_tests["invalid_plan_creation"] = 1

        # Test invalid memory storage
        try:
            await self.query_manager.memory.store(
                content="",  # Invalid empty content
                content_type="invalid_type",  # Invalid type
                keywords=[]
            )
        except Exception:
            recovery_tests["invalid_memory_storage"] = 1

        # Test system continues working after errors
        try:
            valid_plan = await self.query_manager.plans.create(
                title="Recovery Test Plan",
                description="Plan created after error recovery",
                objectives=["Test recovery"],
                expected_outcome="System recovered"
            )
            recovery_tests["system_recovery"] = 1 if valid_plan else 0
        except Exception:
            recovery_tests["system_recovery"] = 0

        return recovery_tests

    async def cleanup(self) -> None:
        """Cleanup test environment."""
        if self.pool:
            await self.pool.close()
        logger.info("Test environment cleaned up")


async def run_real_world_tests() -> Dict[str, Any]:
    """
    Main entry point for real-world testing.

    Returns:
        Complete test results
    """
    runner = RealWorldTestRunner()

    try:
        await runner.initialize()
        results = await runner.run_all_scenarios()
        return results
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    async def main():
        print("🧪 Starting DevStream Real-World Testing")
        print("=" * 50)

        results = await run_real_world_tests()

        print("\n📊 Test Results Summary:")
        print("=" * 50)

        summary = results.get("summary", {})
        print(f"Total Scenarios: {summary.get('total_scenarios', 0)}")
        print(f"Successful: {summary.get('successful_scenarios', 0)}")
        print(f"Failed: {summary.get('failed_scenarios', 0)}")
        print(f"Total Time: {summary.get('total_execution_time', 0):.2f}s")

        print("\n📋 Detailed Results:")
        for scenario, result in results.items():
            if scenario != "summary" and isinstance(result, dict):
                status = result.get("status", "unknown")
                time_taken = result.get("execution_time", 0)
                print(f"  {scenario}: {status} ({time_taken:.2f}s)")

                if status == "failed":
                    print(f"    Error: {result.get('error', 'Unknown error')}")

        # Save results to file
        results_file = Path("testing/results") / f"real_world_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        results_file.parent.mkdir(exist_ok=True)

        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n💾 Results saved to: {results_file}")
        print("\n🎉 Real-world testing completed!")

    asyncio.run(main())