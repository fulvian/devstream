-- ============================================================================
-- SISTEMA INTEGRATO TASK MANAGEMENT & MEMORIA CROSS-SESSION
-- Database Schema SQLite con estensioni FTS5 e Vector Search
-- ============================================================================

-- Abilita estensioni SQLite richieste
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

-- ============================================================================
-- 1. TABELLE CORE - TASK MANAGEMENT
-- ============================================================================

-- Piani di intervento (livello più alto)
CREATE TABLE intervention_plans (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    title TEXT NOT NULL,
    description TEXT,
    objectives JSON NOT NULL, -- Array di stringhe: ["obj1", "obj2"]
    technical_specs JSON, -- Specifiche tecniche: {"language": "python", "framework": "fastapi"}
    expected_outcome TEXT NOT NULL,
    status TEXT CHECK(status IN ('draft', 'active', 'completed', 'archived', 'cancelled')) DEFAULT 'draft',
    priority INTEGER DEFAULT 5 CHECK(priority BETWEEN 1 AND 10),
    estimated_hours REAL,
    actual_hours REAL DEFAULT 0,
    tags JSON, -- Array di tag: ["backend", "api", "database"]
    metadata JSON, -- Metadati aggiuntivi flessibili
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Fasi dei piani (raggruppamento logico di micro-task)
CREATE TABLE phases (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    plan_id TEXT NOT NULL REFERENCES intervention_plans(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    sequence_order INTEGER NOT NULL, -- Ordine di esecuzione
    is_parallel BOOLEAN DEFAULT FALSE, -- Può essere eseguita in parallelo
    dependencies JSON, -- Array di phase_id prerequisiti: ["phase_id_1", "phase_id_2"]
    status TEXT CHECK(status IN ('pending', 'active', 'completed', 'blocked', 'skipped')) DEFAULT 'pending',
    estimated_minutes INTEGER,
    actual_minutes INTEGER DEFAULT 0,
    blocking_reason TEXT, -- Motivo del blocco se status = 'blocked'
    completion_criteria TEXT, -- Criteri per considerare la fase completata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Micro-task (unità minima di lavoro, max 10 minuti)
CREATE TABLE micro_tasks (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    phase_id TEXT NOT NULL REFERENCES phases(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    max_duration_minutes INTEGER DEFAULT 10 CHECK(max_duration_minutes <= 10),
    max_context_tokens INTEGER DEFAULT 256000,
    assigned_agent TEXT, -- Nome dell'agente Claude Code responsabile
    task_type TEXT CHECK(task_type IN ('analysis', 'coding', 'documentation', 'testing', 'review', 'research')) DEFAULT 'coding',
    status TEXT CHECK(status IN ('pending', 'active', 'completed', 'failed', 'skipped')) DEFAULT 'pending',
    priority INTEGER DEFAULT 5 CHECK(priority BETWEEN 1 AND 10),

    -- Input/Output tracking
    input_files JSON, -- Array di file path di input: ["src/main.py", "docs/api.md"]
    output_files JSON, -- Array di file path di output
    generated_code TEXT, -- Codice generato durante il task
    documentation TEXT, -- Documentazione generata
    error_log TEXT, -- Log degli errori se status = 'failed'

    -- Execution metadata
    actual_duration_minutes REAL,
    context_tokens_used INTEGER,
    retry_count INTEGER DEFAULT 0,
    parent_task_id TEXT REFERENCES micro_tasks(id), -- Per task derivati/retry

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_retry_at TIMESTAMP
);

-- ============================================================================
-- 2. SISTEMA MEMORIA SEMANTICA
-- ============================================================================

-- Memoria semantica per ogni elemento del sistema
CREATE TABLE semantic_memory (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),

    -- Collegamento ai task
    plan_id TEXT REFERENCES intervention_plans(id) ON DELETE CASCADE,
    phase_id TEXT REFERENCES phases(id) ON DELETE CASCADE,
    task_id TEXT REFERENCES micro_tasks(id) ON DELETE CASCADE,

    -- Contenuto
    content TEXT NOT NULL,
    content_type TEXT CHECK(content_type IN ('code', 'documentation', 'context', 'output', 'error', 'decision', 'learning')) NOT NULL,
    content_format TEXT CHECK(content_format IN ('text', 'markdown', 'code', 'json', 'yaml')) DEFAULT 'text',

    -- Metadati semantici
    keywords JSON, -- Parole chiave estratte: ["python", "fastapi", "database"]
    entities JSON, -- Entità riconosciute: ["User", "Database", "API"]
    sentiment REAL, -- Sentiment analysis (-1 to 1)
    complexity_score INTEGER CHECK(complexity_score BETWEEN 1 AND 10),

    -- Embedding vettoriale (384 dimensioni per embeddinggemma)
    embedding BLOB, -- Vector embedding in formato binario
    embedding_model TEXT DEFAULT 'embeddinggemma',
    embedding_dimension INTEGER DEFAULT 384,

    -- Context tracking
    context_snapshot JSON, -- Snapshot del contesto al momento della creazione
    related_memory_ids JSON, -- Array di memory_id correlati

    -- Metadati di gestione
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP,
    relevance_score REAL DEFAULT 1.0, -- Score di rilevanza (0-1)
    is_archived BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 3. SISTEMA DI RICERCA E INDICIZZAZIONE
-- ============================================================================

-- Full-Text Search con FTS5
CREATE VIRTUAL TABLE memory_fts USING fts5(
    content,
    keywords,
    entities,
    task_id UNINDEXED,
    content_type UNINDEXED,
    content='semantic_memory',
    content_rowid='rowid'
);

-- Trigger per mantenere FTS sincronizzato
CREATE TRIGGER memory_fts_insert AFTER INSERT ON semantic_memory
BEGIN
    INSERT INTO memory_fts(rowid, content, keywords, entities, task_id, content_type)
    VALUES (
        NEW.rowid,
        NEW.content,
        json_extract(NEW.keywords, '$'),
        json_extract(NEW.entities, '$'),
        NEW.task_id,
        NEW.content_type
    );
END;

CREATE TRIGGER memory_fts_update AFTER UPDATE ON semantic_memory
BEGIN
    UPDATE memory_fts SET
        content = NEW.content,
        keywords = json_extract(NEW.keywords, '$'),
        entities = json_extract(NEW.entities, '$'),
        task_id = NEW.task_id,
        content_type = NEW.content_type
    WHERE rowid = NEW.rowid;
END;

CREATE TRIGGER memory_fts_delete AFTER DELETE ON semantic_memory
BEGIN
    DELETE FROM memory_fts WHERE rowid = OLD.rowid;
END;

-- Indice per similarity search vettoriale (usando sqlite-vss o estensione custom)
CREATE VIRTUAL TABLE vector_index USING vss0(
    memory_id TEXT PRIMARY KEY,
    embedding(384) -- 384 dimensioni per embeddinggemma
);

-- ============================================================================
-- 4. CONFIGURAZIONE AGENTI E HOOK
-- ============================================================================

-- Configurazione agenti Claude Code
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    description TEXT,
    capabilities JSON NOT NULL, -- Array di capability: ["code_generation", "review"]
    triggers JSON, -- Array di trigger events: ["new_task", "code_review"]
    config JSON, -- Configurazione specifica agente
    is_active BOOLEAN DEFAULT TRUE,
    success_rate REAL DEFAULT 0.0, -- Tasso di successo (0-1)
    total_tasks INTEGER DEFAULT 0,
    successful_tasks INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Hook system per Claude Code integration
CREATE TABLE hooks (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    name TEXT NOT NULL,
    event_type TEXT NOT NULL, -- 'user_interaction_start', 'task_completion', etc.
    trigger_condition TEXT, -- Condizione per attivare hook (SQL-like)
    action_type TEXT NOT NULL, -- 'force_task_creation', 'save_memory', 'inject_context'
    action_config JSON, -- Configurazione dell'azione
    is_active BOOLEAN DEFAULT TRUE,
    execution_order INTEGER DEFAULT 100, -- Ordine di esecuzione
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Log delle esecuzioni hook
CREATE TABLE hook_executions (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    hook_id TEXT NOT NULL REFERENCES hooks(id),
    event_data JSON, -- Dati dell'evento che ha scatenato l'hook
    execution_result JSON, -- Risultato dell'esecuzione
    status TEXT CHECK(status IN ('success', 'failed', 'skipped')) NOT NULL,
    error_message TEXT,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 5. SESSION MANAGEMENT E CONTEXT TRACKING
-- ============================================================================

-- Sessioni di lavoro
CREATE TABLE work_sessions (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    plan_id TEXT REFERENCES intervention_plans(id),
    user_id TEXT, -- Identificativo utente
    session_name TEXT,
    context_window_size INTEGER DEFAULT 256000,
    tokens_used INTEGER DEFAULT 0,
    status TEXT CHECK(status IN ('active', 'paused', 'completed', 'archived')) DEFAULT 'active',

    -- Context snapshot
    context_summary TEXT,
    active_tasks JSON, -- Array di task_id attivi
    completed_tasks JSON, -- Array di task_id completati nella sessione

    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP
);

-- Context injection log (per debugging e ottimizzazione)
CREATE TABLE context_injections (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    session_id TEXT NOT NULL REFERENCES work_sessions(id),
    task_id TEXT REFERENCES micro_tasks(id),
    injected_memory_ids JSON, -- Array di memory_id iniettati
    injection_trigger TEXT, -- Cosa ha scatenato l'iniezione
    relevance_threshold REAL, -- Soglia di rilevanza usata
    tokens_injected INTEGER,
    effectiveness_score REAL, -- Score di efficacia (feedback)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 6. ANALYTICS E METRICHE
-- ============================================================================

-- Metriche di performance
CREATE TABLE performance_metrics (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    metric_type TEXT NOT NULL, -- 'task_completion_time', 'memory_recall_accuracy', etc.
    entity_type TEXT NOT NULL, -- 'task', 'phase', 'plan', 'agent'
    entity_id TEXT NOT NULL,
    metric_value REAL NOT NULL,
    metric_unit TEXT, -- 'minutes', 'tokens', 'percentage'
    context JSON, -- Contesto aggiuntivo per la metrica
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Learning insights (per miglioramento continuo)
CREATE TABLE learning_insights (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    insight_type TEXT NOT NULL, -- 'pattern', 'best_practice', 'anti_pattern'
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    confidence_score REAL CHECK(confidence_score BETWEEN 0 AND 1),
    supporting_evidence JSON, -- Riferimenti a task/memory che supportano l'insight
    tags JSON,
    is_validated BOOLEAN DEFAULT FALSE,
    validation_feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP
);

-- ============================================================================
-- 7. INDICI PER PERFORMANCE
-- ============================================================================

-- Indici principali per query frequenti
CREATE INDEX idx_plans_status ON intervention_plans(status);
CREATE INDEX idx_plans_created_at ON intervention_plans(created_at);
CREATE INDEX idx_plans_tags ON intervention_plans(tags);

CREATE INDEX idx_phases_plan_status ON phases(plan_id, status);
CREATE INDEX idx_phases_sequence ON phases(plan_id, sequence_order);

CREATE INDEX idx_tasks_phase_status ON micro_tasks(phase_id, status);
CREATE INDEX idx_tasks_agent ON micro_tasks(assigned_agent);
CREATE INDEX idx_tasks_type_status ON micro_tasks(task_type, status);

CREATE INDEX idx_memory_task ON semantic_memory(task_id);
CREATE INDEX idx_memory_type ON semantic_memory(content_type);
CREATE INDEX idx_memory_created ON semantic_memory(created_at);
CREATE INDEX idx_memory_relevance ON semantic_memory(relevance_score);

CREATE INDEX idx_sessions_status ON work_sessions(status);
CREATE INDEX idx_sessions_plan ON work_sessions(plan_id);

-- ============================================================================
-- 8. TRIGGER PER AUTOMAZIONE
-- ============================================================================

-- Auto-update timestamp su modification
CREATE TRIGGER update_plan_timestamp
    AFTER UPDATE ON intervention_plans
BEGIN
    UPDATE intervention_plans
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

-- Auto-calcolo ore effettive quando piano completato
CREATE TRIGGER calculate_actual_hours
    AFTER UPDATE OF status ON intervention_plans
    WHEN NEW.status = 'completed'
BEGIN
    UPDATE intervention_plans
    SET
        actual_hours = (
            SELECT COALESCE(SUM(actual_minutes), 0) / 60.0
            FROM phases p
            JOIN micro_tasks m ON p.id = m.phase_id
            WHERE p.plan_id = NEW.id
        ),
        completed_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

-- Auto-update fase quando tutti micro-task completati
CREATE TRIGGER auto_complete_phase
    AFTER UPDATE OF status ON micro_tasks
    WHEN NEW.status = 'completed'
BEGIN
    UPDATE phases
    SET
        status = 'completed',
        completed_at = CURRENT_TIMESTAMP,
        actual_minutes = (
            SELECT COALESCE(SUM(actual_duration_minutes), 0)
            FROM micro_tasks
            WHERE phase_id = NEW.phase_id
        )
    WHERE id = NEW.phase_id
    AND NOT EXISTS (
        SELECT 1 FROM micro_tasks
        WHERE phase_id = NEW.phase_id
        AND status NOT IN ('completed', 'skipped')
    );
END;

-- ============================================================================
-- 9. VIEWS PER QUERY COMUNI
-- ============================================================================

-- Vista riassuntiva piani
CREATE VIEW plan_summary AS
SELECT
    p.id,
    p.title,
    p.status,
    p.priority,
    COUNT(DISTINCT ph.id) as total_phases,
    COUNT(DISTINCT CASE WHEN ph.status = 'completed' THEN ph.id END) as completed_phases,
    COUNT(DISTINCT m.id) as total_tasks,
    COUNT(DISTINCT CASE WHEN m.status = 'completed' THEN m.id END) as completed_tasks,
    p.estimated_hours,
    p.actual_hours,
    p.created_at,
    p.updated_at
FROM intervention_plans p
LEFT JOIN phases ph ON p.id = ph.plan_id
LEFT JOIN micro_tasks m ON ph.id = m.phase_id
GROUP BY p.id;

-- Vista task attivi con contesto
CREATE VIEW active_tasks_with_context AS
SELECT
    m.id,
    m.title,
    m.description,
    m.status,
    m.assigned_agent,
    p.title as plan_title,
    ph.name as phase_name,
    m.max_duration_minutes,
    m.created_at,
    m.started_at
FROM micro_tasks m
JOIN phases ph ON m.phase_id = ph.id
JOIN intervention_plans p ON ph.plan_id = p.id
WHERE m.status IN ('pending', 'active');

-- Vista memoria semantica con metadati
CREATE VIEW memory_with_context AS
SELECT
    sm.id,
    sm.content,
    sm.content_type,
    sm.keywords,
    sm.entities,
    sm.relevance_score,
    m.title as task_title,
    ph.name as phase_name,
    p.title as plan_title,
    sm.created_at
FROM semantic_memory sm
LEFT JOIN micro_tasks m ON sm.task_id = m.id
LEFT JOIN phases ph ON sm.phase_id = ph.id
LEFT JOIN intervention_plans p ON sm.plan_id = p.id
WHERE sm.is_archived = FALSE;

-- ============================================================================
-- 10. FUNZIONI UTILITY (disponibili con estensioni)
-- ============================================================================

-- Note: Queste funzioni richiedono estensioni SQLite custom o implementazione Python

/*
-- Similarity search function (richiede sqlite-vss)
CREATE FUNCTION similarity_search(query_embedding BLOB, limit INTEGER DEFAULT 5)
RETURNS TABLE(memory_id TEXT, similarity_score REAL)
AS $$
    SELECT memory_id, vss_distance(embedding, query_embedding) as similarity_score
    FROM vector_index
    ORDER BY similarity_score ASC
    LIMIT limit;
$$;

-- Context injection function
CREATE FUNCTION get_relevant_context(task_id TEXT, max_tokens INTEGER DEFAULT 2000)
RETURNS TEXT
AS $$
    -- Implementazione in Python per recuperare contesto rilevante
    -- basato su similarity search e regole euristiche
$$;
*/

-- ============================================================================
-- 11. CONFIGURAZIONE INIZIALE
-- ============================================================================

-- Inserimento agenti di default
INSERT INTO agents (id, name, role, capabilities, triggers, config) VALUES
('architect', 'Project Architect', 'System Designer',
 '["system_design", "architecture_planning", "technology_selection"]',
 '["new_plan", "architecture_decision"]',
 '{"max_context_tokens": 256000, "prefer_patterns": ["microservices", "clean_architecture"]}'),

('coder', 'Code Generator', 'Implementation Specialist',
 '["code_generation", "refactoring", "debugging"]',
 '["implementation_task", "coding_needed"]',
 '{"max_context_tokens": 200000, "languages": ["python", "typescript", "sql"]}'),

('reviewer', 'Code Reviewer', 'Quality Assurance',
 '["code_review", "testing", "quality_check"]',
 '["code_completed", "review_requested"]',
 '{"max_context_tokens": 150000, "focus_areas": ["security", "performance", "maintainability"]}'),

('documenter', 'Documentation Writer', 'Technical Writer',
 '["documentation", "api_docs", "user_guides"]',
 '["documentation_needed", "task_completed"]',
 '{"max_context_tokens": 100000, "formats": ["markdown", "restructured_text"]}');

-- Hook di default per task-forced workflow
INSERT INTO hooks (name, event_type, trigger_condition, action_type, action_config) VALUES
('Force Task Creation', 'user_interaction_start', 'true', 'force_task_creation',
 '{"require_plan": true, "max_interaction_without_task": 0}'),

('Auto Save Task Output', 'micro_task_completion', 'true', 'save_memory',
 '{"include_code": true, "include_context": true, "generate_embeddings": true}'),

('Context Injection', 'task_start', 'true', 'inject_context',
 '{"max_tokens": 2000, "relevance_threshold": 0.7, "include_best_practices": true}');

-- Schema version tracking
CREATE TABLE schema_version (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_version (version, description) VALUES
('1.0.0', 'Initial schema per Sistema Integrato Task Management & Memoria Cross-Session');

-- ============================================================================
-- FINE SCHEMA
-- ============================================================================