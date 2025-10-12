-- Migration 004: Restore work_sessions table for MCP session tracking
-- Purpose: Fix MCP 40-second timeouts by restoring minimal session tracking
-- Risk: LOW - only creates new table, no existing data affected
-- Date: 2025-10-12
-- Protocol: DevStream v2.2.0 - Option A (Partial Restore)

-- Create work_sessions table to support PostToolUse hook session tracking
CREATE TABLE IF NOT EXISTS work_sessions (
    id VARCHAR(32) NOT NULL PRIMARY KEY,
    plan_id VARCHAR(32),
    user_id VARCHAR(100),
    session_name VARCHAR(200),
    context_window_size INTEGER,
    tokens_used INTEGER,
    status VARCHAR(20) CHECK (status IN ('active', 'paused', 'completed', 'archived')),
    context_summary TEXT,
    active_tasks JSON,
    completed_tasks JSON,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    FOREIGN KEY(plan_id) REFERENCES intervention_plans(id)
);

-- Indexes for performance (critical for PostToolUse hook queries)
CREATE INDEX IF NOT EXISTS idx_work_sessions_plan_id ON work_sessions(plan_id);
CREATE INDEX IF NOT EXISTS idx_work_sessions_status ON work_sessions(status);
CREATE INDEX IF NOT EXISTS idx_work_sessions_started_at ON work_sessions(started_at DESC);

-- Create an active session for immediate use by PostToolUse hook
INSERT INTO work_sessions (
    id,
    user_id,
    session_name,
    status,
    started_at,
    last_activity_at,
    context_summary
) VALUES (
    'sess-mcp-restore-' || substr(hex(randomblob(16)), 1, 8),
    'claude-code',
    'MCP Session Restore - ' || datetime('now'),
    'active',
    datetime('now'),
    datetime('now'),
    'Session created during MCP session tracking restore (Option A)'
);

-- Log migration completion for tracking
INSERT OR IGNORE INTO schema_version (version, description)
VALUES ('2.1.1', 'Restore work_sessions table for MCP session tracking - Option A Partial Restore');

-- Verify migration success
SELECT
    'Migration 004 completed' as status,
    COUNT(*) as total_sessions,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_sessions
FROM work_sessions;