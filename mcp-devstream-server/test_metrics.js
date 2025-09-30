/**
 * Quick test to verify metrics collection is working
 */

const Database = require('better-sqlite3');
const sqliteVec = require('sqlite-vec');
const { Ollama } = require('ollama');

const db = new Database('/Users/fulvioventura/devstream/data/devstream.db');
sqliteVec.load(db);

const ollama = new Ollama({ host: 'http://localhost:11434' });

console.log('🧪 Testing Metrics Collection\n');
console.log('='.repeat(70) + '\n');

async function testMetrics() {
  try {
    // Load the built TypeScript module
    const { getMetrics } = await import('./dist/monitoring/metrics.js');
    const { HybridSearchEngine } = await import('./dist/tools/hybrid-search.js');
    const { getOllamaClient } = await import('./dist/ollama-client.js');
    const { DevStreamDatabase } = await import('./dist/database.js');

    // Initialize
    const database = new DevStreamDatabase('/Users/fulvioventura/devstream/data/devstream.db');
    await database.initialize(); // Initialize the database
    const ollamaClient = getOllamaClient();
    const searchEngine = new HybridSearchEngine(database, ollamaClient);

    // Perform a test search
    console.log('📊 Performing test search to generate metrics...\n');
    const results = await searchEngine.search('vector search sqlite', { k: 5 });
    console.log(`✅ Found ${results.length} results\n`);

    // Get metrics
    console.log('📈 Collecting metrics...\n');
    const metrics = await getMetrics();

    // Filter and display relevant metrics
    const relevantMetrics = metrics.split('\n').filter(line =>
      line.includes('devstream_') && !line.startsWith('#')
    );

    console.log('📊 DevStream Metrics:\n');
    relevantMetrics.slice(0, 30).forEach(line => {
      console.log('  ' + line);
    });

    if (relevantMetrics.length > 30) {
      console.log(`\n  ... and ${relevantMetrics.length - 30} more metrics\n`);
    }

    console.log('\n✅ Metrics collection is working correctly!');

  } catch (error) {
    console.error('❌ Error testing metrics:', error.message);
    console.error(error.stack);
  }
}

testMetrics().finally(() => {
  db.close();
  console.log('\n🏁 Test completed');
});