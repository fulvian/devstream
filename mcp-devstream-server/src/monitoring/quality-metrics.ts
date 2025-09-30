/**
 * DevStream Search Quality Metrics
 *
 * Context7-compliant metrics for measuring search result quality and relevance.
 * Based on information retrieval best practices.
 *
 * Metrics include:
 * - Relevance scores distribution
 * - Result diversity
 * - Hybrid vs single-method performance
 * - Zero-result queries tracking
 * - Query-result latency correlation
 */

import * as promClient from 'prom-client';
import { metricsRegistry } from './metrics.js';
import { HybridSearchResult } from '../tools/hybrid-search.js';

/**
 * Search Quality Histogram
 * Context7 pattern: Track distribution of top result scores
 */
export const searchQualityHistogram = new promClient.Histogram({
  name: 'devstream_search_quality_score',
  help: 'Distribution of top search result quality scores (RRF combined_rank)',
  labelNames: ['query_type'],
  buckets: [0, 0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04],
  registers: [metricsRegistry],
});

/**
 * Zero Results Counter
 * Context7 pattern: Track queries that return no results
 */
export const zeroResultsCounter = new promClient.Counter({
  name: 'devstream_zero_results_total',
  help: 'Total number of queries that returned zero results',
  labelNames: ['query_type'],
  registers: [metricsRegistry],
});

/**
 * Result Diversity Gauge
 * Context7 pattern: Measure content type diversity in results
 */
export const resultDiversityGauge = new promClient.Gauge({
  name: 'devstream_result_diversity',
  help: 'Number of unique content types in recent search results',
  labelNames: ['query_type'],
  registers: [metricsRegistry],
});

/**
 * Hybrid Coverage Gauge
 * Context7 pattern: Track how many results come from both methods vs single method
 */
export const hybridCoverageGauge = new promClient.Gauge({
  name: 'devstream_hybrid_coverage',
  help: 'Percentage of results matched by both vector and keyword search',
  registers: [metricsRegistry],
});

/**
 * Recall at K Histogram
 * Context7 pattern: Information retrieval metric
 */
export const recallAtKHistogram = new promClient.Histogram({
  name: 'devstream_recall_at_k',
  help: 'Recall at K for search queries (what % of relevant docs in top K)',
  labelNames: ['k_value'],
  buckets: [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
  registers: [metricsRegistry],
});

/**
 * Mean Reciprocal Rank (MRR) Histogram
 * Context7 pattern: Classic IR metric for ranking quality
 */
export const mrrHistogram = new promClient.Histogram({
  name: 'devstream_mean_reciprocal_rank',
  help: 'Mean Reciprocal Rank of search results',
  buckets: [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
  registers: [metricsRegistry],
});

/**
 * Query Length Distribution
 * Context7 pattern: Understand query patterns
 */
export const queryLengthHistogram = new promClient.Histogram({
  name: 'devstream_query_length_chars',
  help: 'Distribution of query lengths in characters',
  labelNames: ['query_type'],
  buckets: [0, 10, 20, 50, 100, 200, 500, 1000],
  registers: [metricsRegistry],
});

/**
 * Search Result Rank Distribution
 * Context7 pattern: Track which ranks are actually used
 */
export const resultRankHistogram = new promClient.Histogram({
  name: 'devstream_result_rank_accessed',
  help: 'Distribution of result ranks that are accessed/clicked',
  buckets: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20],
  registers: [metricsRegistry],
});

/**
 * Quality Metrics Collector
 * Context7 pattern: Helper class for quality metric calculation
 */
export class QualityMetricsCollector {
  /**
   * Analyze search results for quality metrics
   * Context7 pattern: Comprehensive result analysis
   */
  static analyzeResults(
    queryType: 'hybrid' | 'vector' | 'keyword',
    query: string,
    results: HybridSearchResult[]
  ): void {
    // Track query length
    queryLengthHistogram.observe({ query_type: queryType }, query.length);

    // Track zero results
    if (results.length === 0) {
      zeroResultsCounter.inc({ query_type: queryType });
      return;
    }

    // Track top result quality (RRF score)
    if (results[0]?.combined_rank) {
      searchQualityHistogram.observe(
        { query_type: queryType },
        results[0].combined_rank
      );
    }

    // Measure result diversity (unique content types)
    const uniqueContentTypes = new Set(results.map(r => r.content_type));
    resultDiversityGauge.set(
      { query_type: queryType },
      uniqueContentTypes.size
    );

    // For hybrid queries, measure coverage (both methods vs single method)
    if (queryType === 'hybrid') {
      const bothMethods = results.filter(r => r.vec_rank && r.fts_rank).length;
      const coverage = results.length > 0 ? (bothMethods / results.length) * 100 : 0;
      hybridCoverageGauge.set(coverage);
    }
  }

  /**
   * Calculate and record Mean Reciprocal Rank (MRR)
   * Context7 pattern: Standard IR metric
   *
   * MRR = 1 / rank of first relevant result
   * Higher is better (1.0 = relevant result at rank 1)
   */
  static recordMRR(rankOfFirstRelevant: number): void {
    if (rankOfFirstRelevant > 0) {
      const mrr = 1.0 / rankOfFirstRelevant;
      mrrHistogram.observe(mrr);
    } else {
      // No relevant results found
      mrrHistogram.observe(0);
    }
  }

  /**
   * Calculate and record Recall at K
   * Context7 pattern: Information retrieval metric
   *
   * Recall@K = (relevant docs in top K) / (total relevant docs)
   */
  static recordRecallAtK(k: number, relevantInTopK: number, totalRelevant: number): void {
    if (totalRelevant > 0) {
      const recall = relevantInTopK / totalRelevant;
      recallAtKHistogram.observe({ k_value: k.toString() }, recall);
    }
  }

  /**
   * Track result access/click through
   * Context7 pattern: User interaction tracking
   */
  static recordResultAccess(rank: number): void {
    resultRankHistogram.observe(rank);
  }

  /**
   * Get quality metrics summary
   * Context7 pattern: Aggregated quality report
   */
  static async getQualityMetrics() {
    // In a real implementation, this would query the metrics registry
    // and calculate aggregate statistics
    return {
      search_quality: {
        description: 'Top result RRF score distribution',
        metric: 'devstream_search_quality_score'
      },
      zero_results_rate: {
        description: 'Percentage of queries with zero results',
        metric: 'devstream_zero_results_total'
      },
      result_diversity: {
        description: 'Number of unique content types in results',
        metric: 'devstream_result_diversity'
      },
      hybrid_coverage: {
        description: 'Percentage of results from both search methods',
        metric: 'devstream_hybrid_coverage'
      },
      mean_reciprocal_rank: {
        description: 'Average MRR across queries',
        metric: 'devstream_mean_reciprocal_rank'
      },
      recall_metrics: {
        description: 'Recall at K for various K values',
        metric: 'devstream_recall_at_k'
      }
    };
  }
}

/**
 * Query Performance Tracker
 * Context7 pattern: Track query-specific quality over time
 */
export class QueryPerformanceTracker {
  private queryHistory: Map<string, number[]> = new Map();

  /**
   * Record query result quality
   */
  recordQuery(query: string, topScore: number): void {
    if (!this.queryHistory.has(query)) {
      this.queryHistory.set(query, []);
    }
    this.queryHistory.get(query)!.push(topScore);
  }

  /**
   * Get average quality for a query
   */
  getAverageQuality(query: string): number | null {
    const scores = this.queryHistory.get(query);
    if (!scores || scores.length === 0) return null;

    const sum = scores.reduce((a, b) => a + b, 0);
    return sum / scores.length;
  }

  /**
   * Identify degrading queries (quality decreasing over time)
   */
  getDegradingQueries(threshold: number = 0.2): string[] {
    const degrading: string[] = [];

    for (const [query, scores] of this.queryHistory) {
      if (scores.length < 3) continue; // Need at least 3 data points

      // Compare first third vs last third
      const firstThird = scores.slice(0, Math.floor(scores.length / 3));
      const lastThird = scores.slice(-Math.floor(scores.length / 3));

      const avgFirst = firstThird.reduce((a, b) => a + b) / firstThird.length;
      const avgLast = lastThird.reduce((a, b) => a + b) / lastThird.length;

      const degradation = (avgFirst - avgLast) / avgFirst;

      if (degradation > threshold) {
        degrading.push(query);
      }
    }

    return degrading;
  }

  /**
   * Clear history (for testing or reset)
   */
  clear(): void {
    this.queryHistory.clear();
  }
}

/**
 * Global query performance tracker instance
 */
export const globalQueryTracker = new QueryPerformanceTracker();