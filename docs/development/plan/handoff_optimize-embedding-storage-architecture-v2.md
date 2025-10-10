# GLM-4.6 Handoff Prompt: Embedding Storage Optimization

**Task ID**: 8bc55d6350ac35b27e1b85a96557bbd7
**Model**: GLM-4.6 (Cost-Optimized Execution)
**Handoff From**: Sonnet 4.5 (Planning & Research Phase)
**Handoff Date**: 2025-10-10
**Estimated Duration**: 90 minutes
**Priority**: 9/10

---

## 📚 Related Documentation (MANDATORY REFERENCE)

**CRITICAL**: This handoff prompt is a **summary** for GLM-4.6 execution. The **complete detailed plan** is:

📋 **Full Implementation Plan**: `docs/development/plan/piano_optimize-embedding-storage-architecture-v2.md`

The full plan contains:
- ✅ Complete implementation checklist (Pre-Migration + 3 Phases + Post-Migration)
- ✅ Extended risk mitigation procedures
- ✅ Detailed rollback procedures for each phase
- ✅ Acceptance criteria per phase
- ✅ Full Context7 research findings with Trust Scores
- ✅ Alternative approaches (if primary fails)

**Before starting Phase 1**, GLM-4.6 MUST:
1. Read `piano_optimize-embedding-storage-architecture-v2.md` completely
2. Review the complete implementation checklist
3. Understand all risk mitigation procedures
4. Verify all acceptance criteria are clear

**If any ambiguity arises during execution**, refer to the full plan first before asking for clarification.

---

## Executive Summary

You are GLM-4.6 receiving handoff from Sonnet 4.5 for **execution phase** of embedding storage optimization.

**Problem**: Database 763 MB with 327 MB duplicate JSON embeddings + inefficient storage.

**Root Cause**: Missing `sync_embedding_update` trigger - PostToolUse hook writes JSON expecting auto-sync to BLOB.

**Approved Solution**: 3-phase implementation:
1. **Phase 1**: Create trigger infrastructure (JSON→BLOB sync + auto-cleanup)
2. **Phase 2**: Backfill 45,385 existing JSON records via trigger
3. **Phase 3**: Binary quantization with re-scoring pattern (32x compression)

**Expected Results**: -454 MB total (-59% database size), zero functionality loss, 50% faster search.

---

## Context Transfer: Research Findings

### SQLite Triggers (Context7 - Trust Score 9.7/10)
- ✅ `AFTER UPDATE` triggers execute after row modification
- ✅ `NEW.column` references updated value
- ✅ Triggers can perform multi-step operations (INSERT + UPDATE)
- ✅ Transaction-safe (rollback if trigger fails)

### sqlite-vec JSON→BLOB Conversion (Context7)
```sql
-- Pattern: JSON array to BLOB
vec_f32('[0.1, 0.2, 0.3]') → X'CDCCCC3D...' (BLOB)
-- 768 floats: JSON 10,281 bytes → BLOB 3,072 bytes (3.3x compression)
```

### Binary Quantization (Context7 - Trust Score 9.7/10)
```sql
-- Pattern: Re-scoring for accuracy
vec_quantize_binary(embedding) → bit[768]
-- Storage: 3,072 bytes → 96 bytes (32x compression)
-- Accuracy: Use coarse filter + float32 re-rank for >95% recall
```

**Re-scoring Strategy**:
- Coarse filter: Binary quantized (bit[768]) for fast pre-filtering
- Fine re-rank: Original float32 for top candidates
- Over-fetch 8x candidates, re-rank with L2 distance

---

## Execution Plan: 3 Phases

### PHASE 1: Create Trigger Infrastructure (20 minutes)

**Objective**: Implement missing `sync_embedding_update` trigger.

**Micro-Tasks**:
1. Backup database: `cp data/devstream.db data/devstream.db.backup-phase1`
2. Create trigger SQL file: `.claude/hooks/devstream/migrations/create_sync_trigger.sql`
3. Execute trigger creation
4. Test trigger with single record
5. Verify PostToolUse hook still works

**Trigger SQL** (EXACT IMPLEMENTATION):
```sql
CREATE TRIGGER sync_embedding_update
AFTER UPDATE OF embedding ON semantic_memory
WHEN NEW.embedding IS NOT NULL AND NEW.embedding != ''
BEGIN
    -- Step 1: Convert JSON array → BLOB float32
    -- Step 2: Insert/Replace in vec_semantic_memory
    INSERT OR REPLACE INTO vec_semantic_memory(
        embedding,
        content_type,
        memory_id,
        content_preview
    )
    VALUES (
        vec_f32(NEW.embedding),           -- JSON → BLOB conversion
        NEW.content_type,
        NEW.id,
        substr(NEW.content, 1, 200)       -- First 200 chars preview
    );

    -- Step 3: Cleanup JSON (prevent future duplication)
    UPDATE semantic_memory
    SET embedding = NULL
    WHERE id = NEW.id;
END;
```

**Test Command**:
```bash
.devstream/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/devstream.db')
conn.enable_load_extension(True)
conn.load_extension('.devstream/lib/python3.11/site-packages/sqlite_vec/vec0')

# Test trigger
conn.execute(\"UPDATE semantic_memory SET embedding = '[0.1, 0.2, 0.3]' WHERE id = (SELECT id FROM semantic_memory LIMIT 1)\")
conn.commit()

# Verify
result = conn.execute(\"SELECT embedding FROM semantic_memory WHERE id = (SELECT id FROM semantic_memory LIMIT 1)\").fetchone()
print(f'JSON embedding after trigger: {result[0]}')  # Should be NULL

result = conn.execute(\"SELECT embedding FROM vec_semantic_memory WHERE memory_id = (SELECT id FROM semantic_memory LIMIT 1)\").fetchone()
print(f'BLOB embedding exists: {result is not None}')  # Should be True
"
```

**Acceptance Criteria**:
- ✅ Trigger exists in sqlite_master
- ✅ Test UPDATE creates BLOB, sets JSON to NULL
- ✅ PostToolUse hook continues working (no code changes)

---

### PHASE 2: Backfill Existing JSON Records (40 minutes)

**Objective**: Migrate 45,385 existing JSON embeddings through trigger.

**Micro-Tasks**:
1. Create backfill script: `scripts/backfill_embeddings_via_trigger.py`
2. Backup database: `cp data/devstream.db data/devstream.db.backup-phase2`
3. Execute backfill (batch size 1000)
4. VACUUM + WAL checkpoint
5. Verify results (0 JSON, 45,385 BLOB, -327 MB)

**Backfill Script** (EXACT IMPLEMENTATION):
```python
#!/usr/bin/env .devstream/bin/python
"""
Trigger-Based JSON→BLOB Migration
Leverages existing sync_embedding_update trigger for conversion
"""

import sqlite3
from pathlib import Path

DB_PATH = "data/devstream.db"

def get_db_connection_with_vec(db_path: str):
    """Load database with sqlite-vec extension"""
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    conn.load_extension('.devstream/lib/python3.11/site-packages/sqlite_vec/vec0')
    return conn

def backfill_via_trigger():
    """
    Trigger-based migration: UPDATE each JSON embedding to activate trigger.
    Trigger handles: JSON→BLOB conversion + auto-cleanup
    """
    conn = get_db_connection_with_vec(DB_PATH)
    cursor = conn.cursor()

    # Count records needing migration
    cursor.execute("""
        SELECT COUNT(*) FROM semantic_memory
        WHERE embedding IS NOT NULL AND embedding != ''
    """)
    total = cursor.fetchone()[0]
    print(f"📊 Records to migrate: {total:,}")

    # Fetch all IDs with JSON embeddings
    cursor.execute("""
        SELECT id FROM semantic_memory
        WHERE embedding IS NOT NULL AND embedding != ''
        ORDER BY created_at DESC
    """)
    record_ids = [row[0] for row in cursor.fetchall()]

    # Batch UPDATE to trigger sync
    batch_size = 1000
    for i in range(0, len(record_ids), batch_size):
        batch = record_ids[i:i+batch_size]

        # UPDATE triggers sync_embedding_update for each record
        placeholders = ','.join('?' * len(batch))
        cursor.execute(f"""
            UPDATE semantic_memory
            SET embedding = embedding  -- Dummy update to trigger
            WHERE id IN ({placeholders})
        """, batch)

        conn.commit()

        progress = min(i + batch_size, total)
        print(f"✓ Migrated: {progress:,}/{total:,} ({progress/total*100:.1f}%)")

    # Cleanup
    cursor.execute("VACUUM")
    cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()

    print("✅ Backfill complete via trigger")
    print("✅ Database vacuumed and WAL checkpoint complete")

if __name__ == "__main__":
    backfill_via_trigger()
```

**Execution Command**:
```bash
.devstream/bin/python scripts/backfill_embeddings_via_trigger.py
```

**Acceptance Criteria**:
- ✅ `SELECT COUNT(*) FROM semantic_memory WHERE embedding IS NOT NULL` = 0
- ✅ `SELECT COUNT(*) FROM vec_semantic_memory` = 45,385
- ✅ Database size: 763 MB → ~440 MB (-327 MB)
- ✅ Hybrid search returns results: `curl http://localhost:3000/hybrid-search?query=test`

---

### PHASE 3: Binary Quantization (30 minutes)

**Objective**: 32x compression via binary quantization + re-scoring pattern.

**Micro-Tasks**:
1. Create migration SQL: `.claude/hooks/devstream/migrations/add_binary_quantization.sql`
2. Backup database: `cp data/devstream.db data/devstream.db.backup-phase3`
3. Create vec_semantic_memory_v2 with dual columns
4. Migrate embeddings with quantization
5. Update hybrid-search.ts (re-scoring pattern)
6. Update trigger (include quantization)
7. Swap tables (zero-downtime)
8. VACUUM + WAL checkpoint
9. Test search latency + accuracy

**Migration SQL** (EXACT IMPLEMENTATION):
```sql
-- Step 1: Create new table with binary quantization
CREATE VIRTUAL TABLE vec_semantic_memory_v2 USING vec0(
    embedding_fine float[768],        -- For re-scoring (3,072 bytes)
    embedding_coarse bit[768],         -- For coarse filter (96 bytes)
    content_type TEXT PARTITION KEY,
    +memory_id TEXT,
    +content_preview TEXT
);

-- Step 2: Migrate existing BLOB embeddings with quantization
INSERT INTO vec_semantic_memory_v2(memory_id, embedding_fine, embedding_coarse, content_type, content_preview)
SELECT
    memory_id,
    embedding as embedding_fine,
    vec_quantize_binary(embedding) as embedding_coarse,
    content_type,
    content_preview
FROM vec_semantic_memory;

-- Step 3: Swap tables (zero-downtime)
DROP TABLE vec_semantic_memory;
ALTER TABLE vec_semantic_memory_v2 RENAME TO vec_semantic_memory;
```

**Update Hybrid Search** (mcp-devstream-server/src/tools/hybrid-search.ts):

**OLD CODE** (lines ~150-160):
```typescript
const sql = `
  SELECT memory_id, distance
  FROM vec_semantic_memory
  WHERE embedding MATCH ?
  ORDER BY distance
  LIMIT ?
`;
```

**NEW CODE** (re-scoring pattern):
```typescript
const sql = `
  WITH coarse_matches AS (
    -- Fast binary filter (32x faster)
    SELECT memory_id, embedding_fine
    FROM vec_semantic_memory
    WHERE embedding_coarse MATCH vec_quantize_binary(?)
    ORDER BY distance
    LIMIT ? * 8  -- Over-fetch 8x for accuracy
  )
  -- Fine re-ranking with float32 (high accuracy)
  SELECT
    memory_id,
    vec_distance_L2(embedding_fine, ?) as distance
  FROM coarse_matches
  ORDER BY distance
  LIMIT ?
`;

// Parameters: [queryEmbeddingBinary, limit*8, queryEmbeddingFloat32, limit]
```

**Update Trigger** (.claude/hooks/devstream/migrations/update_trigger_binary_quant.sql):
```sql
DROP TRIGGER IF EXISTS sync_embedding_update;

CREATE TRIGGER sync_embedding_update
AFTER UPDATE OF embedding ON semantic_memory
WHEN NEW.embedding IS NOT NULL AND NEW.embedding != ''
BEGIN
    -- Convert JSON → BLOB + quantize
    INSERT OR REPLACE INTO vec_semantic_memory(
        embedding_fine,
        embedding_coarse,         -- Auto-quantize
        content_type,
        memory_id,
        content_preview
    )
    VALUES (
        vec_f32(NEW.embedding),
        vec_quantize_binary(vec_f32(NEW.embedding)),  -- Quantize on insert
        NEW.content_type,
        NEW.id,
        substr(NEW.content, 1, 200)
    );

    -- Cleanup JSON
    UPDATE semantic_memory SET embedding = NULL WHERE id = NEW.id;
END;
```

**Acceptance Criteria**:
- ✅ `vec_semantic_memory` has dual columns (embedding_fine + embedding_coarse)
- ✅ Database size: 440 MB → ~310 MB (-127 MB additional)
- ✅ Search latency: <250ms avg (test with 10 queries)
- ✅ Search accuracy: >95% recall vs float32 baseline

---

## Files to Modify

1. **Create**: `.claude/hooks/devstream/migrations/create_sync_trigger.sql`
2. **Create**: `scripts/backfill_embeddings_via_trigger.py`
3. **Create**: `.claude/hooks/devstream/migrations/add_binary_quantization.sql`
4. **Create**: `.claude/hooks/devstream/migrations/update_trigger_binary_quant.sql`
5. **Edit**: `mcp-devstream-server/src/tools/hybrid-search.ts` (re-scoring pattern)

---

## Testing Requirements (MANDATORY)

### Phase 1 Tests:
```bash
# Test trigger exists
.devstream/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/devstream.db')
result = conn.execute(\"SELECT name FROM sqlite_master WHERE type='trigger' AND name='sync_embedding_update'\").fetchone()
print(f'✅ Trigger exists: {result is not None}')
"

# Test trigger functionality (see Phase 1 test command above)
```

### Phase 2 Tests:
```bash
# Verify JSON cleanup
.devstream/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/devstream.db')
result = conn.execute(\"SELECT COUNT(*) FROM semantic_memory WHERE embedding IS NOT NULL\").fetchone()
print(f'JSON embeddings remaining: {result[0]} (should be 0)')
"

# Verify BLOB creation
.devstream/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/devstream.db')
conn.enable_load_extension(True)
conn.load_extension('.devstream/lib/python3.11/site-packages/sqlite_vec/vec0')
result = conn.execute(\"SELECT COUNT(*) FROM vec_semantic_memory\").fetchone()
print(f'BLOB embeddings: {result[0]} (should be 45,385)')
"

# Test hybrid search
curl http://localhost:3000/hybrid-search?query=test&limit=5
```

### Phase 3 Tests:
```bash
# Verify dual columns
.devstream/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/devstream.db')
conn.enable_load_extension(True)
conn.load_extension('.devstream/lib/python3.11/site-packages/sqlite_vec/vec0')
result = conn.execute(\"PRAGMA table_info(vec_semantic_memory)\").fetchall()
columns = [row[1] for row in result]
print(f'Columns: {columns}')
print(f'✅ embedding_fine exists: {\"embedding_fine\" in columns}')
print(f'✅ embedding_coarse exists: {\"embedding_coarse\" in columns}')
"

# Test search latency (run 10 times, calculate avg)
for i in {1..10}; do
  time curl -s http://localhost:3000/hybrid-search?query=test&limit=10 > /dev/null
done

# Test search accuracy (compare results with float32 baseline)
```

---

## Rollback Procedures

### Phase 1 Rollback:
```sql
DROP TRIGGER IF EXISTS sync_embedding_update;
```

### Phase 2 Rollback:
```bash
# Restore from backup
cp data/devstream.db.backup-phase2 data/devstream.db
```

### Phase 3 Rollback:
```sql
-- Revert table swap
DROP TABLE vec_semantic_memory;
ALTER TABLE vec_semantic_memory_backup RENAME TO vec_semantic_memory;

-- Revert trigger
DROP TRIGGER IF EXISTS sync_embedding_update;
-- (re-create Phase 1 trigger)
```

---

## Success Metrics

| Metric | Target | Validation |
|--------|--------|------------|
| Database size reduction | -454 MB (-59%) | `ls -lh data/devstream.db` |
| JSON embeddings remaining | 0 | `SELECT COUNT(*) FROM semantic_memory WHERE embedding IS NOT NULL` |
| BLOB embeddings created | 45,385 | `SELECT COUNT(*) FROM vec_semantic_memory` |
| Search latency | <250ms avg | Time 10 curl requests |
| Search accuracy | >95% recall | Compare results with baseline |
| PostToolUse hook working | ✅ | Test storing new memory record |
| Zero downtime | ✅ | MCP server never restarted |

---

## Execution Instructions for GLM-4.6

**START HERE**:

1. **Phase 1**: Create trigger infrastructure
   - Mark Phase 1 todos "in_progress" one at a time
   - Execute trigger creation SQL
   - Test trigger functionality
   - Verify PostToolUse hook still works
   - Mark Phase 1 todos "completed"

2. **Phase 2**: Backfill existing records
   - Mark Phase 2 todos "in_progress" one at a time
   - Create and execute backfill script
   - VACUUM + WAL checkpoint
   - Verify results (0 JSON, 45,385 BLOB, -327 MB)
   - Mark Phase 2 todos "completed"

3. **Phase 3**: Binary quantization
   - Mark Phase 3 todos "in_progress" one at a time
   - Create migration SQL
   - Update hybrid-search.ts
   - Update trigger
   - Swap tables
   - VACUUM + WAL checkpoint
   - Test search latency + accuracy
   - Mark Phase 3 todos "completed"

4. **Verification**: Run all tests
   - Database size: -454 MB
   - Search latency: <250ms
   - Search accuracy: >95%
   - PostToolUse hook: working

5. **Task Completion**:
   - Update task status: "completed"
   - Store lessons learned in DevStream memory
   - Generate final report

---

## DevStream Protocol Compliance

- ✅ STEP 1 (DISCUSSION): Completed by Sonnet 4.5
- ✅ STEP 2 (ANALYSIS): Completed by Sonnet 4.5
- ✅ STEP 3 (RESEARCH): Context7 research completed
- ✅ STEP 4 (PLANNING): Plan v2 created and approved
- ✅ STEP 5 (APPROVAL): User approved plan v2
- ⏸️ **STEP 6 (IMPLEMENTATION)**: YOUR TASK - Execute 3 phases
- ⏸️ **STEP 7 (VERIFICATION)**: YOUR TASK - Run all tests, verify metrics

---

## Questions or Issues?

If you encounter issues during execution:
1. Check rollback procedures for the current phase
2. Review Context7 research findings above
3. Verify sqlite-vec extension is loaded
4. Check database backup exists before proceeding
5. Test hybrid search after each phase

**Task ID**: 8bc55d6350ac35b27e1b85a96557bbd7
**DevStream DB**: `data/devstream.db`
**MCP Server**: `http://localhost:3000`

---

## 🔗 Documentation Cross-Reference

**Primary Documents**:
1. **Handoff Prompt** (this file): `docs/development/plan/handoff_optimize-embedding-storage-architecture-v2.md`
2. **Full Implementation Plan**: `docs/development/plan/piano_optimize-embedding-storage-architecture-v2.md` ⚠️ **MANDATORY READ**

**Support Documents**:
- DevStream Task: `mcp__devstream__devstream_get_implementation_plan` with task_id `8bc55d6350ac35b27e1b85a96557bbd7`
- Database: `data/devstream.db`
- MCP Server: `mcp-devstream-server/` (port 3000)

**REMINDER**: The full implementation plan (`piano_optimize-embedding-storage-architecture-v2.md`) contains critical details not summarized here. Read it before starting Phase 1.

---

**Handoff Complete**. You are now authorized to execute Phases 1-3.

Good luck, GLM-4.6! 🚀
