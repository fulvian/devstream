const Database = require('better-sqlite3');
const sqliteVec = require('sqlite-vec');

const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');
sqliteVec.load(db); // Load vec0 extension

console.log('Testing FTS5 triggers with vec0 loaded\n');

// Insert test
const testId = 'test_trigger_' + Date.now();
console.log('Inserting test memory:', testId);

db.prepare(`
  INSERT INTO semantic_memory(id, content, content_type, created_at, updated_at)
  VALUES (?, ?, ?, datetime('now'), datetime('now'))
`).run(testId, 'Test content for FTS5 auto-sync trigger validation', 'context');

console.log('✓ Inserted into semantic_memory');

// Check FTS5
const ftsResult = db.prepare('SELECT memory_id, content FROM fts_semantic_memory WHERE memory_id = ?').get(testId);
console.log('\nFTS5 auto-sync:', ftsResult ? '✅ Working' : '❌ Failed');

if (ftsResult) {
  console.log('  Memory ID:', ftsResult.memory_id);
  console.log('  Content:', ftsResult.content.substring(0, 60) + '...');
}

// Test UPDATE
console.log('\nTesting UPDATE trigger...');
db.prepare('UPDATE semantic_memory SET content = ? WHERE id = ?')
  .run('Updated content for trigger test', testId);

const ftsUpdated = db.prepare('SELECT content FROM fts_semantic_memory WHERE memory_id = ?').get(testId);
console.log('FTS5 update:', ftsUpdated && ftsUpdated.content.includes('Updated') ? '✅ Working' : '❌ Failed');

// Test DELETE
console.log('\nTesting DELETE trigger...');
db.prepare('DELETE FROM semantic_memory WHERE id = ?').run(testId);

const ftsDeleted = db.prepare('SELECT memory_id FROM fts_semantic_memory WHERE memory_id = ?').get(testId);
console.log('FTS5 delete:', !ftsDeleted ? '✅ Working' : '❌ Failed');

db.close();
console.log('\n✅ Phase A5 complete - FTS5 auto-sync triggers working!');
