#!/usr/bin/env node
/**
 * DevStream Production Startup Script
 * Context7-compliant production deployment with robust path resolution
 */

import { fileURLToPath } from 'url';
import { dirname, join, resolve } from 'path';
import { readFileSync, existsSync } from 'fs';

// ============================================================================
// Path Resolution (Context7 Pattern: import.meta.url + fileURLToPath)
// ============================================================================

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = resolve(__dirname, '..'); // Navigate to project root

/**
 * Load environment variables from .env.production
 * Override mode: Production config ALWAYS takes precedence
 */
function loadProductionEnv() {
  const prodEnvPath = join(__dirname, '.env.production');

  if (!existsSync(prodEnvPath)) {
    console.warn('⚠️  .env.production not found, using environment defaults');
    return;
  }

  try {
    const envFile = readFileSync(prodEnvPath, 'utf8');
    let loadedCount = 0;

    envFile.split('\n').forEach(line => {
      // Skip comments and empty lines
      if (!line || line.trim().startsWith('#')) return;

      const match = line.match(/^([^#=]+)=(.*)$/);
      if (match) {
        const key = match[1].trim();
        const value = match[2].trim().replace(/^["']|["']$/g, ''); // Remove quotes

        if (key) {
          // OVERRIDE MODE: Production config ALWAYS wins
          process.env[key] = value;
          loadedCount++;
        }
      }
    });

    console.log(`✅ Loaded ${loadedCount} variables from .env.production`);
  } catch (err) {
    console.error(`❌ Error loading .env.production: ${err.message}`);
    process.exit(1);
  }
}

/**
 * Resolve path relative to project root
 * Supports both absolute paths and relative paths
 *
 * @param {string} configPath - Path from config (absolute or relative)
 * @returns {string} Absolute resolved path
 */
function resolveProjectPath(configPath) {
  // Already absolute? Use as-is
  if (configPath.startsWith('/')) {
    return configPath;
  }

  // Relative path: resolve from project root
  return join(projectRoot, configPath);
}

// ============================================================================
// Load Environment First
// ============================================================================

loadProductionEnv();

console.log('🚀 DevStream Production Startup\n');
console.log('='.repeat(70));

// ============================================================================
// Import Modules (after environment loaded)
// ============================================================================

const { DevStreamDatabase } = await import('./dist/database.js');
const { getOllamaClient } = await import('./dist/ollama-client.js');
const { HybridSearchEngine } = await import('./dist/tools/hybrid-search.js');
const { MetricsServer } = await import('./dist/monitoring/metrics-server.js');

async function startProduction() {
  try {
    // 1. Initialize Database
    console.log('\n📊 Step 1: Initializing database...');
    console.log(`   Project root:  ${projectRoot}`);
    console.log(`   Script dir:    ${__dirname}`);
    console.log(`   CWD:           ${process.cwd()}`);

    // Resolve database path (supports both absolute and relative)
    const dbPathRaw = process.env.DEVSTREAM_DB_PATH || 'data/devstream.db';
    const dbPath = resolveProjectPath(dbPathRaw);

    console.log(`   DB config:     ${dbPathRaw}`);
    console.log(`   DB resolved:   ${dbPath}`);

    const database = new DevStreamDatabase(dbPath);
    await database.initialize();
    console.log(`✅ Database initialized: ${dbPath}`);

    // 2. Verify Ollama
    console.log('\n🧠 Step 2: Verifying Ollama connection...');
    const ollamaClient = getOllamaClient();
    const model = ollamaClient.getDefaultModel();
    console.log(`✅ Ollama connected: ${model}`);

    // 3. Initialize Hybrid Search
    console.log('\n🔍 Step 3: Initializing hybrid search...');
    const searchEngine = new HybridSearchEngine(database, ollamaClient);
    const diagnostics = await searchEngine.getDiagnostics();
    console.log('✅ Hybrid search initialized');
    console.log(`   - Vector search: ${diagnostics.vector_search.available ? '✅' : '❌'} (${diagnostics.vector_search.version || 'N/A'})`);
    console.log(`   - FTS5 search: ${diagnostics.fts5_available ? '✅' : '❌'}`);
    console.log(`   - Total memories: ${diagnostics.total_memories}`);
    console.log(`   - With embeddings: ${diagnostics.memories_with_embeddings}`);
    console.log(`   - vec0 indexed: ${diagnostics.vec0_indexed}`);
    console.log(`   - FTS5 indexed: ${diagnostics.fts5_indexed}`);

    // 4. Start Metrics Server
    console.log('\n📈 Step 4: Starting metrics server...');
    const metricsPort = parseInt(process.env.METRICS_PORT || '9090');
    const metricsServer = new MetricsServer({ port: metricsPort });
    await metricsServer.start();
    console.log('✅ Metrics server started');

    // 5. Run Health Check
    console.log('\n🏥 Step 5: Running health checks...');

    // Test search
    const testResults = await searchEngine.search('test query', { k: 5 });
    console.log(`✅ Search test: ${testResults.length} results`);

    // Check metrics endpoint
    const response = await fetch(`http://localhost:${metricsPort}/health`);
    const health = await response.json();
    console.log(`✅ Metrics endpoint: ${health.status}`);

    // 6. Production Ready
    console.log('\n' + '='.repeat(70));
    console.log('\n🎉 DevStream is PRODUCTION READY!\n');
    console.log('📊 Metrics Dashboard:');
    console.log(`   - Prometheus: http://localhost:${metricsPort}/metrics`);
    console.log(`   - JSON API:   http://localhost:${metricsPort}/metrics/json`);
    console.log(`   - Health:     http://localhost:${metricsPort}/health`);
    console.log(`   - Quality:    http://localhost:${metricsPort}/quality`);
    console.log(`   - Errors:     http://localhost:${metricsPort}/errors`);

    console.log('\n📖 Documentation:');
    console.log('   - Architecture: HYBRID_SEARCH.md');
    console.log('   - Monitoring:   MONITORING.md');
    console.log('   - Operations:   OPERATIONAL_RUNBOOK.md');

    console.log('\n⚙️  Configuration:');
    console.log(`   - Project Root: ${projectRoot}`);
    console.log(`   - Database:     ${dbPath}`);
    console.log(`   - Ollama:       ${process.env.OLLAMA_HOST || 'http://localhost:11434'}`);
    console.log(`   - Model:        ${model}`);
    console.log(`   - Metrics Port: ${metricsPort}`);
    console.log(`   - Node Env:     ${process.env.NODE_ENV || 'development'}`);

    console.log('\n✨ MCP Server ready for Claude Code integration!');
    console.log('   Add this server to Claude Code MCP settings.\n');

    // Keep process alive
    console.log('Press Ctrl+C to stop...\n');

    // Graceful shutdown
    const shutdown = async (signal) => {
      console.log(`\n\n⏳ Received ${signal}, shutting down gracefully...`);
      await metricsServer.stop();
      console.log('✅ Metrics server stopped');
      console.log('👋 Goodbye!\n');
      process.exit(0);
    };

    process.on('SIGINT', () => shutdown('SIGINT'));
    process.on('SIGTERM', () => shutdown('SIGTERM'));

  } catch (error) {
    console.error('\n❌ Production startup failed:', error.message);
    console.error('\n📋 Troubleshooting:');
    console.error('   1. Check database path is correct');
    console.error('   2. Verify Ollama is running: curl http://localhost:11434/api/tags');
    console.error('   3. Check metrics port is available: lsof -i :9090');
    console.error('   4. Review logs for detailed errors');
    console.error(`   5. Project root: ${projectRoot}`);
    console.error(`   6. DB path: ${process.env.DEVSTREAM_DB_PATH || 'NOT SET'}`);
    console.error('\n📖 See OPERATIONAL_RUNBOOK.md for more help\n');
    process.exit(1);
  }
}

// Start production
startProduction();
