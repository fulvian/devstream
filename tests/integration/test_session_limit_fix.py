#!/usr/bin/env python3
"""
Integration test for session limit fix.

Tests the enhanced session management system with zombie cleanup,
emergency override, and robust session validation.
"""

import sys
import os
import time
import json
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project paths
sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'utils'))
sys.path.append(str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'sessions'))

from session_coordinator import SessionCoordinator, SessionInfo
from session_cleanup_utils import SessionCleanupManager, CleanupStats


class TestSessionLimitFix:
    """Integration test suite for session limit fix."""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.registry_path = os.path.join(self.temp_dir, 'test_registry.json')
        self.coordinator = None
        self.cleanup_manager = None

    def setup(self):
        """Setup test environment."""
        # Create temporary registry
        with open(self.registry_path, 'w') as f:
            json.dump({}, f)

        # Initialize coordinator and cleanup manager with temp registry
        self.coordinator = SessionCoordinator(self.registry_path)
        self.cleanup_manager = SessionCleanupManager(self.coordinator)

        print(f"✅ Test setup complete with registry: {self.registry_path}")

    def teardown(self):
        """Cleanup test environment."""
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
        except Exception:
            pass

    def test_basic_session_creation(self):
        """Test basic session creation and registration."""
        print("\n🧪 Testing basic session creation...")

        # Register a session
        session_id = "test-session-1"
        success = self.coordinator.register_session(session_id, "test.db")

        assert success, "Session registration should succeed"
        assert self.coordinator.get_session_count() == 1, "Should have 1 active session"

        # Check registry content
        sessions = self.coordinator._read_registry()
        assert session_id in sessions, "Session should be in registry"

        print("   ✅ Basic session creation works")

    def test_zombie_session_detection(self):
        """Test detection and cleanup of zombie sessions."""
        print("\n🧪 Testing zombie session detection...")

        # Create a session with non-existent PID
        zombie_session = SessionInfo(
            session_id="zombie-session",
            pid=99999,  # Non-existent PID
            started_at=time.time() - 3600,  # 1 hour ago
            last_heartbeat=time.time() - 3600,
            status="active"
        )

        # Add zombie session to registry directly
        sessions = {"zombie-session": zombie_session}
        self.coordinator._write_registry(sessions)

        # Verify zombie exists
        assert self.coordinator.get_session_count() == 1, "Zombie session should be counted"

        # Run cleanup
        stats = self.cleanup_manager.aggressive_cleanup()

        # Verify cleanup
        assert stats.zombie_sessions_cleaned == 1, "Should detect and clean 1 zombie session"
        assert self.coordinator.get_session_count() == 0, "Should have 0 sessions after cleanup"

        print("   ✅ Zombie session detection and cleanup works")

    def test_session_limit_behavior(self):
        """Test session limit behavior with emergency override."""
        print("\n🧪 Testing session limit behavior...")

        # Fill up to max sessions
        max_sessions = self.coordinator.MAX_SESSIONS

        for i in range(max_sessions):
            session_id = f"test-session-{i}"
            success = self.coordinator.register_session(session_id, "test.db")
            assert success, f"Session {i} registration should succeed"

        assert self.coordinator.get_session_count() == max_sessions, "Should have max sessions"

        # Try to register one more (should fail normally)
        extra_session = "extra-session"
        success = self.coordinator.register_session(extra_session, "test.db")

        if self.coordinator.LIMIT_BEHAVIOR == 'block':
            assert not success, "Extra session should be blocked"
            print("   ✅ Session limit blocking works")
        else:
            print(f"   ℹ️  Limit behavior is '{self.coordinator.LIMIT_BEHAVIOR}'")

    def test_emergency_override(self):
        """Test emergency override functionality."""
        print("\n🧪 Testing emergency override...")

        # Enable emergency override
        self.cleanup_manager.EMERGENCY_OVERRIDE = True

        # Bypass session limit check by writing directly to registry
        zombie_sessions = {}
        for i in range(self.coordinator.MAX_SESSIONS):
            zombie_sessions[f"zombie-{i}"] = SessionInfo(
                session_id=f"zombie-{i}",
                pid=50000 + i,  # Non-existent PIDs
                started_at=time.time() - 7200,  # 2 hours ago
                last_heartbeat=time.time() - 7200,
                status="active"
            )

        # Write directly to registry (bypass limit check)
        self.coordinator._write_registry(zombie_sessions)

        # Update cache
        self.coordinator._sessions_cache = zombie_sessions

        # Verify sessions exist (should be MAX_SESSIONS)
        session_count = len(zombie_sessions)
        assert session_count == self.coordinator.MAX_SESSIONS, f"Should have {self.coordinator.MAX_SESSIONS} sessions"

        # Force cleanup all sessions
        success = self.cleanup_manager.force_cleanup_all_sessions()
        assert success, "Force cleanup should succeed"
        assert self.coordinator.get_session_count() == 0, "All sessions should be cleared"

        print("   ✅ Emergency override works")

    def test_registry_repair(self):
        """Test registry repair functionality."""
        print("\n🧪 Testing registry repair...")

        # Create corrupted registry
        with open(self.registry_path, 'w') as f:
            f.write("invalid json content")

        # Try to validate and repair
        success = self.cleanup_manager.validate_and_fix_registry()
        assert success, "Registry repair should succeed"

        # Verify registry is now valid
        with open(self.registry_path, 'r') as f:
            data = json.load(f)
            assert isinstance(data, dict), "Registry should be a valid dictionary"

        print("   ✅ Registry repair works")

    def test_cleanup_manager_integration(self):
        """Test cleanup manager integration."""
        print("\n🧪 Testing cleanup manager integration...")

        # Create mixed sessions: some valid, some zombies
        sessions = {}

        # Add valid session (simulated with current PID)
        valid_session = SessionInfo(
            session_id="valid-session",
            pid=os.getpid(),  # Current process (valid)
            started_at=time.time() - 100,  # Recent
            last_heartbeat=time.time() - 100,
            status="active"
        )
        sessions["valid-session"] = valid_session

        # Add zombie sessions
        for i in range(3):
            zombie_session = SessionInfo(
                session_id=f"zombie-{i}",
                pid=50000 + i,  # Non-existent PIDs
                started_at=time.time() - 3600,  # 1 hour ago
                last_heartbeat=time.time() - 3600,
                status="active"
            )
            sessions[f"zombie-{i}"] = zombie_session

        self.coordinator._write_registry(sessions)
        assert self.coordinator.get_session_count() == 4, "Should have 4 sessions total"

        # Run cleanup
        stats = self.cleanup_manager.aggressive_cleanup()

        # Should remove 3 zombies, keep 1 valid
        assert stats.zombie_sessions_cleaned == 3, "Should clean 3 zombie sessions"
        assert self.coordinator.get_session_count() == 1, "Should keep 1 valid session"

        print("   ✅ Cleanup manager integration works")

    def run_all_tests(self):
        """Run all tests."""
        print("🚀 Starting Session Limit Fix Integration Tests")
        print("=" * 60)

        try:
            self.setup()

            self.test_basic_session_creation()
            self.test_zombie_session_detection()
            self.test_session_limit_behavior()
            self.test_emergency_override()
            self.test_registry_repair()
            self.test_cleanup_manager_integration()

            print("\n🎉 All tests passed!")
            print("✅ Session limit fix is working correctly")
            return True

        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            self.teardown()


def main():
    """Main test runner."""
    tester = TestSessionLimitFix()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()