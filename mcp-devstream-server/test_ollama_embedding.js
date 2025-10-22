#!/usr/bin/env node
/**
 * Test Ollama embedding generation from MCP server context
 * Diagnose why embeddings fail in MCP but work via curl
 */

const { Ollama } = require('ollama');

async function testOllamaConnection() {
  console.log('🧪 Testing Ollama connection from Node.js...\n');

  // Use same config as MCP server
  const host = process.env.OLLAMA_HOST || 'http://127.0.0.1:11434';
  const model = 'embeddinggemma:300m';

  console.log(`📦 Configuration:`);
  console.log(`   Host: ${host}`);
  console.log(`   Model: ${model}\n`);

  const ollama = new Ollama({ host });

  // Test 1: Connection check
  console.log('🔌 Test 1: Connection check (ollama.ps())...');
  try {
    await ollama.ps();
    console.log('✅ Connection successful\n');
  } catch (error) {
    console.error(`❌ Connection failed: ${error.message}`);
    console.error('   Is Ollama running? Try: curl http://localhost:11434/api/tags\n');
    process.exit(1);
  }

  // Test 2: Model availability
  console.log('📋 Test 2: Model availability (ollama.list())...');
  try {
    const models = await ollama.list();
    const hasModel = models.models?.some(m => m.name.includes(model));

    if (hasModel) {
      console.log(`✅ Model '${model}' is available\n`);
    } else {
      console.error(`❌ Model '${model}' NOT found`);
      console.log('   Available models:', models.models?.map(m => m.name).join(', '));
      console.error(`   Pull with: ollama pull ${model}\n`);
      process.exit(1);
    }
  } catch (error) {
    console.error(`❌ Model check failed: ${error.message}\n`);
    process.exit(1);
  }

  // Test 3: Embedding generation
  console.log('🧠 Test 3: Embedding generation...');
  console.log('   Query: "session summary"\n');

  const testQueries = [
    'session summary',
    'vector search optimization',
    'embedding generation'
  ];

  for (const query of testQueries) {
    console.log(`   Testing: "${query}"`);

    try {
      const startTime = Date.now();

      const response = await ollama.embed({
        model,
        input: query,
        truncate: true,
        keep_alive: '5m'
      });

      const duration = Date.now() - startTime;

      if (!response.embeddings || !Array.isArray(response.embeddings) || response.embeddings.length === 0) {
        console.error(`   ❌ Invalid response structure`);
        continue;
      }

      const embedding = response.embeddings[0];
      console.log(`   ✅ Generated: ${embedding.length} dimensions in ${duration}ms`);

    } catch (error) {
      console.error(`   ❌ Failed: ${error.message}`);
      console.error(`      Stack: ${error.stack?.split('\n')[0]}`);
    }
  }

  console.log('\n' + '='.repeat(70));
  console.log('🎯 **CONCLUSION**: Ollama embedding generation test complete');
}

testOllamaConnection().catch(error => {
  console.error(`\n❌ Unexpected error: ${error.message}`);
  console.error(error.stack);
  process.exit(1);
});
