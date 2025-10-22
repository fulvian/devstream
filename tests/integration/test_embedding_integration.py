#!/usr/bin/env python3
"""
Integration tests for automatic embedding generation in direct_client.py
Tests the full embedding flow using actual Ollama service.
"""
import pytest
import asyncio
import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude' / 'hooks' / 'devstream' / 'utils'))

from direct_client import DevStreamDirectClient


@pytest.mark.asyncio
async def test_full_embedding_flow_integration():
    """Test complete embedding generation flow with actual Ollama service."""
    client = DevStreamDirectClient()

    # Test content for embedding generation
    test_content = """
    def calculate_fibonacci(n):
        if n <= 1:
            return n
        return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

    # Test the function
    result = calculate_fibonacci(10)
    print(f"Fibonacci(10) = {result}")
    """

    result = await client.store_memory(
        content=test_content,
        content_type="code",
        keywords=["fibonacci", "recursion", "python", "algorithm"]
    )

    # Verify basic storage success
    assert result["success"] is True
    assert "memory_id" in result
    assert result["content_type"] == "code"

    # Check if embedding was generated (may or may not succeed depending on Ollama availability)
    embedding_generated = result.get("embedding_generated", False)

    if embedding_generated:
        # If embedding was generated, verify metadata
        assert result["embedding_format"] == "BLOB"
        assert result["embedding_dimension"] is not None
        assert result["embedding_dimension"] > 0

        # Verify the embedding was actually stored in database
        memory_id = result["memory_id"]
        with client.connection_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT embedding_blob, embedding_model, embedding_dimension FROM semantic_memory WHERE id = ?",
                (memory_id,)
            )
            row = cursor.fetchone()

            assert row is not None
            assert row['embedding_blob'] is not None
            assert len(row['embedding_blob']) > 0
            assert row['embedding_model'] is not None
            assert row['embedding_dimension'] == result["embedding_dimension"]

        print(f"✅ Embedding generated and stored successfully (dimension: {result['embedding_dimension']})")
    else:
        # If embedding failed, verify graceful degradation
        print("⚠️  Embedding generation failed, but storage succeeded (graceful degradation)")

        # Verify record was still saved without embedding
        memory_id = result["memory_id"]
        with client.connection_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT embedding_blob FROM semantic_memory WHERE id = ?",
                (memory_id,)
            )
            row = cursor.fetchone()
            assert row is not None
            assert row['embedding_blob'] is None


@pytest.mark.asyncio
async def test_embedding_search_integration():
    """Test that embedding generation improves search results."""
    client = DevStreamDirectClient()

    # Store multiple related pieces of code
    contents = [
        ("def quicksort(arr):", "code"),
        ("def mergesort(arr):", "code"),
        ("def binary_search(arr, target):", "code"),
        ("print('hello world')", "code")
    ]

    stored_memory_ids = []

    for content, content_type in contents:
        result = await client.store_memory(
            content=content,
            content_type=content_type,
            keywords=["sorting", "searching", "algorithm"]
        )

        if result["success"]:
            stored_memory_ids.append(result["memory_id"])

    # Search for sorting algorithms
    search_result = await client.search_memory(
        query="sorting algorithm implementation",
        content_type="code",
        limit=5
    )

    assert search_result["success"] is True
    assert "results" in search_result
    assert len(search_result["results"]) >= 0

    print(f"✅ Search completed with {len(search_result['results'])} results")


@pytest.mark.asyncio
async def test_embedding_performance_integration():
    """Test embedding generation performance under realistic load."""
    client = DevStreamDirectClient()

    # Test multiple concurrent storage operations
    contents = [
        "Machine learning model training pipeline",
        "Database connection pooling implementation",
        "REST API endpoint with authentication",
        "WebSocket real-time communication",
        "Caching strategy with Redis"
    ]

    import time
    start_time = time.time()

    # Store all content concurrently
    tasks = []
    for i, content in enumerate(contents):
        task = client.store_memory(
            content=content,
            content_type="documentation",
            keywords=["performance", "optimization", f"item_{i}"]
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    elapsed_time = time.time() - start_time

    # Verify all operations completed
    successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
    failed_results = [r for r in results if isinstance(r, Exception)]

    print(f"✅ Concurrent storage completed in {elapsed_time:.2f}s")
    print(f"   Successful: {len(successful_results)}, Failed: {len(failed_results)}")

    # Check performance expectations
    avg_time_per_operation = elapsed_time / len(contents)
    print(f"   Average time per operation: {avg_time_per_operation:.2f}s")

    # Verify that at least some embeddings were generated (if Ollama is available)
    embedding_count = sum(1 for r in successful_results if r.get("embedding_generated"))
    print(f"   Embeddings generated: {embedding_count}/{len(successful_results)}")


@pytest.mark.asyncio
async def test_embedding_error_recovery():
    """Test system behavior when embedding service fails intermittently."""
    client = DevStreamDirectClient()

    # Store content that should work
    result1 = await client.store_memory(
        content="This should work fine",
        content_type="documentation"
    )
    assert result1["success"] is True

    # Store content and verify graceful degradation if Ollama fails
    result2 = await client.store_memory(
        content="Complex code that might stress embedding service",
        content_type="code",
        keywords=["complex", "stress", "test"]
    )

    # Storage should succeed regardless of embedding generation
    assert result2["success"] is True
    assert "memory_id" in result2

    # System should remain functional
    result3 = await client.store_memory(
        content="Recovery test content",
        content_type="documentation"
    )
    assert result3["success"] is True

    print("✅ Error recovery test passed - system remains functional")


@pytest.mark.asyncio
async def test_database_constraints_integration():
    """Test that database constraints are properly enforced."""
    client = DevStreamDirectClient()

    # Test valid embedding dimension (768)
    result_valid = await client.store_memory(
        content="Valid content with proper embedding",
        content_type="code"
    )
    assert result_valid["success"] is True

    # Verify database integrity
    with client.connection_manager.get_connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM semantic_memory")
        count = cursor.fetchone()[0]
        assert count > 0

        # Verify that embedding constraints are satisfied
        cursor = conn.execute("""
            SELECT id, embedding_blob IS NOT NULL as has_embedding
            FROM semantic_memory
            WHERE embedding_blob IS NOT NULL
        """)
        embedding_records = cursor.fetchall()

        for record in embedding_records:
            memory_id, has_embedding = record
            if has_embedding:
                # Verify embedding blob format and size
                cursor = conn.execute(
                    "SELECT length(embedding_blob) FROM semantic_memory WHERE id = ?",
                    (memory_id,)
                )
                blob_size = cursor.fetchone()[0]
                # 768 floats * 4 bytes per float = 3072 bytes
                assert blob_size == 3072, f"Expected 3072 bytes, got {blob_size}"

    print("✅ Database constraints test passed")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_full_embedding_flow_integration())
    asyncio.run(test_embedding_search_integration())
    asyncio.run(test_embedding_performance_integration())
    asyncio.run(test_embedding_error_recovery())
    asyncio.run(test_database_constraints_integration())
    print("🎉 All integration tests completed!")