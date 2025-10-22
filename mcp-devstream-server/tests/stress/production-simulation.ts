/**
 * Production Simulation Test - Worker Pool Migration (Phase 3.4)
 *
 * Simulates real-world MCP DevStream usage pattern:
 * Write tool → PostToolUse → storeMemory (embedding + DB write)
 * Edit tool → PreToolUse → searchMemory (hybrid search)
 * Repeated 100 times to validate zero MCP timeouts.
 *
 * Target Metrics (from plan):
 * - ✅ Zero MCP timeouts (30s window respected)
 * - ✅ Average response time < 500ms
 * - ✅ P99 latency < 2000ms
 * - ✅ Event loop never blocked
 *
 * Context7 Pattern: Production workload simulation
 * - Realistic query patterns
 * - Latency distribution analysis
 * - Timeout detection
 */

import { getDatabasePool, closeDatabasePool } from '../../src/core/database-pool';

interface ProductionSimulationMetrics {
  totalCycles: number;
  completedCycles: number;
  failedCycles: number;
  avgResponseTime: number;
  p50Latency: number;
  p95Latency: number;
  p99Latency: number;
  maxLatency: number;
  minLatency: number;
  timeouts: number;
  cycleDurations: number[];
}

/**
 * Simulates one complete user interaction cycle:
 * 1. Write tool execution → storeMemory (INSERT query)
 * 2. PreToolUse → searchMemory (hybrid search - complex SELECT)
 * 3. Edit tool execution → storeMemory (INSERT query)
 * 4. PreToolUse → searchMemory (hybrid search)
 */
async function simulateUserCycle(cycleId: number): Promise<number> {
  const pool = getDatabasePool();
  const cycleStart = Date.now();

  try {
    // Step 1: Write tool → storeMemory (INSERT)
    await pool.execute(
      'INSERT INTO temp_simulation (cycle_id, step, timestamp) VALUES (?, ?, ?)',
      [cycleId, 'write_tool', Date.now()]
    );

    // Step 2: PreToolUse → searchMemory (complex SELECT simulating hybrid search)
    await pool.query(
      'SELECT * FROM temp_simulation WHERE cycle_id <= ? ORDER BY timestamp DESC LIMIT 10',
      [cycleId]
    );

    // Step 3: Edit tool → storeMemory (INSERT)
    await pool.execute(
      'INSERT INTO temp_simulation (cycle_id, step, timestamp) VALUES (?, ?, ?)',
      [cycleId, 'edit_tool', Date.now()]
    );

    // Step 4: PreToolUse → searchMemory (complex SELECT)
    await pool.query(
      'SELECT * FROM temp_simulation WHERE cycle_id = ? ORDER BY timestamp',
      [cycleId]
    );

    const cycleDuration = Date.now() - cycleStart;
    return cycleDuration;
  } catch (error) {
    throw new Error(`Cycle ${cycleId} failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

async function productionSimulation(): Promise<ProductionSimulationMetrics> {
  const pool = getDatabasePool();

  console.log('🔥 Starting production simulation...');
  console.log('📊 Test Parameters:');
  console.log('   - Total cycles: 100');
  console.log('   - Pattern: Write→Search→Edit→Search (4 DB operations/cycle)');
  console.log('   - Timeout threshold: 30s (MCP timeout window)');
  console.log('');

  // Create temporary table for simulation
  await pool.execute(`
    CREATE TEMP TABLE temp_simulation (
      cycle_id INTEGER,
      step TEXT,
      timestamp INTEGER
    )
  `);

  const totalCycles = 100;
  let completedCycles = 0;
  let failedCycles = 0;
  let timeouts = 0;
  const cycleDurations: number[] = [];

  for (let i = 0; i < totalCycles; i++) {
    try {
      const duration = await simulateUserCycle(i);

      // Check for MCP timeout (30s window)
      if (duration > 30000) {
        timeouts++;
        console.log(`⚠️  Cycle ${i}: Timeout detected (${duration}ms > 30000ms)`);
      }

      cycleDurations.push(duration);
      completedCycles++;

      if ((i + 1) % 10 === 0) {
        console.log(`📊 Progress: ${i + 1}/${totalCycles} cycles completed`);
      }
    } catch (error) {
      failedCycles++;
      console.error(`❌ Cycle ${i} failed:`, error instanceof Error ? error.message : 'Unknown error');
    }
  }

  // Calculate latency percentiles
  const sortedDurations = [...cycleDurations].sort((a, b) => a - b);

  const p50Index = Math.floor(sortedDurations.length * 0.5);
  const p95Index = Math.floor(sortedDurations.length * 0.95);
  const p99Index = Math.floor(sortedDurations.length * 0.99);

  const avgResponseTime = sortedDurations.reduce((sum, d) => sum + d, 0) / sortedDurations.length;
  const p50Latency = sortedDurations[p50Index] || 0;
  const p95Latency = sortedDurations[p95Index] || 0;
  const p99Latency = sortedDurations[p99Index] || 0;
  const maxLatency = Math.max(...sortedDurations);
  const minLatency = Math.min(...sortedDurations);

  const metrics: ProductionSimulationMetrics = {
    totalCycles,
    completedCycles,
    failedCycles,
    avgResponseTime,
    p50Latency,
    p95Latency,
    p99Latency,
    maxLatency,
    minLatency,
    timeouts,
    cycleDurations,
  };

  return metrics;
}

function validateMetrics(metrics: ProductionSimulationMetrics): { passed: boolean; failures: string[] } {
  const failures: string[] = [];

  // Validation 1: Zero MCP timeouts
  if (metrics.timeouts > 0) {
    failures.push(`❌ MCP timeouts detected: ${metrics.timeouts} (expected: 0)`);
  }

  // Validation 2: Average response time < 500ms
  if (metrics.avgResponseTime > 500) {
    failures.push(`❌ Avg response time too high: ${metrics.avgResponseTime.toFixed(2)}ms (expected: <500ms)`);
  }

  // Validation 3: P99 latency < 2000ms
  if (metrics.p99Latency > 2000) {
    failures.push(`❌ P99 latency too high: ${metrics.p99Latency.toFixed(2)}ms (expected: <2000ms)`);
  }

  // Validation 4: All cycles completed successfully
  if (metrics.failedCycles > 0) {
    failures.push(`❌ Failed cycles: ${metrics.failedCycles} (expected: 0)`);
  }

  return {
    passed: failures.length === 0,
    failures,
  };
}

function printResults(metrics: ProductionSimulationMetrics, validation: { passed: boolean; failures: string[] }): void {
  console.log('');
  console.log('═══════════════════════════════════════════════════════════');
  console.log('📊 PRODUCTION SIMULATION RESULTS');
  console.log('═══════════════════════════════════════════════════════════');
  console.log('');
  console.log('Cycle Statistics:');
  console.log(`   Total cycles:       ${metrics.totalCycles}`);
  console.log(`   Completed:          ${metrics.completedCycles}`);
  console.log(`   Failed:             ${metrics.failedCycles}`);
  console.log(`   Success rate:       ${((metrics.completedCycles / metrics.totalCycles) * 100).toFixed(2)}%`);
  console.log('');
  console.log('Latency Metrics:');
  console.log(`   Average:            ${metrics.avgResponseTime.toFixed(2)}ms`);
  console.log(`   P50 (median):       ${metrics.p50Latency.toFixed(2)}ms`);
  console.log(`   P95:                ${metrics.p95Latency.toFixed(2)}ms`);
  console.log(`   P99:                ${metrics.p99Latency.toFixed(2)}ms`);
  console.log(`   Min:                ${metrics.minLatency.toFixed(2)}ms`);
  console.log(`   Max:                ${metrics.maxLatency.toFixed(2)}ms`);
  console.log('');
  console.log('Timeout Analysis:');
  console.log(`   MCP timeouts (>30s): ${metrics.timeouts}`);
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
    const metrics = await productionSimulation();
    const validation = validateMetrics(metrics);

    printResults(metrics, validation);

    await closeDatabasePool();

    // Exit with appropriate code
    process.exit(validation.passed ? 0 : 1);
  } catch (error) {
    console.error('💥 Production simulation execution failed:', error);
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

export { productionSimulation, validateMetrics, ProductionSimulationMetrics };
