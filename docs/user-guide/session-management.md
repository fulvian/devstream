# Session Management Guide

**Version**: 0.1.0-beta
**Audience**: All DevStream users
**Time to Read**: 10 minutes

This guide explains DevStream's cross-session memory preservation system, which ensures you never lose context between Claude Code sessions.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
  - [Session Summary on Startup](#session-summary-on-startup)
  - [Automatic Summary Before Compaction](#automatic-summary-before-compaction)
  - [Manual Summary Preservation](#manual-summary-preservation)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)
- [Best Practices](#best-practices)

---

## Overview

DevStream's session management system automatically preserves your work context across sessions, even when you:
- Close and reopen Claude Code
- Use `/compact` to manage context window limits
- Switch between projects

### How It Works

**Three-Layer Preservation**:

1. **Semantic Memory** - All code, decisions, and context stored with embeddings (permanent)
2. **Session Summaries** - High-level summaries stored before major transitions (queryable)
3. **Startup Continuity** - Previous session summary displayed on next startup (one-time)

**Key Principle**: You can always pick up where you left off, even weeks later.

---

## Features

### Session Summary on Startup

Every time you start Claude Code, DevStream automatically displays a summary of your previous session (if available).

#### What It Displays

```
📋 Previous Session Summary (2025-10-01 14:30)

Tasks Completed:
✅ Implemented JWT authentication
✅ Added user login endpoint
✅ Created password hashing utility

Files Modified:
- src/api/auth.py (new JWT token generation)
- src/models/user.py (added password_hash field)
- tests/test_auth.py (95% coverage)

Key Decisions:
- Using bcrypt for password hashing (OWASP recommended)
- JWT expiration: 24 hours (security vs UX trade-off)

Next Steps:
- Add refresh token rotation
- Implement rate limiting for login endpoint
- Security audit with @code-reviewer
```

#### How It Works

1. **SessionEnd Hook** (when you close Claude Code):
   - Generates summary of completed tasks, modified files, decisions
   - Stores summary in DevStream memory (permanent, searchable)
   - Creates marker file: `~/.claude/state/devstream_last_session.txt`

2. **SessionStart Hook** (when you open Claude Code):
   - Checks for marker file
   - Displays summary if file exists
   - Deletes marker file (one-time display)

#### Configuration

**Enable/Disable**:
```bash
# In .env.devstream
DEVSTREAM_SESSION_SUMMARY_ENABLED=true  # Default: true
DEVSTREAM_SESSION_SUMMARY_MAX_LENGTH=1000  # Max summary characters
```

**Location**:
- Marker file: `~/.claude/state/devstream_last_session.txt`
- Permanent storage: DevStream semantic memory (searchable with `mcp__devstream__devstream_search_memory`)

---

### Automatic Summary Before Compaction

When you run `/compact` (to manage context window limits), DevStream automatically preserves your session state before compaction.

#### What It Preserves

**Comprehensive Session Snapshot**:
- All completed tasks (from current session)
- All modified/created files
- Key decisions and architectural choices
- Outstanding work (incomplete tasks)
- Next steps and recommendations

#### How It Works

**PreCompact Hook** (triggered BEFORE `/compact` executes):

```
User Types: /compact
    ↓
PreCompact Hook Triggered
    ↓
1. Generate session summary
2. Store in DevStream memory with embeddings
3. Create marker file for next session
4. Log preservation confirmation
    ↓
/compact Proceeds (context cleared)
```

**Example Output**:
```
🔄 PreCompact Hook: Preserving session state before compaction...
✅ Summary stored in DevStream memory (ID: session-20251001-1430)
✅ Marker file created: ~/.claude/state/devstream_last_session.txt
✅ Session preserved (5 tasks, 12 files, 3 decisions)
→ /compact proceeding...
```

#### Key Behaviors

- **Non-Blocking**: Always allows `/compact` to proceed (never fails compaction)
- **Automatic**: No user action required
- **Queryable**: Summary stored in memory (search with "session-20251001")
- **Continuity**: Marker file ensures next session shows summary

#### Verification

**Check if summary was stored**:
```
mcp__devstream__devstream_search_memory:
  query: "session summary 2025-10-01"
  content_type: "context"
  limit: 5
```

**Expected Result**:
```json
[
  {
    "content": "Session Summary (2025-10-01 14:30): Completed JWT auth...",
    "content_type": "context",
    "keywords": ["session", "summary", "2025-10-01"],
    "created_at": "2025-10-01T14:30:00Z"
  }
]
```

---

### Manual Summary Preservation

For situations where you want explicit control over summary preservation (e.g., before manually clearing context), use the `/clear-devstream` command.

#### When to Use

- Before manually clearing Claude Code context (not using `/compact`)
- Before switching to a different project
- After completing a major milestone
- When you want to review summary before preservation

#### How to Use

**Command**:
```
/clear-devstream
```

**Interactive Workflow** (5 steps):

```
Step 1: Confirmation Prompt
"⚠️  This will:
1. Generate session summary
2. Store in DevStream memory
3. Create marker file for next session
4. Clear current context

Proceed? (yes/no)"

Step 2: Summary Generation
"🔄 Generating session summary..."
[Uses MCP tool to analyze current session]

Step 3: Summary Preview
"📋 Session Summary Preview:

Tasks: 3 completed, 1 in progress
Files: 8 modified, 2 created
Decisions: 5 architectural choices
Next Steps: 4 recommendations

Full summary: [details...]

Store this summary? (yes/no)"

Step 4: Storage
"✅ Summary stored in DevStream memory
✅ Marker file created for next session"

Step 5: Context Clear
"🧹 Clearing current context..."
[Equivalent to manual context clear]
```

#### Expected Output

**Successful Execution**:
```
✅ Session summary preserved (ID: session-20251001-1500)
✅ DevStream memory updated (vector embeddings generated)
✅ Marker file: ~/.claude/state/devstream_last_session.txt
→ Ready for next session
```

**Cancellation**:
```
❌ Clear cancelled (context preserved)
```

#### Configuration

**Command Location**:
```
.claude/commands/clear-devstream.md
```

**Settings** (`.env.devstream`):
```bash
DEVSTREAM_CLEAR_COMMAND_ENABLED=true  # Enable/disable command
DEVSTREAM_CLEAR_REQUIRE_CONFIRMATION=true  # Require explicit confirmation
```

---

## Configuration

### Environment Variables

**Location**: `.env.devstream`

```bash
# Session Summary Features
DEVSTREAM_SESSION_SUMMARY_ENABLED=true           # Enable session summaries
DEVSTREAM_SESSION_SUMMARY_MAX_LENGTH=1000        # Max summary length (chars)
DEVSTREAM_SESSION_SUMMARY_INCLUDE_FILES=true     # Include modified files list

# PreCompact Hook
DEVSTREAM_PRECOMPACT_ENABLED=true                # Enable automatic preservation
DEVSTREAM_PRECOMPACT_MIN_TASKS=1                 # Min tasks to trigger preservation

# /clear-devstream Command
DEVSTREAM_CLEAR_COMMAND_ENABLED=true             # Enable manual clear command
DEVSTREAM_CLEAR_REQUIRE_CONFIRMATION=true        # Require user confirmation
```

### Settings.json Configuration

**Hook Registration**:
```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/sessions/session_start.py"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/sessions/session_end.py"
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/sessions/pre_compact.py"
          }
        ]
      }
    ]
  }
}
```

**Slash Command Registration**:
```json
{
  "commands": {
    "clear-devstream": {
      "path": ".claude/commands/clear-devstream.md"
    }
  }
}
```

### Marker File Management

**Location**: `~/.claude/state/devstream_last_session.txt`

**Format**:
```
Session Summary (2025-10-01 14:30)

Tasks Completed:
- Task 1 (ID: abc123)
- Task 2 (ID: def456)

Files Modified:
- src/api/auth.py
- src/models/user.py

Key Decisions:
- Decision 1
- Decision 2

Next Steps:
- Step 1
- Step 2
```

**Lifecycle**:
1. Created by: SessionEnd hook, PreCompact hook, /clear-devstream command
2. Read by: SessionStart hook (on Claude Code startup)
3. Deleted by: SessionStart hook (after display)

**Manual Management**:
```bash
# View current marker file
cat ~/.claude/state/devstream_last_session.txt

# Delete marker file (prevent startup display)
rm ~/.claude/state/devstream_last_session.txt

# Create manual marker file (for testing)
echo "Custom summary" > ~/.claude/state/devstream_last_session.txt
```

---

## Troubleshooting

### Summary Not Displayed on Startup

**Symptom**: No summary shown when starting Claude Code

**Possible Causes**:

1. **Marker file missing**
   ```bash
   # Check if file exists
   ls -la ~/.claude/state/devstream_last_session.txt
   ```
   **Solution**: Previous session may not have created marker (no tasks completed)

2. **SessionStart hook not registered**
   ```bash
   # Verify settings.json
   cat ~/.claude/settings.json | grep -A5 "SessionStart"
   ```
   **Solution**: Add SessionStart hook to settings.json (see [Configuration](#configuration))

3. **Hook execution failed**
   ```bash
   # Check hook logs
   tail -n 50 ~/.claude/logs/devstream/session_start.log
   ```
   **Solution**: Review error logs, verify `.devstream/bin/python` exists

4. **Feature disabled**
   ```bash
   # Check .env.devstream
   grep "DEVSTREAM_SESSION_SUMMARY_ENABLED" .env.devstream
   ```
   **Solution**: Set `DEVSTREAM_SESSION_SUMMARY_ENABLED=true`

### PreCompact Hook Not Triggering

**Symptom**: `/compact` runs but no preservation message displayed

**Possible Causes**:

1. **PreCompact hook not registered**
   ```bash
   # Check settings.json
   cat ~/.claude/settings.json | grep -A5 "PreCompact"
   ```
   **Solution**: Add PreCompact hook to settings.json

2. **No tasks completed in session**
   - Minimum 1 task required to trigger preservation
   - **Solution**: Complete at least one task before `/compact`

3. **Hook failed silently**
   ```bash
   # Check logs
   tail -n 50 ~/.claude/logs/devstream/pre_compact.log
   ```
   **Solution**: Review error logs, check MCP server running

4. **Feature disabled**
   ```bash
   grep "DEVSTREAM_PRECOMPACT_ENABLED" .env.devstream
   ```
   **Solution**: Set `DEVSTREAM_PRECOMPACT_ENABLED=true`

### /clear-devstream Command Not Available

**Symptom**: Command not recognized when typed

**Possible Causes**:

1. **Command file missing**
   ```bash
   ls -la .claude/commands/clear-devstream.md
   ```
   **Solution**: Create command file (see FASE 6 implementation)

2. **Command not registered in settings.json**
   ```bash
   cat ~/.claude/settings.json | grep -A5 "clear-devstream"
   ```
   **Solution**: Add command registration to settings.json

3. **Feature disabled**
   ```bash
   grep "DEVSTREAM_CLEAR_COMMAND_ENABLED" .env.devstream
   ```
   **Solution**: Set `DEVSTREAM_CLEAR_COMMAND_ENABLED=true`

4. **Claude Code restart required**
   - Slash commands require restart after registration
   - **Solution**: Restart Claude Code

### Summary Stored But Not Searchable

**Symptom**: Memory search returns no results

**Possible Causes**:

1. **Embeddings not generated**
   ```bash
   # Check Ollama service
   curl http://localhost:11434/api/tags
   ```
   **Solution**: Verify Ollama running, regenerate embeddings

2. **Wrong search query**
   ```
   # Try broader search
   mcp__devstream__devstream_search_memory:
     query: "session"
     limit: 10
   ```
   **Solution**: Use broader keywords

3. **Content type filter too restrictive**
   ```
   # Search without filter
   mcp__devstream__devstream_search_memory:
     query: "session summary"
     # content_type: omit this parameter
   ```
   **Solution**: Remove content_type filter

---

## Examples

### Example 1: Normal Session Workflow

**Day 1 - Afternoon Session**:
```
[Working on authentication feature]
@python-specialist Implement JWT authentication
[Complete task, modify 3 files]

[End of day - Close Claude Code]
→ SessionEnd hook triggered
→ Summary generated and stored
→ Marker file created
```

**Day 2 - Morning Session**:
```
[Start Claude Code]
→ SessionStart hook triggered
→ Display:

📋 Previous Session Summary (2025-10-01 16:30)

Tasks Completed:
✅ Implemented JWT authentication (task ID: abc123)

Files Modified:
- src/api/auth.py (new JWT token generation)
- src/models/user.py (added password_hash field)
- tests/test_auth.py (95% coverage)

Key Decisions:
- Using bcrypt for password hashing (OWASP recommended)
- JWT expiration: 24 hours

Next Steps:
- Add refresh token rotation
- Security audit with @code-reviewer

[Continue work seamlessly]
```

### Example 2: Context Compaction Workflow

**Session with Context Limit**:
```
[Working on multiple features, context window approaching limit]

User: "/compact"

→ PreCompact hook triggered
→ Output:
🔄 PreCompact Hook: Preserving session state...
✅ Summary stored (ID: session-20251001-1430)
✅ Marker file created
✅ Session preserved (5 tasks, 12 files, 3 decisions)
→ /compact proceeding...

[Context cleared, work continues with clean window]
```

**Verification**:
```
mcp__devstream__devstream_search_memory:
  query: "session 2025-10-01"

→ Results:
[
  {
    "content": "Session Summary (2025-10-01 14:30): Completed 5 tasks...",
    "keywords": ["session", "summary", "2025-10-01"],
    "created_at": "2025-10-01T14:30:00Z"
  }
]
```

### Example 3: Manual Summary Preservation

**Before Major Context Clear**:
```
User: "/clear-devstream"

→ Step 1: Confirmation
⚠️  This will:
1. Generate session summary
2. Store in DevStream memory
3. Create marker file
4. Clear context

Proceed? (yes/no)

User: "yes"

→ Step 2: Generation
🔄 Generating session summary...

→ Step 3: Preview
📋 Session Summary Preview:

Tasks: 3 completed, 1 in progress
Files: 8 modified, 2 created
Decisions: 5 architectural choices
Next Steps: 4 recommendations

Full summary:
- Implemented user authentication (JWT, bcrypt)
- Created API endpoints (/login, /register)
- Added password validation (min 8 chars, complexity)
- Modified: src/api/auth.py, src/models/user.py
- Tests: 95% coverage
- Next: Refresh tokens, rate limiting

Store this summary? (yes/no)

User: "yes"

→ Step 4: Storage
✅ Summary stored (ID: session-20251001-1500)
✅ Marker file created
✅ DevStream memory updated

→ Step 5: Clear
🧹 Clearing context...
✅ Context cleared
```

### Example 4: Multi-Day Project Continuity

**Week 1 - Complex Feature Development**:
```
Monday: Start authentication feature
  → SessionEnd: Summary stored

Tuesday: Continue authentication
  → SessionStart: Display Monday's summary
  → Work continues
  → SessionEnd: Updated summary stored

Wednesday: Switch to payment integration
  → SessionStart: Display Tuesday's summary
  → /compact (context limit)
  → PreCompact: Auth summary preserved
  → Work on payments
  → SessionEnd: Payment summary stored

[Weekend break]

Monday (Week 2): Resume work
  → SessionStart: Display last Friday's payment summary
  → Search memory: "authentication" → Find Week 1 auth details
  → Seamless continuity across 5-day gap
```

**Memory Search Example**:
```
# Find authentication work from last week
mcp__devstream__devstream_search_memory:
  query: "authentication JWT bcrypt"
  limit: 5

→ Results include:
- Session summary from Monday (authentication start)
- Session summary from Tuesday (authentication completion)
- Code snippets with JWT implementation
- Decisions about password hashing
- Test coverage reports
```

---

## Best Practices

### 1. Trust the Automation

**DO**:
- ✅ Let hooks run automatically (SessionStart, SessionEnd, PreCompact)
- ✅ Review displayed summaries at startup
- ✅ Use `/compact` freely (preservation is automatic)

**DON'T**:
- ❌ Manually delete marker files (unless debugging)
- ❌ Disable hooks without understanding impact
- ❌ Worry about losing context when compacting

### 2. Use /clear-devstream for Major Transitions

**When to Use**:
- ✅ Switching between unrelated projects
- ✅ Before taking extended breaks (weeks/months)
- ✅ After completing major milestones
- ✅ When you want to review summary before clearing

**When NOT to Use**:
- ❌ Normal session-to-session workflow (SessionEnd handles it)
- ❌ During `/compact` (PreCompact handles it)
- ❌ For trivial work (< 15 minutes)

### 3. Leverage Semantic Memory for Long-Term Recall

**Pattern**:
```
# Work on feature X today
[Automatic storage via hooks]

# Work on feature Y tomorrow
[Automatic storage via hooks]

# Need to remember feature X details next week
mcp__devstream__devstream_search_memory:
  query: "feature X implementation details"

→ Retrieve full context even weeks later
```

**Benefits**:
- Summaries provide high-level overview
- Memory search provides detailed context
- No manual note-taking required

### 4. Monitor Hook Health

**Weekly Check**:
```bash
# Verify hooks executed recently
ls -lt ~/.claude/logs/devstream/ | head -10

# Check for errors
grep "ERROR" ~/.claude/logs/devstream/*.log

# Verify marker file created
ls -la ~/.claude/state/devstream_last_session.txt
```

**If Issues Found**:
- Review [Troubleshooting](#troubleshooting) section
- Check `.env.devstream` configuration
- Verify MCP server running
- Restart Claude Code

### 5. Customize Summary Verbosity

**For Detailed Summaries**:
```bash
# In .env.devstream
DEVSTREAM_SESSION_SUMMARY_MAX_LENGTH=2000  # Longer summaries
DEVSTREAM_SESSION_SUMMARY_INCLUDE_FILES=true  # Include all files
```

**For Concise Summaries**:
```bash
DEVSTREAM_SESSION_SUMMARY_MAX_LENGTH=500  # Shorter summaries
DEVSTREAM_SESSION_SUMMARY_INCLUDE_FILES=false  # Omit file list
```

**Recommendation**: Start with defaults (1000 chars, files included), adjust based on preference.

### 6. Combine with Task Management

**Integrated Workflow**:
```
# Start task
mcp__devstream__devstream_create_task:
  title: "Implement JWT authentication"
  task_type: "coding"

# Work on task
[Automatic memory storage via hooks]

# Complete task
mcp__devstream__devstream_update_task:
  task_id: "abc123"
  status: "completed"

# Session summary includes completed task
[SessionEnd hook generates comprehensive summary]
```

**Benefits**:
- Tasks provide structure
- Summaries provide continuity
- Memory provides searchable history

---

## Next Steps

**After Reading This Guide**:

1. **Verify Features Working**
   - Close and reopen Claude Code (test SessionStart)
   - Run `/compact` (test PreCompact)
   - Try `/clear-devstream` (test manual preservation)

2. **Explore Related Features**
   - [Task Management](core-concepts.md#task-management)
   - [Semantic Memory](core-concepts.md#semantic-memory)
   - [Configuration Options](configuration.md)

3. **Advanced Usage**
   - [Memory Search Strategies](../development/memory-search-strategies.md)
   - [Custom Hook Development](../development/custom-hooks.md)

4. **Get Help**
   - [FAQ](faq.md)
   - [Troubleshooting](troubleshooting.md)
   - [Support Channels](../../CONTRIBUTING.md#getting-help)

---

**Document Version**: 0.1.0-beta
**Last Updated**: 2025-10-02
**Status**: Production Ready - FASE 6 Complete
