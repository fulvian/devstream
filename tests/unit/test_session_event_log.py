#!/usr/bin/env -S .devstream/bin/python
# -*- coding: utf-8 -*-

"""
Unit tests for Session Event Log - Event Sourcing Implementation

Tests cover:
- SessionEvent dataclass validation
- SessionEventLog thread-safe operations
- Registry singleton behavior
- Event filtering and time ranges
- Context7 pattern compliance
"""

import asyncio
import time
from typing import List

import pytest
import sys
import os

# Add the hooks directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../.claude/hooks/devstream'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../.claude/hooks/devstream/sessions'))

from session_event_log import (
    SessionEvent,
    SessionEventLog,
    get_session_log,
    close_session_log,
    get_all_active_sessions,
    cleanup_all_logs,
    validate_event_structure,
    validate_session_log,
    get_registry_stats
)


class TestSessionEvent:
    """Test SessionEvent dataclass."""

    def test_valid_event_creation(self):
        """Test creating valid events."""
        event = SessionEvent(
            timestamp=1728661800.0,
            type="file_modified",
            data={"path": "test.py", "tool": "Write"}
        )

        assert event.timestamp == 1728661800.0
        assert event.type == "file_modified"
        assert event.data["path"] == "test.py"
        assert event.data["tool"] == "Write"

    def test_invalid_timestamp(self):
        """Test event with invalid timestamp."""
        with pytest.raises(TypeError):
            SessionEvent(
                timestamp="2025-10-11",  # String instead of float
                type="file_modified",
                data={}
            )

        with pytest.raises(TypeError):
            SessionEvent(
                timestamp=1728661800,  # Int instead of float
                type="file_modified",
                data={}
            )

    def test_invalid_type(self):
        """Test event with invalid type."""
        with pytest.raises(ValueError, match="type must be non-empty string"):
            SessionEvent(
                timestamp=1728661800.0,
                type="",  # Empty string
                data={}
            )

        with pytest.raises(ValueError, match="type must be non-empty string"):
            SessionEvent(
                timestamp=1728661800.0,
                type="   ",  # Whitespace only
                data={}
            )

        with pytest.raises(ValueError, match="type must be non-empty string"):
            SessionEvent(
                timestamp=1728661800.0,
                type=123,  # Not string
                data={}
            )

    def test_invalid_data(self):
        """Test event with invalid data."""
        with pytest.raises(TypeError):
            SessionEvent(
                timestamp=1728661800.0,
                type="file_modified",
                data="not a dict"  # String instead of dict
            )


class TestSessionEventLog:
    """Test SessionEventLog class."""

    @pytest.mark.asyncio
    async def test_log_creation(self):
        """Test creating event log."""
        log = SessionEventLog("test-session")
        assert log.session_id == "test-session"
        assert len(log.events) == 0

    @pytest.mark.asyncio
    async def test_record_event(self):
        """Test recording events."""
        log = SessionEventLog("test-session")

        event = await log.record_event("file_modified", {"path": "test.py"})

        assert event.type == "file_modified"
        assert event.data["path"] == "test.py"
        assert isinstance(event.timestamp, float)
        assert event.timestamp > 0
        assert len(log.events) == 1

        # Verify event was added to log
        events = log.get_all_events()
        assert len(events) == 1
        assert events[0] is event

    @pytest.mark.asyncio
    async def test_record_multiple_events(self):
        """Test recording multiple events."""
        log = SessionEventLog("test-session")

        await log.record_event("file_modified", {"path": "test.py"})
        await log.record_event("task_completed", {"title": "Fix bug"})
        await log.record_event("decision", {"content": "Use Event Sourcing"})

        assert len(log.events) == 3

        # Verify chronological order
        events = log.get_all_events()
        assert events[0].timestamp < events[1].timestamp < events[2].timestamp

    @pytest.mark.asyncio
    async def test_get_events_by_type(self):
        """Test filtering events by type."""
        log = SessionEventLog("test-session")

        await log.record_event("file_modified", {"path": "test.py"})
        await log.record_event("task_completed", {"title": "Task 1"})
        await log.record_event("file_modified", {"path": "main.py"})
        await log.record_event("task_completed", {"title": "Task 2"})

        file_events = log.get_events_by_type("file_modified")
        task_events = log.get_events_by_type("task_completed")
        other_events = log.get_events_by_type("decision")

        assert len(file_events) == 2
        assert len(task_events) == 2
        assert len(other_events) == 0

        # Verify correct events
        assert file_events[0].data["path"] == "test.py"
        assert file_events[1].data["path"] == "main.py"

    @pytest.mark.asyncio
    async def test_get_time_range(self):
        """Test getting time range of events."""
        log = SessionEventLog("test-session")

        # Empty log
        assert log.get_time_range() is None

        # Single event
        start_time = time.time()
        await log.record_event("file_modified", {"path": "test.py"})

        time_range = log.get_time_range()
        assert time_range is not None
        assert time_range[0] == time_range[1]  # Single event

        # Multiple events
        await asyncio.sleep(0.01)  # Small delay
        await log.record_event("task_completed", {"title": "Task 1"})

        time_range = log.get_time_range()
        assert time_range is not None
        assert time_range[0] < time_range[1]  # Range spans multiple events

    @pytest.mark.asyncio
    async def test_thread_safety_concurrent_writes(self):
        """Test concurrent event recording (thread safety)."""
        log = SessionEventLog("test-session")
        num_tasks = 10

        async def record_events(task_id: int):
            for i in range(5):
                await log.record_event(f"task_{task_id}_event", {"iteration": i})

        # Run concurrent tasks
        tasks = [record_events(i) for i in range(num_tasks)]
        await asyncio.gather(*tasks)

        # Verify all events recorded
        assert len(log.events) == num_tasks * 5

        # Verify no data corruption
        for event in log.events:
            assert isinstance(event.timestamp, float)
            assert isinstance(event.type, str)
            assert isinstance(event.data, dict)

    @pytest.mark.asyncio
    async def test_invalid_event_recording(self):
        """Test recording invalid events."""
        log = SessionEventLog("test-session")

        # Invalid event type
        with pytest.raises(ValueError):
            await log.record_event("", {"data": "test"})

        with pytest.raises(ValueError):
            await log.record_event("   ", {"data": "test"})

        # Invalid data
        with pytest.raises(TypeError):
            await log.record_event("valid_type", "not a dict")

        # Valid event should still work after failures
        event = await log.record_event("valid_type", {"data": "test"})
        assert event.type == "valid_type"
        assert len(log.events) == 1


class TestRegistry:
    """Test session log registry."""

    @pytest.mark.asyncio
    async def test_registry_singleton(self):
        """Test registry returns same instance for same session."""
        session_id = "test-singleton"

        log1 = await get_session_log(session_id)
        log2 = await get_session_log(session_id)

        assert log1 is log2  # Same instance
        assert log1.session_id == session_id

    @pytest.mark.asyncio
    async def test_registry_multiple_sessions(self):
        """Test registry handles multiple sessions."""
        session_ids = ["sess-A", "sess-B", "sess-C"]

        logs = []
        for session_id in session_ids:
            log = await get_session_log(session_id)
            logs.append(log)
            assert log.session_id == session_id

        # Verify all logs are different instances
        for i in range(len(logs)):
            for j in range(i + 1, len(logs)):
                assert logs[i] is not logs[j]

    @pytest.mark.asyncio
    async def test_close_session_log(self):
        """Test closing session logs."""
        session_id = "test-close"

        # Create and use log
        log = await get_session_log(session_id)
        await log.record_event("test", {"data": "value"})

        # Close log
        closed_log = await close_session_log(session_id)
        assert closed_log is log

        # Verify log removed from registry
        new_log = await get_session_log(session_id)
        assert new_log is not log  # New instance
        assert len(new_log.events) == 0  # Empty new log

    @pytest.mark.asyncio
    async def test_close_nonexistent_session(self):
        """Test closing non-existent session."""
        closed_log = await close_session_log("non-existent")
        assert closed_log is None

    @pytest.mark.asyncio
    async def test_get_all_active_sessions(self):
        """Test getting all active sessions."""
        # Start clean
        await cleanup_all_logs()

        session_ids = ["sess-1", "sess-2", "sess-3"]
        for session_id in session_ids:
            await get_session_log(session_id)

        active = await get_all_active_sessions()
        assert set(active) == set(session_ids)

        # Clean up
        await cleanup_all_logs()
        active = await get_all_active_sessions()
        assert len(active) == 0

    @pytest.mark.asyncio
    async def test_cleanup_all_logs(self):
        """Test cleaning up all logs."""
        # Create some logs
        for i in range(5):
            await get_session_log(f"sess-{i}")

        # Verify logs exist
        active_before = await get_all_active_sessions()
        assert len(active_before) == 5

        # Clean up
        cleaned_count = await cleanup_all_logs()
        assert cleaned_count == 5

        # Verify no logs remain
        active_after = await get_all_active_sessions()
        assert len(active_after) == 0


class TestValidation:
    """Test validation functions."""

    def test_validate_event_structure(self):
        """Test event structure validation."""
        # Valid event
        valid_event = SessionEvent(
            timestamp=1728661800.0,
            type="file_modified",
            data={"path": "test.py"}
        )
        assert validate_event_structure(valid_event) is True

        # Test invalid events by bypassing __post_init__ validation
        # Invalid timestamp - create object directly
        invalid_event = object.__new__(SessionEvent)
        invalid_event.timestamp = "2025-10-11"  # String
        invalid_event.type = "file_modified"
        invalid_event.data = {}
        assert validate_event_structure(invalid_event) is False

        # Invalid type
        invalid_event = object.__new__(SessionEvent)
        invalid_event.timestamp = 1728661800.0
        invalid_event.type = ""  # Empty
        invalid_event.data = {}
        assert validate_event_structure(invalid_event) is False

        # Invalid data
        invalid_event = object.__new__(SessionEvent)
        invalid_event.timestamp = 1728661800.0
        invalid_event.type = "file_modified"
        invalid_event.data = "not dict"  # Wrong type
        assert validate_event_structure(invalid_event) is False

        # Negative timestamp
        invalid_event = object.__new__(SessionEvent)
        invalid_event.timestamp = -1.0  # Negative
        invalid_event.type = "file_modified"
        invalid_event.data = {}
        assert validate_event_structure(invalid_event) is False

    @pytest.mark.asyncio
    async def test_validate_session_log(self):
        """Test session log validation."""
        # Valid log
        valid_log = SessionEventLog("test-session")
        await valid_log.record_event("file_modified", {"path": "test.py"})
        assert validate_session_log(valid_log) is True

        # Empty log is valid
        empty_log = SessionEventLog("empty-session")
        assert validate_session_log(empty_log) is True

        # Invalid session ID
        invalid_log = SessionEventLog("")  # Empty session ID
        assert validate_session_log(invalid_log) is False

        # Test chronological order validation
        order_log = SessionEventLog("order-test")

        # Manually add events out of order to test validation
        event1 = SessionEvent(1728661800.0, "type1", {"data": "1"})
        event2 = SessionEvent(1728661700.0, "type2", {"data": "2"})  # Earlier timestamp
        order_log.events = [event1, event2]  # Out of order

        assert validate_session_log(order_log) is False


class TestRegistryStats:
    """Test registry statistics."""

    @pytest.mark.asyncio
    async def test_get_registry_stats(self):
        """Test getting registry statistics."""
        # Start clean
        await cleanup_all_logs()

        # Initial stats
        stats = get_registry_stats()
        assert stats["active_sessions"] == 0
        assert stats["total_events"] == 0
        assert stats["session_ids"] == []

        # Create some logs with events
        log1 = await get_session_log("sess-1")
        await log1.record_event("test", {"data": "1"})
        await log1.record_event("test", {"data": "2"})

        log2 = await get_session_log("sess-2")
        await log2.record_event("test", {"data": "3"})

        # Check updated stats
        stats = get_registry_stats()
        assert stats["active_sessions"] == 2
        assert stats["total_events"] == 3
        assert set(stats["session_ids"]) == {"sess-1", "sess-2"}

        # Clean up
        await cleanup_all_logs()


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_data_defensive_copy(self):
        """Test that event data is defensively copied."""
        log = SessionEventLog("test-session")

        original_data = {"path": "test.py", "count": 1}
        event = await log.record_event("file_modified", original_data)

        # Modify original data after recording
        original_data["path"] = "modified.py"
        original_data["count"] = 999

        # Verify event data wasn't affected
        assert event.data["path"] == "test.py"
        assert event.data["count"] == 1

        # Verify stored event data wasn't affected
        stored_event = log.get_all_events()[0]
        assert stored_event.data["path"] == "test.py"
        assert stored_event.data["count"] == 1

    @pytest.mark.asyncio
    async def test_get_all_events_returns_copy(self):
        """Test that get_all_events returns a copy."""
        log = SessionEventLog("test-session")
        await log.record_event("test", {"data": "value"})

        events = log.get_all_events()
        original_length = len(events)

        # Modify returned list
        events.append(SessionEvent(999.0, "fake", {"data": "fake"}))

        # Verify original log wasn't affected
        assert len(log.events) == original_length
        assert len(log.get_all_events()) == original_length

    @pytest.mark.asyncio
    async def test_concurrent_registry_access(self):
        """Test concurrent access to registry."""
        num_tasks = 10
        session_ids = [f"concurrent-{i}" for i in range(num_tasks)]

        async def create_and_use_log(session_id: str):
            log = await get_session_log(session_id)
            await log.record_event("test", {"session": session_id})
            return log

        # Run concurrent tasks
        tasks = [create_and_use_log(sid) for sid in session_ids]
        logs = await asyncio.gather(*tasks)

        # Verify all logs created and work correctly
        assert len(logs) == num_tasks
        for i, log in enumerate(logs):
            assert log.session_id == session_ids[i]
            assert len(log.events) == 1
            assert log.events[0].data["session"] == session_ids[i]

        # Clean up
        for session_id in session_ids:
            await close_session_log(session_id)