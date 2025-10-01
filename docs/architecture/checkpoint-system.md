# DevStream Checkpoint System

**Version**: 0.1.0-beta
**Status**: Production Ready
**Last Updated**: 2025-10-02

---

## Overview

The DevStream Checkpoint System provides automatic session state saving and recovery through the `/save-progress` command. This document explains the architecture, implementation, and usage of the checkpoint system.

## Purpose

**Problem Solved**: Claude Code sessions can be interrupted (crashes, context window exhaustion, user logout). Without checkpoints, progress is lost.

**Solution**: Automatic state persistence to SQLite database with one-command recovery.

---

## Architecture

### System Components

```mermaid
graph TB
    User[User Session] --> SaveCmd[/save-progress command]
    SaveCmd --> Collector[State Collector]

    Collector --> TaskState[Task State]
    Collector --> TodoState[TodoWrite State]
    Collector --> AgentState[Agent State]
    Collector --> MemoryState[Memory Snapshot]

    TaskState --> Serializer[State Serializer]
    TodoState --> Serializer
    AgentState --> Serializer
    MemoryState --> Serializer

    Serializer --> DB[(SQLite DB)]

    DB --> Restore[Restore Command]
    Restore --> User

    style DB fill:#e1f5ff
    style Serializer fill:#fff3e0
```

### Database Schema

```sql
-- Checkpoints table
CREATE TABLE checkpoints (
    id TEXT PRIMARY KEY,                    -- Unique checkpoint ID
    timestamp TIMESTAMP NOT NULL,           -- Creation time
    session_id TEXT,                        -- Claude Code session ID
    branch TEXT,                            -- Git branch at checkpoint
    serialized_state TEXT NOT NULL,         -- JSON state blob
    metadata JSON,                          -- Additional metadata
    restored_from TEXT,                     -- Parent checkpoint (if restored)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Checkpoint index for fast retrieval
CREATE INDEX idx_checkpoints_timestamp ON checkpoints(timestamp DESC);
CREATE INDEX idx_checkpoints_session ON checkpoints(session_id);
```

### Serialized State Format

```typescript
interface CheckpointState {
  version: string;                  // Schema version (e.g., "1.0")
  timestamp: string;                // ISO 8601 timestamp
  session_id: string;               // Claude Code session ID
  branch: string;                   // Git branch

  // Task Management State
  task: {
    current_task: string | null;    // Active task file
    status: TaskStatus;             // pending | active | completed
    phase: string | null;           // Current phase
    todos: TodoItem[];              // TodoWrite list
  };

  // Agent State
  agents: {
    last_invoked: string | null;    // Last agent called
    delegation_history: DelegationRecord[];
  };

  // Memory Snapshot
  memory: {
    recent_entries: MemoryEntry[];  // Last 10 memories
    keywords: string[];             // Active keywords
  };

  // File Context
  files: {
    modified: string[];             // Modified files since last commit
    staged: string[];               // Git staged files
  };

  // Metadata
  metadata: {
    total_tokens_used: number;      // Context window usage
    active_duration_seconds: number;// Session duration
    commands_executed: number;      // Tool invocations
  };
}
```

---

## Implementation

### Command Flow: `/save-progress`

```python
# Conceptual implementation
async def save_progress_command():
    """
    /save-progress command implementation.

    Flow:
    1. Collect current state from all systems
    2. Serialize state to JSON
    3. Store in SQLite database
    4. Return checkpoint ID to user
    """

    # Step 1: Collect state
    task_state = await collect_task_state()
    agent_state = await collect_agent_state()
    memory_snapshot = await collect_memory_snapshot()
    file_context = await collect_file_context()
    metadata = await collect_metadata()

    # Step 2: Serialize
    checkpoint = CheckpointState(
        version="1.0",
        timestamp=datetime.utcnow().isoformat(),
        session_id=get_session_id(),
        branch=get_git_branch(),
        task=task_state,
        agents=agent_state,
        memory=memory_snapshot,
        files=file_context,
        metadata=metadata
    )

    serialized = json.dumps(checkpoint, indent=2)

    # Step 3: Store in database
    checkpoint_id = f"checkpoint_{timestamp}_{uuid4()}"
    await db.execute(
        "INSERT INTO checkpoints (id, timestamp, session_id, branch, serialized_state) "
        "VALUES (?, ?, ?, ?, ?)",
        (checkpoint_id, checkpoint.timestamp, checkpoint.session_id,
         checkpoint.branch, serialized)
    )

    # Step 4: Return confirmation
    return {
        "status": "success",
        "checkpoint_id": checkpoint_id,
        "timestamp": checkpoint.timestamp,
        "message": f"✅ Progress saved: {checkpoint_id}"
    }
```

### State Collection Details

#### Task State Collection

```python
async def collect_task_state() -> dict:
    """Collect current task management state."""

    # Read current task from .claude/state/current_task.json
    current_task = read_current_task_file()

    # Query DevStream MCP for task details
    task_details = await mcp_call("devstream_list_tasks", {
        "status": "active",
        "limit": 1
    })

    # Get TodoWrite state from Claude Code
    todos = get_active_todos()

    return {
        "current_task": current_task.get("task"),
        "status": task_details[0].get("status") if task_details else None,
        "phase": current_task.get("phase"),
        "todos": todos
    }
```

#### Memory Snapshot Collection

```python
async def collect_memory_snapshot() -> dict:
    """Collect recent memory entries for context."""

    # Get last 10 memories (most recent)
    recent_memories = await mcp_call("devstream_search_memory", {
        "query": "",  # Empty query returns recent
        "limit": 10
    })

    # Extract active keywords
    keywords = set()
    for memory in recent_memories:
        keywords.update(memory.get("keywords", []))

    return {
        "recent_entries": recent_memories,
        "keywords": list(keywords)
    }
```

#### File Context Collection

```python
async def collect_file_context() -> dict:
    """Collect file modification state."""

    # Git status for modified files
    modified = subprocess.check_output(
        ["git", "diff", "--name-only"],
        text=True
    ).strip().split("\n")

    # Git staged files
    staged = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only"],
        text=True
    ).strip().split("\n")

    return {
        "modified": [f for f in modified if f],
        "staged": [f for f in staged if f]
    }
```

---

## Usage

### Saving Progress

**When to Save**:
- Before long breaks (lunch, end of day)
- Before risky operations (major refactoring)
- When context window near exhaustion
- Before switching branches

**Command**:
```bash
/save-progress
```

**Output Example**:
```
✅ Progress saved: checkpoint_20251002_143022_a1b2c3d4

Checkpoint Details:
- Timestamp: 2025-10-02T14:30:22Z
- Branch: feature/user-auth
- Active Task: implement-jwt-authentication
- Todos: 3 pending, 2 completed
- Memory Snapshot: 10 recent entries
- Modified Files: src/api/auth.py, tests/api/test_auth.py

To restore: /restore checkpoint_20251002_143022_a1b2c3d4
```

### Restoring Progress

**When to Restore**:
- After session crash
- After context window restart
- When switching back to previous work
- After accidental state loss

**Command**:
```bash
/restore checkpoint_20251002_143022_a1b2c3d4
```

**Output Example**:
```
🔄 Restoring from checkpoint_20251002_143022_a1b2c3d4...

Restored State:
✅ Task: implement-jwt-authentication (active)
✅ TodoWrite: 5 items loaded (3 pending, 2 completed)
✅ Agent State: Last invoked @python-specialist
✅ Memory: 10 entries injected into context
✅ Files: 2 modified files detected
✅ Branch: feature/user-auth

Ready to continue from where you left off!
```

### Listing Checkpoints

**Command**:
```bash
/list-checkpoints
```

**Output Example**:
```
Recent Checkpoints:

1. checkpoint_20251002_143022_a1b2c3d4
   - Date: 2025-10-02 14:30:22
   - Branch: feature/user-auth
   - Task: implement-jwt-authentication
   - Status: Active

2. checkpoint_20251002_100515_e5f6g7h8
   - Date: 2025-10-02 10:05:15
   - Branch: feature/user-auth
   - Task: design-auth-api
   - Status: Completed

3. checkpoint_20251001_163030_i9j0k1l2
   - Date: 2025-10-01 16:30:30
   - Branch: main
   - Task: None
   - Status: Idle
```

---

## Configuration

### Environment Variables

```bash
# .env.devstream

# Checkpoint System
DEVSTREAM_CHECKPOINT_ENABLED=true              # Enable/disable checkpoints
DEVSTREAM_CHECKPOINT_AUTO_SAVE=false           # Auto-save every N minutes (Phase 2)
DEVSTREAM_CHECKPOINT_AUTO_SAVE_INTERVAL=30     # Minutes between auto-saves
DEVSTREAM_CHECKPOINT_MAX_STORAGE=100           # Max checkpoints stored
DEVSTREAM_CHECKPOINT_RETENTION_DAYS=30         # Days to keep old checkpoints
```

### Storage Limits

**Default Limits**:
- **Max Checkpoints**: 100 (oldest deleted first)
- **Retention Period**: 30 days
- **Max State Size**: 10 MB per checkpoint
- **Database Max Size**: 1 GB (100 checkpoints × 10 MB)

**Cleanup Strategy**:
```sql
-- Automatic cleanup (runs on save)
DELETE FROM checkpoints
WHERE created_at < datetime('now', '-30 days')
OR id NOT IN (
    SELECT id FROM checkpoints
    ORDER BY created_at DESC
    LIMIT 100
);
```

---

## Recovery Scenarios

### Scenario 1: Session Crash

**Problem**: Claude Code crashes mid-task.

**Solution**:
1. Restart Claude Code
2. Run `/list-checkpoints`
3. Identify latest checkpoint before crash
4. Run `/restore <checkpoint_id>`
5. Continue work from restored state

**Example**:
```bash
# After restart
/list-checkpoints
# Shows: checkpoint_20251002_143022_a1b2c3d4 (10 minutes ago)

/restore checkpoint_20251002_143022_a1b2c3d4
# State restored: Task active, 3 pending todos, 2 modified files
```

### Scenario 2: Context Window Exhaustion

**Problem**: Context window full, need to restart session.

**Solution**:
1. Before restart: `/save-progress`
2. Restart Claude Code (compact context)
3. Restore checkpoint: `/restore <checkpoint_id>`
4. Continue with fresh context window

**Example**:
```bash
# Before restart
/save-progress
# Saved: checkpoint_20251002_150000_abc123

# After restart (fresh context)
/restore checkpoint_20251002_150000_abc123
# Work continues with full context window
```

### Scenario 3: Branch Switching

**Problem**: Need to switch branches, return later.

**Solution**:
1. Save progress: `/save-progress`
2. Switch branch: `git checkout main`
3. Do work on main branch
4. Return to feature branch: `git checkout feature/user-auth`
5. Restore: `/restore <checkpoint_id>`

**Example**:
```bash
# On feature/user-auth
/save-progress
# Saved: checkpoint_20251002_140000_xyz789

git checkout main
# Do hotfix work...

git checkout feature/user-auth
/restore checkpoint_20251002_140000_xyz789
# Back to feature work!
```

---

## Best Practices

### 1. Save Frequently for Risky Work

**Recommendation**: Save before major refactoring, schema changes, or complex features.

**Example**:
```bash
# Before risky refactoring
/save-progress
# Saved: checkpoint_20251002_140000_backup

# Perform refactoring...
# If things go wrong: /restore checkpoint_20251002_140000_backup
```

### 2. Use Descriptive Checkpoints (Phase 2 Feature)

**Phase 2 Enhancement**: Add custom names to checkpoints.

**Example (Future)**:
```bash
/save-progress "Before implementing JWT refresh tokens"
# Saved: checkpoint_jwt_refresh_20251002_140000
```

### 3. Clean Up Old Checkpoints

**Recommendation**: Periodically review and delete old checkpoints.

**Example**:
```bash
/list-checkpoints
# Delete old checkpoint
sqlite3 data/devstream.db "DELETE FROM checkpoints WHERE id='checkpoint_old_id';"
```

### 4. Checkpoint Before Long Breaks

**Recommendation**: Always save before lunch, end of day, or extended breaks.

**Rationale**: Protection against unexpected interruptions.

---

## Limitations

### Current Limitations (Phase 1)

1. **Manual Save**: User must invoke `/save-progress` (auto-save in Phase 2)
2. **No Naming**: Cannot name checkpoints (Phase 2 feature)
3. **No Comparison**: Cannot diff between checkpoints (Phase 3 feature)
4. **No Branching**: Cannot create checkpoint branches (Phase 3 feature)

### Future Enhancements

**Phase 2**:
- Automatic checkpoint on critical events
- Custom checkpoint naming
- Checkpoint metadata editing

**Phase 3**:
- Checkpoint diffing (compare states)
- Checkpoint branching (fork state)
- Checkpoint merging (combine states)
- Cloud sync (optional)

---

## Troubleshooting

### Checkpoint Not Saving

**Symptom**: `/save-progress` fails silently.

**Solutions**:
```bash
# Check database exists
ls -la data/devstream.db
# Should exist

# Check database permissions
sqlite3 data/devstream.db "SELECT COUNT(*) FROM checkpoints;"
# Should return number

# Check logs
tail -50 ~/.claude/logs/devstream/checkpoint.log
# Look for errors
```

### Restore Fails

**Symptom**: `/restore` command fails with error.

**Solutions**:
```bash
# Verify checkpoint exists
sqlite3 data/devstream.db "SELECT id FROM checkpoints WHERE id='<checkpoint_id>';"
# Should return checkpoint ID

# Check state validity
sqlite3 data/devstream.db "SELECT serialized_state FROM checkpoints WHERE id='<checkpoint_id>';"
# Should return valid JSON

# Manual restore
sqlite3 data/devstream.db "SELECT serialized_state FROM checkpoints WHERE id='<checkpoint_id>';" > state.json
# Review state.json and manually restore components
```

### Database Corruption

**Symptom**: Checkpoint operations fail with database errors.

**Solutions**:
```bash
# Check database integrity
sqlite3 data/devstream.db "PRAGMA integrity_check;"
# Should return "ok"

# Backup and repair
cp data/devstream.db data/devstream.db.backup
sqlite3 data/devstream.db ".dump" > dump.sql
rm data/devstream.db
sqlite3 data/devstream.db < dump.sql
```

---

## Technical Reference

### Checkpoint State Schema Version History

**v1.0** (Current):
- Initial implementation
- Basic task, agent, memory state
- File context tracking

**v2.0** (Planned - Phase 2):
- Custom checkpoint naming
- Enhanced metadata
- Agent delegation history

**v3.0** (Planned - Phase 3):
- Checkpoint branching support
- State diffing capabilities
- Cloud sync metadata

### Database Queries

**Save Checkpoint**:
```sql
INSERT INTO checkpoints (id, timestamp, session_id, branch, serialized_state, metadata)
VALUES (?, ?, ?, ?, ?, ?);
```

**Restore Checkpoint**:
```sql
SELECT serialized_state FROM checkpoints WHERE id = ?;
```

**List Recent Checkpoints**:
```sql
SELECT id, timestamp, branch, metadata
FROM checkpoints
ORDER BY timestamp DESC
LIMIT 10;
```

**Cleanup Old Checkpoints**:
```sql
DELETE FROM checkpoints
WHERE created_at < datetime('now', '-30 days')
OR id NOT IN (
    SELECT id FROM checkpoints
    ORDER BY created_at DESC
    LIMIT 100
);
```

---

## Related Documentation

- [Architecture Overview](devstream-system-overview.md)
- [Protocol Enforcement](protocol-enforcement.md)
- [Memory System](memory_and_context_system.md)
- [User Guide: Getting Started](../user-guide/getting-started.md)

---

**Document Status**: ✅ Complete
**Phase**: Phase 1 (Production Ready)
**Version**: 0.1.0-beta
**Last Updated**: 2025-10-02
