# Implementation Plan: Vector Schema Upgrade to Best Practice

**Task ID**: vec-schema-upgrade-20251011
**Phase**: Database Optimization & Vector Search Fix
**Priority**: 10/10 (CRITICAL - 86K records missing from vector search)
**Type**: Schema Migration + Code Updates
**Created**: 2025-10-11
**Status**: APPROVED - Ready for Implementation
**Executor**: Sonnet 4.5

---

## Executive Summary

**Problem**: Current `vec_semantic_memory` schema uses 2 columns (minimalist) instead of 4 columns (Context7 best practice). This causes:
- ❌ 86,075 records (99.47%) missing from vector search
- ❌ Slower content_type filtering (no partition key)
- ❌ Unnecessary JOINs with `semantic_memory` table
- ❌ Trigger schema mismatch preventing auto-sync

**Solution**: Migrate to Context7-validated 4-column schema with:
- ✅ PARTITION KEY for 5-10x faster filtered searches
- ✅ AUXILIARY COLUMNS to eliminate JOINs
- ✅ SAFE migration pattern (DROP+CREATE, NO RENAME to avoid Oct 10 failure)
- ✅ Backfill 86K missing records

**Expected Results**:
- ✅ 86,533 records in vector search (from 458)
- ✅ Hybrid search works for 100% of semantic memory
- ✅ 5-10x faster queries with content_type filtering
- ✅ Zero auxiliary table corruption risk

---

## Context7 Research Summary

### Schema Best Practice (Trust Score 9.7/10)

**Pattern from sqlite-vec documentation** (NBC Headlines example):
```sql
CREATE VIRTUAL TABLE vec_articles USING vec0(
  article_id integer primary key,
  published_date text partition key,      -- Sharding per filtering
  headline_embedding float[768]
);
```

**Key Findings**:
1. ✅ **PARTITION KEY** - Internal sharding for filtered searches (5-10x faster)
2. ✅ **AUXILIARY COLUMNS** (`+column_name`) - No indexing, no JOIN needed
3. ✅ **Migration Pattern** - DROP + CREATE (NOT RENAME) to avoid auxiliary table mismatch

### Root Cause Analysis - Oct 10 Failure

**What Went Wrong**:
```sql
CREATE VIRTUAL TABLE vec_semantic_memory_v2 USING vec0(...);
-- ✅ Creates: vec_semantic_memory_v2 + 5 auxiliary tables

ALTER TABLE vec_semantic_memory_v2 RENAME TO vec_semantic_memory;
-- ❌ CATASTROPHIC FAILURE!
-- Renames ONLY main table, auxiliary tables keep old name
-- Result: "no such table: main.vec_semantic_memory_rowids"
-- Database inflated: 421 MB → 1,068 MB
```

**Lesson Learned**: NEVER use `ALTER TABLE RENAME` on virtual tables. Use DROP + CREATE pattern.

---

## Schema Migration

### FROM (Current - 2 Columns)
```sql
CREATE VIRTUAL TABLE vec_semantic_memory USING vec0(
    memory_id TEXT PRIMARY KEY,
    content_embedding FLOAT[768]
);
```

**Limitations**:
- ❌ No partition key → slow filtered searches
- ❌ Requires JOIN with `semantic_memory` for metadata
- ❌ Incompatible with trigger (4-column INSERT)

### TO (Best Practice - 4 Columns)
```sql
CREATE VIRTUAL TABLE vec_semantic_memory USING vec0(
    embedding float[768],                -- Vector column (required)
    content_type TEXT PARTITION KEY,     -- Sharding for content filtering
    +memory_id TEXT,                     -- Auxiliary (no index, evita JOIN)
    +content_preview TEXT                -- Auxiliary (no index, display)
);
```

**Benefits**:
- ✅ **PARTITION KEY** - `content_type` enables internal sharding
- ✅ **AUXILIARY COLUMNS** - `memory_id`, `content_preview` accessible without JOIN
- ✅ **Optimized Queries**: `WHERE embedding MATCH ? AND content_type = 'code'` uses sharding

---

## Code Changes Required

### 1. storage.py (Python - Production Code)

**File**: `src/devstream/memory/storage.py`
**Line**: 136-142

**OLD**:
```python
await conn.execute(text("""
    INSERT OR REPLACE INTO vec_semantic_memory(memory_id, content_embedding)
    VALUES (:memory_id, :embedding)
"""), {
    'memory_id': memory.id,
    'embedding': embedding_binary
})
```

**NEW**:
```python
await conn.execute(text("""
    INSERT INTO vec_semantic_memory(memory_id, embedding, content_type, content_preview)
    VALUES (:memory_id, :embedding, :content_type, :content_preview)
"""), {
    'memory_id': memory.id,
    'embedding': embedding_binary,
    'content_type': memory.content_type,
    'content_preview': memory.content[:200]
})
```

### 2. memory.ts (TypeScript - MCP Server)

**File**: `mcp-devstream-server/src/tools/memory.ts`
**Location**: INSERT statement for vec_semantic_memory

**OLD**:
```typescript
await this.database.execute(`
  INSERT INTO vec_semantic_memory(embedding, content_type, memory_id, content_preview)
  VALUES (?, ?, ?, ?)
`, [embeddingJson, input.content_type, memoryId, input.content.substring(0, 200)]);
```

**NEW**:
```typescript
await this.database.execute(`
  INSERT INTO vec_semantic_memory(memory_id, embedding, content_type, content_preview)
  VALUES (?, ?, ?, ?)
`, [memoryId, embeddingJson, input.content_type, input.content.substring(0, 200)]);
```

### 3. Trigger sync_embedding_update (SQL)

**File**: `.claude/hooks/devstream/migrations/fix_sync_embedding_trigger.sql`

**NEW** (complete rewrite):
```sql
DROP TRIGGER IF EXISTS sync_embedding_update;

CREATE TRIGGER sync_embedding_update
AFTER UPDATE OF embedding ON semantic_memory
WHEN NEW.embedding IS NOT NULL AND NEW.embedding != ''
BEGIN
    -- Step 1: Delete existing entry (prevents duplicates)
    DELETE FROM vec_semantic_memory WHERE memory_id = NEW.id;

    -- Step 2: Insert with 4-column schema
    INSERT INTO vec_semantic_memory(memory_id, embedding, content_type, content_preview)
    VALUES (
        NEW.id,
        vec_f32(NEW.embedding),
        NEW.content_type,
        substr(NEW.content, 1, 200)
    );

    -- Step 3: Cleanup JSON to prevent duplication
    UPDATE semantic_memory SET embedding = NULL WHERE id = NEW.id;
END;
```

---

## Implementation Plan - 10 Micro-Tasks

**Total Time**: ~85 minutes
**Downtime**: ~2 minutes (during migration execution)

### Task 6.1: Pre-Migration Backup (5 min)
```bash
# Full database backup
sqlite3 data/devstream.db ".backup data/devstream.db.backup-schema-upgrade-20251011"

# Backup vec data to temp table
sqlite3 data/devstream.db << EOF
CREATE TABLE vec_backup_20251011 AS
SELECT memory_id, content_embedding FROM vec_semantic_memory;

SELECT 'Backup count:', COUNT(*) FROM vec_backup_20251011;
EOF
```

**Expected Output**: `Backup count: 458`

### Task 6.2: Create Migration Script (10 min)

**File**: `scripts/migrate_vec_schema_to_best_practice.sql`

```sql
-- DevStream Vector Schema Migration
-- Pattern: DROP + CREATE (Context7-validated, NO RENAME)
-- Date: 2025-10-11

BEGIN TRANSACTION;

-- Step 1: Backup data to temporary table
CREATE TEMPORARY TABLE vec_migration_temp AS
SELECT
    vsm.memory_id,
    vsm.content_embedding as embedding,
    COALESCE(sm.content_type, 'context') as content_type,
    substr(COALESCE(sm.content, ''), 1, 200) as content_preview
FROM vec_semantic_memory vsm
LEFT JOIN semantic_memory sm ON sm.id = vsm.memory_id;

-- Step 2: Verify backup count
SELECT 'Backup created:', COUNT(*) FROM vec_migration_temp;

-- Step 3: DROP old table (removes all 5 auxiliary tables automatically)
DROP TABLE vec_semantic_memory;

-- Step 4: CREATE new table with best practice schema
CREATE VIRTUAL TABLE vec_semantic_memory USING vec0(
    embedding float[768],
    content_type TEXT PARTITION KEY,
    +memory_id TEXT,
    +content_preview TEXT
);

-- Step 5: Restore data with new schema
INSERT INTO vec_semantic_memory(memory_id, embedding, content_type, content_preview)
SELECT memory_id, embedding, content_type, content_preview
FROM vec_migration_temp;

-- Step 6: Verify migration success
SELECT 'Post-migration count:', COUNT(*) FROM vec_semantic_memory;

-- Step 7: Cleanup temporary table
DROP TABLE vec_migration_temp;

COMMIT;

-- Step 8: Final verification
SELECT 'Auxiliary tables:', COUNT(*)
FROM sqlite_master
WHERE type='table' AND name LIKE 'vec_semantic_memory%';

SELECT 'Partition key test:', COUNT(*)
FROM vec_semantic_memory
WHERE content_type = 'code';
```

### Task 6.3: Update storage.py (10 min)

**Action**: Apply code changes from section "Code Changes Required #1"

**Verification**:
```python
# Test with single record
async def test_new_schema():
    memory = MemoryEntry(
        id='test-schema-upgrade',
        content='Test content for schema upgrade',
        content_type='code',
        embedding=[0.1] * 768
    )
    await storage.store_memory(memory)

    # Verify in vec table
    result = await conn.execute(text("""
        SELECT memory_id, content_type, content_preview
        FROM vec_semantic_memory
        WHERE memory_id = 'test-schema-upgrade'
    """))
    assert result is not None
```

### Task 6.4: Update memory.ts (10 min)

**Action**: Apply code changes from section "Code Changes Required #2"

**Verification**:
```bash
# Compile TypeScript
cd mcp-devstream-server
npm run build
# Expected: No compilation errors
```

### Task 6.5: Update Trigger (10 min)

**Action**: Apply trigger SQL from section "Code Changes Required #3"

```bash
sqlite3 data/devstream.db < .claude/hooks/devstream/migrations/fix_sync_embedding_trigger.sql

# Verify trigger exists
sqlite3 data/devstream.db "SELECT name FROM sqlite_master WHERE type='trigger' AND name='sync_embedding_update';"
# Expected: sync_embedding_update
```

### Task 6.6: Execute Migration (5 min)

```bash
# Verify sqlite-vec extension loaded
sqlite3 data/devstream.db "SELECT vec_version();"
# Expected: v0.1.6

# Run migration script
sqlite3 data/devstream.db < scripts/migrate_vec_schema_to_best_practice.sql
```

**Expected Output**:
```
Backup created: 458
Post-migration count: 458
Auxiliary tables: 5
Partition key test: <count of code-type records>
```

### Task 6.7: Backfill 86K Missing Records (15 min)

```bash
# Update backfill script to use new 4-column schema
.devstream/bin/python .claude/hooks/devstream/memory/backfill_embeddings.py \
  --batch-size 1000 \
  --db-path data/devstream.db

# Expected output:
# Total records: 86,533
# Processed batches: 87
# Updated records: 86,075
# Synced to vec0: 86,075
# Success rate: 100%
```

### Task 6.8: Verify Schema & Data (5 min)

```bash
# Check schema
sqlite3 data/devstream.db ".schema vec_semantic_memory"

# Check auxiliary tables (should be 5)
sqlite3 data/devstream.db "
  SELECT name FROM sqlite_master
  WHERE type='table' AND name LIKE 'vec_semantic_memory%';
"

# Check record count (should be 86,533)
sqlite3 data/devstream.db "SELECT COUNT(*) FROM vec_semantic_memory;"

# Test partition key query
sqlite3 data/devstream.db "
  SELECT COUNT(*) FROM vec_semantic_memory
  WHERE content_type = 'code';
"

# Test auxiliary columns (no JOIN needed)
sqlite3 data/devstream.db "
  SELECT memory_id, content_preview
  FROM vec_semantic_memory
  LIMIT 5;
"
```

### Task 6.9: Update Documentation (10 min)

**Files to Update**:
1. `schema/schema.sql` - Update vec_semantic_memory schema
2. `docs/api/database-schema.md` - Document 4-column schema
3. `CHANGELOG.md` - Add migration entry

### Task 6.10: VACUUM & Checkpoint (5 min)

```bash
sqlite3 data/devstream.db << EOF
VACUUM;
PRAGMA wal_checkpoint(TRUNCATE);
PRAGMA integrity_check;
EOF

# Check database size
ls -lh data/devstream.db
# Expected: ~420 MB (no inflation)
```

---

## Rollback Strategy

### Rollback Point 1: Before Migration (if Task 6.6 fails)
```bash
# Restore from full backup
cp data/devstream.db.backup-schema-upgrade-20251011 data/devstream.db
```

### Rollback Point 2: After Migration, Before Backfill (if Task 6.7 fails)
```sql
-- Restore old 2-column schema
DROP TABLE vec_semantic_memory;

CREATE VIRTUAL TABLE vec_semantic_memory USING vec0(
    memory_id TEXT PRIMARY KEY,
    content_embedding FLOAT[768]
);

-- Restore data from backup table
INSERT INTO vec_semantic_memory(memory_id, content_embedding)
SELECT memory_id, content_embedding FROM vec_backup_20251011;

DROP TABLE vec_backup_20251011;
```

### Rollback Point 3: Complete Failure
```bash
# Nuclear option: restore full database
mv data/devstream.db data/devstream.db.FAILED-20251011
cp data/devstream.db.backup-schema-upgrade-20251011 data/devstream.db

# Revert code changes
git checkout src/devstream/memory/storage.py
git checkout mcp-devstream-server/src/tools/memory.ts
git checkout .claude/hooks/devstream/migrations/fix_sync_embedding_trigger.sql
```

---

## Acceptance Criteria (STEP 7)

| # | Criterion | Test Command | Expected Result |
|---|-----------|--------------|-----------------|
| 1 | Schema 4 colonne | `sqlite3 data/devstream.db ".schema vec_semantic_memory"` | 4 columns: embedding, content_type, memory_id, content_preview |
| 2 | 5 auxiliary tables | `sqlite3 data/devstream.db "SELECT name FROM sqlite_master WHERE name LIKE 'vec_%';"` | 5 tables |
| 3 | 86K+ records | `sqlite3 data/devstream.db "SELECT COUNT(*) FROM vec_semantic_memory;"` | ≥86,533 |
| 4 | Partition key works | `EXPLAIN QUERY PLAN SELECT ... WHERE content_type='code';` | Uses partition index |
| 5 | Auxiliary columns | `SELECT memory_id, content_preview FROM vec_semantic_memory LIMIT 1;` | Returns data without JOIN |
| 6 | Trigger auto-sync | `UPDATE semantic_memory SET embedding='[...]'; SELECT COUNT(*) FROM vec_semantic_memory WHERE memory_id='test';` | 1 |
| 7 | Hybrid search works | MCP `devstream_search_memory` call | Returns results |
| 8 | No database inflation | `ls -lh data/devstream.db` | ~420 MB |

---

## Testing Strategy

### Pre-Migration Tests
```bash
# Test 1: Current record count
sqlite3 data/devstream.db "SELECT COUNT(*) FROM vec_semantic_memory;"
# Expect: 458

# Test 2: Backup integrity
sqlite3 data/devstream.db.backup-schema-upgrade-20251011 "PRAGMA integrity_check;"
# Expect: ok

# Test 3: Extension loaded
sqlite3 data/devstream.db "SELECT vec_version();"
# Expect: v0.1.6
```

### Post-Migration Tests
```bash
# Test 4: Schema verification
sqlite3 data/devstream.db ".schema vec_semantic_memory"

# Test 5: Auxiliary tables
sqlite3 data/devstream.db "SELECT COUNT(*) FROM sqlite_master WHERE name LIKE 'vec_semantic_memory%';"
# Expect: 5

# Test 6: Record count after backfill
sqlite3 data/devstream.db "SELECT COUNT(*) FROM vec_semantic_memory;"
# Expect: 86,533

# Test 7: Partition key filtering
sqlite3 data/devstream.db "SELECT COUNT(*) FROM vec_semantic_memory WHERE content_type='code';"
# Expect: >0

# Test 8: Auxiliary column access (no JOIN)
sqlite3 data/devstream.db "SELECT memory_id, content_preview FROM vec_semantic_memory LIMIT 1;"
# Expect: Returns 2 columns
```

### End-to-End Tests
```bash
# Test 9: Trigger functionality
sqlite3 data/devstream.db << EOF
INSERT INTO semantic_memory(id, content, content_type, embedding)
VALUES ('test-e2e-trigger', 'Test content', 'code', '[]');

UPDATE semantic_memory
SET embedding = (SELECT '[' || GROUP_CONCAT(CAST(0.1 AS TEXT)) || ']' FROM (SELECT 1 UNION ALL SELECT 1 LIMIT 768))
WHERE id = 'test-e2e-trigger';

SELECT 'Trigger test:', COUNT(*) FROM vec_semantic_memory WHERE memory_id='test-e2e-trigger';
EOF
# Expect: Trigger test: 1

# Test 10: Hybrid search via MCP
# (Execute in separate session after migration)
curl -X POST http://localhost:3000 -d '{
  "query": "vector search optimization",
  "limit": 10
}'
# Expect: JSON response with results
```

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Migration script fails | LOW | HIGH | Pre-test on backup copy, automatic rollback in transaction |
| Auxiliary table mismatch | VERY LOW | CRITICAL | Use DROP+CREATE (NOT RENAME), verified from Context7 |
| Data loss during migration | LOW | CRITICAL | Full backup before start, verify counts after each step |
| Backfill timeout | MEDIUM | MEDIUM | Batch size 1000, script resumable |
| Production downtime >5min | LOW | MEDIUM | Execute during low-traffic window |
| storage.py breaks queries | MEDIUM | HIGH | Test with single record before backfill |
| TypeScript compilation errors | LOW | MEDIUM | npm run build verification before deployment |

---

## Timeline

**Preparation**: 15 minutes (Tasks 6.1-6.2)
**Code Updates**: 30 minutes (Tasks 6.3-6.5)
**Migration Execution**: 10 minutes (Tasks 6.6)
**Backfill**: 15 minutes (Task 6.7)
**Verification**: 15 minutes (Tasks 6.8-6.10)

**TOTAL**: ~85 minutes
**Downtime**: ~2 minutes (during Task 6.6 execution)

---

## Success Metrics

**Before Migration**:
- Vec records: 458
- Hybrid search coverage: 0.53%
- Queries requiring JOIN: 100%

**After Migration**:
- Vec records: 86,533 ✅
- Hybrid search coverage: 100% ✅
- Queries requiring JOIN: 0% ✅
- Partition key queries: 5-10x faster ✅

---

**Plan Status**: ✅ APPROVED
**Ready for Execution**: YES
**Executor**: Sonnet 4.5
**Estimated Completion**: 2025-10-11 (85 minutes)

**Next Step**: STEP 6 - IMPLEMENTATION (execute micro-tasks 6.1-6.10)
