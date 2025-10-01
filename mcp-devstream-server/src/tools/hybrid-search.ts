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
 * Sanitize Unicode content to prevent JSON encoding errors
 * Replaces unpaired surrogate pairs that cause "no low surrogate" errors
 *
 * @param text - Text potentially containing emoji or special Unicode
 * @returns Sanitized text safe for JSON serialization
 */
/**
 * Sanitize Unicode strings to prevent JSON encoding errors.
 *
 * Context7 Research-Backed Approach (Node.js Official Pattern):
 * - Problem: SQLite stores arbitrary Unicode (including emoji/surrogate pairs)
 * - JSON.stringify() fails on unpaired surrogates (0xD800-0xDFFF)
 * - Solution: Use String.prototype.toWellFormed() (Node.js 20+/ES2024)
 *   - Replaces unpaired surrogates with U+FFFD (replacement character)
 *   - Preserves valid surrogate pairs (emoji, supplementary characters)
 *   - Official W3C/WHATWG spec for handling malformed Unicode
 *
 * References:
 * - Node.js FileAPI/unicode.html: Blob/File constructors replace unpaired surrogates
 * - ES2024 String.prototype.toWellFormed(): https://tc39.es/ecma262/#sec-string.prototype.towellformed
 *
 * @param text Input string potentially containing malformed Unicode
 * @returns Sanitized string safe for JSON encoding
 */
function sanitizeUnicode(text: string): string {
  if (!text) return text;

  try {
    // Context7 Best Practice: Use toWellFormed() for spec-compliant Unicode sanitization
    // Automatically replaces unpaired surrogates with \uFFFD while preserving valid pairs
    if (typeof (text as any).toWellFormed === 'function') {
      return (text as any).toWellFormed();
    }

    // Fallback for older Node.js versions (<20.0): Manual unpaired surrogate replacement
    // This preserves valid surrogate pairs while replacing unpaired ones with U+FFFD
    return text.replace(/[\uD800-\uDFFF]/g, (match, offset) => {
      const code = match.charCodeAt(0);
      const isHighSurrogate = code >= 0xD800 && code <= 0xDBFF;

      if (isHighSurrogate) {
        // Check if followed by low surrogate (valid pair)
        const nextChar = text[offset + 1];
        if (nextChar) {
          const nextCode = nextChar.charCodeAt(0);
          if (nextCode >= 0xDC00 && nextCode <= 0xDFFF) {
            return match + nextChar; // Valid pair, keep both
          }
        }
        return '\uFFFD'; // Unpaired high surrogate, replace with U+FFFD
      } else {
        return '\uFFFD'; // Unpaired low surrogate, replace with U+FFFD
      }
    });
  } catch (error) {
    // Final fallback: strip all non-ASCII characters if sanitization fails
    console.warn('⚠️  Unicode sanitization failed, stripping non-ASCII:', error);
    return text.replace(/[^\x00-\x7F]/g, '');
  }
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
   * With performance metrics collection and memory optimization
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

      // Context7 best practice: Convert embedding to Buffer for sqlite-vec
      // Memory optimization: Use typed array directly, let Node.js handle buffer lifecycle
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
            semantic_memory.id as memory_id,
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

      // Context7 best practice: Sanitize FTS5 query to prevent special character parsing errors
      const sanitizedQuery = this.sanitizeFts5Query(query);

      const params = [
        embeddingBuffer,                // vec0 MATCH parameter
        searchConfig.k,                 // vec0 LIMIT
        sanitizedQuery,                 // FTS5 MATCH parameter (sanitized)
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

        // Context7 best practice: Explicit cleanup to help V8 GC
        // Clear references to help Node.js garbage collector reclaim memory faster
        // This is critical for preventing heap exhaustion in long-running processes
        queryEmbedding.length = 0;  // Clear embedding array

        // Trigger GC if available (requires --expose-gc flag)
        if (global.gc && results.length > 0) {
          global.gc();
        }

        // Sanitize Unicode in ALL string/JSON fields to prevent JSON encoding errors
        // Critical: The error "no low surrogate" can occur in ANY field, not just content
        const sanitizedResults = results.map(result => {
          const sanitized: any = { ...result };

          // Sanitize all text fields
          if (sanitized.content) sanitized.content = sanitizeUnicode(sanitized.content);
          if (sanitized.content_type) sanitized.content_type = sanitizeUnicode(sanitized.content_type);
          if (sanitized.content_format) sanitized.content_format = sanitizeUnicode(sanitized.content_format);
          if (sanitized.source) sanitized.source = sanitizeUnicode(sanitized.source);
          if (sanitized.metadata) sanitized.metadata = sanitizeUnicode(sanitized.metadata);

          // Sanitize JSON fields (keywords, entities, context_snapshot, related_memory_ids)
          if (sanitized.keywords) {
            try {
              const parsed = typeof sanitized.keywords === 'string'
                ? JSON.parse(sanitized.keywords)
                : sanitized.keywords;
              sanitized.keywords = Array.isArray(parsed)
                ? parsed.map(k => sanitizeUnicode(String(k)))
                : sanitized.keywords;
            } catch {
              // If JSON parsing fails, sanitize as string
              sanitized.keywords = sanitizeUnicode(String(sanitized.keywords));
            }
          }

          if (sanitized.entities) {
            try {
              const parsed = typeof sanitized.entities === 'string'
                ? JSON.parse(sanitized.entities)
                : sanitized.entities;
              sanitized.entities = sanitizeUnicode(JSON.stringify(parsed));
            } catch {
              sanitized.entities = sanitizeUnicode(String(sanitized.entities));
            }
          }

          if (sanitized.context_snapshot) {
            try {
              const parsed = typeof sanitized.context_snapshot === 'string'
                ? JSON.parse(sanitized.context_snapshot)
                : sanitized.context_snapshot;
              sanitized.context_snapshot = sanitizeUnicode(JSON.stringify(parsed));
            } catch {
              sanitized.context_snapshot = sanitizeUnicode(String(sanitized.context_snapshot));
            }
          }

          return sanitized;
        });

        return sanitizedResults;
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
   * Sanitize FTS5 query to escape special characters and prevent operator parsing errors
   *
   * Context7 Research-Backed Approach (SQLite Official Docs + sqlite-vec):
   * - FTS5 interprets special characters as operators: `-` (NOT), `+` (phrase), `*` (prefix), `.` (column separator)
   * - Column name conflicts: Terms matching column names (e.g., "task") need explicit content: prefix
   * - Solution: Use `content:` column prefix + double-quote wrapping (official SQLite FTS5 pattern)
   * - Join with OR operator for broad semantic matching (sqlite-vec RRF pattern)
   *
   * Examples:
   * - Input: "micro-task release" → Output: content:"micro-task" OR content:"release"
   * - Input: "v0.1.0-beta" → Output: content:"v0.1.0-beta"
   * - Input: 'test "quoted" task' → Output: content:"test" OR content:"""quoted""" OR content:"task"
   *
   * References:
   * - SQLite FTS5 Official Docs: https://www.sqlite.org/fts5.html (column-specific query syntax)
   * - sqlite-vec RRF: https://github.com/asg017/sqlite-vec (Trust Score 9.7)
   *
   * @param query Raw user search query
   * @returns Sanitized FTS5-compatible query string with column prefix
   */
  private sanitizeFts5Query(query: string): string {
    // Split query into individual terms (whitespace separator)
    const terms = query
      .trim()
      .split(/\s+/)
      .filter(term => term.length > 0);

    // Handle empty query
    if (terms.length === 0) {
      return 'content:""';
    }

    // Quote each term for literal matching and escape internal double-quotes
    // Use `content:` prefix to avoid column name conflicts (e.g., "task" column)
    const quotedTerms = terms.map(term => {
      // Escape existing double-quotes with double double-quotes (SQL standard)
      const escaped = term.replace(/"/g, '""');
      // Wrap in double-quotes to force literal matching (ignore FTS5 operators like -, +, *, .)
      // Prefix with `content:` to explicitly target content column (prevents column name conflicts)
      return `content:"${escaped}"`;
    });

    // Join with OR operator for broad matching (sqlite-vec hybrid search pattern)
    // This maintains semantic search behavior while preventing operator parsing errors
    return quotedTerms.join(' OR ');
  }

  /**
   * FTS5-only search fallback
   * Context7 pattern: Simple keyword search when vector search unavailable
   * With performance metrics and query sanitization
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

      // Sanitize query to prevent FTS5 operator parsing errors (hyphens, dots, etc.)
      const sanitizedQuery = this.sanitizeFts5Query(query);

      const results = await MetricsCollector.trackDatabaseOperation(
        'fts5_search',
        async () => await this.database.query<HybridSearchResult>(sql, [sanitizedQuery, limit])
      );

      console.log(`✅ FTS5 search completed: ${results.length} results`);
      MetricsCollector.recordResults('keyword', results.length);

      // Track search quality metrics
      QualityMetricsCollector.analyzeResults('keyword', query, results);

      // Track query performance
      if (results.length > 0 && results[0].combined_rank) {
        globalQueryTracker.recordQuery(query, results[0].combined_rank);
      }

      // Sanitize Unicode in FTS5 results
      const sanitizedResults = results.map(result => ({
        ...result,
        content: sanitizeUnicode(result.content)
      }));

      return sanitizedResults;
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

      // Sanitize Unicode in vector search results
      const sanitizedResults = results.map(result => ({
        ...result,
        content: sanitizeUnicode(result.content)
      }));

      return sanitizedResults;
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