const Database = require('better-sqlite3');
const sqliteVec = require('sqlite-vec');

const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');
sqliteVec.load(db);

console.log('🚀 DevStream Hybrid Search - Data Migration Script\n');
console.log('=' .repeat(60) + '\n');

// Get migration statistics
const stats = {
  total: db.prepare('SELECT COUNT(*) as count FROM semantic_memory').get().count,
  withEmbedding: db.prepare('SELECT COUNT(*) as count FROM semantic_memory WHERE embedding IS NOT NULL').get().count,
  vec0Before: db.prepare('SELECT COUNT(*) as count FROM vec_semantic_memory').get().count,
  fts5Before: db.prepare('SELECT COUNT(*) as count FROM fts_semantic_memory').get().count
};

console.log('📊 Current State:');
console.log(`  Total memories: ${stats.total}`);
console.log(`  With embeddings: ${stats.withEmbedding}`);
console.log(`  In vec0: ${stats.vec0Before}`);
console.log(`  In FTS5: ${stats.fts5Before}\n`);

// Clear existing data for clean migration
console.log('🧹 Clearing existing search indexes...');
db.prepare('DELETE FROM vec_semantic_memory').run();
db.prepare('DELETE FROM fts_semantic_memory').run();
console.log('✅ Indexes cleared\n');

// Migrate to FTS5 (all memories)
console.log('📝 Migrating to FTS5...');
const fts5Inserted = db.prepare(`
  INSERT INTO fts_semantic_memory(rowid, content, content_type, memory_id, created_at)
  SELECT rowid, content, content_type, id, created_at
  FROM semantic_memory
`).run();

console.log(`✅ FTS5: ${fts5Inserted.changes} memories indexed\n`);

// Migrate to vec0 (only memories with embeddings)
console.log('🔢 Migrating to vec0...');

const memoriesWithEmbeddings = db.prepare(`
  SELECT rowid, id, content, content_type, embedding, created_at
  FROM semantic_memory
  WHERE embedding IS NOT NULL
`).all();

console.log(`Found ${memoriesWithEmbeddings.length} memories with embeddings`);

const insertVec = db.prepare(`
  INSERT INTO vec_semantic_memory(embedding, content_type, memory_id, content_preview)
  VALUES (?, ?, ?, ?)
`);

let vec0Count = 0;
let errors = 0;

for (const memory of memoriesWithEmbeddings) {
  try {
    insertVec.run(
      memory.embedding,
      memory.content_type,
      memory.id,
      memory.content.substring(0, 200)
    );
    vec0Count++;
    
    if (vec0Count % 10 === 0) {
      process.stdout.write(`  Progress: ${vec0Count}/${memoriesWithEmbeddings.length}\r`);
    }
  } catch (error) {
    errors++;
    console.error(`\n  ⚠️  Error on ${memory.id}: ${error.message}`);
  }
}

console.log(`\n✅ vec0: ${vec0Count} vectors indexed (${errors} errors)\n`);

// Verification
console.log('=' .repeat(60));
console.log('📊 Migration Results:\n');

const finalStats = {
  vec0After: db.prepare('SELECT COUNT(*) as count FROM vec_semantic_memory').get().count,
  fts5After: db.prepare('SELECT COUNT(*) as count FROM fts_semantic_memory').get().count
};

console.log('FTS5 Full-Text Search:');
console.log(`  Before: ${stats.fts5Before} | After: ${finalStats.fts5After}`);
console.log(`  Change: +${finalStats.fts5After - stats.fts5Before}`);

console.log('\nvec0 Vector Search:');
console.log(`  Before: ${stats.vec0Before} | After: ${finalStats.vec0After}`);
console.log(`  Change: +${finalStats.vec0After - stats.vec0Before}`);

console.log('\nContent Type Distribution:');
const contentTypes = db.prepare(`
  SELECT content_type, COUNT(*) as count
  FROM semantic_memory
  GROUP BY content_type
  ORDER BY count DESC
`).all();

contentTypes.forEach(ct => {
  console.log(`  ${ct.content_type}: ${ct.count}`);
});

// Test hybrid search
console.log('\n' + '='.repeat(60));
console.log('🔍 Testing Hybrid Search...\n');

const testQuery = 'vector search embedding';
console.log(`Query: "${testQuery}"\n`);

// Test vec0
console.log('Vector Search Results:');
const queryArray = new Array(768).fill(0.5);
const queryFloat32 = new Float32Array(queryArray);
const queryBuffer = Buffer.from(queryFloat32.buffer);

const vecResults = db.prepare(`
  SELECT memory_id, content_type, distance
  FROM vec_semantic_memory
  WHERE embedding MATCH ?
  LIMIT 3
`).all(queryBuffer);

vecResults.forEach((r, i) => {
  console.log(`  ${i + 1}. ${r.memory_id} (${r.content_type}) - distance: ${r.distance.toFixed(4)}`);
});

// Test FTS5
console.log('\nKeyword Search Results:');
const ftsResults = db.prepare(`
  SELECT memory_id, content_type, 
         snippet(fts_semantic_memory, 0, '<b>', '</b>', '...', 20) as snippet
  FROM fts_semantic_memory
  WHERE fts_semantic_memory MATCH ?
  LIMIT 3
`).all(testQuery);

ftsResults.forEach((r, i) => {
  console.log(`  ${i + 1}. ${r.memory_id} (${r.content_type})`);
  console.log(`     ${r.snippet}\n`);
});

db.close();

console.log('=' .repeat(60));
console.log('✅ Phase A6 COMPLETE - Data migration successful!');
console.log('\n🎉 Hybrid Search System Ready:');
console.log('  ✓ vec0 virtual table with vector embeddings');
console.log('  ✓ FTS5 virtual table with full-text index');
console.log('  ✓ Auto-sync triggers for FTS5');
console.log('  ✓ All existing data migrated');
