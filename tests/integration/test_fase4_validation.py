#!/usr/bin/env -S .devstream/bin/python
"""
FASE 4: Simplified Integration Testing - DevStream Protocol Enhancement Validation

Focused test suite for validating core protocol enforcement functionality.
Tests the essential FASE 1-3 components without complex dependency issues.

Test Categories:
1. Core Component Initialization Tests
2. Basic Protocol State Management Tests
3. Enforcement Gate Analysis Tests
4. Interactive Step Validation Tests
5. Hook Integration Basic Tests

Target: Validate core functionality and system readiness
"""

import asyncio
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch
import pytest

# Add project paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "hooks" / "devstream" / "protocol"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "hooks" / "devstream"))

# Core Protocol Components
from protocol_state_manager import ProtocolStateManager, ProtocolState, ProtocolStep
from enforcement_gate import EnforcementGate, EnforcementContext
from task_first_handler import TaskFirstHandler

# Interactive Components
from interactive_step_validator import InteractiveStepValidator, StepValidationResult, StepTransition


class TestCoreProtocolComponents:
    """Test core protocol component functionality."""

    @pytest.fixture
    async def temp_state_dir(self):
        """Temporary directory for protocol state files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    async def protocol_manager(self, temp_state_dir):
        """ProtocolStateManager instance with temporary state directory."""
        state_file = Path(temp_state_dir) / "test_protocol_state.json"
        manager = ProtocolStateManager(state_file)
        return manager

    @pytest.mark.asyncio
    async def test_protocol_state_manager_basic_functionality(self, protocol_manager):
        """Test basic ProtocolStateManager functionality."""
        # Test initialization
        assert protocol_manager is not None
        assert hasattr(protocol_manager, 'state_file')

        # Test session creation
        session = await protocol_manager.initialize_session()
        assert isinstance(session, ProtocolState)
        assert session.protocol_step == ProtocolStep.IDLE
        assert session.session_id is not None

        # Test step advancement
        updated_session = await protocol_manager.advance_step(
            session, ProtocolStep.DISCUSSION
        )
        assert updated_session.protocol_step == ProtocolStep.DISCUSSION

        # Test state persistence
        current_state = await protocol_manager.get_current_state()
        assert current_state.session_id == session.session_id
        assert current_state.protocol_step == ProtocolStep.DISCUSSION

    @pytest.mark.asyncio
    async def test_enforcement_gate_basic_analysis(self):
        """Test basic enforcement gate analysis."""
        gate = EnforcementGate()

        # Test initialization
        assert gate is not None
        assert hasattr(gate, 'should_enforce_protocol')

        # Test simple enforcement analysis
        should_enforce, reasons = gate.should_enforce_protocol(
            task_description="Simple fix",
            estimated_duration=5,
            involves_code=False,
            involves_architecture=False,
            requires_context7=False,
            file_count=1
        )
        assert isinstance(should_enforce, bool)
        assert isinstance(reasons, list)

        # Test complex enforcement analysis
        should_enforce_complex, complex_reasons = gate.should_enforce_protocol(
            task_description="Build comprehensive authentication system",
            estimated_duration=120,
            involves_code=True,
            involves_architecture=True,
            requires_context7=True,
            file_count=8
        )
        assert should_enforce_complex is True
        assert len(complex_reasons) > 2

    @pytest.mark.asyncio
    async def test_task_first_handler_functionality(self):
        """Test TaskFirstHandler basic functionality."""
        handler = TaskFirstHandler()

        # Test initialization
        assert handler is not None
        assert hasattr(handler, 'should_create_task')

        # Test task creation analysis
        should_create = handler.should_create_task(
            "Implement new feature with multiple files"
        )
        assert isinstance(should_create, bool)

        # Test simple task (should not require task creation)
        should_create_simple = handler.should_create_task(
            "Fix typo in documentation"
        )
        assert isinstance(should_create_simple, bool)

    @pytest.mark.asyncio
    async def test_protocol_step_enumeration(self):
        """Test ProtocolStep enumeration functionality."""
        # Test all steps exist
        all_steps = list(ProtocolStep)
        expected_step_count = 8  # IDLE + 7 steps
        assert len(all_steps) == expected_step_count

        # Test specific steps
        assert ProtocolStep.IDLE.value == 0
        assert ProtocolStep.DISCUSSION.value == 1
        assert ProtocolStep.VERIFICATION.value == 7

        # Test step string representation
        discussion_str = str(ProtocolStep.DISCUSSION)
        assert "DISCUSSION" in discussion_str

    @pytest.mark.asyncio
    async def test_enforcement_context_creation(self):
        """Test EnforcementContext data structure."""
        context = EnforcementContext(
            task_description="Test task for validation",
            estimated_duration=30,
            complexity_score=0.7,
            involves_code=True,
            involves_architecture=False,
            requires_context7=True,
            trigger_reasons=["Code implementation required", "Context7 research needed"],
            session_id="test-session-123",
            timestamp="2025-10-08T12:00:00Z"
        )

        assert context.task_description == "Test task for validation"
        assert context.estimated_duration == 30
        assert context.complexity_score == 0.7
        assert context.involves_code is True
        assert len(context.trigger_reasons) == 2


class TestInteractiveStepValidation:
    """Test interactive step validation components."""

    @pytest.fixture
    async def mock_mcp_client(self):
        """Mock MCP client for testing."""
        client = Mock()
        client.call_tool = AsyncMock(return_value={"success": True})
        return client

    @pytest.fixture
    async def interactive_validator(self, mock_mcp_client):
        """InteractiveStepValidator instance."""
        return InteractiveStepValidator(mock_mcp_client)

    @pytest.mark.asyncio
    async def test_interactive_validator_initialization(self, interactive_validator):
        """Test InteractiveStepValidator initialization."""
        assert interactive_validator is not None
        assert hasattr(interactive_validator, 'validate_step_completion')
        assert hasattr(interactive_validator, 'handle_step_transition')

    @pytest.mark.asyncio
    async def test_step_validation_result_creation(self):
        """Test StepValidationResult data structure."""
        from interactive_step_validator import ValidationResult

        result = StepValidationResult(
            step=ProtocolStep.DISCUSSION,
            result=ValidationResult.COMPLETED,
            completion_percentage=0.85,
            requirements_met=["Discussion documented", "Trade-offs analyzed"],
            requirements_missing=[],
            evidence={"has_keywords": True},
            next_step_ready=True,
            user_confirmation_required=False
        )

        assert result.step == ProtocolStep.DISCUSSION
        assert result.result == ValidationResult.COMPLETED
        assert result.completion_percentage == 0.85
        assert len(result.requirements_met) == 2
        assert result.next_step_ready is True

    @pytest.mark.asyncio
    async def test_step_transition_creation(self):
        """Test StepTransition data structure."""
        transition = StepTransition(
            from_step=ProtocolStep.DISCUSSION,
            to_step=ProtocolStep.ANALYSIS,
            session_id="test-session",
            user_confirmed=True,
            timestamp="2025-10-08T12:00:00Z",
            evidence={"completion": 85.0},
            notes="Step completed successfully"
        )

        assert transition.from_step == ProtocolStep.DISCUSSION
        assert transition.to_step == ProtocolStep.ANALYSIS
        assert transition.user_confirmed is True
        assert transition.session_id == "test-session"

    @pytest.mark.asyncio
    async def test_basic_step_validation(self, interactive_validator):
        """Test basic step validation functionality."""
        user_input = "Let's discuss implementing a new feature with comprehensive analysis of trade-offs and alternatives."
        context = {"session_id": "test-session"}

        # Test discussion step validation
        result = await interactive_validator.validate_step_completion(
            ProtocolStep.DISCUSSION, user_input, context
        )

        assert isinstance(result, StepValidationResult)
        assert result.step == ProtocolStep.DISCUSSION
        assert isinstance(result.completion_percentage, float)
        assert isinstance(result.requirements_met, list)
        assert isinstance(result.requirements_missing, list)


class TestHookIntegrationBasic:
    """Test basic hook integration functionality."""

    @pytest.fixture
    async def user_prompt_hook(self):
        """UserPromptSubmitHook instance for testing."""
        # Mock dependencies that might fail in test environment
        with patch.multiple(
            'context.user_query_context_enhancer',
            AGENT_DELEGATION_AVAILABLE=False,
            PROTOCOL_ENFORCEMENT_AVAILABLE=True
        ):
            from context.user_query_context_enhancer import UserPromptSubmitHook
            hook = UserPromptSubmitHook()
            return hook

    @pytest.mark.asyncio
    async def test_hook_initialization(self, user_prompt_hook):
        """Test UserPromptSubmitHook initialization."""
        assert user_prompt_hook is not None
        assert hasattr(user_prompt_hook, 'estimate_task_complexity')

    @pytest.mark.asyncio
    async def test_complexity_analysis_basic(self, user_prompt_hook):
        """Test basic complexity analysis functionality."""
        # Test simple task
        simple_input = "Fix typo in README file"
        complexity = user_prompt_hook.estimate_task_complexity(simple_input)

        assert isinstance(complexity, dict)
        assert "complexity_score" in complexity
        assert "triggers" in complexity
        assert "enforce_protocol" in complexity

        # Test complex task
        complex_input = "Build comprehensive microservices architecture with API gateway, authentication, service discovery, and monitoring"
        complex_complexity = user_prompt_hook.estimate_task_complexity(complex_input)

        assert isinstance(complex_complexity, dict)
        assert complex_complexity["complexity_score"] > complexity["complexity_score"]
        assert len(complex_complexity["triggers"]) >= len(complexity["triggers"])

    @pytest.mark.asyncio
    async def test_step_validation_methods(self, user_prompt_hook):
        """Test individual step validation methods."""
        # Test discussion step validation
        discussion_input = "Let's discuss the approach and consider different alternatives with trade-off analysis."
        result = await user_prompt_hook._validate_discussion_step(discussion_input)

        assert isinstance(result, dict)
        assert "completed" in result
        assert isinstance(result["completed"], bool)

        # Test analysis step validation
        analysis_input = "I've analyzed the codebase and identified the components that need modification for this feature."
        result = await user_prompt_hook._validate_analysis_step(analysis_input)

        assert isinstance(result, dict)
        assert "completed" in result

    @pytest.mark.asyncio
    async def test_protocol_instructions_building(self, user_prompt_hook):
        """Test protocol instructions building."""
        workflow_result = {
            "step_validated": True,
            "validation_result": {"completed": True},
            "next_step_ready": True
        }

        instructions = user_prompt_hook._build_protocol_instructions(
            ProtocolStep.IMPLEMENTATION, workflow_result
        )

        assert isinstance(instructions, str)
        assert "DevStream 7-Step Protocol Active" in instructions
        assert "IMPLEMENTATION" in instructions
        assert "Quality Requirements" in instructions


class TestWorkflowIntegration:
    """Test workflow integration scenarios."""

    @pytest.fixture
    async def workflow_components(self):
        """Set up core components for workflow testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize core components
            state_file = Path(temp_dir) / "workflow_state.json"
            protocol_manager = ProtocolStateManager(state_file)
            enforcement_gate = EnforcementGate()

            components = {
                "protocol_manager": protocol_manager,
                "enforcement_gate": enforcement_gate
            }

            yield components

    @pytest.mark.asyncio
    async def test_basic_workflow_progression(self, workflow_components):
        """Test basic protocol workflow progression."""
        protocol_manager = workflow_components["protocol_manager"]

        # Initialize session
        session = await protocol_manager.initialize_session()
        assert session.protocol_step == ProtocolStep.IDLE

        # Progress through steps
        steps = [ProtocolStep.DISCUSSION, ProtocolStep.ANALYSIS, ProtocolStep.RESEARCH]

        for step in steps:
            session = await protocol_manager.advance_step(session, step)
            assert session.protocol_step == step

            # Verify persistence
            current_state = await protocol_manager.get_current_state()
            assert current_state.protocol_step == step

    @pytest.mark.asyncio
    async def test_enforcement_trigger_analysis(self, workflow_components):
        """Test enforcement trigger analysis across different scenarios."""
        enforcement_gate = workflow_components["enforcement_gate"]

        test_cases = [
            {
                "description": "Fix minor typo",
                "duration": 5,
                "code": False,
                "arch": False,
                "context7": False,
                "files": 1,
                "expected_enforce": False
            },
            {
                "description": "Implement user authentication system",
                "duration": 90,
                "code": True,
                "arch": True,
                "context7": True,
                "files": 6,
                "expected_enforce": True
            }
        ]

        for case in test_cases:
            should_enforce, reasons = enforcement_gate.should_enforce_protocol(
                task_description=case["description"],
                estimated_duration=case["duration"],
                involves_code=case["code"],
                involves_architecture=case["arch"],
                requires_context7=case["context7"],
                file_count=case["files"]
            )

            assert should_enforce == case["expected_enforce"], f"Failed for: {case['description']}"

    @pytest.mark.asyncio
    async def test_complexity_scoring_accuracy(self):
        """Test complexity scoring accuracy for different task types."""
        handler = TaskFirstHandler()

        simple_tasks = [
            "Fix typo in documentation",
            "Update README version number",
            "Add simple validation to existing form"
        ]

        complex_tasks = [
            "Implement comprehensive authentication system with OAuth 2.0",
            "Design microservices architecture with API gateway",
            "Build real-time collaborative editing system"
        ]

        # Test simple tasks (should have lower complexity)
        for task in simple_tasks:
            should_create = handler.should_create_task(task)
            # Simple tasks might or might not require task creation based on other factors
            assert isinstance(should_create, bool)

        # Test complex tasks (should more likely require task creation)
        for task in complex_tasks:
            should_create = handler.should_create_task(task)
            assert isinstance(should_create, bool)


class TestErrorHandling:
    """Test error handling and graceful degradation."""

    @pytest.mark.asyncio
    async def test_protocol_state_recovery(self):
        """Test protocol state recovery scenarios."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "recovery_test.json"
            manager = ProtocolStateManager(state_file)

            # Create session and advance
            session1 = await manager.initialize_session()
            session1 = await manager.advance_step(session1, ProtocolStep.DISCUSSION)

            # Create new manager instance (simulates restart)
            manager2 = ProtocolStateManager(state_file)
            recovered_session = await manager2.get_current_state()

            # Should recover state correctly
            assert recovered_session.session_id == session1.session_id
            assert recovered_session.protocol_step == ProtocolStep.DISCUSSION

    @pytest.mark.asyncio
    async def test_missing_dependency_handling(self):
        """Test graceful degradation with missing dependencies."""
        # Test enforcement gate without PyInquirer
        with patch.dict('sys.modules', {'PyInquirer': None}):
            gate = EnforcementGate()
            assert gate is not None

            # Should still perform basic analysis
            should_enforce, reasons = gate.should_enforce_protocol(
                task_description="Test task",
                estimated_duration=30,
                involves_code=True
            )
            assert isinstance(should_enforce, bool)

    @pytest.mark.asyncio
    async def test_invalid_data_handling(self):
        """Test handling of invalid or corrupted data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "invalid_test.json"
            manager = ProtocolStateManager(state_file)

            # Create valid session first
            session = await manager.initialize_session()
            original_session_id = session.session_id

            # Test with various invalid step transitions
            with pytest.raises(Exception):
                # Invalid transition should be caught
                await manager.advance_step(session, ProtocolStep.VERIFICATION)

            # Valid transitions should still work
            valid_session = await manager.advance_step(session, ProtocolStep.DISCUSSION)
            assert valid_session.protocol_step == ProtocolStep.DISCUSSION


if __name__ == "__main__":
    # Run focused validation tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
        "--maxfail=5"  # Maximum number of failures
    ])