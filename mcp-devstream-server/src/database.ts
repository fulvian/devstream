/**
 * DevStream Database Connection Layer
 *
 * SQLite database connection and query utilities for DevStream MCP server.
 * Uses better-sqlite3 for synchronous API and sqlite-vec for vector search.
 *
 * Context7-compliant implementation using official sqlite-vec npm package.
 *
 * FASE 5.1 - Worker Pool Feature Flag (Protocol v2.2.0):
 * - Feature flag: DEVSTREAM_WORKER_POOL_ENABLED (true/false)
 * - When true: Uses DatabasePool (non-blocking, 0ms event loop blocking)
 * - When false: Uses DatabaseDirect (legacy synchronous, 3250ms blocking)
 * - Rollback: Set flag to false and restart to restore synchronous behavior
 */

import Database from 'better-sqlite3';
import * as sqliteVec from 'sqlite-vec';
import { DatabasePool, getDatabasePool } from './core/database-pool';

/**
 * Database connection wrapper with sync/async query support
 *
 * Migration Status (FASE 2.1 - Protocol v2.2.0):
 * - ✅ query() → DatabasePool (non-blocking) OR direct (synchronous) based on flag
 * - ✅ queryOne() → DatabasePool (non-blocking) OR direct (synchronous) based on flag
 * - ✅ execute() → DatabasePool (non-blocking) OR direct (synchronous) based on flag
 * - ✅ initialize() → keeps direct connection for sqlite-vec loading
 * - ✅ Backward compatible API (async methods preserved)
 *
 * FASE 5.1 Feature Flag:
 * - DEVSTREAM_WORKER_POOL_ENABLED=true → Use DatabasePool (non-blocking)
 * - DEVSTREAM_WORKER_POOL_ENABLED=false → Use direct better-sqlite3 (synchronous)
 *
 * Context7 pattern: Use better-sqlite3 for reliable extension loading
 * Piscina pattern: Use worker pool for all query operations (when enabled)
 */
export class DevStreamDatabase {
  private db: Database.Database | null = null;
  private dbPath: string;
  private vectorSearchAvailable: boolean = false;
  private pool: DatabasePool | null = null;
  private workerPoolEnabled: boolean;

  constructor(dbPath: string) {
    this.dbPath = dbPath;
    // FASE 5.1: Check feature flag for worker pool
    this.workerPoolEnabled = process.env.DEVSTREAM_WORKER_POOL_ENABLED === 'true';
  }

  /**
   * Initialize database connection and load sqlite-vec extension
   *
   * FASE 2.1 Migration:
   * - Keeps direct connection for sqlite-vec extension loading (initialization only)
   * - Initializes DatabasePool for all query operations (non-blocking) [if enabled]
   * - Workers inherit configuration (WAL mode, pragmas) from worker initialization
   *
   * FASE 5.1 Feature Flag:
   * - If DEVSTREAM_WORKER_POOL_ENABLED=true: Initialize DatabasePool (non-blocking)
   * - If DEVSTREAM_WORKER_POOL_ENABLED=false: Use direct connection (synchronous)
   */
  async initialize(): Promise<void> {
    try {
      // Open database connection
      // When worker pool disabled: Used for ALL operations (queries + sqlite-vec)
      // When worker pool enabled: Used only for sqlite-vec extension loading
      this.db = new Database(this.dbPath, {
        readonly: false,
        fileMustExist: true
      });

      console.error(`✅ Connected to DevStream database: ${this.dbPath}`);

      // Configure for multi-session concurrency (CRITICAL for 5+ sessions)
      this.db.pragma('journal_mode = WAL');       // Write-Ahead Logging for concurrent reads
      this.db.pragma('busy_timeout = 5000');       // Wait up to 5s for locks
      this.db.pragma('synchronous = NORMAL');      // Faster commits with WAL
      this.db.pragma('cache_size = -64000');       // 64MB cache
      this.db.pragma('temp_store = MEMORY');       // In-memory temp tables
      this.db.pragma('mmap_size = 30000000000');   // Memory-mapped I/O (30GB)

      console.error('✅ SQLite configured for multi-session concurrency');

      // Load sqlite-vec extension using official package
      await this.loadVectorExtension();

      // FASE 5.1: Conditionally initialize DatabasePool based on feature flag
      if (this.workerPoolEnabled) {
        // Initialize DatabasePool for all query operations (FASE 2.1)
        // Workers will have isolated connections with same configuration
        this.pool = getDatabasePool();
        console.error('✅ DatabasePool initialized for non-blocking query operations');
      } else {
        // Worker pool disabled - use direct connection for all operations
        this.pool = null;
        console.error('⚠️  Worker pool disabled - using direct synchronous operations (legacy mode)');
        console.error('   Performance: Event loop may block during database operations');
        console.error('   To enable: Set DEVSTREAM_WORKER_POOL_ENABLED=true and restart');
      }

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      throw new Error(`Failed to initialize DevStream database: ${errorMessage}`);
    }
  }

  /**
   * Load sqlite-vec extension using official npm package
   * Context7 pattern: Use sqliteVec.load() for reliable extension loading
   */
  private async loadVectorExtension(): Promise<void> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      // Load sqlite-vec using official package - this handles all extension complexity
      sqliteVec.load(this.db);

      // Verify extension loaded correctly
      const result = this.db.prepare('SELECT vec_version() as version').get() as { version: string };
      console.error(`✅ sqlite-vec extension loaded: ${result.version}`);

      this.vectorSearchAvailable = true;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error(`⚠️  Failed to load sqlite-vec extension: ${errorMessage}`);
      console.error(`⚠️  Continuing without vector search - text-only search will be used`);
      this.vectorSearchAvailable = false;
    }
  }

  /**
   * Get vector search availability status
   * Context7 pattern: Allow queries to check capability before using vector functions
   */
  getVectorSearchStatus(): boolean {
    return this.vectorSearchAvailable;
  }

  /**
   * Get diagnostic information about vector search configuration
   * Context7 pattern: Provide observability into vector search status
   */
  async getVectorSearchDiagnostics(): Promise<{
    available: boolean;
    version: string | null;
    error: string | null;
    database_size_bytes?: number;
  }> {
    if (!this.vectorSearchAvailable) {
      return {
        available: false,
        version: null,
        error: 'Vector search extension not loaded'
      };
    }

    try {
      if (!this.db) throw new Error('Database not initialized');

      const result = this.db.prepare('SELECT vec_version() as version').get() as { version: string };

      // Get database size
      const sizeResult = this.db.prepare('SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()').get() as { size: number };

      return {
        available: true,
        version: result.version,
        error: null,
        database_size_bytes: sizeResult.size
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        available: false,
        version: null,
        error: `Version check failed: ${errorMessage}`
      };
    }
  }

  /**
   * Execute a SELECT query and return results
   *
   * FASE 2.1 Migration:
   * - ✅ Migrated to DatabasePool (non-blocking) when worker pool enabled
   * - Executes in worker thread (no event loop blocking)
   * - Performance: 3250ms → 0ms main thread blocking
   *
   * FASE 5.1 Feature Flag:
   * - If worker pool enabled: Use DatabasePool (non-blocking)
   * - If worker pool disabled: Use direct better-sqlite3 (synchronous, blocks event loop)
   */
  async query<T = any>(sql: string, params: any[] = []): Promise<T[]> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      // FASE 5.1: Conditional execution based on worker pool flag
      if (this.workerPoolEnabled && this.pool) {
        // Use worker pool (non-blocking)
        return await this.pool.query<T>(sql, params);
      } else {
        // Use direct connection (synchronous - blocks event loop)
        // Context7 pattern: db.prepare().all() for SELECT queries
        const stmt = this.db.prepare(sql);
        return stmt.all(...params) as T[];
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      throw new Error(`Query failed: ${errorMessage}`);
    }
  }

  /**
   * Execute a single row SELECT query
   *
   * FASE 2.1 Migration:
   * - ✅ Migrated to DatabasePool (non-blocking) when worker pool enabled
   * - Executes in worker thread (no event loop blocking)
   *
   * FASE 5.1 Feature Flag:
   * - If worker pool enabled: Use DatabasePool (non-blocking)
   * - If worker pool disabled: Use direct better-sqlite3 (synchronous, blocks event loop)
   */
  async queryOne<T = any>(sql: string, params: any[] = []): Promise<T | null> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      // FASE 5.1: Conditional execution based on worker pool flag
      if (this.workerPoolEnabled && this.pool) {
        // Use worker pool (non-blocking)
        const result = await this.pool.queryOne<T>(sql, params);
        return result || null;
      } else {
        // Use direct connection (synchronous - blocks event loop)
        // Context7 pattern: db.prepare().get() for single row SELECT
        const stmt = this.db.prepare(sql);
        const result = stmt.get(...params) as T | undefined;
        return result || null;
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      throw new Error(`Query failed: ${errorMessage}`);
    }
  }

  /**
   * Execute an INSERT/UPDATE/DELETE query
   *
   * FASE 2.1 Migration:
   * - ✅ Migrated to DatabasePool (non-blocking) when worker pool enabled
   * - Executes in worker thread (no event loop blocking)
   *
   * FASE 5.1 Feature Flag:
   * - If worker pool enabled: Use DatabasePool (non-blocking)
   * - If worker pool disabled: Use direct better-sqlite3 (synchronous, blocks event loop)
   */
  async execute(sql: string, params: any[] = []): Promise<{ lastID?: number; changes: number }> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      // FASE 5.1: Conditional execution based on worker pool flag
      if (this.workerPoolEnabled && this.pool) {
        // Use worker pool (non-blocking)
        const info = await this.pool.execute(sql, params);
        return {
          lastID: info.lastInsertRowid as number,
          changes: info.changes
        };
      } else {
        // Use direct connection (synchronous - blocks event loop)
        // Context7 pattern: db.prepare().run() for INSERT/UPDATE/DELETE
        const stmt = this.db.prepare(sql);
        const info = stmt.run(...params);
        return {
          lastID: info.lastInsertRowid as number,
          changes: info.changes
        };
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      throw new Error(`Execute failed: ${errorMessage}`);
    }
  }

  /**
   * Close database connection
   *
   * FASE 2.1 Migration:
   * - ✅ Closes both direct connection and DatabasePool
   * - Graceful shutdown with pending task completion
   */
  async close(): Promise<void> {
    try {
      // Close DatabasePool first (waits for pending tasks)
      if (this.pool) {
        await this.pool.close();
        this.pool = null;
      }

      // Close direct connection (used for sqlite-vec initialization)
      if (this.db) {
        this.db.close();
        console.error('✅ DevStream database connection closed');
        this.db = null;
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      throw new Error(`Failed to close database: ${errorMessage}`);
    }
  }

  /**
   * Check if database is connected
   */
  isConnected(): boolean {
    return this.db !== null && this.db.open;
  }

  /**
   * Get database schema information
   */
  async getTableInfo(tableName: string): Promise<any[]> {
    return this.query(`PRAGMA table_info(${tableName})`);
  }

  /**
   * List all tables in the database
   */
  async listTables(): Promise<string[]> {
    const result = await this.query<{ name: string }>(
      "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    );
    return result.map(row => row.name);
  }

  /**
   * Test database connection and schema
   */
  async testConnection(): Promise<{ success: boolean; tables: string[]; error?: string }> {
    try {
      if (!this.isConnected()) {
        throw new Error('Database not connected');
      }

      const tables = await this.listTables();

      // Check for required DevStream tables
      const requiredTables = ['intervention_plans', 'phases', 'micro_tasks', 'semantic_memory'];
      const missingTables = requiredTables.filter(table => !tables.includes(table));

      if (missingTables.length > 0) {
        throw new Error(`Missing required tables: ${missingTables.join(', ')}`);
      }

      return { success: true, tables };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return { success: false, tables: [], error: errorMessage };
    }
  }

  /**
   * Get database path (for health monitoring)
   */
  getDatabasePath(): string {
    return this.dbPath;
  }

  /**
   * Get memory statistics for health monitoring
   */
  async getMemoryStats(): Promise<{
    total_records: number;
    records_with_embeddings: number;
    embedding_coverage_percent: number;
  } | null> {
    try {
      if (!this.db) {
        return null;
      }

      // Get total records
      const totalResult = this.db.prepare('SELECT COUNT(*) as count FROM semantic_memory').get() as { count: number };
      const totalRecords = totalResult.count;

      // Get records with embeddings
      const embeddingResult = this.db.prepare(
        'SELECT COUNT(*) as count FROM semantic_memory WHERE embedding IS NOT NULL AND embedding != ""'
      ).get() as { count: number };
      const recordsWithEmbeddings = embeddingResult.count;

      const coveragePercent = totalRecords > 0 ? (recordsWithEmbeddings / totalRecords) * 100 : 0;

      return {
        total_records: totalRecords,
        records_with_embeddings: recordsWithEmbeddings,
        embedding_coverage_percent: Math.round(coveragePercent * 100) / 100,
      };
    } catch (error) {
      console.error('Failed to get memory stats:', error);
      return null;
    }
  }

  /**
   * Get session statistics for health monitoring
   */
  async getSessionStats(): Promise<{
    active_sessions: number;
  } | null> {
    try {
      if (!this.db) {
        return null;
      }

      // Get active sessions
      const sessionResult = this.db.prepare(
        'SELECT COUNT(*) as count FROM work_sessions WHERE status = "active"'
      ).get() as { count: number };

      return {
        active_sessions: sessionResult.count,
      };
    } catch (error) {
      console.error('Failed to get session stats:', error);
      return null;
    }
  }
}

/**
 * Database interfaces matching DevStream schema
 */
export interface InterventionPlan {
  id: string;
  title: string;
  description: string;
  objectives: string; // JSON string
  expected_outcome: string;
  status: 'draft' | 'active' | 'completed' | 'paused';
  priority: number;
  estimated_hours: number;
  actual_hours: number;
  created_at: string;
  updated_at: string;
  tags: string; // JSON string
  metadata: string; // JSON string
}

export interface Phase {
  id: string;
  plan_id: string;
  name: string;
  description: string;
  objective: string;
  sequence_order: number;
  status: 'pending' | 'active' | 'completed';
  started_at: string | null;
  completed_at: string | null;
  estimated_hours: number;
  actual_hours: number;
  dependencies: string; // JSON string
  deliverables: string; // JSON string
  success_criteria: string; // JSON string
  created_at: string;
  updated_at: string;
}

export interface MicroTask {
  id: string;
  phase_id: string;
  title: string;
  description: string;
  max_duration_minutes: number;
  max_context_tokens: number;
  assigned_agent: string;
  task_type: 'analysis' | 'coding' | 'documentation' | 'testing' | 'review' | 'research';
  status: 'pending' | 'active' | 'completed' | 'failed' | 'skipped';
  priority: number;
  input_files: string; // JSON string
  output_files: string; // JSON string
  retry_count: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SemanticMemory {
  id: string;
  plan_id: string | null;
  phase_id: string | null;
  task_id: string | null;
  content: string;
  content_type: 'code' | 'documentation' | 'context' | 'output' | 'error' | 'decision' | 'learning';
  content_format: 'text' | 'markdown' | 'code' | 'json' | 'yaml' | null;
  keywords: string | null; // JSON string array
  entities: string | null; // JSON string
  sentiment: number | null;
  complexity_score: number | null;
  embedding: string | null; // JSON string of vector
  embedding_model: string | null;
  embedding_dimension: number | null;
  context_snapshot: string | null; // JSON string
  related_memory_ids: string | null; // JSON string
  access_count: number | null;
  last_accessed_at: string | null;
  relevance_score: number | null;
  is_archived: boolean | null;
  created_at: string;
  updated_at: string;
}

/**
 * Implementation Plan interface for DevStream Protocol v2.2.0
 * Stores model-specific implementation plans with dual storage pattern (DB + file system)
 */
export interface ImplementationPlan {
  id: string;
  task_id: string;
  model_type: 'glm-4.6' | 'sonnet-4.5';
  plan_content: string;
  plan_file_path: string | null;
  handoff_prompt: string | null;
  metadata: string; // JSON string
  created_at: string;
  updated_at: string;
}