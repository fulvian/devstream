/**
 * Integration Tests for Memory Tools
 * Tests complete workflow: store → search → hybrid ranking
 */

const Database = require('better-sqlite3');
const sqliteVec = require('sqlite-vec');
const { Ollama } = require('ollama');
const fs = require('fs');
const path = require('path');

console.log('🧪 Memory Tools Integration Tests\n');
console.log('='.repeat(70) + '\n');

const TEST_DB_PATH = '/tmp/devstream-test.db';
let db;
let ollama;

// Setup
async function setup() {
  // Remove old test database
  if (fs.existsSync(TEST_DB_PATH)) {
    fs.unlinkSync(TEST_DB_PATH);
  }

  db = new Database(TEST_DB_PATH);
  sqliteVec.load(db);
  ollama = new Ollama({ host: 'http://localhost:11434' });

  // Create schema
  db.exec(`
    CREATE TABLE semantic_memory (
      id TEXT PRIMARY KEY,
      content TEXT NOT NULL,
      content_type TEXT NOT NULL,
      embedding TEXT,
      relevance_score REAL DEFAULT 0.5,
      access_count INTEGER DEFAULT 0,
      last_accessed_at TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE VIRTUAL TABLE vec_semantic_memory USING vec0(
      embedding float[768],
      content_type TEXT PARTITION KEY,
      +memory_id TEXT,
      +content_preview TEXT
    );

    CREATE VIRTUAL TABLE fts_semantic_memory USING fts5(
      content,
      content_type UNINDEXED,
      memory_id UNINDEXED,
      created_at UNINDEXED
    );

    CREATE TRIGGER fts5_sync_insert
    AFTER INSERT ON semantic_memory
    BEGIN
      INSERT INTO fts_semantic_memory(rowid, content, content_type, memory_id, created_at)
      VALUES (NEW.rowid, NEW.content, NEW.content_type, NEW.id, NEW.created_at);
    END;
  `);

  console.log('✅ Test database initialized\n');
}

// Cleanup
function cleanup() {
  if (db) {
    db.close();
  }
  if (fs.existsSync(TEST_DB_PATH)) {
    fs.unlinkSync(TEST_DB_PATH);
  }
}

// Test: Store memory with embedding
async function testStoreMemory() {
  console.log('📝 Test: Store memory with automatic embedding...');

  const content = 'Testing hybrid search with vector embeddings and keyword matching';
  const contentType = 'documentation';
  const memoryId = 'test-memory-1';

  try {
    // Generate embedding
    const embeddingResponse = await ollama.embeddings({
      model: 'embeddinggemma:300m',
      prompt: content
    });

    const embedding = embeddingResponse.embedding;
    if (!embedding || embedding.length !== 768) {
      throw new Error('Invalid embedding generated');
    }

    // Store in semantic_memory
    db.prepare(`
      INSERT INTO semantic_memory(id, content, content_type, embedding, relevance_score)
      VALUES (?, ?, ?, ?, ?)
    `).run(memoryId, content, contentType, JSON.stringify(embedding), 0.8);

    // Sync to vec0
    db.prepare(`
      INSERT INTO vec_semantic_memory(embedding, content_type, memory_id, content_preview)
      VALUES (?, ?, ?, ?)
    `).run(JSON.stringify(embedding), contentType, memoryId, content.substring(0, 200));

    // Verify storage
    const stored = db.prepare('SELECT * FROM semantic_memory WHERE id = ?').get(memoryId);
    const inVec = db.prepare('SELECT memory_id FROM vec_semantic_memory WHERE memory_id = ?').get(memoryId);
    const inFts = db.prepare('SELECT memory_id FROM fts_semantic_memory WHERE memory_id = ?').get(memoryId);

    if (!stored || !inVec || !inFts) {
      throw new Error('Memory not properly stored in all indexes');
    }

    console.log('  ✅ Memory stored successfully');
    console.log(`  ✅ Embedding: ${embedding.length}D`);
    console.log('  ✅ Synced to vec0 and FTS5\n');

    return { memoryId, embedding };

  } catch (error) {
    console.log(`  ❌ Failed: ${error.message}\n`);
    throw error;
  }
}

// Test: Hybrid search
async function testHybridSearch(testMemory) {
  console.log('🔍 Test: Hybrid search with RRF...');

  const query = 'vector embeddings search';

  try {
    // Generate query embedding
    const queryEmbedding = await ollama.embeddings({
      model: 'embeddinggemma:300m',
      prompt: query
    });

    const embeddingBuffer = Buffer.from(new Float32Array(queryEmbedding.embedding).buffer);

    // RRF hybrid search
    const sql = `
      WITH vec_matches AS (
        SELECT
          memory_id,
          ROW_NUMBER() OVER (ORDER BY distance) as rank_number,
          distance
        FROM vec_semantic_memory
        WHERE embedding MATCH ? AND k = 10
      ),
      fts_matches AS (
        SELECT
          memory_id,
          ROW_NUMBER() OVER (ORDER BY rank) as rank_number,
          rank as score
        FROM fts_semantic_memory
        WHERE fts_semantic_memory MATCH ?
        LIMIT 10
      ),
      combined AS (
        SELECT
          semantic_memory.id,
          semantic_memory.content,
          vec_matches.rank_number as vec_rank,
          fts_matches.rank_number as fts_rank,
          (
            COALESCE(1.0 / (60 + fts_matches.rank_number), 0.0) * 1.0
            + COALESCE(1.0 / (60 + vec_matches.rank_number), 0.0) * 1.0
          ) as combined_rank
        FROM fts_matches
        FULL OUTER JOIN vec_matches ON vec_matches.memory_id = fts_matches.memory_id
        JOIN semantic_memory ON semantic_memory.id = COALESCE(fts_matches.memory_id, vec_matches.memory_id)
        ORDER BY combined_rank DESC
      )
      SELECT * FROM combined
    `;

    const results = db.prepare(sql).all(embeddingBuffer, query);

    if (results.length === 0) {
      throw new Error('No results from hybrid search');
    }

    console.log(`  ✅ Found ${results.length} results`);
    console.log(`  ✅ Top result ID: ${results[0].id}`);
    console.log(`  ✅ RRF score: ${results[0].combined_rank.toFixed(4)}`);

    if (results[0].vec_rank && results[0].fts_rank) {
      console.log(`  ✅ Hybrid match (Vector: #${results[0].vec_rank}, FTS: #${results[0].fts_rank})`);
    }

    console.log();
    return results;

  } catch (error) {
    console.log(`  ❌ Failed: ${error.message}\n`);
    throw error;
  }
}

// Test: Access count tracking
function testAccessTracking(memoryId) {
  console.log('👁️  Test: Access count tracking...');

  try {
    const before = db.prepare('SELECT access_count FROM semantic_memory WHERE id = ?').get(memoryId);

    // Simulate access
    db.prepare(`
      UPDATE semantic_memory
      SET access_count = access_count + 1, last_accessed_at = datetime('now')
      WHERE id = ?
    `).run(memoryId);

    const after = db.prepare('SELECT access_count, last_accessed_at FROM semantic_memory WHERE id = ?').get(memoryId);

    if (after.access_count !== before.access_count + 1) {
      throw new Error('Access count not incremented');
    }

    if (!after.last_accessed_at) {
      throw new Error('last_accessed_at not updated');
    }

    console.log(`  ✅ Access count: ${before.access_count} → ${after.access_count}`);
    console.log(`  ✅ Timestamp updated: ${after.last_accessed_at}\n`);

  } catch (error) {
    console.log(`  ❌ Failed: ${error.message}\n`);
    throw error;
  }
}

// Test: Content type filtering
async function testContentTypeFilter() {
  console.log('🏷️  Test: Content type filtering...');

  try {
    // Insert memories with different types
    const types = ['code', 'documentation', 'learning'];

    for (const type of types) {
      const id = `test-${type}`;
      const content = `Test content for ${type} type`;

      const embeddingResponse = await ollama.embeddings({
        model: 'embeddinggemma:300m',
        prompt: content
      });

      db.prepare(`
        INSERT INTO semantic_memory(id, content, content_type, embedding)
        VALUES (?, ?, ?, ?)
      `).run(id, content, type, JSON.stringify(embeddingResponse.embedding));

      db.prepare(`
        INSERT INTO vec_semantic_memory(embedding, content_type, memory_id, content_preview)
        VALUES (?, ?, ?, ?)
      `).run(JSON.stringify(embeddingResponse.embedding), type, id, content);
    }

    // Test partition key filtering
    const embeddingBuffer = Buffer.from(new Float32Array(new Array(768).fill(0.5)).buffer);

    const results = db.prepare(`
      SELECT memory_id, content_type
      FROM vec_semantic_memory
      WHERE embedding MATCH ? AND k = 10
        AND content_type = 'documentation'
    `).all(embeddingBuffer);

    const allDocs = results.every(r => r.content_type === 'documentation');

    if (!allDocs) {
      throw new Error('Content type filter not working');
    }

    console.log(`  ✅ Filtered results: ${results.length}`);
    console.log(`  ✅ All results match content_type='documentation'\n`);

  } catch (error) {
    console.log(`  ❌ Failed: ${error.message}\n`);
    throw error;
  }
}

// Main test runner
async function runTests() {
  let passed = 0;
  let failed = 0;

  try {
    await setup();

    // Run tests sequentially
    const testMemory = await testStoreMemory();
    passed++;

    await testHybridSearch(testMemory);
    passed++;

    testAccessTracking(testMemory.memoryId);
    passed++;

    await testContentTypeFilter();
    passed++;

  } catch (error) {
    failed++;
  } finally {
    cleanup();
  }

  console.log('='.repeat(70));
  console.log(`\n📊 Integration Test Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log('❌ Some tests failed');
    process.exit(1);
  } else {
    console.log('✅ All integration tests passed!');
    process.exit(0);
  }
}

runTests().catch((error) => {
  console.error('Fatal error:', error);
  cleanup();
  process.exit(1);
});