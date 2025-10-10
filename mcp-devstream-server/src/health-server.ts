/**
 * Health Check Server for DevStream MCP Server
 *
 * Provides HTTP health endpoint for monitoring MCP server status.
 * Exposes database connectivity, vector search status, and system metrics.
 */

import { createServer, Server } from 'http';
import { DevStreamDatabase } from './database.js';

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  uptime: number;
  version: string;
  components: {
    database: {
      status: 'connected' | 'disconnected' | 'error';
      path: string;
      size_bytes?: number;
      vector_search_available: boolean;
      embedding_coverage?: number;
    };
    ollama: {
      status: 'connected' | 'disconnected' | 'error';
      model: string;
      embedding_dimension: number;
    };
    memory: {
      heap_used_mb: number;
      heap_total_mb: number;
      external_mb: number;
    };
  };
  metrics: {
    total_records: number;
    records_with_embeddings: number;
    embedding_coverage_percent: number;
    active_sessions: number;
  };
}

/**
 * HTTP Health Server for MCP monitoring
 */
export class HealthServer {
  private server?: Server;
  private port: number;
  private database: DevStreamDatabase;

  constructor(database: DevStreamDatabase, port: number = 9090) {
    this.database = database;
    this.port = port;
  }

  /**
   * Start the health check HTTP server
   */
  async start(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.server = createServer(async (req, res) => {
        // Only handle /health endpoint
        if (req.url === '/health' && req.method === 'GET') {
          try {
            const healthStatus = await this.getHealthStatus();

            res.writeHead(200, {
              'Content-Type': 'application/json',
              'Access-Control-Allow-Origin': '*',
              'Access-Control-Allow-Methods': 'GET',
              'Access-Control-Allow-Headers': 'Content-Type',
            });

            res.end(JSON.stringify(healthStatus, null, 2));
          } catch (error) {
            console.error('Health check error:', error);

            res.writeHead(500, {
              'Content-Type': 'application/json',
              'Access-Control-Allow-Origin': '*',
            });

            res.end(JSON.stringify({
              status: 'error',
              error: error instanceof Error ? error.message : 'Unknown error',
              timestamp: new Date().toISOString(),
            }, null, 2));
          }
        } else if (req.url === '/' && req.method === 'GET') {
          // Simple landing page
          res.writeHead(200, { 'Content-Type': 'text/html' });
          res.end(`
            <!DOCTYPE html>
            <html>
            <head>
              <title>DevStream MCP Server Health</title>
              <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 800px; margin: 0 auto; }
                .status { padding: 20px; border-radius: 8px; margin: 20px 0; }
                .healthy { background-color: #d4edda; border: 1px solid #c3e6cb; }
                .degraded { background-color: #fff3cd; border: 1px solid #ffeaa7; }
                .unhealthy { background-color: #f8d7da; border: 1px solid #f5c6cb; }
                pre { background: #f8f9fa; padding: 10px; border-radius: 4px; overflow-x: auto; }
              </style>
            </head>
            <body>
              <div class="container">
                <h1>🚀 DevStream MCP Server</h1>
                <p><strong>Health Endpoint:</strong> <a href="/health">/health</a></p>
                <p><strong>Format:</strong> JSON with detailed system status</p>
                <p><strong>Usage:</strong> <code>curl http://localhost:9090/health</code></p>
              </div>
            </body>
            </html>
          `);
        } else {
          res.writeHead(404, { 'Content-Type': 'text/plain' });
          res.end('Not Found. Use /health for status check.');
        }
      });

      this.server.listen(this.port, () => {
        console.error(`🏥 Health server listening on http://localhost:${this.port}/health`);
        resolve();
      });

      this.server.on('error', (error) => {
        console.error('Health server error:', error);
        reject(error);
      });
    });
  }

  /**
   * Get comprehensive health status
   */
  private async getHealthStatus(): Promise<HealthStatus> {
    const now = new Date();

    // Get database health
    let dbStatus: HealthStatus['components']['database'] = {
      status: 'connected',
      path: this.database.getDatabasePath(),
      vector_search_available: false,
    };

    let metrics: HealthStatus['metrics'] = {
      total_records: 0,
      records_with_embeddings: 0,
      embedding_coverage_percent: 0,
      active_sessions: 0,
    };

    try {
      // Test database connection
      const diagnostics = await this.database.getVectorSearchDiagnostics();

      if (diagnostics) {
        dbStatus.vector_search_available = true;
        dbStatus.size_bytes = diagnostics.database_size_bytes;

        // Get metrics from database
        const stats = await this.database.getMemoryStats();
        if (stats) {
          metrics.total_records = stats.total_records;
          metrics.records_with_embeddings = stats.records_with_embeddings;
          metrics.embedding_coverage_percent = stats.embedding_coverage_percent;
        }

        // Get active sessions
        const sessionStats = await this.database.getSessionStats();
        if (sessionStats) {
          metrics.active_sessions = sessionStats.active_sessions;
        }
      }
    } catch (error) {
      dbStatus.status = 'error';
      console.error('Database health check failed:', error);
    }

    // Get Ollama status (try to ping it)
    let ollamaStatus: HealthStatus['components']['ollama'] = {
      status: 'disconnected',
      model: 'embeddinggemma:300m',
      embedding_dimension: 768,
    };

    try {
      // Simple ping to Ollama
      const response = await fetch('http://localhost:11434/api/tags', {
        method: 'GET',
        signal: AbortSignal.timeout(2000), // 2 second timeout
      });

      if (response.ok) {
        ollamaStatus.status = 'connected';
      }
    } catch (error) {
      // Ollama not available - this is acceptable for degraded status
      ollamaStatus.status = 'disconnected';
    }

    // Get memory usage
    const memUsage = process.memoryUsage();
    const memoryStatus: HealthStatus['components']['memory'] = {
      heap_used_mb: Math.round(memUsage.heapUsed / 1024 / 1024 * 100) / 100,
      heap_total_mb: Math.round(memUsage.heapTotal / 1024 / 1024 * 100) / 100,
      external_mb: Math.round(memUsage.external / 1024 / 1024 * 100) / 100,
    };

    // Determine overall status
    let overallStatus: HealthStatus['status'] = 'healthy';

    if (dbStatus.status === 'error') {
      overallStatus = 'unhealthy';
    } else if (ollamaStatus.status === 'disconnected' || !dbStatus.vector_search_available) {
      overallStatus = 'degraded';
    }

    return {
      status: overallStatus,
      timestamp: now.toISOString(),
      uptime: Math.floor(process.uptime()),
      version: '1.0.0',
      components: {
        database: dbStatus,
        ollama: ollamaStatus,
        memory: memoryStatus,
      },
      metrics,
    };
  }

  /**
   * Stop the health server
   */
  async stop(): Promise<void> {
    return new Promise((resolve) => {
      if (this.server) {
        this.server.close(() => {
          console.error('🏥 Health server stopped');
          resolve();
        });
      } else {
        resolve();
      }
    });
  }
}