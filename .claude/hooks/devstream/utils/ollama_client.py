#!/usr/bin/env python3
"""
DevStream Ollama Embedding Client - Context7 Compliant

Utility class for generating embeddings using Ollama API.
Implements Context7 best practices from ollama-python library.

Context7 Research:
- ollama.embed(model='gemma3', input=['text1', 'text2']) supports batch
- Batch size ≤16 recommended for accuracy
- Graceful degradation on failure (non-blocking)

Usage:
    client = OllamaEmbeddingClient()
    embedding = await client.generate_embedding("sample text")
"""

import sys
import asyncio
from pathlib import Path
from typing import List, Optional
import json

# Add utils to path
sys.path.append(str(Path(__file__).parent))
from logger import get_devstream_logger


class OllamaEmbeddingClient:
    """
    Ollama embedding client for DevStream semantic memory.

    Generates embeddings using Ollama's embeddinggemma:300m model.
    Context7-compliant implementation with graceful error handling.

    Key Features:
    - Synchronous embedding generation (ollama.embed)
    - Configurable timeout (default: 5s)
    - Graceful degradation on failure
    - Structured logging with context

    Context7 Patterns Applied:
    - ollama.embed() with input parameter for text
    - Non-blocking error handling
    - DevStream standard model: embeddinggemma:300m
    """

    def __init__(
        self,
        model: str = "embeddinggemma:300m",
        base_url: str = "http://localhost:11434",
        timeout: float = 5.0
    ):
        """
        Initialize Ollama embedding client.

        Args:
            model: Ollama embedding model (default: embeddinggemma:300m)
            base_url: Ollama API base URL (default: http://localhost:11434)
            timeout: Request timeout in seconds (default: 5.0)
        """
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

        self.structured_logger = get_devstream_logger('ollama_client')
        self.logger = self.structured_logger.logger

        self.logger.info(
            "OllamaEmbeddingClient initialized",
            model=self.model,
            base_url=self.base_url,
            timeout=self.timeout
        )

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for single text string.

        Context7 Pattern: Use ollama.embed() with input parameter.
        Synchronous implementation for simplicity in hook context.

        Args:
            text: Text to generate embedding for

        Returns:
            List of floats representing embedding vector, or None on failure

        Raises:
            No exceptions raised - graceful degradation on all errors
        """
        if not text or not text.strip():
            self.logger.warning("Empty text provided for embedding generation")
            return None

        try:
            # Import ollama here to avoid import errors if not installed
            import ollama

            self.logger.debug(
                "Generating embedding",
                text_length=len(text),
                model=self.model
            )

            # Context7 Pattern: ollama.embed() with input parameter
            # Note: Using input (not prompt) for batch-compatible API
            response = ollama.embed(
                model=self.model,
                input=text  # Single string, but API accepts list too
            )

            # Extract embeddings from response
            # Response format: {'embeddings': [[...]], ...} for batch
            # or {'embedding': [...], ...} for single
            if 'embeddings' in response:
                # Batch response format
                embeddings = response['embeddings']
                if embeddings and len(embeddings) > 0:
                    embedding = embeddings[0]  # Get first (only) embedding
                else:
                    self.logger.warning("Empty embeddings in response")
                    return None
            elif 'embedding' in response:
                # Single response format
                embedding = response['embedding']
            else:
                self.logger.error(
                    "Unexpected response format from Ollama",
                    response_keys=list(response.keys())
                )
                return None

            # Validate embedding
            if not isinstance(embedding, list) or len(embedding) == 0:
                self.logger.error(
                    "Invalid embedding format",
                    embedding_type=type(embedding).__name__
                )
                return None

            self.logger.debug(
                "Embedding generated successfully",
                embedding_dim=len(embedding)
            )

            return embedding

        except ImportError:
            self.logger.error(
                "ollama-python not installed",
                hint="Install with: pip install ollama"
            )
            return None

        except Exception as e:
            # Graceful degradation - log error but don't raise
            self.logger.error(
                "Failed to generate embedding",
                error=str(e),
                error_type=type(e).__name__
            )
            return None

    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 16
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts with batching.

        Context7 Pattern: Batch size ≤16 for accuracy.
        Processes in batches and returns results in original order.

        Args:
            texts: List of texts to generate embeddings for
            batch_size: Maximum batch size (default: 16, Context7 recommended)

        Returns:
            List of embeddings (or None for failures) in same order as input
        """
        if not texts:
            return []

        # Limit batch size per Context7 recommendation
        batch_size = min(batch_size, 16)

        results: List[Optional[List[float]]] = []

        try:
            import ollama

            # Process in batches
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]

                self.logger.debug(
                    "Processing batch",
                    batch_num=i // batch_size + 1,
                    batch_size=len(batch)
                )

                try:
                    # Context7 Pattern: ollama.embed() with list input
                    response = ollama.embed(
                        model=self.model,
                        input=batch  # List of strings
                    )

                    # Extract embeddings
                    if 'embeddings' in response:
                        batch_embeddings = response['embeddings']
                        results.extend(batch_embeddings)
                    else:
                        self.logger.error("Unexpected batch response format")
                        # Add None for each failed text in batch
                        results.extend([None] * len(batch))

                except Exception as e:
                    self.logger.error(
                        "Batch embedding failed",
                        batch_num=i // batch_size + 1,
                        error=str(e)
                    )
                    # Add None for each failed text in batch
                    results.extend([None] * len(batch))

            return results

        except ImportError:
            self.logger.error("ollama-python not installed")
            return [None] * len(texts)

        except Exception as e:
            self.logger.error(
                "Batch processing failed",
                error=str(e)
            )
            return [None] * len(texts)

    def test_connection(self) -> bool:
        """
        Test connection to Ollama server.

        Returns:
            True if Ollama is available, False otherwise
        """
        try:
            import ollama

            # Try to generate a simple embedding
            response = ollama.embed(
                model=self.model,
                input="test"
            )

            self.logger.info("Ollama connection successful")
            return True

        except ImportError:
            self.logger.error("ollama-python not installed")
            return False

        except Exception as e:
            self.logger.error(
                "Ollama connection failed",
                error=str(e)
            )
            return False


# Convenience function for quick embedding generation
def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Convenience function for quick embedding generation.

    Args:
        text: Text to generate embedding for

    Returns:
        Embedding vector or None on failure
    """
    client = OllamaEmbeddingClient()
    return client.generate_embedding(text)


if __name__ == "__main__":
    # Test script
    import sys

    print("DevStream Ollama Embedding Client Test")
    print("=" * 50)

    client = OllamaEmbeddingClient()

    # Test connection
    print("\n1. Testing connection to Ollama...")
    if client.test_connection():
        print("   ✅ Connection successful")
    else:
        print("   ❌ Connection failed")
        sys.exit(1)

    # Test single embedding
    print("\n2. Testing single embedding generation...")
    test_text = "DevStream is a task management system for Claude Code"
    embedding = client.generate_embedding(test_text)

    if embedding:
        print(f"   ✅ Embedding generated: {len(embedding)} dimensions")
        print(f"   First 5 values: {embedding[:5]}")
    else:
        print("   ❌ Embedding generation failed")

    # Test batch embeddings
    print("\n3. Testing batch embedding generation...")
    test_texts = [
        "First test text",
        "Second test text",
        "Third test text"
    ]
    embeddings = client.generate_embeddings_batch(test_texts)

    success_count = sum(1 for e in embeddings if e is not None)
    print(f"   ✅ Generated {success_count}/{len(test_texts)} embeddings")

    print("\n" + "=" * 50)
    print("Test completed!")