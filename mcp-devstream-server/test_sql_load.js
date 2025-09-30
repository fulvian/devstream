const { DevStreamDatabase } = require('./dist/database.js');

async function test() {
  const db = new DevStreamDatabase('/Users/fulvioventura/devstream/data/devstream.db');
  
  try {
    console.log('1. Initializing database...');
    await db.initialize();
    console.log('✅ Database initialized');
    
    console.log('\n2. Loading extension via SQL...');
    await db.loadExtension('/Users/fulvioventura/devstream/sqlite-extensions/vec0.dylib');
    console.log('✅ Extension loaded');
    
    console.log('\n3. Getting diagnostics...');
    const diagnostics = await db.getVectorSearchDiagnostics();
    console.log('Diagnostics:', JSON.stringify(diagnostics, null, 2));
    
    console.log('\n4. Closing database...');
    await db.close();
    console.log('✅ Test completed successfully');
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    process.exit(1);
  }
}

test();
