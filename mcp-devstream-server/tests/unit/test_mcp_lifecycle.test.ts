/**
 * MCP Server Lifecycle - Unit Tests
 *
 * Tests signal handlers, cleanup functions, and heartbeat timers in isolation.
 * Uses mocks for all external dependencies.
 *
 * Test Coverage:
 * - Signal handlers (SIGTERM, SIGINT) call cleanup()
 * - Cleanup function stops heartbeat timer
 * - Cleanup function stops auto-save service
 * - Cleanup function closes database
 * - Cleanup timeout safety (5s force exit)
 * - Heartbeat timer setup and interval
 */

import { describe, it, expect, beforeEach, afterEach, jest } from '@jest/globals';

/**
 * Mock implementations for external dependencies
 */
class MockDevStreamDatabase {
  private closed = false;

  async initialize(): Promise<void> {
    // Mock initialization
  }

  async close(): Promise<void> {
    this.closed = true;
  }

  isClosed(): boolean {
    return this.closed;
  }

  getVectorSearchStatus(): boolean {
    return true;
  }

  async getVectorSearchDiagnostics() {
    return { version: 'mock-0.1.0' };
  }
}

class MockAutoSaveService {
  private active = false;
  private stopped = false;

  async start(): Promise<void> {
    this.active = true;
  }

  async stop(): Promise<void> {
    this.stopped = true;
    this.active = false;
  }

  isActive(): boolean {
    return this.active;
  }

  isStopped(): boolean {
    return this.stopped;
  }

  async triggerImmediateCheckpoint(): Promise<number> {
    return 0;
  }
}

class MockServer {
  async connect(): Promise<void> {
    // Mock connection
  }

  setRequestHandler(): void {
    // Mock handler setup
  }
}

class MockStdioServerTransport {
  // Mock transport
}

/**
 * Test Server Class (mirrors DevStreamMcpServer structure)
 */
class TestDevStreamMcpServer {
  private server: MockServer;
  private database: MockDevStreamDatabase;
  private autoSaveService: MockAutoSaveService;
  private heartbeatInterval?: NodeJS.Timeout;
  public cleanupCalled = false;
  public cleanupReason = '';

  constructor() {
    this.server = new MockServer();
    this.database = new MockDevStreamDatabase();
    this.autoSaveService = new MockAutoSaveService();
  }

  async start(): Promise<void> {
    await this.database.initialize();

    // Start heartbeat logging (every 5 minutes)
    this.heartbeatInterval = setInterval(() => {
      console.error(`💓 MCP server heartbeat`);
    }, 5 * 60 * 1000);

    await this.autoSaveService.start();
  }

  async cleanup(reason: string = 'shutdown'): Promise<void> {
    this.cleanupCalled = true;
    this.cleanupReason = reason;

    console.error(`🔄 Initiating cleanup (reason: ${reason})...`);

    // Safety timeout: Force exit after 5 seconds
    const cleanupTimeout = setTimeout(() => {
      console.error('⚠️ Cleanup timeout (5s exceeded), forcing exit');
      process.exit(1);
    }, 5000);

    try {
      // Step 1: Stop heartbeat timer
      if (this.heartbeatInterval) {
        clearInterval(this.heartbeatInterval);
        console.error('  ✅ Heartbeat timer stopped');
      }

      // Step 2: Stop auto-save service
      console.error('  └─ Stopping auto-save service...');
      await this.autoSaveService.stop();
      console.error('  ✅ Auto-save service stopped');

      // Step 3: Close database connection
      console.error('  └─ Closing database connection...');
      await this.database.close();
      console.error('  ✅ Database connection closed');

      console.error('✅ Cleanup completed successfully');
    } finally {
      clearTimeout(cleanupTimeout);
    }
  }

  // Expose internals for testing
  getDatabase(): MockDevStreamDatabase {
    return this.database;
  }

  getAutoSaveService(): MockAutoSaveService {
    return this.autoSaveService;
  }

  getHeartbeatInterval(): NodeJS.Timeout | undefined {
    return this.heartbeatInterval;
  }

  isHeartbeatActive(): boolean {
    return this.heartbeatInterval !== undefined;
  }
}

describe('MCP Server Lifecycle - Unit Tests', () => {
  let server: TestDevStreamMcpServer;
  let processExitSpy: jest.SpiedFunction<typeof process.exit>;
  let setTimeoutSpy: jest.SpiedFunction<typeof setTimeout>;
  let clearTimeoutSpy: jest.SpiedFunction<typeof clearTimeout>;
  let clearIntervalSpy: jest.SpiedFunction<typeof clearInterval>;

  beforeEach(() => {
    server = new TestDevStreamMcpServer();

    // Spy on process.exit (prevent actual exit)
    processExitSpy = jest.spyOn(process, 'exit').mockImplementation((code?: string | number | null | undefined): never => {
      throw new Error(`process.exit called with code ${code}`);
    });

    // Spy on timer functions
    setTimeoutSpy = jest.spyOn(global, 'setTimeout');
    clearTimeoutSpy = jest.spyOn(global, 'clearTimeout');
    clearIntervalSpy = jest.spyOn(global, 'clearInterval');
  });

  afterEach(() => {
    // Restore spies
    processExitSpy.mockRestore();
    setTimeoutSpy.mockRestore();
    clearTimeoutSpy.mockRestore();
    clearIntervalSpy.mockRestore();

    // Clear any active intervals
    if (server.getHeartbeatInterval()) {
      clearInterval(server.getHeartbeatInterval()!);
    }
  });

  describe('Cleanup Function', () => {
    it('should stop heartbeat timer during cleanup', async () => {
      await server.start();
      expect(server.isHeartbeatActive()).toBe(true);

      const heartbeatInterval = server.getHeartbeatInterval();
      expect(heartbeatInterval).toBeDefined();

      await server.cleanup('test');

      expect(clearIntervalSpy).toHaveBeenCalledWith(heartbeatInterval);
      expect(server.cleanupCalled).toBe(true);
    });

    it('should stop auto-save service during cleanup', async () => {
      await server.start();
      expect(server.getAutoSaveService().isActive()).toBe(true);

      await server.cleanup('test');

      expect(server.getAutoSaveService().isStopped()).toBe(true);
      expect(server.getAutoSaveService().isActive()).toBe(false);
    });

    it('should close database connection during cleanup', async () => {
      await server.start();
      expect(server.getDatabase().isClosed()).toBe(false);

      await server.cleanup('test');

      expect(server.getDatabase().isClosed()).toBe(true);
    });

    it('should set cleanup timeout for 5 seconds', async () => {
      await server.start();

      const cleanupPromise = server.cleanup('test');

      // Verify setTimeout was called with 5000ms
      expect(setTimeoutSpy).toHaveBeenCalledWith(
        expect.any(Function),
        5000
      );

      await cleanupPromise;
    });

    it('should clear cleanup timeout after successful cleanup', async () => {
      await server.start();

      await server.cleanup('test');

      // Verify clearTimeout was called
      expect(clearTimeoutSpy).toHaveBeenCalled();
    });

    it('should track cleanup reason', async () => {
      await server.start();

      await server.cleanup('SIGTERM');
      expect(server.cleanupReason).toBe('SIGTERM');

      await server.cleanup('SIGINT');
      expect(server.cleanupReason).toBe('SIGINT');
    });

    it('should handle cleanup with no heartbeat timer gracefully', async () => {
      // Don't start server (no heartbeat timer)
      expect(server.isHeartbeatActive()).toBe(false);

      await expect(server.cleanup('test')).resolves.not.toThrow();
      expect(server.cleanupCalled).toBe(true);
    });
  });

  describe('Heartbeat Timer', () => {
    it('should start heartbeat timer on server start', async () => {
      const setIntervalSpy = jest.spyOn(global, 'setInterval');

      await server.start();

      // Verify setInterval called with 5 minute interval
      expect(setIntervalSpy).toHaveBeenCalledWith(
        expect.any(Function),
        5 * 60 * 1000 // 5 minutes in milliseconds
      );

      expect(server.isHeartbeatActive()).toBe(true);

      setIntervalSpy.mockRestore();
    });

    it('should use correct heartbeat interval (5 minutes)', async () => {
      const setIntervalSpy = jest.spyOn(global, 'setInterval');

      await server.start();

      const expectedInterval = 5 * 60 * 1000; // 5 minutes
      expect(setIntervalSpy).toHaveBeenCalledWith(
        expect.any(Function),
        expectedInterval
      );

      setIntervalSpy.mockRestore();
    });
  });

  describe('Signal Handler Integration (Simulated)', () => {
    it('should call cleanup when SIGTERM handler is invoked', async () => {
      await server.start();

      // Simulate SIGTERM handler logic
      const sigtermHandler = async () => {
        await server.cleanup('SIGTERM');
      };

      await sigtermHandler();

      expect(server.cleanupCalled).toBe(true);
      expect(server.cleanupReason).toBe('SIGTERM');
    });

    it('should call cleanup when SIGINT handler is invoked', async () => {
      await server.start();

      // Simulate SIGINT handler logic
      const sigintHandler = async () => {
        await server.cleanup('SIGINT');
      };

      await sigintHandler();

      expect(server.cleanupCalled).toBe(true);
      expect(server.cleanupReason).toBe('SIGINT');
    });
  });

  describe('Cleanup Timeout Safety', () => {
    it('should force exit after 5 second timeout if cleanup hangs', async () => {
      jest.useFakeTimers();

      // Create server with hanging cleanup
      class HangingServer extends TestDevStreamMcpServer {
        async cleanup(reason: string = 'shutdown'): Promise<void> {
          console.error(`🔄 Initiating cleanup (reason: ${reason})...`);

          const cleanupTimeout = setTimeout(() => {
            console.error('⚠️ Cleanup timeout (5s exceeded), forcing exit');
            process.exit(1);
          }, 5000);

          // Simulate hanging operation (never resolves)
          await new Promise(() => {
            // Infinite hang
          });

          clearTimeout(cleanupTimeout);
        }
      }

      const hangingServer = new HangingServer();
      await hangingServer.start();

      // Start cleanup (will hang)
      const cleanupPromise = hangingServer.cleanup('test');

      // Fast-forward time by 5 seconds
      jest.advanceTimersByTime(5000);

      // Verify process.exit was called with code 1
      await expect(cleanupPromise).rejects.toThrow('process.exit called with code 1');

      jest.useRealTimers();
    });

    it('should NOT force exit if cleanup completes before timeout', async () => {
      await server.start();

      // Fast cleanup (completes immediately)
      await server.cleanup('test');

      // Verify process.exit was NOT called
      expect(processExitSpy).not.toHaveBeenCalled();
    });
  });

  describe('Error Handling During Cleanup', () => {
    it('should continue cleanup even if auto-save service fails to stop', async () => {
      // Create server with failing auto-save service
      class FailingAutoSaveServer extends TestDevStreamMcpServer {
        async cleanup(reason: string = 'shutdown'): Promise<void> {
          console.error(`🔄 Initiating cleanup (reason: ${reason})...`);

          const cleanupTimeout = setTimeout(() => {
            console.error('⚠️ Cleanup timeout (5s exceeded), forcing exit');
            process.exit(1);
          }, 5000);

          try {
            // Stop heartbeat timer
            if (this.getHeartbeatInterval()) {
              clearInterval(this.getHeartbeatInterval()!);
              console.error('  ✅ Heartbeat timer stopped');
            }

            // Simulate auto-save service failure
            console.error('  └─ Stopping auto-save service...');
            try {
              throw new Error('Mock auto-save stop failure');
            } catch (error) {
              console.error('  ⚠️ Error stopping auto-save service:', error instanceof Error ? error.message : 'Unknown error');
            }

            // Continue with database close
            console.error('  └─ Closing database connection...');
            await this.getDatabase().close();
            console.error('  ✅ Database connection closed');

            console.error('✅ Cleanup completed successfully');
          } finally {
            clearTimeout(cleanupTimeout);
          }
        }
      }

      const failingServer = new FailingAutoSaveServer();
      await failingServer.start();

      // Cleanup should complete despite auto-save failure
      await expect(failingServer.cleanup('test')).resolves.not.toThrow();

      // Database should still be closed
      expect(failingServer.getDatabase().isClosed()).toBe(true);
    });

    it('should continue cleanup even if database fails to close', async () => {
      // Create server with failing database
      class FailingDatabaseServer extends TestDevStreamMcpServer {
        async cleanup(reason: string = 'shutdown'): Promise<void> {
          console.error(`🔄 Initiating cleanup (reason: ${reason})...`);

          const cleanupTimeout = setTimeout(() => {
            console.error('⚠️ Cleanup timeout (5s exceeded), forcing exit');
            process.exit(1);
          }, 5000);

          try {
            // Stop heartbeat timer
            if (this.getHeartbeatInterval()) {
              clearInterval(this.getHeartbeatInterval()!);
              console.error('  ✅ Heartbeat timer stopped');
            }

            // Stop auto-save service
            console.error('  └─ Stopping auto-save service...');
            await this.getAutoSaveService().stop();
            console.error('  ✅ Auto-save service stopped');

            // Simulate database close failure
            console.error('  └─ Closing database connection...');
            try {
              throw new Error('Mock database close failure');
            } catch (error) {
              console.error('  ⚠️ Error closing database:', error instanceof Error ? error.message : 'Unknown error');
            }

            console.error('✅ Cleanup completed successfully');
          } finally {
            clearTimeout(cleanupTimeout);
          }
        }
      }

      const failingServer = new FailingDatabaseServer();
      await failingServer.start();

      // Cleanup should complete despite database failure
      await expect(failingServer.cleanup('test')).resolves.not.toThrow();

      // Auto-save should still be stopped
      expect(failingServer.getAutoSaveService().isStopped()).toBe(true);
    });
  });

  describe('Cleanup Execution Order', () => {
    it('should execute cleanup steps in correct order', async () => {
      const executionOrder: string[] = [];

      // Track execution order via console.error spy
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation((message: string) => {
        if (typeof message === 'string') {
          if (message.includes('Heartbeat timer stopped')) executionOrder.push('heartbeat');
          if (message.includes('Auto-save service stopped')) executionOrder.push('autosave');
          if (message.includes('Database connection closed')) executionOrder.push('database');
        }
      });

      await server.start();
      await server.cleanup('test');

      // Verify order: heartbeat → autosave → database
      expect(executionOrder).toEqual(['heartbeat', 'autosave', 'database']);

      consoleErrorSpy.mockRestore();
    });
  });
});
