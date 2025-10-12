-- Migration 005: Add missing session columns for PostToolUse hook compatibility
-- Purpose: Fix missing active_files column that PostToolUse hook expects
-- Risk: LOW - only adds new columns, no existing data affected

-- Add active_files column that PostToolUse hook expects
ALTER TABLE work_sessions ADD COLUMN active_files JSON;

-- Add any other potentially missing columns based on schema reference
-- (Checking if these are needed based on PostToolUse hook code review)

-- Update indexes for new columns
CREATE INDEX IF NOT EXISTS idx_work_sessions_active_files ON work_sessions(active_files);

-- Log migration completion
INSERT OR IGNORE INTO schema_version (version, description)
VALUES ('2.1.2', 'Add missing active_files column for PostToolUse hook compatibility');

-- Verify migration success
SELECT
    'Migration 005 completed' as status,
    COUNT(*) as total_sessions,
    COUNT(CASE WHEN active_files IS NOT NULL THEN 1 END) as sessions_with_active_files
FROM work_sessions;