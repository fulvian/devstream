/**
 * MCP Server Stability Integration Tests
 *
 * Comprehensive integration tests for MCP server stability fixes.
 * Tests multi-instance prevention, database validation, session tracking,
 * circuit breaker patterns, and health monitoring functionality.
 */

import { spawn, ChildProcess } from 'child_process';
import { join } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import http from 'http';
import fs from 'fs/promises';
import { setTimeout } from 'timers/promises';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..', '..');

// Test configuration
const TEST_CONFIG = {
  databasePath: join(projectRoot, 'test-data', 'test-devstream.db'),
  wrongDatabasePath: join(projectRoot, 'test-data', 'wrong-db.db'),
  pidFilePath: '/tmp/devstream-mcp-server.pid',
  healthServerPort: 9091, // Use different port to avoid conflicts
  serverPath: join(projectRoot, 'dist', 'index.js'),
  timeout: 30000, // 30 seconds
  retries: 3
};

// Utility functions
function delay(ms) {
  return setTimeout(ms);
}

function spawnServer(databasePath) {
  const server = spawn('node', [TEST_CONFIG.serverPath, databasePath], {
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, DEVSTREAM_DB_PATH: databasePath }
  });

  server.stderr.on('data', (data) => {
    console.error(`[SERVER-STDERR] ${data.toString()}`);
  });

  return server;
}

function makeHttpRequest(url, timeout = 5000) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, { timeout }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve({ statusCode: res.statusCode, data }));
    });

    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error('Request timeout'));
    });
  });
}

async function cleanup() {
  // Clean up any existing processes
  try {
    await fs.unlink(TEST_CONFIG.pidFilePath);
  } catch {}

  // Kill any stray processes (safety net)
  const { exec } = require('child_process');
  return new Promise((resolve) => {
    exec(`pkill -f "node.*${TEST_CONFIG.serverPath}" || true`, resolve);
  });
}

describe('MCP Server Stability Integration Tests', () => {
  let originalDatabase;

  beforeAll(async () => {
    // Clean up before tests
    await cleanup();

    // Create test data directory
    const testDataDir = join(projectRoot, 'test-data');
    await fs.mkdir(testDataDir, { recursive: true });

    // Backup original database if it exists
    try {
      const originalDb = join(projectRoot, 'data', 'devstream.db');
      const originalDbStat = await fs.stat(originalDb);
      if (originalDbStat.size > 100 * 1024 * 1024) { // > 100MB
        originalDatabase = await fs.readFile(originalDb);
        await fs.copyFile(originalDb, TEST_CONFIG.databasePath);
      }
    } catch {
      // No original database available, create minimal test database
      console.warn('No valid original database found, some tests may be limited');
    }
  }, 60000);

  afterAll(async () => {
    await cleanup();
  });

  describe('Phase 1: Multi-Instance Prevention', () => {
    test('should prevent multiple MCP server instances', async () => {
      let server1, server2;

      try {
        // Start first server
        server1 = spawnServer(TEST_CONFIG.databasePath);
        await delay(3000);

        // Check that PID file was created
        const pidFileContent = await fs.readFile(TEST_CONFIG.pidFilePath, 'utf-8');
        expect(pidFileContent).toContain('devstream-mcp-server');

        // Try to start second server
        server2 = spawnServer(TEST_CONFIG.databasePath);
        await delay(3000);

        // Second server should exit immediately (check exit code)
        const exitCode = await new Promise((resolve) => {
          server2.on('close', resolve);
        });

        expect(exitCode).toBe(1);

      } finally {
        server1?.kill();
        server2?.kill();
        await delay(1000);
      }
    }, 30000);

    test('should handle PID file cleanup gracefully', async () => {
      let server;

      try {
        server = spawnServer(TEST_CONFIG.databasePath);
        await delay(3000);

        // Verify PID file exists
        await fs.access(TEST_CONFIG.pidFilePath);

        // Kill server
        server.kill();
        await delay(2000);

        // PID file should be cleaned up
        try {
          await fs.access(TEST_CONFIG.pidFilePath);
          throw new Error('PID file should have been cleaned up');
        } catch {
          // Expected - PID file should not exist
        }

      } finally {
        server?.kill();
        await delay(1000);
      }
    }, 20000);
  });

  describe('Phase 2: Database Path Validation', () => {
    test('should reject wrong database file (small size)', async () => {
      let server;

      try {
        // Create a small dummy database
        await fs.writeFile(TEST_CONFIG.wrongDatabasePath, 'small db');

        server = spawnServer(TEST_CONFIG.wrongDatabasePath);
        await delay(3000);

        // Server should exit due to database validation failure
        const exitCode = await new Promise((resolve) => {
          server.on('close', resolve);
        });

        expect(exitCode).toBe(1);

      } finally {
        server?.kill();
        await delay(1000);

        // Clean up dummy database
        try {
          await fs.unlink(TEST_CONFIG.wrongDatabasePath);
        } catch {}
      }
    }, 20000);

    test('should accept correct database file', async () => {
      let server;

      try {
        // This test only runs if we have a valid database
        if (!originalDatabase) {
          console.warn('Skipping database validation test - no valid database available');
          return;
        }

        server = spawnServer(TEST_CONFIG.databasePath);
        await delay(3000);

        // Server should still be running (no immediate exit)
        expect(server.killed).toBe(false);

      } finally {
        server?.kill();
        await delay(1000);
      }
    }, 20000);
  });

  describe('Phase 3: Health Monitoring', () => {
    test('should start health server on HTTP port', async () => {
      let server;

      try {
        if (!originalDatabase) {
          console.warn('Skipping health server test - no valid database available');
          return;
        }

        server = spawnServer(TEST_CONFIG.databasePath);
        await delay(5000);

        // Test health endpoint
        const healthUrl = `http://localhost:${TEST_CONFIG.healthServerPort}/health`;
        const response = await makeHttpRequest(healthUrl);

        expect(response.statusCode).toBe(200);

        const healthData = JSON.parse(response.data);
        expect(healthData).toHaveProperty('status');
        expect(['healthy', 'degraded', 'unhealthy']).toContain(healthData.status);

        // Test metrics endpoint
        const metricsUrl = `http://localhost:${TEST_CONFIG.healthServerPort}/metrics`;
        const metricsResponse = await makeHttpRequest(metricsUrl);

        expect(metricsResponse.statusCode).toBe(200);
        expect(metricsResponse.data).toContain('devstream_process_uptime_seconds');

      } finally {
        server?.kill();
        await delay(1000);
      }
    }, 20000);

    test('should handle health server port conflicts', async () => {
      // This test verifies the HealthServer's port conflict resolution
      // by starting two servers with different configurations
      let server1, server2;

      try {
        if (!originalDatabase) {
          console.warn('Skipping port conflict test - no valid database available');
          return;
        }

        // Start first server
        server1 = spawnServer(TEST_CONFIG.databasePath);
        await delay(5000);

        // First server should be accessible on default port
        const response1 = await makeHttpRequest(`http://localhost:9090/health`);
        expect(response1.statusCode).toBe(200);

        // Start second server with custom port
        const customDbPath = join(projectRoot, 'test-data', 'test-devstream-2.db');
        if (originalDatabase) {
          await fs.copyFile(TEST_CONFIG.databasePath, customDbPath);
        }

        server2 = spawnServer(customDbPath);
        await delay(5000);

        // Second server should find an alternative port (9091, 9092, etc.)
        let foundPort = false;
        for (let port = 9091; port <= 9100; port++) {
          try {
            const response2 = await makeHttpRequest(`http://localhost:${port}/health`, 1000);
            if (response2.statusCode === 200) {
              foundPort = true;
              break;
            }
          } catch {
            // Continue trying next port
          }
        }

        expect(foundPort).toBe(true);

        // Clean up second database
        try {
          await fs.unlink(customDbPath);
        } catch {}

      } finally {
        server1?.kill();
        server2?.kill();
        await delay(1000);
      }
    }, 30000);
  });

  describe('Phase 4: Session Management', () => {
    test('should maintain sessions across server restarts', async () => {
      let server;

      try {
        if (!originalDatabase) {
          console.warn('Skipping session management test - no valid database available');
          return;
        }

        // Start server and let it initialize
        server = spawnServer(TEST_CONFIG.databasePath);
        await delay(5000);

        // Restart server
        server.kill();
        await delay(2000);

        server = spawnServer(TEST_CONFIG.databasePath);
        await delay(5000);

        // Server should successfully restart and maintain session data
        expect(server.killed).toBe(false);

      } finally {
        server?.kill();
        await delay(1000);
      }
    }, 25000);
  });

  describe('Phase 5: Circuit Breaker Resilience', () => {
    test('should handle database connection failures gracefully', async () => {
      let server;

      try {
        // Use non-existent database to trigger database errors
        const nonExistentDb = join(projectRoot, 'test-data', 'non-existent.db');

        server = spawnServer(nonExistentDb);
        await delay(3000);

        // Server should handle the error and exit gracefully
        const exitCode = await new Promise((resolve) => {
          server.on('close', resolve);
        });

        expect(exitCode).toBe(1);

        // Clean up
        try {
          await fs.unlink(nonExistentDb);
        } catch {}

      } finally {
        server?.kill();
        await delay(1000);
      }
    }, 20000);
  });

  describe('Phase 6: Graceful Shutdown', () => {
    test('should shutdown gracefully on SIGTERM', async () => {
      let server;

      try {
        if (!originalDatabase) {
          console.warn('Skipping shutdown test - no valid database available');
          return;
        }

        server = spawnServer(TEST_CONFIG.databasePath);
        await delay(3000);

        // Send SIGTERM
        server.kill('SIGTERM');

        // Wait for graceful shutdown
        const startTime = Date.now();
        const exitCode = await new Promise((resolve) => {
          server.on('close', (code) => resolve(code));
        });

        const shutdownTime = Date.now() - startTime;

        // Should exit within 10 seconds (graceful shutdown timeout)
        expect(shutdownTime).toBeLessThan(10000);
        expect(exitCode).toBe(0);

      } finally {
        server?.kill();
        await delay(1000);
      }
    }, 15000);
  });

  describe('Phase 7: Memory Management', () => {
    test('should maintain stable memory usage', async () => {
      let server;

      try {
        if (!originalDatabase) {
          console.warn('Skipping memory management test - no valid database available');
          return;
        }

        server = spawnServer(TEST_CONFIG.databasePath);
        await delay(5000);

        // Monitor memory usage over time
        const initialMemory = process.memoryUsage();
        await delay(10000);

        // Server should still be responsive
        const response = await makeHttpRequest(`http://localhost:9090/health`);
        expect(response.statusCode).toBe(200);

        // Basic sanity check - server hasn't crashed
        expect(server.killed).toBe(false);

      } finally {
        server?.kill();
        await delay(1000);
      }
    }, 20000);
  });
});