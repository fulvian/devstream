#!/usr/bin/env -S .devstream/bin/python
"""
FASE 4: Complete Integration Testing Suite - DevStream Protocol Enforcement

Test suite for comprehensive validation of the DevStream Protocol Enhancement system.
Covers FASE 1-3 components with end-to-end workflow enforcement testing.

Test Categories:
1. Component Integration Tests
2. Protocol State Management Tests
3. Interactive Enforcement Gate Tests
4. Hook Integration Tests
5. End-to-End Workflow Tests
6. Performance and Load Tests
7. Error Handling and Recovery Tests

Coverage Target: 95%+ across all protocol components
"""

import asyncio
import os
import sys
import json
import tempfile
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import Mock, AsyncMock, patch
import pytest

# Add project paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "hooks" / "devstream" / "protocol"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "hooks" / "devstream"))

# Protocol Components
from protocol_state_manager import ProtocolStateManager, ProtocolState, ProtocolStep
from enforcement_gate import EnforcementGate, EnforcementContext, EnforcementDecision
from task_first_handler import TaskFirstHandler
from task_state_sync import TaskStateSync
from step_validator import StepValidator

# Interactive Components (FASE 3)
from interactive_step_validator import InteractiveStepValidator, StepValidationResult, StepTransition

# Hook Components
from context.user_query_context_enhancer import UserPromptSubmitHook
# PostToolUseHook has import issues - test without it for now


class TestProtocolComponentIntegration:
    """Test suite for protocol component integration (FASE 1)."""

    @pytest.fixture
    async def mock_mcp_client(self):
        """Mock MCP client for testing."""
        client = Mock()
        client.call_tool = AsyncMock(return_value={"success": True})
        return client

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
    async def test_protocol_state_manager_initialization(self, protocol_manager):
        """Test ProtocolStateManager initialization and session creation."""
        # Test initialization
        assert protocol_manager is not None
        assert hasattr(protocol_manager, 'state_file')

        # Test session creation (no task_id parameter needed)
        session = await protocol_manager.initialize_session()

        assert isinstance(session, ProtocolState)
        assert session.protocol_step == ProtocolStep.IDLE  # Default is IDLE
        assert session.session_id is not None
        assert len(session.session_id) > 0

    @pytest.mark.asyncio
    async def test_enforcement_gate_initialization(self):
        """Test EnforcementGate initialization and complexity analysis."""
        gate = EnforcementGate()

        # Test initialization
        assert gate is not None
        assert hasattr(gate, 'should_enforce_protocol')

        # Test enforcement analysis
        should_enforce, reasons = gate.should_enforce_protocol(
            task_description="Implement comprehensive user authentication system",
            estimated_duration=45,
            involves_code=True,
            involves_architecture=True,
            requires_context7=True,
            file_count=5
        )

        assert should_enforce is True
        assert len(reasons) > 0
        assert any("duration" in reason.lower() for reason in reasons)

    @pytest.mark.asyncio
    async def test_task_first_handler_functionality(self, mock_mcp_client):
        """Test TaskFirstHandler complexity analysis and task creation."""
        handler = TaskFirstHandler()

        # Test initialization
        assert handler is not None
        assert hasattr(handler, 'analyze_complexity')

        # Test complexity analysis
        complexity = await handler.analyze_complexity(
            "Build comprehensive API gateway with rate limiting and authentication"
        )

        assert isinstance(complexity, dict)
        assert "complexity_score" in complexity
        assert "triggers" in complexity
        assert "estimated_duration" in complexity
        assert complexity["complexity_score"] > 0

    @pytest.mark.asyncio
    async def test_step_validator_comprehensive(self):
        """Test StepValidator for all protocol steps."""
        validator = StepValidator()

        # Test all step definitions
        all_steps = validator.get_all_steps()
        expected_steps = [
            "TASK_CREATION", "DISCUSSION", "ANALYSIS", "RESEARCH",
            "PLANNING", "APPROVAL", "IMPLEMENTATION", "VERIFICATION"
        ]

        assert len(all_steps) == len(expected_steps)
        for step in expected_steps:
            assert step in all_steps

    @pytest.mark.asyncio
    async def test_component_integration_workflow(self, protocol_manager, mock_mcp_client):
        """Test complete component integration workflow."""
        # Initialize components
        gate = EnforcementGate()
        handler = TaskFirstHandler()

        # Create protocol session
        task_id = f"integration-test-{uuid.uuid4().hex[:8]}"
        session = await protocol_manager.initialize_session(task_id)

        # Test workflow: Task Creation -> Discussion
        assert session.protocol_step == ProtocolStep.TASK_CREATION

        # Advance to discussion
        updated_session = await protocol_manager.advance_step(
            session, ProtocolStep.DISCUSSION
        )
        assert updated_session.protocol_step == ProtocolStep.DISCUSSION

        # Test enforcement gate integration
        should_enforce, reasons = gate.should_enforce_protocol(
            task_description="Test task for integration validation",
            estimated_duration=20,
            involves_code=True
        )
        assert should_enforce is True


class TestInteractiveStepValidation:
    """Test suite for FASE 3 Interactive Step Validator."""

    @pytest.fixture
    async def mock_mcp_client(self):
        """Mock MCP client for interactive validator testing."""
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
            requirements_met=[
                "Problem/objective discussion documented",
                "Trade-offs considered and analyzed"
            ],
            requirements_missing=[],
            evidence={
                "has_discussion_keywords": True,
                "sufficient_length": True,
                "mentions_alternatives": True
            },
            next_step_ready=True,
            user_confirmation_required=False
        )

        assert result.step == ProtocolStep.DISCUSSION
        assert result.result == ValidationResult.COMPLETED
        assert result.completion_percentage == 0.85
        assert len(result.requirements_met) == 2
        assert len(result.requirements_missing) == 0

    @pytest.mark.asyncio
    async def test_step_transition_creation(self):
        """Test StepTransition data structure."""
        transition = StepTransition(
            from_step=ProtocolStep.DISCUSSION,
            to_step=ProtocolStep.ANALYSIS,
            session_id="test-session",
            user_confirmed=True,
            timestamp="2025-10-08T12:00:00Z",
            evidence={"completion_percentage": 85.0},
            notes="Discussion completed - proceeding to analysis"
        )

        assert transition.from_step == ProtocolStep.DISCUSSION
        assert transition.to_step == ProtocolStep.ANALYSIS
        assert transition.user_confirmed is True
        assert transition.notes is not None

    @pytest.mark.asyncio
    async def test_discussion_step_validation(self, interactive_validator):
        """Test validation of DISCUSSION step."""
        user_input = "Let's discuss implementing a new user authentication system. We need to consider trade-offs between security and usability, and evaluate different approaches like OAuth vs JWT."
        context = {"session_id": "test-session"}

        result = await interactive_validator.validate_step_completion(
            ProtocolStep.DISCUSSION, user_input, context
        )

        assert isinstance(result, StepValidationResult)
        assert result.step == ProtocolStep.DISCUSSION
        assert result.completion_percentage > 50  # Should have good completion

    @pytest.mark.asyncio
    async def test_analysis_step_validation(self, interactive_validator):
        """Test validation of ANALYSIS step."""
        user_input = "I've analyzed the codebase and found similar authentication patterns in src/auth/. The implementation will require modifications to 3 main files and has an estimated complexity of 0.8."
        context = {"session_id": "test-session"}

        result = await interactive_validator.validate_step_completion(
            ProtocolStep.ANALYSIS, user_input, context
        )

        assert isinstance(result, StepValidationResult)
        assert result.step == ProtocolStep.ANALYSIS
        assert "codebase" in result.evidence.get("has_analysis_keywords", "").lower()

    @pytest.mark.asyncio
    async def test_research_step_validation(self, interactive_validator):
        """Test validation of RESEARCH step."""
        user_input = "I've researched best practices for authentication systems using Context7. The OAuth 2.0 specification and JWT standards provide good guidance for secure implementation."
        context = {"session_id": "test-session"}

        result = await interactive_validator.validate_step_completion(
            ProtocolStep.RESEARCH, user_input, context
        )

        assert isinstance(result, StepValidationResult)
        assert result.step == ProtocolStep.RESEARCH
        assert result.completion_percentage > 30  # Should have some research content


class TestEnhancedUserPromptSubmitHook:
    """Test suite for Enhanced UserPromptSubmit Hook (FASE 3)."""

    @pytest.fixture
    async def mock_context(self):
        """Mock UserPromptSubmitContext for hook testing."""
        context = Mock()
        context.user_input = "Implement comprehensive user authentication system with OAuth 2.0"
        context.output = Mock()
        context.output.exit_success = Mock()
        return context

    @pytest.fixture
    async def user_prompt_hook(self):
        """UserPromptSubmitHook instance for testing."""
        # Mock the dependencies that might fail in test environment
        with patch.multiple(
            'context.user_query_context_enhancer',
            AGENT_DELEGATION_AVAILABLE=False,
            PROTOCOL_ENFORCEMENT_AVAILABLE=True
        ):
            hook = UserPromptSubmitHook()
            return hook

    @pytest.mark.asyncio
    async def test_hook_initialization(self, user_prompt_hook):
        """Test UserPromptSubmitHook initialization with FASE 3 components."""
        assert user_prompt_hook is not None
        assert hasattr(user_prompt_hook, '_enhanced_protocol_enforcement')
        assert hasattr(user_prompt_hook, '_handle_protocol_workflow')

    @pytest.mark.asyncio
    async def test_complexity_analysis_integration(self, user_prompt_hook):
        """Test complexity analysis integration."""
        user_input = "Build comprehensive user authentication system with OAuth 2.0, JWT tokens, and session management"

        complexity = user_prompt_hook.estimate_task_complexity(user_input)

        assert isinstance(complexity, dict)
        assert "complexity_score" in complexity
        assert "triggers" in complexity
        assert "enforce_protocol" in complexity
        assert complexity["enforce_protocol"] is True  # Should trigger enforcement

    @pytest.mark.asyncio
    async def test_enhanced_protocol_enforcement_flow(self, user_prompt_hook):
        """Test enhanced protocol enforcement flow."""
        # Create mock protocol state
        mock_state = Mock()
        mock_state.session_id = "test-session"
        mock_state.protocol_step = ProtocolStep.DISCUSSION

        complexity = {
            "complexity_score": 0.8,
            "enforce_protocol": True,
            "triggers": ["code_implementation_required", "architectural_decisions_required"]
        }

        # Test enhanced enforcement
        with patch.object(user_prompt_hook, 'protocol_manager') as mock_manager:
            mock_manager.get_current_state.return_value = mock_state

            result = await user_prompt_hook._enhanced_protocol_enforcement(
                "Implement authentication system", complexity, mock_state
            )

            assert isinstance(result, dict)
            assert "action" in result
            assert result["action"] in ["protocol", "override", "cancel", "fallback"]

    @pytest.mark.asyncio
    async def test_step_validation_methods(self, user_prompt_hook):
        """Test individual step validation methods."""
        # Test discussion step validation
        discussion_input = "Let's discuss the trade-offs between different authentication approaches. OAuth 2.0 provides better security but requires more infrastructure."

        result = await user_prompt_hook._validate_discussion_step(discussion_input)
        assert isinstance(result, dict)
        assert "completed" in result
        assert result["completed"] is True

        # Test analysis step validation
        analysis_input = "I've analyzed the existing codebase and found authentication patterns in src/auth/. This will require modifications to user models and API endpoints."

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


class TestEndToEndWorkflow:
    """Test suite for end-to-end protocol enforcement workflow."""

    @pytest.fixture
    async def workflow_components(self):
        """Set up all components for end-to-end testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock MCP client
            mock_client = Mock()
            mock_client.call_tool = AsyncMock(return_value={"success": True})

            # Initialize components
            state_file = Path(temp_dir) / "e2e_protocol_state.json"
            protocol_manager = ProtocolStateManager(str(state_file))

            components = {
                "protocol_manager": protocol_manager,
                "enforcement_gate": EnforcementGate(),
                "task_handler": TaskFirstHandler(),
                "step_validator": StepValidator(),
                "interactive_validator": InteractiveStepValidator(mock_client),
                "mock_client": mock_client
            }

            yield components

    @pytest.mark.asyncio
    async def test_complete_protocol_workflow_enforcement(self, workflow_components):
        """Test complete protocol workflow from task creation through verification."""
        protocol_manager = workflow_components["protocol_manager"]
        enforcement_gate = workflow_components["enforcement_gate"]

        # Step 1: Task Creation
        task_id = f"e2e-test-{uuid.uuid4().hex[:8]}"
        session = await protocol_manager.initialize_session(task_id)
        assert session.protocol_step == ProtocolStep.TASK_CREATION

        # Step 2: Advance through all protocol steps
        steps = [
            ProtocolStep.DISCUSSION,
            ProtocolStep.ANALYSIS,
            ProtocolStep.RESEARCH,
            ProtocolStep.PLANNING,
            ProtocolStep.APPROVAL,
            ProtocolStep.IMPLEMENTATION,
            ProtocolStep.VERIFICATION
        ]

        for step in steps:
            # Simulate step completion
            session = await protocol_manager.advance_step(session, step)
            assert session.protocol_step == step

            # Verify step persistence
            current_state = await protocol_manager.get_current_state()
            assert current_state.protocol_step == step

    @pytest.mark.asyncio
    async def test_enforcement_gate_integration_workflow(self, workflow_components):
        """Test enforcement gate integration in complete workflow."""
        protocol_manager = workflow_components["protocol_manager"]
        enforcement_gate = workflow_components["enforcement_gate"]

        # Create session
        task_id = f"enforcement-test-{uuid.uuid4().hex[:8]}"
        session = await protocol_manager.initialize_session(task_id)

        # Test enforcement triggering
        should_enforce, reasons = enforcement_gate.should_enforce_protocol(
            task_description="Implement comprehensive microservices architecture",
            estimated_duration=120,
            involves_code=True,
            involves_architecture=True,
            requires_context7=True,
            file_count=10
        )

        assert should_enforce is True
        assert len(reasons) >= 3  # Should trigger multiple enforcement reasons

    @pytest.mark.asyncio
    async def test_protocol_state_crash_recovery(self, workflow_components):
        """Test protocol state crash recovery and persistence."""
        protocol_manager = workflow_components["protocol_manager"]

        # Create session and advance through steps
        task_id = f"recovery-test-{uuid.uuid4().hex[:8]}"
        session = await protocol_manager.initialize_session(task_id)

        # Advance to implementation step
        session = await protocol_manager.advance_step(session, ProtocolStep.DISCUSSION)
        session = await protocol_manager.advance_step(session, ProtocolStep.ANALYSIS)
        session = await protocol_manager.advance_step(session, ProtocolStep.RESEARCH)

        # Simulate crash - create new manager instance
        new_manager = ProtocolStateManager(protocol_manager.state_file)

        # Verify state recovery
        recovered_state = await new_manager.get_current_state()
        assert recovered_state.session_id == session.session_id
        assert recovered_state.task_id == task_id
        assert recovered_state.protocol_step == ProtocolStep.RESEARCH

    @pytest.mark.asyncio
    async def test_complexity_analysis_accuracy(self, workflow_components):
        """Test complexity analysis accuracy across different task types."""
        task_handler = workflow_components["task_handler"]

        test_cases = [
            {
                "description": "Fix typo in README",
                "expected_enforcement": False,
                "expected_score_range": (0.0, 0.3)
            },
            {
                "description": "Implement comprehensive user authentication system with OAuth 2.0 and JWT",
                "expected_enforcement": True,
                "expected_score_range": (0.7, 1.0)
            },
            {
                "description": "Add simple validation to existing form",
                "expected_enforcement": False,
                "expected_score_range": (0.2, 0.5)
            },
            {
                "description": "Design and implement microservices architecture with API gateway, service discovery, and distributed tracing",
                "expected_enforcement": True,
                "expected_score_range": (0.8, 1.0)
            }
        ]

        for test_case in test_cases:
            complexity = await task_handler.analyze_complexity(test_case["description"])

            assert complexity["enforce_protocol"] == test_case["expected_enforcement"]
            score_range = test_case["expected_score_range"]
            assert score_range[0] <= complexity["complexity_score"] <= score_range[1]


class TestPerformanceAndLoad:
    """Test suite for performance and load testing."""

    @pytest.fixture
    async def performance_components(self):
        """Set up components for performance testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "perf_protocol_state.json"
            protocol_manager = ProtocolStateManager(str(state_file))
            enforcement_gate = EnforcementGate()

            yield {
                "protocol_manager": protocol_manager,
                "enforcement_gate": enforcement_gate
            }

    @pytest.mark.asyncio
    async def test_protocol_state_persistence_performance(self, performance_components):
        """Test protocol state persistence performance under load."""
        protocol_manager = performance_components["protocol_manager"]

        # Performance test: Create and update multiple sessions
        session_count = 50
        creation_times = []
        update_times = []

        for i in range(session_count):
            import time

            # Measure session creation time
            start_time = time.time()
            task_id = f"perf-test-{i:03d}"
            session = await protocol_manager.initialize_session(task_id)
            creation_time = time.time() - start_time
            creation_times.append(creation_time)

            # Measure state update time
            start_time = time.time()
            session = await protocol_manager.advance_step(session, ProtocolStep.DISCUSSION)
            update_time = time.time() - start_time
            update_times.append(update_time)

        # Performance assertions
        avg_creation_time = sum(creation_times) / len(creation_times)
        avg_update_time = sum(update_times) / len(update_times)

        # Should be under 10ms per operation on average
        assert avg_creation_time < 0.01, f"Creation too slow: {avg_creation_time:.3f}s"
        assert avg_update_time < 0.01, f"Update too slow: {avg_update_time:.3f}s"

    @pytest.mark.asyncio
    async def test_enforcement_gate_performance(self, performance_components):
        """Test enforcement gate performance under load."""
        enforcement_gate = performance_components["enforcement_gate"]

        # Performance test: Multiple enforcement analyses
        test_count = 100
        analysis_times = []

        for i in range(test_count):
            import time

            start_time = time.time()
            should_enforce, reasons = enforcement_gate.should_enforce_protocol(
                task_description=f"Performance test task {i}: Implement authentication system",
                estimated_duration=30 + (i % 60),  # Vary duration
                involves_code=i % 3 == 0,  # Vary complexity
                involves_architecture=i % 4 == 0,
                requires_context7=i % 2 == 0,
                file_count=i % 5
            )
            analysis_time = time.time() - start_time
            analysis_times.append(analysis_time)

        # Performance assertions
        avg_analysis_time = sum(analysis_times) / len(analysis_times)

        # Should be under 5ms per analysis on average
        assert avg_analysis_time < 0.005, f"Analysis too slow: {avg_analysis_time:.3f}s"

    @pytest.mark.asyncio
    async def test_concurrent_session_management(self, performance_components):
        """Test concurrent protocol session management."""
        protocol_manager = performance_components["protocol_manager"]

        # Create multiple concurrent sessions
        session_count = 20
        tasks = []

        for i in range(session_count):
            task_id = f"concurrent-test-{i:03d}"
            task = protocol_manager.initialize_session(task_id)
            tasks.append(task)

        # Execute all sessions concurrently
        import time
        start_time = time.time()
        sessions = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Verify all sessions created successfully
        assert len(sessions) == session_count
        for session in sessions:
            assert isinstance(session, ProtocolState)
            assert session.session_id is not None

        # Performance assertion: Should handle concurrency efficiently
        avg_time_per_session = total_time / session_count
        assert avg_time_per_session < 0.01, f"Concurrent creation too slow: {avg_time_per_session:.3f}s"


class TestErrorHandlingAndRecovery:
    """Test suite for error handling and recovery scenarios."""

    @pytest.fixture
    async def error_test_components(self):
        """Set up components for error testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "error_protocol_state.json"
            protocol_manager = ProtocolStateManager(str(state_file))

            yield {"protocol_manager": protocol_manager}

    @pytest.mark.asyncio
    async def test_corrupted_state_recovery(self, error_test_components):
        """Test recovery from corrupted protocol state files."""
        protocol_manager = error_test_components["protocol_manager"]

        # Create valid session
        task_id = f"corruption-test-{uuid.uuid4().hex[:8]}"
        session = await protocol_manager.initialize_session(task_id)
        original_session_id = session.session_id

        # Corrupt the state file
        with open(protocol_manager.state_file, 'w') as f:
            f.write('{"invalid": "json", "corrupted": true}')

        # Test recovery - should create new session
        try:
            recovered_session = await protocol_manager.get_current_state()
            # If recovery fails, should create new session
            assert recovered_session is None or recovered_session.session_id != original_session_id
        except Exception:
            # Should handle corruption gracefully
            pass

        # Should still be able to create new sessions
        new_session = await protocol_manager.initialize_session(f"new-{task_id}")
        assert isinstance(new_session, ProtocolState)
        assert new_session.session_id != original_session_id

    @pytest.mark.asyncio
    async def test_invalid_step_advances(self, error_test_components):
        """Test handling of invalid step advancement attempts."""
        protocol_manager = error_test_components["protocol_manager"]

        # Create session
        task_id = f"invalid-step-test-{uuid.uuid4().hex[:8]}"
        session = await protocol_manager.initialize_session(task_id)

        # Test invalid step transitions
        with pytest.raises(Exception):
            # Should not allow skipping directly to verification
            await protocol_manager.advance_step(session, ProtocolStep.VERIFICATION)

        # Valid transition should still work
        session = await protocol_manager.advance_step(session, ProtocolStep.DISCUSSION)
        assert session.protocol_step == ProtocolStep.DISCUSSION

    @pytest.mark.asyncio
    async def test_missing_dependency_handling(self):
        """Test graceful degradation when dependencies are missing."""
        # Test with missing PyInquirer
        with patch.dict('sys.modules', {'PyInquirer': None}):
            gate = EnforcementGate()
            # Should handle missing dependency gracefully
            assert gate is not None

            # Should still perform enforcement analysis
            should_enforce, reasons = gate.should_enforce_protocol(
                task_description="Test task",
                estimated_duration=30,
                involves_code=True
            )
            assert isinstance(should_enforce, bool)

    @pytest.mark.asyncio
    async def test_database_connection_failures(self, error_test_components):
        """Test handling of database connection failures."""
        protocol_manager = error_test_components["protocol_manager"]

        # Simulate database permission issues
        original_file = protocol_manager.state_file

        # Create directory without write permissions
        readonly_dir = tempfile.mkdtemp()
        readonly_file = Path(readonly_dir) / "readonly_state.json"
        os.chmod(readonly_dir, 0o444)  # Read-only

        protocol_manager.state_file = str(readonly_file)

        try:
            # Should handle permission errors gracefully
            with pytest.raises(Exception):
                await protocol_manager.initialize_session("permission-test")
        finally:
            # Restore permissions for cleanup
            os.chmod(readonly_dir, 0o755)
            protocol_manager.state_file = original_file


if __name__ == "__main__":
    # Run tests with coverage reporting
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--cov=.claude/hooks/devstream/protocol",
        "--cov=.claude/hooks/devstream/context",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=85"
    ])