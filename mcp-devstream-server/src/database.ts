/**
 * DevStream Database Connection Layer
 *
 * SQLite database connection and query utilities for DevStream MCP server.
 * Uses better-sqlite3 for synchronous API and sqlite-vec for vector search.
 *
 * Context7-compliant implementation using official sqlite-vec npm package.
 */

import Database from 'better-sqlite3';
import * as sqliteVec from 'sqlite-vec';

/**
 * Database connection wrapper with sync/async query support
 * Context7 pattern: Use better-sqlite3 for reliable extension loading
 */
export class DevStreamDatabase {
  private db: Database.Database | null = null;
  private dbPath: string;
  private vectorSearchAvailable: boolean = false;

  constructor(dbPath: string) {
    this.dbPath = dbPath;
  }

  /**
   * Initialize database connection and load sqlite-vec extension
   * Context7 pattern: Load sqlite-vec using official npm package
   */
  async initialize(): Promise<void> {
    try {
      // Open database connection
      this.db = new Database(this.dbPath, {
        readonly: false,
        fileMustExist: true
      });

      console.error(`✅ Connected to DevStream database: ${this.dbPath}`);

      // Load sqlite-vec extension using official package
      await this.loadVectorExtension();

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

      return {
        available: true,
        version: result.version,
        error: null
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
   * Context7 pattern: Synchronous API with better-sqlite3
   */
  async query<T = any>(sql: string, params: any[] = []): Promise<T[]> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      const stmt = this.db.prepare(sql);
      const rows = stmt.all(...params) as T[];
      return rows;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      throw new Error(`Query failed: ${errorMessage}`);
    }
  }

  /**
   * Execute a single row SELECT query
   */
  async queryOne<T = any>(sql: string, params: any[] = []): Promise<T | null> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      const stmt = this.db.prepare(sql);
      const row = stmt.get(...params) as T | undefined;
      return row || null;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      throw new Error(`Query failed: ${errorMessage}`);
    }
  }

  /**
   * Execute an INSERT/UPDATE/DELETE query
   */
  async execute(sql: string, params: any[] = []): Promise<{ lastID?: number; changes: number }> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      const stmt = this.db.prepare(sql);
      const info = stmt.run(...params);
      return {
        lastID: info.lastInsertRowid as number,
        changes: info.changes
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      throw new Error(`Execute failed: ${errorMessage}`);
    }
  }

  /**
   * Close database connection
   */
  async close(): Promise<void> {
    if (!this.db) {
      return;
    }

    try {
      this.db.close();
      console.error('✅ DevStream database connection closed');
      this.db = null;
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