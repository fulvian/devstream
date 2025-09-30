const Database = require('better-sqlite3');
const sqliteVec = require('sqlite-vec');

const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');
sqliteVec.load(db);

// Get memory with embedding
const memory = db.prepare(`
  SELECT rowid, id, content, content_type, embedding
  FROM semantic_memory
  WHERE embedding IS NOT NULL
  LIMIT 1
`).get();

console.log('Testing JSON string vector insertion...\n');
console.log('rowid:', memory.rowid);
console.log('memory_id:', memory.id);
console.log('content_type:', memory.content_type);
console.log('embedding length (JSON):', memory.embedding.length, 'chars\n');

try {
  // Test 1: Insert with JSON string vector
  db.prepare(`
    INSERT INTO vec_semantic_memory(rowid, embedding, content_type)
    VALUES (?, ?, ?)
  `).run(memory.rowid, memory.embedding, memory.content_type);
  
  console.log('✅ Insert successful with JSON string!\n');
  
  // Query it back
  const result = db.prepare(`
    SELECT rowid, content_type
    FROM vec_semantic_memory
    WHERE rowid = ?
  `).get(memory.rowid);
  
  console.log('Query result:', result);
  
  // Test vector search with buffer
  console.log('\n🔍 Testing vector search with buffer...');
  const embeddingArray = JSON.parse(memory.embedding);
  const float32 = new Float32Array(embeddingArray);
  const buffer = Buffer.from(float32.buffer);
  
  const similar = db.prepare(`
    SELECT rowid, content_type, distance
    FROM vec_semantic_memory
    WHERE embedding MATCH ?
    LIMIT 3
  `).all(buffer);
  
  console.log('Similar vectors found:', similar.length);
  similar.forEach((s, i) => {
    console.log(`  ${i + 1}. rowid=${s.rowid}, distance=${s.distance.toFixed(6)}`);
  });
  
} catch (error) {
  console.log('❌ Error:', error.message);
}

db.close();
