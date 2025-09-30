/**
 * DevStream Memory Management Tools
 *
 * MCP tools for managing DevStream semantic memory and knowledge storage.
 * Context7-compliant automatic embedding generation using embeddinggemma.
 */

import { DevStreamDatabase, SemanticMemory } from '../database.js';
import { getOllamaClient, DevStreamOllamaClient } from '../ollama-client.js';
import { HybridSearchEngine } from './hybrid-search.js';
import { MetricsCollector, memoryStorageCounter } from '../monitoring/metrics.js';
import { z } from 'zod';

// Input validation schemas
const StoreMemoryInputSchema = z.object({
  content: z.string().min(1),
  content_type: z.enum(['code', 'documentation', 'context', 'output', 'error', 'decision', 'learning']),
  keywords: z.array(z.string()).optional().default([])
});

const SearchMemoryInputSchema = z.object({
  query: z.string().min(1),
  content_type: z.enum(['code', 'documentation', 'context', 'output', 'error', 'decision', 'learning']).optional(),
  limit: z.number().min(1).max(50).optional().default(10)
});

export class MemoryTools {
  private ollamaClient: DevStreamOllamaClient;
  private hybridSearch: HybridSearchEngine;

  constructor(private database: DevStreamDatabase) {
    // Context7 pattern: initialize Ollama client for embedding generation
    this.ollamaClient = getOllamaClient();
    // Context7 pattern: initialize hybrid search engine with RRF
    this.hybridSearch = new HybridSearchEngine(database, this.ollamaClient);
  }

  /**
   * Store information in DevStream semantic memory
   */
  async storeMemory(args: any) {
    try {
      const input = StoreMemoryInputSchema.parse(args);

      // Generate memory ID
      const memoryId = this.generateId();

      // Determine content format based on content type
      const contentFormat = this.getContentFormat(input.content_type, input.content);

      // Calculate importance score based on content type and length
      const importanceScore = this.calculateImportanceScore(input.content_type, input.content);

      // Context7 pattern: Generate embedding automatically for all content with metrics
      console.log(`🧠 Generating embedding for content (${input.content.length} chars)...`);
      const embedding = await MetricsCollector.trackEmbeddingGeneration(
        this.ollamaClient.getDefaultModel(),
        async () => await this.ollamaClient.generateEmbedding(input.content)
      );

      let embeddingJson: string | null = null;
      let embeddingModel: string | null = null;
      let embeddingDimension: number | null = null;

      if (embedding) {
        embeddingJson = JSON.stringify(embedding);
        embeddingModel = this.ollamaClient.getDefaultModel();
        embeddingDimension = embedding.length;
        console.log(`✅ Embedding generated: ${embeddingDimension} dimensions using ${embeddingModel}`);
      } else {
        console.warn(`⚠️ Embedding generation failed - storing without vector search capability`);
      }

      // Store in semantic memory with embedding (Context7 pattern: complete schema with metrics)
      const result = await MetricsCollector.trackDatabaseOperation('memory_storage', async () =>
        await this.database.execute(`
          INSERT INTO semantic_memory (
            id, content, content_type, content_format, keywords,
            embedding, embedding_model, embedding_dimension,
            relevance_score, access_count, context_snapshot
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `, [
          memoryId,
          input.content,
          input.content_type,
          contentFormat,
          JSON.stringify(input.keywords),
          embeddingJson,
          embeddingModel,
          embeddingDimension,
          importanceScore, // Use as relevance_score
          0,
          JSON.stringify({
            stored_via: 'mcp_server',
            timestamp: new Date().toISOString(),
            content_length: input.content.length,
            source: 'mcp_user_input',
            embedding_status: embedding ? 'generated' : 'failed'
          })
        ])
      );

      // Track memory storage in metrics
      memoryStorageCounter.inc({
        content_type: input.content_type,
        has_embedding: embedding ? 'true' : 'false'
      });

      // Context7 pattern: Sync to vec0 if embedding was generated
      if (embedding && this.database.getVectorSearchStatus()) {
        try {
          console.log('📊 Syncing to vec0 vector search index...');
          await MetricsCollector.trackDatabaseOperation('vec0_sync', async () =>
            await this.database.execute(`
              INSERT INTO vec_semantic_memory(embedding, content_type, memory_id, content_preview)
              VALUES (?, ?, ?, ?)
            `, [
              embeddingJson,
              input.content_type,
              memoryId,
              input.content.substring(0, 200)
            ])
          );
          console.log('✅ vec0 sync completed');
        } catch (vecError) {
          console.warn('⚠️ vec0 sync failed:', vecError instanceof Error ? vecError.message : 'Unknown error');
          // Continue - FTS5 will still work via trigger
        }
      }

      return {
        content: [
          {
            type: 'text',
            text: `✅ **Memory Stored Successfully**\n\n` +
                  `📝 **Content Type**: ${input.content_type}\n` +
                  `📊 **Importance Score**: ${importanceScore.toFixed(2)}\n` +
                  `🏷️ **Keywords**: ${input.keywords.length > 0 ? input.keywords.join(', ') : 'None'}\n` +
                  `📍 **Source**: mcp_user_input\n` +
                  `🆔 **Memory ID**: \`${memoryId}\`\n` +
                  `🧠 **Embedding**: ${embedding ? `✅ Generated (${embeddingDimension}D, ${embeddingModel})` : '❌ Failed'}\n\n` +
                  `💾 **Content Preview**: ${input.content.substring(0, 100)}${input.content.length > 100 ? '...' : ''}\n\n` +
                  `The information has been stored in DevStream semantic memory${embedding ? ' with vector search capability' : ' (text-only, vector search unavailable)'} and can be retrieved using search queries.`
          }
        ]
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        content: [
          {
            type: 'text',
            text: `❌ Error storing memory: ${errorMessage}`
          }
        ]
      };
    }
  }

  /**
   * Search DevStream semantic memory using hybrid search (RRF)
   * Context7 pattern: Combines vector similarity + FTS5 keyword search
   */
  async searchMemory(args: any) {
    try {
      const input = SearchMemoryInputSchema.parse(args);

      // Context7 pattern: Use HybridSearchEngine with RRF
      console.log(`🔍 Performing hybrid search for: "${input.query}"`);
      const results = await this.hybridSearch.search(input.query, {
        k: input.limit,
        rrf_k: 60,
        weight_fts: 1.0,
        weight_vec: 1.0
      });

      // Filter by content_type if specified
      const filteredResults = input.content_type
        ? results.filter(r => r.content_type === input.content_type)
        : results;

      if (filteredResults.length === 0) {
        return {
          content: [
            {
              type: 'text',
              text: `🔍 **No Memory Results Found**\n\n` +
                    `Query: "${input.query}"\n` +
                    (input.content_type ? `Content Type: ${input.content_type}\n` : '') +
                    `\nTry using different keywords or check if the information has been stored in DevStream memory.`
            }
          ]
        };
      }

      // Update access count for retrieved memories
      const memoryIds = filteredResults.map(m => `'${m.memory_id}'`).join(',');
      if (memoryIds) {
        await this.database.execute(
          `UPDATE semantic_memory SET access_count = access_count + 1, last_accessed_at = datetime('now') WHERE id IN (${memoryIds})`,
          []
        );
      }

      // Context7 pattern: Show hybrid search diagnostics
      const diagnostics = await this.hybridSearch.getDiagnostics();
      const searchMethod = diagnostics.vector_search.available ? 'Hybrid (Vector + Keyword)' : 'Keyword Only (FTS5)';

      let output = `🔍 **DevStream Hybrid Search Results**\n\n`;
      output += `Query: "${input.query}"\n`;
      output += `Method: ${searchMethod}\n`;
      output += `Found: ${filteredResults.length} results\n\n`;

      filteredResults.forEach((result, index) => {
        const typeEmoji = {
          code: '💻',
          documentation: '📚',
          context: '📋',
          output: '📤',
          error: '❌',
          decision: '🎯',
          learning: '🧠'
        }[result.content_type] || '📄';

        // Context7 pattern: Show RRF combined rank
        const rankScore = (result.combined_rank * 100).toFixed(1);
        const rankText = result.combined_rank > 0.05 ? 'HIGH' : result.combined_rank > 0.02 ? 'MEDIUM' : 'LOW';

        output += `${index + 1}. ${typeEmoji} **${result.content_type.toUpperCase()}** Memory\n`;
        output += `   📊 Relevance: ${rankText} (RRF Score: ${rankScore})\n`;

        // Show search method contribution
        if (result.vec_rank && result.fts_rank) {
          output += `   🔬 Vector Rank: #${result.vec_rank} • Keyword Rank: #${result.fts_rank}\n`;
        } else if (result.vec_rank) {
          output += `   🔬 Vector Rank: #${result.vec_rank} (distance: ${result.vec_distance?.toFixed(4)})\n`;
        } else if (result.fts_rank) {
          output += `   🔬 Keyword Rank: #${result.fts_rank}\n`;
        }

        // Show content preview
        const contentPreview = result.content.length > 200
          ? result.content.substring(0, 200) + '...'
          : result.content;

        output += `   💾 Content: ${contentPreview}\n`;
        output += `   🆔 ID: \`${result.memory_id}\`\n`;
        output += `   📅 Created: ${new Date(result.created_at).toLocaleDateString()}\n\n`;
      });

      output += `💡 **Tip**: Hybrid search combines semantic similarity and keyword matching for better results.`;

      return {
        content: [
          {
            type: 'text',
            text: output
          }
        ]
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        content: [
          {
            type: 'text',
            text: `❌ Error searching memory: ${errorMessage}`
          }
        ]
      };
    }
  }

  /**
   * Determine content format based on content type and content
   */
  private getContentFormat(contentType: string, content: string): string {
    // Try to detect format from content
    if (content.trim().startsWith('{') || content.trim().startsWith('[')) {
      return 'json';
    }

    if (content.includes('```') || content.includes('def ') || content.includes('function ')) {
      return 'code';
    }

    if (content.includes('# ') || content.includes('## ') || content.includes('**')) {
      return 'markdown';
    }

    // Default based on content type
    switch (contentType) {
      case 'code':
        return 'code';
      case 'documentation':
        return 'markdown';
      default:
        return 'text';
    }
  }

  /**
   * Calculate importance score based on content characteristics
   */
  private calculateImportanceScore(contentType: string, content: string): number {
    let score = 0.5; // Base score

    // Content type importance
    const typeScores = {
      error: 0.9,      // Errors are important to remember
      decision: 0.8,   // Decisions have high importance
      learning: 0.8,   // Learning insights are valuable
      code: 0.7,       // Code snippets are useful
      context: 0.6,    // Context is moderately important
      documentation: 0.6,
      output: 0.4      // Output is least critical
    };

    score += (typeScores[contentType as keyof typeof typeScores] || 0.5) * 0.6;

    // Content length factor
    const lengthFactor = Math.min(content.length / 1000, 1) * 0.2;
    score += lengthFactor;

    // Keyword density (simple heuristic)
    const keywordCount = (content.match(/\b(error|bug|fix|optimize|implement|create|update|delete|critical|important|todo|fixme)\b/gi) || []).length;
    const keywordFactor = Math.min(keywordCount / 10, 1) * 0.2;
    score += keywordFactor;

    return Math.min(Math.max(score, 0.1), 1.0); // Clamp between 0.1 and 1.0
  }

  /**
   * Generate unique ID for database records
   */
  private generateId(): string {
    return require('crypto').randomBytes(16).toString('hex');
  }
}