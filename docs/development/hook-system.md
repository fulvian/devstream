# DevStream Hook System - Technical Architecture

**Version**: 1.0.0 | **Date**: 2025-10-02 | **Status**: Production

## Table of Contents

1. [System Overview](#system-overview)
2. [Hook Architecture](#hook-architecture)
3. [PreCompact Hook](#precompact-hook)
4. [cchooks Integration](#cchooks-integration)
5. [Error Handling Strategy](#error-handling-strategy)
6. [Related Documentation](#related-documentation)

---

## System Overview

DevStream implements an automated context preservation system using Claude Code's hook mechanism via the `cchooks` library. The system intercepts key lifecycle events to inject context, store artifacts, and preserve session state.

### Hook Registry

| Hook | Trigger | Purpose | File | Status |
|------|---------|---------|------|--------|
| **PreToolUse** | Before every tool execution | Inject Context7 + DevStream memory | `memory/pre_tool_use.py` | ✅ Production |
| **PostToolUse** | After every tool execution | Store code/docs/context + embeddings | `memory/post_tool_use.py` | ✅ Production |
| **UserPromptSubmit** | On every user prompt | Enhance query with code-aware context | `context/user_query_context_enhancer.py` | ✅ Production |
| **SessionStart** | On Claude Code startup | Display last session summary | `sessions/session_start.py` | ✅ Production |
| **SessionEnd** | On Claude Code exit | Generate session summary + store | `sessions/session_end.py` | ✅ Production |
| **PreCompact** | Before `/compact` command | Preserve session before context reset | `sessions/pre_compact.py` | ✅ Production |

### Core Integration Pattern

```
User Action
    ↓
Claude Code Event (cchooks)
    ↓
DevStream Hook (Python async)
    ↓
┌─────────────────────────────────────────┐
│ 1. Context Validation (safe_create_context) │
│ 2. Configuration Check (should_run)      │
│ 3. Business Logic (async processing)     │
│ 4. Error Handling (graceful degradation) │
│ 5. Exit Status (exit_success/exit_non_block) │
└─────────────────────────────────────────┘
    ↓
Continue User Workflow (non-blocking)
```

**CRITICAL**: All hooks are **non-blocking** - failures degrade gracefully without interrupting user workflow.

---

## Hook Architecture

### Component Hierarchy

```
DevStreamHookBase (abstract)
    ├── Configuration management (.env.devstream)
    ├── Feedback system (silent/minimal/verbose)
    ├── Debug logging (structured)
    ├── MCP client integration (safe_mcp_call)
    └── Error handling (graceful fallback)
        ↓
Specialized Hooks (concrete implementations)
    ├── PreToolUse → Context injection (Context7 + memory search)
    ├── PostToolUse → Artifact storage (code/docs + embeddings)
    ├── UserPromptSubmit → Query enhancement (code-aware queries)
    ├── SessionStart → Session restoration (marker file read)
    ├── SessionEnd → Session summary (triple-source aggregation)
    └── PreCompact → Pre-compaction preservation (summary + marker)
```

### Base Class Features (`DevStreamHookBase`)

**File**: `.claude/hooks/devstream/utils/devstream_base.py`

**Provides**:
- ✅ Environment configuration loading (`.env.devstream`)
- ✅ Feedback verbosity control (silent/minimal/verbose)
- ✅ Structured debug logging (`debug_log()`)
- ✅ MCP client error handling (`safe_mcp_call()`)
- ✅ User messaging (`success_feedback`, `warning_feedback`, `error_feedback`)

**Example Usage**:

```python
from devstream_base import DevStreamHookBase

class MyHook:
    def __init__(self):
        self.base = DevStreamHookBase("my_hook")

    async def process(self, context):
        # Check configuration
        if not self.base.should_run():
            self.base.debug_log("Hook disabled")
            context.output.exit_success()
            return

        # Safe MCP call with automatic error handling
        result = await self.base.safe_mcp_call(
            mcp_client,
            "devstream_store_memory",
            {"content": "data", "content_type": "context"}
        )

        if result:
            self.base.success_feedback("Data stored")
        else:
            self.base.warning_feedback("Storage failed (non-blocking)")
```

**Key Methods**:

| Method | Purpose | Blocking |
|--------|---------|----------|
| `should_run()` | Check if hook is enabled in config | No |
| `debug_log(msg)` | Log debug message if `DEVSTREAM_DEBUG=true` | No |
| `safe_mcp_call()` | Async MCP tool call with error handling | No |
| `success_feedback()` | Show success (verbose mode only) | No |
| `warning_feedback()` | Show warning (minimal+ modes) | No |
| `error_feedback()` | Show error (always, unless silent) | No |

---

## PreCompact Hook

### Purpose

The PreCompact hook executes **before** the `/compact` command to preserve session state before context window reset. This ensures work progress is captured even when compaction interrupts normal session flow.

### Architectural Design

```
User: /compact
    ↓
cchooks: PreCompact Event
    ↓
PreCompactHook.process()
    ↓
┌─────────────────────────────────────────┐
│ Step 1: Get Active Session ID           │
│   └─ Query: work_sessions WHERE status='active' │
├─────────────────────────────────────────┤
│ Step 2: Extract Session Data            │
│   └─ SessionDataExtractor (reuse from SessionEnd) │
├─────────────────────────────────────────┤
│ Step 3: Generate Summary                │
│   └─ SessionSummaryGenerator (triple-source) │
├─────────────────────────────────────────┤
│ Step 4: Store in DevStream Memory       │
│   └─ MCP: devstream_store_memory (with embedding) │
├─────────────────────────────────────────┤
│ Step 5: Write Marker File               │
│   └─ ~/.claude/state/devstream_last_session.txt │
└─────────────────────────────────────────┘
    ↓
exit_success → /compact proceeds
```

### File Structure

**File**: `.claude/hooks/devstream/sessions/pre_compact.py`

**Dependencies**:
```python
# cchooks integration
from cchooks import safe_create_context, PreCompactContext

# DevStream base
from devstream_base import DevStreamHookBase
from mcp_client import get_mcp_client

# Session components (reused from SessionEnd)
from session_data_extractor import SessionDataExtractor
from session_summary_generator import SessionSummaryGenerator
```

**Component Reuse**: PreCompact reuses `SessionDataExtractor` and `SessionSummaryGenerator` from SessionEnd hook to maintain consistency and avoid code duplication.

### Core Workflow

#### Step 1: Get Active Session ID

```python
async def get_active_session_id(self) -> Optional[str]:
    """
    Query work_sessions table for currently active session.

    SQL Query:
        SELECT id FROM work_sessions
        WHERE status = 'active'
        ORDER BY started_at DESC
        LIMIT 1

    Returns:
        Session ID string or None if no active session
    """
    async with aiosqlite.connect(self.db_path) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute(
            "SELECT id FROM work_sessions WHERE status = 'active' "
            "ORDER BY started_at DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            return row['id'] if row else None
```

**Error Handling**: Returns `None` on database errors (logged but non-blocking).

#### Step 2: Extract Session Data

```python
# Reuse SessionDataExtractor (from session_end.py)
session_data = await self.data_extractor.get_session_metadata(session_id)

# Triple-source data extraction:
# 1. Session metadata: work_sessions table
# 2. Memory stats: semantic_memory (time-range query)
# 3. Task stats: micro_tasks (time-range query)
```

**Component**: `SessionDataExtractor` (shared with SessionEnd hook)

**Extracted Data**:
- Session metadata (name, start time, tokens used)
- Memory statistics (files modified, decisions, learnings)
- Task statistics (completed, active, titles)

#### Step 3: Generate Summary

```python
# Reuse SessionSummaryGenerator (from session_end.py)
summary_markdown = self.summary_generator.generate_summary(
    session_data,   # Session metadata
    memory_stats,   # Files/decisions/learnings
    task_stats      # Task completion data
)
```

**Component**: `SessionSummaryGenerator` (shared with SessionEnd hook)

**Output Format**: Markdown summary with sections:
- 📊 Work Accomplished (tasks, files, tokens)
- 🎯 Key Decisions (architectural choices)
- 💡 Lessons Learned (debugging insights)

#### Step 4: Store in DevStream Memory

```python
# Store via MCP with embedding generation
result = await self.base.safe_mcp_call(
    self.mcp_client,
    "devstream_store_memory",
    {
        "content": summary_markdown,
        "content_type": "context",
        "keywords": ["session", "summary", session_id, "pre-compact"]
    }
)
```

**Backend Flow**:
1. MCP server receives summary
2. Ollama generates embedding (async)
3. SQLite stores content + embedding
4. sqlite-vec indexes for hybrid search

**Retrieval**: Summary can be retrieved via `devstream_search_memory` using keywords or semantic similarity.

#### Step 5: Write Marker File

```python
async def write_marker_file(self, summary: str) -> bool:
    """
    Write summary to marker file for SessionStart hook.

    Path: ~/.claude/state/devstream_last_session.txt

    Purpose: SessionStart reads this file on next startup to display
    last session summary (one-time display pattern).
    """
    marker_file = Path.home() / ".claude" / "state" / "devstream_last_session.txt"
    marker_file.parent.mkdir(parents=True, exist_ok=True)
    marker_file.write_text(summary)
```

**Lifecycle**:
1. **Created by**: SessionEnd or PreCompact hooks
2. **Read by**: SessionStart hook (next startup)
3. **Deleted by**: SessionStart hook (after display)

**Pattern**: One-time display ensures users see session summary once per session without repetition.

---

## cchooks Integration

### Context Creation Pattern

All hooks use `safe_create_context()` from cchooks to validate execution environment.

```python
from cchooks import safe_create_context, PreCompactContext

def main():
    # Automatically detects hook type from environment
    ctx = safe_create_context()

    # Type validation
    if not isinstance(ctx, PreCompactContext):
        print(f"Error: Expected PreCompactContext, got {type(ctx)}", file=sys.stderr)
        sys.exit(1)

    # Create hook instance
    hook = PreCompactHook()

    # Run async processing
    asyncio.run(hook.process(ctx))
```

**What `safe_create_context()` Does**:
- ✅ Reads environment variables set by Claude Code
- ✅ Parses cchooks context schema
- ✅ Validates required fields
- ✅ Returns typed context object (`PreCompactContext`, `PreToolUseContext`, etc.)

### Exit Handling

Hooks **MUST** call one of these exit methods to signal completion:

```python
# Success - allow operation to proceed
context.output.exit_success()

# Non-blocking error - log warning but proceed
context.output.exit_non_block("Storage failed (non-blocking)")

# Blocking error - prevent operation (RARE, use sparingly)
context.output.exit_block("Critical security violation detected")
```

**Best Practice**: Use `exit_success()` for all normal flows, `exit_non_block()` for errors that shouldn't interrupt user workflow.

### PreCompactContext Schema

```python
class PreCompactContext:
    """
    Context provided by cchooks for PreCompact event.

    Attributes:
        output: Exit handler (exit_success, exit_non_block, exit_block)
        environment: Environment variables
        project_dir: Project root directory
    """
    output: OutputHandler
    environment: Dict[str, str]
    project_dir: Path
```

**Usage**:

```python
async def process(self, context: PreCompactContext):
    # Access project directory
    db_path = context.project_dir / "data" / "devstream.db"

    # Signal success
    context.output.exit_success()
```

### Non-Blocking Error Pattern

**CRITICAL**: PreCompact hook is **non-blocking** - it never prevents `/compact` from executing.

```python
async def process_pre_compact(self, context: PreCompactContext):
    try:
        session_id = await self.get_active_session_id()

        if not session_id:
            self.base.debug_log("No active session")
            context.output.exit_success()  # Still allow compaction
            return

        summary = await self.generate_and_store_summary(session_id)

        if not summary:
            self.base.warning_feedback("Summary generation failed")
            context.output.exit_non_block("Summary failed")
            context.output.exit_success()  # Still allow compaction
            return

        # Write marker file
        await self.write_marker_file(summary)

        # Always allow compaction
        context.output.exit_success()

    except Exception as e:
        # Graceful failure - log and proceed
        self.base.debug_log(f"PreCompact error: {e}")
        context.output.exit_non_block(f"Hook error: {str(e)[:100]}")
        context.output.exit_success()  # ALWAYS allow compaction
```

**Design Rationale**: `/compact` is a user-initiated command to manage context window limits. Hook failures should not block this critical operation.

---

## Marker File Persistence Mechanism

### Overview

DevStream uses a **marker file pattern** for one-time session summary display across sessions.

### Architecture

```
Session N (ends)
    ↓
SessionEnd or PreCompact Hook
    ↓
Write: ~/.claude/state/devstream_last_session.txt
    ↓
[Session ends / /compact executed]
    ↓
Session N+1 (starts)
    ↓
SessionStart Hook
    ↓
Read: ~/.claude/state/devstream_last_session.txt
    ↓
Display Summary to User (one-time)
    ↓
Delete: ~/.claude/state/devstream_last_session.txt
    ↓
[File deleted - no further displays]
```

### Marker File Path

**Location**: `~/.claude/state/devstream_last_session.txt`

**Format**: Plain text markdown (session summary)

**Lifecycle**:
1. **Created by**: `SessionEnd.py` (normal exit) or `PreCompact.py` (before `/compact`)
2. **Read by**: `SessionStart.py` (next session startup)
3. **Deleted by**: `SessionStart.py` (after display to prevent re-display)

### Creation Logic

```python
# In SessionEnd or PreCompact hooks
async def write_marker_file(self, summary: str) -> bool:
    marker_file = Path.home() / ".claude" / "state" / "devstream_last_session.txt"

    # Create parent directories if missing
    marker_file.parent.mkdir(parents=True, exist_ok=True)

    # Write summary text
    marker_file.write_text(summary)

    return True
```

**Error Handling**: Non-blocking - logs failure but doesn't raise exception.

### Consumption Logic

```python
# In SessionStart hook
async def read_and_display_marker_file(self) -> bool:
    marker_file = Path.home() / ".claude" / "state" / "devstream_last_session.txt"

    if not marker_file.exists():
        return False  # No previous session summary

    # Read summary
    summary = marker_file.read_text()

    # Display to user
    print("\n" + "=" * 60, file=sys.stderr)
    print("📝 DevStream: Last Session Summary", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(summary, file=sys.stderr)
    print("=" * 60 + "\n", file=sys.stderr)

    # Delete marker file (one-time display)
    marker_file.unlink()

    return True
```

**One-Time Display**: File deletion ensures summary is shown exactly once per session.

### Edge Cases Handled

| Scenario | Behavior |
|----------|----------|
| File doesn't exist | SessionStart skips display (no error) |
| File read fails | SessionStart logs error, doesn't crash |
| File delete fails | SessionStart logs warning, continues |
| Multiple SessionStart calls | Only first call displays (file deleted after first read) |
| PreCompact + SessionEnd both run | Last hook to run wins (file overwritten) |

---

## Error Handling Strategy

### Graceful Degradation Principle

**Core Philosophy**: DevStream hooks **enhance** workflow but should **never block** it. All failures degrade gracefully with logging.

### Error Coverage

```python
async def process_pre_compact(self, context: PreCompactContext):
    try:
        # Database query (may fail if DB locked/corrupted)
        session_id = await self.get_active_session_id()

        if not session_id:
            # Graceful exit - no active session is valid state
            context.output.exit_success()
            return

        try:
            # Summary generation (may fail if data incomplete)
            summary = await self.generate_and_store_summary(session_id)
        except Exception as e:
            # Log error, don't crash
            self.base.debug_log(f"Summary generation failed: {e}")
            context.output.exit_non_block("Summary failed")
            context.output.exit_success()
            return

        try:
            # File I/O (may fail if disk full/permissions)
            await self.write_marker_file(summary)
        except Exception as e:
            # Log warning, don't crash
            self.base.warning_feedback("Marker file write failed")
            # Still exit success - summary is in database

        # Always allow compaction
        context.output.exit_success()

    except Exception as e:
        # Catch-all for unexpected errors
        self.base.error_feedback(f"PreCompact error: {e}")
        context.output.exit_non_block(f"Hook error: {str(e)[:100]}")
        context.output.exit_success()  # Non-blocking
```

### Error Types and Handling

| Error Type | Example | Handling Strategy | User Impact |
|------------|---------|-------------------|-------------|
| **Database unavailable** | SQLite locked | Return `None`, log debug | No context injection (degraded) |
| **MCP call failure** | Server unreachable | `safe_mcp_call` returns `None` | No storage (logged) |
| **File I/O error** | Disk full | Log warning, continue | No marker file (minor) |
| **Data validation error** | Missing session metadata | Skip operation, log | No summary (logged) |
| **Unexpected exception** | Bug in code | Catch-all handler, exit_non_block | Operation continues |

### Logging Strategy

DevStream uses structured logging via `DevStreamHookBase`:

```python
# Debug logs (only if DEVSTREAM_DEBUG=true)
self.base.debug_log("Active session found: {session_id[:8]}...")

# User feedback (respects DEVSTREAM_FEEDBACK_LEVEL)
self.base.success_feedback("Session summary preserved")
self.base.warning_feedback("Summary storage failed (non-blocking)")
self.base.error_feedback("Critical error occurred")
```

**Feedback Levels**:
- `silent`: No user output (logs to file only)
- `minimal`: Warnings and errors only (default)
- `verbose`: Success messages + warnings + errors

**Configuration**: `.env.devstream` → `DEVSTREAM_FEEDBACK_LEVEL=minimal`

---

## Integration Examples

### Example 1: Normal Flow (PreCompact Success)

```
User: /compact

1. cchooks triggers PreCompact event
2. PreCompactHook.process() executes
3. Active session found: "abc123..."
4. Session data extracted:
   - 5 tasks completed
   - 12 files modified
   - 3 decisions recorded
5. Summary generated (1200 chars)
6. Summary stored in DevStream memory (with embedding)
7. Marker file written: ~/.claude/state/devstream_last_session.txt
8. exit_success() → /compact proceeds
9. Context window compacted

Next Session:

10. SessionStart reads marker file
11. Displays summary to user (one-time)
12. Deletes marker file
```

### Example 2: Error Flow (Database Unavailable)

```
User: /compact

1. cchooks triggers PreCompact event
2. PreCompactHook.process() executes
3. Database query fails (SQLite locked)
4. get_active_session_id() returns None
5. Log: "Failed to get active session: database is locked"
6. exit_success() → /compact proceeds (non-blocking)
7. Context window compacted

Result: /compact succeeds, summary not preserved (graceful degradation)
```

### Example 3: Partial Success (Storage Fails)

```
User: /compact

1. cchooks triggers PreCompact event
2. PreCompactHook.process() executes
3. Active session found
4. Summary generated successfully
5. MCP storage call fails (server down)
6. safe_mcp_call() returns None
7. Log: "Summary storage failed (non-blocking)"
8. Marker file still written (summary preserved locally)
9. exit_success() → /compact proceeds
10. Context window compacted

Next Session:

11. SessionStart displays marker file summary (local copy)
12. Summary not in database (search unavailable)

Result: User still sees summary, but it's not searchable in memory
```

---

## Code Examples

### Hook Initialization

```python
#!/usr/bin/env python3
from cchooks import safe_create_context, PreCompactContext
from devstream_base import DevStreamHookBase
import asyncio

class PreCompactHook:
    def __init__(self):
        self.base = DevStreamHookBase("pre_compact")
        self.mcp_client = get_mcp_client()

        # Reuse existing components
        self.data_extractor = SessionDataExtractor()
        self.summary_generator = SessionSummaryGenerator()

    async def process(self, context: PreCompactContext):
        # Check configuration
        if not self.base.should_run():
            context.output.exit_success()
            return

        # Process workflow
        await self.process_pre_compact(context)

def main():
    ctx = safe_create_context()
    hook = PreCompactHook()
    asyncio.run(hook.process(ctx))

if __name__ == "__main__":
    main()
```

### Summary Generation Workflow

```python
async def generate_and_store_summary(self, session_id: str) -> Optional[str]:
    # Step 1: Extract session metadata
    session_data = await self.data_extractor.get_session_metadata(session_id)
    if not session_data:
        return None

    # Step 2: Extract memory stats (time-range query)
    memory_stats = await self.data_extractor.get_memory_stats(
        session_data.started_at,
        datetime.now()
    )

    # Step 3: Extract task stats (time-range query)
    task_stats = await self.data_extractor.get_task_stats(
        session_data.started_at,
        datetime.now()
    )

    # Step 4: Generate markdown summary
    summary_markdown = self.summary_generator.generate_summary(
        session_data,
        memory_stats,
        task_stats
    )

    # Step 5: Store in DevStream memory
    await self.base.safe_mcp_call(
        self.mcp_client,
        "devstream_store_memory",
        {
            "content": summary_markdown,
            "content_type": "context",
            "keywords": ["session", "summary", session_id, "pre-compact"]
        }
    )

    return summary_markdown
```

### Marker File Creation

```python
async def write_marker_file(self, summary: str) -> bool:
    try:
        marker_file = Path.home() / ".claude" / "state" / "devstream_last_session.txt"
        marker_file.parent.mkdir(parents=True, exist_ok=True)
        marker_file.write_text(summary)

        self.base.debug_log(f"Marker file written: {marker_file}")
        return True

    except Exception as e:
        self.base.debug_log(f"Failed to write marker file: {e}")
        return False
```

### cchooks Exit Handling

```python
async def process_pre_compact(self, context: PreCompactContext):
    try:
        # Main workflow
        session_id = await self.get_active_session_id()

        if not session_id:
            # No active session - valid state
            context.output.exit_success()
            return

        summary = await self.generate_and_store_summary(session_id)

        if not summary:
            # Generation failed - log and proceed
            self.base.warning_feedback("Summary generation failed")
            context.output.exit_non_block("Summary failed")
            context.output.exit_success()  # Non-blocking
            return

        # Write marker file (best-effort)
        marker_written = await self.write_marker_file(summary)

        if marker_written:
            self.base.success_feedback("Session summary preserved")

        # Always allow compaction
        context.output.exit_success()

    except Exception as e:
        # Catch-all error handler
        self.base.debug_log(f"PreCompact error: {e}")
        context.output.exit_non_block(f"Hook error: {str(e)[:100]}")
        context.output.exit_success()  # Non-blocking
```

---

## Related Documentation

### DevStream Documentation

- **[Session Management Guide](../user-guide/session-management.md)** - User-facing session workflow
- **[Session Summary Behavioral Refinement](./b2-session-summary-behavioral-refinement.md)** - SessionEnd hook implementation
- **[MCP Lifecycle Management](./mcp-lifecycle-management.md)** - MCP server integration patterns
- **[Code-Aware Query Implementation](./code-aware-query-implementation.md)** - UserPromptSubmit hook architecture

### External References

- **[cchooks Documentation](https://github.com/cchook/cchooks)** - Claude Code hook framework
- **[Context7 Best Practices](/asg017/sqlite-vec)** - sqlite-vec hybrid search patterns
- **[aiosqlite Documentation](https://aiosqlite.omnilib.dev/)** - Async SQLite operations

### Configuration Reference

**File**: `.env.devstream`

```bash
# Hook System Configuration
DEVSTREAM_HOOKS_ENABLED=true              # Master switch for all hooks
DEVSTREAM_FEEDBACK_LEVEL=minimal          # User feedback verbosity (silent/minimal/verbose)
DEVSTREAM_DEBUG=false                     # Enable debug logging

# PreCompact Hook
DEVSTREAM_PRECOMPACT_ENABLED=true         # Enable PreCompact hook
DEVSTREAM_PRECOMPACT_MARKER_FILE=~/.claude/state/devstream_last_session.txt

# Session Management
DEVSTREAM_SESSION_SUMMARY_ENABLED=true    # Enable session summary generation
DEVSTREAM_SESSION_AUTO_TRACK=true         # Automatic session tracking

# Database
DEVSTREAM_DB_PATH=data/devstream.db       # SQLite database path

# MCP Server
DEVSTREAM_MCP_PORT=3000                   # MCP server port
DEVSTREAM_MCP_TIMEOUT=5000                # MCP call timeout (ms)
```

---

## Architectural Decisions

### Why Reuse SessionSummaryGenerator?

**Decision**: PreCompact hook reuses `SessionSummaryGenerator` and `SessionDataExtractor` from SessionEnd hook.

**Rationale**:
- ✅ **Consistency**: Identical summary format across normal exit and `/compact`
- ✅ **DRY Principle**: Single source of truth for summary generation logic
- ✅ **Maintainability**: Changes to summary format propagate to both hooks
- ✅ **Testing**: Test summary generator once, confidence in both hooks

**Alternative Considered**: Separate summary generator for PreCompact
- ❌ Code duplication
- ❌ Divergent summary formats
- ❌ Double maintenance burden

**Context7 Pattern**: Component reuse from [sqlite-vec examples](https://github.com/asg017/sqlite-vec/tree/main/examples) - shared utilities across multiple scripts.

### Why Non-Blocking Design?

**Decision**: PreCompact hook **always** allows `/compact` to proceed, even on errors.

**Rationale**:
- ✅ **User Intent**: `/compact` is user-initiated - blocking it violates expectations
- ✅ **Context Window**: Users run `/compact` when context is full - blocking prevents recovery
- ✅ **Graceful Degradation**: Summary preservation is enhancement, not requirement
- ✅ **Recovery Path**: Even if summary fails, user can still reset context and continue

**Alternative Considered**: Block `/compact` on summary failure
- ❌ Violates user intent
- ❌ No recovery path if hook permanently broken
- ❌ Poor user experience (unexpected blocking)

**Context7 Pattern**: Non-blocking design from [FastAPI background tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) - enhancement without interruption.

### Why Marker File Pattern?

**Decision**: Use persistent marker file (`~/.claude/state/devstream_last_session.txt`) for cross-session communication.

**Rationale**:
- ✅ **Session Boundary**: Claude Code sessions are isolated - file bridges gap
- ✅ **One-Time Display**: File deletion after read prevents repetition
- ✅ **Simplicity**: Plain text file, no complex state management
- ✅ **Reliability**: File survives crashes, compaction, restarts

**Alternative Considered**: Database flag for "summary displayed"
- ❌ Requires database schema change
- ❌ More complex query logic
- ❌ Harder to reset if corrupted

**Context7 Pattern**: Marker file pattern from [Unix daemon design](https://en.wikipedia.org/wiki/Unix_daemon) - PID files for process coordination.

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-02
**Status**: ✅ Production Ready
**Author**: DevStream Development Team
