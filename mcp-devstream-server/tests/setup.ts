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

// Increase timeout for integration tests
jest.setTimeout(30000);
