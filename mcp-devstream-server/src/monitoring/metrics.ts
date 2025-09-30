/**
 * DevStream Performance Metrics Collection
 *
 * Context7-compliant implementation using prom-client
 * Based on: https://github.com/siimon/prom-client
 *
 * Metrics collected:
 * - Query duration (histogram)
 * - Query count (counter)
 * - Vector search performance (histogram)
 * - FTS5 search performance (histogram)
 * - Embedding generation time (histogram)
 * - Active queries (gauge)
 * - Database connection status (gauge)
 */

import * as promClient from 'prom-client';

/**
 * Metrics Registry
 * Context7 pattern: Custom registry for isolation
 */
export const metricsRegistry = new promClient.Registry();

/**
 * Collect default Node.js metrics
 * Context7 pattern: Default metrics with custom prefix
 */
promClient.collectDefaultMetrics({
  register: metricsRegistry,
  prefix: 'devstream_',
  labels: {
    app: 'devstream-mcp-server',
  },
});

/**
 * Query Duration Histogram
 * Context7 pattern: Exponential buckets for wide range of query times
 * Tracks: hybrid search, vector-only, FTS5-only query durations
 */
export const queryDurationHistogram = new promClient.Histogram({
  name: 'devstream_query_duration_seconds',
  help: 'Duration of search queries in seconds',
  labelNames: ['query_type', 'status'],
  buckets: promClient.exponentialBuckets(0.001, 2, 10), // 1ms to ~1s
  registers: [metricsRegistry],
});

/**
 * Query Counter
 * Context7 pattern: Counter for tracking query volume
 */
export const queryCounter = new promClient.Counter({
  name: 'devstream_queries_total',
  help: 'Total number of search queries',
  labelNames: ['query_type', 'status'],
  registers: [metricsRegistry],
});

/**
 * Vector Search Performance Histogram
 * Context7 pattern: Specific histogram for vector operations
 */
export const vectorSearchHistogram = new promClient.Histogram({
  name: 'devstream_vector_search_duration_seconds',
  help: 'Duration of vector similarity search in seconds',
  labelNames: ['status'],
  buckets: promClient.exponentialBuckets(0.001, 2, 8), // 1ms to ~256ms
  registers: [metricsRegistry],
});

/**
 * FTS5 Search Performance Histogram
 * Context7 pattern: Specific histogram for keyword search
 */
export const fts5SearchHistogram = new promClient.Histogram({
  name: 'devstream_fts5_search_duration_seconds',
  help: 'Duration of FTS5 keyword search in seconds',
  labelNames: ['status'],
  buckets: promClient.exponentialBuckets(0.001, 2, 8), // 1ms to ~256ms
  registers: [metricsRegistry],
});

/**
 * Embedding Generation Histogram
 * Context7 pattern: Track external API call performance
 */
export const embeddingGenerationHistogram = new promClient.Histogram({
  name: 'devstream_embedding_generation_duration_seconds',
  help: 'Duration of embedding generation via Ollama in seconds',
  labelNames: ['status', 'model'],
  buckets: promClient.linearBuckets(0.1, 0.1, 10), // 100ms to 1s
  registers: [metricsRegistry],
});

/**
 * Active Queries Gauge
 * Context7 pattern: Point-in-time observation of concurrent queries
 */
export const activeQueriesGauge = new promClient.Gauge({
  name: 'devstream_active_queries',
  help: 'Number of currently executing queries',
  labelNames: ['query_type'],
  registers: [metricsRegistry],
});

/**
 * Results Count Histogram
 * Context7 pattern: Track result set sizes
 */
export const resultsCountHistogram = new promClient.Histogram({
  name: 'devstream_query_results_count',
  help: 'Number of results returned by queries',
  labelNames: ['query_type'],
  buckets: [0, 1, 5, 10, 20, 50, 100],
  registers: [metricsRegistry],
});

/**
 * Database Operations Counter
 * Context7 pattern: Track database operations
 */
export const databaseOpsCounter = new promClient.Counter({
  name: 'devstream_database_operations_total',
  help: 'Total number of database operations',
  labelNames: ['operation', 'status'],
  registers: [metricsRegistry],
});

/**
 * Memory Storage Counter
 * Context7 pattern: Track memory storage operations
 */
export const memoryStorageCounter = new promClient.Counter({
  name: 'devstream_memory_storage_total',
  help: 'Total number of memories stored',
  labelNames: ['content_type', 'has_embedding'],
  registers: [metricsRegistry],
});

/**
 * Vector Index Size Gauge
 * Context7 pattern: Async collect for point-in-time metrics
 */
export const vectorIndexSizeGauge = new promClient.Gauge({
  name: 'devstream_vector_index_size',
  help: 'Number of vectors in vec0 index',
  registers: [metricsRegistry],
});

/**
 * FTS5 Index Size Gauge
 * Context7 pattern: Async collect for point-in-time metrics
 */
export const fts5IndexSizeGauge = new promClient.Gauge({
  name: 'devstream_fts5_index_size',
  help: 'Number of documents in FTS5 index',
  registers: [metricsRegistry],
});

/**
 * RRF Score Histogram
 * Context7 pattern: Track ranking quality
 */
export const rrfScoreHistogram = new promClient.Histogram({
  name: 'devstream_rrf_score',
  help: 'Distribution of RRF combined ranking scores',
  buckets: promClient.linearBuckets(0, 0.01, 10), // 0 to 0.1 by 0.01
  registers: [metricsRegistry],
});

/**
 * Query Complexity Gauge
 * Context7 pattern: Track hybrid vs single-method queries
 */
export const queryComplexityGauge = new promClient.Gauge({
  name: 'devstream_query_complexity',
  help: 'Complexity of queries (0=keyword only, 1=vector only, 2=hybrid)',
  labelNames: ['type'],
  registers: [metricsRegistry],
});

/**
 * Metric Collection Helper
 * Context7 pattern: Utility for timing operations
 */
export class MetricsCollector {
  /**
   * Track query execution with automatic timing
   * Context7 pattern: startTimer utility method
   */
  static async trackQuery<T>(
    queryType: 'hybrid' | 'vector' | 'keyword',
    operation: () => Promise<T>
  ): Promise<T> {
    const endTimer = queryDurationHistogram.startTimer({
      query_type: queryType,
    });

    activeQueriesGauge.inc({ query_type: queryType });

    try {
      const result = await operation();

      endTimer({ status: 'success' });
      queryCounter.inc({ query_type: queryType, status: 'success' });

      return result;
    } catch (error) {
      endTimer({ status: 'error' });
      queryCounter.inc({ query_type: queryType, status: 'error' });
      throw error;
    } finally {
      activeQueriesGauge.dec({ query_type: queryType });
    }
  }

  /**
   * Track embedding generation
   * Context7 pattern: Timing external API calls
   */
  static async trackEmbeddingGeneration<T>(
    model: string,
    operation: () => Promise<T>
  ): Promise<T> {
    const endTimer = embeddingGenerationHistogram.startTimer({ model });

    try {
      const result = await operation();
      endTimer({ status: 'success', model });
      return result;
    } catch (error) {
      endTimer({ status: 'error', model });
      throw error;
    }
  }

  /**
   * Track database operations
   * Context7 pattern: Operation-specific tracking
   */
  static async trackDatabaseOperation<T>(
    operation: string,
    task: () => Promise<T>
  ): Promise<T> {
    try {
      const result = await task();
      databaseOpsCounter.inc({ operation, status: 'success' });
      return result;
    } catch (error) {
      databaseOpsCounter.inc({ operation, status: 'error' });
      throw error;
    }
  }

  /**
   * Record query results
   * Context7 pattern: Observe histogram values
   */
  static recordResults(queryType: string, count: number): void {
    resultsCountHistogram.observe({ query_type: queryType }, count);
  }

  /**
   * Record RRF scores
   * Context7 pattern: Track ranking quality metrics
   */
  static recordRRFScores(scores: number[]): void {
    scores.forEach(score => {
      rrfScoreHistogram.observe(score);
    });
  }

  /**
   * Update index sizes
   * Context7 pattern: Point-in-time gauge updates
   */
  static updateIndexSizes(vecCount: number, ftsCount: number): void {
    vectorIndexSizeGauge.set(vecCount);
    fts5IndexSizeGauge.set(ftsCount);
  }
}

/**
 * Get metrics in Prometheus format
 * Context7 pattern: Async registry metrics
 */
export async function getMetrics(): Promise<string> {
  return await metricsRegistry.metrics();
}

/**
 * Get metrics as JSON
 * Context7 pattern: JSON format for programmatic access
 */
export async function getMetricsJSON() {
  return await metricsRegistry.getMetricsAsJSON();
}

/**
 * Reset all metrics (for testing)
 * Context7 pattern: Clean slate for test isolation
 */
export function resetMetrics(): void {
  metricsRegistry.resetMetrics();
}