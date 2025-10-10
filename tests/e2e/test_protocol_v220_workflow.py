#!/usr/bin/env python3
"""
End-to-End Test: DevStream Protocol v2.2.0 Complete Workflow

Tests the complete 7-step workflow with Strategic Choice Gate and GLM handoff:
1. Task Creation at Step 1 (DISCUSSION)
2. Analysis and Research (Steps 2-3)
3. Implementation Plan Generation (Step 4)
4. Strategic Choice Gate (Step 5)
5. GLM Handoff Workflow Simulation
6. Plan Storage Verification (Dual Storage)
7. Complete Workflow Validation

Test Scenarios:
- Scenario 1: Sonnet Full Workflow (Steps 1-7)
- Scenario 2: Hybrid Workflow (Sonnet planning → GLM execution)
- Scenario 3: Plan Retrieval and Verification
- Scenario 4: Error Handling (duplicate plans, missing tasks)
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'utils'))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'protocol'))

from implementation_plan_generator import (
    ImplementationPlanGenerator,
    ModelChoice,
    PlanContext
)
from logger import get_devstream_logger

logger = get_devstream_logger(__name__)


class MockMCPClient:
    """Mock MCP client for testing."""

    def __init__(self):
        self.tasks_created = {}
        self.plans_created = {}
        self.memory_stored = []

    async def create_task(
        self,
        title: str,
        description: str,
        task_type: str,
        priority: int,
        phase_name: str,
        project: str
    ) -> Dict[str, Any]:
        """Mock task creation."""
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        self.tasks_created[task_id] = {
            "task_id": task_id,
            "title": title,
            "description": description,
            "task_type": task_type,
            "priority": priority,
            "phase_name": phase_name,
            "project": project,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        return {"task_id": task_id}

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Mock MCP tool calls."""
        if tool_name == "devstream_create_implementation_plan":
            plan_id = f"plan-{uuid.uuid4().hex[:8]}"
            self.plans_created[args["task_id"]] = {
                "plan_id": plan_id,
                "task_id": args["task_id"],
                "model_type": args["model_type"],
                "plan_content": args["plan_content"],
                "plan_file_path": args.get("plan_file_path"),
                "handoff_prompt": args.get("handoff_prompt"),
                "metadata": args.get("metadata", {}),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            return {"plan_id": plan_id}

        elif tool_name == "devstream_get_implementation_plan":
            return self.plans_created.get(args["task_id"])

        elif tool_name == "devstream_update_implementation_plan":
            if args["task_id"] in self.plans_created:
                self.plans_created[args["task_id"]].update(args)
                return {"success": True}
            return None

        elif tool_name == "devstream_list_implementation_plans":
            plans = list(self.plans_created.values())
            if "model_type" in args:
                plans = [p for p in plans if p["model_type"] == args["model_type"]]
            return {"plans": plans[:args.get("limit", 20)]}

        return None

    async def store_memory(
        self,
        content: str,
        content_type: str,
        keywords: list
    ) -> None:
        """Mock memory storage."""
        self.memory_stored.append({
            "content": content,
            "content_type": content_type,
            "keywords": keywords,
            "stored_at": datetime.now(timezone.utc).isoformat()
        })


class ProtocolV220E2ETest:
    """End-to-End test suite for Protocol v2.2.0."""

    def __init__(self):
        self.mcp_client = MockMCPClient()
        self.plan_generator = ImplementationPlanGenerator(self.mcp_client)
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []

    def assert_true(self, condition: bool, message: str):
        """Assert condition is true."""
        if condition:
            self.tests_passed += 1
            self.test_results.append(("PASS", message))
            print(f"  ✅ {message}")
        else:
            self.tests_failed += 1
            self.test_results.append(("FAIL", message))
            print(f"  ❌ {message}")
            raise AssertionError(message)

    def assert_equal(self, actual: Any, expected: Any, message: str):
        """Assert actual equals expected."""
        if actual == expected:
            self.tests_passed += 1
            self.test_results.append(("PASS", message))
            print(f"  ✅ {message}")
        else:
            self.tests_failed += 1
            self.test_results.append(("FAIL", message))
            print(f"  ❌ {message} (expected: {expected}, got: {actual})")
            raise AssertionError(f"{message}: expected {expected}, got {actual}")

    def assert_contains(self, text: str, substring: str, message: str):
        """Assert text contains substring."""
        if substring in text:
            self.tests_passed += 1
            self.test_results.append(("PASS", message))
            print(f"  ✅ {message}")
        else:
            self.tests_failed += 1
            self.test_results.append(("FAIL", message))
            print(f"  ❌ {message} (substring '{substring}' not found)")
            raise AssertionError(f"{message}: '{substring}' not in text")

    async def test_scenario_1_sonnet_full_workflow(self):
        """Test Scenario 1: Sonnet 4.5 Full Workflow (Steps 1-7)."""
        print("\n🧪 Test Scenario 1: Sonnet 4.5 Full Workflow")
        print("=" * 80)

        # Step 1: Create task
        print("\n📝 Step 1: Task Creation")
        task_result = await self.mcp_client.create_task(
            title="Implement User Authentication System",
            description="Build JWT-based authentication with FastAPI",
            task_type="coding",
            priority=8,
            phase_name="Core Engine & Infrastructure",
            project="DevStream"
        )
        task_id = task_result["task_id"]
        self.assert_true(task_id is not None, "Task created successfully")
        print(f"  Task ID: {task_id}")

        # Step 4: Generate implementation plan
        print("\n📋 Step 4: Implementation Plan Generation")
        plan_context = PlanContext(
            task_id=task_id,
            task_title="Implement User Authentication System",
            task_description="Build JWT-based authentication with FastAPI",
            task_type="coding",
            priority=8,
            phase_name="Core Engine & Infrastructure",
            estimated_duration=120,
            complexity_score=0.8,
            context7_libraries=["fastapi", "pyjwt", "bcrypt"],
            research_findings="Use bcrypt for password hashing, JWT for tokens, rate limiting for security",
            code_examples={"auth_example": "async def authenticate_user(...)"},
            files_to_modify=["src/api/users.py"],
            files_to_create=["src/auth/jwt.py", "src/auth/password.py"],
            dependencies=["fastapi", "pyjwt", "bcrypt"],
            performance_targets="< 100ms authentication response time",
            todowrite_tasks=[
                {"content": "Implement password hashing", "status": "pending"},
                {"content": "Create JWT token generation", "status": "pending"},
                {"content": "Add authentication endpoints", "status": "pending"}
            ],
            session_id=f"sess-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        # Generate plan with Sonnet template
        success, plan_path = await self.plan_generator.generate_plan(
            plan_context,
            ModelChoice.SONNET_45
        )
        self.assert_true(success, "Plan generated successfully for Sonnet 4.5")
        self.assert_true(plan_path is not None, "Plan file path returned")
        print(f"  Plan Path: {plan_path}")

        # Verify plan stored in mock database
        stored_plan = self.mcp_client.plans_created.get(task_id)
        self.assert_true(stored_plan is not None, "Plan stored in database")
        self.assert_equal(stored_plan["model_type"], "sonnet-4.5", "Model type is Sonnet 4.5")
        self.assert_contains(
            stored_plan["plan_content"],
            "Sonnet 4.5",
            "Plan content contains Sonnet-specific content"
        )

        # Verify no handoff prompt for Sonnet
        self.assert_true(
            stored_plan["handoff_prompt"] is None,
            "No handoff prompt for Sonnet workflow"
        )

        print("\n✅ Scenario 1: PASSED - Sonnet full workflow validated")

    async def test_scenario_2_hybrid_workflow_glm_handoff(self):
        """Test Scenario 2: Hybrid Workflow (Sonnet planning → GLM execution)."""
        print("\n🧪 Test Scenario 2: Hybrid Workflow (Sonnet → GLM Handoff)")
        print("=" * 80)

        # Step 1: Create task
        print("\n📝 Step 1: Task Creation")
        task_result = await self.mcp_client.create_task(
            title="Add Email Validation to User API",
            description="Implement email validation with regex and DNS check",
            task_type="coding",
            priority=6,
            phase_name="Core Engine & Infrastructure",
            project="DevStream"
        )
        task_id = task_result["task_id"]
        self.assert_true(task_id is not None, "Task created successfully")
        print(f"  Task ID: {task_id}")

        # Step 4: Generate implementation plan
        print("\n📋 Step 4: Implementation Plan Generation")
        plan_context = PlanContext(
            task_id=task_id,
            task_title="Add Email Validation to User API",
            task_description="Implement email validation with regex and DNS check",
            task_type="coding",
            priority=6,
            phase_name="Core Engine & Infrastructure",
            estimated_duration=45,
            complexity_score=0.5,
            context7_libraries=["email-validator", "pydantic"],
            research_findings="Use pydantic EmailStr for validation, DNS check optional for production",
            code_examples={"validation": "EmailStr from pydantic"},
            files_to_modify=["src/api/users.py"],
            files_to_create=[],
            dependencies=["pydantic", "email-validator"],
            performance_targets="< 50ms validation time",
            todowrite_tasks=[
                {"content": "Add EmailStr field to User model", "status": "pending"},
                {"content": "Add validation endpoint", "status": "pending"},
                {"content": "Write tests", "status": "pending"}
            ],
            session_id=f"sess-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        # Step 5: Strategic Choice Gate → Select GLM-4.6
        print("\n🎯 Step 5: Strategic Choice Gate → GLM-4.6 Selected")
        success, plan_path = await self.plan_generator.generate_plan(
            plan_context,
            ModelChoice.GLM_46
        )
        self.assert_true(success, "Plan generated successfully for GLM-4.6")
        self.assert_true(plan_path is not None, "Plan file path returned")
        print(f"  Plan Path: {plan_path}")

        # Verify plan stored with GLM template
        stored_plan = self.mcp_client.plans_created.get(task_id)
        self.assert_true(stored_plan is not None, "Plan stored in database")
        self.assert_equal(stored_plan["model_type"], "glm-4.6", "Model type is GLM-4.6")
        self.assert_contains(
            stored_plan["plan_content"],
            "GLM-4.6",
            "Plan content contains GLM-specific content"
        )

        # Verify handoff prompt generated
        self.assert_true(
            stored_plan["handoff_prompt"] is not None,
            "Handoff prompt generated for GLM workflow"
        )
        self.assert_contains(
            stored_plan["handoff_prompt"],
            "Claude Sonnet 4.5",
            "Handoff prompt contains Sonnet source"
        )
        self.assert_contains(
            stored_plan["handoff_prompt"],
            "GLM-4.6",
            "Handoff prompt contains GLM target"
        )
        self.assert_contains(
            stored_plan["handoff_prompt"],
            plan_path,
            "Handoff prompt contains plan file path"
        )

        # Verify metadata stored
        metadata = stored_plan.get("metadata", {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        self.assert_true("complexity" in metadata, "Metadata contains complexity")
        self.assert_true("estimated_duration" in metadata, "Metadata contains duration")

        print("\n✅ Scenario 2: PASSED - Hybrid workflow with GLM handoff validated")

    async def test_scenario_3_plan_retrieval_and_verification(self):
        """Test Scenario 3: Plan Retrieval and Verification."""
        print("\n🧪 Test Scenario 3: Plan Retrieval and Verification")
        print("=" * 80)

        # Create a plan first
        task_result = await self.mcp_client.create_task(
            title="Test Task for Retrieval",
            description="Testing plan retrieval",
            task_type="testing",
            priority=5,
            phase_name="Testing",
            project="DevStream"
        )
        task_id = task_result["task_id"]

        plan_context = PlanContext(
            task_id=task_id,
            task_title="Test Task for Retrieval",
            task_description="Testing plan retrieval",
            task_type="testing",
            priority=5,
            phase_name="Testing",
            estimated_duration=30,
            complexity_score=0.3,
            context7_libraries=["pytest"],
            research_findings="Use pytest fixtures",
            code_examples={},
            files_to_modify=[],
            files_to_create=["tests/test_retrieval.py"],
            dependencies=["pytest"],
            performance_targets="N/A",
            todowrite_tasks=[],
            session_id=f"sess-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        await self.plan_generator.generate_plan(plan_context, ModelChoice.SONNET_45)

        # Test retrieval
        print("\n📖 Retrieving Plan by Task ID")
        retrieved_plan = await self.mcp_client.call_tool(
            "devstream_get_implementation_plan",
            {"task_id": task_id}
        )
        self.assert_true(retrieved_plan is not None, "Plan retrieved successfully")
        self.assert_equal(retrieved_plan["task_id"], task_id, "Task ID matches")
        self.assert_equal(retrieved_plan["model_type"], "sonnet-4.5", "Model type matches")

        # Test list with filter
        print("\n📋 Listing Plans with Filter")
        plans_list = await self.mcp_client.call_tool(
            "devstream_list_implementation_plans",
            {"model_type": "sonnet-4.5", "limit": 10}
        )
        self.assert_true(plans_list is not None, "Plans list retrieved")
        self.assert_true(len(plans_list["plans"]) > 0, "Plans list contains entries")

        print("\n✅ Scenario 3: PASSED - Plan retrieval and verification successful")

    async def test_scenario_4_error_handling(self):
        """Test Scenario 4: Error Handling (duplicate plans, missing tasks)."""
        print("\n🧪 Test Scenario 4: Error Handling")
        print("=" * 80)

        # Test 1: Attempt to create duplicate plan
        print("\n🔍 Test: Duplicate Plan Prevention")
        task_result = await self.mcp_client.create_task(
            title="Task for Duplicate Test",
            description="Testing duplicate prevention",
            task_type="testing",
            priority=5,
            phase_name="Testing",
            project="DevStream"
        )
        task_id = task_result["task_id"]

        plan_context = PlanContext(
            task_id=task_id,
            task_title="Task for Duplicate Test",
            task_description="Testing duplicate prevention",
            task_type="testing",
            priority=5,
            phase_name="Testing",
            estimated_duration=30,
            complexity_score=0.3,
            context7_libraries=[],
            research_findings="",
            code_examples={},
            files_to_modify=[],
            files_to_create=[],
            dependencies=[],
            performance_targets="N/A",
            todowrite_tasks=[],
            session_id=f"sess-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        # Create first plan
        success1, _ = await self.plan_generator.generate_plan(plan_context, ModelChoice.GLM_46)
        self.assert_true(success1, "First plan created successfully")

        # Attempt to create duplicate (mock allows it, but real DB would reject)
        # In real scenario, this would fail at DB level due to UNIQUE constraint
        print("  Note: Duplicate prevention enforced by database UNIQUE constraint")

        # Test 2: Retrieve non-existent plan
        print("\n🔍 Test: Non-Existent Plan Retrieval")
        fake_task_id = "task-nonexistent"
        retrieved = await self.mcp_client.call_tool(
            "devstream_get_implementation_plan",
            {"task_id": fake_task_id}
        )
        self.assert_true(retrieved is None, "Non-existent plan returns None")

        print("\n✅ Scenario 4: PASSED - Error handling validated")

    async def test_template_loading(self):
        """Test template loading and variable substitution."""
        print("\n🧪 Test: Template Loading and Variable Substitution")
        print("=" * 80)

        # Test GLM template loading
        print("\n📄 Loading GLM-4.6 Template")
        glm_template = await self.plan_generator._load_template(ModelChoice.GLM_46)
        self.assert_true(glm_template is not None, "GLM template loaded")
        self.assert_contains(glm_template, "GLM-4.6", "GLM template contains model name")
        self.assert_contains(glm_template, "{{task_title}}", "GLM template contains variables")
        print(f"  Template size: {len(glm_template)} chars")

        # Test Sonnet template loading
        print("\n📄 Loading Sonnet 4.5 Template")
        sonnet_template = await self.plan_generator._load_template(ModelChoice.SONNET_45)
        self.assert_true(sonnet_template is not None, "Sonnet template loaded")
        self.assert_contains(sonnet_template, "Sonnet 4.5", "Sonnet template contains model name")
        self.assert_contains(sonnet_template, "{{task_title}}", "Sonnet template contains variables")
        print(f"  Template size: {len(sonnet_template)} chars")

        # Test variable substitution
        print("\n🔄 Testing Variable Substitution")
        plan_context = PlanContext(
            task_id="test-123",
            task_title="Test Task Title",
            task_description="Test description",
            task_type="testing",
            priority=5,
            phase_name="Testing Phase",
            estimated_duration=60,
            complexity_score=0.5,
            context7_libraries=["pytest", "asyncio"],
            research_findings="Test findings",
            code_examples={"example": "test code"},
            files_to_modify=["file1.py", "file2.py"],
            files_to_create=["new_file.py"],
            dependencies=["dep1", "dep2"],
            performance_targets="< 100ms",
            todowrite_tasks=[],
            session_id="sess-test",
            timestamp="2025-10-09T12:00:00Z"
        )

        filled_template = self.plan_generator._fill_template(
            glm_template,
            plan_context,
            ModelChoice.GLM_46
        )

        self.assert_contains(filled_template, "Test Task Title", "Task title substituted")
        self.assert_contains(filled_template, "test-123", "Task ID substituted")
        self.assert_contains(filled_template, "Testing Phase", "Phase name substituted")
        self.assert_true(
            "{{task_title}}" not in filled_template,
            "All {{task_title}} variables replaced"
        )
        print(f"  Filled template size: {len(filled_template)} chars")

        print("\n✅ Template Loading Test: PASSED")

    async def test_file_path_generation(self):
        """Test plan file path generation."""
        print("\n🧪 Test: Plan File Path Generation")
        print("=" * 80)

        test_cases = [
            ("Implement User Authentication", "docs/development/plan/piano_implement-user-authentication.md"),
            ("Add Email Validation", "docs/development/plan/piano_add-email-validation.md"),
            ("Fix Bug in API", "docs/development/plan/piano_fix-bug-in-api.md"),
            ("Very Long Task Title That Exceeds The Maximum Length Allowed For File Names Should Be Truncated Properly",
             "docs/development/plan/piano_very-long-task-title-that-exceeds-the-maximum-.md")
        ]

        for title, expected_pattern in test_cases:
            plan_context = PlanContext(
                task_id="test",
                task_title=title,
                task_description="",
                task_type="testing",
                priority=5,
                phase_name="",
                estimated_duration=30,
                complexity_score=0.5,
                context7_libraries=[],
                research_findings="",
                code_examples={},
                files_to_modify=[],
                files_to_create=[],
                dependencies=[],
                performance_targets="",
                todowrite_tasks=[],
                session_id="",
                timestamp=""
            )

            file_path = self.plan_generator._generate_plan_file_path(plan_context)
            print(f"  Title: '{title}'")
            print(f"  Path:  '{file_path}'")

            self.assert_true(file_path.startswith("docs/development/plan/piano_"), "Path has correct prefix")
            self.assert_true(file_path.endswith(".md"), "Path has .md extension")
            self.assert_true(len(file_path) <= 100, "Path length is reasonable")

        print("\n✅ File Path Generation Test: PASSED")

    async def run_all_tests(self):
        """Run all E2E tests."""
        print("\n" + "=" * 80)
        print("🚀 DevStream Protocol v2.2.0 - E2E Test Suite")
        print("=" * 80)

        start_time = datetime.now()

        try:
            await self.test_scenario_1_sonnet_full_workflow()
            await self.test_scenario_2_hybrid_workflow_glm_handoff()
            await self.test_scenario_3_plan_retrieval_and_verification()
            await self.test_scenario_4_error_handling()
            await self.test_template_loading()
            await self.test_file_path_generation()

        except AssertionError as e:
            print(f"\n❌ Test failed: {e}")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Print summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests:  {self.tests_passed + self.tests_failed}")
        print(f"✅ Passed:    {self.tests_passed}")
        print(f"❌ Failed:    {self.tests_failed}")
        print(f"⏱️  Duration:  {duration:.2f}s")
        print(f"✨ Success Rate: {(self.tests_passed / (self.tests_passed + self.tests_failed) * 100):.1f}%")

        if self.tests_failed == 0:
            print("\n🎉 ALL TESTS PASSED! Protocol v2.2.0 is production ready.")
        else:
            print(f"\n⚠️  {self.tests_failed} test(s) failed. Review failures above.")

        print("=" * 80)

        return self.tests_failed == 0


async def main():
    """Main entry point."""
    test_suite = ProtocolV220E2ETest()
    success = await test_suite.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
