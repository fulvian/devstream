# Implementation Plan: Holistic Session Context Persistence Architecture Redesign

**Task ID**: 375c778977df733b517653ed6b859ca6
**Priority**: CRITICAL (10/10)
**Model**: Sonnet 4.5 (Architectural Work)
**Date**: 2025-10-10
**Status**: Ready for Implementation
**Estimated Duration**: 4-6 hours

---

## 📋 EXECUTIVE SUMMARY

### Problem Statement
Multi-session environment (Sonnet 4.5 + GLM-4.6 concurrent) suffers from:
1. `/compact` command consistently fails (blocking workflow)
2. `/clear-devstream` partially resets context (requires additional `/clear`)
3. `/exit` doesn't create cross-session summaries
4. Single shared marker file causes race conditions and data loss

### Solution: Hybrid Architecture (Opzione D)
- **Session Registry Enhancement**: Track multiple sessions with status, timestamps, compaction events
- **Session-Specific Marker Files**: `devstream_session_{session_id}.txt` prevents collisions
- **Context7-Backed Cleanup**: psutil-based PID validation and zombie detection
- **7-Day Retention Policy**: Automatic cleanup of ended sessions

### Success Criteria
✅ Multi-session support: Sonnet + GLM run concurrently without data loss
✅ `/compact` reliability: 100% success rate
✅ `/clear-devstream` works correctly (no manual `/clear` needed)
✅ `/exit` generates cross-session summaries
✅ SessionStart displays ALL pending summaries from multiple sessions
✅ Backward compatible: existing sessions migrate automatically

---

## 🏗️ ARCHITECTURAL DESIGN

### Component 1: Enhanced Session Registry

**File**: `~/.claude/state/session_registry.json`

**Schema**:
```json
{
  "sess-{session_id}": {
    "session_id": "sess-140e6cbfc5c24fee",
    "pid": 78848,
    "started_at": 1760111500.597228,
    "last_heartbeat": 1760111500.597228,
    "ended_at": null,
    "status": "active|compacted|ended|zombie",
    "db_path": "/Users/fulvioventura/devstream/data/devstream.db",
    "marker_file_path": "~/.claude/state/devstream_session_{session_id}.txt",
    "compaction_events": [
      {
        "timestamp": 1760113500.123456,
        "trigger": "manual|auto|clear-devstream",
        "marker_file_written": true,
        "db_stored": true,
        "summary_length": 558
      }
    ],
    "summary_displayed": false,
    "model_type": "sonnet-4.5|glm-4.6|unknown",
    "session_name": "Session sess-140"
  }
}
```

**Implementation**: `session_coordinator.py` (already exists - enhance with new fields)

### Component 2: Session-Specific Marker Files

**Naming Convention**: `~/.claude/state/devstream_session_{session_id}.txt`

**Lifecycle**:
- **Creation**: PreCompact OR SessionEnd writes file
- **Existence**: Persists until SessionStart displays summary
- **Deletion**: SessionStart reads → displays → deletes OR cleanup after 7 days

### Component 3: Hook Modifications

**Files to Modify**:
1. `.claude/hooks/devstream/sessions/pre_compact.py`
2. `.claude/hooks/devstream/sessions/session_end.py`
3. `.claude/hooks/devstream/sessions/session_start.py`

**New Methods**:
- `write_marker_file_session_specific()` - Write to session-specific path
- `update_registry_compaction_event()` - Update registry with compaction event
- `update_registry_session_end()` - Mark session as ended
- `display_all_pending_summaries()` - Display multiple summaries
- `cleanup_old_sessions()` - Context7 psutil-based cleanup
- `migrate_legacy_marker_file()` - One-time migration

---

## 📐 IMPLEMENTATION PHASES

### Phase 1: Registry Schema Enhancement (45 min)

**Objective**: Add new fields to session registry for multi-session tracking

**Tasks**:
1. Update `session_coordinator.py`:
   - Add `compaction_events` field (list)
   - Add `marker_file_path` field (string)
   - Add `summary_displayed` field (bool)
   - Add `model_type` field (enum)
   - Add `session_name` field (optional string)

2. Implement `validate_registry_schema()`:
   ```python
   def validate_registry_schema(registry: dict) -> bool:
       """Validate registry conforms to new schema."""
       # Check all required fields
       # Validate field types
       # Return True if valid, False otherwise
   ```

3. Implement `migrate_registry_schema()`:
   ```python
   async def migrate_registry_schema(registry_path: Path) -> bool:
       """Migrate old registry to new schema (add missing fields)."""
       # Read existing registry
       # Add new fields with defaults
       # Write back atomically
   ```

**Acceptance Criteria**:
- [ ] All new fields added to schema
- [ ] Validation function passes for new registry
- [ ] Migration function adds fields to existing sessions
- [ ] Backward compatible (old sessions still work)

### Phase 2: PreCompact Hook Refactoring (60 min)

**Objective**: Write session-specific marker files instead of shared file

**Tasks**:
1. Implement `write_marker_file_session_specific()`:
   - Generate session-specific path
   - Atomic write using `write_atomic()`
   - Update registry with compaction event

2. Implement `update_registry_compaction_event()`:
   - Use `fcntl.flock()` for thread-safe updates
   - Append compaction event to list
   - Update status to "compacted"
   - Set `summary_displayed = False`

3. Modify `process_pre_compact()`:
   - Replace `write_marker_file()` call with `write_marker_file_session_specific()`
   - Pass `session_id` to new method

4. Add logging for new workflow

**Acceptance Criteria**:
- [ ] Session-specific marker files written correctly
- [ ] Registry updated with compaction events
- [ ] File locking prevents race conditions
- [ ] Logging shows session_id and marker file path
- [ ] Multiple `/compact` commands don't overwrite each other

### Phase 3: SessionEnd Hook Refactoring (60 min)

**Objective**: Mark sessions as "ended" and write session-specific summaries

**Tasks**:
1. Implement `write_marker_file_session_specific()` (similar to PreCompact):
   - Session-specific path
   - Atomic write
   - Call `update_registry_session_end()`

2. Implement `update_registry_session_end()`:
   - Set `status = "ended"`
   - Set `ended_at = current_time`
   - Set `marker_file_path`
   - Set `summary_displayed = False`
   - Use file locking

3. Modify `process_session_end()`:
   - Replace marker file write with session-specific version
   - Remove old `devstream_last_session.txt` write

4. Add logging for session end workflow

**Acceptance Criteria**:
- [ ] SessionEnd writes session-specific marker files
- [ ] Registry updated with ended_at timestamp
- [ ] Status set to "ended" correctly
- [ ] File locking works correctly
- [ ] Multiple sessions can end without collision

### Phase 4: SessionStart Hook Major Refactoring (90 min)

**Objective**: Display ALL pending summaries and cleanup old sessions

**Tasks**:
1. Implement `display_all_pending_summaries()`:
   - Read registry with shared lock
   - Find sessions with `summary_displayed = False` AND `ended_at != null`
   - Sort by `ended_at` (oldest first)
   - Display all summaries with metadata (session_id, model_type, ended timestamp)
   - Mark `summary_displayed = True` for all displayed
   - Delete marker files after display
   - Call `cleanup_old_sessions()`

2. Implement `cleanup_old_sessions()` (Context7 psutil patterns):
   - Rule 1: Remove sessions ended > 7 days ago
   - Rule 2: Remove zombie sessions (PID validation with psutil)
   - Use `psutil.pid_exists()` for fast check
   - Use `Process.is_running()` for PID reuse protection
   - Handle `NoSuchProcess`, `AccessDenied`, `ZombieProcess` exceptions
   - Delete marker files for removed sessions
   - Update registry (remove cleaned sessions)

3. Implement `migrate_legacy_marker_file()`:
   - Check if `devstream_last_session.txt` exists
   - Find most recent ended session
   - Write to session-specific marker
   - Delete legacy file

4. Modify `run_hook()`:
   - Call `migrate_legacy_marker_file()` first (one-time)
   - Call `display_all_pending_summaries()`
   - Initialize current session (unchanged)

**Acceptance Criteria**:
- [ ] All pending summaries displayed in single SessionStart
- [ ] Summaries sorted by ended_at (oldest first)
- [ ] Metadata shown for each summary (session_id, model, timestamp)
- [ ] Zombie detection works with psutil
- [ ] 7-day retention policy enforced
- [ ] Legacy marker file migrated correctly
- [ ] Marker files deleted after display

### Phase 5: Fallback Strategies (45 min)

**Objective**: Ensure system works even with corrupted/missing data

**Tasks**:
1. Implement registry corruption fallback:
   ```python
   try:
       registry = json.load(registry_file)
   except (FileNotFoundError, json.JSONDecodeError):
       # Scan directory for marker files
       # Display all found summaries
       # Rebuild registry from coordinator
   ```

2. Implement marker file missing fallback:
   ```python
   if not marker_file.exists():
       # Query DB for session summary
       summary = await query_db_for_session_summary(session_id)
       # Display from DB or mark as displayed anyway
   ```

3. Implement DB unavailable handling:
   - Marker file is critical path (always written)
   - Log warning if DB unavailable
   - SessionStart can still display from marker file

**Acceptance Criteria**:
- [ ] Corrupted registry handled gracefully
- [ ] Missing marker files recovered from DB
- [ ] DB unavailable doesn't block summary display
- [ ] All fallbacks logged clearly

### Phase 6: Testing & Validation (60 min)

**Objective**: Validate all scenarios work correctly

**Test Scenarios**:
1. **Multi-Session Test**:
   - Start Sonnet session A
   - Start GLM session B
   - Run `/compact` on A
   - Run `/compact` on B
   - Close A (SessionEnd)
   - Close B (SessionEnd)
   - Restart Claude Code
   - Verify: Both summaries displayed, correct order, no data loss

2. **Zombie Session Test**:
   - Start session A
   - Kill process without SessionEnd (simulate crash)
   - Wait > 1 hour
   - Start new session
   - Verify: Zombie session cleaned up, marker file removed

3. **7-Day Retention Test**:
   - Create ended session with `ended_at` = 8 days ago
   - Start new session
   - Verify: Old session removed, marker file deleted

4. **Backward Compatibility Test**:
   - Place legacy `devstream_last_session.txt`
   - Start session
   - Verify: Migrated to session-specific format, legacy file deleted

5. **Registry Corruption Test**:
   - Corrupt `session_registry.json` (invalid JSON)
   - Start session
   - Verify: Fallback to marker file scan, summaries still displayed

6. **Concurrent /compact Test**:
   - Two sessions run `/compact` simultaneously
   - Verify: Both marker files written, no overwrites, no corruption

**Acceptance Criteria**:
- [ ] All 6 test scenarios pass
- [ ] No data loss in any scenario
- [ ] No race conditions observed
- [ ] Fallbacks work correctly
- [ ] Performance acceptable (<2s for SessionStart)

---

## 🛡️ ERROR HANDLING STRATEGY

### File Locking (Thread-Safe Registry Updates)
```python
import fcntl

# Read with shared lock (concurrent reads allowed)
with open(registry_path, "r") as f:
    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
    registry = json.load(f)
    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

# Write with exclusive lock (atomic update)
with open(registry_path, "r+") as f:
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    registry = json.load(f)
    # ... modify registry ...
    f.seek(0)
    json.dump(registry, f, indent=2)
    f.truncate()
    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

### Context7 psutil Exception Handling
```python
import psutil

try:
    process = psutil.Process(pid)
    is_running = process.is_running()
except psutil.NoSuchProcess:
    # PID doesn't exist or was reused - safe to remove
    pass
except psutil.AccessDenied:
    # Process exists but can't access - assume active
    pass
except psutil.ZombieProcess:
    # Process is zombie - safe to remove
    pass
```

### Atomic File Operations
```python
# Use existing atomic_file_writer.py utility
from atomic_file_writer import write_atomic

success = await write_atomic(marker_file, summary)
# Guarantees: no partial writes, crash recovery, atomic rename
```

---

## 📊 SUCCESS METRICS

### Functional Requirements
- ✅ Multi-session support: Sonnet + GLM concurrent without data loss
- ✅ `/compact` success rate: 100%
- ✅ `/clear-devstream` works without manual `/clear`
- ✅ `/exit` creates cross-session summaries
- ✅ SessionStart displays ALL pending summaries
- ✅ Zombie detection: psutil-based PID validation
- ✅ 7-day retention: automatic cleanup
- ✅ Backward compatible: legacy sessions migrate

### Non-Functional Requirements
- ✅ Performance: SessionStart <2s (even with 10 pending summaries)
- ✅ Reliability: 0 race conditions, 0 data loss
- ✅ Observability: Comprehensive logging at all stages
- ✅ Maintainability: Clear separation of concerns, type hints, docstrings

### Test Coverage
- ✅ 6 test scenarios passing
- ✅ Edge cases covered (corruption, missing files, zombies)
- ✅ Concurrent operations validated
- ✅ Fallbacks tested

---

## 🔄 ROLLBACK PLAN

If implementation causes issues:

1. **Immediate Rollback**: Revert hook files to original versions
   ```bash
   git checkout HEAD -- .claude/hooks/devstream/sessions/pre_compact.py
   git checkout HEAD -- .claude/hooks/devstream/sessions/session_end.py
   git checkout HEAD -- .claude/hooks/devstream/sessions/session_start.py
   ```

2. **Partial Rollback**: Keep registry enhancements, revert marker file changes
   - Set feature flag in config: `DEVSTREAM_USE_LEGACY_MARKER_FILE=true`
   - Hooks check flag and use old path if enabled

3. **Monitoring**: Enhanced logging provides visibility for debugging

---

## 📚 DELIVERABLES

### Code Changes
1. `session_coordinator.py` - Registry schema enhancement
2. `pre_compact.py` - Session-specific marker files
3. `session_end.py` - Session end tracking
4. `session_start.py` - Multi-summary display + cleanup
5. `atomic_file_writer.py` - No changes (reuse existing)

### Configuration
- No configuration changes needed (all automatic)
- Optional: `DEVSTREAM_SESSION_RETENTION_DAYS=7` (default)

### Documentation
- Update `CLAUDE.md` with new session persistence architecture
- Add troubleshooting guide for multi-session scenarios
- Document migration from legacy to new system

### Test Suite
- 6 integration tests covering all scenarios
- Performance benchmarks for SessionStart
- Concurrent operation stress tests

---

## ⏱️ IMPLEMENTATION ORDER

1. **Phase 1**: Registry Schema Enhancement (45 min)
2. **Phase 2**: PreCompact Hook Refactoring (60 min)
3. **Phase 3**: SessionEnd Hook Refactoring (60 min)
4. **Phase 4**: SessionStart Hook Major Refactoring (90 min)
5. **Phase 5**: Fallback Strategies (45 min)
6. **Phase 6**: Testing & Validation (60 min)

**Total Estimated Time**: 6 hours

---

## 🎯 QUALITY GATES

Before marking task complete, verify:

- [ ] All 6 phases completed with acceptance criteria met
- [ ] All 6 test scenarios passing
- [ ] No regression in existing functionality
- [ ] Code review passed (type hints, docstrings, error handling)
- [ ] Logging comprehensive and structured
- [ ] Performance benchmarks met (<2s SessionStart)
- [ ] Documentation updated

---

**Status**: ✅ READY FOR IMPLEMENTATION
**Estimated Duration**: 6 hours
**Risk Level**: MEDIUM (complex refactoring, but well-designed fallbacks)
**Confidence Level**: HIGH (Context7-backed, research-driven approach)
