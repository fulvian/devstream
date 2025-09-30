const Database = require('better-sqlite3');

const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');

console.log('📝 Creating FTS5 virtual table for semantic_memory...\n');

// Drop existing table if any
try {
  db.prepare('DROP TABLE IF EXISTS fts_semantic_memory').run();
  console.log('✓ Dropped existing FTS5 table\n');
} catch (error) {
  console.log('No existing FTS5 table to drop\n');
}

// Create FTS5 virtual table
// Context7 pattern: Use unicode61 tokenizer with remove_diacritics for multilingual support
db.prepare(`
  CREATE VIRTUAL TABLE fts_semantic_memory USING fts5(
    content,
    content_type UNINDEXED,
    memory_id UNINDEXED,
    created_at UNINDEXED,
    tokenize='unicode61 remove_diacritics 2'
  )
`).run();

console.log('✅ FTS5 table created successfully\n');

// Verify table structure
const tableInfo = db.prepare("SELECT * FROM pragma_module_list WHERE name='fts5'").get();
console.log('FTS5 module available:', tableInfo ? 'Yes' : 'No');

// Test insertion
console.log('\n📥 Testing FTS5 insertion...\n');

const testMemories = db.prepare(`
  SELECT rowid, id, content, content_type, created_at
  FROM semantic_memory
  LIMIT 5
`).all();

const insertStmt = db.prepare(`
  INSERT INTO fts_semantic_memory(rowid, content, content_type, memory_id, created_at)
  VALUES (?, ?, ?, ?, ?)
`);

for (const memory of testMemories) {
  insertStmt.run(
    memory.rowid,
    memory.content,
    memory.content_type,
    memory.id,
    memory.created_at
  );
  console.log(`  ✓ ${memory.id} (${memory.content_type})`);
}

// Verify insertion
const count = db.prepare('SELECT COUNT(*) as count FROM fts_semantic_memory').get();
console.log(`\n📊 Total indexed documents: ${count.count}`);

// Test full-text search
console.log('\n🔍 Testing full-text search...\n');

const searchQueries = [
  'embedding generation',
  'vector search',
  'Claude Code'
];

for (const query of searchQueries) {
  const results = db.prepare(`
    SELECT memory_id, content_type, snippet(fts_semantic_memory, 0, '<b>', '</b>', '...', 32) as snippet
    FROM fts_semantic_memory
    WHERE fts_semantic_memory MATCH ?
    LIMIT 3
  `).all(query);
  
  console.log(`Query: "${query}"`);
  console.log(`Results: ${results.length}`);
  
  results.forEach((r, i) => {
    console.log(`  ${i + 1}. ${r.memory_id} (${r.content_type})`);
    console.log(`     ${r.snippet}\n`);
  });
}

db.close();
console.log('✅ Phase A4 complete - FTS5 table working correctly!');
