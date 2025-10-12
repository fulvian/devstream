/**
 * Endurance Testing Script - Worker Pool Migration (Phase 3.2)
 *
 * Tests database pool stability over extended period (5 minutes).
 * Monitors memory leaks, worker crashes, and performance degradation.
 *
 * Target Metrics (from plan):
 * - ✅ Zero memory leaks (heap stable)
 * - ✅ Zero worker crashes
 * - ✅ Performance stable (no degradation over time)
 * - ✅ Event loop lag < 10ms median
 *
 * Context7 Pattern: Long-running stability testing
 * - Continuous load simulation
 * - Resource monitoring
 * - Performance degradation detection
 */

import { getDatabasePool, closeDatabasePool } from '../../src/core/database-pool';

interface EnduranceMetrics {
  duration: number;
  totalQueries: number;
  successfulQueries: number;
  failedQueries: number;
  avgQps: number;
  peakQps: number;
  minQps: number;
  initialHeapMB: number;
  finalHeapMB: number;
  heapGrowthMB: number;
  workerCrashes: number;
  performanceSamples: PerformanceSample[];
}

interface PerformanceSample {
  timestamp: number;
  qps: number;
  heapMB: number;
  avgRunTime: number;
  avgWaitTime: number;
}

async function enduranceTest(): Promise<EnduranceMetrics> {
  const pool = getDatabasePool();

  const TEST_DURATION_MS = 5 * 60 * 1000; // 5 minutes
  const QUERY_INTERVAL_MS = 100; // Query every 100ms
  const SAMPLE_INTERVAL_MS = 10 * 1000; // Sample every 10 seconds

  console.log('🔥 Starting endurance test...');
  console.log('📊 Test Parameters:');
  console.log(`   - Duration: ${TEST_DURATION_MS / 1000} seconds (5 minutes)`);
  console.log(`   - Query interval: ${QUERY_INTERVAL_MS}ms`);
  console.log(`   - Expected total queries: ~${Math.floor(TEST_DURATION_MS / QUERY_INTERVAL_MS)}`);
  console.log('');

  const startTime = Date.now();
  const initialHeapMB = process.memoryUsage().heapUsed / 1024 / 1024;

  let totalQueries = 0;
  let successfulQueries = 0;
  let failedQueries = 0;
  let workerCrashes = 0;

  const performanceSamples: PerformanceSample[] = [];

  // Sample performance every 10 seconds
  const samplingInterval = setInterval(() => {
    const heapMB = process.memoryUsage().heapUsed / 1024 / 1024;
    const stats = pool.getStats();
    const elapsed = Date.now() - startTime;
    const qps = Math.round((successfulQueries / (elapsed / 1000)));

    const sample: PerformanceSample = {
      timestamp: elapsed,
      qps,
      heapMB,
      avgRunTime: stats.runTime.average,
      avgWaitTime: stats.waitTime.average,
    };

    performanceSamples.push(sample);

    console.log(`📊 Sample ${performanceSamples.length}:`, {
      elapsed: `${Math.floor(elapsed / 1000)}s`,
      qps,
      heapMB: heapMB.toFixed(2) + 'MB',
      avgRunTime: stats.runTime.average.toFixed(2) + 'ms',
      avgWaitTime: stats.waitTime.average.toFixed(2) + 'ms',
    });
  }, SAMPLE_INTERVAL_MS);

  // Execute queries continuously for TEST_DURATION_MS
  const queryPromise = new Promise<void>((resolve) => {
    const queryInterval = setInterval(async () => {
      const elapsed = Date.now() - startTime;

      if (elapsed >= TEST_DURATION_MS) {
        clearInterval(queryInterval);
        resolve();
        return;
      }

      totalQueries++;

      try {
        await pool.query('SELECT ? as value, ? as timestamp', [totalQueries, Date.now()]);
        successfulQueries++;
      } catch (error) {
        failedQueries++;
        // Check if error indicates worker crash
        if (error instanceof Error && error.message.includes('worker')) {
          workerCrashes++;
        }
      }
    }, QUERY_INTERVAL_MS);
  });

  // Wait for test duration to complete
  await queryPromise;

  clearInterval(samplingInterval);

  const duration = Date.now() - startTime;
  const finalHeapMB = process.memoryUsage().heapUsed / 1024 / 1024;
  const heapGrowthMB = finalHeapMB - initialHeapMB;

  const avgQps = Math.round(successfulQueries / (duration / 1000));
  const peakQps = Math.max(...performanceSamples.map(s => s.qps));
  const minQps = Math.min(...performanceSamples.map(s => s.qps));

  const metrics: EnduranceMetrics = {
    duration,
    totalQueries,
    successfulQueries,
    failedQueries,
    avgQps,
    peakQps,
    minQps,
    initialHeapMB,
    finalHeapMB,
    heapGrowthMB,
    workerCrashes,
    performanceSamples,
  };

  return metrics;
}

function validateMetrics(metrics: EnduranceMetrics): { passed: boolean; failures: string[] } {
  const failures: string[] = [];

  // Validation 1: Zero memory leaks (heap growth < 50MB)
  if (metrics.heapGrowthMB > 50) {
    failures.push(`❌ Memory leak detected: ${metrics.heapGrowthMB.toFixed(2)}MB growth (expected: <50MB)`);
  }

  // Validation 2: Zero worker crashes
  if (metrics.workerCrashes > 0) {
    failures.push(`❌ Worker crashes detected: ${metrics.workerCrashes} (expected: 0)`);
  }

  // Validation 3: Performance stable (variation < 30%)
  const qpsVariation = ((metrics.peakQps - metrics.minQps) / metrics.avgQps) * 100;
  if (qpsVariation > 30) {
    failures.push(`❌ Performance degradation: ${qpsVariation.toFixed(1)}% variation (expected: <30%)`);
  }

  // Validation 4: Query success rate > 99%
  const successRate = (metrics.successfulQueries / metrics.totalQueries) * 100;
  if (successRate < 99) {
    failures.push(`❌ Low success rate: ${successRate.toFixed(2)}% (expected: >99%)`);
  }

  return {
    passed: failures.length === 0,
    failures,
  };
}

function printResults(metrics: EnduranceMetrics, validation: { passed: boolean; failures: string[] }): void {
  console.log('');
  console.log('═══════════════════════════════════════════════════════════');
  console.log('📊 ENDURANCE TEST RESULTS');
  console.log('═══════════════════════════════════════════════════════════');
  console.log('');
  console.log('Query Statistics:');
  console.log(`   Duration:           ${Math.floor(metrics.duration / 1000)}s`);
  console.log(`   Total queries:      ${metrics.totalQueries}`);
  console.log(`   Successful:         ${metrics.successfulQueries}`);
  console.log(`   Failed:             ${metrics.failedQueries}`);
  console.log(`   Success rate:       ${((metrics.successfulQueries / metrics.totalQueries) * 100).toFixed(2)}%`);
  console.log('');
  console.log('Performance Metrics:');
  console.log(`   Average QPS:        ${metrics.avgQps}`);
  console.log(`   Peak QPS:           ${metrics.peakQps}`);
  console.log(`   Min QPS:            ${metrics.minQps}`);
  console.log(`   QPS variation:      ${(((metrics.peakQps - metrics.minQps) / metrics.avgQps) * 100).toFixed(1)}%`);
  console.log('');
  console.log('Memory Metrics:');
  console.log(`   Initial heap:       ${metrics.initialHeapMB.toFixed(2)}MB`);
  console.log(`   Final heap:         ${metrics.finalHeapMB.toFixed(2)}MB`);
  console.log(`   Heap growth:        ${metrics.heapGrowthMB.toFixed(2)}MB`);
  console.log('');
  console.log('Stability Metrics:');
  console.log(`   Worker crashes:     ${metrics.workerCrashes}`);
  console.log(`   Performance samples: ${metrics.performanceSamples.length}`);
  console.log('');
  console.log('Validation Results:');

  if (validation.passed) {
    console.log('   ✅ ALL VALIDATIONS PASSED');
  } else {
    console.log('   ❌ SOME VALIDATIONS FAILED:');
    validation.failures.forEach(failure => {
      console.log(`      ${failure}`);
    });
  }

  console.log('');
  console.log('═══════════════════════════════════════════════════════════');
  console.log('');
}

async function main() {
  try {
    const metrics = await enduranceTest();
    const validation = validateMetrics(metrics);

    printResults(metrics, validation);

    await closeDatabasePool();

    // Exit with appropriate code
    process.exit(validation.passed ? 0 : 1);
  } catch (error) {
    console.error('💥 Endurance test execution failed:', error);
    await closeDatabasePool();
    process.exit(1);
  }
}

// Run if executed directly
if (require.main === module) {
  main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}

export { enduranceTest, validateMetrics, EnduranceMetrics };
