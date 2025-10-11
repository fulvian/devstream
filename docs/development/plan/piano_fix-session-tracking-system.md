# Implementation Plan: Fix Session Tracking System (Multi-Session Safe)

**Task ID**: ad87f91d05af48a9991e8f744359848f
**Model**: Sonnet 4.5 (Architectural/Complex Reasoning)
**Priority**: 9/10
**Estimated Duration**: 4-5 hours
**Revision**: v2 - Multi-Session Compatibility Added

---

## Executive Summary

Fix critical bugs in DevStream session tracking system causing empty summaries, double session creation, zombie sessions, and incorrect duration calculations. Root cause: PostToolUse session tracking code disabled due to missing `active_files` parameter in WorkSessionManager.

**NEW (v2)**: Extended to handle multi-session scenarios (Sonnet 4.5 + GLM-4.6 concurrent sessions) with environment-based session identification and session_id-based idempotency.

---

## Architecture Decisions

### ADR-001: Enable Session Tracking via WorkSessionManager Extension

**Context**: PostToolUse hook has session tracking code disabled (lines 1015-1056) because `update_session_progress()` doesn't accept `active_files` parameter.

**Decision**: Extend `WorkSessionManager.update_session_progress()` with `active_files` parameter instead of direct database writes.

**Rationale**:
- Maintains abstraction layer (Context7 pattern)
- Enables re-use of existing WorkSessionManager infrastructure
- Allows atomic updates with proper error handling

**Alternatives Considered**:
1. Direct database writes in PostToolUse (rejected - breaks abstraction)
2. Create separate FileTrackingManager (rejected - unnecessary complexity)

### ADR-002: Environment-Based Session Identification (NEW - v2)

**Context**: Multi-session scenarios (Sonnet + GLM concurrent) require unambiguous session identification. Database query `SELECT ... WHERE status='active' LIMIT 1` is ambiguous when multiple sessions active.

**Decision**: Use `CLAUDE_SESSION_ID` environment variable as primary session identifier, with database fallback only for single-session scenarios.

**Rationale**:
- Environment variables are process-specific → guaranteed isolation
- Claude Code sets `CLAUDE_SESSION_ID` per session
- Database fallback maintains backward compatibility
- Prevents session tracking cross-contamination

**Alternatives Considered**:
1. PID-based identification (rejected - same process can have multiple Claude Code sessions)
2. Registry-only tracking (rejected - requires hook coordination complexity)
3. Thread-local storage (rejected - doesn't work across async contexts)

### ADR-003: Session ID-Based Idempotency (NEW - v2)

**Context**: SessionStart hook executed twice creates duplicate sessions. PID-based idempotency check fails when multiple sessions share same process.

**Decision**: Check idempotency by `session_id` (not PID) - if session already exists and active, return it.

**Rationale**:
- Session ID is unique per session (not per process)
- Supports multiple sessions in same process
- Database query is definitive source of truth
- Maintains backward compatibility with single-session scenarios

**Alternatives Considered**:
1. PID-based idempotency (rejected - fails multi-session)
2. Registry-based locking (rejected - race conditions)
3. Debounce execution (rejected - unreliable timing)

---

## Component-Level Design

### Component 1: WorkSessionManager Extension

**Location**: `.claude/hooks/devstream/sessions/work_session_manager.py`

**Changes**:
```python
async def update_session_progress(
    self,
    session_id: str,
    tokens_delta: int = 0,
    active_tasks: Optional[List[str]] = None,
    completed_tasks: Optional[List[str]] = None,
    active_files: Optional[List[str]] = None  # NEW PARAMETER
) -> bool:
    """Update session progress metrics including active files."""
    
    import json
    now = datetime.now().isoformat()
    
    # Build UPDATE query dynamically
    updates = ["last_activity_at = ?"]
    params = [now]
    
    if tokens_delta != 0:
        updates.append("tokens_used = tokens_used + ?")
        params.append(tokens_delta)
    
    if active_tasks is not None:
        updates.append("active_tasks = ?")
        params.append(json.dumps(active_tasks))
    
    if completed_tasks is not None:
        updates.append("completed_tasks = ?")
        params.append(json.dumps(completed_tasks))
    
    # NEW: Handle active_files parameter
    if active_files is not None:
        updates.append("active_files = ?")
        params.append(json.dumps(active_files))
    
    params.append(session_id)
    
    query = f"UPDATE work_sessions SET {', '.join(updates)} WHERE id = ?"
    
    # Context7 pattern: async with + explicit commit
    async with self._get_connection() as db:
        cursor = await db.execute(query, params)
        await db.commit()
        
        if cursor.rowcount == 0:
            self.logger.warning(f"No session found to update: {session_id}")
            return False
    
    self.logger.debug(f"Updated session: {session_id}, files={len(active_files) if active_files else 0}")
    return True
```

**Testing Strategy**:
- Unit test: Verify active_files parameter accepted
- Integration test: Verify PostToolUse → WorkSessionManager flow
- E2E test: Verify files appear in session summary

### Component 2: PostToolUse Session Tracking Re-enablement

**Location**: `.claude/hooks/devstream/memory/post_tool_use.py:965-1065`

**Changes**:
```python
async def update_session_tracking(
    self,
    tool_name: str,
    tool_input: Dict[str, Any]
) -> None:
    """Update work_sessions with active files and tasks via WorkSessionManager."""
    
    try:
        session_id = await self._get_current_session_id()
        if not session_id:
            self.base.debug_log("No active session - skip tracking")
            return
        
        # Initialize WorkSessionManager
        from work_session_manager import WorkSessionManager
        session_manager = WorkSessionManager()
        
        # Track active files (Write/Edit/MultiEdit)
        if tool_name in ["Write", "Edit", "MultiEdit"]:
            file_path = tool_input.get("file_path")
            if file_path:
                current_files = await self._get_active_files(session_id)
                
                if file_path not in current_files:
                    current_files.append(file_path)
                    
                    # ENABLED: Now using active_files parameter
                    await session_manager.update_session_progress(
                        session_id=session_id,
                        active_files=current_files
                    )
                    
                    self.base.debug_log(
                        f"Updated active_files: {file_path} (total: {len(current_files)})"
                    )
        
        # Track active tasks (TodoWrite)
        elif tool_name == "TodoWrite":
            todos = tool_input.get("todos", [])
            current_tasks = await self._get_active_tasks(session_id)
            
            tasks_updated = False
            for todo in todos:
                if todo.get("status") == "in_progress":
                    task_content = todo.get("content", "")
                    
                    if task_content and task_content not in current_tasks:
                        current_tasks.append(task_content)
                        tasks_updated = True
            
            # ENABLED: Now using active_tasks parameter
            if tasks_updated:
                await session_manager.update_session_progress(
                    session_id=session_id,
                    active_tasks=current_tasks
                )
                
                self.base.debug_log(
                    f"Updated active_tasks: {len(current_tasks)} tasks"
                )
    
    except Exception as e:
        self.base.debug_log(f"Session tracking failed (non-blocking): {e}")
```

**Testing Strategy**:
- Verify Write tool updates active_files
- Verify Edit tool updates active_files
- Verify TodoWrite updates active_tasks

### Component 3: SessionStart Idempotency Check

**Location**: `.claude/hooks/devstream/sessions/session_start.py:80-178`

**Changes**:
```python
async def initialize_session(self, session_id: str) -> Dict[str, Any]:
    """Initialize work session with idempotency check."""
    
    results = {
        "success": False,
        "session_id": session_id,
        "session_created": False,
        "session_resumed": False,
        "error": None
    }
    
    try:
        # NEW: Idempotency check via PID
        current_pid = os.getpid()
        
        if not self.coordinator._acquire_lock(timeout=5):
            raise RuntimeError("Failed to acquire registry lock")
        
        try:
            sessions = self.coordinator._read_registry()
            
            # Check if session for this PID already exists
            for existing_session_id, session_info in sessions.items():
                if session_info.pid == current_pid and session_info.status == "active":
                    self.logger.warning(
                        f"Session already exists for PID {current_pid}: {existing_session_id}"
                    )
                    
                    results["success"] = True
                    results["session_resumed"] = True
                    results["session_id"] = existing_session_id
                    
                    # Return existing session (idempotent)
                    return results
        
        finally:
            self.coordinator._release_lock()
        
        # Proactive cleanup of zombie sessions...
        # (rest of existing code)
        
        # Register session with coordinator...
        # (rest of existing code)
        
        # Resume or create session...
        session = await self.session_manager.resume_session(session_id)
        
        results["success"] = True
        results["session_created"] = session.tokens_used == 0
        results["session_resumed"] = session.tokens_used > 0
        
        return results
    
    except Exception as e:
        results["error"] = str(e)
        self.structured_logger.log_hook_error(e, {
            "session_id": session_id,
            "operation": "initialize_session"
        })
    
    return results
```

**Testing Strategy**:
- Unit test: Verify PID check prevents duplicate sessions
- Integration test: Call SessionStart twice, verify only 1 session created
- Verify existing session returned on second call

### Component 4: Duration Formatting Fix

**Location**: `.claude/hooks/devstream/sessions/session_summary_generator.py`

**Changes**:
```python
def _format_duration(self, session_data: SessionData) -> str:
    """Format session duration in human-readable format."""
    
    if not session_data.ended_at or not session_data.started_at:
        return "0 minutes"
    
    duration_seconds = int((session_data.ended_at - session_data.started_at).total_seconds())
    
    if duration_seconds < 60:
        return f"{duration_seconds} seconds"
    elif duration_seconds < 3600:
        minutes = duration_seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
```

**Testing Strategy**:
- Unit test: Verify 13 seconds → "13 seconds"
- Unit test: Verify 65 seconds → "1 minute"
- Unit test: Verify 3665 seconds → "1 hour 1 minute"

---

## Micro-Task Breakdown

### Phase 1: WorkSessionManager Extension (Priority 1)
**Duration**: 30 minutes

1. Add `active_files` parameter to `update_session_progress()` signature
2. Add JSON serialization for active_files
3. Add UPDATE query modification for active_files
4. Add debug logging for file tracking
5. Test parameter acceptance

### Phase 2: PostToolUse Re-enablement (Priority 1)
**Duration**: 45 minutes

1. Remove DISABLED comments from lines 1015-1056
2. Update `update_session_tracking()` to call WorkSessionManager with active_files
3. Update `update_session_tracking()` to call WorkSessionManager with active_tasks
4. Add error handling for session manager failures
5. Test Write/Edit/TodoWrite tools trigger tracking

### Phase 3: SessionStart Idempotency (Priority 3)
**Duration**: 30 minutes

1. Add PID check before session creation
2. Add registry lookup for existing sessions by PID
3. Add early return for existing sessions
4. Add debug logging for idempotency checks
5. Test double execution scenario

### Phase 4: Duration Formatting (Priority 4)
**Duration**: 20 minutes

1. Add `_format_duration()` method to SessionSummaryGenerator
2. Replace duration calculation in `generate_summary()`
3. Add unit tests for various durations
4. Verify summary output formatting

### Phase 5: SessionEnd Investigation (Priority 2)
**Duration**: 45 minutes

1. Add debug logging to SessionEnd entry point
2. Verify hook configuration in settings.json
3. Test manual SessionEnd invocation
4. Check for blocking errors
5. Verify marker file creation

### Phase 6: Zombie Session Cleanup (Priority 5)
**Duration**: 15 minutes

1. Run aggressive cleanup script
2. Verify zombie sessions removed from registry
3. Verify database sessions updated
4. Document cleanup statistics

### Phase 7: Integration Testing (Priority 1)
**Duration**: 45 minutes

1. Test full workflow: Write → PostToolUse → WorkSessionManager → DB
2. Verify session summaries show non-zero data
3. Test SessionEnd → Summary generation
4. Verify marker file creation and display
5. Validate no new zombie sessions created

---

## Testing Requirements

### Unit Tests (95%+ Coverage)

```python
# test_work_session_manager.py
async def test_update_session_progress_with_active_files():
    """Verify active_files parameter accepted and stored."""
    manager = WorkSessionManager()
    session_id = "test-session-123"
    
    # Create test session
    await manager.create_session(session_id)
    
    # Update with active_files
    success = await manager.update_session_progress(
        session_id=session_id,
        active_files=["/test/file1.py", "/test/file2.ts"]
    )
    
    assert success == True
    
    # Verify files stored
    session = await manager.get_session(session_id)
    assert len(session.active_tasks) == 0  # Should be empty
    # Note: active_files not in WorkSession dataclass yet - need to add it
```

### Integration Tests

```python
# test_session_tracking_integration.py
async def test_posttooluse_to_worksessionmanager_flow():
    """Verify PostToolUse → WorkSessionManager → DB flow."""
    # Setup: Create active session
    # Execute: Trigger Write tool via PostToolUse
    # Assert: active_files updated in work_sessions table
```

### E2E Tests

```python
# test_session_summary_e2e.py
async def test_session_summary_shows_files_and_tasks():
    """Verify session summary shows non-zero files and tasks."""
    # Setup: Create session, execute Write/Edit/TodoWrite
    # Execute: Trigger SessionEnd
    # Assert: Summary shows files_modified > 0, tasks_completed > 0
```

---

## Risks & Mitigation

### Risk 1: WorkSession Dataclass Missing active_files Field
**Impact**: High  
**Probability**: High  
**Mitigation**: Add `active_files: List[str]` to WorkSession dataclass in work_session_manager.py:28-47

### Risk 2: Database Schema Missing active_files Column
**Impact**: Low (column already exists)  
**Probability**: Low  
**Mitigation**: Verified schema has `active_files JSON DEFAULT '[]'` column

### Risk 3: SessionEnd Still Not Triggered
**Impact**: High  
**Probability**: Medium  
**Mitigation**: Phase 5 investigation will identify root cause

### Risk 4: Race Conditions in Registry Access
**Impact**: Medium  
**Probability**: Low  
**Mitigation**: SessionCoordinator already uses fcntl file locking (production-tested)

---

## Success Criteria

1. ✅ Session summaries show non-zero files_modified and tasks_completed
2. ✅ No duplicate sessions created on startup
3. ✅ Session duration displays correctly (seconds/minutes/hours)
4. ✅ Zero zombie sessions after cleanup
5. ✅ Marker files created and displayed on next session
6. ✅ 95%+ test coverage for modified code
7. ✅ All existing tests pass

---

## Rollback Plan

If implementation fails:
1. Revert WorkSessionManager changes
2. Re-disable PostToolUse session tracking
3. Restore original SessionStart logic
4. Document failure reason in task notes

---

**Implementation Start**: Awaiting approval  
**Estimated Completion**: 3-4 hours after approval