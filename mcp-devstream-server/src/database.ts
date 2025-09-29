/**
 * DevStream Database Connection Layer
 *
 * SQLite database connection and query utilities for DevStream MCP server.
 * Handles connections to the existing DevStream database schema.
 */

import sqlite3 from 'sqlite3';
import { promisify } from 'util';

/**
 * Database connection wrapper with async query support
 */
export class DevStreamDatabase {
  private db: sqlite3.Database | null = null;
  private dbPath: string;

  constructor(dbPath: string) {
    this.dbPath = dbPath;
  }

  /**
   * Initialize database connection
   */
  async initialize(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.db = new sqlite3.Database(this.dbPath, sqlite3.OPEN_READWRITE, (err) => {
        if (err) {
          reject(new Error(`Failed to connect to DevStream database: ${err.message}`));
        } else {
          console.error(`Connected to DevStream database: ${this.dbPath}`);
          resolve();
        }
      });
    });
  }

  /**
   * Execute a SELECT query and return results
   */
  async query<T = any>(sql: string, params: any[] = []): Promise<T[]> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    return new Promise((resolve, reject) => {
      this.db!.all(sql, params, (err, rows) => {
        if (err) {
          reject(new Error(`Query failed: ${err.message}`));
        } else {
          resolve(rows as T[]);
        }
      });
    });
  }

  /**
   * Execute a single row SELECT query
   */
  async queryOne<T = any>(sql: string, params: any[] = []): Promise<T | null> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    return new Promise((resolve, reject) => {
      this.db!.get(sql, params, (err, row) => {
        if (err) {
          reject(new Error(`Query failed: ${err.message}`));
        } else {
          resolve(row as T || null);
        }
      });
    });
  }

  /**
   * Execute an INSERT/UPDATE/DELETE query
   */
  async execute(sql: string, params: any[] = []): Promise<{ lastID?: number; changes: number }> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    return new Promise((resolve, reject) => {
      this.db!.run(sql, params, function(err) {
        if (err) {
          reject(new Error(`Execute failed: ${err.message}`));
        } else {
          resolve({ lastID: this.lastID, changes: this.changes });
        }
      });
    });
  }

  /**
   * Close database connection
   */
  async close(): Promise<void> {
    if (!this.db) {
      return;
    }

    return new Promise((resolve, reject) => {
      this.db!.close((err) => {
        if (err) {
          reject(new Error(`Failed to close database: ${err.message}`));
        } else {
          console.error('DevStream database connection closed');
          this.db = null;
          resolve();
        }
      });
    });
  }

  /**
   * Check if database is connected
   */
  isConnected(): boolean {
    return this.db !== null;
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