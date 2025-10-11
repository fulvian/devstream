# GLM-4.6 Handoff Prompt: Event Sourcing Session Summary Rewrite

**Handoff Date**: 2025-10-11
**From**: Sonnet 4.5 (Architectural Design)
**To**: GLM-4.6 (Precision Implementation)
**Task ID**: 70749bd53638b4af7f80954192ebef6e
**Plan ID**: 67ebdfde9f2e997735b8f4fcc550076f

---

## 🎯 Mission Statement

You are GLM-4.6, tasked with **precise execution** of Event Sourcing Session Summary System v2 rewrite. Sonnet 4.5 completed ANALYSIS, RESEARCH, and PLANNING. Your job: **IMPLEMENT exactly as specified** in the implementation plan.

**Your Role**: Execution specialist (NOT architect). Follow plan precisely, implement Context7 patterns, write tests, validate quality gates.

---

## 📦 Context Transfer (Complete)

### What Sonnet 4.5 Completed

**✅ STEP 1: DISCUSSION** - Identified problem: Current system over-engineered (6655 LOC), fragile, timezone bugs, race conditions
**✅ STEP 2: ANALYSIS** - Complete architectural audit (14 files, 5 abstraction layers, 3 data sources, 7-9 queries per SessionEnd)
**✅ STEP 3: RESEARCH** - Context7 validation:
  - pyeventsourcing (Trust 7.4, 489 snippets) - Append-only pattern
  - eventsourcing.nodejs (Trust 9.7, 184 snippets) - Aggregation pattern
  - Best practices: Epoch timestamps, in-memory capture, zero-query
**✅ STEP 4: PLANNING** - Complete implementation plan (450 LOC target, 5 phases, test strategy)
**✅ STEP 5: APPROVAL** - User approved Event Sourcing rewrite + GLM-4.6 handoff

### What You Must Implement

**Target**: 450 LOC new code + 250 LOC tests = 700 LOC total
**Timeline**: 3-4 hours
**Quality Gates**: 100% test pass, mypy --strict, Context7 compliance

---

## 📋 Implementation Plan Location

**Primary Reference**: `/Users/fulvioventura/devstream/docs/development/plan/piano_event-sourcing-session-summary-v2.md`

**Read this file IMMEDIATELY** - It contains:
- Complete architecture specifications
- Code templates for all components
- Testing strategy with example code
- Deployment phases
- Success criteria

---

## 🔧 Implementation Checklist (Execute in Order)

### Phase 1: Core Event Log (1 hour)

**File**: `.claude/hooks/devstream/sessions/session_event_log.py` (150 LOC)

**Requirements**:
```python
# MUST implement exactly as specified:

@dataclass
class SessionEvent:
    timestamp: float  # time.time() - Epoch seconds ONLY
    type: str         # Event discriminator
    data: Dict[str, Any]  # Event payload

class SessionEventLog:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.events: List[SessionEvent] = []
        self._lock = asyncio.Lock()  # Thread-safe

    async def record_event(self, event_type: str, data: Dict[str, Any]) -> SessionEvent:
        """Append event to log (Context7 append-only pattern)."""
        async with self._lock:
            event = SessionEvent(
                timestamp=time.time(),  # CRITICAL: Epoch only
                type=event_type,
                data=data
            )
            self.events.append(event)
            return event

    def get_all_events(self) -> List[SessionEvent]:
        """Return all events in chronological order."""
        return self.events.copy()

# Global registry (singleton per session)
_session_logs: Dict[str, SessionEventLog] = {}
_registry_lock = asyncio.Lock()

async def get_session_log(session_id: str) -> SessionEventLog:
    """Get or create session log (thread-safe singleton)."""
    async with _registry_lock:
        if session_id not in _session_logs:
            _session_logs[session_id] = SessionEventLog(session_id)
        return _session_logs[session_id]

async def close_session_log(session_id: str) -> Optional[SessionEventLog]:
    """Close and remove log from registry."""
    async with _registry_lock:
        return _session_logs.pop(session_id, None)
```

**Quality Gates**:
- ✅ mypy --strict passes (full type hints)
- ✅ Epoch timestamps ONLY (no datetime, no ISO)
- ✅ Thread-safe (asyncio.Lock for all mutations)
- ✅ Docstrings for all public methods

**Unit Test**: `tests/unit/test_session_event_log.py` (50 LOC)
```python
import pytest
from session_event_log import SessionEvent, SessionEventLog, get_session_log, close_session_log

@pytest.mark.asyncio
async def test_record_event():
    log = SessionEventLog("test-session")
    event = await log.record_event("file_modified", {"path": "test.py"})

    assert event.type == "file_modified"
    assert event.data["path"] == "test.py"
    assert isinstance(event.timestamp, float)
    assert len(log.events) == 1

@pytest.mark.asyncio
async def test_registry_singleton():
    session_id = "test-singleton"
    log1 = await get_session_log(session_id)
    log2 = await get_session_log(session_id)

    assert log1 is log2  # Same instance

    closed = await close_session_log(session_id)
    assert closed is log1
```

---

### Phase 2: Event Aggregation (1.5 hours)

**File**: `.claude/hooks/devstream/sessions/session_end_v2.py` (200 LOC)

**Requirements**:
```python
@dataclass
class SessionSummaryData:
    """Aggregated session statistics from events."""
    session_id: str
    started_at: float  # Epoch
    ended_at: float
    duration_seconds: float

    # Counters
    files_modified: int
    tasks_completed: int
    tasks_started: int
    decisions_made: int
    learnings_captured: int
    errors_occurred: int

    # Samples (top N)
    file_list: List[str]
    completed_task_titles: List[str]
    decision_list: List[str]
    learning_list: List[str]

class EventAggregator:
    """Context7 Pattern: Array.reduce() aggregation (eventsourcing.nodejs)."""

    @staticmethod
    def aggregate(events: List[SessionEvent]) -> SessionSummaryData:
        """
        Aggregate events into summary data (zero database queries).

        CRITICAL: Use reduce pattern - iterate events, accumulate state.
        """
        if not events:
            raise ValueError("Cannot aggregate empty event list")

        # Initialize counters
        files_modified = 0
        tasks_completed = 0
        # ... all counters

        # Initialize accumulators
        file_set = set()
        task_titles = []
        decisions = []
        learnings = []

        # Reduce events into state
        for event in events:
            if event.type == "file_modified":
                files_modified += 1
                path = event.data.get("path", "unknown")
                file_set.add(path)

            elif event.type == "task_completed":
                tasks_completed += 1
                title = event.data.get("title", "Untitled")
                task_titles.append(title)

            # ... handle all event types

        return SessionSummaryData(
            session_id="...",  # Extract from first event if needed
            started_at=events[0].timestamp,
            ended_at=events[-1].timestamp,
            duration_seconds=events[-1].timestamp - events[0].timestamp,
            files_modified=files_modified,
            # ... all fields
            file_list=list(file_set)[:10],  # Top 10
            completed_task_titles=task_titles[:10],
            decision_list=decisions[:5],
            learning_list=learnings[:5]
        )

class SummaryGenerator:
    """Generate markdown summary from aggregated data."""

    @staticmethod
    def generate_markdown(data: SessionSummaryData) -> str:
        """
        Generate markdown-formatted summary.

        CRITICAL: Use datetime.fromtimestamp(epoch) for display.
        """
        from datetime import datetime

        started = datetime.fromtimestamp(data.started_at).strftime("%Y-%m-%d %H:%M:%S")
        ended = datetime.fromtimestamp(data.ended_at).strftime("%Y-%m-%d %H:%M:%S")
        duration_min = int(data.duration_seconds / 60)

        md = f"""# DevStream Session Summary

**Session**: {data.session_id[:12]}...
**Started**: {started}
**Ended**: {ended}
**Duration**: {duration_min} minutes

---

## 📊 Work Accomplished

### Files Modified: {data.files_modified}
"""
        # ... complete markdown generation (see implementation plan)

        return md

class SessionEndHookV2:
    """SessionEnd hook v2 - Event Sourcing implementation."""

    async def process_session_end(self, session_id: str) -> bool:
        """
        Process session end workflow with Event Sourcing.

        Steps:
        1. Get event log from registry
        2. Aggregate events (zero queries)
        3. Generate summary
        4. Store in memory (1x write)
        5. Write marker file
        6. Close event log
        """
        try:
            # Step 1: Get event log
            event_log = await get_session_log(session_id)
            events = event_log.get_all_events()

            if not events:
                self.base.debug_log("No events - empty session")
                return False

            # Step 2: Aggregate
            aggregator = EventAggregator()
            summary_data = aggregator.aggregate(events)

            # Step 3: Generate markdown
            generator = SummaryGenerator()
            summary_markdown = generator.generate_markdown(summary_data)

            # Step 4: Store in memory (1x database write)
            result = await self.base.safe_mcp_call(
                self.mcp_client,
                "devstream_store_memory",
                {
                    "content": summary_markdown,
                    "content_type": "context",
                    "keywords": ["session", "summary", session_id, "event-sourcing"]
                }
            )

            # Step 5: Write marker file (atomic)
            marker_file = Path.home() / ".claude" / "state" / f"devstream_session_{session_id}.txt"
            marker_file.parent.mkdir(parents=True, exist_ok=True)
            marker_written = await write_atomic(marker_file, summary_markdown)

            # Step 6: Close event log
            await close_session_log(session_id)

            self.base.success_feedback(f"Session ended: {summary_data.tasks_completed} tasks")
            return True

        except Exception as e:
            self.base.debug_log(f"Session end error: {e}")
            return False
```

**Quality Gates**:
- ✅ Zero database queries during aggregation
- ✅ Epoch timestamps for all time calculations
- ✅ Context7 reduce pattern (iterate events, accumulate state)
- ✅ Full type hints + docstrings

**Unit Test**: `tests/unit/test_event_aggregator.py` (50 LOC)
```python
def test_aggregate_events():
    events = [
        SessionEvent(1728661800.0, "file_modified", {"path": "a.py"}),
        SessionEvent(1728661850.0, "task_completed", {"title": "Fix bug"}),
        SessionEvent(1728661900.0, "decision", {"content": "Use Event Sourcing"})
    ]

    summary = EventAggregator.aggregate(events)

    assert summary.files_modified == 1
    assert summary.tasks_completed == 1
    assert summary.decisions_made == 1
    assert summary.duration_seconds == 100.0  # 1900 - 1800
    assert "a.py" in summary.file_list
    assert "Fix bug" in summary.completed_task_titles
```

---

### Phase 3: PostToolUse Integration (30 minutes)

**File**: `.claude/hooks/devstream/memory/post_tool_use.py` (modify existing, +20 LOC)

**Requirements**:
```python
# Add import at top
from sessions.session_event_log import get_session_log

# In process_tool_use() method, AFTER existing logic:
async def process_tool_use(self, context: PostToolUseContext):
    # ... existing code (DO NOT MODIFY) ...

    # NEW: Event capture (add before return)
    try:
        session_id = os.environ.get("CLAUDE_SESSION_ID", "sess-unknown")
        event_log = await get_session_log(session_id)

        # Capture events based on tool
        if tool_name in ["Write", "Edit", "MultiEdit"]:
            await event_log.record_event("file_modified", {
                "path": str(file_path),
                "tool": tool_name,
                "size_bytes": len(content) if content else 0
            })

        elif tool_name == "TodoWrite":
            # Check if task completed (heuristic)
            content_str = str(content).lower()
            if "completed" in content_str or "status\": \"completed" in content_str:
                await event_log.record_event("task_completed", {
                    "task_id": "todo-item",
                    "title": str(content)[:100]
                })

    except Exception as e:
        # Non-blocking - don't fail hook
        self.logger.warning(f"Event capture failed (non-critical): {e}")
```

**Quality Gates**:
- ✅ Non-blocking (wrapped in try-except)
- ✅ Minimal changes to existing code
- ✅ Event types match specification

---

### Phase 4: Integration Tests (30 minutes)

**File**: `tests/integration/test_session_end_v2_workflow.py` (100 LOC)

```python
import pytest
from pathlib import Path
from session_event_log import get_session_log, close_session_log
from session_end_v2 import SessionEndHookV2

@pytest.mark.asyncio
async def test_complete_workflow():
    """Test end-to-end Event Sourcing workflow."""
    session_id = "test-workflow-123"

    # Step 1: Capture events
    log = await get_session_log(session_id)
    await log.record_event("file_modified", {"path": "test.py", "tool": "Edit", "size_bytes": 100})
    await log.record_event("task_completed", {"task_id": "task-1", "title": "Implement feature"})
    await log.record_event("decision", {"content": "Use Event Sourcing", "category": "architecture"})

    # Step 2: Process session end
    hook = SessionEndHookV2()
    success = await hook.process_session_end(session_id)

    assert success

    # Step 3: Verify marker file
    marker_file = Path.home() / ".claude" / "state" / f"devstream_session_{session_id}.txt"
    assert marker_file.exists()

    # Read and verify content
    with open(marker_file, "r") as f:
        content = f.read()

    assert "# DevStream Session Summary" in content
    assert "Files Modified: 1" in content
    assert "Tasks Completed: 1" in content
    assert "test.py" in content
    assert "Implement feature" in content

    # Step 4: Verify event log closed
    # (Registry should be empty for this session)

    # Cleanup
    if marker_file.exists():
        marker_file.unlink()

@pytest.mark.asyncio
async def test_parallel_sessions():
    """Test multiple concurrent sessions."""
    session_ids = ["sess-A", "sess-B", "sess-C"]

    # Create logs for all sessions
    logs = [await get_session_log(sid) for sid in session_ids]

    # Record events concurrently
    for i, log in enumerate(logs):
        await log.record_event("file_modified", {"path": f"file_{i}.py"})

    # Verify isolation (each log has only its events)
    for i, log in enumerate(logs):
        events = log.get_all_events()
        assert len(events) == 1
        assert events[0].data["path"] == f"file_{i}.py"

    # Cleanup
    for sid in session_ids:
        await close_session_log(sid)
```

---

### Phase 5: Migration Setup (30 minutes)

**File**: `.claude/settings.json` (modify)

**Requirements**:
```json
{
  "hooks": {
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/sessions/session_end.py",
            "timeout": 45
          }
        ]
      },
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/sessions/session_end_v2.py",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

**Validation Script**: `scripts/validate_parallel_operation.py`
```python
#!/usr/bin/env python3
"""
Validate parallel operation of old and new SessionEnd hooks.
Compare summaries for accuracy.
"""

import asyncio
from pathlib import Path

async def compare_summaries():
    """Compare old vs new summaries for same session."""
    # Read marker files
    state_dir = Path.home() / ".claude" / "state"

    # Logic: Compare content, identify discrepancies
    # Target: 95%+ accuracy

    pass

if __name__ == "__main__":
    asyncio.run(compare_summaries())
```

---

## 🎯 Quality Gates (MANDATORY)

### Before Proceeding to Next Phase
- ✅ All unit tests pass (100%)
- ✅ mypy --strict passes (zero type errors)
- ✅ Full docstrings for all public methods
- ✅ Code follows Context7 patterns exactly
- ✅ Error handling for all async operations

### Before Requesting Review
- ✅ All integration tests pass (100%)
- ✅ Parallel operation validated (95%+ accuracy)
- ✅ Performance validated (SessionEnd <50ms)
- ✅ No memory leaks (event logs properly closed)

---

## 🚨 Critical Don'ts (FORBIDDEN)

❌ **DO NOT** use datetime objects internally (Epoch float ONLY)
❌ **DO NOT** query database during event aggregation (in-memory only)
❌ **DO NOT** modify existing old system code (parallel operation)
❌ **DO NOT** skip tests (100% coverage required)
❌ **DO NOT** deviate from Context7 patterns (append-only, reduce)
❌ **DO NOT** use naive timestamps or ISO strings (Epoch ONLY)

---

## ✅ Success Criteria

**Code Metrics**:
- Total LOC: 450 new + 250 tests = 700 LOC
- Test coverage: 100% for new code
- mypy --strict: Zero errors
- Performance: SessionEnd <50ms

**Functional**:
- Zero database queries during session
- 1x database write at SessionEnd
- Zero race conditions (thread-safe)
- 100% event capture (no data loss)

**Quality**:
- Context7 patterns applied correctly
- Full type hints + docstrings
- Error handling for all async
- Clean rollback path

---

## 📞 Communication Protocol

**When to Ask Sonnet 4.5**:
- Architectural ambiguity (unclear design decisions)
- Deviation from plan required (explain why)
- Blocked by external dependencies
- Quality gates fail repeatedly

**When to Proceed Independently**:
- Implementation details (variable names, private methods)
- Test case variations
- Code organization within files
- Error message wording

**Status Updates**:
- Report after each phase completion
- Report any deviations from plan
- Report test results (pass/fail)

---

## 🔗 Key File Paths

**Implementation Plan**: `/Users/fulvioventura/devstream/docs/development/plan/piano_event-sourcing-session-summary-v2.md`

**New Files** (create these):
- `.claude/hooks/devstream/sessions/session_event_log.py`
- `.claude/hooks/devstream/sessions/session_end_v2.py`
- `tests/unit/test_session_event_log.py`
- `tests/unit/test_event_aggregator.py`
- `tests/integration/test_session_end_v2_workflow.py`

**Modified Files**:
- `.claude/hooks/devstream/memory/post_tool_use.py` (+20 LOC)
- `.claude/settings.json` (add SessionEnd hook)

**Reference Files** (read for context):
- `.claude/hooks/devstream/sessions/session_end.py` (old system - DON'T MODIFY)
- `.claude/hooks/devstream/utils/atomic_file_writer.py` (reuse)
- `.claude/hooks/devstream/utils/devstream_base.py` (reuse)

---

## 🚀 Execution Start Command

**When ready to implement**:

```bash
# 1. Read implementation plan
cat /Users/fulvioventura/devstream/docs/development/plan/piano_event-sourcing-session-summary-v2.md

# 2. Create session_event_log.py (Phase 1)
# 3. Write unit tests
# 4. Run tests: .devstream/bin/python -m pytest tests/unit/test_session_event_log.py -v
# 5. Proceed to Phase 2...
```

---

**Handoff Complete**: You are now authorized to begin implementation. Follow plan precisely, validate quality gates, report progress. Good luck! 🚀

**Sonnet 4.5 signing off. GLM-4.6, you have the controls.**
