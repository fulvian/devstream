const Database = require('better-sqlite3');
const sqliteVec = require('sqlite-vec');

const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');
sqliteVec.load(db);

// Create a simple test vector
const testVector = new Float32Array(768).fill(0.5);
const buffer = Buffer.from(testVector.buffer);

console.log('Test: Inserting with explicit integer rowid...\n');
console.log('rowid type:', typeof 1);
console.log('rowid value:', 1);
console.log('buffer type:', buffer.constructor.name);
console.log('buffer length:', buffer.length, 'bytes\n');

try {
  db.prepare(`
    INSERT INTO vec_semantic_memory(rowid, embedding, content_type)
    VALUES (?, ?, ?)
  `).run(1, buffer, 'test');
  console.log('✅ Insert successful!');
} catch (error) {
  console.log('❌ Error:', error.message);
}

db.close();
