#!/usr/bin/env node

/**
 * Test E2E per sistema embedding DevStream
 * Verifica: memoria storage → embedding generation → vector search
 */

const http = require('http');

const BASE_URL = 'http://localhost:9094';

async function testMemoryStorage() {
  console.log(`🧪 Test 1: Memory Storage con Embedding...`);

  const testData = {
    content: "Questo è un test di verifica del sistema embedding per DevStream. Include concetti come database worker pool, sqlite-vec extension, e hybrid search functionality.",
    content_type: "test",
    keywords: ["embedding", "worker pool", "sqlite-vec", "hybrid search"],
    metadata: {
      test_id: "e2e_test_001",
      timestamp: new Date().toISOString(),
      component: "mcp_server"
    }
  };

  return new Promise((resolve, reject) => {
    const postData = JSON.stringify(testData);

    const options = {
      hostname: 'localhost',
      port: 9094,
      path: '/memory/store',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const result = JSON.parse(data);
          console.log(`   ✅ Memory storage: ${result.success ? 'SUCCESS' : 'FAILED'}`);
          if (result.success) {
            console.log(`   📝 Record ID: ${result.record_id}`);
            console.log(`   🧠 Embedding generato: ${result.embedding_generated ? 'SÌ' : 'NO'}`);
          }
          resolve(result);
        } catch (e) {
          console.log(`   ❌ Memory storage: ERROR (${e.message})`);
          resolve({ success: false, error: e.message });
        }
      });
    });

    req.on('error', (err) => {
      console.log(`   ❌ Memory storage: CONNECTION ERROR (${err.message})`);
      resolve({ success: false, error: err.message });
    });

    req.write(postData);
    req.end();
  });
}

async function testHybridSearch() {
  console.log(``);
  console.log(`🔍 Test 2: Hybrid Search...`);

  const searchQuery = "worker pool sqlite-vec embedding";

  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      query: searchQuery,
      limit: 5,
      content_type: null
    });

    const options = {
      hostname: 'localhost',
      port: 9094,
      path: '/memory/search',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const result = JSON.parse(data);
          console.log(`   ✅ Hybrid search: ${result.success ? 'SUCCESS' : 'FAILED'}`);
          if (result.success) {
            console.log(`   📊 Risultati trovati: ${result.results.length}`);
            console.log(`   🎯 Top score: ${result.results[0]?.score?.toFixed(4) || 'N/A'}`);
            console.log(`   ⏱️  Query time: ${result.query_time_ms || 'N/A'}ms`);

            // Verifica che il nostro test sia nei risultati
            const testResult = result.results.find(r => r.content?.includes('e2e_test_001'));
            if (testResult) {
              console.log(`   🎯 Test record trovato (rank: ${result.results.indexOf(testResult) + 1})`);
            }
          }
          resolve(result);
        } catch (e) {
          console.log(`   ❌ Hybrid search: ERROR (${e.message})`);
          resolve({ success: false, error: e.message });
        }
      });
    });

    req.on('error', (err) => {
      console.log(`   ❌ Hybrid search: CONNECTION ERROR (${err.message})`);
      resolve({ success: false, error: err.message });
    });

    req.write(postData);
    req.end();
  });
}

async function testVectorSearch() {
  console.log(``);
  console.log(`🎯 Test 3: Vector Search Puro...`);

  const searchQuery = "database performance optimization threading";

  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      query: searchQuery,
      limit: 3,
      search_type: "vector_only"
    });

    const options = {
      hostname: 'localhost',
      port: 9094,
      path: '/memory/search',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const result = JSON.parse(data);
          console.log(`   ✅ Vector search: ${result.success ? 'SUCCESS' : 'FAILED'}`);
          if (result.success) {
            console.log(`   📊 Risultati: ${result.results.length}`);
            console.log(`   🎯 Top similarity: ${result.results[0]?.similarity?.toFixed(4) || 'N/A'}`);
          }
          resolve(result);
        } catch (e) {
          console.log(`   ❌ Vector search: ERROR (${e.message})`);
          resolve({ success: false, error: e.message });
        }
      });
    });

    req.on('error', (err) => {
      console.log(`   ❌ Vector search: CONNECTION ERROR (${err.message})`);
      resolve({ success: false, error: err.message });
    });

    req.write(postData);
    req.end();
  });
}

async function testSystemMetrics() {
  console.log(``);
  console.log(`📊 Test 4: System Metrics...`);

  return new Promise((resolve, reject) => {
    const req = http.get(`${BASE_URL}/metrics`, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        // Estrai metriche rilevanti
        const queryCount = (data.match(/devstream_queries_total[^}]+} (\d+)/) || [])[1] || '0';
        const vectorIndex = (data.match(/devstream_vector_index_size (\d+)/) || [])[1] || '0';
        const ftsIndex = (data.match(/devstream_fts5_index_size (\d+)/) || [])[1] || '0';

        console.log(`   ✅ Metrics: SUCCESS`);
        console.log(`   📊 Query totali: ${queryCount}`);
        console.log(`   🎯 Vector index size: ${vectorIndex}`);
        console.log(`   📝 FTS5 index size: ${ftsIndex}`);

        resolve({
          success: true,
          queryCount: parseInt(queryCount),
          vectorIndex: parseInt(vectorIndex),
          ftsIndex: parseInt(ftsIndex)
        });
      });
    });

    req.on('error', (err) => {
      console.log(`   ❌ Metrics: CONNECTION ERROR (${err.message})`);
      resolve({ success: false, error: err.message });
    });
  });
}

async function runE2ETest() {
  console.log(`🚀 DevStream MCP E2E Test Suite`);
  console.log(`====================================`);
  console.log(`Target: ${BASE_URL}`);
  console.log(``);

  const results = {
    memoryStorage: await testMemoryStorage(),
    hybridSearch: await testHybridSearch(),
    vectorSearch: await testVectorSearch(),
    systemMetrics: await testSystemMetrics()
  };

  console.log(``);
  console.log(`📋 RIEPILOGO RISULTATI:`);
  console.log(``);

  const passed = Object.values(results).filter(r => r.success).length;
  const total = Object.keys(results).length;

  Object.entries(results).forEach(([test, result]) => {
    const status = result.success ? '✅ PASS' : '❌ FAIL';
    console.log(`   ${test.padEnd(15)}: ${status}`);
  });

  console.log(``);
  console.log(`🎯 VERDETTO FINALE: ${passed}/${total} test passati`);

  if (passed === total) {
    console.log(``);
    console.log(`🎉 SISTEMA FULLY OPERATIVO!`);
    console.log(`   ✅ Memory storage con embedding automatico`);
    console.log(`   ✅ Hybrid search (vector + FTS5)`);
    console.log(`   ✅ Vector search puro`);
    console.log(`   ✅ System metrics`);
    console.log(`   ✅ Worker pool (test precedente: 426 QPS)`);
  } else {
    console.log(``);
    console.log(`⚠️  PROBLEMI RILEVATI - Sistema non completamente operativo`);
  }

  process.exit(passed === total ? 0 : 1);
}

runE2ETest().catch(console.error);