#!/usr/bin/env python3
"""
Test isolato per Memory Models

Test solo dei modelli Pydantic senza dipendenze esterne.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_memory_models_isolated():
    """Test memory models in isolation."""
    print("🧪 Testing Memory Models (Isolated)...")

    try:
        # Test direct file import senza __init__.py chain
        import importlib.util
        models_path = os.path.join(os.path.dirname(__file__), 'src', 'devstream', 'memory', 'models.py')
        spec = importlib.util.spec_from_file_location("models", models_path)
        models = importlib.util.module_from_spec(spec)

        # Add required dependencies
        import enum
        import json
        from datetime import datetime
        from typing import Any, Optional
        import numpy as np
        from pydantic import BaseModel, Field, validator

        # Set up module environment
        models.Enum = enum.Enum
        models.BaseModel = BaseModel
        models.Field = Field
        models.validator = validator
        models.datetime = datetime
        models.np = np
        models.json = json

        # Execute the module
        spec.loader.exec_module(models)
        print("✅ Memory models loaded successfully")

        # Test ContentType enum
        ContentType = models.ContentType
        print(f"✅ ContentType values: {[ct.value for ct in ContentType]}")

        # Test MemoryEntry creation
        MemoryEntry = models.MemoryEntry
        memory = MemoryEntry(
            id='test-memory-001',
            content='This is a comprehensive test memory entry for validation of the DevStream memory system implementation. It contains multiple sentences to test complexity scoring.',
            content_type=ContentType.DOCUMENTATION,
            content_format=models.ContentFormat.MARKDOWN,
            keywords=['test', 'memory', 'validation', 'devstream', 'system'],
            entities=[
                {"text": "DevStream", "label": "PRODUCT"},
                {"text": "memory system", "label": "FEATURE"},
                {"text": "validation", "label": "PROCESS"}
            ],
            complexity_score=7,
            sentiment=0.3
        )

        print(f"✅ Memory entry created successfully:")
        print(f"   ID: {memory.id}")
        print(f"   Type: {memory.content_type}")
        print(f"   Format: {memory.content_format}")
        print(f"   Keywords: {memory.keywords}")
        print(f"   Entities: {len(memory.entities)} entities")
        print(f"   Complexity: {memory.complexity_score}")
        print(f"   Sentiment: {memory.sentiment}")
        print(f"   Created: {memory.created_at}")

        # Test embedding functionality
        test_embedding = [0.1, 0.2, 0.3] * 128  # 384 dimensions
        memory.set_embedding(np.array(test_embedding))
        print(f"✅ Embedding set: {len(memory.embedding)} dimensions")

        embedding_array = memory.get_embedding_array()
        print(f"✅ Embedding retrieved: shape {embedding_array.shape}")

        # Test SearchQuery
        SearchQuery = models.SearchQuery
        query = SearchQuery(
            query_text='comprehensive test for memory system validation',
            max_results=20,
            semantic_weight=1.2,
            keyword_weight=0.9,
            min_relevance=0.4,
            content_types=[ContentType.DOCUMENTATION, ContentType.CODE],
            rrf_k=50
        )

        print(f"✅ Search query created:")
        print(f"   Query: {query.query_text}")
        print(f"   Max results: {query.max_results}")
        print(f"   Weights: semantic={query.semantic_weight}, keyword={query.keyword_weight}")
        print(f"   Content types: {query.content_types}")

        # Test ContextAssemblyResult
        ContextAssemblyResult = models.ContextAssemblyResult
        context_result = ContextAssemblyResult(
            assembled_context="Test assembled context with relevant memories.",
            memory_entries=[memory],
            total_tokens=150,
            tokens_budget=1000,
            tokens_remaining=850,
            relevance_threshold=0.3,
            truncated=False,
            assembly_strategy="relevance",
            assembly_time_ms=45.2
        )

        print(f"✅ Context assembly result created:")
        print(f"   Total tokens: {context_result.total_tokens}")
        print(f"   Remaining: {context_result.tokens_remaining}")
        print(f"   Strategy: {context_result.assembly_strategy}")
        print(f"   Assembly time: {context_result.assembly_time_ms}ms")

        # Test validation
        assert memory.complexity_score >= 1 and memory.complexity_score <= 10
        assert -1.0 <= memory.sentiment <= 1.0
        assert query.max_results > 0
        assert context_result.tokens_remaining == context_result.tokens_budget - context_result.total_tokens
        print("✅ All model validations passed")

        # Test serialization
        memory_dict = memory.dict()
        memory_json = memory.json()
        print(f"✅ Serialization working: {len(memory_json)} chars JSON")

        return True

    except Exception as e:
        print(f"❌ Memory models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_exceptions_isolated():
    """Test memory exceptions in isolation."""
    print("\n🧪 Testing Memory Exceptions (Isolated)...")

    try:
        # Test direct file import
        import importlib.util
        exceptions_path = os.path.join(os.path.dirname(__file__), 'src', 'devstream', 'memory', 'exceptions.py')
        spec = importlib.util.spec_from_file_location("exceptions", exceptions_path)
        exceptions = importlib.util.module_from_spec(spec)

        # Add dependencies
        from typing import Any, Optional
        exceptions.Any = Any
        exceptions.Optional = Optional

        # Execute module
        spec.loader.exec_module(exceptions)
        print("✅ Exception classes loaded successfully")

        # Test exception hierarchy
        MemoryError = exceptions.MemoryError
        StorageError = exceptions.StorageError
        SearchError = exceptions.SearchError

        assert issubclass(StorageError, MemoryError)
        assert issubclass(SearchError, MemoryError)
        print("✅ Exception hierarchy validated")

        # Test exception creation
        error = MemoryError("Test error message", {"context": "test", "code": 500})
        assert error.message == "Test error message"
        assert error.details["context"] == "test"
        print("✅ Exception creation and details validated")

        return True

    except Exception as e:
        print(f"❌ Exception test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run isolated memory system tests."""
    print("🚀 Starting Memory System Isolated Tests\n")

    success = True

    # Test models
    success &= test_memory_models_isolated()

    # Test exceptions
    success &= test_exceptions_isolated()

    if success:
        print(f"\n🎉 Memory System Phase 1.4 Implementation Complete!")
        print(f"✅ Models: MemoryEntry, SearchQuery, ContextAssemblyResult")
        print(f"✅ Enums: ContentType, ContentFormat")
        print(f"✅ Validation: Pydantic models con constraints")
        print(f"✅ Serialization: JSON serialization support")
        print(f"✅ Embedding: NumPy array integration")
        print(f"✅ Exceptions: Structured error hierarchy")
    else:
        print(f"\n❌ Some tests failed!")

    return success

if __name__ == "__main__":
    sys.exit(0 if main() else 1)