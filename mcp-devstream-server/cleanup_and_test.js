const Database = require('better-sqlite3');
const sqliteVec = require('sqlite-vec');

const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');
sqliteVec.load(db);

console.log('🧹 Cleaning up existing test data...');
db.prepare('DELETE FROM vec_semantic_memory').run();
console.log('✅ Table cleared\n');

console.log('📊 Testing vec0 with fresh data...\n');

// Get multiple memories with embeddings
const memories = db.prepare(`
  SELECT rowid, id, content, content_type, embedding, relevance_score, created_at
  FROM semantic_memory
  WHERE embedding IS NOT NULL
  LIMIT 5
`).all();

console.log(`Found ${memories.length} memories with embeddings\n`);

// Insert all memories
console.log('📥 Inserting vectors...');
const insertStmt = db.prepare(`
  INSERT INTO vec_semantic_memory(
    rowid,
    embedding,
    content_type,
    relevance_score,
    created_at,
    memory_id,
    content_preview
  ) VALUES (?, ?, ?, ?, ?, ?, ?)
`);

for (const memory of memories) {
  const embeddingArray = JSON.parse(memory.embedding);
  const float32 = new Float32Array(embeddingArray);
  const buffer = Buffer.from(float32.buffer);
  
  insertStmt.run(
    memory.rowid,
    buffer,
    memory.content_type,
    memory.relevance_score || 0.0,
    memory.created_at,
    memory.id,
    memory.content.substring(0, 200)
  );
  console.log(`  ✓ Inserted: ${memory.id} (${memory.content_type})`);
}

// Verify insertions
console.log('\n📊 Verification:');
const count = db.prepare('SELECT COUNT(*) as count FROM vec_semantic_memory').get();
console.log(`Total vectors in table: ${count.count}`);

// Test vector similarity search
console.log('\n🔍 Testing vector similarity search...');
const queryMemory = memories[0];
const queryArray = JSON.parse(queryMemory.embedding);
const queryFloat32 = new Float32Array(queryArray);
const queryBuffer = Buffer.from(queryFloat32.buffer);

const similar = db.prepare(`
  SELECT
    memory_rowid,
    content_type,
    memory_id,
    content_preview,
    distance
  FROM vec_semantic_memory
  WHERE embedding MATCH ?
  ORDER BY distance
  LIMIT 5
`).all(queryBuffer);

console.log(`\nQuery: ${queryMemory.id}`);
console.log(`Results: ${similar.length} similar vectors\n`);

similar.forEach((s, i) => {
  console.log(`${i + 1}. ${s.memory_id}`);
  console.log(`   Type: ${s.content_type}`);
  console.log(`   Distance: ${s.distance.toFixed(6)}`);
  console.log(`   Preview: ${s.content_preview.substring(0, 80)}...`);
  console.log();
});

db.close();
console.log('✅ All tests completed successfully!');
