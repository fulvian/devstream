#!/usr/bin/env node
/**
 * Test Complete Embedding Flow
 * Simula esattamente il flusso MCP server: Ollama → semantic_memory → trigger → vec_semantic_memory
 */

const Database = require('better-sqlite3');
const sqliteVec = require('sqlite-vec');
const axios = require('axios');

const DB_PATH = '../data/devstream.db';
const OLLAMA_URL = 'http://localhost:11434/api/embed';

async function testCompleteFlow() {
  console.log('🧪 Testing Complete Embedding Flow (MCP Server Simulation)\n');
  console.log('═'.repeat(70));

  // 1. Generate embedding with Ollama
  console.log('\n1️⃣  STEP 1: Generating embedding with Ollama...');
  const response = await axios.post(OLLAMA_URL, {
    model: 'embeddinggemma:300m',
    input: 'Test complete embedding flow verification'
  });

  const embedding = response.data.embeddings[0];
  console.log(`   ✅ Generated embedding: ${embedding.length} dimensions`);
  console.log(`   ✅ Type: ${typeof embedding}, isArray: ${Array.isArray(embedding)}`);
  console.log(`   ✅ First 3 values: [${embedding.slice(0, 3).map(v => v.toFixed(4)).join(', ')}]`);

  // 2. Connect to database and load sqlite-vec
  console.log('\n2️⃣  STEP 2: Connecting to database...');
  const db = new Database(DB_PATH);
  sqliteVec.load(db);
  console.log('   ✅ Database connected');
  console.log('   ✅ sqlite-vec extension loaded');

  // 3. Check triggers exist
  console.log('\n3️⃣  STEP 3: Verifying triggers...');
  const triggers = db.prepare(`
    SELECT name FROM sqlite_master
    WHERE type = 'trigger' AND tbl_name = 'semantic_memory'
  `).all();
  console.log(`   ✅ Found ${triggers.length} triggers:`);
  triggers.forEach(t => console.log(`      - ${t.name}`));

  // 4. Insert record with embedding (simulating MCP server)
  console.log('\n4️⃣  STEP 4: Inserting record with embedding...');
  const testId = `test-flow-${Date.now()}`;
  const embeddingJson = JSON.stringify(embedding);

  console.log(`   📝 Test ID: ${testId}`);
  console.log(`   📝 embedding JSON length: ${embeddingJson.length} chars`);
  console.log(`   📝 embedding JSON preview: ${embeddingJson.substring(0, 100)}...`);

  const insertStmt = db.prepare(`
    INSERT INTO semantic_memory (
      id, content, content_type, keywords,
      embedding, embedding_dimension, embedding_model,
      created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
  `);

  const insertResult = insertStmt.run(
    testId,
    'Test complete embedding flow verification',
    'test',
    'test,embedding,flow',
    embeddingJson,
    embedding.length,
    'embeddinggemma:300m'
  );

  console.log(`   ✅ Record inserted (changes: ${insertResult.changes})`);

  // 5. Check semantic_memory table
  console.log('\n5️⃣  STEP 5: Checking semantic_memory table...');
  const semanticRecord = db.prepare(`
    SELECT id, content_type,
           CASE WHEN embedding IS NULL THEN 'NULL'
                WHEN embedding = '' THEN 'EMPTY'
                ELSE 'HAS_DATA'
           END as embedding_status,
           length(embedding) as embedding_length,
           embedding_dimension
    FROM semantic_memory
    WHERE id = ?
  `).get(testId);

  console.log(`   📊 semantic_memory record:`);
  console.log(`      id: ${semanticRecord.id}`);
  console.log(`      embedding_status: ${semanticRecord.embedding_status}`);
  console.log(`      embedding_length: ${semanticRecord.embedding_length} chars`);
  console.log(`      embedding_dimension: ${semanticRecord.embedding_dimension}`);

  // 6. Check if trigger activated vec_semantic_memory
  console.log('\n6️⃣  STEP 6: Checking trigger activation (vec_semantic_memory)...');
  const vecRecord = db.prepare(`
    SELECT memory_id, content_type,
           length(content_preview) as preview_length,
           vec_length(embedding) as vec_dimensions
    FROM vec_semantic_memory
    WHERE memory_id = ?
  `).get(testId);

  if (vecRecord) {
    console.log(`   ✅ TRIGGER ACTIVATED! vec_semantic_memory record:`);
    console.log(`      memory_id: ${vecRecord.memory_id}`);
    console.log(`      content_type: ${vecRecord.content_type}`);
    console.log(`      preview_length: ${vecRecord.preview_length} chars`);
    console.log(`      vec_dimensions: ${vecRecord.vec_dimensions}`);
  } else {
    console.log(`   ❌ TRIGGER NOT ACTIVATED - no record in vec_semantic_memory`);
  }

  // 7. Re-check semantic_memory (embedding should be NULL after trigger cleanup)
  console.log('\n7️⃣  STEP 7: Re-checking semantic_memory (embedding cleanup)...');
  const cleanedRecord = db.prepare(`
    SELECT id,
           CASE WHEN embedding IS NULL THEN 'NULL'
                WHEN embedding = '' THEN 'EMPTY'
                ELSE 'STILL_HAS_DATA'
           END as embedding_status,
           length(embedding) as embedding_length
    FROM semantic_memory
    WHERE id = ?
  `).get(testId);

  console.log(`   📊 semantic_memory after trigger:`);
  console.log(`      embedding_status: ${cleanedRecord.embedding_status}`);
  console.log(`      embedding_length: ${cleanedRecord.embedding_length || 0} chars`);

  if (cleanedRecord.embedding_status === 'NULL') {
    console.log(`   ✅ Embedding cleanup successful (saves ~${Math.round(embeddingJson.length / 1024)} KB)`);
  } else {
    console.log(`   ⚠️  Embedding NOT cleaned (still has data)`);
  }

  // 8. Cleanup test records
  console.log('\n8️⃣  STEP 8: Cleaning up test records...');
  db.prepare('DELETE FROM semantic_memory WHERE id = ?').run(testId);
  db.prepare('DELETE FROM vec_semantic_memory WHERE memory_id = ?').run(testId);
  console.log('   ✅ Test records cleaned up');

  // 9. Final summary
  console.log('\n' + '═'.repeat(70));
  console.log('📊 TEST SUMMARY');
  console.log('═'.repeat(70));
  console.log(`Embedding Generated:      ${embedding.length}D with Ollama ✅`);
  console.log(`Saved to semantic_memory: ${semanticRecord.embedding_status === 'HAS_DATA' ? 'YES ✅' : 'NO ❌'}`);
  console.log(`Trigger Activated:        ${vecRecord ? 'YES ✅' : 'NO ❌'}`);
  console.log(`Embedding Cleaned:        ${cleanedRecord.embedding_status === 'NULL' ? 'YES ✅' : 'NO ❌'}`);
  console.log('═'.repeat(70));

  // 10. Conclusion
  if (vecRecord && cleanedRecord.embedding_status === 'NULL') {
    console.log('\n🎉 SUCCESS! Complete embedding flow works correctly:');
    console.log('   ✅ Ollama generates 768D embedding');
    console.log('   ✅ MCP server saves embedding as JSON');
    console.log('   ✅ Trigger converts JSON → BLOB in vec_semantic_memory');
    console.log('   ✅ Trigger cleans JSON from semantic_memory');
    console.log('\n💡 CONCLUSION: The embedding pipeline is FUNCTIONAL!');
    console.log('   Problem must be elsewhere (PostToolUse hook not executing?)');
  } else {
    console.log('\n❌ FAILURE! Embedding flow broken:');
    if (!vecRecord) {
      console.log('   ❌ Trigger did NOT activate');
      console.log('   💡 Check trigger conditions: WHEN NEW.embedding IS NOT NULL AND NEW.embedding != \'\'');
    }
    if (cleanedRecord.embedding_status !== 'NULL') {
      console.log('   ❌ Embedding cleanup did NOT work');
      console.log('   💡 Check trigger UPDATE statement');
    }
  }

  db.close();
}

testCompleteFlow().catch(err => {
  console.error('❌ Test failed:', err);
  process.exit(1);
});
