const sqlite3 = require('sqlite3');

const db = new sqlite3.Database(':memory:');

// Check if loadExtension method exists
console.log('loadExtension method exists:', typeof db.loadExtension === 'function');

// Try to check if extension loading is enabled
db.serialize(() => {
  db.all("PRAGMA compile_options", (err, rows) => {
    if (err) {
      console.error('Error checking compile options:', err.message);
    } else {
      console.log('\nSQLite compile options:');
      const relevant = rows.filter(r => 
        r.compile_option.includes('ENABLE_LOAD_EXTENSION') ||
        r.compile_option.includes('OMIT_LOAD_EXTENSION')
      );
      
      if (relevant.length > 0) {
        relevant.forEach(r => console.log('  -', r.compile_option));
      } else {
        console.log('  (no explicit extension loading flags found - may be enabled by default)');
      }
    }
    db.close();
  });
});
