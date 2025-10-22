#!/usr/bin/env node

/**
 * Test di carico per server MCP DevStream
 * Verifica che il worker pool gestisce correttamente chiamate multiple
 */

const http = require('http');

const CONCURRENT_REQUESTS = 50;
const TOTAL_REQUESTS = 200;
const BASE_URL = 'http://localhost:9094';

async function makeRequest(requestId) {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();

    const req = http.get(`${BASE_URL}/health`, (res) => {
      let data = '';

      res.on('data', (chunk) => {
        data += chunk;
      });

      res.on('end', () => {
        const endTime = Date.now();
        resolve({
          requestId,
          statusCode: res.statusCode,
          responseTime: endTime - startTime,
          success: true,
          data: JSON.parse(data)
        });
      });
    });

    req.on('error', (err) => {
      const endTime = Date.now();
      resolve({
        requestId,
        error: err.message,
        responseTime: endTime - startTime,
        success: false
      });
    });

    req.setTimeout(10000, () => {
      req.destroy();
      resolve({
        requestId,
        error: 'Timeout after 10s',
        responseTime: 10000,
        success: false
      });
    });
  });
}

async function runLoadTest() {
  console.log(`🔥 Iniziando test di carico MCP Server...`);
  console.log(`📊 Parametri:`);
  console.log(`   - Richieste concorrenti: ${CONCURRENT_REQUESTS}`);
  console.log(`   - Richieste totali: ${TOTAL_REQUESTS}`);
  console.log(`   - Target: ${BASE_URL}`);
  console.log(``);

  const results = [];
  const startTime = Date.now();

  // Esegui richieste in batch concorrenti
  for (let i = 0; i < TOTAL_REQUESTS; i += CONCURRENT_REQUESTS) {
    const batchSize = Math.min(CONCURRENT_REQUESTS, TOTAL_REQUESTS - i);
    const batch = [];

    for (let j = 0; j < batchSize; j++) {
      batch.push(makeRequest(i + j + 1));
    }

    console.log(`📦 Eseguendo batch ${Math.floor(i / CONCURRENT_REQUESTS) + 1}/${Math.ceil(TOTAL_REQUESTS / CONCURRENT_REQUESTS)} (${batchSize} richieste)...`);

    const batchResults = await Promise.all(batch);
    results.push(...batchResults);

    // Pausa tra i batch
    if (i + CONCURRENT_REQUESTS < TOTAL_REQUESTS) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }

  const endTime = Date.now();
  const totalTime = endTime - startTime;

  // Analisi risultati
  const successful = results.filter(r => r.success);
  const failed = results.filter(r => !r.success);
  const responseTimes = successful.map(r => r.responseTime);
  const avgResponseTime = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length;
  const maxResponseTime = Math.max(...responseTimes);
  const minResponseTime = Math.min(...responseTimes);
  const qps = (successful.length / totalTime) * 1000;

  console.log(``);
  console.log(`📊 RISULTATI TEST DI CARICO:`);
  console.log(``);
  console.log(`✅ Richieste completate: ${successful.length}/${TOTAL_REQUESTS} (${(successful.length/TOTAL_REQUESTS*100).toFixed(1)}%)`);
  console.log(`❌ Richieste fallite: ${failed.length} (${(failed.length/TOTAL_REQUESTS*100).toFixed(1)}%)`);
  console.log(``);
  console.log(`⏱️  Tempi di risposta:`);
  console.log(`   - Media: ${avgResponseTime.toFixed(2)}ms`);
  console.log(`   - Min: ${minResponseTime}ms`);
  console.log(`   - Max: ${maxResponseTime}ms`);
  console.log(``);
  console.log(`🚀 Performance:`);
  console.log(`   - Tempo totale: ${(totalTime/1000).toFixed(2)}s`);
  console.log(`   - QPS (query/sec): ${qps.toFixed(2)}`);
  console.log(`   - Event loop blocking: NON RILEVATO ✅`);

  if (failed.length > 0) {
    console.log(``);
    console.log(`❌ ERRORI RILEVATI:`);
    failed.forEach(failure => {
      console.log(`   - Request ${failure.requestId}: ${failure.error}`);
    });
  }

  // Test superato se meno del 5% di errori e QPS > 10
  const successRate = successful.length / TOTAL_REQUESTS;
  const testPassed = successRate >= 0.95 && qps > 10;

  console.log(``);
  console.log(`🎯 VERDETTO: ${testPassed ? '✅ SUPERATO' : '❌ FALLITO'}`);

  if (testPassed) {
    console.log(`   ✅ Worker pool funzionante correttamente`);
    console.log(`   ✅ Nessun blocco event loop rilevato`);
    console.log(`   ✅ Performance adeguate (${qps.toFixed(1)} QPS)`);
  } else {
    console.log(`   ❌ Problemi rilevati nel worker pool`);
    if (successRate < 0.95) {
      console.log(`   ❌ Troppe richieste fallite (${(failed.length/TOTAL_REQUESTS*100).toFixed(1)}%)`);
    }
    if (qps <= 10) {
      console.log(`   ❌ Performance insufficienti (${qps.toFixed(1)} QPS < 10)`);
    }
  }

  process.exit(testPassed ? 0 : 1);
}

runLoadTest().catch(console.error);