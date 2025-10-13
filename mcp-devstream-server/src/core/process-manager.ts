/**
 * Process Manager for MCP Server Singleton Enforcement
 *
 * Prevents multiple MCP server instances using PID file locking
 * Provides graceful shutdown and cleanup mechanisms
 */

import fs from 'fs';
import path from 'path';

export class ProcessManager {
    private static readonly PID_FILE = '/tmp/devstream-mcp-server.pid';
    private static readonly LOCK_TIMEOUT = 30000; // 30 seconds
    private static shutdownHandler: NodeJS.Timeout | null = null;

    /**
     * Check if another instance is running and acquire lock
     * @returns {boolean} True if lock acquired successfully
     */
    static async acquireLock(): Promise<boolean> {
        try {
            // Check if PID file exists
            if (fs.existsSync(this.PID_FILE)) {
                const existingPid = parseInt(fs.readFileSync(this.PID_FILE, 'utf8').trim());

                // Check if process is actually running
                if (this.isProcessRunning(existingPid)) {
                    console.error(`❌ MCP server already running (PID: ${existingPid})`);
                    return false;
                } else {
                    // Stale PID file, remove it
                    console.error(`⚠️ Stale PID file found, removing...`);
                    fs.unlinkSync(this.PID_FILE);
                }
            }

            // Write current PID to file
            const currentPid = process.pid;
            fs.writeFileSync(this.PID_FILE, currentPid.toString());

            // Set up cleanup handlers
            this.setupCleanupHandlers();

            console.error(`✅ MCP server lock acquired (PID: ${currentPid})`);
            return true;

        } catch (error) {
            console.error(`❌ Failed to acquire process lock: ${error}`);
            return false;
        }
    }

    /**
     * Check if a process with given PID is running
     */
    private static isProcessRunning(pid: number): boolean {
        try {
            // Try to send signal 0 to check if process exists
            process.kill(pid, 0);
            return true;
        } catch {
            return false;
        }
    }

    /**
     * Setup cleanup handlers for graceful shutdown
     */
    private static setupCleanupHandlers(): void {
        // Handle SIGINT (Ctrl+C)
        process.on('SIGINT', () => {
            console.error('🛑 SIGINT received, initiating graceful shutdown...');
            this.cleanup('SIGINT');
        });

        // Handle SIGTERM (kill command)
        process.on('SIGTERM', () => {
            console.error('🛑 SIGTERM received, initiating graceful shutdown...');
            this.cleanup('SIGTERM');
        });

        // Handle process exit
        process.on('exit', () => {
            this.cleanup('process-exit');
        });

        // Handle uncaught exceptions
        process.on('uncaughtException', (error) => {
            console.error('💥 Uncaught exception:', error);
            this.cleanup('uncaught-exception');
        });
    }

    /**
     * Cleanup PID file and other resources
     */
    static cleanup(reason: string): void {
        try {
            if (fs.existsSync(this.PID_FILE)) {
                fs.unlinkSync(this.PID_FILE);
                console.error(`✅ Process lock cleaned up (reason: ${reason})`);
            }
        } catch (error) {
            console.error(`❌ Failed to cleanup process lock: ${error}`);
        }

        // Cancel any pending shutdown
        if (this.shutdownHandler) {
            clearTimeout(this.shutdownHandler);
            this.shutdownHandler = null;
        }
    }

    /**
     * Force remove stale PID file
     */
    static forceCleanup(): void {
        try {
            if (fs.existsSync(this.PID_FILE)) {
                const pid = parseInt(fs.readFileSync(this.PID_FILE, 'utf8').trim());
                console.error(`🔧 Force removing stale PID file (PID: ${pid})`);
                fs.unlinkSync(this.PID_FILE);
            }
        } catch (error) {
            console.error(`❌ Failed to force cleanup: ${error}`);
        }
    }
}