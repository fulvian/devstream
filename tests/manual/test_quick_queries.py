#!/usr/bin/env python3
"""
Quick Natural Language Query Test

Simple script for rapid testing of DevStream memory search.
Use this for quick validation during development.

Usage:
    python test_quick_queries.py "your natural language query here"
    python test_quick_queries.py  # Interactive mode
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from devstream.database.connection import ConnectionPool
from devstream.memory.storage import MemoryStorage
from devstream.memory.search import HybridSearchEngine
from devstream.memory.models import SearchQuery
from devstream.memory.processing import TextProcessor
from devstream.ollama.client import OllamaClient


async def quick_query(query: str, top_k: int = 3):
    """Execute a single natural language query."""
    print(f"\n🔍 Query: {query}\n")
    print("="*80)

    # Initialize
    pool = ConnectionPool("data/devstream.db")
    await pool.initialize()

    storage = MemoryStorage(pool)
    ollama_client = OllamaClient(base_url="http://localhost:11434")
    processor = TextProcessor(ollama_client)
    search_engine = HybridSearchEngine(storage, processor)

    # Search
    search_query = SearchQuery(
        query_text=query,
        max_results=top_k,
        semantic_weight=0.6,
        keyword_weight=0.4
    )
    results = await search_engine.search(search_query)

    # Display results
    if not results:
        print("❌ No results found")
    else:
        print(f"✅ Found {len(results)} results:\n")

        for i, result in enumerate(results, 1):
            memory = result.memory_entry
            score = result.combined_score

            print(f"#{i} [Score: {score:.3f}] - {memory.content_type.value}")
            print(f"   {memory.content[:200]}...")
            if memory.keywords:
                print(f"   Keywords: {', '.join(memory.keywords[:5])}")
            print()

    print("="*80)

    await pool.close()


async def interactive_mode():
    """Simple interactive query mode."""
    print("\n🎮 Quick Query Tester - Interactive Mode")
    print("Enter queries or 'exit' to quit\n")

    pool = ConnectionPool("data/devstream.db")
    await pool.initialize()
    storage = MemoryStorage(pool)
    ollama_client = OllamaClient(base_url="http://localhost:11434")
    processor = TextProcessor(ollama_client)
    search_engine = HybridSearchEngine(storage, processor)

    while True:
        try:
            query = input("\n🔍 Query: ").strip()

            if query.lower() in ['exit', 'quit', 'q']:
                break

            if not query:
                continue

            print("Searching...")
            search_query = SearchQuery(
                query_text=query,
                max_results=3,
                semantic_weight=0.6,
                keyword_weight=0.4
            )
            results = await search_engine.search(search_query)

            if not results:
                print("❌ No results found")
            else:
                for i, result in enumerate(results, 1):
                    memory = result.memory_entry
                    score = result.combined_score
                    print(f"\n#{i} [Relevance: {score:.3f}]")
                    print(f"Type: {memory.content_type.value}")
                    print(f"Content: {memory.content[:150]}...")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {e}")

    await pool.close()
    print("\n👋 Bye!")


async def main():
    if len(sys.argv) > 1:
        # Single query mode
        query = " ".join(sys.argv[1:])
        await quick_query(query)
    else:
        # Interactive mode
        await interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())
