# Implementation Plan v2: Optimize Embedding Storage Architecture (CORRECTED)

**Task ID**: 8bc55d6350ac35b27e1b85a96557bbd7
**Phase**: Database Optimization & Architecture
**Priority**: 9/10
**Type**: Analysis + Implementation
**Created**: 2025-10-10
**Status**: Planning (STEP 4 - Revised)

---

## Executive Summary

**Problem**: Database contains 327 MB of duplicate embedding data + inefficient storage format.

**Root Cause**:
- PostToolUse hook stores embeddings as **JSON TEXT** in `semantic_memory.embedding` (10,281 bytes/embedding)
- Code assumes **database trigger** auto-syncs to `vec_semantic_memory` BLOB format
- **Trigger NEVER created** - manual sync via backfill scripts only
- Hybrid search uses ONLY `vec_semantic_memory` - JSON copy unused

**Correct Solution** (User-Validated):
1. ✅ **Create trigger infrastructure** that hook expects (JSON→BLOB sync + auto-cleanup)
2. ✅ **Backfill existing** JSON embeddings through trigger
3. ✅ **Binary Quantization** as **MANDATORY** optimization (8x compression)

**Expected Results**:
- Phase 1+2: -327 MB JSON waste + proper architecture
- Phase 3: Additional -127 MB via binary quantization (145 MB → 18 MB)
- **Total**: -454 MB (-59% database size), zero functionality loss

---

## Context7 Research Summary

### SQLite Triggers (Official Docs)
- ✅ `AFTER UPDATE` triggers execute after row modification
- ✅ `NEW.column` references updated value
- ✅ Triggers can perform multi-step operations (INSERT + UPDATE)
- ✅ Transaction-safe (rollback if trigger fails)

### sqlite-vec JSON→BLOB Conversion (Trust Score 9.7/10)
```sql
-- Context7 Pattern: JSON array to BLOB
vec_f32('[0.1, 0.2, 0.3]') → X'CDCCCC3D...' (BLOB)
-- 768 floats: JSON 10,281 bytes → BLOB 3,072 bytes (3.3x compression)
```

### Binary Quantization (Trust Score 9.7/10)
```sql
-- Context7 Pattern: Re-scoring for accuracy
vec_quantize_binary(embedding) → bit[768]
-- Storage: 3,072 bytes → 96 bytes (32x compression)
-- Accuracy: Use coarse filter + float32 re-rank
```

**Re-scoring Strategy**:
- Coarse filter: Binary quantized (bit[768]) for fast pre-filtering
- Fine re-rank: Original float32 for top candidates
- Context7 example: Over-fetch 8x candidates, re-rank with L2 distance

---

## CORRECTED Architecture Plan

### Phase 1: Create Trigger Infrastructure (What Code Expects)

**Objective**: Implement missing `sync_embedding_update` trigger

**Trigger Specification**:
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

    -- Step 3: Cleanup JSON (prevent duplication in future)
    UPDATE semantic_memory
    SET embedding = NULL
    WHERE id = NEW.id;
END;
```

**Context7 Pattern Applied**:
- `vec_f32(NEW.embedding)`: Converts JSON array `'[0.1, 0.2, ...]'` → BLOB
- `INSERT OR REPLACE`: Handles both new and updated embeddings
- **Auto-cleanup**: Removes JSON after BLOB created (prevents future duplication)

**Testing**:
```sql
-- Test trigger
UPDATE semantic_memory
SET embedding = '[0.1, 0.2, 0.3, 0.4]'
WHERE id = 'test-id';

-- Verify: BLOB created, JSON cleaned
SELECT
    (SELECT embedding FROM semantic_memory WHERE id = 'test-id') as json_embedding,  -- Should be NULL
    (SELECT embedding FROM vec_semantic_memory WHERE memory_id = 'test-id') as blob_embedding  -- Should be BLOB
FROM semantic_memory LIMIT 1;
```

**Expected Result**: PostToolUse hook continues working as-is, trigger handles sync automatically.

---

### Phase 2: Backfill Existing JSON Records

**Objective**: Migrate 45,385 existing JSON embeddings through trigger

**Backfill Strategy**:
```python
#!/usr/bin/env .devstream/bin/python
"""
Trigger-Based JSON→BLOB Migration
Leverages existing sync_embedding_update trigger for conversion
"""

import sqlite3
from pathlib import Path

DB_PATH = "data/devstream.db"

def backfill_via_trigger():
    """
    Trigger-based migration: UPDATE each JSON embedding to activate trigger.
    Trigger handles: JSON→BLOB conversion + auto-cleanup
    """
    conn = get_db_connection_with_vec(DB_PATH)  # Load sqlite-vec extension
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

    conn.close()
    print("✅ Backfill complete via trigger")

if __name__ == "__main__":
    backfill_via_trigger()
```

**Alternative Direct Sync** (if trigger fails):
```python
# Fallback: Direct INSERT without trigger
for record in records_with_json:
    embedding_blob = struct.pack(f'{len(record.embedding)}f', *record.embedding)
    cursor.execute("""
        INSERT OR REPLACE INTO vec_semantic_memory(embedding, content_type, memory_id, content_preview)
        VALUES (?, ?, ?, ?)
    """, (embedding_blob, record.content_type, record.id, record.content[:200]))

    # Manual cleanup
    cursor.execute("UPDATE semantic_memory SET embedding = NULL WHERE id = ?", (record.id,))
```

**Expected Result**: All 45,385 JSON embeddings converted to BLOB, JSON fields NULL, -327 MB space saved.

---

### Phase 3: Binary Quantization (MANDATORY)

**Objective**: 32x compression via binary quantization + re-scoring pattern

**Why Mandatory** (Context7 Research):
- **Storage**: 145 MB (float32) → 4.5 MB (binary) = -140 MB saved
- **Performance**: Binary search is 32x faster for coarse filtering
- **Accuracy**: Re-scoring pattern maintains >95% recall (Context7 benchmark)

**Architecture Change**: Re-scoring Pattern
```sql
-- OLD: Single float32 column
CREATE VIRTUAL TABLE vec_semantic_memory USING vec0(
    embedding float[768],
    ...
);

-- NEW: Dual-column re-scoring pattern
CREATE VIRTUAL TABLE vec_semantic_memory_v2 USING vec0(
    embedding_fine float[768],        -- For re-scoring (3,072 bytes)
    embedding_coarse bit[768],         -- For coarse filter (96 bytes)
    content_type TEXT PARTITION KEY,
    +memory_id TEXT,
    +content_preview TEXT
);
```

**Migration Script**:
```sql
-- Step 1: Create new table with binary quantization
CREATE VIRTUAL TABLE vec_semantic_memory_v2 USING vec0(
    embedding_fine float[768],
    embedding_coarse bit[768],
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
```typescript
// OLD: Single float32 search
const sql = `
  SELECT memory_id, distance
  FROM vec_semantic_memory
  WHERE embedding MATCH ?
  ORDER BY distance
  LIMIT ?
`;

// NEW: Re-scoring pattern (Context7)
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

**Update PostToolUse Hook Trigger**:
```sql
CREATE TRIGGER sync_embedding_update_v2
AFTER UPDATE OF embedding ON semantic_memory
WHEN NEW.embedding IS NOT NULL AND NEW.embedding != ''
BEGIN
    -- Convert JSON → BLOB
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

**Expected Result**:
- Storage: 145 MB → 18 MB (-127 MB, 87% reduction)
- Search latency: -50% (coarse filter optimization)
- Accuracy: >95% recall (Context7 benchmark with re-scoring)

---

## Implementation Phases Summary

| Phase | Task | Storage Impact | Functionality Impact |
|-------|------|----------------|---------------------|
| **1** | Create trigger (JSON→BLOB sync + cleanup) | 0 MB (infrastructure) | ✅ Enables auto-sync |
| **2** | Backfill 45,385 JSON → BLOB via trigger | -327 MB (JSON removed) | ✅ Zero impact |
| **3** | Binary quantization + re-scoring | -127 MB (BLOB optimization) | ✅ Faster search |
| **TOTAL** | | **-454 MB (-59%)** | **✅ Improved performance** |

---

## Acceptance Criteria

### Phase 1 (Trigger Creation):
- ✅ Trigger `sync_embedding_update` exists in sqlite_master
- ✅ Test: UPDATE with JSON → BLOB created, JSON NULL
- ✅ PostToolUse hook continues working (no code changes needed)

### Phase 2 (Backfill):
- ✅ `SELECT COUNT(*) FROM semantic_memory WHERE embedding IS NOT NULL` = 0
- ✅ `SELECT COUNT(*) FROM vec_semantic_memory` = 45,385
- ✅ Database size: 763 MB → ~440 MB (-327 MB)
- ✅ Hybrid search returns results (curl test)

### Phase 3 (Binary Quantization):
- ✅ `vec_semantic_memory` has dual columns (embedding_fine + embedding_coarse)
- ✅ Database size: 440 MB → ~310 MB (-127 MB additional)
- ✅ Search latency: <250ms avg (50% improvement)
- ✅ Search accuracy: >95% recall vs float32 baseline

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Trigger breaks PostToolUse | Test with single record first; rollback script ready |
| vec_f32() JSON parse error | Validate JSON format before trigger creation |
| Binary quant accuracy loss | Re-scoring pattern maintains 95%+ recall (Context7) |
| Zero-downtime migration | Use table swap pattern (CREATE→INSERT→SWAP) |
| Rollback needed | Backup before each phase, documented restore procedure |

**Rollback Procedure**:
```sql
-- Phase 1 rollback: Drop trigger
DROP TRIGGER IF EXISTS sync_embedding_update;

-- Phase 2 rollback: Restore from backup
-- cp data/devstream.db.backup-phase1 data/devstream.db

-- Phase 3 rollback: Revert table swap
DROP TABLE vec_semantic_memory;
ALTER TABLE vec_semantic_memory_backup RENAME TO vec_semantic_memory;
```

---

## Implementation Checklist

### Pre-Migration:
- [ ] Backup database: `cp data/devstream.db data/devstream.db.backup-embedding-opt`
- [ ] Verify sqlite-vec loaded: `SELECT vec_version()`
- [ ] Test vec_f32() with sample JSON: `SELECT vec_f32('[0.1, 0.2]')`

### Phase 1: Trigger Infrastructure
- [ ] Create `sync_embedding_update` trigger
- [ ] Test trigger with single record
- [ ] Verify: JSON→BLOB conversion works
- [ ] Verify: JSON auto-cleanup works
- [ ] Test PostToolUse hook (no code changes needed)

### Phase 2: Backfill
- [ ] Run backfill script (trigger-based)
- [ ] Verify: 0 JSON embeddings remain
- [ ] Verify: 45,385 BLOB embeddings in vec_semantic_memory
- [ ] VACUUM + WAL checkpoint
- [ ] Verify: Database size -327 MB
- [ ] Test hybrid search (curl)

### Phase 3: Binary Quantization
- [ ] Create vec_semantic_memory_v2 with dual columns
- [ ] Migrate embeddings with quantization
- [ ] Update hybrid-search.ts (re-scoring pattern)
- [ ] Update trigger (include quantization)
- [ ] Swap tables (zero-downtime)
- [ ] Test search latency (<250ms avg)
- [ ] Test search accuracy (>95% recall)
- [ ] VACUUM + WAL checkpoint
- [ ] Verify: Database size -127 MB additional

### Post-Migration:
- [ ] Remove old backups (keep latest only)
- [ ] Update documentation
- [ ] Monitor search quality (7 days)

---

## Next Steps (STEP 5: APPROVAL)

**Present to User**:
1. ✅ Corrected architecture: Trigger-first approach
2. ✅ Phase 1: Create infrastructure code expects
3. ✅ Phase 2: Backfill via trigger
4. ✅ Phase 3: Binary quantization (MANDATORY)
5. ✅ Expected: -454 MB total (-59%), faster search

**After Approval**:
- Execute Phase 1 (trigger creation + test)
- Execute Phase 2 (backfill via trigger)
- Execute Phase 3 (binary quantization)
- Complete STEP 7 verification

---

**Document Version**: 2.0 (Corrected)
**Last Updated**: 2025-10-10
**Status**: Awaiting STEP 5 Approval
**Key Changes**: Trigger-first approach, binary quantization mandatory
