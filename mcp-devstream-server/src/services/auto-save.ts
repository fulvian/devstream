/**
 * DevStream Auto-Save Background Task Service
 *
 * Periodically saves checkpoints for active tasks to enable progress tracking
 * and recovery. Implements non-blocking background processing with graceful
 * shutdown and comprehensive error handling.
 *
 * Context7 Pattern: Async background task with interval-based execution,
 * similar to Node.js production-ready cron services.
 *
 * Architecture:
 * - Runs every 5 minutes (300s interval)
 * - Queries active tasks from database
 * - Creates checkpoint entries in semantic_memory
 * - Non-blocking execution (doesn't block MCP server)
 * - Graceful shutdown on server stop
 * - Error isolation (failures don't crash service)
 */

import { DevStreamDatabase, MicroTask } from '../database.js';

/**
 * Checkpoint data structure stored in semantic memory
 */
interface TaskCheckpoint {
  task_id: string;
  task_title: string;
  phase_name: string;
  status: string;
  priority: number;
  started_at: string | null;
  elapsed_minutes: number | null;
  checkpoint_timestamp: string;
  checkpoint_reason: 'auto_save' | 'manual' | 'status_change' | 'tool_trigger' | 'shutdown';
}

/**
 * Auto-save service configuration
 */
interface AutoSaveConfig {
  intervalMs: number;           // Interval between auto-saves (default: 300000ms = 5min)
  enabled: boolean;             // Enable/disable auto-save
  checkpointContentType: string; // Content type for checkpoints (default: 'context')
}

/**
 * Auto-Save Background Task Service
 *
 * Manages periodic checkpointing of active tasks for progress tracking.
 * Implements production-ready patterns: non-blocking execution, graceful
 * shutdown, error isolation, structured logging.
 */
export class AutoSaveService {
  private database: DevStreamDatabase;
  private config: AutoSaveConfig;
  private intervalId: NodeJS.Timeout | null = null;
  private isRunning: boolean = false;
  private isShuttingDown: boolean = false;

  /**
   * Initialize auto-save service
   *
   * @param database - DevStream database connection
   * @param config - Service configuration (optional)
   */
  constructor(database: DevStreamDatabase, config?: Partial<AutoSaveConfig>) {
    this.database = database;
    this.config = {
      intervalMs: config?.intervalMs ?? 300000, // Default: 5 minutes
      enabled: config?.enabled ?? true,
      checkpointContentType: config?.checkpointContentType ?? 'context'
    };
  }

  /**
   * Start auto-save background task
   *
   * Context7 Pattern: Use setInterval for periodic execution with proper
   * cleanup handling. Non-blocking execution ensures MCP server remains
   * responsive.
   *
   * @throws Error if service is already running
   */
  async start(): Promise<void> {
    if (this.isRunning) {
      throw new Error('Auto-save service is already running');
    }

    if (!this.config.enabled) {
      console.error('⏸️  Auto-save service is disabled (config.enabled = false)');
      return;
    }

    this.isRunning = true;
    this.isShuttingDown = false;

    console.error(`🔄 Auto-save service started (interval: ${this.config.intervalMs / 1000}s)`);

    // Run initial checkpoint immediately
    await this.executeCheckpointCycle().catch(error => {
      console.error('⚠️  Initial checkpoint failed:', error instanceof Error ? error.message : 'Unknown error');
    });

    // Schedule periodic checkpoints
    this.intervalId = setInterval(async () => {
      if (this.isShuttingDown) {
        return; // Skip execution during shutdown
      }

      await this.executeCheckpointCycle().catch(error => {
        // Context7 Pattern: Log error but continue service execution
        // Individual failures should not crash the background service
        console.error('⚠️  Checkpoint cycle failed:', error instanceof Error ? error.message : 'Unknown error');
      });
    }, this.config.intervalMs);
  }

  /**
   * Stop auto-save background task with graceful shutdown
   *
   * Context7 Pattern: Graceful shutdown ensures in-progress operations
   * complete before termination. Uses flag-based coordination to prevent
   * new cycles from starting during shutdown.
   */
  async stop(): Promise<void> {
    if (!this.isRunning) {
      return;
    }

    console.error('🛑 Stopping auto-save service (graceful shutdown)...');
    this.isShuttingDown = true;

    // Clear interval to prevent new cycles
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }

    // Wait for any in-progress checkpoint to complete (max 10s)
    const shutdownTimeout = 10000; // 10 seconds
    const startTime = Date.now();

    while (this.isRunning && (Date.now() - startTime) < shutdownTimeout) {
      await new Promise(resolve => setTimeout(resolve, 100)); // Poll every 100ms
    }

    this.isRunning = false;
    console.error('✅ Auto-save service stopped');
  }

  /**
   * Execute single checkpoint cycle for all active tasks
   *
   * Context7 Pattern: Transactional checkpoint creation with error isolation.
   * Each task checkpoint is independent - failure of one doesn't affect others.
   *
   * @returns Number of checkpoints created
   */
  private async executeCheckpointCycle(): Promise<number> {
    try {
      // Query all active tasks from database
      const activeTasks = await this.getActiveTasks();

      if (activeTasks.length === 0) {
        console.error('ℹ️  No active tasks found - skipping checkpoint cycle');
        return 0;
      }

      console.error(`🔄 Checkpoint cycle started (${activeTasks.length} active tasks)`);

      // Create checkpoint for each active task
      let successCount = 0;
      let failureCount = 0;

      for (const task of activeTasks) {
        try {
          await this.createTaskCheckpoint(task);
          successCount++;
        } catch (error) {
          // Context7 Pattern: Log error but continue processing other tasks
          failureCount++;
          console.error(`⚠️  Checkpoint failed for task ${task.id}:`, error instanceof Error ? error.message : 'Unknown error');
        }
      }

      console.error(`✅ Checkpoint cycle completed (${successCount} success, ${failureCount} failures)`);
      return successCount;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      throw new Error(`Checkpoint cycle execution failed: ${errorMessage}`);
    }
  }

  /**
   * Query all active tasks from database
   *
   * Context7 Pattern: JOIN query to retrieve task context (phase, project)
   * for comprehensive checkpoint data.
   *
   * @returns Array of active tasks with context
   */
  private async getActiveTasks(): Promise<(MicroTask & { phase_name: string; project_title: string })[]> {
    const sql = `
      SELECT
        mt.*,
        p.name as phase_name,
        ip.title as project_title
      FROM micro_tasks mt
      JOIN phases p ON mt.phase_id = p.id
      JOIN intervention_plans ip ON p.plan_id = ip.id
      WHERE mt.status = 'active'
      ORDER BY mt.priority DESC, mt.started_at ASC
    `;

    return this.database.query<MicroTask & { phase_name: string; project_title: string }>(sql, []);
  }

  /**
   * Create checkpoint entry for a specific task
   *
   * Context7 Pattern: Store checkpoint in semantic_memory table with
   * structured metadata. Enables progress tracking, recovery, and analytics.
   *
   * @param task - Task to checkpoint
   */
  private async createTaskCheckpoint(task: MicroTask & { phase_name: string; project_title: string }): Promise<void> {
    // Delegate to parameterized method with 'auto_save' reason
    await this.createTaskCheckpointWithReason(task, 'auto_save');
  }

  /**
   * Format checkpoint data as human-readable content
   *
   * Context7 Pattern: Store both structured (context_snapshot) and
   * readable (content) representations for flexibility.
   *
   * @param checkpoint - Checkpoint data
   * @returns Formatted content string
   */
  private formatCheckpointContent(checkpoint: TaskCheckpoint): string {
    return `
Task Checkpoint (Auto-Save)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task:       ${checkpoint.task_title}
Phase:      ${checkpoint.phase_name}
Status:     ${checkpoint.status.toUpperCase()}
Priority:   ${checkpoint.priority}/10
Started:    ${checkpoint.started_at ?? 'Not started'}
Elapsed:    ${checkpoint.elapsed_minutes ?? 'N/A'} minutes
Checkpoint: ${checkpoint.checkpoint_timestamp}
Reason:     ${checkpoint.checkpoint_reason}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`.trim();
  }

  /**
   * Generate unique ID for database records
   *
   * Context7 Pattern: Use crypto.randomBytes for secure ID generation
   * matching DevStream database ID format.
   *
   * @returns 32-character hexadecimal ID
   */
  private generateId(): string {
    return require('crypto').randomBytes(16).toString('hex');
  }

  /**
   * Check if service is currently running
   *
   * @returns true if service is running
   */
  isActive(): boolean {
    return this.isRunning && !this.isShuttingDown;
  }

  /**
   * Get current service configuration
   *
   * @returns Service configuration
   */
  getConfig(): Readonly<AutoSaveConfig> {
    return { ...this.config };
  }

  /**
   * Update service configuration (requires restart)
   *
   * @param newConfig - Partial configuration to update
   */
  updateConfig(newConfig: Partial<AutoSaveConfig>): void {
    if (this.isRunning) {
      throw new Error('Cannot update config while service is running. Stop service first.');
    }

    this.config = { ...this.config, ...newConfig };
  }

  /**
   * Trigger immediate checkpoint for all active tasks
   *
   * Context7 Pattern: Public API for on-demand checkpoint creation.
   * Used by PostToolUse hook to save progress after critical tool executions.
   *
   * Use Cases:
   * - Critical tool execution (Write, Edit, Bash, TodoWrite)
   * - Manual checkpoint request
   * - Pre-shutdown checkpoint
   *
   * @param reason - Reason for checkpoint (default: 'manual')
   * @returns Number of checkpoints created
   * @throws Error if checkpoint cycle fails
   */
  async triggerImmediateCheckpoint(reason: 'manual' | 'tool_trigger' | 'shutdown' = 'manual'): Promise<number> {
    try {
      console.error(`🔄 Immediate checkpoint triggered (reason: ${reason})`);

      // Query all active tasks
      const activeTasks = await this.getActiveTasks();

      if (activeTasks.length === 0) {
        console.error('ℹ️  No active tasks found - skipping checkpoint');
        return 0;
      }

      // Create checkpoint for each active task with custom reason
      let successCount = 0;
      let failureCount = 0;

      for (const task of activeTasks) {
        try {
          await this.createTaskCheckpointWithReason(task, reason);
          successCount++;
        } catch (error) {
          failureCount++;
          console.error(`⚠️  Checkpoint failed for task ${task.id}:`, error instanceof Error ? error.message : 'Unknown error');
        }
      }

      console.error(`✅ Immediate checkpoint completed (${successCount} success, ${failureCount} failures)`);
      return successCount;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      throw new Error(`Immediate checkpoint failed: ${errorMessage}`);
    }
  }

  /**
   * Create checkpoint with custom reason (extracted from createTaskCheckpoint)
   *
   * Context7 Pattern: Parameterized checkpoint creation for different trigger sources.
   *
   * @param task - Task to checkpoint
   * @param reason - Checkpoint reason
   */
  private async createTaskCheckpointWithReason(
    task: MicroTask & { phase_name: string; project_title: string },
    reason: 'auto_save' | 'manual' | 'tool_trigger' | 'status_change' | 'shutdown'
  ): Promise<void> {
    // Calculate elapsed time if task has started
    let elapsedMinutes: number | null = null;
    if (task.started_at) {
      const startTime = new Date(task.started_at).getTime();
      const currentTime = Date.now();
      elapsedMinutes = Math.round((currentTime - startTime) / 60000); // Convert ms to minutes
    }

    // Build checkpoint data structure
    const checkpoint: TaskCheckpoint = {
      task_id: task.id,
      task_title: task.title,
      phase_name: task.phase_name,
      status: task.status,
      priority: task.priority,
      started_at: task.started_at,
      elapsed_minutes: elapsedMinutes,
      checkpoint_timestamp: new Date().toISOString(),
      checkpoint_reason: reason
    };

    // Generate checkpoint ID
    const checkpointId = this.generateId();

    // Store checkpoint in semantic_memory
    await this.database.execute(`
      INSERT INTO semantic_memory (
        id, task_id, content, content_type, content_format, keywords,
        relevance_score, access_count, context_snapshot
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `, [
      checkpointId,
      task.id,
      this.formatCheckpointContent(checkpoint),
      this.config.checkpointContentType,
      'json',
      JSON.stringify(['checkpoint', reason, 'progress', task.status]),
      0.8, // High relevance for checkpoint data
      0,   // Initial access count
      JSON.stringify(checkpoint) // Full structured checkpoint data
    ]);

    console.error(`✅ Checkpoint created for task "${task.title}" (elapsed: ${elapsedMinutes ?? 'N/A'} min, reason: ${reason})`);
  }
}
