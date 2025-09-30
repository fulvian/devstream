const Database = require('better-sqlite3');

console.log('Testing better-sqlite3 with sqlite-vec extension...\n');

try {
  console.log('1. Opening database...');
  const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');
  console.log('✅ Database opened');
  
  console.log('\n2. Loading extension...');
  db.loadExtension('/Users/fulvioventura/devstream/sqlite-extensions/vec0.dylib');
  console.log('✅ Extension loaded');
  
  console.log('\n3. Testing vec_version()...');
  const result = db.prepare('SELECT vec_version() as version').get();
  console.log('✅ vec_version():', result.version);
  
  console.log('\n4. Closing database...');
  db.close();
  console.log('✅ Database closed');
  
  console.log('\n🎉 Test completed successfully!');
} catch (error) {
  console.error('\n❌ Test failed:', error.message);
  process.exit(1);
}
