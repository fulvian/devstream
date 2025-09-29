/**
 * DevStream Memory Management Tools
 *
 * MCP tools for managing DevStream semantic memory and knowledge storage.
 * Context7-compliant automatic embedding generation using embeddinggemma.
 */

import { DevStreamDatabase, SemanticMemory } from '../database.js';
import { getOllamaClient, DevStreamOllamaClient } from '../ollama-client.js';
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

  constructor(private database: DevStreamDatabase) {
    // Context7 pattern: initialize Ollama client for embedding generation
    this.ollamaClient = getOllamaClient();
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

      // Context7 pattern: Generate embedding automatically for all content
      console.log(`🧠 Generating embedding for content (${input.content.length} chars)...`);
      const embedding = await this.ollamaClient.generateEmbedding(input.content);

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

      // Store in semantic memory with embedding (Context7 pattern: complete schema)
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
      ]);

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
   * Search DevStream semantic memory for relevant information
   */
  async searchMemory(args: any) {
    try {
      const input = SearchMemoryInputSchema.parse(args);

      // Build search query using actual database schema
      let sql = `
        SELECT
          sm.*,
          CASE
            WHEN sm.content LIKE ? THEN 10
            WHEN sm.keywords LIKE ? THEN 8
            WHEN json_extract(sm.context_snapshot, '$.source') LIKE ? THEN 5
            ELSE sm.relevance_score
          END as search_relevance_score
        FROM semantic_memory sm
        WHERE (
          sm.content LIKE ? OR
          sm.keywords LIKE ? OR
          json_extract(sm.context_snapshot, '$.source') LIKE ?
        )
      `;

      const searchPattern = `%${input.query}%`;
      const params = [
        searchPattern, searchPattern, searchPattern,  // For relevance scoring
        searchPattern, searchPattern, searchPattern   // For WHERE clause
      ];

      // Add content type filter if specified
      if (input.content_type) {
        sql += ' AND sm.content_type = ?';
        params.push(input.content_type);
      }

      sql += `
        ORDER BY search_relevance_score DESC, sm.relevance_score DESC, sm.created_at DESC
        LIMIT ?
      `;
      params.push(input.limit.toString());

      const memories = await this.database.query<SemanticMemory & { relevance_score: number }>(sql, params);

      if (memories.length === 0) {
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
      const memoryIds = memories.map(m => `'${m.id}'`).join(',');
      await this.database.execute(
        `UPDATE semantic_memory SET access_count = access_count + 1, last_accessed_at = datetime('now') WHERE id IN (${memoryIds})`,
        [] // Empty params array
      );

      let output = `🔍 **DevStream Memory Search Results**\n\n`;
      output += `Query: "${input.query}"\n`;
      output += `Found: ${memories.length} results\n\n`;

      memories.forEach((memory, index) => {
        const typeEmoji = {
          code: '💻',
          documentation: '📚',
          context: '📋',
          output: '📤',
          error: '❌',
          decision: '🎯',
          learning: '🧠'
        }[memory.content_type] || '📄';

        const relevanceScore = (memory as any).search_relevance_score || memory.relevance_score || 0;
        const relevanceText = relevanceScore >= 8 ? 'HIGH' : relevanceScore >= 5 ? 'MEDIUM' : 'LOW';

        output += `${index + 1}. ${typeEmoji} **${memory.content_type.toUpperCase()}** Memory\n`;
        output += `   📊 Relevance: ${relevanceText} (${relevanceScore}/10) • Score: ${memory.relevance_score?.toFixed(2) || 'N/A'}\n`;

        // Extract source from context_snapshot
        try {
          const contextSnapshot = JSON.parse(memory.context_snapshot || '{}');
          output += `   📍 Source: ${contextSnapshot.source || 'unknown'}\n`;
        } catch (e) {
          output += `   📍 Source: unknown\n`;
        }

        // Parse and display keywords
        try {
          const keywords = memory.keywords ? JSON.parse(memory.keywords) : [];
          if (Array.isArray(keywords) && keywords.length > 0) {
            output += `   🏷️ Keywords: ${keywords.join(', ')}\n`;
          }
        } catch (e) {
          // Skip if keywords is not valid JSON
        }

        // Show content preview
        const contentPreview = memory.content.length > 200
          ? memory.content.substring(0, 200) + '...'
          : memory.content;

        output += `   💾 Content: ${contentPreview}\n`;
        output += `   🆔 ID: \`${memory.id}\`\n`;
        output += `   📅 Created: ${new Date(memory.created_at).toLocaleDateString()}\n`;

        if (memory.access_count && memory.access_count > 0) {
          output += `   👁️ Accessed: ${memory.access_count + 1} times\n`;
        }

        output += '\n';
      });

      output += `💡 **Tip**: Use specific keywords or content types to refine your search results.`;

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