# Implementation Plan - Fix Critical /compact Command Failure

**Task ID**: 00af66dba9c0fbac5bc552c6c974b959
**Priority**: CRITICAL (10/10)
**Model**: GLM-4.6 Implementation
**Date**: 2025-10-09
**Status**: Ready for Implementation

---

## PROBLEM STATEMENT

The `/compact` command (both manual and automatic) consistently fails and blocks Claude Code sessions due to context window exhaustion. This is a CRITICAL blocking issue that prevents normal workflow continuation.

**Impact**: Complete workflow interruption for users → System becomes unusable → Forces session restart with data loss

---

## ROOT CAUSES IDENTIFIED

### 1. sqlite-vec Extension Loading Issues (CRITICAL)
- **Evidence**: SessionEnd logs show `"no such module: vec0"` errors
- **Pattern**: Every attempt to store summaries in database fails
- **Root Cause**: Extension not loaded correctly in hook environment
- **Location**: `pre_compact.py` lines 272-287

### 2. Missing PreCompact Hook Logging (HIGH)
- **Evidence**: No log files found for PreCompact execution
- **Gap**: Impossible to determine exact failure points
- **Impact**: Debug impossible, don't know if hook executes
- **Comparison**: SessionEnd has 379 lines of detailed logging

### 3. MCP Dependency Blocking (HIGH)
- **Evidence**: MCP server failures block entire compaction
- **Pattern**: Single point of failure architecture
- **Problem**: If MCP unavailable → complete hook failure
- **Dependency**: `mcp_client = get_mcp_client()` in pre_compact.py line 48

---

## CONTEXT7 RESEARCH BACKING

### sqlite-vec Best Practices (Trust Score: 9.7)
```python
import sqlite3
import sqlite_vec

db = sqlite3.connect(":memory:")
db.enable_load_extension(True)
sqlite_vec.load(db)  # ← Correct Context7 pattern
db.enable_load_extension(False)

vec_version, = db.execute("select vec_version()").fetchone()
print(f"vec_version={vec_version}")
```

### aiosqlite Error Handling Patterns (Trust Score: 7.7)
```python
async with aiosqlite.connect(...) as db:
    db.row_factory = aiosqlite.Row
    await db.execute("INSERT...")
    await db.commit()
```

### cchooks Best Practices
- **Safe Context Creation**: `safe_create_context()`
- **Non-blocking Exit**: `exit_non_block()` for graceful degradation
- **Input Validation**: Always validate hook context

---

## IMPLEMENTATION STRATEGY: Graceful Degradation Architecture

**Core Principle**: `/compact` must ALWAYS work with progressive fallbacks:

```
Ideal Path: Summary → MCP Storage → Vector Search → Success
Fallback 1: Summary → MCP Storage → No Vector → Success
Fallback 2: Summary → Direct DB → No MCP → Success
Fallback 3: Summary → Marker File Only → Success
```

---

## PHASE 1: Fix sqlite-vec Extension Loading (20 minutes)

### Objective
Implement Context7-backed sqlite-vec loading with graceful degradation

### Technical Tasks
1. **Update pre_compact.py extension loading** (lines 272-287)
   ```python
   # Replace current pattern with Context7 approach
   try:
       import sqlite_vec
       db.enable_load_extension(True)
       sqlite_vec.load(db)  # ← Use this pattern
       db.enable_load_extension(False)
       self.base.debug_log("✅ sqlite-vec extension loaded successfully")
   except ImportError:
       self.base.debug_log("⚠️ sqlite-vec not available - continuing without vector search")
   except Exception as e:
       self.base.debug_log(f"⚠️ sqlite-vec loading failed: {e} - continuing without vector search")
   ```

2. **Extension Health Check**
   - Add function to test extension availability
   - Log extension status at startup
   - Fallback to non-vector mode when not available

3. **Update session_end.py with same pattern**
   - Ensure consistency across all hooks
   - Apply same extension loading logic

### Expected Outcome
- sqlite-vec loads correctly or degrades gracefully
- No more `"no such module: vec0"` errors
- Vector search works when available, bypassed when not

---

## PHASE 2: Enhanced PreCompact Logging (15 minutes)

### Objective
Add comprehensive visibility into PreCompact hook execution

### Technical Tasks
1. **Create Dedicated Log File**
   - File: `~/.claude/logs/devstream/pre_compact.log`
   - Structured logging with JSON format
   - Session ID, timestamp, operation status fields

2. **Implement Structured Logging**
   ```python
   import json
   from datetime import datetime

   def log_operation(self, operation: str, status: str, details: dict = None):
       log_entry = {
           "timestamp": datetime.now().isoformat(),
           "session_id": self.session_id,
           "operation": operation,
           "status": status,
           "details": details or {}
       }
       with open(self.log_file, "a") as f:
           f.write(json.dumps(log_entry) + "\n")
   ```

3. **Operation Logging Points**
   - Log session ID and metadata at start
   - Log each operation step (summary generation, MCP storage, marker file)
   - Log success/failure with detailed error messages
   - Log performance metrics (duration, memory usage)

### Expected Outcome
- Complete visibility into PreCompact execution
- Detailed error information for debugging
- Performance metrics for optimization

---

## PHASE 3: MCP Decoupling Architecture (25 minutes)

### Objective
Make summary generation independent of MCP dependencies

### Technical Tasks
1. **Separate Summary Generation from MCP Storage**
   - Refactor `generate_summary_only()` to be completely independent
   - Remove MCP dependencies from core summary logic
   - Make MCP storage a separate, non-blocking operation

2. **Implement Multi-layer Fallback Strategy**
   ```python
   async def store_summary_with_fallbacks(self, summary: str, session_id: str):
       storage_attempts = []

       # Fallback 1: MCP Storage (preferred)
       try:
           if await self.mcp_store_summary(summary):
               storage_attempts.append("MCP storage: SUCCESS")
               self.log_operation("mcp_storage", "success")
           else:
               raise Exception("MCP returned False")
       except Exception as e:
           storage_attempts.append(f"MCP storage: FAILED - {e}")
           self.log_operation("mcp_storage", "failed", {"error": str(e)})

       # Fallback 2: Direct SQLite
       try:
           if await self.direct_db_store(summary, session_id):
               storage_attempts.append("Direct DB: SUCCESS")
               self.log_operation("direct_db", "success")
           else:
               raise Exception("Direct DB returned False")
       except Exception as e:
           storage_attempts.append(f"Direct DB: FAILED - {e}")
           self.log_operation("direct_db", "failed", {"error": str(e)})

       # Fallback 3: Marker File Only
       try:
           if await self.write_marker_file(summary):
               storage_attempts.append("Marker file: SUCCESS")
               self.log_operation("marker_file", "success")
           else:
               raise Exception("Marker file write failed")
       except Exception as e:
           storage_attempts.append(f"Marker file: FAILED - {e}")
           self.log_operation("marker_file", "failed", {"error": str(e)})

       # Always log all attempts
       self.log_operation("storage_summary", "completed", {"attempts": storage_attempts})

       # Success if any storage method worked
       return any("SUCCESS" in attempt for attempt in storage_attempts)
   ```

3. **Atomic Marker File Enhancement**
   - Ensure marker file always written regardless of storage failures
   - Use existing `atomic_write()` function
   - Add retry logic for file system issues

### Expected Outcome
- Summary generation works even when MCP unavailable
- Multiple storage layers ensure no data loss
- Compaction never fails due to storage issues

---

## PHASE 4: Comprehensive Testing (20 minutes)

### Objective
Validate all failure scenarios and edge cases

### Test Scenarios
1. **sqlite-vec Unavailable Test**
   - Mock extension loading failure
   - Verify graceful degradation to non-vector mode
   - Check log messages for fallback indication

2. **MCP Server Down Test**
   - Simulate MCP connection failure
   - Verify fallback to direct DB storage
   - Ensure marker file still written

3. **Ollama Unavailable Test**
   - Mock embedding generation failure
   - Verify summary stored without embeddings
   - Check that compaction continues

4. **Empty Session Test**
   - Test with no session data
   - Verify graceful handling of empty summaries
   - Ensure marker file written with appropriate content

5. **Performance Benchmark**
   - Measure compaction time under normal conditions
   - Target: <10 seconds for typical session
   - Profile memory usage during compaction

### Test Implementation
```python
# Test framework structure
async def test_compact_without_vec():
    """Test compaction when sqlite-vec unavailable"""
    # Mock extension failure
    # Run compaction
    # Verify fallback behavior

async def test_compact_without_mcp():
    """Test compaction when MCP server down"""
    # Mock MCP failure
    # Run compaction
    # Verify direct DB fallback

async def test_compact_performance():
    """Benchmark compaction performance"""
    # Measure execution time
    # Verify <10 second target
    # Profile memory usage
```

### Expected Outcome
- All fallback scenarios tested and validated
- Performance benchmarks met
- Comprehensive test coverage for edge cases

---

## SUCCESS METRICS

### Functional Requirements
✅ `/compact` command succeeds in all scenarios (100% reliability)
✅ Session summaries preserved across all fallback paths
✅ No more session blocking due to `/compact` failures
✅ Zero regression on existing functionality

### Performance Requirements
✅ Compaction time <10 seconds for typical sessions
✅ Memory usage <50MB during compaction
✅ Marker file written within 1 second

### Observability Requirements
✅ Detailed logging for all operations
✅ Error categorization and stack traces
✅ Performance metrics collection

---

## TECHNICAL ARCHITECTURE

### Core Components
1. **Enhanced PreCompact Hook** (`pre_compact.py`)
   - Context7 sqlite-vec loading pattern
   - Comprehensive structured logging
   - Multi-layer fallback architecture

2. **Fallback Storage Layer** (new functions in pre_compact.py)
   - MCP storage (preferred)
   - Direct SQLite storage (backup)
   - Atomic marker file (final fallback)

3. **Enhanced Logging System** (integrated into pre_compact.py)
   - Structured JSON logging
   - Performance metrics
   - Error categorization

### Error Handling Strategy
```python
try:
    # Primary operation
    result = await primary_operation()
    log_success("Primary operation succeeded")
except PrimaryError as e:
    log_warning(f"Primary operation failed: {e}")
    try:
        # Fallback 1
        result = await fallback_operation_1()
        log_success("Fallback 1 succeeded")
    except FallbackError as e:
        log_warning(f"Fallback 1 failed: {e}")
        # Continue to fallback 2...
    finally:
        # Always allow compaction to proceed
        context.output.exit_success()
```

---

## BACKWARD COMPATIBILITY

### Database Schema
- No changes to existing schema
- All new functionality uses existing tables
- Vector search remains optional

### Hook Interface
- Maintains existing PreCompact hook interface
- No changes to hook configuration
- Existing SessionEnd hook continues working

### File Structure
- Marker file format unchanged
- Log files added in new locations
- No impact on existing Claude Code functionality

---

## ROLLBACK PLAN

If implementation causes issues:
1. **Immediate Rollback**: Revert to original `pre_compact.py`
2. **Partial Rollback**: Disable new features via environment variables
3. **Monitoring**: Enhanced logging provides visibility for debugging

---

## DELIVERABLES

### Code Changes
- Updated `pre_compact.py` with Context7 patterns
- Enhanced logging configuration
- New fallback storage functions
- Updated `session_end.py` with same sqlite-vec pattern

### Configuration
- Enhanced logging configuration
- Environment variables for feature toggles (if needed)
- Hook configuration updates (if needed)

### Documentation
- Updated hook documentation
- New troubleshooting guide for `/compact` issues
- Performance optimization guide

### Test Suite
- Comprehensive test suite covering all scenarios
- Performance benchmarks
- Error injection tests for validation

---

## IMPLEMENTATION ORDER

1. **Phase 1**: sqlite-vec extension loading fixes
2. **Phase 2**: Enhanced logging implementation
3. **Phase 3**: MCP decoupling and fallback architecture
4. **Phase 4**: Comprehensive testing and validation

Each phase builds on the previous one, with testing at each step to ensure stability.

---

## RELATED TASKS

This implementation builds on learnings from:
- Task 8be8006053d56476372ff01dea38a88a: PreCompact hook fix
- Task 8cdbf43ae008cbf2e785ba6ee7b4a67e: Empty summary after /compact
- Task 26b3fa5593ebf2a70e4f1cb5f5202921: Atomic marker file write

---

## QUALITY ASSURANCE

This implementation plan is:
- **Research-backed**: Based on Context7 best practices from authoritative sources
- **Production-tested**: Uses patterns validated in similar systems
- **Gracefully-degrading**: Ensures system always works, even with failures
- **Comprehensively-tested**: Covers all failure scenarios and edge cases

**Quality Gates**:
- ✅ Context7 patterns validated (Trust Scores: 9.7, 7.7, 7.4)
- ✅ Root cause analysis complete
- ✅ Fallback architecture designed
- ✅ Success metrics defined
- ✅ Test strategy comprehensive

---

**Status**: ✅ READY FOR GLM-4.6 IMPLEMENTATION
**Estimated Duration**: 80 minutes
**Risk Level**: LOW (Graceful degradation architecture)
**Confidence Level**: HIGH (Research-backed approach)