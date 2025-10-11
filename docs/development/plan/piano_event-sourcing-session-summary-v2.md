# Implementation Plan: Event Sourcing Session Summary Rewrite

**Task ID**: 70749bd53638b4af7f80954192ebef6e
**Model**: GLM-4.6 (Cost-Optimized Execution)
**Status**: Ready for Implementation
**Estimated Duration**: 3-4 hours

---

## 📋 Executive Summary

Rewrite session summary system (6655 LOC → 450 LOC, -93%) using Event Sourcing pattern. Replace triple-source post-hoc inference with in-memory append-only event log. Eliminate timezone bugs, race conditions, and database query overhead.

**Context7 Research Applied**:
- pyeventsourcing (Trust 7.4, 489 snippets) - Append-only pattern
- eventsourcing.nodejs (Trust 9.7, 184 snippets) - Aggregation pattern
- PostgreSQL Event Sourcing (Trust 8.8) - Reference implementation

---

## 🎯 Implementation Checklist

### Phase 1: Core Event Log (1 hour)
- [ ] Create `session_event_log.py` (150 LOC)
  - [ ] `SessionEvent` dataclass (epoch timestamp, type, data)
  - [ ] `SessionEventLog` class (in-memory append-only log)
  - [ ] Thread-safe `record_event()` with asyncio.Lock
  - [ ] Global session registry with `get_session_log()`
  - [ ] `close_session_log()` for cleanup
- [ ] Unit tests: `tests/unit/test_session_event_log.py` (50 LOC)
  - [ ] Test event recording
  - [ ] Test thread-safety
  - [ ] Test registry singleton

### Phase 2: Event Aggregation (1.5 hours)
- [ ] Create `session_end_v2.py` (200 LOC)
  - [ ] `SessionSummaryData` dataclass
  - [ ] `EventAggregator` class with `aggregate()` method
  - [ ] `SummaryGenerator` class with `generate_markdown()`
  - [ ] `SessionEndHookV2` main orchestrator
  - [ ] Integrate with MCP (1x database write)
  - [ ] Atomic marker file write
- [ ] Unit tests: `tests/unit/test_event_aggregator.py` (50 LOC)
  - [ ] Test aggregation logic
  - [ ] Test markdown generation
  - [ ] Test edge cases (empty events, single event)

### Phase 3: PostToolUse Integration (30 minutes)
- [ ] Modify `.claude/hooks/devstream/memory/post_tool_use.py` (+20 LOC)
  - [ ] Import `session_event_log`
  - [ ] Capture "file_modified" events (Write, Edit tools)
  - [ ] Capture "task_completed" events (TodoWrite tool)
  - [ ] Non-blocking error handling

### Phase 4: Integration Tests (30 minutes)
- [ ] Create `tests/integration/test_session_end_v2_workflow.py` (100 LOC)
  - [ ] Test complete workflow (capture → aggregate → store)
  - [ ] Test marker file creation
  - [ ] Test parallel sessions
  - [ ] Test event log cleanup

### Phase 5: Migration Setup (30 minutes)
- [ ] Update `.claude/settings.json` (parallel operation)
  - [ ] Enable both old and new SessionEnd hooks
  - [ ] Add new hook timeout (30s)
- [ ] Create migration validation script
  - [ ] Compare old vs new summaries
  - [ ] Verify 95%+ accuracy
- [ ] Document rollback procedure

---

## 📐 Architecture Specifications

### Component 1: session_event_log.py

```python
@dataclass
class SessionEvent:
    timestamp: float  # Epoch seconds
    type: str         # "file_modified", "task_completed", etc.
    data: Dict[str, Any]

class SessionEventLog:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.events: List[SessionEvent] = []
        self._lock = asyncio.Lock()
    
    async def record_event(self, event_type: str, data: Dict[str, Any]) -> SessionEvent:
        async with self._lock:
            event = SessionEvent(time.time(), event_type, data)
            self.events.append(event)
            return event
```

**Event Types**:
- `file_modified`: {"path": str, "tool": str, "size_bytes": int}
- `task_completed`: {"task_id": str, "title": str}
- `task_started`: {"task_id": str, "title": str}
- `decision`: {"content": str, "category": str}
- `learning`: {"content": str, "importance": str}
- `error`: {"error_type": str, "message": str}

### Component 2: session_end_v2.py

```python
class EventAggregator:
    @staticmethod
    def aggregate(events: List[SessionEvent]) -> SessionSummaryData:
        # Reduce pattern (Context7 eventsourcing.nodejs)
        # Count events by type
        # Collect samples (top 10 files, top 5 decisions, etc.)
        # Return SessionSummaryData

class SummaryGenerator:
    @staticmethod
    def generate_markdown(data: SessionSummaryData) -> str:
        # Generate markdown sections:
        # - Header (session ID, timestamps, duration)
        # - Files Modified (list)
        # - Tasks Completed (list)
        # - Key Decisions (numbered)
        # - Lessons Learned (numbered)
        # - Footer (timestamp)
```

**Workflow**:
1. Get event log from registry
2. Aggregate events (zero database queries)
3. Generate markdown
4. Store in memory via MCP (1x write)
5. Write marker file (atomic)
6. Close event log

### Component 3: PostToolUse Integration

```python
# In post_tool_use.py process_tool_use() method
async def process_tool_use(self, context):
    # ... existing code ...
    
    # NEW: Event capture
    try:
        session_id = os.environ.get("CLAUDE_SESSION_ID", "sess-unknown")
        event_log = await get_session_log(session_id)
        
        if tool_name in ["Write", "Edit", "MultiEdit"]:
            await event_log.record_event("file_modified", {
                "path": str(file_path),
                "tool": tool_name,
                "size_bytes": len(content)
            })
    except Exception as e:
        self.logger.warning(f"Event capture failed: {e}")
```

---

## 🧪 Testing Strategy

### Unit Tests (Total: 150 LOC)

**test_session_event_log.py** (50 LOC):
```python
async def test_record_event():
    log = SessionEventLog("test")
    event = await log.record_event("file_modified", {"path": "test.py"})
    assert event.type == "file_modified"
    assert len(log.events) == 1

async def test_thread_safety():
    # Concurrent writes
    pass

def test_registry_singleton():
    # Same session ID returns same log
    pass
```

**test_event_aggregator.py** (50 LOC):
```python
def test_aggregate_events():
    events = [
        SessionEvent(1.0, "file_modified", {"path": "a.py"}),
        SessionEvent(2.0, "task_completed", {"title": "Fix bug"})
    ]
    summary = EventAggregator.aggregate(events)
    assert summary.files_modified == 1
    assert summary.tasks_completed == 1

def test_markdown_generation():
    # Verify markdown format
    pass
```

**test_summary_generator.py** (50 LOC):
```python
def test_generate_markdown():
    data = SessionSummaryData(...)
    md = SummaryGenerator.generate_markdown(data)
    assert "# DevStream Session Summary" in md
    assert "Files Modified:" in md
```

### Integration Tests (Total: 100 LOC)

**test_session_end_v2_workflow.py**:
```python
async def test_complete_workflow():
    session_id = "test-123"
    log = await get_session_log(session_id)
    
    # Capture events
    await log.record_event("file_modified", {"path": "test.py"})
    await log.record_event("task_completed", {"title": "Implement"})
    
    # Process session end
    hook = SessionEndHookV2()
    success = await hook.process_session_end(session_id)
    
    assert success
    # Verify marker file
    marker_file = Path.home() / ".claude" / "state" / f"devstream_session_{session_id}.txt"
    assert marker_file.exists()
    
    # Verify event log closed
    # ...
```

---

## 📦 File Manifest

**New Files** (Total: 450 LOC):
- `.claude/hooks/devstream/sessions/session_event_log.py` (150 LOC)
- `.claude/hooks/devstream/sessions/session_end_v2.py` (200 LOC)
- `.claude/hooks/devstream/sessions/session_start_v2.py` (100 LOC)

**Modified Files**:
- `.claude/hooks/devstream/memory/post_tool_use.py` (+20 LOC)
- `.claude/settings.json` (add new SessionEnd hook)

**Test Files** (Total: 250 LOC):
- `tests/unit/test_session_event_log.py` (50 LOC)
- `tests/unit/test_event_aggregator.py` (50 LOC)
- `tests/unit/test_summary_generator.py` (50 LOC)
- `tests/integration/test_session_end_v2_workflow.py` (100 LOC)

**Deprecated** (move to `.deprecated/` after validation):
- `session_end.py` (642 LOC)
- `session_data_extractor.py` (1168 LOC)
- `session_summary_generator.py` (946 LOC)
- `session_cleanup_utils.py` (200 LOC)
- `langmem_schema.py` (200 LOC)
- Total: 4500+ LOC removed

---

## 🔍 Quality Gates

**Before Proceeding to Next Phase**:
- ✅ All unit tests pass (100%)
- ✅ All integration tests pass (100%)
- ✅ mypy --strict passes (zero type errors)
- ✅ Code follows Context7 patterns
- ✅ Docstrings for all public methods
- ✅ Error handling for all async operations

**Before Production Deployment**:
- ✅ Parallel operation validation (95%+ accuracy vs old system)
- ✅ Performance validation (SessionEnd <50ms)
- ✅ Memory leak check (no log leaks)
- ✅ Stress test (100 concurrent sessions)

---

## 🚀 Deployment Strategy

### Phase 1: Parallel Operation (Week 1)
```json
{
  "hooks": {
    "SessionEnd": [
      {"hooks": [{"command": ".devstream/bin/python .claude/hooks/devstream/sessions/session_end.py"}]},
      {"hooks": [{"command": ".devstream/bin/python .claude/hooks/devstream/sessions/session_end_v2.py"}]}
    ]
  }
}
```
**Validation**: Compare summaries, log discrepancies

### Phase 2: Switch to v2 Only (Week 2)
```json
{
  "hooks": {
    "SessionEnd": [
      {"hooks": [{"command": ".devstream/bin/python .claude/hooks/devstream/sessions/session_end_v2.py"}]}
    ]
  }
}
```

### Phase 3: Archive Old Code (Week 3)
```bash
mkdir -p .claude/hooks/devstream/sessions/.deprecated
mv session_end.py .deprecated/
# ... move all deprecated files
```

### Phase 4: Cleanup (Week 4)
```bash
rm -rf .deprecated/  # After 30-day grace period
```

---

## 📊 Success Metrics

**Performance**:
- SessionEnd latency: <50ms (vs 200-300ms current)
- Database queries: 0 during session (vs 7-9 current)
- Memory overhead: <50KB (vs 500KB current)

**Quality**:
- Code reduction: 93% (6655 → 450 LOC)
- Test coverage: 100% (new code)
- Race conditions: 0 (append-only)
- Coverage: 100% (vs 90% dual-write)

**Reliability**:
- Zero timestamp bugs (epoch only)
- Zero database query failures (in-memory)
- Zero race conditions (thread-safe append)

---

## 🔄 Rollback Plan

**Emergency Rollback** (if critical issues):
1. Disable v2 in settings.json
2. Re-enable old system
3. No data loss (old code in `.deprecated/`)
4. Instant rollback (<5 minutes)

---

## 📚 Reference Documentation

**Context7 Research**:
- pyeventsourcing: https://eventsourcing.readthedocs.io/
- eventsourcing.nodejs: https://github.com/oskardudycz/eventsourcing.nodejs
- Martin Fowler Event Sourcing: https://martinfowler.com/eaaDev/EventSourcing.html

**DevStream Protocol v2.2.0**:
- Implementation Plans: Protocol v2.2.0 specification
- Strategic Choice Gate: Sonnet→GLM handoff pattern
- Task Management: Core Engine & Infrastructure phase

---

**Generated**: 2025-10-11 by Sonnet 4.5
**Approved for GLM-4.6 Execution**: YES
**Handoff Ready**: YES