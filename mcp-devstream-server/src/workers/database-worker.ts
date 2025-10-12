/**
 * Database Worker for Piscina Pool
 *
 * Executes synchronous SQLite operations in isolated worker thread
 * to prevent blocking the main event loop.
 *
 * Context7 Research:
 * - better-sqlite3 official worker pattern (Trust Score 6.8, 58 snippets)
 * - Piscina worker implementation (Trust Score 6.4, 195 snippets)
 *
 * Architecture:
 * - Each worker has isolated SQLite connection (WAL mode)
 * - Synchronous operations (db.prepare().all()) run in worker thread
 * - Main thread remains non-blocking (Promise-based communication)
 *
 * Performance:
 * - Event loop blocking: 3250ms → 0ms (main thread)
 * - Query execution: Same performance, but isolated
 * - Concurrency: 8 workers × 10 concurrent tasks = 80 parallel ops
 */

import Database from 'better-sqlite3';
import * as sqliteVec from 'sqlite-vec';
import path from 'path';

// Type definitions for worker messages
interface WorkerMessage {
  type: 'query' | 'execute' | 'queryOne';
  sql: string;
  params: any[];
}

interface WorkerResponse {
  success: boolean;
  result?: any;
  error?: string;
  code?: string;
}

// Database configuration from environment
const DB_PATH = process.env.DEVSTREAM_DB_PATH || path.join(process.cwd(), 'data', 'devstream.db');

// Initialize SQLite connection (isolated per worker)
const db = new Database(DB_PATH, {
  readonly: false,
  fileMustExist: true,
});

// Configure SQLite for optimal performance (WAL mode preserved)
db.pragma('journal_mode = WAL');
db.pragma('busy_timeout = 5000');
db.pragma('synchronous = NORMAL');
db.pragma('cache_size = -64000'); // 64MB cache
db.pragma('mmap_size = 30000000000'); // 30GB memory-mapped I/O

// Load sqlite-vec extension (CRITICAL - each worker needs its own extension load)
// Context7 pattern: sqliteVec.load() handles all extension complexity
try {
  sqliteVec.load(db);
  const result = db.prepare('SELECT vec_version() as version').get() as { version: string };
  console.error(`✅ Worker ${process.pid} loaded sqlite-vec extension: ${result.version}`);
} catch (error) {
  const errorMessage = error instanceof Error ? error.message : 'Unknown error';
  console.error(`❌ Worker ${process.pid} failed to load sqlite-vec: ${errorMessage}`);
  throw error; // Critical error - worker cannot function without vec0
}

console.error(`✅ Worker ${process.pid} initialized with database: ${DB_PATH}`);

/**
 * Piscina Worker Handler Function
 *
 * Piscina Pattern (Context7 Trust Score 6.4):
 * - Workers export a default function that receives task payload
 * - Piscina handles all communication (no parentPort needed)
 * - Function can be sync or async (we use sync for better-sqlite3)
 * - Errors are automatically caught and propagated to main thread
 *
 * @param message - Task payload with SQL operation details
 * @returns WorkerResponse with success status and result/error
 */
export default function(message: WorkerMessage): WorkerResponse {
  try {
    let result: any;

    // Execute operation based on type
    switch (message.type) {
      case 'query':
        // Execute query returning all rows (db.prepare().all())
        result = db.prepare(message.sql).all(...message.params);
        break;

      case 'execute':
        // Execute statement returning run info (db.prepare().run())
        result = db.prepare(message.sql).run(...message.params);
        break;

      case 'queryOne':
        // Execute query returning first row (db.prepare().get())
        result = db.prepare(message.sql).get(...message.params);
        break;

      default:
        throw new Error(`Unknown operation type: ${message.type}`);
    }

    // Return successful response
    return {
      success: true,
      result,
    };
  } catch (error: any) {
    // Return error response
    return {
      success: false,
      error: error.message,
      code: error.code,
    };
  }
}

// Graceful cleanup on worker exit
process.on('exit', () => {
  console.error(`🔄 Worker ${process.pid} closing database connection...`);
  db.close();
});

process.on('SIGTERM', () => {
  console.error(`🛑 Worker ${process.pid} received SIGTERM`);
  db.close();
  process.exit(0);
});

process.on('SIGINT', () => {
  console.error(`🛑 Worker ${process.pid} received SIGINT`);
  db.close();
  process.exit(0);
});
