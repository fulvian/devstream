/**
 * DevStream Health Check Tool
 *
 * Provides health status for critical DevStream dependencies:
 * - Database connectivity (SQLite + vec0 extension)
 * - Ollama service (embedding generation)
 * - Embedding coverage (semantic_memory table)
 *
 * Used for proactive monitoring and troubleshooting.
 */

import Database from 'better-sqlite3';
import * as sqliteVec from 'sqlite-vec';

interface HealthCheckResult {
  status: 'healthy' | 'degraded' | 'error';
  timestamp: string;
  checks: {
    database: DatabaseHealth;
    ollama: OllamaHealth;
    embedding_coverage: EmbeddingCoverage;
  };
}

interface DatabaseHealth {
  status: 'ok' | 'error';
  message: string;
  total_records?: number;
  vec0_version?: string;
}

interface OllamaHealth {
  status: 'ok' | 'error';
  message: string;
  model?: string;
  latency_ms?: number;
}

interface EmbeddingCoverage {
  status: 'ok' | 'warning' | 'error';
  message: string;
  total_records?: number;
  with_embeddings?: number;
  coverage_percent?: number;
  missing?: number;
}

/**
 * Execute health check for all DevStream dependencies.
 *
 * @param dbPath - Path to DevStream database
 * @param ollamaUrl - Ollama API base URL (default: http://localhost:11434)
 * @returns Health check result with status for each dependency
 */
export async function executeHealthCheck(
  dbPath: string,
  ollamaUrl: string = 'http://localhost:11434'
): Promise<HealthCheckResult> {
  const result: HealthCheckResult = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    checks: {
      database: await checkDatabase(dbPath),
      ollama: await checkOllama(ollamaUrl),
      embedding_coverage: await checkEmbeddingCoverage(dbPath)
    }
  };

  // Determine overall status
  const hasError = Object.values(result.checks).some(check => check.status === 'error');
  const hasWarning = Object.values(result.checks).some(check => check.status === 'warning');

  if (hasError) {
    result.status = 'error';
  } else if (hasWarning) {
    result.status = 'degraded';
  }

  return result;
}

/**
 * Check database connectivity and vec0 extension.
 */
async function checkDatabase(dbPath: string): Promise<DatabaseHealth> {
  try {
    const db = new Database(dbPath);

    // Load vec0 extension
    sqliteVec.load(db);

    // Verify vec0 loaded
    const vecResult = db.prepare(
      "SELECT name FROM pragma_module_list WHERE name = 'vec0'"
    ).get() as { name: string } | undefined;

    if (!vecResult) {
      db.close();
      return {
        status: 'error',
        message: 'vec0 extension not loaded'
      };
    }

    // Get vec0 version
    const versionResult = db.prepare('SELECT vec_version() as version').get() as { version: string };

    // Count total records
    const countResult = db.prepare(
      'SELECT COUNT(*) as total FROM semantic_memory'
    ).get() as { total: number };

    db.close();

    return {
      status: 'ok',
      message: 'Database connected, vec0 extension loaded',
      total_records: countResult.total,
      vec0_version: versionResult.version
    };

  } catch (error) {
    return {
      status: 'error',
      message: `Database error: ${error instanceof Error ? error.message : String(error)}`
    };
  }
}

/**
 * Check Ollama service availability and latency.
 */
async function checkOllama(baseUrl: string): Promise<OllamaHealth> {
  try {
    const startTime = Date.now();

    // Test embedding generation with small input
    const response = await fetch(`${baseUrl}/api/embed`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'embeddinggemma:300m',
        input: 'health check test'
      }),
      signal: AbortSignal.timeout(5000)  // 5 second timeout
    });

    const latency = Date.now() - startTime;

    if (!response.ok) {
      return {
        status: 'error',
        message: `Ollama API error: ${response.status} ${response.statusText}`
      };
    }

    const data = await response.json() as { embeddings?: number[][] };

    if (!data.embeddings || !Array.isArray(data.embeddings)) {
      return {
        status: 'error',
        message: 'Invalid response from Ollama (missing embeddings)'
      };
    }

    return {
      status: 'ok',
      message: 'Ollama service running',
      model: 'embeddinggemma:300m',
      latency_ms: latency
    };

  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      return {
        status: 'error',
        message: 'Ollama timeout (>5s)'
      };
    }

    return {
      status: 'error',
      message: `Ollama error: ${error instanceof Error ? error.message : String(error)}`
    };
  }
}

/**
 * Check embedding coverage in semantic_memory table.
 */
async function checkEmbeddingCoverage(dbPath: string): Promise<EmbeddingCoverage> {
  try {
    const db = new Database(dbPath);

    const result = db.prepare(`
      SELECT
        COUNT(*) as total,
        SUM(CASE WHEN embedding IS NOT NULL AND embedding != '' THEN 1 ELSE 0 END) as with_embeddings
      FROM semantic_memory
    `).get() as { total: number; with_embeddings: number };

    db.close();

    const total = result.total;
    const withEmbeddings = result.with_embeddings;
    const missing = total - withEmbeddings;
    const coveragePercent = total > 0 ? (withEmbeddings / total) * 100 : 0;

    // Determine status
    let status: 'ok' | 'warning' | 'error';
    let message: string;

    if (coveragePercent >= 95) {
      status = 'ok';
      message = `Embedding coverage: ${coveragePercent.toFixed(1)}% (healthy)`;
    } else if (coveragePercent >= 80) {
      status = 'warning';
      message = `Embedding coverage: ${coveragePercent.toFixed(1)}% (below target, backfill recommended)`;
    } else {
      status = 'error';
      message = `Embedding coverage: ${coveragePercent.toFixed(1)}% (critical, backfill required)`;
    }

    return {
      status,
      message,
      total_records: total,
      with_embeddings: withEmbeddings,
      coverage_percent: parseFloat(coveragePercent.toFixed(1)),
      missing
    };

  } catch (error) {
    return {
      status: 'error',
      message: `Coverage check error: ${error instanceof Error ? error.message : String(error)}`
    };
  }
}

/**
 * Format health check result as human-readable string.
 */
export function formatHealthCheckResult(result: HealthCheckResult): string {
  const lines = [];

  lines.push('🏥 DevStream Health Check');
  lines.push('═'.repeat(60));
  lines.push(`Status: ${result.status.toUpperCase()}`);
  lines.push(`Timestamp: ${result.timestamp}`);
  lines.push('');

  // Database
  lines.push('📊 Database:');
  const db = result.checks.database;
  lines.push(`  ${db.status === 'ok' ? '✅' : '❌'} ${db.message}`);
  if (db.total_records !== undefined) {
    lines.push(`     Records: ${db.total_records.toLocaleString()}`);
  }
  if (db.vec0_version) {
    lines.push(`     vec0: ${db.vec0_version}`);
  }
  lines.push('');

  // Ollama
  lines.push('🤖 Ollama:');
  const ollama = result.checks.ollama;
  lines.push(`  ${ollama.status === 'ok' ? '✅' : '❌'} ${ollama.message}`);
  if (ollama.model) {
    lines.push(`     Model: ${ollama.model}`);
  }
  if (ollama.latency_ms !== undefined) {
    lines.push(`     Latency: ${ollama.latency_ms}ms`);
  }
  lines.push('');

  // Embedding Coverage
  lines.push('📈 Embedding Coverage:');
  const coverage = result.checks.embedding_coverage;
  const icon = coverage.status === 'ok' ? '✅' : coverage.status === 'warning' ? '⚠️' : '❌';
  lines.push(`  ${icon} ${coverage.message}`);
  if (coverage.total_records !== undefined && coverage.with_embeddings !== undefined) {
    lines.push(`     Total: ${coverage.total_records.toLocaleString()}`);
    lines.push(`     With embeddings: ${coverage.with_embeddings.toLocaleString()}`);
    lines.push(`     Missing: ${coverage.missing?.toLocaleString()}`);
  }
  lines.push('');

  lines.push('═'.repeat(60));

  return lines.join('\n');
}
