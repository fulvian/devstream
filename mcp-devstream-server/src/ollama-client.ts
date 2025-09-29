/**
 * Ollama Client for DevStream MCP Server
 * Context7-validated integration per /ollama/ollama-js patterns
 *
 * Provides embedding generation using embeddinggemma model.
 */

import { Ollama } from 'ollama';

/**
 * Configuration interface for Ollama client
 */
interface OllamaConfig {
  host?: string;
  timeout?: number;
  defaultModel?: string;
}

/**
 * Embedding response interface
 */
interface EmbeddingResponse {
  embeddings: number[][];
  total_duration?: number;
  load_duration?: number;
  prompt_eval_count?: number;
}

/**
 * DevStream Ollama client wrapper
 * Context7 pattern: single responsibility, error handling, async operations
 */
export class DevStreamOllamaClient {
  private ollama: Ollama;
  private defaultModel: string;
  private isConnected: boolean = false;

  constructor(config: OllamaConfig = {}) {
    // Context7 pattern: use defaults, allow override
    const host = config.host || process.env.OLLAMA_HOST || 'http://127.0.0.1:11434';
    this.defaultModel = config.defaultModel || 'embeddinggemma:300m';

    this.ollama = new Ollama({
      host,
      // Context7 pattern: reasonable timeout for embedding generation
      fetch: config.timeout ? this.createTimeoutFetch(config.timeout) : undefined
    });
  }

  /**
   * Create fetch function with timeout
   * Context7 pattern: non-blocking operations with reasonable limits
   */
  private createTimeoutFetch(timeoutMs: number) {
    return (input: string | URL | Request, init?: RequestInit) => {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), timeoutMs);

      return fetch(input, {
        ...init,
        signal: controller.signal
      }).finally(() => clearTimeout(timeout));
    };
  }

  /**
   * Test connection to Ollama server
   * Context7 pattern: health check before operations
   */
  async testConnection(): Promise<boolean> {
    try {
      await this.ollama.ps();
      this.isConnected = true;
      console.log('✅ Ollama connection established');
      return true;
    } catch (error) {
      this.isConnected = false;
      console.warn('⚠️ Ollama connection failed:', error instanceof Error ? error.message : 'Unknown error');
      return false;
    }
  }

  /**
   * Generate embedding for text content
   * Context7 pattern: single text input, deterministic output
   *
   * @param text - Text content to embed
   * @param model - Optional model override (default: embeddinggemma)
   * @returns Embedding vector or null if failed
   */
  async generateEmbedding(text: string, model?: string): Promise<number[] | null> {
    if (!text.trim()) {
      console.warn('⚠️ Empty text provided for embedding');
      return null;
    }

    const modelToUse = model || this.defaultModel;

    try {
      // Context7 pattern: use official ollama-js embed method
      const response = await this.ollama.embed({
        model: modelToUse,
        input: text,
        // Context7 pattern: truncate to model's max context length
        truncate: true,
        // Context7 pattern: don't keep model loaded indefinitely
        keep_alive: '5m'
      }) as EmbeddingResponse;

      // Context7 pattern: validate response structure
      if (!response.embeddings || !Array.isArray(response.embeddings) || response.embeddings.length === 0) {
        console.error('❌ Invalid embedding response structure');
        return null;
      }

      // Context7 pattern: return first embedding (single input)
      const embedding = response.embeddings[0];

      // Context7 pattern: validate embedding vector
      if (!Array.isArray(embedding) || embedding.length === 0) {
        console.error('❌ Invalid embedding vector');
        return null;
      }

      console.log(`✅ Generated embedding: ${embedding.length} dimensions, model: ${modelToUse}`);
      return embedding;

    } catch (error) {
      console.error('❌ Embedding generation failed:', error instanceof Error ? error.message : 'Unknown error');

      // Context7 pattern: graceful degradation
      if (error instanceof Error) {
        if (error.message.includes('model not found')) {
          console.error(`❌ Model '${modelToUse}' not found. Please pull the model first:`, `ollama pull ${modelToUse}`);
        } else if (error.message.includes('connection')) {
          console.error('❌ Connection to Ollama server failed. Is Ollama running?');
          this.isConnected = false;
        }
      }

      return null;
    }
  }

  /**
   * Generate embeddings for multiple texts
   * Context7 pattern: batch processing for efficiency
   *
   * @param texts - Array of text contents to embed
   * @param model - Optional model override
   * @returns Array of embedding vectors (null for failed items)
   */
  async generateEmbeddings(texts: string[], model?: string): Promise<(number[] | null)[]> {
    if (!Array.isArray(texts) || texts.length === 0) {
      console.warn('⚠️ Empty or invalid texts array provided for embeddings');
      return [];
    }

    const modelToUse = model || this.defaultModel;

    try {
      // Context7 pattern: batch API call for efficiency
      const response = await this.ollama.embed({
        model: modelToUse,
        input: texts,
        truncate: true,
        keep_alive: '5m'
      }) as EmbeddingResponse;

      // Context7 pattern: validate batch response
      if (!response.embeddings || !Array.isArray(response.embeddings)) {
        console.error('❌ Invalid batch embedding response structure');
        return texts.map(() => null);
      }

      console.log(`✅ Generated ${response.embeddings.length} embeddings, model: ${modelToUse}`);
      return response.embeddings;

    } catch (error) {
      console.error('❌ Batch embedding generation failed:', error instanceof Error ? error.message : 'Unknown error');

      // Context7 pattern: fallback to individual processing
      console.log('🔄 Falling back to individual embedding generation...');
      const results: (number[] | null)[] = [];

      for (const text of texts) {
        const embedding = await this.generateEmbedding(text, model);
        results.push(embedding);

        // Context7 pattern: small delay to avoid overwhelming the server
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      return results;
    }
  }

  /**
   * Check if a model is available
   * Context7 pattern: proactive model availability check
   */
  async isModelAvailable(model: string = this.defaultModel): Promise<boolean> {
    try {
      const models = await this.ollama.list();
      return models.models?.some(m => m.name.includes(model)) || false;
    } catch (error) {
      console.error('❌ Failed to check model availability:', error instanceof Error ? error.message : 'Unknown error');
      return false;
    }
  }

  /**
   * Get connection status
   */
  getConnectionStatus(): boolean {
    return this.isConnected;
  }

  /**
   * Get default model name
   */
  getDefaultModel(): string {
    return this.defaultModel;
  }
}

/**
 * Singleton instance for MCP server usage
 * Context7 pattern: single instance, lazy initialization
 */
let ollamaClientInstance: DevStreamOllamaClient | null = null;

/**
 * Get or create Ollama client instance
 * Context7 pattern: factory function with configuration
 */
export function getOllamaClient(config?: OllamaConfig): DevStreamOllamaClient {
  if (!ollamaClientInstance) {
    ollamaClientInstance = new DevStreamOllamaClient(config);
  }
  return ollamaClientInstance;
}

/**
 * Initialize Ollama client with connection test
 * Context7 pattern: explicit initialization with health check
 */
export async function initializeOllamaClient(config?: OllamaConfig): Promise<DevStreamOllamaClient> {
  const client = getOllamaClient(config);
  await client.testConnection();

  // Context7 pattern: proactive model availability check
  const isModelAvailable = await client.isModelAvailable();
  if (!isModelAvailable) {
    console.warn(`⚠️ Model '${client.getDefaultModel()}' not available. Please pull it first: ollama pull ${client.getDefaultModel()}`);
  }

  return client;
}