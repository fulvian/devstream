const Database = require('better-sqlite3');
const sqliteVec = require('sqlite-vec');

const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');
sqliteVec.load(db);

console.log('📊 Testing vec0 table with existing embeddings...\n');

// Get one memory with embedding
const memory = db.prepare(`
  SELECT rowid, id, content, content_type, embedding, relevance_score, created_at
  FROM semantic_memory
  WHERE embedding IS NOT NULL
  LIMIT 1
`).get();

if (!memory) {
  console.log('❌ No memories with embeddings found');
  process.exit(1);
}

console.log('Found memory:', memory.id);
console.log('Content type:', memory.content_type);
console.log('Embedding length:', memory.embedding ? memory.embedding.length : 0, 'chars (JSON)');

// Parse embedding from JSON
const embeddingArray = JSON.parse(memory.embedding);
console.log('Embedding dimensions:', embeddingArray.length);

// Convert to Float32Array and Buffer
const float32 = new Float32Array(embeddingArray);
const buffer = Buffer.from(float32.buffer);

console.log('Buffer size:', buffer.length, 'bytes');
console.log('Expected:', 768 * 4, 'bytes (768 floats x 4 bytes)');

// Insert into vec0 table
console.log('\n📥 Inserting into vec_semantic_memory...');

try {
  // Ensure rowid is an integer
  const rowid = parseInt(memory.rowid);
  console.log('Using rowid:', rowid);

  db.prepare(`
    INSERT INTO vec_semantic_memory (
      memory_rowid,
      embedding,
      content_type,
      relevance_score,
      created_at,
      memory_id,
      content_preview
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
  `).run(
    rowid,
    buffer,
    memory.content_type,
    memory.relevance_score || 0.0,
    memory.created_at,
    memory.id,
    memory.content.substring(0, 200)
  );

  console.log('✅ Vector inserted successfully');

  // Query it back
  const result = db.prepare(`
    SELECT
      memory_rowid,
      content_type,
      relevance_score,
      memory_id,
      content_preview
    FROM vec_semantic_memory
    WHERE memory_rowid = ?
  `).get(rowid);

  console.log('\n📤 Query result:');
  console.log(result);

  // Test vector search
  console.log('\n🔍 Testing vector similarity search...');
  const similar = db.prepare(`
    SELECT
      memory_rowid,
      content_type,
      memory_id,
      distance
    FROM vec_semantic_memory
    WHERE embedding MATCH ?
    ORDER BY distance
    LIMIT 5
  `).all(buffer);

  console.log('Similar vectors found:', similar.length);
  similar.forEach((s, i) => {
    console.log(`  ${i + 1}. ${s.memory_id} (${s.content_type}) - distance: ${s.distance}`);
  });

} catch (error) {
  console.error('❌ Error:', error.message);
  process.exit(1);
} finally {
  db.close();
}