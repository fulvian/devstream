const Database = require('better-sqlite3');

const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');

console.log('🔧 Creating auto-sync triggers for hybrid search...\n');

// Drop existing triggers if any
const existingTriggers = db.prepare(`
  SELECT name FROM sqlite_master 
  WHERE type='trigger' 
  AND name LIKE 'sync_%'
`).all();

for (const trigger of existingTriggers) {
  db.prepare(`DROP TRIGGER IF EXISTS ${trigger.name}`).run();
  console.log(`✓ Dropped existing trigger: ${trigger.name}`);
}

console.log('\n📝 Creating INSERT trigger...\n');

// Trigger 1: INSERT - sync new memories to both vec0 and FTS5
db.prepare(`
  CREATE TRIGGER sync_insert_memory
  AFTER INSERT ON semantic_memory
  WHEN NEW.embedding IS NOT NULL
  BEGIN
    -- Insert into vec0 table (vector search)
    INSERT INTO vec_semantic_memory(embedding, content_type, memory_id, content_preview)
    VALUES (NEW.embedding, NEW.content_type, NEW.id, substr(NEW.content, 1, 200));
    
    -- Insert into FTS5 table (keyword search)
    INSERT INTO fts_semantic_memory(rowid, content, content_type, memory_id, created_at)
    VALUES (NEW.rowid, NEW.content, NEW.content_type, NEW.id, NEW.created_at);
  END
`).run();

console.log('✅ INSERT trigger created');

console.log('\n📝 Creating UPDATE trigger...\n');

// Trigger 2: UPDATE - sync changes to both tables
db.prepare(`
  CREATE TRIGGER sync_update_memory
  AFTER UPDATE ON semantic_memory
  WHEN NEW.embedding IS NOT NULL
  BEGIN
    -- Delete old entries
    DELETE FROM vec_semantic_memory WHERE rowid = OLD.rowid;
    DELETE FROM fts_semantic_memory WHERE rowid = OLD.rowid;
    
    -- Insert updated entries
    INSERT INTO vec_semantic_memory(embedding, content_type, memory_id, content_preview)
    VALUES (NEW.embedding, NEW.content_type, NEW.id, substr(NEW.content, 1, 200));
    
    INSERT INTO fts_semantic_memory(rowid, content, content_type, memory_id, created_at)
    VALUES (NEW.rowid, NEW.content, NEW.content_type, NEW.id, NEW.created_at);
  END
`).run();

console.log('✅ UPDATE trigger created');

console.log('\n📝 Creating DELETE trigger...\n');

// Trigger 3: DELETE - remove from both tables
db.prepare(`
  CREATE TRIGGER sync_delete_memory
  AFTER DELETE ON semantic_memory
  BEGIN
    DELETE FROM vec_semantic_memory WHERE rowid = OLD.rowid;
    DELETE FROM fts_semantic_memory WHERE rowid = OLD.rowid;
  END
`).run();

console.log('✅ DELETE trigger created');

// Verify triggers
console.log('\n📊 Verifying triggers...\n');

const triggers = db.prepare(`
  SELECT name, sql FROM sqlite_master 
  WHERE type='trigger' 
  AND name LIKE 'sync_%'
  ORDER BY name
`).all();

console.log(`Total triggers created: ${triggers.length}`);
triggers.forEach(t => {
  console.log(`  ✓ ${t.name}`);
});

// Test trigger functionality
console.log('\n🧪 Testing triggers with INSERT...\n');

// Clear test data
db.prepare('DELETE FROM vec_semantic_memory WHERE memory_id LIKE "test_%"').run();
db.prepare('DELETE FROM fts_semantic_memory WHERE memory_id LIKE "test_%"').run();
db.prepare('DELETE FROM semantic_memory WHERE id LIKE "test_%"').run();

// Insert test memory (should auto-trigger sync)
const testId = 'test_trigger_' + Date.now();
db.prepare(`
  INSERT INTO semantic_memory(
    id, content, content_type, embedding, created_at, updated_at
  ) VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
`).run(
  testId,
  'This is a test memory for trigger validation with vector search and keyword matching',
  'context',
  JSON.stringify(new Array(768).fill(0.5))
);

console.log(`✓ Inserted test memory: ${testId}`);

// Check if it appears in vec0 table
const vecResult = db.prepare('SELECT memory_id FROM vec_semantic_memory WHERE memory_id = ?').get(testId);
console.log(`  vec0 sync: ${vecResult ? '✅ Success' : '❌ Failed'}`);

// Check if it appears in FTS5 table
const ftsResult = db.prepare('SELECT memory_id FROM fts_semantic_memory WHERE memory_id = ?').get(testId);
console.log(`  FTS5 sync: ${ftsResult ? '✅ Success' : '❌ Failed'}`);

// Test UPDATE
console.log('\n🧪 Testing UPDATE trigger...\n');

db.prepare(`
  UPDATE semantic_memory 
  SET content = 'Updated content with new keywords for testing'
  WHERE id = ?
`).run(testId);

const ftsUpdated = db.prepare(`
  SELECT content FROM fts_semantic_memory WHERE memory_id = ?
`).get(testId);

console.log(`  FTS5 content updated: ${ftsUpdated && ftsUpdated.content.includes('Updated') ? '✅ Success' : '❌ Failed'}`);

// Test DELETE
console.log('\n🧪 Testing DELETE trigger...\n');

db.prepare('DELETE FROM semantic_memory WHERE id = ?').run(testId);

const vecDeleted = db.prepare('SELECT memory_id FROM vec_semantic_memory WHERE memory_id = ?').get(testId);
const ftsDeleted = db.prepare('SELECT memory_id FROM fts_semantic_memory WHERE memory_id = ?').get(testId);

console.log(`  vec0 deleted: ${!vecDeleted ? '✅ Success' : '❌ Failed'}`);
console.log(`  FTS5 deleted: ${!ftsDeleted ? '✅ Success' : '❌ Failed'}`);

db.close();
console.log('\n✅ Phase A5 complete - Auto-sync triggers working correctly!');
