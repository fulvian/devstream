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
import { initializeOllamaClient } from './ollama-client.js';
import { AutoSaveService } from './services/auto-save.js';

/**
 * Main MCP Server class for DevStream integration
 */
class DevStreamMcpServer {
  private server: Server;
  private database: DevStreamDatabase;
  private taskTools: TaskTools;
  private planTools: PlanTools;
  private memoryTools: MemoryTools;
  private autoSaveService: AutoSaveService;

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

    // Initialize auto-save background service
    this.autoSaveService = new AutoSaveService(this.database, {
      intervalMs: 300000, // 5 minutes
      enabled: true
    });

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

    console.error('🚀 DevStream MCP Server started - HYBRID SEARCH v2.0 (better-sqlite3 + sqlite-vec)');

    // Start auto-save background service
    try {
      await this.autoSaveService.start();
      console.error('✅ Auto-save service started successfully');
    } catch (error) {
      console.error('⚠️ Failed to start auto-save service:', error instanceof Error ? error.message : 'Unknown error');
      console.error('⚠️ Continuing without auto-save - manual checkpoints still available');
    }
  }

  /**
   * Cleanup and close connections
   */
  async close(): Promise<void> {
    // Stop auto-save service first (graceful shutdown)
    try {
      await this.autoSaveService.stop();
    } catch (error) {
      console.error('⚠️ Error stopping auto-save service:', error instanceof Error ? error.message : 'Unknown error');
    }

    // Close database connection
    await this.database.close();
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

  // Handle graceful shutdown
  process.on('SIGINT', async () => {
    console.error('Shutting down DevStream MCP Server...');
    await server.close();
    process.exit(0);
  });

  process.on('SIGTERM', async () => {
    console.error('Shutting down DevStream MCP Server...');
    await server.close();
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