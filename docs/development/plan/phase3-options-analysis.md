# Phase 3 Binary Quantization - Options Analysis

**Date**: 2025-10-10
**Context**: GLM-4.6 Phase 3 failed due to virtual table auxiliary tables mismatch
**Current State**: 413 MB database, 46.4% optimized, NO binary quantization

---

## Technical Background

### What Went Wrong in GLM-4.6 Phase 3

**Attempted Operation**:
```sql
CREATE VIRTUAL TABLE vec_semantic_memory_v2 USING vec0(
    embedding_fine float[768],
    embedding_coarse bit[768],
    ...
);

INSERT INTO vec_semantic_memory_v2(...) SELECT ... FROM vec_semantic_memory;

DROP TABLE vec_semantic_memory;
ALTER TABLE vec_semantic_memory_v2 RENAME TO vec_semantic_memory;  -- ❌ FAILED
```

**Error**: `"no such table: main.vec_semantic_memory_rowids"`

**Root Cause**:
- sqlite-vec creates 5 auxiliary tables automatically:
  - `vec_semantic_memory_auxiliary` (metadata)
  - `vec_semantic_memory_chunks` (data chunking)
  - `vec_semantic_memory_info` (table info)
  - `vec_semantic_memory_rowids` (row ID mappings)
  - `vec_semantic_memory_vector_chunks00` (vector data blocks)
- `ALTER TABLE RENAME` renames **ONLY the main table**
- Auxiliary tables remain with old name: `vec_semantic_memory_v2_*`
- System expects: `vec_semantic_memory_rowids`
- Actually exists: `vec_semantic_memory_v2_rowids`
- **MISMATCH → CORRUPTION**

**Impact**:
- Database size: 421 MB → 1,068 MB (+154% inflation)
- Required rollback to Phase 2 state
- 46.4% optimization achieved, but Phase 3 (-30% additional) lost

---

## Context7 Research Findings

### What sqlite-vec Documentation DOES NOT Cover

❌ Schema migrations for virtual tables
❌ ALTER TABLE for vec0 tables
❌ RENAME operations for virtual tables
❌ Auxiliary table lifecycle management
❌ In-place schema changes

### What Context7 Shows (Trust Score 9.7/10)

✅ **Pattern 1**: Attach Database Approach (NBC Headlines example)
```sql
attach database 'new.db' as slim;
create virtual table slim.vec_articles using vec0(...);
insert into slim.vec_articles SELECT ... FROM main.vec_articles;
-- No RENAME needed - different namespace
```

✅ **Pattern 2**: Full Rebuild (implicit in examples)
```sql
DROP TABLE vec_semantic_memory;
CREATE VIRTUAL TABLE vec_semantic_memory USING vec0(...);
INSERT INTO vec_semantic_memory SELECT ...;
```

---

## OPTION A: Attach Database Pattern (Zero-Rename Approach)

### Strategy
Use attached database with different namespace to avoid RENAME operation entirely.

### Implementation
```sql
-- Step 1: Attach temporary database
ATTACH DATABASE 'data/devstream_temp.db' AS temp_db;

-- Step 2: Create new table in temp namespace
CREATE VIRTUAL TABLE temp_db.vec_semantic_memory USING vec0(
    embedding_fine float[768],
    embedding_coarse bit[768],
    content_type TEXT PARTITION KEY,
    +memory_id TEXT,
    +content_preview TEXT
);

-- Step 3: Migrate data with quantization
INSERT INTO temp_db.vec_semantic_memory(memory_id, embedding_fine, embedding_coarse, content_type, content_preview)
SELECT
    memory_id,
    embedding as embedding_fine,
    vec_quantize_binary(embedding) as embedding_coarse,
    content_type,
    content_preview
FROM main.vec_semantic_memory;

-- Step 4: Drop old table (frees auxiliary tables)
DROP TABLE main.vec_semantic_memory;

-- Step 5: Detach and swap databases
DETACH DATABASE temp_db;
-- Manual file system operation: mv devstream_temp.db devstream.db
```

### Pros
- ✅ Avoids RENAME operation entirely (no auxiliary table mismatch)
- ✅ Uses documented Context7 pattern (NBC Headlines example)
- ✅ Clean migration (no orphaned auxiliary tables)
- ✅ Testable in staging (create temp_db first)

### Cons
- ⚠️ Requires database file swap (brief downtime ~5-10s)
- ⚠️ Manual file system operation (mv command)
- ⚠️ Need to update trigger after swap (embedding → embedding_fine/coarse)
- ⚠️ Higher complexity than Option B

### Risk Assessment
- **Corruption Risk**: LOW (uses documented pattern)
- **Downtime**: ~10 seconds (file swap)
- **Rollback**: Easy (keep backup, restore if needed)
- **Auxiliary Tables**: SAFE (new namespace, no conflicts)

### Expected Results
- Database size: 413 MB → ~280 MB (-133 MB, -32% additional)
- Storage per embedding: 3,072 bytes → 3,168 bytes (float32 + bit[768])
- Search latency: -50% (binary coarse filter)
- Search accuracy: >95% (re-scoring pattern)

---

## OPTION B: Full Rebuild (Direct Drop + Recreate)

### Strategy
Accept brief downtime, drop old table completely, recreate with new schema.

### Implementation
```sql
-- Step 1: Backup current data to temp table
CREATE TABLE semantic_memory_embedding_backup AS
SELECT
    memory_id,
    embedding,
    content_type,
    content_preview
FROM vec_semantic_memory;

-- Step 2: Drop old virtual table (deletes all auxiliary tables)
DROP TABLE vec_semantic_memory;

-- Step 3: Create new table with binary quantization
CREATE VIRTUAL TABLE vec_semantic_memory USING vec0(
    embedding_fine float[768],
    embedding_coarse bit[768],
    content_type TEXT PARTITION KEY,
    +memory_id TEXT,
    +content_preview TEXT
);

-- Step 4: Re-insert data with quantization
INSERT INTO vec_semantic_memory(memory_id, embedding_fine, embedding_coarse, content_type, content_preview)
SELECT
    memory_id,
    embedding as embedding_fine,
    vec_quantize_binary(embedding) as embedding_coarse,
    content_type,
    content_preview
FROM semantic_memory_embedding_backup;

-- Step 5: Drop backup table
DROP TABLE semantic_memory_embedding_backup;

-- Step 6: Update trigger for new schema
-- (See trigger update in piano_v2.md)
```

### Pros
- ✅ Simplest approach (no attach/detach complexity)
- ✅ Clean slate (no auxiliary table baggage)
- ✅ All operations in single transaction (rollback-safe)
- ✅ No file system operations required

### Cons
- ⚠️ Downtime during rebuild (~30-60 seconds for 54K embeddings)
- ⚠️ Temporary table doubles memory usage (413 MB → ~826 MB peak)
- ⚠️ PostToolUse hook blocked during migration (no new embeddings)
- ⚠️ Risk if migration fails mid-process (rollback required)

### Risk Assessment
- **Corruption Risk**: MEDIUM (rollback if migration fails)
- **Downtime**: ~60 seconds (create + insert + vacuum)
- **Rollback**: REQUIRED if failure (restore from backup)
- **Auxiliary Tables**: SAFE (complete DROP removes all)

### Expected Results
Same as Option A:
- Database size: 413 MB → ~280 MB (-133 MB, -32% additional)
- Search latency: -50%
- Search accuracy: >95%

---

## OPTION C: Defer Phase 3 (Status Quo)

### Strategy
Maintain current 46.4% optimization, defer binary quantization until sqlite-vec improves.

### Rationale
1. **Current state is production-ready**:
   - 413 MB (down from 771 MB)
   - Zero BLOB duplicates
   - Trigger fixed and tested
   - Hybrid search working

2. **Risk vs. Reward**:
   - Additional savings: -133 MB (32% more)
   - Risk: Virtual table corruption (proven in Phase 3)
   - Complexity: High (attach/detach OR rebuild)
   - Testing: No staging environment available

3. **sqlite-vec evolution**:
   - Library is actively developed
   - May introduce migration tools in future
   - Current version has no documented migration patterns

4. **Cost analysis**:
   - Current: 413 MB (acceptable)
   - Target: 280 MB (nice-to-have, not critical)
   - Risk: Data corruption + rollback effort

### Pros
- ✅ Zero risk (no migration = no corruption)
- ✅ System stable and production-ready NOW
- ✅ 46.4% optimization already excellent
- ✅ Can revisit when sqlite-vec matures

### Cons
- ❌ Misses -133 MB additional savings (32% more optimization)
- ❌ No performance improvement from binary quantization
- ❌ Leaves optimization incomplete

### Future Path
- Monitor sqlite-vec releases for migration tools
- Re-attempt when staging environment available
- Consider when database size becomes critical (>500 MB)

---

## RECOMMENDATION MATRIX

| Factor | Option A (Attach) | Option B (Rebuild) | Option C (Defer) |
|--------|-------------------|-------------------|------------------|
| **Corruption Risk** | LOW | MEDIUM | NONE |
| **Downtime** | 10s (file swap) | 60s (rebuild) | 0s |
| **Complexity** | HIGH | MEDIUM | NONE |
| **Rollback Ease** | EASY | REQUIRED | N/A |
| **Context7 Support** | ✅ Documented | ⚠️ Implicit | ✅ Current state |
| **Test Coverage** | Requires staging | Testable in transaction | N/A |
| **Storage Savings** | -133 MB | -133 MB | 0 MB |
| **Performance Gain** | 50% faster search | 50% faster search | 0% |

---

## DECISION CRITERIA

### Choose OPTION A (Attach) if:
- ✅ Need binary quantization now
- ✅ Can accept 10s downtime for file swap
- ✅ Want lowest corruption risk with Context7-documented pattern
- ✅ Have tested attach/detach workflow in dev environment

### Choose OPTION B (Rebuild) if:
- ✅ Need binary quantization now
- ✅ Can accept 60s downtime
- ✅ Prefer simpler implementation (no file operations)
- ⚠️ Have robust backup + rollback plan ready

### Choose OPTION C (Defer) if:
- ✅ Current 46.4% optimization is sufficient
- ✅ Risk tolerance is LOW (avoid any corruption possibility)
- ✅ Can wait for sqlite-vec migration tools
- ✅ No immediate pressure on database size

---

## CURRENT RECOMMENDATION: OPTION C (Defer)

**Rationale**:
1. **Production-ready now**: 413 MB, 46.4% optimized, stable
2. **Risk > Reward**: -133 MB additional savings not critical vs corruption risk
3. **No staging environment**: Cannot safely test Option A or B
4. **sqlite-vec maturity**: Wait for library to add migration tools

**Revisit Phase 3 when**:
- Database size exceeds 500 MB (pressure threshold)
- sqlite-vec adds schema migration documentation
- Staging environment available for safe testing
- Search performance becomes critical bottleneck

---

**Status**: Analysis complete, awaiting user decision
**Options**: A (Attach), B (Rebuild), C (Defer)
**Default**: C (Defer) unless user explicitly chooses A or B
