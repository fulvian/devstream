-- Migration 001: Add Session Tracking Support
-- Memory Vector Enhancement - Phase 6.1
-- Backward-compatible schema changes

-- Add session_id column to semantic_memory table
ALTER TABLE semantic_memory ADD COLUMN session_id TEXT;

-- Create index for performance on session queries
CREATE INDEX IF NOT EXISTS idx_semantic_memory_session_id ON semantic_memory(session_id);

-- Add session tracking to work_sessions table for enhanced monitoring
CREATE TABLE IF NOT EXISTS session_migration_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_version TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    records_affected INTEGER DEFAULT 0,
    status TEXT DEFAULT 'completed'
);

-- Log migration execution
INSERT INTO session_migration_log (migration_version, records_affected)
VALUES ('001_add_session_tracking', (
    SELECT COUNT(*) FROM semantic_memory WHERE session_id IS NULL
));

-- Update existing records with placeholder session_id for backward compatibility
-- This ensures all existing records are queryable while maintaining functionality
UPDATE semantic_memory
SET session_id = 'legacy-session-' || substr(hex(id), 1, 8)
WHERE session_id IS NULL;

-- Verify migration success
SELECT
    'Migration completed' as status,
    COUNT(*) as total_records,
    COUNT(CASE WHEN session_id IS NOT NULL THEN 1 END) as records_with_session_id,
    COUNT(CASE WHEN session_id LIKE 'legacy-session-%' THEN 1 END) as legacy_records_updated
FROM semantic_memory;