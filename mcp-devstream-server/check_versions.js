const Database = require('better-sqlite3');
const sqliteVec = require('sqlite-vec');
const path = require('path');

const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');
sqliteVec.load(db);

// Check sqlite-vec version
const vecVersion = db.prepare('SELECT vec_version() as version').get();
console.log('sqlite-vec version:', vecVersion.version);

// Check SQLite version
const sqliteVersion = db.prepare('SELECT sqlite_version() as version').get();
console.log('SQLite version:', sqliteVersion.version);

// Check better-sqlite3 version
const pkg = require('./package.json');
console.log('better-sqlite3 version:', pkg.dependencies['better-sqlite3']);
console.log('sqlite-vec npm version:', pkg.dependencies['sqlite-vec']);

db.close();
