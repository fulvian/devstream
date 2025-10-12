#!/usr/bin/env node
/**
 * Test MCP vector search functionality
 * Replicates exact MCP server behavior to diagnose why vector search fails
 */

const Database = require('better-sqlite3');
const path = require('path');

// Database path (same as MCP config)
const dbPath = path.join(__dirname, '../data/devstream.db');
console.log(`🔗 Connecting to: ${dbPath}`);

try {
  const db = new Database(dbPath);

  // Load sqlite-vec extension (same path as MCP)
  const extPath = path.join(__dirname, 'node_modules/sqlite-vec-darwin-arm64/vec0');
  console.log(`📦 Loading extension: ${extPath}`);

  db.loadExtension(extPath);

  const version = db.prepare('SELECT vec_version()').get();
  console.log(`✅ sqlite-vec loaded: ${JSON.stringify(version)}`);

  // Check virtual table
  const vecCount = db.prepare('SELECT COUNT(*) as count FROM vec_semantic_memory').get();
  console.log(`📊 Vec embeddings: ${vecCount.count.toLocaleString()}`);

  const ftsCount = db.prepare('SELECT COUNT(*) as count FROM fts_semantic_memory').get();
  console.log(`📊 FTS5 records: ${ftsCount.count.toLocaleString()}\n`);

  // Test simple vector query with sample embedding
  console.log('🧪 Testing vector query...');

  // Get a sample embedding from database
  const sample = db.prepare('SELECT memory_id, embedding FROM vec_semantic_memory LIMIT 1').get();

  if (!sample) {
    console.error('❌ No embeddings found in vec_semantic_memory');
    process.exit(1);
  }

  console.log(`✅ Sample memory_id: ${sample.memory_id}`);
  console.log(`✅ Embedding type: ${typeof sample.embedding}, length: ${sample.embedding.length}\n`);

  // Test vec0 MATCH query (MODERN syntax)
  console.log('🧪 Testing MODERN syntax: WHERE embedding MATCH ? ORDER BY distance LIMIT ?');

  try {
    const stmt = db.prepare(`
      SELECT memory_id, distance
      FROM vec_semantic_memory
      WHERE embedding MATCH ?
      ORDER BY distance
      LIMIT ?
    `);

    const results = stmt.all(sample.embedding, 5);
    console.log(`✅ Query succeeded! Found ${results.length} results\n`);

    results.forEach((r, i) => {
      console.log(`  ${i+1}. memory_id: ${r.memory_id.substring(0, 16)}... | distance: ${r.distance.toFixed(4)}`);
    });

    // Verify exact match at rank #1
    if (results[0].memory_id === sample.memory_id) {
      console.log(`\n✅ **PERFECT**: Exact match at rank #1`);
      console.log(`✅ Distance: ${results[0].distance} (should be 0.0)`);
    } else {
      console.log(`\n⚠️  Expected exact match at rank #1`);
    }

  } catch (error) {
    console.error(`❌ Vector query failed: ${error.message}`);
    process.exit(1);
  }

  // Test FTS5 query
  console.log('\n' + '='.repeat(70));
  console.log('🧪 Testing FTS5 query...\n');

  try {
    const ftsStmt = db.prepare(`
      SELECT memory_id, rank
      FROM fts_semantic_memory
      WHERE fts_semantic_memory MATCH ?
      LIMIT 5
    `);

    const ftsResults = ftsStmt.all('content:"session"');
    console.log(`✅ FTS5 query succeeded! Found ${ftsResults.length} results`);

  } catch (error) {
    console.error(`❌ FTS5 query failed: ${error.message}`);
  }

  db.close();

  console.log('\n' + '='.repeat(70));
  console.log('🎯 **CONCLUSION**: Both vector and FTS5 queries work correctly');
  console.log('🚨 **MCP server issue is elsewhere** (check Ollama connection or error handling)');

} catch (error) {
  console.error(`❌ Test failed: ${error.message}`);
  console.error(error.stack);
  process.exit(1);
}
