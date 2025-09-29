/**
 * DevStream Plan Management Tools
 *
 * MCP tools for managing DevStream intervention plans.
 */

import { DevStreamDatabase, InterventionPlan, Phase } from '../database.js';
import { z } from 'zod';

// Input validation schemas
const ListPlansInputSchema = z.object({
  status: z.enum(['draft', 'active', 'completed', 'paused']).optional()
});

export class PlanTools {
  constructor(private database: DevStreamDatabase) {}

  /**
   * List all intervention plans with their phases and progress
   */
  async listPlans(args: any) {
    try {
      const input = ListPlansInputSchema.parse(args);

      // Build SQL query with optional filters
      let sql = `
        SELECT
          ip.*,
          COUNT(p.id) as total_phases,
          COUNT(CASE WHEN p.status = 'completed' THEN 1 END) as completed_phases,
          COUNT(mt.id) as total_tasks,
          COUNT(CASE WHEN mt.status = 'completed' THEN 1 END) as completed_tasks
        FROM intervention_plans ip
        LEFT JOIN phases p ON ip.id = p.plan_id
        LEFT JOIN micro_tasks mt ON p.id = mt.phase_id
      `;

      const params: any[] = [];

      if (input.status) {
        sql += ' WHERE ip.status = ?';
        params.push(input.status);
      }

      sql += ' GROUP BY ip.id ORDER BY ip.priority DESC, ip.created_at DESC';

      const plans = await this.database.query<InterventionPlan & {
        total_phases: number;
        completed_phases: number;
        total_tasks: number;
        completed_tasks: number;
      }>(sql, params);

      if (plans.length === 0) {
        return {
          content: [
            {
              type: 'text',
              text: '📋 No DevStream plans found matching the specified criteria.'
            }
          ]
        };
      }

      let output = '📋 **DevStream Intervention Plans**\n\n';

      for (const plan of plans) {
        const statusEmoji = {
          draft: '📝',
          active: '🔄',
          completed: '✅',
          paused: '⏸️'
        }[plan.status] || '❓';

        const priorityText = plan.priority >= 8 ? 'HIGH' : plan.priority >= 5 ? 'MEDIUM' : 'LOW';
        const phaseProgress = plan.total_phases > 0 ? Math.round((plan.completed_phases / plan.total_phases) * 100) : 0;
        const taskProgress = plan.total_tasks > 0 ? Math.round((plan.completed_tasks / plan.total_tasks) * 100) : 0;

        output += `${statusEmoji} **${plan.title}**\n`;
        output += `📊 Status: **${plan.status.toUpperCase()}** | Priority: ${plan.priority}/10 (${priorityText})\n`;
        output += `📈 Progress: ${phaseProgress}% phases (${plan.completed_phases}/${plan.total_phases}) • ${taskProgress}% tasks (${plan.completed_tasks}/${plan.total_tasks})\n`;
        output += `⏱️ Time: ${plan.actual_hours}/${plan.estimated_hours} hours\n`;
        output += `📝 ${plan.description}\n`;

        // Parse and display objectives
        try {
          const objectives = JSON.parse(plan.objectives);
          if (Array.isArray(objectives) && objectives.length > 0) {
            output += `🎯 **Objectives**:\n`;
            objectives.slice(0, 3).forEach((obj, index) => {
              output += `   ${index + 1}. ${obj}\n`;
            });
            if (objectives.length > 3) {
              output += `   ... and ${objectives.length - 3} more\n`;
            }
          }
        } catch (e) {
          // Skip if objectives is not valid JSON
        }

        output += `🆔 ID: \`${plan.id}\`\n\n`;

        // Get phase details for active plans
        if (plan.status === 'active') {
          const phases = await this.database.query<Phase>(
            'SELECT * FROM phases WHERE plan_id = ? ORDER BY sequence_order',
            [plan.id]
          );

          if (phases.length > 0) {
            output += `   📁 **Phases**:\n`;
            phases.forEach(phase => {
              const phaseStatusEmoji = {
                pending: '⏳',
                active: '🔄',
                completed: '✅'
              }[phase.status] || '❓';

              output += `   ${phaseStatusEmoji} ${phase.name} (${phase.status})\n`;
            });
            output += '\n';
          }
        }
      }

      output += `📊 **Summary**: ${plans.length} plans found`;
      if (input.status) output += ` • Status: ${input.status}`;

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
            text: `❌ Error listing plans: ${errorMessage}`
          }
        ]
      };
    }
  }
}