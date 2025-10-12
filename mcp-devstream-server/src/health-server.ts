/**
 * Health Check Server for DevStream MCP Server
 *
 * Provides HTTP health endpoint for monitoring MCP server status.
 * Exposes database connectivity, vector search status, and system metrics.
 */

import { createServer, Server } from 'http';
import { DevStreamDatabase } from './database.js';
import { getDatabasePool } from './core/database-pool.js';

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
  private maxRetries = 10;
  private retryDelay = 1000; // 1 second as per Node.js best practice

  constructor(database: DevStreamDatabase, port: number = 9090) {
    this.database = database;
    this.port = port;
  }

  /**
   * Find an available port using Node.js best practice pattern
   */
  private async findAvailablePort(): Promise<number> {
    return new Promise((resolve, reject) => {
      const testServer = createServer();

      testServer.listen(this.port, () => {
        const address = testServer.address();
        const port = typeof address === 'string' ? parseInt(address) : address?.port || this.port;
        testServer.close(() => resolve(port));
      });

      testServer.on('error', (e: any) => {
        if (e.code === 'EADDRINUSE') {
          console.error(`⚠️ Port ${this.port} in use, trying next port...`);
          if (this.port < 9100) {
            this.port++;
            resolve(this.findAvailablePort());
          } else {
            reject(new Error('No available ports found in range 9090-9100'));
          }
        } else {
          reject(e);
        }
      });
    });
  }

  /**
   * Start the health check HTTP server with EADDRINUSE retry mechanism
   * Implements Node.js best practice for port conflict resolution
   */
  async start(): Promise<void> {
    // First, find an available port
    try {
      this.port = await this.findAvailablePort();
      console.error(`🔍 Found available port: ${this.port}`);
    } catch (error) {
      console.error('❌ Failed to find available port:', error);
      throw error;
    }

    // Now start the server with retry mechanism
    return this.startWithRetry();
  }

  /**
   * Start server with Node.js EADDRINUSE retry mechanism
   * Implements the official Node.js best practice pattern
   */
  private async startWithRetry(retryCount = 0): Promise<void> {
    return new Promise((resolve, reject) => {
      this.server = createServer(async (req, res) => {
        // Handle /metrics endpoint (Prometheus format - FASE 4.1)
        if (req.url === '/metrics' && req.method === 'GET') {
          try {
            const prometheusMetrics = await this.getPrometheusMetrics();

            res.writeHead(200, {
              'Content-Type': 'text/plain; version=0.0.4',
              'Access-Control-Allow-Origin': '*',
            });

            res.end(prometheusMetrics);
          } catch (error) {
            console.error('Metrics endpoint error:', error);

            res.writeHead(500, { 'Content-Type': 'text/plain' });
            res.end('# Error generating metrics\n');
          }
        }
        // Handle /health endpoint
        else if (req.url === '/health' && req.method === 'GET') {
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
          // Simple landing page with dynamic port
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
                <h2>Available Endpoints:</h2>
                <ul>
                  <li>
                    <strong>Health Check:</strong> <a href="/health">/health</a>
                    <p>JSON format with detailed system status</p>
                    <code>curl http://localhost:${this.port}/health</code>
                  </li>
                  <li>
                    <strong>Prometheus Metrics:</strong> <a href="/metrics">/metrics</a>
                    <p>Prometheus exposition format for monitoring (FASE 4.1)</p>
                    <code>curl http://localhost:${this.port}/metrics</code>
                  </li>
                </ul>
              </div>
            </body>
            </html>
          `);
        } else {
          res.writeHead(404, { 'Content-Type': 'text/plain' });
          res.end('Not Found. Use /health for status check.');
        }
      });

      // Node.js best practice: Handle EADDRINUSE with retry
      this.server.on('error', (e: any) => {
        if (e.code === 'EADDRINUSE' && retryCount < this.maxRetries) {
          console.error(`⚠️ Address in use, retrying... (attempt ${retryCount + 1}/${this.maxRetries})`);

          // Close any existing server and retry after delay (Node.js best practice)
          if (this.server) {
            this.server.close();
          }

          setTimeout(() => {
            this.port++;
            this.startWithRetry(retryCount + 1).then(resolve).catch(reject);
          }, this.retryDelay);
        } else {
          console.error('❌ Health server error:', e);
          reject(e);
        }
      });

      this.server.listen(this.port, () => {
        console.error(`🏥 Health server listening on http://localhost:${this.port}/health`);
        resolve();
      });
    });
  }

  /**
   * Get Prometheus-formatted metrics (FASE 4.1)
   *
   * Context7 Pattern: Prometheus exposition format
   * - Counter metrics (devstream_pool_completed_total)
   * - Gauge metrics (devstream_pool_runtime_avg_ms, devstream_pool_threads)
   * - Histogram-like metrics (runTime, waitTime statistics)
   *
   * Reference: https://prometheus.io/docs/instrumenting/exposition_formats/
   */
  private async getPrometheusMetrics(): Promise<string> {
    try {
      const pool = getDatabasePool();
      const stats = pool.getStats();

      // Prometheus format: # HELP, # TYPE, metric_name value
      const metrics = `# HELP devstream_pool_completed_total Total completed tasks
# TYPE devstream_pool_completed_total counter
devstream_pool_completed_total ${stats.completed}

# HELP devstream_pool_duration_seconds Pool uptime in seconds
# TYPE devstream_pool_duration_seconds gauge
devstream_pool_duration_seconds ${(stats.duration / 1000).toFixed(2)}

# HELP devstream_pool_runtime_avg_ms Average task runtime in milliseconds
# TYPE devstream_pool_runtime_avg_ms gauge
devstream_pool_runtime_avg_ms ${stats.runTime.average.toFixed(2)}

# HELP devstream_pool_runtime_min_ms Minimum task runtime in milliseconds
# TYPE devstream_pool_runtime_min_ms gauge
devstream_pool_runtime_min_ms ${stats.runTime.min.toFixed(2)}

# HELP devstream_pool_runtime_max_ms Maximum task runtime in milliseconds
# TYPE devstream_pool_runtime_max_ms gauge
devstream_pool_runtime_max_ms ${stats.runTime.max.toFixed(2)}

# HELP devstream_pool_waittime_avg_ms Average task wait time in milliseconds
# TYPE devstream_pool_waittime_avg_ms gauge
devstream_pool_waittime_avg_ms ${stats.waitTime.average.toFixed(2)}

# HELP devstream_pool_waittime_min_ms Minimum task wait time in milliseconds
# TYPE devstream_pool_waittime_min_ms gauge
devstream_pool_waittime_min_ms ${stats.waitTime.min.toFixed(2)}

# HELP devstream_pool_waittime_max_ms Maximum task wait time in milliseconds
# TYPE devstream_pool_waittime_max_ms gauge
devstream_pool_waittime_max_ms ${stats.waitTime.max.toFixed(2)}

# HELP devstream_pool_threads Current number of active threads
# TYPE devstream_pool_threads gauge
devstream_pool_threads ${stats.threads}

# HELP devstream_pool_queue_size Current queue size
# TYPE devstream_pool_queue_size gauge
devstream_pool_queue_size ${stats.queueSize}

# HELP devstream_process_uptime_seconds Process uptime in seconds
# TYPE devstream_process_uptime_seconds gauge
devstream_process_uptime_seconds ${Math.floor(process.uptime())}

# HELP devstream_heap_used_bytes Heap memory used in bytes
# TYPE devstream_heap_used_bytes gauge
devstream_heap_used_bytes ${process.memoryUsage().heapUsed}

# HELP devstream_heap_total_bytes Heap memory total in bytes
# TYPE devstream_heap_total_bytes gauge
devstream_heap_total_bytes ${process.memoryUsage().heapTotal}
`;

      return metrics;
    } catch (error) {
      console.error('Error collecting Prometheus metrics:', error);
      return '# Error collecting metrics\n';
    }
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