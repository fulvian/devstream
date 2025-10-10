# GLM-4.6 Handoff Prompt: Fix Vector Search System Issues

**Session Transfer**: Sonnet 4.5 → GLM-4.6
**Task ID**: `6e63cfeb622dc7f16e9b38316589a5a5`
**Plan ID**: `a0bb9e2a9c51016045a5aacafe6cd0dd`
**Priority**: 10/10 (CRITICAL)
**Estimated Duration**: 4h 45min
**Generated**: 2025-10-09 23:02

---

## 🎯 MISSION BRIEFING

You are GLM-4.6, taking over implementation of a **critical fix** for DevStream's vector search system. Sonnet 4.5 has completed STEPS 1-5 (DISCUSSION, ANALYSIS, RESEARCH, PLANNING, APPROVAL). Your role: **Execute STEP 6 (IMPLEMENTATION) + STEP 7 (TESTING)** with precision.

**Context**: DevStream semantic search is **100% non-functional** despite successful storage. Root cause: 4 system-level issues. This handoff includes complete research findings, implementation plan, and execution instructions.

---

## 📊 BACKGROUND CONTEXT (STEPS 1-3 Completed by Sonnet 4.5)

### STEP 1: DISCUSSION - Problem Statement

**Symptoms**:
- ✅ Storage: SUCCESS (embeddings generated, Memory IDs created)
- ❌ Search: FAILURE (0% success rate, universal failure across all queries)
- 💥 Impact: Complete loss of semantic memory retrieval → zero cross-session continuity

**Root Cause Analysis** (4 Issues Identified):

1. **MCP Configuration Path**
   - Problem: `.claude/mcp_servers.json` uses `data.noindex/devstream.db` instead of `data/devstream.db`
   - Impact: MCP server accesses isolated database → search queries miss all stored data
   - Evidence: `lsof` shows PID 1873 using `data.noindex/`, hooks use `data/`

2. **Missing Embeddings**
   - Problem: 38,145 of 48,265 records (79%) have NULL embeddings
   - Impact: Vector search cannot match queries without embeddings
   - Evidence: Database query shows 79% gap in `semantic_memory.embedding`

3. **PostToolUse Insertion Gap**
   - Problem: Hook does INSERT → then UPDATE embedding (2-step pattern)
   - Impact: Ollama failure between INSERT and UPDATE = permanent gap
   - Evidence: Code analysis shows no retry logic in embedding generation

4. **No Health Monitoring**
   - Problem: Zero proactive detection of MCP/Ollama failures
   - Impact: Cannot diagnose issues without manual investigation
   - Evidence: No health check endpoint exists in MCP server

**Decision**: Fix all 4 issues systematically to restore full functionality.

### STEP 2: ANALYSIS - Codebase Investigation

**Key Files Analyzed**:

1. **`.claude/mcp_servers.json`** (Line 14)
   - Current: `"DEVSTREAM_DB_PATH": "${CLAUDE_PROJECT_DIR}/data.noindex/devstream.db"`
   - Required: `"DEVSTREAM_DB_PATH": "${CLAUDE_PROJECT_DIR}/data/devstream.db"`

2. **`data/devstream.db`** vs **`data.noindex/devstream.db`**
   - `data/`: 48,265 records (production database used by hooks)
   - `data.noindex/`: Unknown count (isolated database used by MCP server)
   - Issue: Two separate databases → search queries miss hook-stored data

3. **`.claude/hooks/devstream/memory/post_tool_use.py`** (Lines 148-170)
   - Current pattern:
     ```python
     # Step 1: INSERT without embedding
     memory_id = await self.db_client.insert_memory(content, content_type, keywords)

     # Step 2: Generate embedding (can fail)
     embedding = self._generate_embedding(content)

     # Step 3: UPDATE with embedding (if Step 2 succeeds)
     await self.update_memory_embedding(memory_id, embedding)
     ```
   - Problem: Ollama failure in Step 2 → record inserted without embedding → permanent gap
   - Required: Retry logic (3 attempts, exponential backoff)

4. **`mcp-devstream-server/src/tools/`**
   - Missing: Health check endpoint
   - Required: `health-check.ts` with DB, Ollama, coverage monitoring

**Acceptance Criteria Defined**:
- ✅ MCP server uses correct DB path (`data/devstream.db`)
- ✅ Zero processes accessing `data.noindex/devstream.db`
- ✅ Embedding coverage ≥95% (≥45,851/48,265 records)
- ✅ PostToolUse graceful failure handling (retry logic)
- ✅ Health check endpoint operational

### STEP 3: RESEARCH - Context7 Findings (4 Libraries)

#### 1. **sqlite-vec** (Trust Score: 9.7/10 | 122 Code Snippets)

**Library ID**: `/asg017/sqlite-vec`

**Key Finding - Extension Loading (Node.js)**:
```javascript
import * as sqliteVec from "sqlite-vec";
import Database from "better-sqlite3";

const db = new Database("data/devstream.db");
sqliteVec.load(db);  // Automatic extension loading

// Verify
const { vec_version } = db.prepare("select vec_version()").get();
console.log(`sqlite-vec version: ${vec_version}`);
```

**Validation**: ✅ NPM package includes precompiled extension → no manual `.load` needed

**Hybrid Search Pattern (RRF - Reciprocal Rank Fusion)**:
```sql
-- Combine semantic (60%) + keyword (40%)
WITH vec_matches AS (
  SELECT rowid, ROW_NUMBER() OVER (ORDER BY distance) AS rank_number
  FROM vec_semantic_memory
  WHERE embedding MATCH :query AND k = 10
),
fts_matches AS (
  SELECT rowid, ROW_NUMBER() OVER (ORDER BY rank) AS rank_number
  FROM fts_semantic_memory
  WHERE content MATCH :query LIMIT 10
)
SELECT
  coalesce(1.0 / (:rrf_k + fts_rank), 0.0) * 0.4 +
  coalesce(1.0 / (:rrf_k + vec_rank), 0.0) * 0.6 AS combined_rank
FROM fts_matches FULL OUTER JOIN vec_matches ...
ORDER BY combined_rank DESC;
```

**Metadata Filtering** (our current pattern ✅):
```sql
SELECT * FROM vec_semantic_memory
WHERE embedding MATCH '[...]' AND k = 5
  AND content_type = 'code'  -- Standard SQL WHERE clauses
  AND created_at > '2025-10-01';
```

#### 2. **ollama-python** (Trust Score: 7.5/10 | 35 Code Snippets)

**Library ID**: `/ollama/ollama-python`

**Key Finding - Batch Embedding Generation**:
```python
import ollama

# Batch processing (RECOMMENDED for backfill)
response = ollama.embed(
    model='gemma3',
    input=['text1', 'text2', 'text3']  # Array input
)
embeddings = response['embeddings']  # List[List[float]]
```

**Batch Size Best Practice**:
- ✅ No explicit limit mentioned in docs
- ✅ Our current limit (16) is conservative and safe
- ✅ Larger batches = better throughput

**Error Handling Pattern**:
```python
import ollama

try:
    response = ollama.embed(model='gemma3', input=texts)
except ollama.ResponseError as e:
    print(f'Error: {e.error}')
    if e.status_code == 404:
        # Model not found - pull it
        ollama.pull('gemma3')
    elif e.status_code == 500:
        # Server error - retry with backoff
        pass
```

**keep_alive Configuration** (memory optimization):
```python
response = ollama.embed(
    model='gemma3',
    input=texts,
    keep_alive="5m"  # Auto-unload after 5 min idle
)
```
- ✅ Our current pattern uses `keep_alive="5m"` (optimal for backfill)
- ⚠️ Cold start penalty: ~2-3s when model reloads after idle

#### 3. **SQLite** (Trust Score: N/A | 244 Code Snippets)

**Library ID**: `/sqlite/sqlite`

**Key Finding - WAL Mode & Consistency**:
```sql
-- Verify WAL mode (our current setup ✅)
PRAGMA journal_mode;  -- Should return "wal"

-- Manual checkpoint (if needed)
PRAGMA wal_checkpoint(FULL);

-- Verify integrity
PRAGMA integrity_check;
```

**WAL Mode Benefits** (already enabled ✅):
- ✅ Better concurrency (readers don't block writers)
- ✅ Atomic transactions
- ✅ Checkpoint control

**Triggers Pattern** (our implementation ✅):
```sql
CREATE TRIGGER sync_update_memory
AFTER UPDATE ON semantic_memory
WHEN NEW.embedding IS NOT NULL AND NEW.embedding != ''
    AND (OLD.embedding IS NULL OR OLD.embedding != NEW.embedding)
BEGIN
    -- Cleanup old entries
    DELETE FROM vec_semantic_memory WHERE memory_id = OLD.id;

    -- Insert updated vector
    INSERT INTO vec_semantic_memory(embedding, content_type, memory_id, content_preview)
    VALUES (vec_f32(JSON_EXTRACT(NEW.embedding, '$')), NEW.content_type, NEW.id, ...);
END;
```
**Best Practice**: WHEN clauses prevent unnecessary trigger executions ✅

#### 4. **aiosqlite** (Trust Score: 7.7/10 | 33 Code Snippets)

**Library ID**: `/omnilib/aiosqlite`

**Key Finding - Async Connection Management**:
```python
import aiosqlite

# Context manager pattern (best practice)
async with aiosqlite.connect(db_path) as db:
    await db.execute("INSERT INTO ...")
    await db.commit()

    async with db.execute("SELECT ...") as cursor:
        async for row in cursor:
            # Process row
            pass
```

**Row Factory Pattern**:
```python
async with aiosqlite.connect(db_path) as db:
    db.row_factory = aiosqlite.Row  # Dict-like access
    async with db.execute("SELECT * FROM table") as cursor:
        async for row in cursor:
            value = row['column']  # Named access
```

---

## 🎯 IMPLEMENTATION PLAN (22 Micro-Tasks)

**Plan File**: `docs/development/plan/piano_fix-vector-search-system-issues.md`

**Plan Structure**:
- **FASE 1**: MCP Configuration + DB Reconciliation (30 min) - Tasks 1.1 to 1.6
- **FASE 2**: Embedding Backfill + PostToolUse Enhancement (2h 45min) - Tasks 2.1 to 2.6
- **FASE 3**: Documentation + Health Check (1h) - Tasks 3.1 to 3.4
- **STEP 7**: Testing & Verification (30 min) - Tasks 7.1 to 7.3

**Total**: 22 micro-tasks, 4h 45min estimated duration

**Critical Path**:
1. Fix MCP config path → Restart MCP server → Verify correct DB in use
2. Run backfill script (~2h for 38,145 records) → Verify 95%+ coverage
3. Add retry logic to PostToolUse → Test failure handling
4. Create health check endpoint → Update documentation
5. Run all tests → Verify all 4 issues resolved

---

## 🚀 EXECUTION INSTRUCTIONS FOR GLM-4.6

### Starting Actions (MANDATORY)

**Action 1**: Read the complete implementation plan
```bash
Read: docs/development/plan/piano_fix-vector-search-system-issues.md
```

**Action 2**: Create TodoWrite list with all 22 micro-tasks
```json
[
  {
    "content": "Backup MCP configuration file",
    "activeForm": "Backing up MCP configuration",
    "status": "pending"
  },
  {
    "content": "Fix DB path in mcp_servers.json",
    "activeForm": "Fixing DB path in config",
    "status": "pending"
  },
  {
    "content": "Kill wrong-path MCP instance (PID 1873)",
    "activeForm": "Killing wrong-path MCP instance",
    "status": "pending"
  },
  {
    "content": "Restart MCP with correct path",
    "activeForm": "Restarting MCP server",
    "status": "pending"
  },
  {
    "content": "Database reconciliation (data/ vs data.noindex/)",
    "activeForm": "Reconciling databases",
    "status": "pending"
  },
  {
    "content": "Add DB validation to startup script",
    "activeForm": "Adding DB validation",
    "status": "pending"
  },
  {
    "content": "Verify Ollama service running",
    "activeForm": "Verifying Ollama service",
    "status": "pending"
  },
  {
    "content": "Dry-run backfill test (5 records)",
    "activeForm": "Running dry-run backfill",
    "status": "pending"
  },
  {
    "content": "Execute full backfill (38,145 records)",
    "activeForm": "Executing full backfill",
    "status": "pending"
  },
  {
    "content": "Verify backfill coverage (≥95%)",
    "activeForm": "Verifying backfill coverage",
    "status": "pending"
  },
  {
    "content": "Add retry logic to PostToolUse hook",
    "activeForm": "Adding retry logic",
    "status": "pending"
  },
  {
    "content": "Test PostToolUse failure handling",
    "activeForm": "Testing failure handling",
    "status": "pending"
  },
  {
    "content": "Document vec0 extension loading",
    "activeForm": "Documenting vec0 loading",
    "status": "pending"
  },
  {
    "content": "Create MCP health endpoint",
    "activeForm": "Creating health endpoint",
    "status": "pending"
  },
  {
    "content": "Add embedding coverage metric",
    "activeForm": "Adding coverage metric",
    "status": "pending"
  },
  {
    "content": "Update troubleshooting documentation",
    "activeForm": "Updating documentation",
    "status": "pending"
  },
  {
    "content": "Run unit tests",
    "activeForm": "Running unit tests",
    "status": "pending"
  },
  {
    "content": "Run integration tests",
    "activeForm": "Running integration tests",
    "status": "pending"
  },
  {
    "content": "Verify all 4 issues resolved",
    "activeForm": "Verifying issue resolution",
    "status": "pending"
  }
]
```

**Action 3**: Start with Task 1.1 (Backup MCP Configuration)

---

### Execution Rules (CRITICAL)

#### 🚨 MANDATORY Rules

1. **Python Environment** (ALWAYS)
   - ✅ Use `.devstream/bin/python` for ALL Python commands
   - ❌ NEVER use `python`, `python3`, or system Python
   - ❌ NEVER use `uv run` (non-persistent environment)

2. **TodoWrite Tracking** (ALWAYS)
   - ✅ Mark task "in_progress" BEFORE starting work
   - ✅ Mark task "completed" IMMEDIATELY after finishing
   - ✅ ONE task "in_progress" at a time
   - ❌ NEVER mark "completed" without verifying success criteria

3. **Success Criteria Verification** (ALWAYS)
   - ✅ Check success criteria AFTER each task
   - ✅ Document verification results
   - ❌ NEVER proceed to next task if criteria not met

4. **Backup Before Modifications** (ALWAYS)
   - ✅ Backup config files before editing (`.backup-YYYYMMDD-HHMMSS`)
   - ✅ Verify backup created successfully
   - ❌ NEVER modify critical files without backup

5. **Testing Before Completion** (ALWAYS)
   - ✅ Run STEP 7 (Testing & Verification) BEFORE marking task complete
   - ✅ 100% unit test pass rate required
   - ✅ 100% integration test pass rate required
   - ❌ NEVER mark task "completed" with failing tests

#### 📊 Progress Logging

**Use DevStream Memory for ALL decisions**:
```python
# Log major decisions
mcp__devstream__devstream_store_memory(
    content="Decision: Archive data.noindex/ after verifying data/ completeness",
    content_type="decision",
    keywords=["database", "reconciliation", "migration"]
)

# Log learnings
mcp__devstream__devstream_store_memory(
    content="Lesson: Backfill with batch_size=16 completed in 1h 58min (faster than expected)",
    content_type="learning",
    keywords=["backfill", "performance", "embedding"]
)

# Log errors
mcp__devstream__devstream_store_memory(
    content="Error: Ollama failed on batch 342, retried 3 times, skipped 2 records",
    content_type="error",
    keywords=["ollama", "embedding", "retry"]
)
```

---

### Tools Available

| Tool | Usage | Notes |
|------|-------|-------|
| **Bash** | Command execution | Use for system commands, git, npm, curl |
| **Read** | File inspection | Use before editing any file |
| **Edit** | File modification | Exact string replacement only |
| **Write** | File creation | For new files only (not existing) |
| **TodoWrite** | Task tracking | MANDATORY for progress tracking |
| **mcp__devstream__*** | DevStream operations | Memory storage, task updates |
| **.devstream/bin/python** | Python execution | MANDATORY for ALL Python commands |

---

### Success Criteria Summary

**FASE 1** (30 min):
- ✅ `.claude/mcp_servers.json` uses `data/devstream.db`
- ✅ PID 1873 killed, zero processes on `data.noindex/`
- ✅ MCP server running with correct DB path
- ✅ Database reconciliation decision documented
- ✅ Startup script has DB path validation

**FASE 2** (2h 45min):
- ✅ Ollama service verified running
- ✅ Dry-run backfill test passed (5 records)
- ✅ Full backfill completed (38,145 records)
- ✅ Embedding coverage ≥95% (≥36,238/38,145)
- ✅ PostToolUse retry logic added (3 attempts, exponential backoff)
- ✅ Failure handling test passed (no crash, graceful degradation)

**FASE 3** (1h):
- ✅ `docs/architecture/vector-search-engine-setup.md` created
- ✅ `mcp-devstream-server/src/tools/health-check.ts` implemented
- ✅ Health endpoint returns DB, Ollama, coverage metrics
- ✅ `docs/guides/troubleshooting.md` updated with 4 root causes

**STEP 7** (30 min):
- ✅ 100% unit test pass rate
- ✅ 100% integration test pass rate
- ✅ All 4 issues manually verified resolved

---

### Troubleshooting Guide

**Issue**: MCP server won't restart after config change
**Fix**:
```bash
# Kill all MCP processes
pkill -f "mcp-devstream-server"

# Verify all killed
ps aux | grep mcp-devstream-server

# Restart
./start-devstream.sh
```

**Issue**: Backfill script fails with Ollama connection error
**Fix**:
```bash
# Check Ollama status
curl http://localhost:11434/api/embed -d '{"model": "gemma3", "input": "test"}'

# Restart Ollama if needed
ollama serve &

# Verify model loaded
curl http://localhost:11434/api/tags | grep gemma3
```

**Issue**: Database locked during reconciliation
**Fix**:
```bash
# Check for locks
lsof | grep devstream.db

# Kill locking processes
kill <PID>

# Checkpoint WAL
sqlite3 data/devstream.db "PRAGMA wal_checkpoint(FULL);"
```

---

## 📝 FINAL CHECKLIST (Before Task Completion)

- [ ] All 22 micro-tasks marked "completed" in TodoWrite
- [ ] All success criteria verified and documented
- [ ] 100% unit test pass rate
- [ ] 100% integration test pass rate
- [ ] All 4 issues manually verified resolved
- [ ] MCP server using correct DB path (`data/devstream.db`)
- [ ] Embedding coverage ≥95%
- [ ] PostToolUse retry logic operational
- [ ] Health check endpoint functional
- [ ] Documentation updated (architecture + troubleshooting)
- [ ] DevStream memory populated with decisions/learnings
- [ ] Zero regression on existing functionality

---

## 🎯 HANDOFF COMPLETION

**When you finish**:

1. Mark task `6e63cfeb622dc7f16e9b38316589a5a5` as "completed" in DevStream
2. Store final summary in DevStream memory:
```python
mcp__devstream__devstream_store_memory(
    content="Task completed: Fixed 4 critical issues in vector search system. MCP config corrected, 95%+ embeddings backfilled, retry logic added, health check operational. All tests passing.",
    content_type="learning",
    keywords=["task-completion", "vector-search", "fix", "success"]
)
```
3. Notify user: "✅ Task complete. All 4 issues resolved. System operational."

---

**Handoff Generated**: 2025-10-09 23:02
**Model**: GLM-4.6 (execution-optimized)
**Session Transfer**: Sonnet 4.5 → GLM-4.6
**Ready for Execution**: ✅

---

## 🚀 START HERE

Copy this prompt into a **new GLM-4.6 session** on [z.ai](https://z.ai) or [nano-gpt.com](https://nano-gpt.com) to begin execution.

Your first action: Read `docs/development/plan/piano_fix-vector-search-system-issues.md` and create the TodoWrite list.

Good luck! 🎯
