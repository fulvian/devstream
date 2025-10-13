/**
 * Jest Configuration for Integration Tests
 *
 * Configuration for running MCP server stability integration tests.
 * Tests require longer timeouts and special setup for server processes.
 */

export default {
  // Test environment
  testEnvironment: 'node',

  // Test file patterns
  testMatch: [
    '<rootDir>/tests/integration/**/*.test.js'
  ],

  // Module file extensions
  moduleFileExtensions: ['js', 'json'],

  // Transform files (ESM support)
  transform: {
    '^.+\\.js$': 'babel-jest'
  },

  // Setup files
  setupFilesAfterEnv: [
    '<rootDir>/tests/integration/setup.js'
  ],

  // Test timeout (30 seconds for integration tests)
  testTimeout: 30000,

  // Verbose output
  verbose: true,

  // Coverage configuration
  collectCoverage: false, // Coverage handled separately for unit tests

  // Global test configuration
  globals: {
    'NODE_ENV': 'test'
  },

  // Test reporter
  reporters: [
    'default',
    [
      'jest-junit',
      {
        outputDirectory: 'test-results',
        outputName: 'integration-test-results.xml'
      }
    ]
  ],

  // Test retry configuration
  retryTimes: 1,

  // Maximum workers (limit to avoid resource conflicts)
  maxWorkers: 1,

  // Force exit after tests
  forceExit: true,

  // Detect open handles
  detectOpenHandles: true,

  // Detect leaks
  detectLeaks: false, // Set to true for stricter testing

  // Clear mocks between tests
  clearMocks: true,

  // Restore mocks after each test
  restoreMocks: true
};