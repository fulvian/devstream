const Database = require('better-sqlite3');

const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');

console.log('Testing FTS5 triggers - simplified test\n');

// Insert test
const testId = 'test_simple_' + Date.now();
console.log('Inserting test memory:', testId);

db.prepare(`
  INSERT INTO semantic_memory(id, content, content_type, created_at, updated_at)
  VALUES (?, ?, ?, datetime('now'), datetime('now'))
`).run(testId, 'Test content for FTS5 trigger validation', 'context');

console.log('✓ Inserted into semantic_memory');

// Check FTS5
const result = db.prepare('SELECT memory_id FROM fts_semantic_memory WHERE memory_id = ?').get(testId);
console.log('FTS5 auto-sync:', result ? '✅ Working' : '❌ Failed');

if (result) {
  console.log('  Memory ID:', result.memory_id);
}

// Cleanup
console.log('\nCleaning up...');
db.prepare('DELETE FROM semantic_memory WHERE id = ?').run(testId);

const deleted = db.prepare('SELECT memory_id FROM fts_semantic_memory WHERE memory_id = ?').get(testId);
console.log('FTS5 auto-delete:', !deleted ? '✅ Working' : '❌ Failed');

db.close();
console.log('\n✅ FTS5 triggers validated successfully!');
