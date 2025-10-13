-- DevStream Trigger Fix V2: sync_embedding_insert_and_update
-- Context7 Best Practice: Trigger on BOTH INSERT and UPDATE
-- Date: 2025-10-11
-- Task: vec-schema-upgrade-20251011
--
-- This trigger automatically syncs embeddings from semantic_memory (JSON storage)
-- to vec_semantic_memory (BLOB format for vector search) when embeddings are inserted or updated.
--
-- Schema Alignment:
--   vec_semantic_memory columns: embedding, content_type, +memory_id, +content_preview
--   Column order for INSERT: memory_id, embedding, content_type, content_preview
--
-- Context7 Pattern:
--   - vec_f32() converts JSON array to float32 BLOB
--   - DELETE before INSERT prevents duplicates
--   - UPDATE embedding=NULL prevents JSON duplication (saves ~327 MB)
--
-- V2 Changes:
--   - Added INSERT trigger (was only UPDATE before)
--   - Ensures real-time sync for all new records

-- Drop old triggers
DROP TRIGGER IF EXISTS sync_embedding_update;
DROP TRIGGER IF EXISTS sync_embedding_insert;

-- Trigger for INSERT (new records with embedding)
CREATE TRIGGER sync_embedding_insert
AFTER INSERT ON semantic_memory
WHEN NEW.embedding IS NOT NULL AND NEW.embedding != ''
BEGIN
    -- Step 1: Insert into vec0 with 4-column best practice schema
    -- Column order MUST match: memory_id, embedding, content_type, content_preview
    INSERT INTO vec_semantic_memory(memory_id, embedding, content_type, content_preview)
    VALUES (
        NEW.id,
        vec_f32(NEW.embedding),
        NEW.content_type,
        substr(NEW.content, 1, 200)
    );

    -- Step 2: Cleanup JSON to prevent duplication (Context7 optimization)
    -- This saves ~327 MB by removing redundant JSON after BLOB conversion
    UPDATE semantic_memory SET embedding = NULL WHERE id = NEW.id;
END;

-- Trigger for UPDATE (backfill scenario)
CREATE TRIGGER sync_embedding_update
AFTER UPDATE OF embedding ON semantic_memory
WHEN NEW.embedding IS NOT NULL AND NEW.embedding != ''
BEGIN
    -- Step 1: Delete existing entry (prevents duplicates during backfill)
    DELETE FROM vec_semantic_memory WHERE memory_id = NEW.id;

    -- Step 2: Insert with 4-column best practice schema
    -- Column order MUST match: memory_id, embedding, content_type, content_preview
    INSERT INTO vec_semantic_memory(memory_id, embedding, content_type, content_preview)
    VALUES (
        NEW.id,
        vec_f32(NEW.embedding),
        NEW.content_type,
        substr(NEW.content, 1, 200)
    );

    -- Step 3: Cleanup JSON to prevent duplication (Context7 optimization)
    -- This saves ~327 MB by removing redundant JSON after BLOB conversion
    UPDATE semantic_memory SET embedding = NULL WHERE id = NEW.id;
END;
