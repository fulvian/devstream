/**
 * Load Testing Script - Worker Pool Migration (Phase 3.1)
 *
 * Tests database pool under high concurrency (1000 queries).
 * Validates performance, stability, and resource management.
 *
 * Target Metrics (from plan):
 * - ✅ 1000 queries completed without errors
 * - ✅ QPS > 100 (10x improvement vs current ~10 QPS)
 * - ✅ Average wait time < 100ms
 * - ✅ Max wait time < 500ms
 * - ✅ Zero worker crashes
 *
 * Context7 Pattern: Stress testing based on Piscina best practices
 * - High concurrency validation
 * - Queue saturation testing
 * - Performance metrics collection
 */

import { getDatabasePool, closeDatabasePool } from '../../src/core/database-pool';

interface LoadTestMetrics {
  totalQueries: number;
  duration: number;
  qps: number;
  avgRunTime: number;
  avgWaitTime: number;
  maxWaitTime: number;
  minWaitTime: number;
  threads: number;
  completed: number;
  errors: number;
}

async function loadTest(): Promise<LoadTestMetrics> {
  // Context7 Pattern: Use simple query that doesn't depend on production schema
  // Stress testing should validate pool behavior, not production data
  const pool = getDatabasePool();

  console.log('🔥 Starting load test...');
  console.log('📊 Test Parameters:');
  console.log('   - Total queries: 1000');
  console.log('   - Concurrency: All at once');
  console.log('   - Query: SELECT ? as value');
  console.log('');

  const start = Date.now();
  let errors = 0;

  try {
    // 1000 concurrent queries (simple SELECT to validate pool behavior)
    const promises = Array.from({ length: 1000 }, (_, i) =>
      pool.query('SELECT ? as value', [i])
        .catch(error => {
          errors++;
          console.error(`❌ Query ${i} failed:`, error.message);
          return [];
        })
    );

    await Promise.all(promises);

    const duration = Date.now() - start;
    const qps = Math.round(1000 / (duration / 1000));

    // Collect final statistics
    const stats = pool.getStats();

    const metrics: LoadTestMetrics = {
      totalQueries: 1000,
      duration,
      qps,
      avgRunTime: stats.runTime.average,
      avgWaitTime: stats.waitTime.average,
      maxWaitTime: stats.waitTime.max,
      minWaitTime: stats.waitTime.min,
      threads: stats.threads,
      completed: stats.completed,
      errors,
    };

    return metrics;
  } catch (error) {
    console.error('💥 Load test failed catastrophically:', error);
    throw error;
  }
}

function validateMetrics(metrics: LoadTestMetrics): { passed: boolean; failures: string[] } {
  const failures: string[] = [];

  // Validation 1: All queries completed
  if (metrics.errors > 0) {
    failures.push(`❌ ${metrics.errors} queries failed (expected: 0)`);
  }

  // Validation 2: QPS > 100
  if (metrics.qps < 100) {
    failures.push(`❌ QPS too low: ${metrics.qps} (expected: >100)`);
  }

  // Validation 3: Average wait time < 100ms
  if (metrics.avgWaitTime > 100) {
    failures.push(`❌ Avg wait time too high: ${metrics.avgWaitTime.toFixed(2)}ms (expected: <100ms)`);
  }

  // Validation 4: Max wait time < 500ms
  if (metrics.maxWaitTime > 500) {
    failures.push(`❌ Max wait time too high: ${metrics.maxWaitTime.toFixed(2)}ms (expected: <500ms)`);
  }

  return {
    passed: failures.length === 0,
    failures,
  };
}

function printResults(metrics: LoadTestMetrics, validation: { passed: boolean; failures: string[] }): void {
  console.log('');
  console.log('═══════════════════════════════════════════════════════════');
  console.log('📊 LOAD TEST RESULTS');
  console.log('═══════════════════════════════════════════════════════════');
  console.log('');
  console.log('Performance Metrics:');
  console.log(`   Duration:           ${metrics.duration}ms`);
  console.log(`   Queries/sec:        ${metrics.qps} QPS`);
  console.log(`   Avg run time:       ${metrics.avgRunTime.toFixed(2)}ms`);
  console.log(`   Avg wait time:      ${metrics.avgWaitTime.toFixed(2)}ms`);
  console.log(`   Min wait time:      ${metrics.minWaitTime.toFixed(2)}ms`);
  console.log(`   Max wait time:      ${metrics.maxWaitTime.toFixed(2)}ms`);
  console.log('');
  console.log('Pool Statistics:');
  console.log(`   Active threads:     ${metrics.threads}`);
  console.log(`   Completed tasks:    ${metrics.completed}`);
  console.log(`   Failed queries:     ${metrics.errors}`);
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
    const metrics = await loadTest();
    const validation = validateMetrics(metrics);

    printResults(metrics, validation);

    await closeDatabasePool();

    // Exit with appropriate code
    process.exit(validation.passed ? 0 : 1);
  } catch (error) {
    console.error('💥 Load test execution failed:', error);
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

export { loadTest, validateMetrics, LoadTestMetrics };
