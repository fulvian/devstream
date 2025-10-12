/**
 * Jest Test Setup
 *
 * Global test configuration and setup utilities.
 */

// Suppress console.error during tests (unless debugging)
if (!process.env.DEBUG_TESTS) {
  global.console.error = jest.fn();
}

// Set test environment variables
process.env.NODE_ENV = 'test';
process.env.DEVSTREAM_LOG_LEVEL = 'error';

// Context7 Pattern: Configure worker pool for high-concurrency tests
// database-pool.test.ts runs 100 concurrent queries, requires larger queue than default (64)
process.env.DEVSTREAM_WORKER_POOL_MAX_QUEUE = '128'; // Support high-concurrency tests

// Increase timeout for integration tests
jest.setTimeout(30000);
