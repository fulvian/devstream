/**
 * Integration Test Setup
 *
 * Global setup and teardown for MCP server integration tests.
 * Handles cleanup of test processes, databases, and temporary files.
 */

import { spawn } from 'child_process';
import fs from 'fs/promises';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..', '..');

// Test configuration
const TEST_CONFIG = {
  pidFilePath: '/tmp/devstream-mcp-server.pid',
  testDataDir: join(projectRoot, 'test-data'),
  serverPath: join(projectRoot, 'dist', 'index.js')
};

// Global cleanup function
async function globalCleanup() {
  console.log('🧹 Global integration test cleanup started...');

  // 1. Kill any running MCP server processes
  console.log('  🔄 Terminating MCP server processes...');
  try {
    const { exec } = require('child_process');
    await new Promise((resolve, reject) => {
      exec(`pkill -f "node.*${TEST_CONFIG.serverPath}" || true`, (error, stdout, stderr) => {
        if (error && !error.message.includes('No such process')) {
          console.warn('    ⚠️ Process termination warning:', error.message);
        }
        resolve();
      });
    });

    // Give processes time to terminate
    await new Promise(resolve => setTimeout(resolve, 2000));
  } catch (error) {
    console.warn('    ⚠️ Process cleanup error:', error.message);
  }

  // 2. Clean up PID file
  console.log('  🗑️  Cleaning up PID files...');
  try {
    await fs.unlink(TEST_CONFIG.pidFilePath);
  } catch {
    // PID file might not exist - that's fine
  }

  // 3. Clean up test data directory
  console.log('  🗑️  Cleaning up test data...');
  try {
    const files = await fs.readdir(TEST_CONFIG.testDataDir);
    for (const file of files) {
      const filePath = join(TEST_CONFIG.testDataDir, file);
      const stat = await fs.stat(filePath);
      if (stat.isFile()) {
        await fs.unlink(filePath);
      }
    }
  } catch {
    // Test directory might not exist - that's fine
  }

  // 4. Force cleanup of any remaining node processes (safety net)
  console.log('  🔄 Final safety cleanup...');
  try {
    const { exec } = require('child_process');
    await new Promise((resolve) => {
      exec('pkill -f "devstream-mcp-server" || true', resolve);
    });
  } catch {
    // Ignore errors in final cleanup
  }

  console.log('✅ Global integration test cleanup completed');
}

// Global setup function
async function globalSetup() {
  console.log('🚀 Global integration test setup started...');

  // 1. Create test data directory
  console.log('  📁 Creating test data directory...');
  try {
    await fs.mkdir(TEST_CONFIG.testDataDir, { recursive: true });
  } catch (error) {
    console.warn('    ⚠️ Test directory creation warning:', error.message);
  }

  // 2. Ensure clean state
  console.log('  🧹 Ensuring clean test environment...');
  await globalCleanup();

  console.log('✅ Global integration test setup completed');
}

// Jest global setup
if (global.beforeAll) {
  beforeAll(async () => {
    await globalSetup();
  }, 60000); // 60 seconds timeout for global setup

  afterAll(async () => {
    await globalCleanup();
  }, 30000); // 30 seconds timeout for global cleanup
}

// Export for direct usage
export { globalSetup, globalCleanup };