#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pytest>=7.0.0",
#     "pytest-asyncio>=0.21.0",
#     "pytest-cov>=4.0.0",
#     "aiofiles>=23.0.0",
#     "structlog>=23.0.0",
#     "cryptography>=41.0.0",
#     "cachetools>=5.0.0",
# ]
# ///

"""
Test suite for Protocol State Manager component.

Tests atomic state persistence, session management, step advancement,
and crash recovery capabilities of the protocol state manager.
"""

import asyncio
import json
import pytest
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'protocol'))

from protocol_state_manager import (
    ProtocolStateManager,
    ProtocolStep,
    ProtocolState,
    get_protocol_manager
)


@pytest.fixture
async def temp_state_file():
    """Create temporary state file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = Path(f.name)

    yield temp_file

    # Cleanup
    if temp_file.exists():
        temp_file.unlink()


@pytest.fixture
async def state_manager(temp_state_file):
    """Create protocol state manager with temporary file."""
    return ProtocolStateManager(temp_state_file)


@pytest.fixture
def sample_session_id():
    """Sample session ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_state(sample_session_id):
    """Sample protocol state for testing."""
    return ProtocolState(
        session_id=sample_session_id,
        protocol_step=ProtocolStep.DISCUSSION,
        task_id="task-123",
        start_time=datetime.now(timezone.utc).isoformat(),
        last_updated=datetime.now(timezone.utc).isoformat(),
        metadata={"test": "data"}
    )


class TestProtocolStep:
    """Test ProtocolStep enum functionality."""

    def test_step_enum_values(self):
        """Test that all required steps are defined."""
        expected_steps = [
            ProtocolStep.IDLE,
            ProtocolStep.DISCUSSION,
            ProtocolStep.ANALYSIS,
            ProtocolStep.RESEARCH,
            ProtocolStep.PLANNING,
            ProtocolStep.APPROVAL,
            ProtocolStep.IMPLEMENTATION,
            ProtocolStep.VERIFICATION
        ]

        assert len(expected_steps) == 8

        # Test step values
        assert ProtocolStep.IDLE.value == 0
        assert ProtocolStep.DISCUSSION.value == 1
        assert ProtocolStep.VERIFICATION.value == 7

    def test_from_int_conversion(self):
        """Test integer to ProtocolStep conversion."""
        assert ProtocolStep.from_int(0) == ProtocolStep.IDLE
        assert ProtocolStep.from_int(1) == ProtocolStep.DISCUSSION
        assert ProtocolStep.from_int(7) == ProtocolStep.VERIFICATION

        # Test invalid values
        with pytest.raises(ValueError, match="Invalid protocol step"):
            ProtocolStep.from_int(8)

    def test_string_representation(self):
        """Test string representation of steps."""
        assert str(ProtocolStep.IDLE) == "Idle"
        assert str(ProtocolStep.DISCUSSION) == "Step 1: DISCUSSION"
        assert str(ProtocolStep.VERIFICATION) == "Step 7: VERIFICATION"

    def test_step_transition_validation(self):
        """Test step transition validation."""
        # Valid transitions from IDLE
        assert ProtocolStep.IDLE.is_valid_next_step(ProtocolStep.DISCUSSION)
        assert not ProtocolStep.IDLE.is_valid_next_step(ProtocolStep.ANALYSIS)

        # Valid sequential transitions
        assert ProtocolStep.DISCUSSION.is_valid_next_step(ProtocolStep.ANALYSIS)
        assert ProtocolStep.ANALYSIS.is_valid_next_step(ProtocolStep.RESEARCH)
        assert ProtocolStep.RESEARCH.is_valid_next_step(ProtocolStep.PLANNING)
        assert ProtocolStep.PLANNING.is_valid_next_step(ProtocolStep.APPROVAL)
        assert ProtocolStep.APPROVAL.is_valid_next_step(ProtocolStep.IMPLEMENTATION)
        assert ProtocolStep.IMPLEMENTATION.is_valid_next_step(ProtocolStep.VERIFICATION)

        # Invalid transitions
        assert not ProtocolStep.DISCUSSION.is_valid_next_step(ProtocolStep.VERIFICATION)
        assert not ProtocolStep.ANALYSIS.is_valid_next_step(ProtocolStep.IDLE)


class TestProtocolState:
    """Test ProtocolState dataclass functionality."""

    def test_state_creation(self, sample_session_id):
        """Test basic state creation."""
        state = ProtocolState(
            session_id=sample_session_id,
            protocol_step=ProtocolStep.IDLE
        )

        assert state.session_id == sample_session_id
        assert state.protocol_step == ProtocolStep.IDLE
        assert state.task_id is None
        assert state.start_time is not None
        assert state.last_updated is not None
        assert state.metadata == {}

    def test_state_creation_with_all_fields(self, sample_session_id):
        """Test state creation with all fields."""
        start_time = datetime.now(timezone.utc).isoformat()
        state = ProtocolState(
            session_id=sample_session_id,
            protocol_step=ProtocolStep.DISCUSSION,
            task_id="task-123",
            start_time=start_time,
            last_updated=start_time,
            metadata={"key": "value"}
        )

        assert state.session_id == sample_session_id
        assert state.protocol_step == ProtocolStep.DISCUSSION
        assert state.task_id == "task-123"
        assert state.start_time == start_time
        assert state.metadata == {"key": "value"}

    def test_invalid_session_id_format(self):
        """Test validation of session ID format."""
        with pytest.raises(ValueError, match="Invalid session_id format"):
            ProtocolState(
                session_id="invalid-uuid",
                protocol_step=ProtocolStep.IDLE
            )

    def test_dict_conversion(self, sample_session_id):
        """Test dictionary conversion."""
        state = ProtocolState(
            session_id=sample_session_id,
            protocol_step=ProtocolStep.DISCUSSION,
            task_id="task-123",
            metadata={"test": "data"}
        )

        # Convert to dict
        state_dict = state.to_dict()
        assert state_dict["session_id"] == sample_session_id
        assert state_dict["protocol_step"] == 1  # Enum value
        assert state_dict["task_id"] == "task-123"

        # Convert from dict
        restored_state = ProtocolState.from_dict(state_dict)
        assert restored_state.session_id == state.session_id
        assert restored_state.protocol_step == state.protocol_step
        assert restored_state.task_id == state.task_id

    def test_checksum_calculation(self, sample_session_id):
        """Test checksum calculation for state validation."""
        state = ProtocolState(
            session_id=sample_session_id,
            protocol_step=ProtocolStep.DISCUSSION,
            metadata={"test": "data"}
        )

        # Calculate checksum
        checksum = state.calculate_checksum()
        assert checksum is not None
        assert len(checksum) == 64  # SHA256 hex digest

        # Consistency check
        checksum2 = state.calculate_checksum()
        assert checksum == checksum2

    def test_state_validation(self, sample_session_id):
        """Test state integrity validation."""
        state = ProtocolState(
            session_id=sample_session_id,
            protocol_step=ProtocolStep.DISCUSSION
        )

        # Valid state should have checksum
        state.checksum = state.calculate_checksum()
        assert state.is_valid()

        # Invalid checksum should fail validation
        state.checksum = "invalid_checksum"
        assert not state.is_valid()

        # Missing checksum should fail validation
        state.checksum = None
        assert not state.is_valid()

    def test_immutable_updates(self, sample_session_id):
        """Test immutable state updates."""
        original_state = ProtocolState(
            session_id=sample_session_id,
            protocol_step=ProtocolStep.DISCUSSION,
            task_id="task-123"
        )

        # Update step
        updated_state = original_state.with_updates(protocol_step=ProtocolStep.ANALYSIS)

        # Original should be unchanged
        assert original_state.protocol_step == ProtocolStep.DISCUSSION
        assert updated_state.protocol_step == ProtocolStep.ANALYSIS
        assert updated_state.session_id == original_state.session_id
        assert updated_state.last_updated != original_state.last_updated


class TestProtocolStateManager:
    """Test ProtocolStateManager functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, state_manager, temp_state_file):
        """Test manager initialization."""
        assert state_manager.state_file == temp_state_file
        assert state_manager.lock_file == temp_state_file.with_suffix('.lock')
        assert not state_manager._cache_key in state_manager._cache

    @pytest.mark.asyncio
    async def test_new_session_initialization(self, state_manager, temp_state_file):
        """Test new session initialization."""
        # File doesn't exist initially
        assert not temp_state_file.exists()

        # Initialize session
        state = await state_manager.initialize_session()

        # Verify state properties
        assert state.protocol_step == ProtocolStep.IDLE
        assert state.session_id is not None
        assert state.is_valid()

        # Verify file was created
        assert temp_state_file.exists()

        # Verify file contents
        content = temp_state_file.read_text()
        saved_data = json.loads(content)
        assert saved_data["session_id"] == state.session_id
        assert saved_data["protocol_step"] == 0

    @pytest.mark.asyncio
    async def test_session_recovery(self, state_manager, temp_state_file, sample_state):
        """Test session recovery from existing state."""
        # Save initial state
        await state_manager._save_state(sample_state)

        # Create new manager instance
        new_manager = ProtocolStateManager(temp_state_file)

        # Recover session
        recovered_state = await new_manager.initialize_session()

        # Verify recovery
        assert recovered_state.session_id == sample_state.session_id
        assert recovered_state.protocol_step == sample_state.protocol_step
        assert recovered_state.task_id == sample_state.task_id

    @pytest.mark.asyncio
    async def test_step_advancement(self, state_manager, sample_session_id):
        """Test step advancement with validation."""
        # Start with idle state
        initial_state = await state_manager.initialize_session()
        assert initial_state.protocol_step == ProtocolStep.IDLE

        # Advance to discussion (valid)
        discussion_state = await state_manager.advance_step(
            initial_state,
            ProtocolStep.DISCUSSION,
            task_id="task-123"
        )
        assert discussion_state.protocol_step == ProtocolStep.DISCUSSION
        assert discussion_state.task_id == "task-123"

        # Try invalid transition (should fail)
        with pytest.raises(ValueError, match="Invalid step transition"):
            await state_manager.advance_step(
                discussion_state,
                ProtocolStep.VERIFICATION  # Skip steps
            )

        # Valid sequential transition
        analysis_state = await state_manager.advance_step(
            discussion_state,
            ProtocolStep.ANALYSIS
        )
        assert analysis_state.protocol_step == ProtocolStep.ANALYSIS

    @pytest.mark.asyncio
    async def test_force_step_advancement(self, state_manager, sample_session_id):
        """Test forced step advancement (for recovery)."""
        initial_state = await state_manager.initialize_session()

        # Force invalid transition
        forced_state = await state_manager.advance_step(
            initial_state,
            ProtocolStep.VERIFICATION,
            force=True
        )
        assert forced_state.protocol_step == ProtocolStep.VERIFICATION

    @pytest.mark.asyncio
    async def test_state_persistence_and_retrieval(self, state_manager, sample_session_id):
        """Test state persistence and retrieval with caching."""
        # Create and save state
        original_state = await state_manager.initialize_session()
        updated_state = await state_manager.advance_step(
            original_state,
            ProtocolStep.DISCUSSION,
            task_id="task-123"
        )

        # Retrieve from cache
        cached_state = await state_manager.get_current_state()
        assert cached_state.session_id == updated_state.session_id
        assert cached_state.protocol_step == updated_state.protocol_step
        assert cached_state.task_id == updated_state.task_id

        # Verify cache usage
        assert state_manager._cache_key in state_manager._cache

    @pytest.mark.asyncio
    async def test_session_reset(self, state_manager, sample_session_id):
        """Test session reset functionality."""
        # Setup session with progress
        initial_state = await state_manager.initialize_session()
        progressed_state = await state_manager.advance_step(
            initial_state,
            ProtocolStep.DISCUSSION,
            task_id="task-123"
        )

        # Reset session
        reset_state = await state_manager.reset_session()

        # Verify reset
        assert reset_state.protocol_step == ProtocolStep.IDLE
        assert reset_state.task_id is None
        assert reset_state.session_id != progressed_state.session_id

    @pytest.mark.asyncio
    async def test_corrupted_state_handling(self, state_manager, temp_state_file):
        """Test handling of corrupted state files."""
        # Create corrupted state file
        temp_state_file.write_text('{"invalid": "json"}')

        # Should handle gracefully and create new session
        state = await state_manager.initialize_session()
        assert state.protocol_step == ProtocolStep.IDLE
        assert state.is_valid()

    @pytest.mark.asyncio
    async def test_empty_state_file_handling(self, state_manager, temp_state_file):
        """Test handling of empty state files."""
        # Create empty state file
        temp_state_file.write_text("")

        # Should handle gracefully and create new session
        state = await state_manager.initialize_session()
        assert state.protocol_step == ProtocolStep.IDLE
        assert state.is_valid()

    @pytest.mark.asyncio
    async def test_session_status(self, state_manager, sample_session_id):
        """Test session status reporting."""
        # Create session with progress
        initial_state = await state_manager.initialize_session()
        progressed_state = await state_manager.advance_step(
            initial_state,
            ProtocolStep.DISCUSSION,
            task_id="task-123"
        )

        # Get status
        status = state_manager.get_session_status(progressed_state)

        # Verify status contents
        assert status["session_id"] == progressed_state.session_id
        assert status["current_step"] == "Step 1: DISCUSSION"
        assert status["step_number"] == 1
        assert status["task_id"] == "task-123"
        assert status["is_valid"] == True
        assert "duration_seconds" in status

    @pytest.mark.asyncio
    async def test_concurrent_session_handling(self, state_manager, temp_state_file):
        """Test handling of concurrent session access."""
        # Create first session
        session1 = await state_manager.initialize_session()
        session1_id = session1.session_id

        # Create second session (different manager)
        manager2 = ProtocolStateManager(temp_state_file)
        session2 = await manager2.initialize_session()

        # Should be different sessions
        assert session2.session_id != session1_id

        # Each should maintain its own state
        await state_manager.advance_step(session1, ProtocolStep.DISCUSSION)
        await manager2.advance_step(session2, ProtocolStep.ANALYSIS)

        # Verify states are independent
        final_session1 = await state_manager.get_current_state()
        final_session2 = await manager2.get_current_state()

        assert final_session1.protocol_step == ProtocolStep.DISCUSSION
        assert final_session2.protocol_step == ProtocolStep.ANALYSIS


class TestGlobalManager:
    """Test global manager instance functionality."""

    @pytest.mark.asyncio
    async def test_global_manager_singleton(self):
        """Test that global manager returns same instance."""
        manager1 = get_protocol_manager()
        manager2 = get_protocol_manager()

        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_global_manager_session_initialization(self):
        """Test global manager session initialization convenience function."""
        from protocol_state_manager import initialize_protocol_session

        state = await initialize_protocol_session()
        assert state.protocol_step == ProtocolStep.IDLE
        assert state.session_id is not None
        assert state.is_valid()


@pytest.mark.asyncio
async def test_integration_workflow(state_manager, temp_state_file):
    """Test complete integration workflow."""
    # Initialize session
    state = await state_manager.initialize_session()
    assert state.protocol_step == ProtocolStep.IDLE

    # Progress through all steps
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
        state = await state_manager.advance_step(state, step, task_id=f"task-{step.value}")
        assert state.protocol_step == step

    # Verify final state
    assert state.protocol_step == ProtocolStep.VERIFICATION

    # Test status reporting
    status = state_manager.get_session_status(state)
    assert status["step_number"] == 7
    assert status["is_valid"] == True

    # Test session reset
    reset_state = await state_manager.reset_session()
    assert reset_state.protocol_step == ProtocolStep.IDLE


if __name__ == "__main__":
    # Run tests directly
    import subprocess
    result = subprocess.run(["pytest", __file__, "-v"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    print(f"Tests completed with exit code: {result.returncode}")