#!/usr/bin/env python3
"""
Mock OllamaEmbeddingClient for testing purposes.
"""

class MockOllamaEmbeddingClient:
    """Mock OllamaEmbeddingClient that returns predictable embeddings for testing."""

    def __init__(self):
        self.call_count = 0
        self.last_content = None

    def generate_embedding(self, content: str):
        """Generate mock embedding based on content hash for consistency."""
        self.call_count += 1
        self.last_content = content

        # Generate deterministic embedding based on content
        import hashlib
        hash_obj = hashlib.md5(content.encode())
        hash_hex = hash_obj.hexdigest()

        # Convert hash to float values between -1 and 1
        embedding = []
        for i in range(0, len(hash_hex), 2):
            hex_pair = hash_hex[i:i+2]
            val = int(hex_pair, 16) / 255.0 * 2 - 1  # Scale to [-1, 1]
            embedding.append(val)

        # Ensure we have exactly 768 dimensions (standard for many embedding models)
        while len(embedding) < 768:
            embedding.append(0.0)
        return embedding[:768]

# For tests that want to control the behavior
class ControlMockOllamaEmbeddingClient:
    """Controllable mock for specific test scenarios."""

    def __init__(self, return_value=None, side_effect=None):
        self.return_value = return_value
        self.side_effect = side_effect
        self.call_count = 0
        self.last_content = None

    def generate_embedding(self, content: str):
        self.call_count += 1
        self.last_content = content

        if self.side_effect:
            raise self.side_effect

        if self.return_value:
            return self.return_value

        # Default behavior
        return [0.1] * 768

# Install the mock as the default OllamaEmbeddingClient for testing
OllamaEmbeddingClient = MockOllamaEmbeddingClient