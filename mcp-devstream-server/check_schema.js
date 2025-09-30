const Database = require('better-sqlite3');
const sqliteVec = require('sqlite-vec');

const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');
sqliteVec.load(db);

const info = db.prepare('PRAGMA table_info(vec_semantic_memory)').all();
console.log('vec_semantic_memory columns:');
info.forEach(col => {
  console.log(`  ${col.name} (${col.type})`);
});

db.close();
