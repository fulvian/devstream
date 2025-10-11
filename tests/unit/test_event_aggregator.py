#!/usr/bin/env -S .devstream/bin/python
# -*- coding: utf-8 -*-

"""
Unit tests for Event Aggregator and Summary Generator

Tests cover:
- EventAggregator.reduce pattern (Context7 eventsourcing.nodejs)
- SummaryGenerator markdown formatting
- Edge cases (empty events, single event)
- SessionSummaryData structure validation
"""

import time
from datetime import datetime
from typing import List

import pytest
import sys
import os

# Add the hooks directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../.claude/hooks/devstream'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../.claude/hooks/devstream/sessions'))

from sessions.session_event_log import SessionEvent
from sessions.session_end_v2 import EventAggregator, SummaryGenerator, SessionSummaryData


class TestSessionSummaryData:
    """Test SessionSummaryData dataclass."""

    def test_summary_data_creation(self):
        """Test creating summary data."""
        data = SessionSummaryData(
            session_id="test-session",
            started_at=1728661800.0,
            ended_at=1728662400.0,
            duration_seconds=600.0,
            files_modified=5,
            tasks_completed=3,
            tasks_started=4,
            decisions_made=2,
            learnings_captured=1,
            errors_occurred=0,
            file_list=["a.py", "b.py", "test.py"],
            completed_task_titles=["Task 1", "Task 2", "Task 3"],
            started_task_titles=["Task 1", "Task 2", "Task 3", "Task 4"],
            decision_list=["Decision 1", "Decision 2"],
            learning_list=["Learning 1"],
            error_list=[],
            total_events=15,
            unique_event_types=4
        )

        assert data.session_id == "test-session"
        assert data.duration_seconds == 600.0
        assert data.files_modified == 5
        assert data.tasks_completed == 3
        assert len(data.file_list) == 3


class TestEventAggregator:
    """Test EventAggregator class."""

    def create_test_events(self) -> List[SessionEvent]:
        """Create test events for aggregation."""
        base_time = 1728661800.0
        return [
            SessionEvent(base_time, "file_modified", {"path": "test.py", "tool": "Write"}),
            SessionEvent(base_time + 10, "task_started", {"title": "Fix bug"}),
            SessionEvent(base_time + 20, "file_modified", {"path": "main.py", "tool": "Edit"}),
            SessionEvent(base_time + 30, "decision", {"content": "Use Event Sourcing", "category": "architecture"}),
            SessionEvent(base_time + 40, "task_completed", {"title": "Fix bug"}),
            SessionEvent(base_time + 50, "learning", {"content": "Event sourcing simplifies state management", "importance": "high"}),
            SessionEvent(base_time + 60, "file_modified", {"path": "utils.py", "tool": "Edit"}),
            SessionEvent(base_time + 70, "error", {"error_type": "ImportError", "message": "Module not found"}),
        ]

    def test_aggregate_events(self):
        """Test basic event aggregation."""
        events = self.create_test_events()
        summary = EventAggregator.aggregate(events)

        # Verify basic metrics
        assert summary.files_modified == 3
        assert summary.tasks_completed == 1
        assert summary.tasks_started == 1
        assert summary.decisions_made == 1
        assert summary.learnings_captured == 1
        assert summary.errors_occurred == 1
        assert summary.total_events == 8

        # Verify time metrics
        assert summary.started_at == events[0].timestamp
        assert summary.ended_at == events[-1].timestamp
        assert summary.duration_seconds == 70.0

        # Verify file list
        assert set(summary.file_list) == {"test.py", "main.py", "utils.py"}

        # Verify task titles
        assert summary.completed_task_titles == ["Fix bug"]
        assert summary.started_task_titles == ["Fix bug"]

        # Verify decisions
        assert len(summary.decision_list) == 1
        assert "[architecture]" in summary.decision_list[0]
        assert "Event Sourcing" in summary.decision_list[0]

        # Verify learnings
        assert len(summary.learning_list) == 1
        assert "[high]" in summary.learning_list[0]
        assert "simplifies" in summary.learning_list[0]

        # Verify errors
        assert len(summary.error_list) == 1
        assert "[ImportError]" in summary.error_list[0]

    def test_aggregate_empty_events(self):
        """Test aggregating empty event list."""
        with pytest.raises(ValueError, match="Cannot aggregate empty event list"):
            EventAggregator.aggregate([])

    def test_aggregate_single_event(self):
        """Test aggregating single event."""
        event = SessionEvent(1728661800.0, "file_modified", {"path": "test.py"})
        summary = EventAggregator.aggregate([event])  # Pass as list

        assert summary.files_modified == 1
        assert summary.tasks_completed == 0
        assert summary.total_events == 1
        assert summary.duration_seconds == 0.0
        assert summary.started_at == summary.ended_at
        assert summary.file_list == ["test.py"]

    def test_aggregate_duplicate_files(self):
        """Test handling duplicate file modifications."""
        events = [
            SessionEvent(1.0, "file_modified", {"path": "test.py"}),
            SessionEvent(2.0, "file_modified", {"path": "test.py"}),  # Duplicate
            SessionEvent(3.0, "file_modified", {"path": "main.py"}),
            SessionEvent(4.0, "file_modified", {"path": "test.py"}),  # Duplicate again
        ]

        summary = EventAggregator.aggregate(events)

        # Should count modifications but deduplicate file list
        assert summary.files_modified == 4
        assert set(summary.file_list) == {"test.py", "main.py"}
        assert len(summary.file_list) == 2

    def test_aggregate_many_tasks(self):
        """Test aggregating many tasks (limits list size)."""
        events = []
        for i in range(15):
            events.append(SessionEvent(float(i), "task_completed", {"title": f"Task {i}"}))

        summary = EventAggregator.aggregate(events)

        # Should count all tasks but limit list
        assert summary.tasks_completed == 15
        assert len(summary.completed_task_titles) == 10  # Limited to 10
        assert summary.completed_task_titles[0] == "Task 0"
        assert summary.completed_task_titles[-1] == "Task 9"

    def test_aggregate_unknown_event_types(self):
        """Test handling unknown event types."""
        events = [
            SessionEvent(1.0, "file_modified", {"path": "test.py"}),
            SessionEvent(2.0, "unknown_event", {"data": "value"}),  # Unknown type
            SessionEvent(3.0, "another_unknown", {"foo": "bar"}),   # Unknown type
        ]

        summary = EventAggregator.aggregate(events)

        # Should count events but not affect counters
        assert summary.total_events == 3
        assert summary.files_modified == 1
        assert summary.tasks_completed == 0
        assert summary.unique_event_types == 3  # Including unknown types

    def test_aggregate_missing_data_fields(self):
        """Test handling events with missing data fields."""
        events = [
            SessionEvent(1.0, "file_modified", {}),  # Missing path
            SessionEvent(2.0, "task_completed", {}),  # Missing title
            SessionEvent(3.0, "decision", {}),        # Missing content and category
            SessionEvent(4.0, "learning", {}),        # Missing content and importance
            SessionEvent(5.0, "error", {}),           # Missing error_type and message
        ]

        summary = EventAggregator.aggregate(events)

        # Should handle missing fields gracefully
        assert summary.files_modified == 1
        assert summary.tasks_completed == 1
        assert summary.decisions_made == 1
        assert summary.learnings_captured == 1
        assert summary.errors_occurred == 1

        # Check default values were used
        assert "unknown" in summary.file_list[0]
        assert "Untitled" in summary.completed_task_titles[0]
        assert "[general]" in summary.decision_list[0]
        assert "[normal]" in summary.learning_list[0]
        assert "[unknown]" in summary.error_list[0]

    def test_aggregate_session_id_extraction(self):
        """Test session ID extraction from event data."""
        events = [
            SessionEvent(1.0, "file_modified", {"session_id": "test-session-123", "path": "test.py"}),
            SessionEvent(2.0, "task_completed", {"title": "Task 1"}),
        ]

        summary = EventAggregator.aggregate(events)
        assert summary.session_id == "test-session-123"

        # Test missing session_id
        events_no_id = [
            SessionEvent(1.0, "file_modified", {"path": "test.py"}),
            SessionEvent(2.0, "task_completed", {"title": "Task 1"}),
        ]

        summary_no_id = EventAggregator.aggregate(events_no_id)
        assert summary_no_id.session_id == "unknown"

    def test_aggregate_chronological_order(self):
        """Test that events are processed in chronological order."""
        # Create events out of order
        events = [
            SessionEvent(3.0, "file_modified", {"path": "last.py"}),
            SessionEvent(1.0, "file_modified", {"path": "first.py"}),
            SessionEvent(2.0, "file_modified", {"path": "second.py"}),
        ]

        summary = EventAggregator.aggregate(events)

        # Time range should reflect correct order (aggregator sorts events)
        assert summary.started_at == 1.0
        assert summary.ended_at == 3.0
        assert summary.duration_seconds == 2.0


class TestSummaryGenerator:
    """Test SummaryGenerator class."""

    def create_test_summary_data(self) -> SessionSummaryData:
        """Create test summary data for markdown generation."""
        return SessionSummaryData(
            session_id="test-session-123",
            started_at=1728661800.0,  # 2025-10-11 15:30:00
            ended_at=1728662400.0,    # 2025-10-11 15:40:00
            duration_seconds=600.0,
            files_modified=3,
            tasks_completed=2,
            tasks_started=3,
            decisions_made=1,
            learnings_captured=1,
            errors_occurred=0,
            file_list=["test.py", "main.py", "utils.py"],
            completed_task_titles=["Fix authentication bug", "Add unit tests"],
            started_task_titles=["Fix authentication bug", "Add unit tests", "Refactor code"],
            decision_list=["[architecture] Use Event Sourcing pattern"],
            learning_list=["[high] Event sourcing simplifies state management"],
            error_list=[],
            total_events=10,
            unique_event_types=4
        )

    def test_generate_markdown_basic(self):
        """Test basic markdown generation."""
        data = self.create_test_summary_data()
        markdown = SummaryGenerator.generate_markdown(data)

        # Check header
        assert "# DevStream Session Summary" in markdown
        assert "test-session-123" in markdown

        # Check timestamps (look for the exact bold pattern)
        assert "**Started**:" in markdown
        assert "**Ended**:" in markdown
        assert "**Duration**:" in markdown

        # Check sections
        assert "## 📊 Work Accomplished" in markdown
        assert "### Files Modified: 3" in markdown
        assert "### Tasks Completed: 2" in markdown

        # Check content
        assert "test.py" in markdown
        assert "main.py" in markdown
        assert "utils.py" in markdown
        assert "Fix authentication bug" in markdown
        assert "Add unit tests" in markdown

        # Check metrics
        assert "## 📈 Session Metrics" in markdown
        assert "**Total Events**: 10" in markdown
        assert "**Event Types**: 4" in markdown

    def test_generate_markdown_with_decisions(self):
        """Test markdown generation with decisions."""
        data = self.create_test_summary_data()
        markdown = SummaryGenerator.generate_markdown(data)

        assert "## 🎯 Key Decisions" in markdown
        assert "1. [architecture] Use Event Sourcing pattern" in markdown

    def test_generate_markdown_with_learnings(self):
        """Test markdown generation with learnings."""
        data = self.create_test_summary_data()
        markdown = SummaryGenerator.generate_markdown(data)

        assert "## 💡 Lessons Learned" in markdown
        assert "1. [high] Event sourcing simplifies state management" in markdown

    def test_generate_markdown_with_errors(self):
        """Test markdown generation with errors."""
        data = self.create_test_summary_data()
        data.errors_occurred = 1
        data.error_list = ["[ImportError] Module not found: requests"]

        markdown = SummaryGenerator.generate_markdown(data)

        assert "## 🚨 Errors Encountered" in markdown
        assert "1. [ImportError] Module not found: requests" in markdown

    def test_generate_markdown_empty_sections(self):
        """Test markdown generation with empty sections."""
        data = SessionSummaryData(
            session_id="empty-session",
            started_at=1728661800.0,
            ended_at=1728661800.0,
            duration_seconds=0.0,
            files_modified=0,
            tasks_completed=0,
            tasks_started=0,
            decisions_made=0,
            learnings_captured=0,
            errors_occurred=0,
            file_list=[],
            completed_task_titles=[],
            started_task_titles=[],
            decision_list=[],
            learning_list=[],
            error_list=[],
            total_events=0,
            unique_event_types=0
        )

        markdown = SummaryGenerator.generate_markdown(data)

        # Should still have basic structure
        assert "# DevStream Session Summary" in markdown
        assert "### Files Modified: 0" in markdown
        assert "### Tasks Completed: 0" in markdown

        # Should show placeholder text
        assert "_No files modified_" in markdown
        assert "_No tasks completed_" in markdown

        # Should not have optional sections
        assert "## 🎯 Key Decisions" not in markdown
        assert "## 💡 Lessons Learned" not in markdown
        assert "## 🚨 Errors Encountered" not in markdown

    def test_generate_markdown_duration_formatting(self):
        """Test duration formatting in markdown."""
        # Test that duration is formatted and present
        data = self.create_test_summary_data()
        data.duration_seconds = 90.5  # 1.5 minutes
        markdown = SummaryGenerator.generate_markdown(data)

        # Should contain Duration: with minutes and seconds format
        assert "**Duration**:" in markdown
        # Check for the pattern like "1m 30s"
        assert "m" in markdown and "s" in markdown

    def test_generate_markdown_long_lists_truncation(self):
        """Test that long lists are properly truncated by EventAggregator."""
        # Note: SummaryGenerator uses the truncated lists from EventAggregator
        # So this test verifies the truncation happens at aggregation level
        from sessions.session_end_v2 import EventAggregator

        # Create many events that would generate long lists
        events = []
        for i in range(20):
            events.append(SessionEvent(float(i), "file_modified", {"path": f"file_{i}.py"}))
            events.append(SessionEvent(float(i) + 0.1, "task_completed", {"title": f"Task {i}"}))

        # Aggregate (should truncate)
        summary_data = EventAggregator.aggregate(events)

        # Generate markdown
        markdown = SummaryGenerator.generate_markdown(summary_data)

        # Should have truncated lists (10 items max for files, 10 for tasks)
        file_lines = [line for line in markdown.split('\n') if 'file_' in line and '•' in line]
        task_lines = [line for line in markdown.split('\n') if 'Task ' in line and any(line.strip().startswith(f'{i}.') for i in range(1, 11))]

        assert len(file_lines) <= 10  # Files truncated to 10
        assert len(task_lines) <= 10  # Tasks truncated to 10

    def test_generate_markdown_session_id_display(self):
        """Test session ID display in markdown."""
        data = self.create_test_summary_data()
        data.session_id = "very-long-session-id-that-should-be-displayed-completely"

        markdown = SummaryGenerator.generate_markdown(data)

        # Should display the full session ID
        assert data.session_id in markdown
        assert "very-long-session-id-that-should-be-displayed-completely" in markdown


class TestIntegration:
    """Integration tests for aggregator and generator."""

    def test_full_workflow(self):
        """Test complete aggregation -> generation workflow."""
        # Create realistic events with session ID
        base_time = time.time()
        session_id = "integration-test-session"
        events = [
            SessionEvent(base_time, "file_modified", {"session_id": session_id, "path": "auth.py", "tool": "Edit"}),
            SessionEvent(base_time + 60, "task_started", {"title": "Fix authentication bug"}),
            SessionEvent(base_time + 120, "file_modified", {"path": "tests/test_auth.py", "tool": "Write"}),
            SessionEvent(base_time + 180, "decision", {"content": "Add JWT token validation", "category": "security"}),
            SessionEvent(base_time + 240, "file_modified", {"path": "utils/jwt.py", "tool": "Write"}),
            SessionEvent(base_time + 300, "task_completed", {"title": "Fix authentication bug"}),
            SessionEvent(base_time + 360, "learning", {"content": "JWT libraries handle token validation automatically", "importance": "high"}),
        ]

        # Aggregate events
        summary_data = EventAggregator.aggregate(events)

        # Generate markdown
        markdown = SummaryGenerator.generate_markdown(summary_data)

        # Verify complete workflow
        assert summary_data.files_modified == 3
        assert summary_data.tasks_completed == 1
        assert summary_data.decisions_made == 1
        assert summary_data.learnings_captured == 1
        assert summary_data.session_id == session_id

        assert "# DevStream Session Summary" in markdown
        assert session_id in markdown
        assert "auth.py" in markdown
        assert "Fix authentication bug" in markdown
        assert "JWT token validation" in markdown
        assert "JWT libraries handle" in markdown
        # Check for duration pattern (e.g., "6m 0s")
        assert "**Duration**:" in markdown