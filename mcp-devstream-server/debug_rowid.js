const Database = require('better-sqlite3');
const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');

const memory = db.prepare(`
  SELECT rowid, id, typeof(rowid) as rowid_type
  FROM semantic_memory
  WHERE embedding IS NOT NULL
  LIMIT 1
`).get();

console.log('rowid value:', memory.rowid);
console.log('rowid type in JS:', typeof memory.rowid);
console.log('rowid type in SQLite:', memory.rowid_type);
console.log('parseInt result:', parseInt(memory.rowid));
console.log('parseInt type:', typeof parseInt(memory.rowid));
console.log('Number result:', Number(memory.rowid));
console.log('Number type:', typeof Number(memory.rowid));

// Try BigInt conversion if rowid is returned as BigInt
if (typeof memory.rowid === 'bigint') {
  console.log('Converting BigInt to Number:', Number(memory.rowid));
}

db.close();
