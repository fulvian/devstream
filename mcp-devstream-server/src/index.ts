#!/usr/bin/env node

/**
 * DevStream MCP Server
 *
 * Model Context Protocol server for DevStream task management and memory system.
 * Provides natural language integration with Claude Code for DevStream functionality.
 *
 * Architecture:
 * Claude Code → MCP Protocol → DevStream MCP Server → SQLite DevStream DB
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from '@modelcontextprotocol/sdk/types.js';
import { DevStreamDatabase } from './database.js';
import { TaskTools } from './tools/tasks.js';
import { PlanTools } from './tools/plans.js';
import { MemoryTools } from './tools/memory.js';
import { ImplementationPlanTools } from './tools/implementation-plans.js';
import { initializeOllamaClient } from './ollama-client.js';
import { AutoSaveService } from './services/auto-save.js';
import { HealthServer } from './health-server.js';

/**
 * Main MCP Server class for DevStream integration
 */
class DevStreamMcpServer {
  private server: Server;
  private database: DevStreamDatabase;
  private taskTools: TaskTools;
  private planTools: PlanTools;
  private memoryTools: MemoryTools;
  private implementationPlanTools: ImplementationPlanTools;
  private autoSaveService: AutoSaveService;
  private healthServer: HealthServer;
  private heartbeatInterval?: NodeJS.Timeout;

  constructor(dbPath: string) {
    // Initialize MCP server
    this.server = new Server(
      {
        name: 'devstream-mcp-server',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    // Initialize database connection
    this.database = new DevStreamDatabase(dbPath);

    // Initialize tool handlers
    this.taskTools = new TaskTools(this.database);
    this.planTools = new PlanTools(this.database);
    this.memoryTools = new MemoryTools(this.database);
    this.implementationPlanTools = new ImplementationPlanTools(this.database);

    // Initialize auto-save background service
    this.autoSaveService = new AutoSaveService(this.database, {
      intervalMs: 300000, // 5 minutes
      enabled: true
    });

    // Initialize health server
    this.healthServer = new HealthServer(this.database);

    this.setupHandlers();
  }

  /**
   * Setup MCP protocol handlers
   */
  private setupHandlers(): void {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      const tools: Tool[] = [
        // Task management tools
        {
          name: 'devstream_list_tasks',
          description: 'List all DevStream tasks with optional filtering by status, priority, or project',
          inputSchema: {
            type: 'object',
            properties: {
              status: {
                type: 'string',
                enum: ['pending', 'active', 'completed', 'failed', 'skipped'],
                description: 'Filter tasks by status'
              },
              project: {
                type: 'string',
                description: 'Filter tasks by project name (e.g., "RUSTY Trading Platform")'
              },
              priority: {
                type: 'number',
                minimum: 1,
                maximum: 10,
                description: 'Filter tasks by minimum priority level'
              }
            },
            additionalProperties: false
          }
        },
        {
          name: 'devstream_create_task',
          description: 'Create a new DevStream task in a specific phase',
          inputSchema: {
            type: 'object',
            properties: {
              title: {
                type: 'string',
                description: 'Task title'
              },
              description: {
                type: 'string',
                description: 'Detailed task description'
              },
              task_type: {
                type: 'string',
                enum: ['analysis', 'coding', 'documentation', 'testing', 'review', 'research'],
                description: 'Type of task'
              },
              priority: {
                type: 'number',
                minimum: 1,
                maximum: 10,
                description: 'Task priority (1-10, higher is more important)'
              },
              phase_name: {
                type: 'string',
                description: 'Phase name (e.g., "Core Engine & Infrastructure")'
              },
              project: {
                type: 'string',
                description: 'Project name (optional, defaults to "RUSTY Trading Platform")'
              }
            },
            required: ['title', 'description', 'task_type', 'priority', 'phase_name'],
            additionalProperties: false
          }
        },
        {
          name: 'devstream_update_task',
          description: 'Update task status or properties',
          inputSchema: {
            type: 'object',
            properties: {
              task_id: {
                type: 'string',
                description: 'Task ID to update'
              },
              status: {
                type: 'string',
                enum: ['pending', 'active', 'completed', 'failed', 'skipped'],
                description: 'New task status'
              },
              notes: {
                type: 'string',
                description: 'Optional notes about the update'
              }
            },
            required: ['task_id', 'status'],
            additionalProperties: false
          }
        },

        // Plan management tools
        {
          name: 'devstream_list_plans',
          description: 'List all intervention plans with their phases and progress',
          inputSchema: {
            type: 'object',
            properties: {
              status: {
                type: 'string',
                enum: ['draft', 'active', 'completed', 'paused'],
                description: 'Filter plans by status'
              }
            },
            additionalProperties: false
          }
        },

        // Implementation plan management tools (Protocol v2.2.0)
        {
          name: 'devstream_create_implementation_plan',
          description: 'Create a new implementation plan with model-specific template (GLM-4.6 or Sonnet 4.5) for DevStream Protocol v2.2.0',
          inputSchema: {
            type: 'object',
            properties: {
              task_id: {
                type: 'string',
                description: 'Task ID to create plan for'
              },
              model_type: {
                type: 'string',
                enum: ['glm-4.6', 'sonnet-4.5'],
                description: 'Model type for implementation (glm-4.6: cost-optimized, sonnet-4.5: quality-first)'
              },
              plan_content: {
                type: 'string',
                description: 'Full markdown plan content'
              },
              plan_file_path: {
                type: 'string',
                description: 'File system path for markdown file (e.g., docs/development/plan/piano_xxx.md)'
              },
              handoff_prompt: {
                type: 'string',
                description: 'Pre-generated handoff prompt for GLM-4.6 workflow (optional)'
              },
              metadata: {
                type: 'object',
                properties: {
                  complexity: {
                    type: 'number',
                    description: 'Task complexity score (0-1)'
                  },
                  estimated_duration: {
                    type: 'number',
                    description: 'Estimated duration in minutes'
                  },
                  context7_libraries: {
                    type: 'array',
                    items: { type: 'string' },
                    description: 'Libraries researched via Context7'
                  },
                  research_findings: {
                    type: 'string',
                    description: 'Summary of research findings'
                  }
                }
              }
            },
            required: ['task_id', 'model_type', 'plan_content'],
            additionalProperties: false
          }
        },
        {
          name: 'devstream_get_implementation_plan',
          description: 'Get implementation plan by task ID',
          inputSchema: {
            type: 'object',
            properties: {
              task_id: {
                type: 'string',
                description: 'Task ID to retrieve plan for'
              }
            },
            required: ['task_id'],
            additionalProperties: false
          }
        },
        {
          name: 'devstream_update_implementation_plan',
          description: 'Update existing implementation plan',
          inputSchema: {
            type: 'object',
            properties: {
              task_id: {
                type: 'string',
                description: 'Task ID to update plan for'
              },
              plan_content: {
                type: 'string',
                description: 'Updated plan content (optional)'
              },
              handoff_prompt: {
                type: 'string',
                description: 'Updated handoff prompt (optional)'
              },
              metadata: {
                type: 'object',
                description: 'Updated metadata (optional)'
              }
            },
            required: ['task_id'],
            additionalProperties: false
          }
        },
        {
          name: 'devstream_list_implementation_plans',
          description: 'List implementation plans with optional filtering by model type',
          inputSchema: {
            type: 'object',
            properties: {
              model_type: {
                type: 'string',
                enum: ['glm-4.6', 'sonnet-4.5'],
                description: 'Filter by model type (optional)'
              },
              limit: {
                type: 'number',
                minimum: 1,
                maximum: 100,
                default: 20,
                description: 'Maximum number of results'
              }
            },
            additionalProperties: false
          }
        },

        // Memory management tools
        {
          name: 'devstream_store_memory',
          description: 'Store information in DevStream semantic memory',
          inputSchema: {
            type: 'object',
            properties: {
              content: {
                type: 'string',
                description: 'Content to store in memory'
              },
              content_type: {
                type: 'string',
                enum: ['code', 'documentation', 'context', 'output', 'error', 'decision', 'learning'],
                description: 'Type of content being stored'
              },
              keywords: {
                type: 'array',
                items: { type: 'string' },
                description: 'Keywords for easier retrieval'
              }
            },
            required: ['content', 'content_type'],
            additionalProperties: false
          }
        },
        {
          name: 'devstream_search_memory',
          description: 'Search DevStream semantic memory for relevant information',
          inputSchema: {
            type: 'object',
            properties: {
              query: {
                type: 'string',
                description: 'Search query for memory content'
              },
              content_type: {
                type: 'string',
                enum: ['code', 'documentation', 'context', 'output', 'error', 'decision', 'learning'],
                description: 'Filter by content type'
              },
              limit: {
                type: 'number',
                minimum: 1,
                maximum: 50,
                default: 10,
                description: 'Maximum number of results to return'
              },
              min_relevance: {
                type: 'number',
                minimum: 0.0,
                maximum: 1.0,
                default: 0.03,
                description: 'Minimum RRF score threshold (default: 0.03 = 3%). Filters out LOW relevance results. Higher values return fewer but more relevant results.'
              }
            },
            required: ['query'],
            additionalProperties: false
          }
        },
        {
          name: 'devstream_trigger_checkpoint',
          description: 'Trigger immediate checkpoint for all active tasks (used by PostToolUse hook after critical tool executions)',
          inputSchema: {
            type: 'object',
            properties: {
              reason: {
                type: 'string',
                enum: ['manual', 'tool_trigger', 'shutdown'],
                default: 'tool_trigger',
                description: 'Reason for checkpoint: manual (user request), tool_trigger (PostToolUse hook), shutdown (graceful shutdown)'
              }
            },
            additionalProperties: false
          }
        }
      ];

      return { tools };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          // Task tools
          case 'devstream_list_tasks':
            return await this.taskTools.listTasks(args);
          case 'devstream_create_task':
            return await this.taskTools.createTask(args);
          case 'devstream_update_task':
            return await this.taskTools.updateTask(args);

          // Plan tools
          case 'devstream_list_plans':
            return await this.planTools.listPlans(args);

          // Implementation plan tools (Protocol v2.2.0)
          case 'devstream_create_implementation_plan':
            return await this.implementationPlanTools.createPlan(args);
          case 'devstream_get_implementation_plan':
            return await this.implementationPlanTools.getPlan(args);
          case 'devstream_update_implementation_plan':
            return await this.implementationPlanTools.updatePlan(args);
          case 'devstream_list_implementation_plans':
            return await this.implementationPlanTools.listPlans(args);

          // Memory tools
          case 'devstream_store_memory':
            return await this.memoryTools.storeMemory(args);
          case 'devstream_search_memory':
            return await this.memoryTools.searchMemory(args);

          // Checkpoint tools
          case 'devstream_trigger_checkpoint':
            return await this.triggerCheckpoint(args);

          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        return {
          content: [
            {
              type: 'text',
              text: `Error executing ${name}: ${errorMessage}`
            }
          ]
        };
      }
    });
  }

  /**
   * Trigger immediate checkpoint for all active tasks
   *
   * Context7 Pattern: Exposes AutoSaveService checkpoint functionality via MCP.
   * Used by PostToolUse hook to save progress after critical tool executions.
   *
   * @param args - Tool arguments
   * @returns MCP tool response
   */
  private async triggerCheckpoint(args: any): Promise<{ content: Array<{ type: string; text: string }> }> {
    try {
      const reason = args.reason || 'tool_trigger';

      // Trigger immediate checkpoint via AutoSaveService
      const checkpointCount = await this.autoSaveService.triggerImmediateCheckpoint(reason);

      const message = checkpointCount > 0
        ? `✅ Checkpoint triggered: ${checkpointCount} active task${checkpointCount !== 1 ? 's' : ''} saved (reason: ${reason})`
        : `ℹ️ No active tasks found - checkpoint skipped`;

      return {
        content: [
          {
            type: 'text',
            text: message
          }
        ]
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        content: [
          {
            type: 'text',
            text: `⚠️ Checkpoint failed: ${errorMessage}`
          }
        ]
      };
    }
  }

  /**
   * Start the MCP server
   */
  async start(): Promise<void> {
    // Initialize database connection (sqlite-vec loaded automatically)
    await this.database.initialize();

    // Verify vector search availability
    const vectorStatus = this.database.getVectorSearchStatus();
    if (vectorStatus) {
      const diagnostics = await this.database.getVectorSearchDiagnostics();
      console.error(`✅ Vector search ready: ${diagnostics.version}`);
    } else {
      console.error('⚠️ Vector search not available - using text-only fallback');
    }

    // Context7 pattern: Initialize Ollama client for embedding generation
    console.error('🧠 Initializing Ollama client for automatic embedding generation...');
    try {
      await initializeOllamaClient();
      console.error('✅ Ollama client initialized successfully');
    } catch (error) {
      console.error('⚠️ Ollama client initialization failed:', error instanceof Error ? error.message : 'Unknown error');
      console.error('⚠️ Continuing without embedding support - memory will be stored as text-only');
    }

    // Start server with stdio transport
    const transport = new StdioServerTransport();
    await this.server.connect(transport);

    // Get database path for logging
    const dbPath = process.argv[2] || 'unknown';

    // Comprehensive startup health log
    console.error('🚀 DevStream MCP Server started - HYBRID SEARCH v2.0 (better-sqlite3 + sqlite-vec)');
    console.error(`📊 Server Info:`);
    console.error(`   PID: ${process.pid}`);
    console.error(`   Transport: stdio`);
    console.error(`   Database: ${dbPath}`);
    console.error(`   Metrics endpoint: http://localhost:9090/health`);

    // Start heartbeat logging (every 5 minutes)
    this.heartbeatInterval = setInterval(() => {
      const uptimeMinutes = Math.floor(process.uptime() / 60);
      console.error(`💓 MCP server heartbeat (uptime: ${uptimeMinutes} min, PID: ${process.pid})`);
    }, 5 * 60 * 1000); // 5 minutes

    // Start auto-save background service (non-blocking to prevent startup delay)
    // Context7 Pattern: Background task initialization should not block server readiness
    this.autoSaveService.start()
      .then(() => {
        console.error('✅ Auto-save service started successfully');
      })
      .catch((error) => {
        console.error('⚠️ Failed to start auto-save service:', error instanceof Error ? error.message : 'Unknown error');
        console.error('⚠️ Continuing without auto-save - manual checkpoints still available');
      });

    // Start health server
    try {
      await this.healthServer.start();
    } catch (error) {
      console.error('⚠️ Failed to start health server:', error instanceof Error ? error.message : 'Unknown error');
      console.error('⚠️ Continuing without health endpoint - MCP functionality unaffected');
    }
  }

  /**
   * Cleanup and close connections with timeout safety
   *
   * Context7 Pattern: Graceful shutdown with 5-second timeout protection.
   * Ensures server doesn't hang during cleanup phase.
   *
   * @param reason - Reason for cleanup (for logging)
   */
  async cleanup(reason: string = 'shutdown'): Promise<void> {
    console.error(`🔄 Initiating cleanup (reason: ${reason})...`);

    // Safety timeout: Force exit after 5 seconds if cleanup hangs
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

      // Step 2: Stop auto-save service (graceful shutdown)
      console.error('  └─ Stopping auto-save service...');
      try {
        await this.autoSaveService.stop();
        console.error('  ✅ Auto-save service stopped');
      } catch (error) {
        console.error('  ⚠️ Error stopping auto-save service:', error instanceof Error ? error.message : 'Unknown error');
      }

      // Step 2.5: Stop health server
      console.error('  └─ Stopping health server...');
      try {
        await this.healthServer.stop();
        console.error('  ✅ Health server stopped');
      } catch (error) {
        console.error('  ⚠️ Error stopping health server:', error instanceof Error ? error.message : 'Unknown error');
      }

      // Step 3: Close database connection
      console.error('  └─ Closing database connection...');
      try {
        await this.database.close();
        console.error('  ✅ Database connection closed');
      } catch (error) {
        console.error('  ⚠️ Error closing database:', error instanceof Error ? error.message : 'Unknown error');
      }

      console.error('✅ Cleanup completed successfully');
    } finally {
      // Always clear timeout to prevent forced exit
      clearTimeout(cleanupTimeout);
    }
  }

  /**
   * Legacy close() method - delegates to cleanup()
   * @deprecated Use cleanup() for better observability
   */
  async close(): Promise<void> {
    await this.cleanup('legacy-close');
  }
}

/**
 * Main entry point
 */
async function main() {
  // Get database path from command line argument
  const dbPath = process.argv[2];

  if (!dbPath) {
    console.error('Usage: devstream-mcp <database-path>');
    console.error('Example: devstream-mcp /path/to/devstream.db');
    process.exit(1);
  }

  const server = new DevStreamMcpServer(dbPath);

  /**
   * MCP Spec 2025-03-26 Compliance: Signal-Based Lifecycle
   *
   * Per MCP specification, server shutdown is SIGNAL-BASED, not stdin EOF-based.
   * Rationale:
   * - stdin EOF occurs during Claude Code operations like /compact
   * - Shutting down on stdin EOF causes disconnection (server becomes unreachable)
   * - Proper shutdown is via SIGTERM (graceful) or SIGINT (user interrupt)
   *
   * Research sources:
   * - https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle
   * - Node.js best practices for long-running processes
   * - DevStream Context7 research findings (2025-10-02)
   *
   * Behavior:
   * - Server stays alive during stdin EOF (e.g., /compact command)
   * - Server shuts down gracefully on SIGTERM (Docker/kill)
   * - Server shuts down gracefully on SIGINT (Ctrl+C)
   */

  // Handle SIGINT (Ctrl+C / user interrupt)
  process.on('SIGINT', async () => {
    console.error('🛑 SIGINT received (user interrupt), initiating graceful shutdown...');
    await server.cleanup('SIGINT');
    process.exit(0);
  });

  // Handle SIGTERM (graceful termination from Docker/kill)
  process.on('SIGTERM', async () => {
    console.error('🛑 SIGTERM received (graceful termination), initiating graceful shutdown...');
    await server.cleanup('SIGTERM');
    process.exit(0);
  });

  // Start the server
  try {
    await server.start();
  } catch (error) {
    console.error('Failed to start DevStream MCP Server:', error);
    process.exit(1);
  }
}

// Run the server
if (require.main === module) {
  main().catch((error) => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}

export { DevStreamMcpServer };