const Database = require('better-sqlite3');
const sqliteVec = require('sqlite-vec');

const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');
sqliteVec.load(db);

const memory = db.prepare(`
  SELECT rowid, id, embedding
  FROM semantic_memory
  WHERE embedding IS NOT NULL
  LIMIT 1
`).get();

const embeddingArray = JSON.parse(memory.embedding);
const float32 = new Float32Array(embeddingArray);
const buffer = Buffer.from(float32.buffer);

console.log('Testing different parameter binding methods...\n');

// Test 1: Named parameters
console.log('Test 1: Named parameters');
try {
  db.prepare(`
    INSERT INTO vec_semantic_memory(rowid, embedding, content_type)
    VALUES (@rowid, @embedding, @contentType)
  `).run({
    rowid: memory.rowid,
    embedding: buffer,
    contentType: 'test'
  });
  console.log('  ✅ Success with named parameters\n');
} catch (error) {
  console.log(`  ❌ Error: ${error.message}\n`);
}

db.close();
