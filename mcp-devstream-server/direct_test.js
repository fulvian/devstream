const sqlite3 = require('sqlite3');
const path = require('path');

const dbPath = '/Users/fulvioventura/devstream/data/devstream.db';
const extPath = '/Users/fulvioventura/devstream/sqlite-extensions/vec0.dylib';

console.log('Creating database connection...');
const db = new sqlite3.Database(dbPath, sqlite3.OPEN_READWRITE, (err) => {
  if (err) {
    console.error('Connection error:', err);
    process.exit(1);
  }
  
  console.log('✅ Connected');
  console.log('Checking if loadExtension exists:', typeof db.loadExtension);
  
  if (typeof db.loadExtension !== 'function') {
    console.error('❌ loadExtension method not available');
    db.close();
    process.exit(1);
  }
  
  console.log('Attempting to load extension...');
  
  // Try with a callback timeout
  let callbackCalled = false;
  const timeout = setTimeout(() => {
    if (!callbackCalled) {
      console.error('⚠️ loadExtension callback never called - likely hanging');
      process.exit(1);
    }
  }, 3000);
  
  db.loadExtension(extPath, (err) => {
    callbackCalled = true;
    clearTimeout(timeout);
    
    if (err) {
      console.error('❌ Extension load error:', err.message);
      db.close();
      process.exit(1);
    }
    
    console.log('✅ Extension loaded successfully');
    
    // Verify it works
    db.get('SELECT vec_version()', (err, row) => {
      if (err) {
        console.error('❌ vec_version() error:', err.message);
      } else {
        console.log('✅ vec_version():', row);
      }
      
      db.close((err) => {
        if (err) console.error('Close error:', err);
        console.log('Test complete');
        process.exit(0);
      });
    });
  });
});
