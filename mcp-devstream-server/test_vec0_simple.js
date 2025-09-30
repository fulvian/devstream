const Database = require('better-sqlite3');
const sqliteVec = require('sqlite-vec');

const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');
sqliteVec.load(db);

console.log('📊 Testing vec0 insertion following Context7 patterns...\n');

// Get one memory with embedding
const memory = db.prepare(`
  SELECT rowid, id, content, content_type, embedding, relevance_score, created_at
  FROM semantic_memory
  WHERE embedding IS NOT NULL
  LIMIT 1
`).get();

console.log('Found memory rowid:', memory.rowid);
console.log('Content type:', memory.content_type);

// Parse embedding and convert to Buffer
const embeddingArray = JSON.parse(memory.embedding);
const float32 = new Float32Array(embeddingArray);
const buffer = Buffer.from(float32.buffer);

console.log('Buffer size:', buffer.length, 'bytes\n');

// Context7 pattern: INSERT using rowid column, not the primary key column name
try {
  db.prepare(`
    INSERT INTO vec_semantic_memory(
      rowid,
      embedding,
      content_type,
      relevance_score,
      created_at,
      memory_id,
      content_preview
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
  `).run(
    memory.rowid,
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
    SELECT memory_rowid, content_type, memory_id, content_preview
    FROM vec_semantic_memory
    WHERE memory_rowid = ?
  `).get(memory.rowid);

  console.log('\n📤 Query result:');
  console.log(result);

  // Test vector similarity search
  console.log('\n🔍 Testing vector similarity search...');
  const similar = db.prepare(`
    SELECT memory_rowid, content_type, memory_id, distance
    FROM vec_semantic_memory
    WHERE embedding MATCH ?
    ORDER BY distance
    LIMIT 5
  `).all(buffer);

  console.log('Similar vectors found:', similar.length);
  similar.forEach((s, i) => {
    console.log(`  ${i + 1}. ${s.memory_id} (${s.content_type}) - distance: ${s.distance.toFixed(4)}`);
  });

} catch (error) {
  console.error('❌ Error:', error.message);
  process.exit(1);
} finally {
  db.close();
}
