/**
 * Quick Database Pool Test
 *
 * Fast sanity check to verify pool initialization and basic query execution.
 * Run with: npm test -- database-pool-quick.test.ts
 */

import { getDatabasePool, closeDatabasePool } from '../../src/core/database-pool';

describe('DatabasePool Quick Test', () => {
  afterAll(async () => {
    await closeDatabasePool();
  }, 10000); // 10s timeout for cleanup

  it('should initialize pool and execute simple query', async () => {
    const pool = getDatabasePool();

    // Simple query
    const result = await pool.query('SELECT 1 as value');

    expect(result).toEqual([{ value: 1 }]);

    // Verify statistics
    const stats = pool.getStats();
    expect(stats.completed).toBeGreaterThanOrEqual(1);
    expect(stats.threads).toBeGreaterThan(0);

    console.log('✅ Pool working correctly:', {
      completed: stats.completed,
      threads: stats.threads,
      avgRunTime: stats.runTime.average.toFixed(2) + 'ms',
    });
  }, 30000); // 30s timeout
});
