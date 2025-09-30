/**
 * DevStream Metrics HTTP Server
 *
 * Context7-compliant Prometheus metrics endpoint.
 * Lightweight HTTP server for exposing metrics to Prometheus scraper.
 *
 * Based on: https://github.com/siimon/prom-client best practices
 */

import http from 'http';
import { getMetrics, getMetricsJSON } from './metrics.js';
import { QualityMetricsCollector } from './quality-metrics.js';
import { ErrorTracker } from './error-tracking.js';

/**
 * Metrics Server Configuration
 */
export interface MetricsServerConfig {
  port: number;
  path: string;
}

/**
 * Default Configuration
 * Context7 pattern: Standard Prometheus setup
 */
export const DEFAULT_METRICS_CONFIG: MetricsServerConfig = {
  port: 9090,
  path: '/metrics',
};

/**
 * Metrics HTTP Server
 * Context7 pattern: Simple HTTP server for Prometheus scraping
 */
export class MetricsServer {
  private server: http.Server | null = null;
  private config: MetricsServerConfig;

  constructor(config: Partial<MetricsServerConfig> = {}) {
    this.config = { ...DEFAULT_METRICS_CONFIG, ...config };
  }

  /**
   * Start the metrics server
   * Context7 pattern: HTTP server for /metrics endpoint
   */
  async start(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.server = http.createServer(async (req, res) => {
        // CORS headers for browser access
        res.setHeader('Access-Control-Allow-Origin', '*');
        res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

        // Handle preflight
        if (req.method === 'OPTIONS') {
          res.writeHead(204);
          res.end();
          return;
        }

        // Route handling
        if (req.url === this.config.path && req.method === 'GET') {
          // Prometheus metrics endpoint
          try {
            const metrics = await getMetrics();
            res.setHeader('Content-Type', 'text/plain; version=0.0.4; charset=utf-8');
            res.writeHead(200);
            res.end(metrics);
          } catch (error) {
            console.error('Error generating metrics:', error);
            res.writeHead(500);
            res.end('Error generating metrics');
          }
        } else if (req.url === '/metrics/json' && req.method === 'GET') {
          // JSON format for programmatic access
          try {
            const metricsJson = await getMetricsJSON();
            res.setHeader('Content-Type', 'application/json');
            res.writeHead(200);
            res.end(JSON.stringify(metricsJson, null, 2));
          } catch (error) {
            console.error('Error generating JSON metrics:', error);
            res.writeHead(500);
            res.end(JSON.stringify({ error: 'Error generating metrics' }));
          }
        } else if (req.url === '/health' && req.method === 'GET') {
          // Health check endpoint
          res.setHeader('Content-Type', 'application/json');
          res.writeHead(200);
          res.end(JSON.stringify({
            status: 'healthy',
            timestamp: new Date().toISOString(),
            uptime: process.uptime(),
          }));
        } else if (req.url === '/quality' && req.method === 'GET') {
          // Quality metrics summary
          try {
            const qualityMetrics = await QualityMetricsCollector.getQualityMetrics();
            res.setHeader('Content-Type', 'application/json');
            res.writeHead(200);
            res.end(JSON.stringify(qualityMetrics, null, 2));
          } catch (error) {
            console.error('Error generating quality metrics:', error);
            res.writeHead(500);
            res.end(JSON.stringify({ error: 'Error generating quality metrics' }));
          }
        } else if (req.url === '/errors' && req.method === 'GET') {
          // Error tracking summary
          try {
            const errorStats = await ErrorTracker.getErrorStats();
            res.setHeader('Content-Type', 'application/json');
            res.writeHead(200);
            res.end(JSON.stringify(errorStats, null, 2));
          } catch (error) {
            console.error('Error generating error stats:', error);
            res.writeHead(500);
            res.end(JSON.stringify({ error: 'Error generating error stats' }));
          }
        } else {
          // 404 for unknown paths
          res.writeHead(404);
          res.end(JSON.stringify({
            error: 'Not Found',
            available_endpoints: [
              this.config.path,
              '/metrics/json',
              '/health',
              '/quality',
              '/errors',
            ],
          }));
        }
      });

      this.server.on('error', reject);

      this.server.listen(this.config.port, () => {
        console.log(`📊 Metrics server started on http://localhost:${this.config.port}`);
        console.log(`   - Prometheus endpoint: http://localhost:${this.config.port}${this.config.path}`);
        console.log(`   - JSON metrics: http://localhost:${this.config.port}/metrics/json`);
        console.log(`   - Health check: http://localhost:${this.config.port}/health`);
        console.log(`   - Quality metrics: http://localhost:${this.config.port}/quality`);
        console.log(`   - Error stats: http://localhost:${this.config.port}/errors`);
        resolve();
      });
    });
  }

  /**
   * Stop the metrics server
   */
  async stop(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.server) {
        resolve();
        return;
      }

      this.server.close((err) => {
        if (err) {
          reject(err);
        } else {
          console.log('📊 Metrics server stopped');
          this.server = null;
          resolve();
        }
      });
    });
  }

  /**
   * Get server info
   */
  getInfo() {
    return {
      running: this.server !== null,
      port: this.config.port,
      path: this.config.path,
      endpoints: {
        metrics: `http://localhost:${this.config.port}${this.config.path}`,
        json: `http://localhost:${this.config.port}/metrics/json`,
        health: `http://localhost:${this.config.port}/health`,
        quality: `http://localhost:${this.config.port}/quality`,
        errors: `http://localhost:${this.config.port}/errors`,
      },
    };
  }
}

/**
 * Create and export a global metrics server instance
 * Can be started with: `globalMetricsServer.start()`
 */
export const globalMetricsServer = new MetricsServer();