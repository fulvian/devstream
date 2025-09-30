/**
 * DevStream Hybrid Search Implementation
 *
 * Context7-compliant hybrid search combining:
 * - Vector similarity search (sqlite-vec vec0)
 * - Full-text keyword search (SQLite FTS5)
 * - Reciprocal Rank Fusion (RRF) for result merging
 *
 * Based on: https://github.com/asg017/sqlite-vec/blob/main/examples/nbc-headlines/3_search.ipynb
 */

import { DevStreamDatabase } from '../database.js';
import { DevStreamOllamaClient } from '../ollama-client.js';
import { MetricsCollector } from '../monitoring/metrics.js';
import { QualityMetricsCollector, globalQueryTracker } from '../monitoring/quality-metrics.js';

/**
 * Hybrid search result with combined ranking
 */
export interface HybridSearchResult {
  memory_id: string;
  content: string;
  content_type: string;
  created_at: string;
  vec_rank: number | null;
  fts_rank: number | null;
  combined_rank: number;
  vec_distance: number | null;
  fts_score: number | null;
}

/**
 * Hybrid search configuration
 */
export interface HybridSearchConfig {
  k: number;              // Number of results from each search method
  rrf_k: number;          // RRF constant (typically 60)
  weight_fts: number;     // Weight for FTS results (0-1)
  weight_vec: number;     // Weight for vector results (0-1)
}

/**
 * Default hybrid search configuration
 * Context7 pattern: Use proven defaults from sqlite-vec examples
 */
export const DEFAULT_HYBRID_CONFIG: HybridSearchConfig = {
  k: 10,
  rrf_k: 60,
  weight_fts: 1.0,
  weight_vec: 1.0
};

/**
 * Hybrid Search Engine
 * Context7-compliant implementation using RRF algorithm
 */
export class HybridSearchEngine {
  constructor(
    private database: DevStreamDatabase,
    private ollamaClient: DevStreamOllamaClient
  ) {}

  /**
   * Perform hybrid search combining vector and keyword search with RRF
   * Context7 pattern: Based on sqlite-vec NBC headlines example
   * With performance metrics collection
   */
  async search(
    query: string,
    config: Partial<HybridSearchConfig> = {}
  ): Promise<HybridSearchResult[]> {
    return await MetricsCollector.trackQuery('hybrid', async () => {
      const searchConfig = { ...DEFAULT_HYBRID_CONFIG, ...config };

      // Check if vector search is available
      const vectorAvailable = this.database.getVectorSearchStatus();

      if (!vectorAvailable) {
        console.warn('⚠️ Vector search not available - using FTS5 only');
        return this.ftsOnlySearch(query, searchConfig.k);
      }

      // Generate query embedding with metrics
      console.log(`🧠 Generating query embedding for: "${query}"`);
      const queryEmbedding = await MetricsCollector.trackEmbeddingGeneration(
        this.ollamaClient.getDefaultModel(),
        async () => await this.ollamaClient.generateEmbedding(query)
      );

      if (!queryEmbedding) {
        console.warn('⚠️ Failed to generate query embedding - using FTS5 only');
        return this.ftsOnlySearch(query, searchConfig.k);
      }

      // Convert embedding to Buffer for sqlite-vec
      const embeddingFloat32 = new Float32Array(queryEmbedding);
      const embeddingBuffer = Buffer.from(embeddingFloat32.buffer);

      // Context7 pattern: RRF hybrid search with CTEs
      const sql = `
        WITH vec_matches AS (
          SELECT
            memory_id,
            ROW_NUMBER() OVER (ORDER BY distance) as rank_number,
            distance
          FROM vec_semantic_memory
          WHERE embedding MATCH ?
            AND k = ?
        ),
        fts_matches AS (
          SELECT
            memory_id,
            ROW_NUMBER() OVER (ORDER BY rank) as rank_number,
            rank as score
          FROM fts_semantic_memory
          WHERE fts_semantic_memory MATCH ?
          LIMIT ?
        ),
        combined AS (
          SELECT
            semantic_memory.id,
            semantic_memory.content,
            semantic_memory.content_type,
            semantic_memory.created_at,
            vec_matches.rank_number as vec_rank,
            fts_matches.rank_number as fts_rank,
            (
              COALESCE(1.0 / (? + fts_matches.rank_number), 0.0) * ?
              + COALESCE(1.0 / (? + vec_matches.rank_number), 0.0) * ?
            ) as combined_rank,
            vec_matches.distance as vec_distance,
            fts_matches.score as fts_score
          FROM fts_matches
          FULL OUTER JOIN vec_matches ON vec_matches.memory_id = fts_matches.memory_id
          JOIN semantic_memory ON semantic_memory.id = COALESCE(fts_matches.memory_id, vec_matches.memory_id)
          ORDER BY combined_rank DESC
        )
        SELECT * FROM combined
      `;

      const params = [
        embeddingBuffer,                // vec0 MATCH parameter
        searchConfig.k,                 // vec0 LIMIT
        query,                          // FTS5 MATCH parameter
        searchConfig.k,                 // FTS5 LIMIT
        searchConfig.rrf_k,             // RRF constant for FTS
        searchConfig.weight_fts,        // FTS weight
        searchConfig.rrf_k,             // RRF constant for vec
        searchConfig.weight_vec         // Vector weight
      ];

      try {
        const results = await MetricsCollector.trackDatabaseOperation(
          'hybrid_search',
          async () => await this.database.query<HybridSearchResult>(sql, params)
        );

        console.log(`✅ Hybrid search completed: ${results.length} results`);

        // Track result count and RRF scores
        MetricsCollector.recordResults('hybrid', results.length);
        MetricsCollector.recordRRFScores(results.map(r => r.combined_rank));

        // Track search quality metrics
        QualityMetricsCollector.analyzeResults('hybrid', query, results);

        // Track query performance over time
        if (results.length > 0 && results[0].combined_rank) {
          globalQueryTracker.recordQuery(query, results[0].combined_rank);
        }

        return results;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        console.error(`❌ Hybrid search failed: ${errorMessage}`);

        // Fallback to FTS5 only
        console.log('🔄 Falling back to FTS5 search...');
        return this.ftsOnlySearch(query, searchConfig.k);
      }
    });
  }

  /**
   * FTS5-only search fallback
   * Context7 pattern: Simple keyword search when vector search unavailable
   * With performance metrics
   */
  private async ftsOnlySearch(query: string, limit: number): Promise<HybridSearchResult[]> {
    return await MetricsCollector.trackQuery('keyword', async () => {
      const sql = `
        SELECT
          semantic_memory.id as memory_id,
          semantic_memory.content,
          semantic_memory.content_type,
          semantic_memory.created_at,
          NULL as vec_rank,
          ROW_NUMBER() OVER (ORDER BY rank) as fts_rank,
          (1.0 / (60 + ROW_NUMBER() OVER (ORDER BY rank))) as combined_rank,
          NULL as vec_distance,
          rank as fts_score
        FROM fts_semantic_memory
        JOIN semantic_memory ON semantic_memory.id = fts_semantic_memory.memory_id
        WHERE fts_semantic_memory MATCH ?
        ORDER BY rank
        LIMIT ?
      `;

      const results = await MetricsCollector.trackDatabaseOperation(
        'fts5_search',
        async () => await this.database.query<HybridSearchResult>(sql, [query, limit])
      );

      console.log(`✅ FTS5 search completed: ${results.length} results`);
      MetricsCollector.recordResults('keyword', results.length);

      // Track search quality metrics
      QualityMetricsCollector.analyzeResults('keyword', query, results);

      // Track query performance
      if (results.length > 0 && results[0].combined_rank) {
        globalQueryTracker.recordQuery(query, results[0].combined_rank);
      }

      return results;
    });
  }

  /**
   * Vector-only search (for testing or when FTS5 unavailable)
   * With performance metrics
   */
  async vectorSearch(
    queryEmbedding: number[],
    limit: number = 10
  ): Promise<HybridSearchResult[]> {
    return await MetricsCollector.trackQuery('vector', async () => {
      const embeddingFloat32 = new Float32Array(queryEmbedding);
      const embeddingBuffer = Buffer.from(embeddingFloat32.buffer);

      const sql = `
        SELECT
          semantic_memory.id as memory_id,
          semantic_memory.content,
          semantic_memory.content_type,
          semantic_memory.created_at,
          ROW_NUMBER() OVER (ORDER BY distance) as vec_rank,
          NULL as fts_rank,
          (1.0 / (60 + ROW_NUMBER() OVER (ORDER BY distance))) as combined_rank,
          distance as vec_distance,
          NULL as fts_score
        FROM vec_semantic_memory
        JOIN semantic_memory ON semantic_memory.id = vec_semantic_memory.memory_id
        WHERE embedding MATCH ?
          AND k = ?
        ORDER BY distance
      `;

      const results = await MetricsCollector.trackDatabaseOperation(
        'vector_search',
        async () => await this.database.query<HybridSearchResult>(sql, [embeddingBuffer, limit])
      );

      console.log(`✅ Vector search completed: ${results.length} results`);
      MetricsCollector.recordResults('vector', results.length);

      // Track search quality metrics
      // Note: vector search doesn't have a query string, so we use empty string
      QualityMetricsCollector.analyzeResults('vector', '', results);

      return results;
    });
  }

  /**
   * Get search diagnostics
   * Context7 pattern: Observability for debugging and optimization
   * With metrics gauge updates
   */
  async getDiagnostics() {
    const vectorAvailable = this.database.getVectorSearchStatus();
    const vectorDiagnostics = vectorAvailable
      ? await this.database.getVectorSearchDiagnostics()
      : { available: false, version: null, error: 'Extension not loaded' };

    const vec0Count = vectorAvailable ? (await this.database.queryOne<{ count: number }>(
      'SELECT COUNT(*) as count FROM vec_semantic_memory', []
    ))?.count || 0 : 0;

    const fts5Count = (await this.database.queryOne<{ count: number }>(
      'SELECT COUNT(*) as count FROM fts_semantic_memory', []
    ))?.count || 0;

    // Update metrics gauges
    MetricsCollector.updateIndexSizes(vec0Count, fts5Count);

    const stats = {
      vector_search: vectorDiagnostics,
      fts5_available: true, // Built-in to SQLite
      total_memories: (await this.database.queryOne<{ count: number }>(
        'SELECT COUNT(*) as count FROM semantic_memory', []
      ))?.count || 0,
      memories_with_embeddings: (await this.database.queryOne<{ count: number }>(
        'SELECT COUNT(*) as count FROM semantic_memory WHERE embedding IS NOT NULL', []
      ))?.count || 0,
      vec0_indexed: vec0Count,
      fts5_indexed: fts5Count
    };

    return stats;
  }
}