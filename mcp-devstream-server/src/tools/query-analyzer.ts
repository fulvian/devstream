/**
 * Query Analyzer for Adaptive Threshold System
 *
 * Research-backed implementation based on:
 * - Adaptive-RAG (NAACL 2024): Query complexity classification
 * - Azure AI Search 2024: Dynamic threshold filtering
 * - IDF-based term specificity analysis
 *
 * Provides:
 * - Query complexity detection (simple/medium/complex/technical)
 * - IDF-based term analysis
 * - Dynamic threshold recommendations
 * - Adaptive RRF weight calculation
 */

import { DevStreamDatabase } from '../database.js';

/**
 * Query complexity levels
 * Based on Adaptive-RAG (NAACL 2024) classification
 */
export type QueryComplexity = 'simple' | 'medium' | 'complex' | 'technical';

/**
 * Query analysis result
 */
export interface QueryAnalysis {
  query: string;
  complexity: QueryComplexity;
  termCount: number;
  technicalTermCount: number;
  specificityScore: number;        // 0-1 (IDF-based)
  avgIDF: number;
  maxIDF: number;
  recommendedThreshold: number;    // Dynamic threshold
  recommendedWeights: {
    weight_vec: number;
    weight_fts: number;
  };
  reasoning: string;                // Human-readable explanation
}

/**
 * Threshold configuration by complexity level
 * Based on Azure AI Search 2024 adaptive filtering patterns
 */
const THRESHOLD_MAP: Record<QueryComplexity, number> = {
  simple:    0.03,  // Generic queries: high threshold (3%) - filter noise
  medium:    0.02,  // Average queries: medium threshold (2%)
  complex:   0.01,  // Multi-term queries: low threshold (1%)
  technical: 0.005  // Highly specific queries: minimal threshold (0.5%)
};

/**
 * RRF weight configuration by complexity level
 * Based on Azure AI Search vector weighting patterns
 */
const WEIGHT_MAP: Record<QueryComplexity, { weight_vec: number, weight_fts: number }> = {
  simple:    { weight_vec: 1.0, weight_fts: 1.2 },  // Favor keyword for generic terms
  medium:    { weight_vec: 1.0, weight_fts: 1.0 },  // Balanced
  complex:   { weight_vec: 1.2, weight_fts: 1.0 },  // Slight vector preference
  technical: { weight_vec: 1.5, weight_fts: 0.7 }   // Strong vector preference for technical terms
};

/**
 * Query Analyzer
 * Analyzes query complexity and recommends adaptive thresholds and weights
 */
export class QueryAnalyzer {
  private idfCache: Map<string, number> = new Map();
  private corpusSize: number = 0;
  private initialized: boolean = false;

  constructor(private database: DevStreamDatabase) {}

  /**
   * Initialize IDF cache from corpus
   * Calculates Inverse Document Frequency for all terms in semantic_memory
   */
  async initialize(): Promise<void> {
    if (this.initialized) return;

    try {
      // Get total document count
      const countResult = await this.database.queryOne<{ count: number }>(
        'SELECT COUNT(*) as count FROM semantic_memory',
        []
      );
      this.corpusSize = countResult?.count || 0;

      if (this.corpusSize === 0) {
        console.warn('⚠️ QueryAnalyzer: No documents in corpus, using defaults');
        this.initialized = true;
        return;
      }

      // Calculate IDF for top terms
      // For performance, we calculate IDF only for terms appearing in recent documents
      const termFrequencies = await this.calculateTermFrequencies();

      for (const [term, docCount] of termFrequencies.entries()) {
        const idf = Math.log((this.corpusSize + 1) / (docCount + 1));
        this.idfCache.set(term.toLowerCase(), idf);
      }

      this.initialized = true;
      console.error(`✅ QueryAnalyzer initialized: ${this.idfCache.size} terms, ${this.corpusSize} documents`);

    } catch (error) {
      console.error('❌ QueryAnalyzer initialization failed:', error);
      this.initialized = true; // Mark as initialized anyway to avoid repeated attempts
    }
  }

  /**
   * Calculate term frequencies across corpus
   * Returns map of term → document count
   */
  private async calculateTermFrequencies(): Promise<Map<string, number>> {
    const termFrequencies = new Map<string, number>();

    try {
      // Sample recent documents for IDF calculation (performance optimization)
      const sampleSize = Math.min(1000, this.corpusSize);
      const documents = await this.database.query<{ content: string }>(
        `SELECT content FROM semantic_memory
         ORDER BY created_at DESC
         LIMIT ?`,
        [sampleSize]
      );

      // Count document frequency for each term
      for (const doc of documents) {
        const terms = this.tokenize(doc.content);
        const uniqueTerms = new Set(terms);

        for (const term of uniqueTerms) {
          const normalizedTerm = term.toLowerCase();
          termFrequencies.set(
            normalizedTerm,
            (termFrequencies.get(normalizedTerm) || 0) + 1
          );
        }
      }

    } catch (error) {
      console.error('❌ Term frequency calculation failed:', error);
    }

    return termFrequencies;
  }

  /**
   * Tokenize text into terms
   * Simple whitespace + punctuation tokenization
   */
  private tokenize(text: string): string[] {
    return text
      .toLowerCase()
      .replace(/[^\w\s]/g, ' ')  // Replace punctuation with spaces
      .split(/\s+/)
      .filter(term => term.length > 2);  // Filter short terms
  }

  /**
   * Get IDF for a term
   * Returns cached value or calculates on-the-fly
   */
  private getIDF(term: string): number {
    const normalizedTerm = term.toLowerCase();

    // Check cache first
    if (this.idfCache.has(normalizedTerm)) {
      return this.idfCache.get(normalizedTerm)!;
    }

    // Default IDF for unknown terms (medium specificity)
    // Assumes term appears in ~10% of documents
    const defaultIDF = Math.log((this.corpusSize + 1) / (this.corpusSize * 0.1 + 1));
    return defaultIDF;
  }

  /**
   * Analyze query and return complexity assessment
   * Main entry point for query analysis
   */
  async analyze(query: string): Promise<QueryAnalysis> {
    // Ensure initialized
    if (!this.initialized) {
      await this.initialize();
    }

    // Tokenize query
    const terms = this.tokenize(query);
    const termCount = terms.length;

    // Calculate IDF metrics
    const idfScores = terms.map(term => this.getIDF(term));
    const avgIDF = idfScores.length > 0
      ? idfScores.reduce((a, b) => a + b, 0) / idfScores.length
      : 0;
    const maxIDF = idfScores.length > 0 ? Math.max(...idfScores) : 0;

    // Specificity score (0-1): normalized average IDF
    // High IDF → High specificity (technical/rare terms)
    // Low IDF → Low specificity (common terms)
    const maxPossibleIDF = Math.log(this.corpusSize + 1);
    const specificityScore = maxPossibleIDF > 0
      ? Math.min(avgIDF / maxPossibleIDF, 1.0)
      : 0.5;

    // Count technical terms (high IDF)
    const technicalThreshold = maxPossibleIDF * 0.7;  // Top 30% IDF range
    const technicalTermCount = idfScores.filter(idf => idf >= technicalThreshold).length;

    // Determine complexity based on Adaptive-RAG patterns + IDF analysis
    const complexity = this.classifyComplexity(
      termCount,
      technicalTermCount,
      specificityScore,
      avgIDF
    );

    // Get recommended threshold and weights
    const recommendedThreshold = THRESHOLD_MAP[complexity];
    const recommendedWeights = WEIGHT_MAP[complexity];

    // Generate reasoning
    const reasoning = this.generateReasoning(
      complexity,
      termCount,
      technicalTermCount,
      specificityScore
    );

    return {
      query,
      complexity,
      termCount,
      technicalTermCount,
      specificityScore,
      avgIDF,
      maxIDF,
      recommendedThreshold,
      recommendedWeights,
      reasoning
    };
  }

  /**
   * Classify query complexity
   * Based on Adaptive-RAG (NAACL 2024) + IDF-based term analysis
   */
  private classifyComplexity(
    termCount: number,
    technicalTermCount: number,
    specificityScore: number,
    avgIDF: number
  ): QueryComplexity {
    // Technical: High specificity + multiple technical terms
    if (specificityScore > 0.75 && technicalTermCount >= 2) {
      return 'technical';
    }

    // Technical: Very high specificity even with fewer terms
    if (specificityScore > 0.85) {
      return 'technical';
    }

    // Complex: Long query OR high specificity
    if (termCount >= 5 || (specificityScore > 0.6 && termCount >= 3)) {
      return 'complex';
    }

    // Medium: Average length and specificity
    if (termCount >= 2 && specificityScore > 0.4) {
      return 'medium';
    }

    // Simple: Short query with common terms
    return 'simple';
  }

  /**
   * Generate human-readable reasoning
   */
  private generateReasoning(
    complexity: QueryComplexity,
    termCount: number,
    technicalTermCount: number,
    specificityScore: number
  ): string {
    const specificityPercent = (specificityScore * 100).toFixed(0);

    switch (complexity) {
      case 'technical':
        return `Technical query: ${technicalTermCount}/${termCount} technical terms, ${specificityPercent}% specificity. Using minimal threshold (0.5%) and vector-weighted search.`;
      case 'complex':
        return `Complex query: ${termCount} terms with ${specificityPercent}% specificity. Using low threshold (1%) for comprehensive results.`;
      case 'medium':
        return `Medium complexity: ${termCount} terms with ${specificityPercent}% specificity. Using balanced threshold (2%) and weights.`;
      case 'simple':
        return `Simple query: ${termCount} common terms with ${specificityPercent}% specificity. Using higher threshold (3%) to filter noise.`;
    }
  }

  /**
   * Get diagnostics for debugging
   */
  async getDiagnostics() {
    return {
      initialized: this.initialized,
      corpusSize: this.corpusSize,
      cachedTerms: this.idfCache.size,
      sampleTerms: Array.from(this.idfCache.entries())
        .sort((a, b) => b[1] - a[1])  // Sort by IDF descending
        .slice(0, 10)
        .map(([term, idf]) => ({ term, idf: idf.toFixed(3) }))
    };
  }
}
