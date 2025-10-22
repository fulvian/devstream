/**
 * DevStream Task Management Tools
 *
 * MCP tools for managing DevStream tasks through natural language commands.
 */

import { DevStreamDatabase, MicroTask, Phase, InterventionPlan } from '../database.js';
import { z } from 'zod';

// Input validation schemas
const ListTasksInputSchema = z.object({
  status: z.enum(['pending', 'active', 'completed', 'failed', 'skipped']).optional(),
  project: z.string().optional(),
  priority: z.number().min(1).max(10).optional()
});

const CreateTaskInputSchema = z.object({
  title: z.string().min(1),
  description: z.string().min(1),
  task_type: z.enum(['analysis', 'coding', 'documentation', 'testing', 'review', 'research']),
  priority: z.number().min(1).max(10),
  phase_name: z.string().min(1),
  project: z.string().optional().default('RUSTY Trading Platform Development')
});

const UpdateTaskInputSchema = z.object({
  task_id: z.string().min(1),
  status: z.enum(['pending', 'active', 'completed', 'failed', 'skipped']),
  notes: z.string().optional()
});

export class TaskTools {
  constructor(private database: DevStreamDatabase) {}

  /**
   * List all DevStream tasks with optional filtering
   */
  async listTasks(args: any) {
    try {
      const input = ListTasksInputSchema.parse(args);

      // Build SQL query with optional filters
      let sql = `
        SELECT
          mt.*,
          p.name as phase_name,
          ip.title as project_title
        FROM micro_tasks mt
        JOIN phases p ON mt.phase_id = p.id
        JOIN intervention_plans ip ON p.plan_id = ip.id
      `;

      const conditions: string[] = [];
      const params: any[] = [];

      if (input.status) {
        conditions.push('mt.status = ?');
        params.push(input.status);
      }

      if (input.project) {
        conditions.push('ip.title LIKE ?');
        params.push(`%${input.project}%`);
      }

      if (input.priority) {
        conditions.push('mt.priority >= ?');
        params.push(input.priority);
      }

      if (conditions.length > 0) {
        sql += ' WHERE ' + conditions.join(' AND ');
      }

      sql += ' ORDER BY mt.priority DESC, mt.created_at ASC';

      const tasks = await this.database.query<MicroTask & { phase_name: string; project_title: string }>(sql, params);

      if (tasks.length === 0) {
        return {
          content: [
            {
              type: 'text',
              text: '📋 No DevStream tasks found matching the specified criteria.'
            }
          ]
        };
      }

      // Format tasks for display
      const tasksByProject = tasks.reduce((acc, task) => {
        const project = task.project_title;
        if (!acc[project]) acc[project] = [];
        acc[project].push(task);
        return acc;
      }, {} as Record<string, typeof tasks>);

      let output = '📋 **DevStream Tasks**\n\n';

      Object.entries(tasksByProject).forEach(([project, projectTasks]) => {
        output += `## 🎯 ${project}\n\n`;

        const tasksByPhase = projectTasks.reduce((acc, task) => {
          const phase = task.phase_name;
          if (!acc[phase]) acc[phase] = [];
          acc[phase].push(task);
          return acc;
        }, {} as Record<string, typeof projectTasks>);

        Object.entries(tasksByPhase).forEach(([phase, phaseTasks]) => {
          output += `### 📁 ${phase}\n\n`;

          phaseTasks.forEach(task => {
            const statusEmoji = {
              pending: '⏳',
              active: '🔄',
              completed: '✅',
              failed: '❌',
              skipped: '⏭️'
            }[task.status] || '❓';

            const priorityText = task.priority >= 8 ? 'HIGH' : task.priority >= 5 ? 'MEDIUM' : 'LOW';

            output += `${statusEmoji} **[${task.status.toUpperCase()}]** ${task.title}\n`;
            output += `   📝 ${task.description}\n`;
            output += `   🏷️ Type: ${task.task_type} | Priority: ${task.priority}/10 (${priorityText})\n`;
            output += `   🆔 ID: \`${task.id}\`\n\n`;
          });
        });
      });

      output += `\n📊 **Summary**: ${tasks.length} tasks found`;
      if (input.status) output += ` • Status: ${input.status}`;
      if (input.priority) output += ` • Priority ≥ ${input.priority}`;

      return {
        content: [
          {
            type: 'text',
            text: output
          }
        ]
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        content: [
          {
            type: 'text',
            text: `❌ Error listing tasks: ${errorMessage}`
          }
        ]
      };
    }
  }

  /**
   * Create a new DevStream task
   */
  async createTask(args: any) {
    try {
      const input = CreateTaskInputSchema.parse(args);

      // Find the project and phase
      const plan = await this.database.queryOne<InterventionPlan>(
        'SELECT * FROM intervention_plans WHERE title LIKE ? LIMIT 1',
        [`%${input.project}%`]
      );

      if (!plan) {
        throw new Error(`Project not found: ${input.project}`);
      }

      const phase = await this.database.queryOne<Phase>(
        'SELECT * FROM phases WHERE plan_id = ? AND name LIKE ? LIMIT 1',
        [plan.id, `%${input.phase_name}%`]
      );

      if (!phase) {
        throw new Error(`Phase not found: ${input.phase_name} in project ${input.project}`);
      }

      // Generate task ID
      const taskId = this.generateId();

      // Insert new task
      await this.database.execute(`
        INSERT INTO micro_tasks (
          id, phase_id, title, description, max_duration_minutes, max_context_tokens,
          assigned_agent, task_type, status, priority, input_files, output_files, retry_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `, [
        taskId,
        phase.id,
        input.title,
        input.description,
        10, // Default max duration
        256000, // Default max context tokens
        'developer', // Default agent
        input.task_type,
        'pending',
        input.priority,
        JSON.stringify([]),
        JSON.stringify([]),
        0
      ]);

      return {
        content: [
          {
            type: 'text',
            text: `✅ **Task Created Successfully**\n\n` +
                  `📝 **Title**: ${input.title}\n` +
                  `📁 **Phase**: ${phase.name}\n` +
                  `🎯 **Project**: ${plan.title}\n` +
                  `🏷️ **Type**: ${input.task_type}\n` +
                  `⭐ **Priority**: ${input.priority}/10\n` +
                  `🆔 **Task ID**: \`${taskId}\`\n\n` +
                  `The task has been added to the "${phase.name}" phase and is ready for execution.`
          }
        ]
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        content: [
          {
            type: 'text',
            text: `❌ Error creating task: ${errorMessage}`
          }
        ]
      };
    }
  }

  /**
   * Update task status
   */
  async updateTask(args: any) {
    try {
      const input = UpdateTaskInputSchema.parse(args);

      // Check if task exists
      const task = await this.database.queryOne<MicroTask>(
        'SELECT * FROM micro_tasks WHERE id = ?',
        [input.task_id]
      );

      if (!task) {
        throw new Error(`Task not found: ${input.task_id}`);
      }

      // Update task status
      const updateFields: string[] = ['status = ?', 'updated_at = datetime("now")'];
      const updateParams: any[] = [input.status];

      // Set timestamps based on status
      if (input.status === 'active' && !task.started_at) {
        updateFields.push('started_at = datetime("now")');
      } else if (['completed', 'failed', 'skipped'].includes(input.status) && !task.completed_at) {
        updateFields.push('completed_at = datetime("now")');
      }

      await this.database.execute(
        `UPDATE micro_tasks SET ${updateFields.join(', ')} WHERE id = ?`,
        [...updateParams, input.task_id]
      );

      // Store update notes in memory if provided
      if (input.notes) {
        await this.storeTaskUpdate(input.task_id, input.status, input.notes);
      }

      return {
        content: [
          {
            type: 'text',
            text: `✅ **Task Updated Successfully**\n\n` +
                  `📝 **Task**: ${task.title}\n` +
                  `📊 **Status**: ${task.status} → **${input.status.toUpperCase()}**\n` +
                  `🆔 **Task ID**: \`${input.task_id}\`\n` +
                  (input.notes ? `\n📝 **Notes**: ${input.notes}` : '') +
                  `\n\nThe task status has been updated and logged in the DevStream database.`
          }
        ]
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        content: [
          {
            type: 'text',
            text: `❌ Error updating task: ${errorMessage}`
          }
        ]
      };
    }
  }

  /**
   * Store task update information in semantic memory
   */
  private async storeTaskUpdate(taskId: string, status: string, notes: string): Promise<void> {
    const memoryId = this.generateId();

    await this.database.execute(`
      INSERT INTO semantic_memory (
        id, task_id, content, content_type, content_format, keywords, source,
        importance_score, access_count, metadata
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `, [
      memoryId,
      taskId,
      `Task status update: ${status}. Notes: ${notes}`,
      'decision',
      'text',
      JSON.stringify(['task', 'update', status]),
      'task_update',
      0.7, // Medium importance
      0,
      JSON.stringify({ task_id: taskId, previous_status: status, update_type: 'status_change' })
    ]);
  }

  /**
   * Generate unique ID for database records
   */
  private generateId(): string {
    return require('crypto').randomBytes(16).toString('hex');
  }
}