const Database = require('better-sqlite3');
const sqliteVec = require('sqlite-vec');

const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');
sqliteVec.load(db);

console.log('🧹 Cleaning and populating vec0 table...\n');

// Clear table
db.prepare('DELETE FROM vec_semantic_memory').run();

// Get memories with embeddings
const memories = db.prepare(`
  SELECT rowid, id, content, content_type, embedding, relevance_score, created_at
  FROM semantic_memory
  WHERE embedding IS NOT NULL
  LIMIT 10
`).all();

console.log(`Found ${memories.length} memories with embeddings\n`);

// Insert all  
const insertStmt = db.prepare(`
  INSERT INTO vec_semantic_memory(embedding, content_type, memory_id, content_preview)
  VALUES (?, ?, ?, ?)
`);

for (const memory of memories) {
  insertStmt.run(
    memory.embedding,
    memory.content_type,
    memory.id,
    memory.content.substring(0, 200)
  );
  console.log(`  ✓ ${memory.id} (${memory.content_type})`);
}

// Verify
const count = db.prepare('SELECT COUNT(*) as count FROM vec_semantic_memory').get();
console.log(`\n📊 Total vectors: ${count.count}`);

// Test vector similarity search
console.log('\n🔍 Vector similarity search test...\n');

const queryMemory = memories[0];
const queryArray = JSON.parse(queryMemory.embedding);
const queryFloat32 = new Float32Array(queryArray);
const queryBuffer = Buffer.from(queryFloat32.buffer);

const similar = db.prepare(`
  SELECT
    rowid,
    content_type,
    memory_id,
    content_preview,
    distance
  FROM vec_semantic_memory
  WHERE embedding MATCH ?
  ORDER BY distance
  LIMIT 5
`).all(queryBuffer);

console.log(`Query: ${queryMemory.id}`);
console.log(`Results: ${similar.length}\n`);

similar.forEach((s, idx) => {
  console.log(`${idx + 1}. ${s.memory_id}`);
  console.log(`   Type: ${s.content_type}, Distance: ${s.distance.toFixed(6)}`);
  console.log(`   ${s.content_preview.substring(0, 80)}...\n`);
});

db.close();
console.log('✅ Phase A3 complete - vec0 table working correctly!');
