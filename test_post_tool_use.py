#!/usr/bin/env .devstream/bin/python
"""
Test script to verify PostToolUse hook functionality.
This will be processed by the PostToolUse hook to generate embeddings.
"""

def test_embedding_generation():
    """
    Test function for embedding generation via PostToolUse hook.

    This function demonstrates DevStream's automatic embedding generation
    when code files are modified. The PostToolUse hook should:
    1. Detect this file modification
    2. Extract the content
    3. Generate embedding using Ollama embeddinggemma:300m
    4. Store in semantic_memory with proper metadata
    5. Sync to vec_semantic_memory via triggers
    """
    return "PostToolUse hook embedding test successful!"

if __name__ == "__main__":
    result = test_embedding_generation()
    print(f"Result: {result}")
    print("If this file was processed by PostToolUse hook, check semantic_memory for embedding.")