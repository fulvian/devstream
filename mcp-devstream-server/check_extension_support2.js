const sqlite3 = require('sqlite3');

const db = new sqlite3.Database(':memory:');

db.serialize(() => {
  db.all("PRAGMA compile_options", (err, rows) => {
    if (err) {
      console.error('Error:', err.message);
    } else {
      console.log('All compile options:', rows.map(r => r.compile_option).join(', '));
    }
    db.close();
  });
});
