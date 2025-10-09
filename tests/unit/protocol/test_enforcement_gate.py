#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pytest>=7.0.0",
#     "pytest-asyncio>=0.21.0",
#     "pytest-cov>=4.0.0",
#     "aiofiles>=23.0.0",
#     "structlog>=23.0.0",
# ]
# ///

"""
Test suite for Enforcement Gate component.

Tests protocol enforcement logic, user interaction, decision logging,
and graceful degradation when PyInquirer is unavailable.
"""

import asyncio
import json
import pytest
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'protocol'))

from enforcement_gate import (
    EnforcementGate,
    EnforcementDecision,
    EnforcementContext,
    get_enforcement_gate
)


@pytest.fixture
def mock_memory_client():
    """Create mock memory client."""
    client = AsyncMock()
    client.store_memory = AsyncMock()
    return client


@pytest.fixture
def enforcement_gate(mock_memory_client):
    """Create enforcement gate with mock memory client."""
    gate = EnforcementGate()
    gate.memory_client = mock_memory_client
    return gate


@pytest.fixture
def sample_context():
    """Sample enforcement context for testing."""
    return EnforcementContext(
        task_description="Implement comprehensive user authentication system",
        estimated_duration=45,
        complexity_score=0.8,
        involves_code=True,
        involves_architecture=True,
        requires_context7=True,
        trigger_reasons=[
            "Estimated duration > 15min (45min)",
            "Involves code implementation",
            "Requires Context7 research"
        ],
        session_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat()
    )


class TestEnforcementDecision:
    """Test EnforcementDecision enum functionality."""

    def test_decision_values(self):
        """Test decision enum values."""
        assert EnforcementDecision.PROTOCOL.value == "protocol"
        assert EnforcementDecision.OVERRIDE.value == "override"
        assert EnforcementDecision.CANCEL.value == "cancel"


class TestEnforcementContext:
    """Test EnforcementContext dataclass functionality."""

    def test_context_creation(self):
        """Test basic context creation."""
        context = EnforcementContext(
            task_description="Test task",
            estimated_duration=30,
            complexity_score=0.5,
            involves_code=False,
            involves_architecture=False,
            requires_context7=False,
            trigger_reasons=["Test reason"],
            session_id="test-session",
            timestamp="2025-01-01T00:00:00Z"
        )

        assert context.task_description == "Test task"
        assert context.estimated_duration == 30
        assert context.complexity_score == 0.5
        assert context.involves_code == False


class TestEnforcementGate:
    """Test EnforcementGate functionality."""

    def test_gate_initialization(self):
        """Test gate initialization."""
        gate = EnforcementGate()

        assert gate.decisions_logged == 0
        assert isinstance(gate.pyinquirer_available, bool)

    def test_enforcement_trigger_analysis_simple_task(self, enforcement_gate):
        """Test enforcement analysis for simple task."""
        should_enforce, reasons = enforcement_gate.should_enforce_protocol(
            task_description="Fix typo in README",
            estimated_duration=5,
            involves_code=False,
            involves_architecture=False,
            requires_context7=False,
            file_count=1
        )

        assert should_enforce == False
        assert len(reasons) == 0

    def test_enforcement_trigger_analysis_complex_task(self, enforcement_gate):
        """Test enforcement analysis for complex task."""
        should_enforce, reasons = enforcement_gate.should_enforce_protocol(
            task_description="Implement new API endpoint with authentication",
            estimated_duration=45,
            involves_code=True,
            involves_architecture=True,
            requires_context7=True,
            file_count=3
        )

        assert should_enforce == True
        assert len(reasons) > 0
        assert any("duration" in reason.lower() for reason in reasons)
        assert any("code" in reason.lower() for reason in reasons)

    def test_enforcement_trigger_duration_threshold(self, enforcement_gate):
        """Test duration-based enforcement trigger."""
        # Below threshold
        should_enforce, _ = enforcement_gate.should_enforce_protocol(
            task_description="Test task",
            estimated_duration=10
        )
        assert should_enforce == False

        # At threshold
        should_enforce, _ = enforcement_gate.should_enforce_protocol(
            task_description="Test task",
            estimated_duration=15
        )
        assert should_enforce == False

        # Above threshold
        should_enforce, reasons = enforcement_gate.should_enforce_protocol(
            task_description="Test task",
            estimated_duration=20
        )
        assert should_enforce == True
        assert any("duration" in reason.lower() for reason in reasons)

    def test_enforcement_trigger_complexity_indicators(self, enforcement_gate):
        """Test complexity-based enforcement triggers."""
        complex_indicators = [
            "implement user authentication system",
            "design microservices architecture",
            "build comprehensive integration",
            "migrate database to new system",
            "optimize performance bottlenecks"
        ]

        for description in complex_indicators:
            should_enforce, reasons = enforcement_gate.should_enforce_protocol(
                task_description=description
            )
            assert should_enforce == True
            assert len(reasons) > 0

    def test_warning_message_building(self, enforcement_gate, sample_context):
        """Test warning message construction."""
        warning = enforcement_gate._build_warning_message(sample_context)

        # Verify message contains required elements
        assert "DevStream Protocol Required" in warning
        assert sample_context.task_description in warning
        assert "45 minutes" in warning
        assert "Risks of override" in warning
        assert "Context7 research" in warning

    @pytest.mark.asyncio
    async def test_non_interactive_fallback(self, enforcement_gate, sample_context):
        """Test non-interactive fallback when PyInquirer unavailable."""
        # Mock PyInquirer as unavailable
        with patch('claude.hooks.devstream.protocol.enforcement_gate.PYINQUIRER_AVAILABLE', False):
            decision = await enforcement_gate._non_interactive_fallback(sample_context)

            # Should default to PROTOCOL
            assert decision == EnforcementDecision.PROTOCOL

    @pytest.mark.asyncio
    async def test_environment_override_fallback(self, enforcement_gate, sample_context):
        """Test environment variable override in non-interactive mode."""
        # Set environment variable for override
        with patch.dict('os.environ', {'DEVSTREAM_PROTOCOL_OVERRIDE': 'true'}):
            with patch('claude.hooks.devstream.protocol.enforcement_gate.PYINQUIRER_AVAILABLE', False):
                decision = await enforcement_gate._non_interactive_fallback(sample_context)

                # Should respect environment override
                assert decision == EnforcementDecision.OVERRIDE

    @pytest.mark.asyncio
    async def test_decision_logging_to_memory(self, enforcement_gate, sample_context, mock_memory_client):
        """Test decision logging to memory."""
        decision = EnforcementDecision.OVERRIDE

        await enforcement_gate._log_decision_to_memory(
            sample_context,
            decision,
            mock_memory_client
        )

        # Verify memory client was called
        mock_memory_client.store_memory.assert_called_once()

        # Get call arguments
        call_args = mock_memory_client.store_memory.call_args
        content = call_args[1]['content']
        content_type = call_args[1]['content_type']
        keywords = call_args[1]['keywords']

        # Verify content
        assert "OVERRIDE" in content
        assert sample_context.task_description in content
        assert "PROTOCOL OVERRIDE - RISKS ACCEPTED" in content
        assert content_type == "decision"
        assert "protocol-enforcement" in keywords
        assert "override" in keywords
        assert sample_context.session_id in keywords

    @pytest.mark.asyncio
    async def test_decision_logging_fallback_to_file(self, enforcement_gate, sample_context):
        """Test decision logging fallback to file when memory client unavailable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "protocol_decisions.jsonl"

            # Mock memory client to raise exception
            failing_memory_client = AsyncMock()
            failing_memory_client.store_memory.side_effect = Exception("Memory client failed")

            decision = EnforcementDecision.PROTOCOL

            await enforcement_gate._log_decision_to_memory(
                sample_context,
                decision,
                failing_memory_client
            )

            # Verify log file was created
            assert log_file.exists()

            # Verify log content
            log_content = log_file.read_text()
            log_entry = json.loads(log_content.strip())

            assert log_entry["decision"] == "protocol"
            assert log_entry["session_id"] == sample_context.session_id
            assert log_entry["task_description"] == sample_context.task_description

    @pytest.mark.asyncio
    async def test_keyboard_interrupt_handling(self, enforcement_gate, sample_context):
        """Test handling of keyboard interrupt during enforcement."""
        with patch('claude.hooks.devstream.protocol.enforcement_gate.PYINQUIRER_AVAILABLE', True):
            with patch('claude.hooks.devstream.protocol.enforcement_gate.prompt',
                      side_effect=KeyboardInterrupt()):
                decision = await enforcement_gate.show_enforcement_gate(
                    sample_context,
                    memory_client=None
                )

                assert decision == EnforcementDecision.CANCEL

    @pytest.mark.asyncio
    async def test_gate_error_handling(self, enforcement_gate, sample_context):
        """Test error handling in enforcement gate."""
        with patch('claude.hooks.devstream.protocol.enforcement_gate.PYINQUIRER_AVAILABLE', True):
            with patch('claude.hooks.devstream.protocol.enforcement_gate.prompt',
                      side_effect=Exception("Prompt error")):
                decision = await enforcement_gate.show_enforcement_gate(
                    sample_context,
                    memory_client=None
                )

                # Should return CANCEL on error
                assert decision == EnforcementDecision.CANCEL

    def test_additional_context_display(self, enforcement_gate, sample_context, capsys):
        """Test additional context display."""
        enforcement_gate._display_additional_context(sample_context)

        captured = capsys.readouterr()
        output = captured.out

        # Verify context information is displayed
        assert sample_context.session_id in output
        assert "45 minutes" in output
        assert "0.8/1.0" in output
        assert "⚡ Code implementation required" in output
        assert "🏗️  Architectural decisions involved" in output
        assert "🔍 Context7 research required" in output

    def test_statistics_tracking(self, enforcement_gate):
        """Test statistics tracking."""
        # Initial statistics
        stats = enforcement_gate.get_statistics()
        assert stats["decisions_logged"] == 0
        assert "pyinquirer_available" in stats
        assert stats["enforcement_active"] == True

        # Update statistics
        enforcement_gate.decisions_logged = 5

        updated_stats = enforcement_gate.get_statistics()
        assert updated_stats["decisions_logged"] == 5


class TestGlobalGate:
    """Test global gate instance functionality."""

    def test_global_gate_singleton(self):
        """Test that global gate returns same instance."""
        gate1 = get_enforcement_gate()
        gate2 = get_enforcement_gate()

        assert gate1 is gate2


@pytest.mark.asyncio
async def test_integration_complex_task_workflow(enforcement_gate, mock_memory_client):
    """Test complete workflow for complex task enforcement."""
    # Create complex task context
    context = EnforcementContext(
        task_description="Build comprehensive API gateway with rate limiting and authentication",
        estimated_duration=120,
        complexity_score=0.9,
        involves_code=True,
        involves_architecture=True,
        requires_context7=True,
        trigger_reasons=[
            "Estimated duration > 15min (120min)",
            "Involves code implementation",
            "Involves architectural decisions",
            "Requires Context7 research"
        ],
        session_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat()
    )

    # Mock user to choose protocol (non-interactive mode)
    with patch('claude.hooks.devstream.protocol.enforcement_gate.PYINQUIRER_AVAILABLE', False):
        decision = await enforcement_gate.show_enforcement_gate(
            context,
            mock_memory_client
        )

        # Should default to PROTOCOL in non-interactive mode
        assert decision == EnforcementDecision.PROTOCOL

        # Verify decision was logged
        mock_memory_client.store_memory.assert_called_once()


@pytest.mark.asyncio
async def test_integration_override_workflow(enforcement_gate, mock_memory_client):
    """Test override decision workflow."""
    context = EnforcementContext(
        task_description="Quick fix for urgent bug",
        estimated_duration=10,
        complexity_score=0.3,
        involves_code=True,
        involves_architecture=False,
        requires_context7=False,
        trigger_reasons=["Involves code implementation"],
        session_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat()
    )

    # Mock user to choose override
    with patch('claude.hooks.devstream.protocol.enforcement_gate.PYINQUIRER_AVAILABLE', False):
        with patch.dict('os.environ', {'DEVSTREAM_PROTOCOL_OVERRIDE': 'true'}):
            decision = await enforcement_gate.show_enforcement_gate(
                context,
                mock_memory_client
            )

            assert decision == EnforcementDecision.OVERRIDE

            # Verify override decision was logged with risk warnings
            mock_memory_client.store_memory.assert_called_once()
            call_args = mock_memory_client.store_memory.call_args
            content = call_args[1]['content']
            assert "OVERRIDE" in content
            assert "PROTOCOL OVERRIDE - RISKS ACCEPTED" in content
            assert "No Context7 research" in content


if __name__ == "__main__":
    # Run tests directly
    import subprocess
    result = subprocess.run(["pytest", __file__, "-v"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    print(f"Tests completed with exit code: {result.returncode}")