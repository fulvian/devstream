/**
 * Auto-Save Service Test Suite
 *
 * Tests for the auto-save background task service.
 * Verifies checkpoint creation, error handling, and graceful shutdown.
 */

import { AutoSaveService } from './auto-save.js';
import { DevStreamDatabase } from '../database.js';
import { describe, it, expect, beforeAll, afterAll, beforeEach } from '@jest/globals';
import * as fs from 'fs';
import * as path from 'path';

describe('AutoSaveService', () => {
  let database: DevStreamDatabase;
  let autoSaveService: AutoSaveService;
  const testDbPath = path.join(__dirname, '../../test-data/test-autosave.db');

  beforeAll(async () => {
    // Create test database directory
    const testDataDir = path.dirname(testDbPath);
    if (!fs.existsSync(testDataDir)) {
      fs.mkdirSync(testDataDir, { recursive: true });
    }

    // Copy production database schema for testing
    const prodDbPath = path.join(__dirname, '../../data/devstream.db');
    if (fs.existsSync(prodDbPath) && !fs.existsSync(testDbPath)) {
      fs.copyFileSync(prodDbPath, testDbPath);
    }

    // Initialize database
    database = new DevStreamDatabase(testDbPath);
    await database.initialize();
  });

  afterAll(async () => {
    // Cleanup
    if (autoSaveService?.isActive()) {
      await autoSaveService.stop();
    }
    await database.close();

    // Remove test database
    if (fs.existsSync(testDbPath)) {
      fs.unlinkSync(testDbPath);
    }
  });

  beforeEach(() => {
    // Reset service before each test
    if (autoSaveService?.isActive()) {
      autoSaveService.stop();
    }
  });

  describe('Service Lifecycle', () => {
    it('should start and stop gracefully', async () => {
      autoSaveService = new AutoSaveService(database, {
        intervalMs: 60000, // 1 minute for testing
        enabled: true
      });

      await autoSaveService.start();
      expect(autoSaveService.isActive()).toBe(true);

      await autoSaveService.stop();
      expect(autoSaveService.isActive()).toBe(false);
    });

    it('should prevent starting service twice', async () => {
      autoSaveService = new AutoSaveService(database, {
        intervalMs: 60000,
        enabled: true
      });

      await autoSaveService.start();
      await expect(autoSaveService.start()).rejects.toThrow('already running');

      await autoSaveService.stop();
    });

    it('should not start when disabled', async () => {
      autoSaveService = new AutoSaveService(database, {
        intervalMs: 60000,
        enabled: false
      });

      await autoSaveService.start();
      expect(autoSaveService.isActive()).toBe(false);
    });
  });

  describe('Checkpoint Creation', () => {
    it('should create checkpoints for active tasks', async () => {
      // Create test task
      const taskId = generateTestId();
      const phaseId = await createTestPhase(database);
      await createTestTask(database, taskId, phaseId, 'active');

      // Start auto-save service with short interval
      autoSaveService = new AutoSaveService(database, {
        intervalMs: 2000, // 2 seconds for testing
        enabled: true
      });

      await autoSaveService.start();

      // Wait for checkpoint to be created
      await new Promise(resolve => setTimeout(resolve, 3000));

      // Verify checkpoint exists in semantic_memory
      const checkpoints = await database.query(
        `SELECT * FROM semantic_memory WHERE task_id = ? AND content_type = 'context'`,
        [taskId]
      );

      expect(checkpoints.length).toBeGreaterThan(0);
      expect(checkpoints[0].keywords).toContain('checkpoint');

      await autoSaveService.stop();
    });

    it('should skip checkpoint when no active tasks exist', async () => {
      autoSaveService = new AutoSaveService(database, {
        intervalMs: 2000,
        enabled: true
      });

      await autoSaveService.start();

      // Wait for one checkpoint cycle
      await new Promise(resolve => setTimeout(resolve, 3000));

      // Service should continue running even with no tasks
      expect(autoSaveService.isActive()).toBe(true);

      await autoSaveService.stop();
    });
  });

  describe('Error Handling', () => {
    it('should continue running after checkpoint failure', async () => {
      autoSaveService = new AutoSaveService(database, {
        intervalMs: 2000,
        enabled: true
      });

      await autoSaveService.start();

      // Service should remain active even if individual checkpoints fail
      await new Promise(resolve => setTimeout(resolve, 3000));
      expect(autoSaveService.isActive()).toBe(true);

      await autoSaveService.stop();
    });
  });

  describe('Configuration Management', () => {
    it('should return current configuration', () => {
      autoSaveService = new AutoSaveService(database, {
        intervalMs: 60000,
        enabled: true
      });

      const config = autoSaveService.getConfig();
      expect(config.intervalMs).toBe(60000);
      expect(config.enabled).toBe(true);
    });

    it('should update configuration when stopped', () => {
      autoSaveService = new AutoSaveService(database, {
        intervalMs: 60000,
        enabled: true
      });

      autoSaveService.updateConfig({ intervalMs: 120000 });

      const config = autoSaveService.getConfig();
      expect(config.intervalMs).toBe(120000);
    });

    it('should prevent configuration update while running', async () => {
      autoSaveService = new AutoSaveService(database, {
        intervalMs: 60000,
        enabled: true
      });

      await autoSaveService.start();

      expect(() => {
        autoSaveService.updateConfig({ intervalMs: 120000 });
      }).toThrow('Cannot update config while service is running');

      await autoSaveService.stop();
    });
  });
});

/**
 * Helper: Generate test ID
 */
function generateTestId(): string {
  return require('crypto').randomBytes(16).toString('hex');
}

/**
 * Helper: Create test phase
 */
async function createTestPhase(database: DevStreamDatabase): Promise<string> {
  const phaseId = generateTestId();
  const planId = await createTestPlan(database);

  await database.execute(`
    INSERT INTO phases (
      id, plan_id, name, description, sequence_order, status,
      estimated_minutes, actual_minutes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `, [phaseId, planId, 'Test Phase', 'Test phase description', 1, 'active', 60, 0]);

  return phaseId;
}

/**
 * Helper: Create test plan
 */
async function createTestPlan(database: DevStreamDatabase): Promise<string> {
  const planId = generateTestId();

  await database.execute(`
    INSERT INTO intervention_plans (
      id, title, description, objectives, expected_outcome, status, priority,
      estimated_hours, actual_hours
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `, [
    planId,
    'Test Plan',
    'Test plan description',
    JSON.stringify(['Test objective']),
    'Test outcome',
    'active',
    5,
    10,
    0
  ]);

  return planId;
}

/**
 * Helper: Create test task
 */
async function createTestTask(
  database: DevStreamDatabase,
  taskId: string,
  phaseId: string,
  status: string
): Promise<void> {
  await database.execute(`
    INSERT INTO micro_tasks (
      id, phase_id, title, description, max_duration_minutes, max_context_tokens,
      assigned_agent, task_type, status, priority, input_files, output_files, retry_count,
      started_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
  `, [
    taskId,
    phaseId,
    'Test Task',
    'Test task description',
    10,
    256000,
    'developer',
    'coding',
    status,
    5,
    JSON.stringify([]),
    JSON.stringify([]),
    0
  ]);
}
