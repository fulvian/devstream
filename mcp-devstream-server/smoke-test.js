#!/usr/bin/env node
/**
 * Production Smoke Tests
 * Context7-compliant validation of deployed system
 */

import { DevStreamDatabase } from './dist/database.js';
import { getOllamaClient } from './dist/ollama-client.js';
import { HybridSearchEngine } from './dist/tools/hybrid-search.js';

const TESTS = [
  { name: 'Database Connection', fn: testDatabase },
  { name: 'Ollama Service', fn: testOllama },
  { name: 'Vector Search Extension', fn: testVectorExtension },
  { name: 'Hybrid Search - Simple Query', fn: testSimpleSearch },
  { name: 'Hybrid Search - Complex Query', fn: testComplexSearch },
  { name: 'Metrics Server', fn: testMetricsServer },
];

let passedTests = 0;
let failedTests = 0;

async function testDatabase() {
  const dbPath = process.env.DEVSTREAM_DB_PATH || '/Users/fulvioventura/devstream/data/devstream.db';
  const db = new DevStreamDatabase(dbPath);
  await db.initialize();

  const tables = await db.listTables();
  if (!tables.includes('semantic_memory')) {
    throw new Error('semantic_memory table not found');
  }

  await db.close();
  return 'Connected and verified schema';
}

async function testOllama() {
  const client = getOllamaClient();
  const model = client.getDefaultModel();

  if (!model) {
    throw new Error('No default model configured');
  }

  return `Model: ${model}`;
}

async function testVectorExtension() {
  const dbPath = process.env.DEVSTREAM_DB_PATH || '/Users/fulvioventura/devstream/data/devstream.db';
  const db = new DevStreamDatabase(dbPath);
  await db.initialize();

  const available = db.getVectorSearchStatus();
  if (!available) {
    throw new Error('Vector search extension not loaded');
  }

  const diagnostics = await db.getVectorSearchDiagnostics();
  await db.close();

  return `Version: ${diagnostics.version}`;
}

async function testSimpleSearch() {
  const dbPath = process.env.DEVSTREAM_DB_PATH || '/Users/fulvioventura/devstream/data/devstream.db';
  const db = new DevStreamDatabase(dbPath);
  await db.initialize();

  const ollama = getOllamaClient();
  const searchEngine = new HybridSearchEngine(db, ollama);

  const results = await searchEngine.search('task management', { k: 5 });
  await db.close();

  if (results.length === 0) {
    throw new Error('No results returned');
  }

  return `${results.length} results, top score: ${results[0].combined_rank.toFixed(6)}`;
}

async function testComplexSearch() {
  const dbPath = process.env.DEVSTREAM_DB_PATH || '/Users/fulvioventura/devstream/data/devstream.db';
  const db = new DevStreamDatabase(dbPath);
  await db.initialize();

  const ollama = getOllamaClient();
  const searchEngine = new HybridSearchEngine(db, ollama);

  const results = await searchEngine.search('implement intervention plan with dependencies', { k: 10 });
  await db.close();

  if (results.length === 0) {
    throw new Error('No results returned');
  }

  // Check result diversity
  const contentTypes = new Set(results.map(r => r.content_type));

  return `${results.length} results, ${contentTypes.size} content types`;
}

async function testMetricsServer() {
  const port = process.env.METRICS_PORT || '9090';

  // Test health endpoint
  const healthResponse = await fetch(`http://localhost:${port}/health`);
  if (!healthResponse.ok) {
    throw new Error(`Health check failed: ${healthResponse.status}`);
  }

  const health = await healthResponse.json();
  if (health.status !== 'healthy') {
    throw new Error(`Health status: ${health.status}`);
  }

  // Test metrics endpoint
  const metricsResponse = await fetch(`http://localhost:${port}/metrics`);
  if (!metricsResponse.ok) {
    throw new Error(`Metrics endpoint failed: ${metricsResponse.status}`);
  }

  const metricsText = await metricsResponse.text();
  if (!metricsText.includes('devstream_')) {
    throw new Error('No DevStream metrics found');
  }

  return `Health: ${health.status}, Uptime: ${Math.floor(health.uptime)}s`;
}

async function runTest(test) {
  try {
    const result = await test.fn();
    console.log(`✅ ${test.name}: ${result}`);
    passedTests++;
  } catch (error) {
    console.error(`❌ ${test.name}: ${error.message}`);
    failedTests++;
  }
}

async function main() {
  console.log('🧪 DevStream Production Smoke Tests\n');
  console.log('='.repeat(70));

  for (const test of TESTS) {
    await runTest(test);
  }

  console.log('='.repeat(70));
  console.log(`\n📊 Test Results: ${passedTests}/${TESTS.length} passed`);

  if (failedTests > 0) {
    console.log(`❌ ${failedTests} tests failed`);
    process.exit(1);
  } else {
    console.log('✅ All tests passed - System is production ready!');
    process.exit(0);
  }
}

main();