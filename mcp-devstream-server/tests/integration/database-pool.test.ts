/**
 * Database Pool Integration Tests
 *
 * Tests the Piscina worker pool implementation to ensure:
 * 1. Basic query execution works
 * 2. Concurrent queries are handled correctly
 * 3. Statistics tracking functions
 * 4. Error handling propagates correctly
 * 5. Graceful shutdown works
 *
 * Run with: npm test -- database-pool.test.ts
 */

import { getDatabasePool, closeDatabasePool } from '../../src/core/database-pool';

describe('DatabasePool Integration Tests', () => {
  afterAll(async () => {
    // Cleanup: Close pool after all tests
    await closeDatabasePool();
  });

  describe('Basic Operations', () => {
    it('should execute simple query', async () => {
      const pool = getDatabasePool();
      const result = await pool.query('SELECT 1 as value');

      expect(result).toEqual([{ value: 1 }]);
    });

    it('should execute query with parameters', async () => {
      const pool = getDatabasePool();
      const result = await pool.query('SELECT ? as value', [42]);

      expect(result).toEqual([{ value: 42 }]);
    });

    it('should execute queryOne returning first row', async () => {
      const pool = getDatabasePool();
      const result = await pool.queryOne('SELECT ? as value', [99]);

      expect(result).toEqual({ value: 99 });
    });

    it('should execute insert statement', async () => {
      const pool = getDatabasePool();

      // Use a unique table name for this test to avoid conflicts
      const testTableName = `test_table_${Date.now()}`;

      // Create temporary table
      await pool.execute(`CREATE TEMP TABLE ${testTableName} (id INTEGER, value TEXT)`);

      // Insert data
      const insertResult = await pool.execute(
        `INSERT INTO ${testTableName} (id, value) VALUES (?, ?)`,
        [1, 'test']
      );

      expect(insertResult.changes).toBe(1);

      // Verify data was inserted
      const rows = await pool.query(`SELECT * FROM ${testTableName}`);
      expect(rows).toHaveLength(1);
      expect(rows[0]).toEqual({ id: 1, value: 'test' });
    });
  });

  describe('Concurrent Operations', () => {
    it('should handle 10 concurrent queries', async () => {
      const pool = getDatabasePool();

      const promises = Array.from({ length: 10 }, (_, i) =>
        pool.query('SELECT ? as value', [i])
      );

      const results = await Promise.all(promises);

      expect(results).toHaveLength(10);
      expect(results[0]).toEqual([{ value: 0 }]);
      expect(results[9]).toEqual([{ value: 9 }]);
    });

    it('should handle 100 concurrent queries', async () => {
      const pool = getDatabasePool();

      const promises = Array.from({ length: 100 }, (_, i) =>
        pool.query('SELECT ? as value', [i])
      );

      const results = await Promise.all(promises);

      expect(results).toHaveLength(100);
      expect(results[0]).toEqual([{ value: 0 }]);
      expect(results[99]).toEqual([{ value: 99 }]);
    });
  });

  describe('Statistics Tracking', () => {
    it('should collect statistics after queries', async () => {
      const pool = getDatabasePool();

      // Execute some queries
      await pool.query('SELECT 1');
      await pool.query('SELECT 2');
      await pool.query('SELECT 3');

      const stats = pool.getStats();

      // Verify statistics are tracked
      expect(stats.completed).toBeGreaterThanOrEqual(3);
      expect(stats.runTime.average).toBeGreaterThan(0);
      expect(stats.runTime.min).toBeGreaterThanOrEqual(0);
      expect(stats.runTime.max).toBeGreaterThan(0);
      expect(stats.waitTime).toBeDefined();
      expect(stats.threads).toBeGreaterThan(0);
      expect(stats.queueSize).toBeGreaterThanOrEqual(0);
    });

    it('should track query duration', async () => {
      const pool = getDatabasePool();

      const statsBefore = pool.getStats();
      const completedBefore = statsBefore.completed;

      // Execute query
      await pool.query('SELECT 1');

      const statsAfter = pool.getStats();
      const completedAfter = statsAfter.completed;

      // Verify completed count increased
      expect(completedAfter).toBeGreaterThan(completedBefore);
    });
  });

  describe('Error Handling', () => {
    it('should propagate SQL syntax errors', async () => {
      const pool = getDatabasePool();

      await expect(pool.query('INVALID SQL SYNTAX')).rejects.toThrow();
    });

    it('should handle invalid table errors', async () => {
      const pool = getDatabasePool();

      await expect(pool.query('SELECT * FROM non_existent_table')).rejects.toThrow();
    });

    it('should handle invalid parameters', async () => {
      const pool = getDatabasePool();

      // Try to bind more parameters than placeholders
      await expect(pool.query('SELECT ?', [1, 2])).rejects.toThrow();
    });
  });

  describe('Real Database Queries', () => {
    // Context7 Pattern: Test pool behavior with temporary tables, not production schema
    // Production schema tables (semantic_memory) should be tested in dedicated integration tests
    // with a properly configured test database

    it('should handle queries on non-existent tables gracefully', async () => {
      const pool = getDatabasePool();

      // Test error handling for missing table
      await expect(
        pool.query('SELECT * FROM non_existent_table_12345')
      ).rejects.toThrow();
    });

    it('should handle empty result sets with temp tables', async () => {
      const pool = getDatabasePool();

      // Create temporary table for testing
      const testTableName = `test_empty_${Date.now()}`;
      await pool.execute(`CREATE TEMP TABLE ${testTableName} (id TEXT, value TEXT)`);

      // Query empty table
      const result = await pool.query(`SELECT * FROM ${testTableName} WHERE id = ?`, ['non-existent']);

      expect(result).toEqual([]);
    });
  });

  describe('Pool Management', () => {
    it('should support singleton pattern', () => {
      const pool1 = getDatabasePool();
      const pool2 = getDatabasePool();

      // Both calls should return the same instance
      expect(pool1).toBe(pool2);
    });

    it('should have correct configuration', () => {
      const pool = getDatabasePool();
      const stats = pool.getStats();

      // Verify worker threads are spawned
      expect(stats.threads).toBeGreaterThan(0);
      expect(stats.threads).toBeLessThanOrEqual(8); // maxThreads on MacBook Pro M3 Max
    });
  });
});
