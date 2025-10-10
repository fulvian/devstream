#!/usr/bin/env node
/**
 * Manual Test Script for Vector Search Fix
 *
 * Tests the hybrid search system with real queries to verify:
 * 1. Search returns results (>0)
 * 2. RRF scores are valid
 * 3. Both vector and FTS5 results are combined
 */

import { DevStreamDatabase } from './mcp-devstream-server/dist/database.js';
import { HybridSearchEngine } from './mcp-devstream-server/dist/tools/hybrid-search.js';
import { getOllamaClient } from './mcp-devstream-server/dist/ollama-client.js';

async function runTests() {
  console.log('🧪 DevStream Vector Search Manual Test Suite\n');
  console.log('═'.repeat(70) + '\n');

  // Initialize database and search engine
  const db = new DevStreamDatabase('data/devstream.db');
  await db.initialize();

  const ollamaClient = getOllamaClient();
  const searchEngine = new HybridSearchEngine(db, ollamaClient);

  // Test 1: Search for known content
  console.log('📋 TEST 1: Search for "vector search FULL OUTER JOIN"');
  console.log('─'.repeat(70));
  try {
    const results1 = await searchEngine.search('vector search FULL OUTER JOIN', {
      k: 5,
      rrf_k: 60,
      weight_fts: 1.0,
      weight_vec: 1.0
    });

    console.log(`✅ Results found: ${results1.length}`);
    if (results1.length > 0) {
      console.log(`📊 Top result RRF score: ${results1[0].combined_rank.toFixed(4)}`);
      console.log(`🔍 Content preview: ${results1[0].content.substring(0, 100)}...`);
      console.log(`📈 Vector rank: ${results1[0].vec_rank || 'N/A'}`);
      console.log(`📈 FTS rank: ${results1[0].fts_rank || 'N/A'}`);
    } else {
      console.log('⚠️  No results found (unexpected!)');
    }
  } catch (error) {
    console.error(`❌ TEST 1 FAILED: ${error.message}`);
  }
  console.log('\n');

  // Test 2: Search for Context7 integration
  console.log('📋 TEST 2: Search for "Context7 integration DevStream"');
  console.log('─'.repeat(70));
  try {
    const results2 = await searchEngine.search('Context7 integration DevStream', {
      k: 5,
      rrf_k: 60,
      weight_fts: 1.0,
      weight_vec: 1.0
    });

    console.log(`✅ Results found: ${results2.length}`);
    if (results2.length > 0) {
      console.log(`📊 Top 3 RRF scores: ${results2.slice(0, 3).map(r => r.combined_rank.toFixed(4)).join(', ')}`);
      console.log(`🔍 Hybrid matches: ${results2.filter(r => r.vec_rank && r.fts_rank).length}`);
      console.log(`🔍 Vector-only matches: ${results2.filter(r => r.vec_rank && !r.fts_rank).length}`);
      console.log(`🔍 FTS-only matches: ${results2.filter(r => !r.vec_rank && r.fts_rank).length}`);
    }
  } catch (error) {
    console.error(`❌ TEST 2 FAILED: ${error.message}`);
  }
  console.log('\n');

  // Test 3: Search for session management
  console.log('📋 TEST 3: Search for "session summary cleanup"');
  console.log('─'.repeat(70));
  try {
    const results3 = await searchEngine.search('session summary cleanup', {
      k: 10,
      rrf_k: 60,
      weight_fts: 1.0,
      weight_vec: 1.0
    });

    console.log(`✅ Results found: ${results3.length}`);
    if (results3.length > 0) {
      console.log(`📊 RRF score range: ${results3[results3.length - 1].combined_rank.toFixed(4)} - ${results3[0].combined_rank.toFixed(4)}`);

      // Group by content type
      const byType = results3.reduce((acc, r) => {
        acc[r.content_type] = (acc[r.content_type] || 0) + 1;
        return acc;
      }, {});
      console.log(`📂 Results by type: ${JSON.stringify(byType)}`);
    }
  } catch (error) {
    console.error(`❌ TEST 3 FAILED: ${error.message}`);
  }
  console.log('\n');

  // Test 4: Get diagnostics
  console.log('📋 TEST 4: System Diagnostics');
  console.log('─'.repeat(70));
  try {
    const diagnostics = await searchEngine.getDiagnostics();
    console.log(`✅ Vector search available: ${diagnostics.vector_search.available}`);
    console.log(`📊 Total memories: ${diagnostics.total_memories}`);
    console.log(`🧠 Memories with embeddings: ${diagnostics.memories_with_embeddings}`);
    console.log(`📇 vec0 indexed: ${diagnostics.vec0_indexed}`);
    console.log(`📇 FTS5 indexed: ${diagnostics.fts5_indexed}`);
    if (diagnostics.vector_search.version) {
      console.log(`🔧 sqlite-vec version: ${diagnostics.vector_search.version}`);
    }
  } catch (error) {
    console.error(`❌ TEST 4 FAILED: ${error.message}`);
  }
  console.log('\n');

  // Close database
  await db.close();

  console.log('═'.repeat(70));
  console.log('✅ Manual test suite completed!\n');
  console.log('Expected results:');
  console.log('  - All tests should return >0 results');
  console.log('  - RRF scores should be in 0.01-1.0 range');
  console.log('  - Hybrid matches should combine vec_rank AND fts_rank');
  console.log('  - System diagnostics should show vector_search.available = true');
}

runTests().catch(error => {
  console.error('💥 Test suite failed:', error);
  process.exit(1);
});
