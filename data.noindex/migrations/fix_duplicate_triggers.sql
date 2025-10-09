-- Migration: Fix Duplicate FTS5 Triggers
-- Issue: sync_insert_memory and fts5_sync_insert both insert into fts_semantic_memory
-- Causa: constraint failed error quando si inserisce in semantic_memory
-- Soluzione: Rimuovere i trigger duplicati fts5_sync_* (keep only sync_* triggers)

-- Drop duplicate FTS5 triggers
DROP TRIGGER IF EXISTS fts5_sync_insert;
DROP TRIGGER IF EXISTS fts5_sync_update;
DROP TRIGGER IF EXISTS fts5_sync_delete;

-- Verify: List remaining triggers
-- Expected: Only sync_insert_memory, sync_update_memory, sync_delete_memory
SELECT 'Remaining triggers:' as status;
SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='semantic_memory';