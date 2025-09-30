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

console.log('Testing INSERT without explicit rowid...\n');

try {
  // Let SQLite auto-assign rowid
  const info = db.prepare(`
    INSERT INTO vec_semantic_memory(embedding, content_type)
    VALUES (?, ?)
  `).run(memory.embedding, memory.content_type);
  
  console.log('✅ Insert successful!');
  console.log('Auto-assigned rowid:', info.lastInsertRowid);
  
  // Query it back
  const result = db.prepare(`
    SELECT rowid, content_type
    FROM vec_semantic_memory
    WHERE rowid = ?
  `).get(info.lastInsertRowid);
  
  console.log('\nQuery result:', result);
  
} catch (error) {
  console.log('❌ Error:', error.message);
}

db.close();
