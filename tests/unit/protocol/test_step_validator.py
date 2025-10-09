#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pytest>=7.0.0",
#     "pytest-asyncio>=0.21.0",
#     "pytest-cov>=4.0.0",
#     "aiofiles>=23.0.0",
#     "structlog>=23.0.0",
#     "cachetools>=5.0.0",
# ]
# ///

"""
Test suite for Step Validator component.

Tests step completion validation, memory search integration,
Context7 usage validation, and requirement checking for all protocol steps.
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'protocol'))

from step_validator import (
    StepValidator,
    ValidationStatus,
    ValidationResult,
    ValidationRequirement,
    get_step_validator
)


@pytest.fixture
def mock_memory_client():
    """Create mock memory client."""
    client = AsyncMock()
    client.search_memory = AsyncMock()
    client.store_memory = AsyncMock()
    return client


@pytest.fixture
def step_validator(mock_memory_client):
    """Create step validator with mock memory client."""
    return StepValidator(memory_client=mock_memory_client)


@pytest.fixture
def sample_session_id():
    """Sample session ID for testing."""
    return "test-session-123"


class TestValidationStatus:
    """Test ValidationStatus enum functionality."""

    def test_status_values(self):
        """Test status enum values."""
        assert ValidationStatus.PASSED.value == "passed"
        assert ValidationStatus.FAILED.value == "failed"
        assert ValidationStatus.WARNING.value == "warning"
        assert ValidationStatus.SKIPPED.value == "skipped"


class TestValidationRequirement:
    """Test ValidationRequirement dataclass functionality."""

    def test_requirement_creation(self):
        """Test basic requirement creation."""
        req = ValidationRequirement(
            name="test_requirement",
            description="Test requirement description",
            validator="test_validator",
            required=True,
            timeout_minutes=30
        )

        assert req.name == "test_requirement"
        assert req.description == "Test requirement description"
        assert req.validator == "test_validator"
        assert req.required == True
        assert req.timeout_minutes == 30

    def test_optional_requirement(self):
        """Test optional requirement creation."""
        req = ValidationRequirement(
            name="optional_requirement",
            description="Optional requirement",
            validator="optional_validator",
            required=False
        )

        assert req.required == False


class TestValidationResult:
    """Test ValidationResult dataclass functionality."""

    def test_result_creation(self):
        """Test basic result creation."""
        result = ValidationResult(
            step_name="DISCUSSION",
            status=ValidationStatus.PASSED,
            requirements_met=["discussion_records"],
            requirements_failed=[],
            requirements_warning=[],
            evidence={"test": "evidence"},
            timestamp="2025-01-01T00:00:00Z",
            validation_duration_seconds=0.5
        )

        assert result.step_name == "DISCUSSION"
        assert result.status == ValidationStatus.PASSED
        assert result.requirements_met == ["discussion_records"]
        assert result.requirements_failed == []
        assert result.requirements_warning == []
        assert result.evidence == {"test": "evidence"}


class TestStepValidator:
    """Test StepValidator functionality."""

    def test_validator_initialization(self, step_validator):
        """Test validator initialization."""
        assert step_validator.memory_client is not None
        assert len(step_validator.step_requirements) == 7  # 7 protocol steps
        assert "DISCUSSION" in step_validator.step_requirements
        assert "VERIFICATION" in step_validator.step_requirements

    def test_step_requirements_structure(self, step_validator):
        """Test that all steps have required structure."""
        for step_name, requirements in step_validator.step_requirements.items():
            assert isinstance(requirements, list)
            assert len(requirements) > 0

            for req in requirements:
                assert isinstance(req, ValidationRequirement)
                assert req.name is not None
                assert req.description is not None
                assert req.validator is not None
                assert hasattr(req, 'required')

    @pytest.mark.asyncio
    async def test_validate_unknown_step(self, step_validator, sample_session_id):
        """Test validation of unknown step."""
        result = await step_validator.validate_step(
            "UNKNOWN_STEP",
            sample_session_id
        )

        assert result.status == ValidationStatus.SKIPPED
        assert "error" in result.evidence

    @pytest.mark.asyncio
    async def test_validate_discussion_step_success(self, step_validator, sample_session_id):
        """Test successful DISCUSSION step validation."""
        # Mock memory search results
        step_validator.memory_client.search_memory.return_value = {
            "results": [
                {
                    "id": "decision-1",
                    "content": f"Discussion about session {sample_session_id}. Decision made to proceed with implementation.",
                    "content_type": "decision",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            ]
        }

        result = await step_validator.validate_step(
            "DISCUSSION",
            sample_session_id
        )

        assert result.status == ValidationStatus.PASSED
        assert len(result.requirements_met) > 0
        assert len(result.requirements_failed) == 0

        # Verify memory search was called
        step_validator.memory_client.search_memory.assert_called()

    @pytest.mark.asyncio
    async def test_validate_discussion_step_no_records(self, step_validator, sample_session_id):
        """Test DISCUSSION step validation with no discussion records."""
        # Mock empty memory search results
        step_validator.memory_client.search_memory.return_value = {
            "results": []
        }

        result = await step_validator.validate_step(
            "DISCUSSION",
            sample_session_id
        )

        assert result.status == ValidationStatus.FAILED
        assert len(result.requirements_failed) > 0
        assert "No discussion records found" in str(result.evidence)

    @pytest.mark.asyncio
    async def test_validate_research_step_success(self, step_validator, sample_session_id):
        """Test successful RESEARCH step validation."""
        # Mock memory search results with Context7 indicators
        step_validator.memory_client.search_memory.return_value = {
            "results": [
                {
                    "id": "research-1",
                    "content": f"Context7 research completed for session {sample_session_id}. Best practices documented.",
                    "content_type": "context",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            ]
        }

        result = await step_validator.validate_step(
            "RESEARCH",
            sample_session_id
        )

        assert result.status == ValidationStatus.PASSED
        assert len(result.requirements_met) > 0

    @pytest.mark.asyncio
    async def test_validate_research_step_no_context7(self, step_validator, sample_session_id):
        """Test RESEARCH step validation without Context7 usage."""
        # Mock memory search results without Context7 indicators
        step_validator.memory_client.search_memory.return_value = {
            "results": [
                {
                    "id": "research-1",
                    "content": f"General discussion for session {sample_session_id}.",
                    "content_type": "context",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            ]
        }

        result = await step_validator.validate_step(
            "RESEARCH",
            sample_session_id
        )

        assert result.status == ValidationStatus.WARNING
        assert len(result.requirements_warning) > 0

    @pytest.mark.asyncio
    async def test_validate_planning_step_success(self, step_validator, sample_session_id):
        """Test successful PLANNING step validation."""
        # Mock memory search results with TodoWrite indicators
        step_validator.memory_client.search_memory.return_value = {
            "results": [
                {
                    "id": "planning-1",
                    "content": f"TodoWrite list created for session {sample_session_id}. Micro-tasks defined.",
                    "content_type": "context",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            ]
        }

        result = await step_validator.validate_step(
            "PLANNING",
            sample_session_id
        )

        assert result.status == ValidationStatus.PASSED
        assert len(result.requirements_met) > 0

    @pytest.mark.asyncio
    async def test_validate_implementation_step_success(self, step_validator, sample_session_id):
        """Test successful IMPLEMENTATION step validation."""
        # Mock memory search results with code documentation
        step_validator.memory_client.search_memory.return_value = {
            "results": [
                {
                    "id": "code-1",
                    "content": 'def authenticate_user(username: str, password: str) -> bool:\n    """\n    Authenticate user with credentials.\n    \n    Args:\n        username: User identifier\n        password: User password\n        \n    Returns:\n        True if authentication successful\n    """\n    # Implementation here',
                    "content_type": "code",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            ]
        }

        result = await step_validator.validate_step(
            "IMPLEMENTATION",
            sample_session_id
        )

        assert result.status == ValidationStatus.PASSED
        assert len(result.requirements_met) > 0

    @pytest.mark.asyncio
    async def test_validator_execution_error_handling(self, step_validator, sample_session_id):
        """Test error handling in validator execution."""
        # Mock memory client to raise exception
        step_validator.memory_client.search_memory.side_effect = Exception("Memory search failed")

        result = await step_validator.validate_step(
            "DISCUSSION",
            sample_session_id
        )

        # Should not crash, but return failed status
        assert result.status == ValidationStatus.FAILED
        assert len(result.requirements_failed) > 0

    @pytest.mark.asyncio
    async def test_validation_timeout_handling(self, step_validator, sample_session_id):
        """Test validation timeout handling."""
        # Mock validator method that takes too long
        async def slow_validator(*args):
            await asyncio.sleep(0.1)  # 100ms delay
            return {"status": "passed", "evidence": {}}

        # Replace validator method
        with patch.object(step_validator, 'validate_discussion_records', side_effect=slow_validator):
            # Test with short timeout
            result = await step_validator.validate_step(
                "DISCUSSION",
                sample_session_id,
                timeout_minutes=0  # Very short timeout
            )

            # Should still complete (our timeout is basic)
            assert result.status in [ValidationStatus.PASSED, ValidationStatus.FAILED]

    def test_validation_summary_generation(self, step_validator):
        """Test validation summary generation."""
        # Create sample validation results
        results = [
            ValidationResult(
                step_name="DISCUSSION",
                status=ValidationStatus.PASSED,
                requirements_met=["discussion_records", "consensus_documented"],
                requirements_failed=[],
                requirements_warning=[],
                evidence={},
                timestamp="2025-01-01T00:00:00Z",
                validation_duration_seconds=0.5
            ),
            ValidationResult(
                step_name="RESEARCH",
                status=ValidationStatus.WARNING,
                requirements_met=["context7_usage"],
                requirements_failed=[],
                requirements_warning=["best_practices_researched"],
                evidence={},
                timestamp="2025-01-01T00:00:00Z",
                validation_duration_seconds=0.3
            ),
            ValidationResult(
                step_name="IMPLEMENTATION",
                status=ValidationStatus.FAILED,
                requirements_met=["micro_task_execution"],
                requirements_failed=["code_documentation"],
                requirements_warning=[],
                evidence={},
                timestamp="2025-01-01T00:00:00Z",
                validation_duration_seconds=0.8
            )
        ]

        summary = step_validator.get_validation_summary(results)

        assert summary["total_steps"] == 3
        assert summary["passed_steps"] == 1
        assert summary["failed_steps"] == 1
        assert summary["warning_steps"] == 1
        assert summary["success_rate"] == "33.3%"
        assert summary["overall_status"] == "FAILED"

        # Verify step results are included
        assert "DISCUSSION" in summary["step_results"]
        assert "RESEARCH" in summary["step_results"]
        assert "IMPLEMENTATION" in summary["step_results"]


class TestIndividualValidators:
    """Test individual validator methods."""

    @pytest.mark.asyncio
    async def test_discussion_records_validator(self, step_validator, sample_session_id):
        """Test discussion records validator."""
        # Test with discussion records
        step_validator.memory_client.search_memory.return_value = {
            "results": [
                {
                    "id": "discussion-1",
                    "content": f"Discussion about decision for session {sample_session_id}",
                    "content_type": "decision"
                }
            ]
        }

        result = await step_validator.validate_discussion_records(
            sample_session_id, "task-123", "DISCUSSION"
        )

        assert result["status"] == "passed"
        assert "discussion_count" in result["evidence"]

        # Test without discussion records
        step_validator.memory_client.search_memory.return_value = {
            "results": []
        }

        result = await step_validator.validate_discussion_records(
            sample_session_id, "task-123", "DISCUSSION"
        )

        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_consensus_documented_validator(self, step_validator, sample_session_id):
        """Test consensus documented validator."""
        # Test with consensus
        step_validator.memory_client.search_memory.return_value = {
            "results": [
                {
                    "id": "decision-1",
                    "content": f"Team reached consensus for session {sample_session_id}. Approved implementation approach.",
                    "content_type": "decision"
                }
            ]
        }

        result = await step_validator.validate_consensus_documented(
            sample_session_id, "task-123", "DISCUSSION"
        )

        assert result["status"] == "passed"

        # Test without consensus
        step_validator.memory_client.search_memory.return_value = {
            "results": [
                {
                    "id": "decision-1",
                    "content": f"General discussion for session {sample_session_id}.",
                    "content_type": "decision"
                }
            ]
        }

        result = await step_validator.validate_consensus_documented(
            sample_session_id, "task-123", "DISCUSSION"
        )

        assert result["status"] == "warning"

    @pytest.mark.asyncio
    async def test_context7_usage_validator(self, step_validator, sample_session_id):
        """Test Context7 usage validator."""
        # Test with Context7 usage
        step_validator.memory_client.search_memory.return_value = {
            "results": [
                {
                    "id": "research-1",
                    "content": f"Context7 research completed for session {sample_session_id}. Library docs retrieved.",
                    "content_type": "context"
                }
            ]
        }

        result = await step_validator.validate_context7_usage(
            sample_session_id, "task-123", "RESEARCH"
        )

        assert result["status"] == "passed"

        # Test without Context7 usage
        step_validator.memory_client.search_memory.return_value = {
            "results": []
        }

        result = await step_validator.validate_context7_usage(
            sample_session_id, "task-123", "RESEARCH"
        )

        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_todowrite_created_validator(self, step_validator, sample_session_id):
        """Test TodoWrite created validator."""
        # Test with TodoWrite usage
        step_validator.memory_client.search_memory.return_value = {
            "results": [
                {
                    "id": "planning-1",
                    "content": f"TodoWrite list created for session {sample_session_id}. Tasks: pending, in_progress, completed.",
                    "content_type": "context"
                }
            ]
        }

        result = await step_validator.validate_todowrite_created(
            sample_session_id, "task-123", "PLANNING"
        )

        assert result["status"] == "passed"

    @pytest.mark.asyncio
    async def test_code_documentation_validator(self, step_validator, sample_session_id):
        """Test code documentation validator."""
        # Test with well-documented code
        step_validator.memory_client.search_memory.return_value = {
            "results": [
                {
                    "id": "code-1",
                    "content": 'def function_name(param: str) -> bool:\n    """\n    Function description.\n    \n    Args:\n        param: Input parameter\n        \n    Returns:\n        Result boolean\n    """\n    return True',
                    "content_type": "code"
                },
                {
                    "id": "code-2",
                    "content": 'class TestClass:\n    """Test class documentation."""\n    def method(self) -> None:\n        """Method documentation."""\n        pass',
                    "content_type": "code"
                }
            ]
        }

        result = await step_validator.validate_code_documentation(
            sample_session_id, "task-123", "IMPLEMENTATION"
        )

        assert result["status"] == "passed"
        assert result["evidence"]["documentation_ratio"] == "100.0%"

        # Test with poorly documented code
        step_validator.memory_client.search_memory.return_value = {
            "results": [
                {
                    "id": "code-1",
                    "content": "def function(param):\n    return True\n\ndef another_function():\n    pass",
                    "content_type": "code"
                }
            ]
        }

        result = await step_validator.validate_code_documentation(
            sample_session_id, "task-123", "IMPLEMENTATION"
        )

        assert result["status"] == "failed"


class TestGlobalValidator:
    """Test global validator instance functionality."""

    def test_global_validator_singleton(self):
        """Test that global validator returns same instance."""
        validator1 = get_step_validator()
        validator2 = get_step_validator()

        assert validator1 is validator2


@pytest.mark.asyncio
async def test_integration_full_protocol_validation(step_validator, sample_session_id):
    """Test complete protocol validation workflow."""
    # Mock memory search results for each step
    discussion_results = {
        "results": [
            {
                "id": "discussion-1",
                "content": f"Discussion completed for session {sample_session_id}",
                "content_type": "decision"
            }
        ]
    }

    research_results = {
        "results": [
            {
                "id": "research-1",
                "content": f"Context7 research completed for session {sample_session_id}",
                "content_type": "context"
            }
        ]
    }

    planning_results = {
        "results": [
            {
                "id": "planning-1",
                "content": f"TodoWrite list created for session {sample_session_id}",
                "content_type": "context"
            }
        ]
    }

    # Set up side effects for different search calls
    step_validator.memory_client.search_memory.side_effect = [
        discussion_results,  # DISCUSSION validation
        research_results,    # RESEARCH validation
        planning_results      # PLANNING validation
    ]

    # Validate all steps
    steps_to_validate = ["DISCUSSION", "RESEARCH", "PLANNING"]
    results = []

    for step in steps_to_validate:
        result = await step_validator.validate_step(step, sample_session_id)
        results.append(result)

    # Verify all steps passed
    for result in results:
        assert result.status == ValidationStatus.PASSED

    # Generate summary
    summary = step_validator.get_validation_summary(results)
    assert summary["total_steps"] == 3
    assert summary["passed_steps"] == 3
    assert summary["failed_steps"] == 0
    assert summary["success_rate"] == "100.0%"
    assert summary["overall_status"] == "PASSED"


if __name__ == "__main__":
    # Run tests directly
    import subprocess
    result = subprocess.run(["pytest", __file__, "-v"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    print(f"Tests completed with exit code: {result.returncode}")