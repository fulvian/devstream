const Database = require('better-sqlite3');
const sqliteVec = require('sqlite-vec');

const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');
sqliteVec.load(db);

console.log('Dropping and recreating vec0 table...\n');

db.prepare('DROP TABLE IF EXISTS vec_semantic_memory').run();

// Context7 pattern: All metadata columns should allow NULL by default
db.prepare(`
  CREATE VIRTUAL TABLE vec_semantic_memory USING vec0(
    embedding float[768],
    content_type TEXT PARTITION KEY,
    +memory_id TEXT,
    +content_preview TEXT
  )
`).run();

console.log('✅ Table created (removed relevance_score and created_at)\n');

// Test insertion
const memory = db.prepare(`
  SELECT rowid, id, content, content_type, embedding
  FROM semantic_memory
  WHERE embedding IS NOT NULL
  LIMIT 1
`).get();

console.log('Testing insertion...');
const info = db.prepare(`
  INSERT INTO vec_semantic_memory(rowid, embedding, content_type, memory_id, content_preview)
  VALUES (?, ?, ?, ?, ?)
`).run(
  memory.rowid,
  memory.embedding,
  memory.content_type,
  memory.id,
  memory.content.substring(0, 200)
);

console.log('✅ Insert successful!');
console.log('Row ID:', info.lastInsertRowid || memory.rowid);

db.close();
