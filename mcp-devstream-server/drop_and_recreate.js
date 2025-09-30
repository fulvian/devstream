const Database = require('better-sqlite3');
const sqliteVec = require('sqlite-vec');

const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');
sqliteVec.load(db);

console.log('Dropping old vec_semantic_memory table...');
db.prepare('DROP TABLE IF EXISTS vec_semantic_memory').run();
console.log('✅ Table dropped\n');

console.log('Creating new vec0 table without explicit primary key column name...');
db.prepare(`
  CREATE VIRTUAL TABLE vec_semantic_memory USING vec0(
    embedding float[768],
    content_type TEXT PARTITION KEY,
    relevance_score FLOAT,
    created_at TEXT,
    +memory_id TEXT,
    +content_preview TEXT
  )
`).run();

console.log('✅ vec0 table created\n');

// Check schema
const info = db.prepare('PRAGMA table_info(vec_semantic_memory)').all();
console.log('Columns:');
info.forEach(col => {
  console.log(`  ${col.name} (${col.type || 'virtual'})`);
});

db.close();
