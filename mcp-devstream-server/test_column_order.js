const Database = require('better-sqlite3');
const sqliteVec = require('sqlite-vec');

const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');
sqliteVec.load(db);

const memory = db.prepare(`
  SELECT rowid, id, content, content_type, embedding
  FROM semantic_memory
  WHERE embedding IS NOT NULL
  LIMIT 1
`).get();

console.log('Test: Different column orders\n');

// Test 1: embedding FIRST (before rowid)
console.log('Test 1: Embedding first, then rowid');
try {
  db.prepare(`
    INSERT INTO vec_semantic_memory(embedding, rowid, content_type)
    VALUES (?, ?, ?)
  `).run(memory.embedding, memory.rowid, memory.content_type);
  console.log('✅ Success!\n');
} catch (error) {
  console.log('❌ Error:', error.message, '\n');
}

// Test 2: ALL columns in schema order
console.log('Test 2: All columns in schema order');
try {
  db.prepare(`
    INSERT INTO vec_semantic_memory(embedding, content_type, memory_id, content_preview)
    VALUES (?, ?, ?, ?)
  `).run(memory.embedding, memory.content_type, memory.id, memory.content.substring(0, 200));
  console.log('✅ Success!\n');
  console.log('Checking inserted data...');
  const result = db.prepare('SELECT * FROM vec_semantic_memory LIMIT 1').get();
  console.log('Result:', result);
} catch (error) {
  console.log('❌ Error:', error.message, '\n');
}

db.close();
