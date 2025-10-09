/**
 * DevStream Implementation Plans Management Tools
 *
 * MCP tools for managing implementation plans with model-specific templates.
 * Supports DevStream Protocol v2.2.0 with Strategic Choice Gate workflow.
 */

import { DevStreamDatabase, ImplementationPlan, MicroTask } from '../database.js';
import { z } from 'zod';
import * as fs from 'fs/promises';
import * as path from 'path';

// Input validation schemas
const CreatePlanInputSchema = z.object({
  task_id: z.string().min(1),
  model_type: z.enum(['glm-4.6', 'sonnet-4.5']),
  plan_content: z.string().min(1),
  plan_file_path: z.string().optional(),
  handoff_prompt: z.string().optional(),
  metadata: z.object({
    complexity: z.number().optional(),
    estimated_duration: z.number().optional(),
    context7_libraries: z.array(z.string()).optional(),
    research_findings: z.string().optional()
  }).optional()
});

const GetPlanInputSchema = z.object({
  task_id: z.string().min(1)
});

const UpdatePlanInputSchema = z.object({
  task_id: z.string().min(1),
  plan_content: z.string().optional(),
  handoff_prompt: z.string().optional(),
  metadata: z.object({}).passthrough().optional()
});

const ListPlansInputSchema = z.object({
  model_type: z.enum(['glm-4.6', 'sonnet-4.5']).optional(),
  limit: z.number().min(1).max(100).optional().default(20)
});

export class ImplementationPlanTools {
  constructor(private database: DevStreamDatabase) {}

  /**
   * Create a new implementation plan with dual storage (DB + file system)
   */
  async createPlan(args: any) {
    try {
      const input = CreatePlanInputSchema.parse(args);

      // Verify task exists
      const task = await this.database.queryOne<MicroTask>(
        'SELECT * FROM micro_tasks WHERE id = ?',
        [input.task_id]
      );

      if (!task) {
        throw new Error(`Task not found: ${input.task_id}`);
      }

      // Check if plan already exists for this task
      const existingPlan = await this.database.queryOne<ImplementationPlan>(
        'SELECT * FROM implementation_plans WHERE task_id = ?',
        [input.task_id]
      );

      if (existingPlan) {
        throw new Error(`Implementation plan already exists for task: ${input.task_id}`);
      }

      // Generate plan ID
      const planId = this.generateId();

      // Prepare metadata
      const metadata = input.metadata ? JSON.stringify(input.metadata) : JSON.stringify({});

      // Insert plan into database
      await this.database.execute(`
        INSERT INTO implementation_plans (
          id, task_id, model_type, plan_content, plan_file_path, handoff_prompt, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
      `, [
        planId,
        input.task_id,
        input.model_type,
        input.plan_content,
        input.plan_file_path || null,
        input.handoff_prompt || null,
        metadata
      ]);

      // Write to file system if path provided
      if (input.plan_file_path) {
        await this.writePlanToFile(input.plan_file_path, input.plan_content);
      }

      return {
        content: [
          {
            type: 'text',
            text: `✅ **Implementation Plan Created Successfully**\n\n` +
                  `📝 **Task ID**: \`${input.task_id}\`\n` +
                  `📋 **Task**: ${task.title}\n` +
                  `🤖 **Model Type**: ${input.model_type}\n` +
                  `🆔 **Plan ID**: \`${planId}\`\n` +
                  (input.plan_file_path ? `📄 **File**: \`${input.plan_file_path}\`\n` : '') +
                  (input.handoff_prompt ? `🚀 **Handoff Prompt**: Generated (${input.handoff_prompt.length} chars)\n` : '') +
                  `\nThe implementation plan has been saved to the database` +
                  (input.plan_file_path ? ' and file system' : '') + `.`
          }
        ]
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        content: [
          {
            type: 'text',
            text: `❌ Error creating implementation plan: ${errorMessage}`
          }
        ]
      };
    }
  }

  /**
   * Get implementation plan by task ID
   */
  async getPlan(args: any) {
    try {
      const input = GetPlanInputSchema.parse(args);

      const plan = await this.database.queryOne<ImplementationPlan>(
        'SELECT * FROM implementation_plans WHERE task_id = ?',
        [input.task_id]
      );

      if (!plan) {
        throw new Error(`No implementation plan found for task: ${input.task_id}`);
      }

      // Get task details
      const task = await this.database.queryOne<MicroTask>(
        'SELECT * FROM micro_tasks WHERE id = ?',
        [input.task_id]
      );

      // Parse metadata
      let metadataObj: any = {};
      try {
        metadataObj = JSON.parse(plan.metadata);
      } catch (e) {
        // Ignore parse error
      }

      let output = `📋 **Implementation Plan**\n\n`;
      output += `**Task**: ${task?.title || 'Unknown'}\n`;
      output += `**Task ID**: \`${input.task_id}\`\n`;
      output += `**Model Type**: ${plan.model_type}\n`;
      output += `**Created**: ${new Date(plan.created_at).toLocaleString()}\n`;
      output += `**Updated**: ${new Date(plan.updated_at).toLocaleString()}\n\n`;

      if (plan.plan_file_path) {
        output += `📄 **Plan File**: \`${plan.plan_file_path}\`\n\n`;
      }

      if (metadataObj.complexity) {
        output += `📊 **Complexity**: ${(metadataObj.complexity * 100).toFixed(0)}%\n`;
      }

      if (metadataObj.estimated_duration) {
        output += `⏱️ **Estimated Duration**: ${metadataObj.estimated_duration} minutes\n`;
      }

      if (metadataObj.context7_libraries && Array.isArray(metadataObj.context7_libraries)) {
        output += `📚 **Context7 Libraries**: ${metadataObj.context7_libraries.join(', ')}\n`;
      }

      output += `\n---\n\n`;
      output += `**Plan Content** (${plan.plan_content.length} chars):\n`;
      output += `\`\`\`\n${plan.plan_content.substring(0, 500)}${plan.plan_content.length > 500 ? '...\n[Truncated - See full plan in file]' : ''}\n\`\`\`\n`;

      if (plan.handoff_prompt) {
        output += `\n---\n\n`;
        output += `**Handoff Prompt** (${plan.handoff_prompt.length} chars):\n`;
        output += `Available for GLM-4.6 session handoff.\n`;
      }

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
            text: `❌ Error retrieving implementation plan: ${errorMessage}`
          }
        ]
      };
    }
  }

  /**
   * Update existing implementation plan
   */
  async updatePlan(args: any) {
    try {
      const input = UpdatePlanInputSchema.parse(args);

      // Check if plan exists
      const plan = await this.database.queryOne<ImplementationPlan>(
        'SELECT * FROM implementation_plans WHERE task_id = ?',
        [input.task_id]
      );

      if (!plan) {
        throw new Error(`No implementation plan found for task: ${input.task_id}`);
      }

      // Build update query
      const updates: string[] = [];
      const params: any[] = [];

      if (input.plan_content) {
        updates.push('plan_content = ?');
        params.push(input.plan_content);

        // Update file if path exists
        if (plan.plan_file_path) {
          await this.writePlanToFile(plan.plan_file_path, input.plan_content);
        }
      }

      if (input.handoff_prompt) {
        updates.push('handoff_prompt = ?');
        params.push(input.handoff_prompt);
      }

      if (input.metadata) {
        updates.push('metadata = ?');
        params.push(JSON.stringify(input.metadata));
      }

      if (updates.length === 0) {
        throw new Error('No updates provided');
      }

      // Add task_id for WHERE clause
      params.push(input.task_id);

      // Execute update
      await this.database.execute(
        `UPDATE implementation_plans SET ${updates.join(', ')} WHERE task_id = ?`,
        params
      );

      return {
        content: [
          {
            type: 'text',
            text: `✅ **Implementation Plan Updated Successfully**\n\n` +
                  `📝 **Task ID**: \`${input.task_id}\`\n` +
                  `🔄 **Updated Fields**: ${updates.length}\n` +
                  `\nThe implementation plan has been updated.`
          }
        ]
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        content: [
          {
            type: 'text',
            text: `❌ Error updating implementation plan: ${errorMessage}`
          }
        ]
      };
    }
  }

  /**
   * List implementation plans with optional filtering
   */
  async listPlans(args: any) {
    try {
      const input = ListPlansInputSchema.parse(args);

      let sql = `
        SELECT
          ip.*,
          mt.title as task_title,
          mt.status as task_status,
          mt.priority as task_priority
        FROM implementation_plans ip
        JOIN micro_tasks mt ON ip.task_id = mt.id
      `;

      const conditions: string[] = [];
      const params: any[] = [];

      if (input.model_type) {
        conditions.push('ip.model_type = ?');
        params.push(input.model_type);
      }

      if (conditions.length > 0) {
        sql += ' WHERE ' + conditions.join(' AND ');
      }

      sql += ' ORDER BY ip.created_at DESC LIMIT ?';
      params.push(input.limit);

      const plans = await this.database.query<ImplementationPlan & {
        task_title: string;
        task_status: string;
        task_priority: number;
      }>(sql, params);

      if (plans.length === 0) {
        return {
          content: [
            {
              type: 'text',
              text: '📋 No implementation plans found matching the specified criteria.'
            }
          ]
        };
      }

      let output = `📋 **Implementation Plans** (${plans.length} found)\n\n`;

      plans.forEach(plan => {
        const modelEmoji = plan.model_type === 'glm-4.6' ? '⚡' : '🧠';
        const statusEmoji = {
          pending: '⏳',
          active: '🔄',
          completed: '✅',
          failed: '❌',
          skipped: '⏭️'
        }[plan.task_status] || '❓';

        output += `${modelEmoji} **${plan.task_title}**\n`;
        output += `   📊 Model: ${plan.model_type} | Status: ${statusEmoji} ${plan.task_status}\n`;
        output += `   🆔 Task ID: \`${plan.task_id}\`\n`;
        output += `   📅 Created: ${new Date(plan.created_at).toLocaleDateString()}\n`;
        if (plan.plan_file_path) {
          output += `   📄 File: \`${plan.plan_file_path}\`\n`;
        }
        output += `\n`;
      });

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
            text: `❌ Error listing implementation plans: ${errorMessage}`
          }
        ]
      };
    }
  }

  /**
   * Write plan content to file system
   */
  private async writePlanToFile(filePath: string, content: string): Promise<void> {
    try {
      // Ensure directory exists
      const dir = path.dirname(filePath);
      await fs.mkdir(dir, { recursive: true });

      // Write file
      await fs.writeFile(filePath, content, 'utf-8');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      throw new Error(`Failed to write plan to file: ${errorMessage}`);
    }
  }

  /**
   * Generate unique ID for database records
   */
  private generateId(): string {
    return require('crypto').randomBytes(16).toString('hex');
  }
}
