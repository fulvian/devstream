#!/usr/bin/env python3
"""
Unit Tests - SessionCoordinator

Tests for multi-session coordination with PID tracking and file locking.
Target: 95%+ test coverage

Test Categories:
1. Singleton Pattern Tests
2. Session Registration Tests
3. PID Tracking Tests
4. File Locking Tests
5. Heartbeat Tests
6. Cleanup Tests
7. Session Limits Tests
"""

import pytest
import os
import time
import json
import tempfile
from pathlib import Path
import sys

# Add utils to path
sys.path.append(str(Path(__file__).parent.parent.parent / '.claude/hooks/devstream/utils'))
from session_coordinator import SessionCoordinator, SessionInfo, get_session_coordinator


class TestSingletonPattern:
    """Test singleton pattern enforcement."""

    def test_singleton_instance(self):
        """Verify singleton pattern returns same instance."""
        coordinator1 = SessionCoordinator.get_instance()
        coordinator2 = SessionCoordinator.get_instance()

        assert coordinator1 is coordinator2, "Singleton pattern failed"

    def test_singleton_direct_instantiation_blocked(self):
        """Verify direct instantiation is blocked after singleton created."""
        SessionCoordinator.get_instance()

        with pytest.raises(RuntimeError, match="Use SessionCoordinator.get_instance"):
            SessionCoordinator()


class TestSessionRegistration:
    """Test session registration and unregistration."""

    def test_register_session(self, temp_registry):
        """Verify session can be registered."""
        coordinator = SessionCoordinator.get_instance(temp_registry)
        session_id = "test-session-001"

        success = coordinator.register_session(session_id, "data.noindex/devstream.db")

        assert success is True, "Session registration failed"

        # Verify session is in registry
        active_sessions = coordinator.get_active_sessions()
        assert len(active_sessions) == 1
        assert active_sessions[0].session_id == session_id

    def test_register_multiple_sessions(self, temp_registry):
        """Verify multiple sessions can be registered."""
        coordinator = SessionCoordinator.get_instance(temp_registry)

        session_ids = ["session-1", "session-2", "session-3"]
        for sid in session_ids:
            success = coordinator.register_session(sid)
            assert success is True

        active_sessions = coordinator.get_active_sessions()
        assert len(active_sessions) == 3

    def test_unregister_session(self, temp_registry):
        """Verify session can be unregistered."""
        coordinator = SessionCoordinator.get_instance(temp_registry)
        session_id = "test-session-unregister"

        # Register then unregister
        coordinator.register_session(session_id)
        success = coordinator.unregister_session(session_id)

        assert success is True, "Session unregistration failed"

        # Verify session is removed
        active_sessions = coordinator.get_active_sessions()
        assert len(active_sessions) == 0

    def test_unregister_nonexistent_session(self, temp_registry):
        """Verify unregistering nonexistent session returns False."""
        coordinator = SessionCoordinator.get_instance(temp_registry)

        success = coordinator.unregister_session("nonexistent-session")

        assert success is False, "Should fail for nonexistent session"


class TestPIDTracking:
    """Test PID tracking functionality."""

    def test_session_info_stores_pid(self, temp_registry):
        """Verify session info stores current PID."""
        coordinator = SessionCoordinator.get_instance(temp_registry)
        session_id = "test-pid-tracking"

        coordinator.register_session(session_id)
        active_sessions = coordinator.get_active_sessions()

        assert len(active_sessions) == 1
        assert active_sessions[0].pid == os.getpid()

    def test_zombie_detection(self):
        """Verify zombie session detection (non-existent PID)."""
        # Create session info with fake PID
        session_info = SessionInfo(
            session_id="zombie-session",
            pid=999999,  # Non-existent PID
            started_at=time.time(),
            last_heartbeat=time.time(),
            status="active"
        )

        is_zombie = session_info.is_zombie()

        assert is_zombie is True, "Failed to detect zombie session"

    def test_active_session_not_zombie(self):
        """Verify active session is not detected as zombie."""
        session_info = SessionInfo(
            session_id="active-session",
            pid=os.getpid(),
            started_at=time.time(),
            last_heartbeat=time.time(),
            status="active"
        )

        is_zombie = session_info.is_zombie()

        assert is_zombie is False, "Active session incorrectly marked as zombie"


class TestFileLocking:
    """Test file locking functionality."""

    def test_file_lock_acquisition(self, temp_registry):
        """Verify file lock can be acquired."""
        coordinator = SessionCoordinator.get_instance(temp_registry)

        acquired = coordinator._acquire_lock(timeout=2)

        assert acquired is True, "Failed to acquire lock"

        # Release lock
        coordinator._release_lock()

    def test_file_lock_release(self, temp_registry):
        """Verify file lock can be released."""
        coordinator = SessionCoordinator.get_instance(temp_registry)

        coordinator._acquire_lock()
        coordinator._release_lock()

        # Should be able to acquire again after release
        acquired = coordinator._acquire_lock(timeout=1)
        assert acquired is True, "Lock not properly released"

        coordinator._release_lock()

    def test_registry_persistence(self, temp_registry):
        """Verify registry is persisted to file."""
        coordinator = SessionCoordinator.get_instance(temp_registry)
        session_id = "persist-test"

        coordinator.register_session(session_id)

        # Read registry file directly
        with open(temp_registry, 'r') as f:
            data = json.load(f)

        assert session_id in data, "Session not persisted to file"


class TestHeartbeat:
    """Test heartbeat mechanism."""

    def test_update_heartbeat(self, temp_registry):
        """Verify heartbeat can be updated."""
        coordinator = SessionCoordinator.get_instance(temp_registry)
        session_id = "heartbeat-test"

        coordinator.register_session(session_id)

        # Get initial heartbeat
        sessions = coordinator.get_active_sessions()
        initial_heartbeat = sessions[0].last_heartbeat

        # Wait and update
        time.sleep(0.1)
        success = coordinator.update_heartbeat(session_id)

        assert success is True, "Heartbeat update failed"

        # Verify timestamp updated
        sessions = coordinator.get_active_sessions()
        updated_heartbeat = sessions[0].last_heartbeat

        assert updated_heartbeat > initial_heartbeat, "Heartbeat not updated"

    def test_stale_session_detection(self):
        """Verify stale session detection."""
        # Create session with old heartbeat
        old_time = time.time() - 400  # 400 seconds ago
        session_info = SessionInfo(
            session_id="stale-session",
            pid=os.getpid(),
            started_at=old_time,
            last_heartbeat=old_time,
            status="active"
        )

        is_stale = session_info.is_stale(timeout_seconds=300)

        assert is_stale is True, "Failed to detect stale session"

    def test_active_session_not_stale(self):
        """Verify active session is not marked as stale."""
        session_info = SessionInfo(
            session_id="active-session",
            pid=os.getpid(),
            started_at=time.time(),
            last_heartbeat=time.time(),
            status="active"
        )

        is_stale = session_info.is_stale(timeout_seconds=300)

        assert is_stale is False, "Active session incorrectly marked as stale"


class TestCleanup:
    """Test automatic cleanup of stale/zombie sessions."""

    def test_cleanup_zombie_sessions(self, temp_registry):
        """Verify zombie sessions are cleaned up."""
        coordinator = SessionCoordinator.get_instance(temp_registry)

        # Manually add zombie session to registry
        zombie_session = SessionInfo(
            session_id="zombie-cleanup-test",
            pid=999999,  # Non-existent PID
            started_at=time.time(),
            last_heartbeat=time.time(),
            status="active"
        )

        # Write to registry manually
        if coordinator._acquire_lock():
            try:
                sessions = coordinator._read_registry()
                sessions["zombie-cleanup-test"] = zombie_session
                coordinator._write_registry(sessions)
            finally:
                coordinator._release_lock()

        # Bypass rate limiting for test (coordinator._last_cleanup initialized to time.time())
        coordinator._last_cleanup = 0

        # Trigger cleanup
        cleaned = coordinator._cleanup_stale_sessions()

        assert cleaned >= 1, "Zombie session not cleaned up"

        # Verify zombie session removed
        active = coordinator.get_active_sessions()
        zombie_ids = [s.session_id for s in active if s.session_id == "zombie-cleanup-test"]
        assert len(zombie_ids) == 0, "Zombie session still in registry"

    def test_cleanup_rate_limiting(self, temp_registry):
        """Verify cleanup is rate-limited."""
        coordinator = SessionCoordinator.get_instance(temp_registry)

        # First cleanup
        cleaned1 = coordinator._cleanup_stale_sessions()

        # Immediate second cleanup (should be skipped)
        cleaned2 = coordinator._cleanup_stale_sessions()

        assert cleaned2 == 0, "Cleanup not rate-limited"


class TestSessionLimits:
    """Test session limit enforcement."""

    def test_session_count_tracking(self, temp_registry):
        """Verify session count is tracked correctly."""
        coordinator = SessionCoordinator.get_instance(temp_registry)

        # Register 3 sessions
        for i in range(3):
            coordinator.register_session(f"session-{i}")

        count = coordinator.get_session_count()

        assert count == 3, f"Session count incorrect: {count}"

    def test_session_limit_detection(self, temp_registry):
        """Verify session limit detection."""
        coordinator = SessionCoordinator.get_instance(temp_registry)

        # Register sessions up to limit
        max_sessions = coordinator.MAX_SESSIONS
        for i in range(max_sessions):
            coordinator.register_session(f"session-{i}")

        is_limit_reached = coordinator.is_session_limit_reached()

        assert is_limit_reached is True, "Session limit not detected"

    def test_session_limit_enforcement_block_behavior(self, temp_registry):
        """Verify session limit enforcement with block behavior."""
        coordinator = SessionCoordinator.get_instance(temp_registry)

        # Register sessions up to limit
        max_sessions = coordinator.MAX_SESSIONS
        for i in range(max_sessions):
            success = coordinator.register_session(f"session-{i}")
            assert success is True

        # Try to register one more (should fail with block behavior)
        if coordinator.LIMIT_BEHAVIOR == 'block':
            success = coordinator.register_session(f"session-{max_sessions}")
            assert success is False, "Session limit not enforced"


class TestStatistics:
    """Test statistics and metrics."""

    def test_get_stats(self, temp_registry):
        """Verify statistics are returned correctly."""
        coordinator = SessionCoordinator.get_instance(temp_registry)

        stats = coordinator.get_stats()

        assert "active_sessions" in stats
        assert "max_sessions" in stats
        assert "session_utilization" in stats
        assert "registry_path" in stats
        assert "heartbeat_timeout" in stats
        assert "cleanup_interval" in stats

    def test_session_utilization_calculation(self, temp_registry):
        """Verify session utilization is calculated correctly."""
        coordinator = SessionCoordinator.get_instance(temp_registry)

        # Register 2 sessions
        coordinator.register_session("util-session-1")
        coordinator.register_session("util-session-2")

        stats = coordinator.get_stats()
        expected_utilization = 2.0 / coordinator.MAX_SESSIONS

        assert abs(stats["session_utilization"] - expected_utilization) < 0.01


class TestConvenienceFunctions:
    """Test convenience wrapper functions."""

    def test_get_session_coordinator_function(self):
        """Verify get_session_coordinator() returns singleton."""
        coordinator1 = get_session_coordinator()
        coordinator2 = get_session_coordinator()

        assert coordinator1 is coordinator2


# Pytest fixtures
@pytest.fixture
def temp_registry():
    """Create temporary registry file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        registry_path = f.name

    yield registry_path

    # Cleanup
    try:
        os.unlink(registry_path)
        os.unlink(registry_path + '.lock')
    except FileNotFoundError:
        pass


@pytest.fixture(autouse=True)
def cleanup_singleton():
    """Reset singleton between tests."""
    yield
    # Reset singleton
    SessionCoordinator._instance = None


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short", "-x"])
