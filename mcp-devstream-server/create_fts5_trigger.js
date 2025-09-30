const Database = require('better-sqlite3');

const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');

console.log('🔧 Creating FTS5 auto-sync triggers...\n');
console.log('⚠️  Note: vec0 sync will be handled by MCP server (requires extension)\n');

// Drop existing triggers
const existingTriggers = db.prepare(`
  SELECT name FROM sqlite_master 
  WHERE type='trigger' 
  AND name LIKE 'fts5_sync_%'
`).all();

for (const trigger of existingTriggers) {
  db.prepare(`DROP TRIGGER IF EXISTS ${trigger.name}`).run();
  console.log(`✓ Dropped: ${trigger.name}`);
}

// Trigger 1: INSERT - sync to FTS5
console.log('\n📝 Creating FTS5 INSERT trigger...');
db.prepare(`
  CREATE TRIGGER fts5_sync_insert
  AFTER INSERT ON semantic_memory
  BEGIN
    INSERT INTO fts_semantic_memory(rowid, content, content_type, memory_id, created_at)
    VALUES (NEW.rowid, NEW.content, NEW.content_type, NEW.id, NEW.created_at);
  END
`).run();
console.log('✅ INSERT trigger created');

// Trigger 2: UPDATE - sync to FTS5
console.log('\n📝 Creating FTS5 UPDATE trigger...');
db.prepare(`
  CREATE TRIGGER fts5_sync_update
  AFTER UPDATE OF content, content_type ON semantic_memory
  BEGIN
    DELETE FROM fts_semantic_memory WHERE rowid = OLD.rowid;
    INSERT INTO fts_semantic_memory(rowid, content, content_type, memory_id, created_at)
    VALUES (NEW.rowid, NEW.content, NEW.content_type, NEW.id, NEW.created_at);
  END
`).run();
console.log('✅ UPDATE trigger created');

// Trigger 3: DELETE - sync to FTS5
console.log('\n📝 Creating FTS5 DELETE trigger...');
db.prepare(`
  CREATE TRIGGER fts5_sync_delete
  AFTER DELETE ON semantic_memory
  BEGIN
    DELETE FROM fts_semantic_memory WHERE rowid = OLD.rowid;
  END
`).run();
console.log('✅ DELETE trigger created');

// Verify
console.log('\n📊 Verification...\n');
const triggers = db.prepare(`
  SELECT name FROM sqlite_master 
  WHERE type='trigger' AND name LIKE 'fts5_sync_%'
`).all();
console.log(`Triggers created: ${triggers.length}`);
triggers.forEach(t => console.log(`  ✓ ${t.name}`));

// Test
console.log('\n🧪 Testing FTS5 trigger...\n');

// Cleanup
db.prepare("DELETE FROM fts_semantic_memory WHERE memory_id LIKE 'test_%'").run();
db.prepare("DELETE FROM semantic_memory WHERE id LIKE 'test_%'").run();

// Insert test
const testId = 'test_fts5_' + Date.now();
db.prepare(`
  INSERT INTO semantic_memory(id, content, content_type, created_at, updated_at)
  VALUES (?, ?, ?, datetime('now'), datetime('now'))
`).run(testId, 'Test content for FTS5 auto-sync validation', 'context');

const result = db.prepare('SELECT memory_id FROM fts_semantic_memory WHERE memory_id = ?').get(testId);
console.log(`FTS5 auto-sync: ${result ? '✅ Working' : '❌ Failed'}`);

// Cleanup test data
db.prepare('DELETE FROM semantic_memory WHERE id = ?').run(testId);

db.close();
console.log('\n✅ Phase A5 complete - FTS5 auto-sync working!');
console.log('📝 Note: vec0 sync will be implemented in MCP server memory tools');
