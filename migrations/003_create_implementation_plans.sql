-- Migration: Create implementation_plans table
-- Version: 003
-- Date: 2025-10-09
-- Description: Implementation plans storage for DevStream Protocol v2.2.0
--              Supports model-specific templates (GLM-4.6, Sonnet 4.5) and dual storage pattern

-- Create implementation_plans table
CREATE TABLE IF NOT EXISTS implementation_plans (
    -- Primary key
    id TEXT PRIMARY KEY,

    -- Foreign key to micro_tasks (1:1 relationship)
    task_id TEXT NOT NULL UNIQUE,

    -- Model type for template selection
    model_type TEXT NOT NULL CHECK(model_type IN ('glm-4.6', 'sonnet-4.5')),

    -- Plan content (full markdown)
    plan_content TEXT NOT NULL,

    -- File system path to markdown file
    plan_file_path TEXT,

    -- Pre-generated handoff prompt for GLM workflow
    handoff_prompt TEXT,

    -- Metadata (JSON format)
    -- Example: {"complexity": 0.8, "estimated_duration": 480, "context7_libraries": ["fastapi", "sqlalchemy"]}
    metadata JSON,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key constraint
    FOREIGN KEY (task_id) REFERENCES micro_tasks(id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_implementation_plans_task_id ON implementation_plans(task_id);
CREATE INDEX IF NOT EXISTS idx_implementation_plans_model_type ON implementation_plans(model_type);
CREATE INDEX IF NOT EXISTS idx_implementation_plans_created_at ON implementation_plans(created_at DESC);

-- Create trigger for updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_implementation_plans_timestamp
AFTER UPDATE ON implementation_plans
FOR EACH ROW
BEGIN
    UPDATE implementation_plans
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

-- Verify migration
SELECT 'Migration 003 completed successfully. implementation_plans table created.' AS status;
