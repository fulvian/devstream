#!/usr/bin/env node
/**
 * Test MCP Server Embedding Storage
 * Verifica se l'MCP server salva correttamente gli embedding nel database
 */

const Database = require('better-sqlite3');
const axios = require('axios');

const DB_PATH = './data/devstream.db';

async function testEmbeddingGeneration() {
    console.log('🧪 Testing MCP Server Embedding Storage\n');

    // 1. Genera embedding via Ollama
    console.log('1️⃣ Generating embedding with Ollama...');
    const response = await axios.post('http://localhost:11434/api/embed', {
        model: 'embeddinggemma:300m',
        input: 'Test embedding storage verification'
    });

    const embedding = response.data.embeddings[0];
    console.log(`✅ Generated embedding: ${embedding.length} dimensions\n`);

    // 2. Crea record di test con embedding
    console.log('2️⃣ Inserting test record with embedding...');
    const db = new Database(DB_PATH);

    const embeddingJson = JSON.stringify(embedding);
    const testId = `test-${Date.now()}`;

    const insertStmt = db.prepare(`
        INSERT INTO semantic_memory (
            id, content, content_type, keywords,
            embedding, embedding_dimension, embedding_model,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    `);

    insertStmt.run(
        testId,
        'Test embedding storage verification',
        'test',
        'test,embedding,storage',
        embeddingJson,
        embedding.length,
        'embeddinggemma:300m'
    );

    console.log(`✅ Inserted record with id: ${testId}\n`);

    // 3. Verifica embedding in semantic_memory
    console.log('3️⃣ Checking semantic_memory table...');
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

    console.log('📊 semantic_memory record:');
    console.log(JSON.stringify(semanticRecord, null, 2));
    console.log('');

    // 4. Verifica se trigger ha popolato vec_semantic_memory
    console.log('4️⃣ Checking vec_semantic_memory table (trigger activation)...');
    const vecRecord = db.prepare(`
        SELECT memory_id, content_type,
               length(content_preview) as preview_length,
               vec_length(embedding) as vec_dimensions
        FROM vec_semantic_memory
        WHERE memory_id = ?
    `).get(testId);

    if (vecRecord) {
        console.log('✅ Trigger activated! vec_semantic_memory record:');
        console.log(JSON.stringify(vecRecord, null, 2));
    } else {
        console.log('❌ Trigger NOT activated - no record in vec_semantic_memory');
    }
    console.log('');

    // 5. Verifica embedding cleanup in semantic_memory
    console.log('5️⃣ Re-checking semantic_memory after trigger (should be NULL)...');
    const cleanedRecord = db.prepare(`
        SELECT id,
               CASE WHEN embedding IS NULL THEN 'NULL'
                    WHEN embedding = '' THEN 'EMPTY'
                    ELSE 'STILL_HAS_DATA'
               END as embedding_status
        FROM semantic_memory
        WHERE id = ?
    `).get(testId);

    console.log('📊 semantic_memory embedding after trigger:');
    console.log(JSON.stringify(cleanedRecord, null, 2));
    console.log('');

    // 6. Cleanup test record
    console.log('6️⃣ Cleaning up test records...');
    db.prepare('DELETE FROM semantic_memory WHERE id = ?').run(testId);
    db.prepare('DELETE FROM vec_semantic_memory WHERE memory_id = ?').run(testId);
    console.log('✅ Test records cleaned up\n');

    // 7. Results
    console.log('═══════════════════════════════════════════');
    console.log('📊 TEST RESULTS');
    console.log('═══════════════════════════════════════════');
    console.log(`Embedding Generated: ${embedding.length} dimensions`);
    console.log(`Saved to semantic_memory: ${semanticRecord.embedding_status}`);
    console.log(`Trigger Activated: ${vecRecord ? 'YES ✅' : 'NO ❌'}`);
    console.log(`Embedding Cleaned: ${cleanedRecord.embedding_status === 'NULL' ? 'YES ✅' : 'NO ❌'}`);
    console.log('═══════════════════════════════════════════\n');

    db.close();
}

testEmbeddingGeneration().catch(err => {
    console.error('❌ Test failed:', err);
    process.exit(1);
});
