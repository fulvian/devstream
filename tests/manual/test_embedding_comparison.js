/**
 * Direct comparison test: TypeScript vs Python embedding generation
 *
 * Tests if ollama-js and ollama-python generate identical embeddings
 * for the same input text using the same model.
 */

import { Ollama } from 'ollama';
import fs from 'fs';

const TEST_QUERY = "session summary atomic write marker file";
const MODEL = "embeddinggemma:300m";

async function testEmbeddingGeneration() {
  console.log('🔍 Testing Embedding Generation Consistency\n');
  console.log(`Query: "${TEST_QUERY}"`);
  console.log(`Model: ${MODEL}\n`);

  try {
    // Generate embedding using ollama-js
    const ollama = new Ollama({ host: 'http://localhost:11434' });

    console.log('📊 Generating embedding with ollama-js...');
    const startTime = Date.now();

    const response = await ollama.embed({
      model: MODEL,
      input: TEST_QUERY,
      truncate: true,
      keep_alive: '5m'
    });

    const duration = Date.now() - startTime;

    // Extract embedding from response
    const embedding = response.embeddings[0];

    console.log(`✅ Embedding generated in ${duration}ms`);
    console.log(`📐 Dimensions: ${embedding.length}`);
    console.log(`📊 First 5 values: [${embedding.slice(0, 5).map(v => v.toFixed(6)).join(', ')}]`);
    console.log(`📊 Last 5 values: [${embedding.slice(-5).map(v => v.toFixed(6)).join(', ')}]`);

    // Calculate statistics
    const sum = embedding.reduce((a, b) => a + b, 0);
    const mean = sum / embedding.length;
    const variance = embedding.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / embedding.length;
    const stdDev = Math.sqrt(variance);
    const min = Math.min(...embedding);
    const max = Math.max(...embedding);
    const magnitude = Math.sqrt(embedding.reduce((a, b) => a + b * b, 0));

    console.log(`\n📊 Statistics:`);
    console.log(`   Mean: ${mean.toFixed(6)}`);
    console.log(`   Std Dev: ${stdDev.toFixed(6)}`);
    console.log(`   Min: ${min.toFixed(6)}`);
    console.log(`   Max: ${max.toFixed(6)}`);
    console.log(`   Magnitude (L2 norm): ${magnitude.toFixed(6)}`);

    // Check if normalized
    const isNormalized = Math.abs(magnitude - 1.0) < 0.01;
    console.log(`   Normalized: ${isNormalized ? '✅ YES' : '❌ NO'}`);

    // Save to file for Python comparison
    fs.writeFileSync('embedding_typescript.json', JSON.stringify({
      query: TEST_QUERY,
      model: MODEL,
      embedding: embedding,
      statistics: {
        dimensions: embedding.length,
        mean,
        stdDev,
        min,
        max,
        magnitude,
        isNormalized
      }
    }, null, 2));

    console.log(`\n💾 Embedding saved to embedding_typescript.json`);
    console.log(`\n🔄 Now run the Python comparison script to compare results.`);

  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

testEmbeddingGeneration();
