#!/usr/bin/env python3
"""
Standalone test per Memory System Models

Test delle funzionalità core del memory system senza dipendenze
dal resto del package DevStream.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_memory_models():
    """Test memory models functionality."""
    print("🧪 Testing Memory System Models...")

    try:
        # Import models directly
        from devstream.memory.models import MemoryEntry, ContentType, ContentFormat, SearchQuery
        print("✅ Memory models imported successfully")

        # Test ContentType enum
        print(f"✅ ContentType values: {[ct.value for ct in ContentType]}")

        # Test MemoryEntry creation
        memory = MemoryEntry(
            id='test-memory-001',
            content='This is a test memory entry for validation of the DevStream memory system.',
            content_type=ContentType.DOCUMENTATION,
            content_format=ContentFormat.MARKDOWN,
            keywords=['test', 'memory', 'validation', 'devstream'],
            entities=[
                {"text": "DevStream", "label": "PRODUCT"},
                {"text": "memory system", "label": "FEATURE"}
            ],
            complexity_score=6,
            sentiment=0.2
        )

        print(f"✅ Memory entry created:")
        print(f"   ID: {memory.id}")
        print(f"   Type: {memory.content_type.value}")
        print(f"   Format: {memory.content_format.value}")
        print(f"   Keywords: {memory.keywords}")
        print(f"   Entities: {len(memory.entities)} entities")
        print(f"   Complexity: {memory.complexity_score}")
        print(f"   Sentiment: {memory.sentiment}")

        # Test SearchQuery creation
        query = SearchQuery(
            query_text='test search for memory validation',
            max_results=15,
            semantic_weight=1.0,
            keyword_weight=0.8,
            min_relevance=0.3
        )

        print(f"✅ Search query created:")
        print(f"   Query: {query.query_text}")
        print(f"   Max results: {query.max_results}")
        print(f"   Weights: semantic={query.semantic_weight}, keyword={query.keyword_weight}")

        # Test validation
        assert memory.complexity_score >= 1 and memory.complexity_score <= 10
        assert -1.0 <= memory.sentiment <= 1.0
        assert query.max_results > 0
        print("✅ All validations passed")

        return True

    except Exception as e:
        print(f"❌ Memory models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_memory_exceptions():
    """Test memory exceptions."""
    print("\n🧪 Testing Memory Exceptions...")

    try:
        from devstream.memory.exceptions import (
            MemoryError, StorageError, SearchError,
            ProcessingError, ContextError
        )
        print("✅ Exception classes imported successfully")

        # Test exception hierarchy
        assert issubclass(StorageError, MemoryError)
        assert issubclass(SearchError, MemoryError)
        assert issubclass(ProcessingError, MemoryError)
        assert issubclass(ContextError, MemoryError)
        print("✅ Exception hierarchy validated")

        # Test exception creation
        error = MemoryError("Test error", {"detail": "test"})
        assert error.message == "Test error"
        assert error.details == {"detail": "test"}
        print("✅ Exception creation validated")

        return True

    except Exception as e:
        print(f"❌ Memory exceptions test failed: {e}")
        return False

def main():
    """Run all memory system tests."""
    print("🚀 Starting Memory System Validation Tests\n")

    success = True

    # Test models
    success &= test_memory_models()

    # Test exceptions
    success &= test_memory_exceptions()

    print(f"\n{'🎉 All tests passed!' if success else '❌ Some tests failed!'}")
    return success

if __name__ == "__main__":
    sys.exit(0 if main() else 1)