const Database = require('better-sqlite3');

console.log('Testing simpler sqlite-vec build...\n');

try {
  console.log('1. Opening database...');
  const db = new Database(':memory:');
  console.log('✅ Database opened');
  
  console.log('\n2. Loading extension...');
  db.loadExtension('/Users/fulvioventura/devstream/sqlite-extensions/vec0-simple.dylib');
  console.log('✅ Extension loaded');
  
  console.log('\n3. Testing vec_version()...');
  const result = db.prepare('SELECT vec_version() as version').get();
  console.log('✅ vec_version():', result.version);
  
  console.log('\n4. Closing database...');
  db.close();
  console.log('✅ Database closed');
  
  console.log('\n🎉 SUCCESS!');
  process.exit(0);
} catch (error) {
  console.error('\n❌ Failed:', error.message);
  process.exit(1);
}
