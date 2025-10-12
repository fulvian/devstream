#!/usr/bin/env node
/**
 * End-to-end test replicating EXACT MCP server hybrid search flow
 * Diagnose why vector search fails in production MCP
 */

const Database = require('better-sqlite3');
const sqliteVec = require('sqlite-vec');
const { Ollama } = require('ollama');
const path = require('path');

async function testMCPHybridSearch() {
  console.log('🧪 E2E Test: MCP Hybrid Search Flow\n');

  // STEP 1: Database setup (same as MCP)
  const dbPath = path.resolve(__dirname, '../data/devstream.db');
  console.log(`📦 Database: ${dbPath}`);

  const db = new Database(dbPath, { readonly: false, fileMustExist: true });
  console.log('✅ Database opened\n');

  // STEP 2: Load sqlite-vec (same method as MCP)
  console.log('📦 Loading sqlite-vec extension...');
  try {
    sqliteVec.load(db);
    const version = db.prepare('SELECT vec_version() as version').get();
    console.log(`✅ sqlite-vec loaded: ${version.version}\n`);
  } catch (error) {
    console.error(`❌ Failed to load sqlite-vec: ${error.message}`);
    process.exit(1);
  }

  // STEP 3: Ollama setup (same as MCP)
  console.log('📦 Setting up Ollama client...');
  const ollama = new Ollama({
    host: process.env.OLLAMA_HOST || 'http://127.0.0.1:11434'
  });

  try {
    await ollama.ps();
    console.log('✅ Ollama connection established\n');
  } catch (error) {
    console.error(`❌ Ollama connection failed: ${error.message}`);
    process.exit(1);
  }

  // STEP 4: Generate query embedding (same as MCP)
  const query = 'session summary';
  console.log(`🧠 Generating embedding for query: "${query}"`);

  let queryEmbedding;
  try {
    const response = await ollama.embed({
      model: 'embeddinggemma:300m',
      input: query,
      truncate: true,
      keep_alive: '5m'
    });

    if (!response.embeddings || response.embeddings.length === 0) {
      throw new Error('Invalid embedding response');
    }

    queryEmbedding = response.embeddings[0];
    console.log(`✅ Embedding generated: ${queryEmbedding.length} dimensions\n`);
  } catch (error) {
    console.error(`❌ Embedding generation failed: ${error.message}`);
    console.error('🔄 This triggers FTS5-only fallback in MCP!\n');
    process.exit(1);
  }

  // STEP 5: Execute hybrid search (same SQL as MCP)
  console.log('🔍 Executing hybrid search query...\n');

  // Convert embedding to Buffer (same as MCP)
  const embeddingFloat32 = new Float32Array(queryEmbedding);
  const embeddingBuffer = Buffer.from(embeddingFloat32.buffer);

  // Sanitize FTS5 query (same as MCP)
  const sanitizedQuery = query.split(/\s+/).map(term => `content:"${term}"`).join(' OR ');
  console.log(`   FTS5 query: ${sanitizedQuery}`);

  const sql = `
    WITH vec_matches AS (
      SELECT
        memory_id,
        ROW_NUMBER() OVER (ORDER BY distance) as rank_number,
        distance
      FROM vec_semantic_memory
      WHERE embedding MATCH ?
      ORDER BY distance
      LIMIT ?
    ),
    fts_matches AS (
      SELECT
        memory_id,
        ROW_NUMBER() OVER (ORDER BY rank) as rank_number,
        rank as score
      FROM fts_semantic_memory
      WHERE fts_semantic_memory MATCH ?
      LIMIT ?
    ),
    combined AS (
      SELECT
        memory_id,
        NULL as vec_rank,
        rank_number as fts_rank,
        NULL as vec_distance,
        score as fts_score
      FROM fts_matches

      UNION ALL

      SELECT
        memory_id,
        rank_number as vec_rank,
        NULL as fts_rank,
        distance as vec_distance,
        NULL as fts_score
      FROM vec_matches
    )
    SELECT
      semantic_memory.id as memory_id,
      semantic_memory.content,
      semantic_memory.content_type,
      semantic_memory.created_at,
      MAX(combined.vec_rank) as vec_rank,
      MAX(combined.fts_rank) as fts_rank,
      (
        COALESCE(1.0 / (60 + MAX(combined.fts_rank)), 0.0) * 1.0
        + COALESCE(1.0 / (60 + MAX(combined.vec_rank)), 0.0) * 1.0
      ) as combined_rank,
      MAX(combined.vec_distance) as vec_distance,
      MAX(combined.fts_score) as fts_score
    FROM combined
    JOIN semantic_memory ON semantic_memory.id = combined.memory_id
    GROUP BY semantic_memory.id
    ORDER BY combined_rank DESC
    LIMIT 5
  `;

  try {
    const stmt = db.prepare(sql);
    const results = stmt.all(embeddingBuffer, 10, sanitizedQuery, 10);

    console.log(`✅ Hybrid search completed: ${results.length} results\n`);
    console.log('=' * 70 + '\n');

    results.forEach((r, i) => {
      console.log(`${i + 1}. ${r.content_type.toUpperCase()} Memory`);
      console.log(`   RRF Score: ${(r.combined_rank * 100).toFixed(1)}`);

      if (r.vec_rank && r.fts_rank) {
        console.log(`   ✅ HYBRID: Vector Rank #${r.vec_rank} + Keyword Rank #${r.fts_rank}`);
      } else if (r.vec_rank) {
        console.log(`   📊 Vector Only: Rank #${r.vec_rank} (distance: ${r.vec_distance?.toFixed(4)})`);
      } else if (r.fts_rank) {
        console.log(`   📊 Keyword Only: Rank #${r.fts_rank}`);
      }

      console.log(`   Content: ${r.content.substring(0, 100)}...`);
      console.log(`   ID: ${r.memory_id}\n`);
    });

    // Check if vector search actually worked
    const hasVectorResults = results.some(r => r.vec_rank !== null);
    const hasFTSResults = results.some(r => r.fts_rank !== null);

    console.log('=' * 70);
    console.log('🎯 **DIAGNOSIS**:\n');

    if (hasVectorResults && hasFTSResults) {
      console.log('✅ **HYBRID SEARCH WORKS!** Both vector and keyword results present');
      console.log('✅ RRF fusion working correctly');
    } else if (hasFTSResults && !hasVectorResults) {
      console.log('❌ **VECTOR SEARCH FAILED!** Only keyword results present');
      console.log('   This is exactly what we see in MCP production!');
      console.log('   Possible causes:');
      console.log('   - vec_semantic_memory table empty/inaccessible');
      console.log('   - Embedding buffer format incorrect');
      console.log('   - sqlite-vec extension not working');
    } else if (hasVectorResults && !hasFTSResults) {
      console.log('⚠️  **KEYWORD SEARCH FAILED!** Only vector results present');
    } else {
      console.log('❌ **BOTH FAILED!** No results from either method');
    }

  } catch (error) {
    console.error(`❌ Hybrid search query failed: ${error.message}`);
    console.error(error.stack);
  }

  db.close();
}

testMCPHybridSearch().catch(error => {
  console.error(`\n❌ E2E test failed: ${error.message}`);
  console.error(error.stack);
  process.exit(1);
});
