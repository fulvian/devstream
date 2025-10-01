"""
Unit tests for Protocol Enforcement Gate (Fix A1).

Tests:
- Simple query (no trigger)
- Complex query (trigger enforcement gate)
- User prompt injection
- Override scenario
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import sys

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / '.claude/hooks/devstream'))

# Test data
SIMPLE_QUERY = "What is the status of the project?"
COMPLEX_QUERY = """
Implement a new user authentication system with JWT tokens,
password hashing using bcrypt, refresh token rotation,
and integration with the existing FastAPI backend.
Add comprehensive tests and documentation.
"""

class TestProtocolEnforcement:
    """Test Protocol Enforcement Gate functionality."""

    def test_simple_query_no_trigger(self):
        """Test that simple queries do not trigger enforcement gate."""
        # Import protocol enforcement module
        from user_query_context_enhancer import should_trigger_protocol_gate

        # Simple queries should not trigger
        assert not should_trigger_protocol_gate(SIMPLE_QUERY, estimated_duration=5)

    def test_complex_query_triggers_gate(self):
        """Test that complex queries trigger enforcement gate."""
        from user_query_context_enhancer import should_trigger_protocol_gate

        # Complex implementation tasks should trigger
        assert should_trigger_protocol_gate(COMPLEX_QUERY, estimated_duration=30)

    def test_duration_threshold_trigger(self):
        """Test that tasks > 15 minutes trigger enforcement."""
        from user_query_context_enhancer import should_trigger_protocol_gate

        query = "Add email validation"

        # Short task - no trigger
        assert not should_trigger_protocol_gate(query, estimated_duration=10)

        # Long task - trigger
        assert should_trigger_protocol_gate(query, estimated_duration=20)

    def test_code_implementation_trigger(self):
        """Test that code implementation keywords trigger enforcement."""
        from user_query_context_enhancer import should_trigger_protocol_gate

        # Keywords: "implement", "add", "create"
        queries = [
            "Implement user authentication",
            "Add password reset feature",
            "Create database migration",
            "Build API endpoint"
        ]

        for query in queries:
            assert should_trigger_protocol_gate(query, estimated_duration=15)

    def test_architectural_decision_trigger(self):
        """Test that architectural decisions trigger enforcement."""
        from user_query_context_enhancer import should_trigger_protocol_gate

        queries = [
            "Design the database schema",
            "Choose authentication strategy",
            "Refactor the API layer"
        ]

        for query in queries:
            assert should_trigger_protocol_gate(query, estimated_duration=10)

    def test_multi_file_trigger(self):
        """Test that multi-file operations trigger enforcement."""
        from user_query_context_enhancer import should_trigger_protocol_gate

        query = "Update user.py, auth.py, and tests"

        assert should_trigger_protocol_gate(query, estimated_duration=15)

    def test_context7_research_trigger(self):
        """Test that tasks requiring Context7 research trigger enforcement."""
        from user_query_context_enhancer import should_trigger_protocol_gate

        queries = [
            "How to implement JWT authentication in FastAPI?",
            "Best practices for async database connections",
            "Research SQLite vector search implementation"
        ]

        for query in queries:
            assert should_trigger_protocol_gate(query, estimated_duration=15)

    @patch('user_query_context_enhancer.get_user_input')
    def test_user_chooses_protocol(self, mock_input):
        """Test user explicitly choosing protocol workflow."""
        from user_query_context_enhancer import handle_protocol_gate

        # Mock user input: "1" = protocol
        mock_input.return_value = "1"

        result = handle_protocol_gate(COMPLEX_QUERY)

        assert result["choice"] == "protocol"
        assert result["proceed_with_protocol"] is True

    @patch('user_query_context_enhancer.get_user_input')
    def test_user_chooses_override(self, mock_input):
        """Test user explicitly choosing to override protocol."""
        from user_query_context_enhancer import handle_protocol_gate

        # Mock user input: "2" = override
        mock_input.return_value = "2"

        result = handle_protocol_gate(COMPLEX_QUERY)

        assert result["choice"] == "override"
        assert result["proceed_with_protocol"] is False
        assert "risks_acknowledged" in result

    @patch('user_query_context_enhancer.log_protocol_override')
    @patch('user_query_context_enhancer.get_user_input')
    async def test_override_tracking(self, mock_input, mock_log):
        """Test that protocol overrides are logged to memory."""
        from user_query_context_enhancer import handle_protocol_gate

        # User chooses override
        mock_input.return_value = "2"

        result = handle_protocol_gate(COMPLEX_QUERY)

        # Verify override logged
        assert mock_log.called
        call_args = mock_log.call_args[0]
        assert COMPLEX_QUERY in call_args[0]
        assert "protocol-override" in call_args[1]  # keywords

    def test_enforcement_gate_message_format(self):
        """Test that enforcement gate message is properly formatted."""
        from user_query_context_enhancer import format_enforcement_gate_message

        message = format_enforcement_gate_message(COMPLEX_QUERY)

        # Verify message contains key elements
        assert "⚠️ DevStream Protocol Required" in message
        assert "7-step workflow" in message
        assert "DISCUSSION → ANALYSIS → RESEARCH → PLANNING → APPROVAL → IMPLEMENTATION → VERIFICATION" in message
        assert "OPTIONS:" in message
        assert "✅ [RECOMMENDED] Follow DevStream protocol" in message
        assert "⚠️  [OVERRIDE] Skip protocol" in message
        assert "Risks of override:" in message
        assert "❌ No Context7 research" in message
        assert "❌ No @code-reviewer validation" in message

    def test_bypass_forbidden(self):
        """Test that enforcement gate cannot be disabled via config."""
        from user_query_context_enhancer import should_trigger_protocol_gate
        import os

        # Try to disable via env var
        os.environ["DEVSTREAM_PROTOCOL_ENFORCEMENT_ENABLED"] = "false"

        # Should still trigger for complex tasks
        assert should_trigger_protocol_gate(COMPLEX_QUERY, estimated_duration=20)

        # Cleanup
        del os.environ["DEVSTREAM_PROTOCOL_ENFORCEMENT_ENABLED"]


class TestProtocolViolationDetection:
    """Test protocol violation detection and handling."""

    @patch('user_query_context_enhancer.detect_protocol_violation')
    async def test_violation_detection(self, mock_detect):
        """Test that protocol violations are detected."""
        from user_query_context_enhancer import monitor_protocol_compliance

        # Simulate violation: proceeding without approval
        mock_detect.return_value = {
            "violated": True,
            "reason": "Implementation started without approval",
            "context": {"tool_name": "Write", "file_path": "src/auth.py"}
        }

        result = await monitor_protocol_compliance()

        assert result["violated"] is True
        assert "Implementation started without approval" in result["reason"]

    @patch('user_query_context_enhancer.rollback_to_checkpoint')
    async def test_violation_rollback(self, mock_rollback):
        """Test that violations trigger rollback to last checkpoint."""
        from user_query_context_enhancer import handle_protocol_violation

        violation = {
            "violated": True,
            "reason": "Implementation without approval",
            "context": {"tool_name": "Write"}
        }

        await handle_protocol_violation(violation)

        # Verify rollback called
        assert mock_rollback.called


class TestProtocolIntegrationWithHooks:
    """Test protocol enforcement integration with hook system."""

    @pytest.mark.asyncio
    async def test_user_prompt_submit_hook_integration(self):
        """Test protocol gate integrated with UserPromptSubmit hook."""
        from user_query_context_enhancer import UserQueryContextEnhancer

        enhancer = UserQueryContextEnhancer()

        # Mock UserPromptSubmitContext
        mock_context = Mock()
        mock_context.user_query = COMPLEX_QUERY
        mock_context.output = Mock()
        mock_context.output.exit_success = Mock()

        # Patch user input to choose protocol
        with patch('user_query_context_enhancer.get_user_input', return_value="1"):
            await enhancer.process(mock_context)

        # Verify protocol workflow initiated
        # (actual workflow happens in next tool call)
        assert mock_context.output.exit_success.called


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
