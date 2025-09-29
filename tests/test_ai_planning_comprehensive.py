"""
Comprehensive AI Planning System Tests

Integration tests for the complete AI planning pipeline.
Validates end-to-end functionality, robustness, and performance.
"""

import asyncio
import json
import logging
import os
import pytest
from datetime import datetime
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock

from devstream.planning.planner import OllamaPlanner
from devstream.planning.models import AIPlannerConfig, TaskBreakdownRequest
from devstream.planning.testing import AITestFramework, TestSeverity
from devstream.ollama.client import OllamaClient
from devstream.memory.search import HybridSearchEngine

logger = logging.getLogger(__name__)


class TestAIPlanningIntegration:
    """Integration tests for AI Planning system."""

    @pytest.fixture
    async def ollama_client(self):
        """Create mock Ollama client."""
        client = AsyncMock(spec=OllamaClient)

        # Mock successful chat response
        client.chat.return_value = {
            "message": {
                "content": json.dumps({
                    "tasks": [
                        {
                            "title": "Design user interface",
                            "description": "Create wireframes and mockups for the user interface",
                            "estimated_minutes": 8,
                            "complexity_score": 5,
                            "priority_score": 7,
                            "task_type": "design",
                            "reasoning": "UI design is crucial for user experience"
                        },
                        {
                            "title": "Implement authentication backend",
                            "description": "Set up JWT-based authentication system",
                            "estimated_minutes": 10,
                            "complexity_score": 7,
                            "priority_score": 9,
                            "task_type": "implementation",
                            "reasoning": "Security is a high priority requirement"
                        },
                        {
                            "title": "Create user registration form",
                            "description": "Build frontend form for user registration",
                            "estimated_minutes": 6,
                            "complexity_score": 4,
                            "priority_score": 8,
                            "task_type": "implementation",
                            "reasoning": "Registration is needed for user onboarding"
                        }
                    ],
                    "planning_confidence": 0.85,
                    "total_estimated_minutes": 24
                })
            }
        }

        # Mock embedding response
        client.embedding.return_value = {
            "embedding": [0.1] * 384  # Mock embedding vector
        }

        return client

    @pytest.fixture
    async def memory_search(self):
        """Create mock memory search engine."""
        search = AsyncMock(spec=HybridSearchEngine)

        # Mock search results
        search.hybrid_search.return_value = {
            "results": [
                {
                    "content": "Previous authentication implementation example",
                    "score": 0.85,
                    "content_type": "code",
                    "keywords": ["authentication", "JWT", "security"]
                }
            ],
            "query_metadata": {
                "semantic_weight": 1.0,
                "keyword_weight": 0.8
            }
        }

        return search

    @pytest.fixture
    async def planner_config(self):
        """Create test planner configuration."""
        return AIPlannerConfig(
            model_name="llama2:latest",
            max_tokens=2048,
            temperature=0.3,
            timeout_seconds=30
        )

    @pytest.fixture
    async def ai_planner(self, ollama_client, memory_search, planner_config):
        """Create AI planner instance for testing."""
        return OllamaPlanner(
            ollama_client=ollama_client,
            memory_search=memory_search,
            config=planner_config
        )

    @pytest.fixture
    async def test_framework(self, ai_planner):
        """Create test framework instance."""
        return AITestFramework(ai_planner)

    @pytest.mark.asyncio
    async def test_comprehensive_test_suite(self, test_framework):
        """Run the complete comprehensive test suite."""
        logger.info("Starting comprehensive AI planning test suite")

        # Run comprehensive tests
        report = await test_framework.run_comprehensive_tests()

        # Validate overall success
        assert report["summary"]["total_tests"] > 0, "No tests were executed"

        # Check success rate
        success_rate = report["summary"]["success_rate"]
        assert success_rate >= 0.8, f"Success rate {success_rate:.2%} below 80% threshold"

        # Ensure no critical failures
        critical_failures = report["critical_failures"]
        assert len(critical_failures) == 0, f"Critical failures detected: {critical_failures}"

        # Validate test categories
        categories = report["categories"]
        assert categories["functional"]["total"] > 0, "No functional tests executed"
        assert categories["robustness"]["total"] > 0, "No robustness tests executed"
        assert categories["performance"]["total"] > 0, "No performance tests executed"

        logger.info(f"Test suite completed with {success_rate:.2%} success rate")

        return report

    @pytest.mark.asyncio
    async def test_basic_task_breakdown(self, ai_planner):
        """Test basic task breakdown functionality."""
        request = TaskBreakdownRequest(
            objective="Implement user authentication system",
            context="Web application with user management",
            max_tasks=5,
            context_source="test"
        )

        result = await ai_planner.break_down_task(request)

        # Validate basic structure
        assert len(result.suggested_tasks) > 0, "No tasks generated"
        assert 0.0 <= result.confidence_score <= 1.0, "Invalid confidence score"

        # Validate task properties
        for task in result.suggested_tasks:
            assert task.title, "Task missing title"
            assert task.description, "Task missing description"
            assert 1 <= task.estimated_minutes <= 60, "Invalid estimated minutes"
            assert 1 <= task.complexity_score <= 10, "Invalid complexity score"

    @pytest.mark.asyncio
    async def test_dependency_analysis(self, ai_planner):
        """Test dependency analysis functionality."""
        request = TaskBreakdownRequest(
            objective="Build complete web application",
            context="Full-stack development with database",
            max_tasks=6,
            context_source="test"
        )

        result = await ai_planner.break_down_task(request)

        # Validate dependencies (for complex tasks, some dependencies expected)
        if len(result.suggested_tasks) > 2:
            # Not strictly required but expected for complex tasks
            assert isinstance(result.dependencies, list), "Dependencies should be a list"

    @pytest.mark.asyncio
    async def test_complexity_estimation(self, ai_planner):
        """Test complexity estimation accuracy."""
        # Simple task
        simple_request = TaskBreakdownRequest(
            objective="Fix spelling error in button text",
            context="Simple frontend fix",
            max_tasks=2,
            context_source="test"
        )

        simple_result = await ai_planner.break_down_task(simple_request)
        simple_complexities = [task.complexity_score for task in simple_result.suggested_tasks]

        # Complex task
        complex_request = TaskBreakdownRequest(
            objective="Design and implement real-time multiplayer game engine",
            context="High-performance game development",
            max_tasks=8,
            context_source="test"
        )

        complex_result = await ai_planner.break_down_task(complex_request)
        complex_complexities = [task.complexity_score for task in complex_result.suggested_tasks]

        # Simple tasks should generally have lower complexity
        avg_simple = sum(simple_complexities) / len(simple_complexities)
        avg_complex = sum(complex_complexities) / len(complex_complexities)

        # Allow some flexibility but expect general trend
        assert avg_simple <= avg_complex + 2, "Complexity estimation seems inverted"

    @pytest.mark.asyncio
    async def test_validation_error_handling(self, ai_planner):
        """Test validation and error handling."""
        # Test empty objective
        with pytest.raises((ValueError, Exception)):
            request = TaskBreakdownRequest(
                objective="",
                context="Test context",
                context_source="test"
            )
            await ai_planner.break_down_task(request)

    @pytest.mark.asyncio
    async def test_memory_context_integration(self, ai_planner):
        """Test memory context integration."""
        request = TaskBreakdownRequest(
            objective="Add authentication to existing project",
            context="Building on previous authentication work",
            max_tasks=4,
            context_source="memory_test"
        )

        result = await ai_planner.break_down_task(request)

        # Memory integration should provide context-aware suggestions
        assert len(result.suggested_tasks) > 0, "No tasks generated with memory context"

        # Tasks should reference authentication concepts
        auth_related = any(
            "auth" in task.title.lower() or "auth" in task.description.lower()
            for task in result.suggested_tasks
        )
        assert auth_related, "No authentication-related tasks generated"

    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, ai_planner):
        """Test performance benchmarks."""
        start_time = datetime.now()

        request = TaskBreakdownRequest(
            objective="Optimize database query performance",
            context="Performance improvement task",
            max_tasks=5,
            context_source="performance_test"
        )

        result = await ai_planner.break_down_task(request)

        execution_time = (datetime.now() - start_time).total_seconds()

        # Performance requirements
        assert execution_time < 10.0, f"Planning took {execution_time:.2f}s, should be < 10s"
        assert len(result.suggested_tasks) > 0, "No tasks generated in performance test"

    @pytest.mark.asyncio
    async def test_concurrent_planning_requests(self, ai_planner):
        """Test handling of concurrent planning requests."""
        requests = [
            TaskBreakdownRequest(
                objective=f"Implement feature {i}",
                context=f"Context for feature {i}",
                max_tasks=3,
                context_source=f"concurrent_test_{i}"
            )
            for i in range(3)
        ]

        # Execute concurrently
        results = await asyncio.gather(
            *[ai_planner.break_down_task(req) for req in requests],
            return_exceptions=True
        )

        # Validate all succeeded
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Concurrent request {i} failed: {result}"
            assert len(result.suggested_tasks) > 0, f"No tasks in concurrent result {i}"

    @pytest.mark.asyncio
    async def test_fallback_mechanisms(self, ai_planner):
        """Test fallback mechanisms when AI fails."""
        # Mock AI failure
        ai_planner.ollama_client.chat.side_effect = Exception("Mock AI failure")

        request = TaskBreakdownRequest(
            objective="Test fallback handling",
            context="Fallback test context",
            max_tasks=3,
            context_source="fallback_test"
        )

        # Should still return results via fallback
        result = await ai_planner.break_down_task(request)

        assert len(result.suggested_tasks) > 0, "Fallback should still generate tasks"
        assert result.confidence_score < 0.5, "Fallback should have low confidence"

    def test_test_framework_initialization(self, test_framework):
        """Test test framework initialization."""
        assert test_framework is not None
        assert len(test_framework.scenarios) > 0, "No test scenarios loaded"

        # Validate scenario types
        scenario_names = [s.name for s in test_framework.scenarios]
        assert "basic_implementation_task" in scenario_names
        assert "complex_system_design" in scenario_names
        assert "vague_objective" in scenario_names

    @pytest.mark.asyncio
    async def test_edge_cases(self, ai_planner):
        """Test various edge cases."""
        edge_cases = [
            {
                "name": "unicode_objective",
                "objective": "Créer une application avec émojis 🚀🌟",
                "context": "Unicode handling test"
            },
            {
                "name": "very_long_objective",
                "objective": "Create a comprehensive enterprise-grade distributed microservices architecture with real-time data processing, machine learning capabilities, advanced security features, multi-tenant support, and scalable deployment infrastructure" * 3,
                "context": "Long text handling"
            },
            {
                "name": "special_characters",
                "objective": "Fix issue with @#$%^&*()_+ characters in user input",
                "context": "Special character handling"
            }
        ]

        for case in edge_cases:
            request = TaskBreakdownRequest(
                objective=case["objective"],
                context=case["context"],
                max_tasks=4,
                context_source=f"edge_case_{case['name']}"
            )

            try:
                result = await ai_planner.break_down_task(request)
                assert len(result.suggested_tasks) > 0, f"Edge case {case['name']} generated no tasks"
            except Exception as e:
                pytest.fail(f"Edge case {case['name']} failed: {e}")


# Standalone test runner for manual execution
async def run_comprehensive_tests():
    """Run comprehensive tests manually."""
    from devstream.ollama.client import OllamaClient
    from devstream.memory.search import HybridSearchEngine

    # Create real or mock components
    config = AIPlannerConfig(
        model_name="llama2:latest",
        max_tokens=2048,
        temperature=0.3
    )

    # For manual testing, you might want to use real components
    # client = OllamaClient()
    # search = HybridSearchEngine()

    # For now, use mocks
    client = AsyncMock(spec=OllamaClient)
    search = AsyncMock(spec=HybridSearchEngine)

    planner = OllamaPlanner(
        ollama_client=client,
        memory_search=search,
        config=config
    )

    framework = AITestFramework(planner)
    report = await framework.run_comprehensive_tests()

    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"ai_planning_test_report_{timestamp}.json"

    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"Comprehensive test report saved to: {report_file}")
    print(f"Test Summary: {report['summary']['passed_tests']}/{report['summary']['total_tests']} passed")
    print(f"Success Rate: {report['summary']['success_rate']:.2%}")

    return report


if __name__ == "__main__":
    # Run standalone tests
    asyncio.run(run_comprehensive_tests())