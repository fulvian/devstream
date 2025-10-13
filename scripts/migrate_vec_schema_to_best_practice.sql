-- DevStream Vector Schema Migration
-- Pattern: DROP + CREATE (Context7-validated, NO RENAME)
-- Date: 2025-10-11
-- Task: vec-schema-upgrade-20251011
--
-- Context7 Research:
--   - sqlite-vec v0.1.6 best practice: PARTITION KEY + AUXILIARY COLUMNS
--   - Safe migration: DROP TABLE (removes all 5 auxiliary tables)
--   - NEVER use ALTER TABLE RENAME (causes auxiliary table mismatch)
--
-- Schema Change:
--   FROM: vec_semantic_memory(memory_id, content_embedding) - 2 columns
--   TO:   vec_semantic_memory(embedding, content_type, +memory_id, +content_preview) - 4 columns
--
-- Benefits:
--   - 5-10x faster filtered searches with PARTITION KEY
--   - Zero JOINs needed with AUXILIARY COLUMNS
--   - Fixes trigger schema mismatch (86K missing records)

BEGIN TRANSACTION;

-- Step 1: Backup data to temporary table
-- Combines vec_semantic_memory with semantic_memory for complete metadata
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
-- Context7 Pattern: Safe cleanup of vec0 virtual table
DROP TABLE vec_semantic_memory;

-- Step 4: CREATE new table with best practice schema
-- PARTITION KEY: content_type for internal sharding (5-10x faster filtering)
-- AUXILIARY COLUMNS: +memory_id, +content_preview (no indexing, no JOIN needed)
CREATE VIRTUAL TABLE vec_semantic_memory USING vec0(
    embedding float[768],
    content_type TEXT PARTITION KEY,
    +memory_id TEXT,
    +content_preview TEXT
);

-- Step 5: Restore data with new schema
-- Column order MUST match CREATE TABLE definition
INSERT INTO vec_semantic_memory(memory_id, embedding, content_type, content_preview)
SELECT memory_id, embedding, content_type, content_preview
FROM vec_migration_temp;

-- Step 6: Verify migration success
SELECT 'Post-migration count:', COUNT(*) FROM vec_semantic_memory;

-- Step 7: Cleanup temporary table
DROP TABLE vec_migration_temp;

COMMIT;

-- Step 8: Final verification (outside transaction)
SELECT 'Auxiliary tables:', COUNT(*)
FROM sqlite_master
WHERE type='table' AND name LIKE 'vec_semantic_memory%';

SELECT 'Partition key test:', COUNT(*)
FROM vec_semantic_memory
WHERE content_type = 'code';

-- Expected Output:
--   Backup created: 458
--   Post-migration count: 458
--   Auxiliary tables: 5
--   Partition key test: <count of code-type records>
