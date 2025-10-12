#!/usr/bin/env python3
"""
Simple Search Test - Uses only FTS (keyword) search for quick testing.

This is a simplified version that works without embedding generation.
Use this for quick validation of search functionality.

Usage:
    python test_simple_search.py "your query here"
    python test_simple_search.py  # Interactive mode
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from devstream.database.connection import ConnectionPool
from devstream.memory.storage import MemoryStorage


async def simple_search(query: str, top_k: int = 5):
    """Execute a keyword-based search (FTS5)."""
    print(f"\n🔍 Query: {query}\n")
    print("="*80)

    # Initialize
    pool = ConnectionPool("data/devstream.db")
    await pool.initialize()
    storage = MemoryStorage(pool)

    try:
        # Use FTS (keyword) search only
        print("Searching with keyword matching...")
        fts_results = await storage.search_fts(query, k=top_k)

        if not fts_results:
            print("❌ No results found")
        else:
            print(f"✅ Found {len(fts_results)} results:\n")

            # Get full memory entries
            for i, (memory_id, rank) in enumerate(fts_results, 1):
                memory = await storage.get_memory(memory_id)
                if memory:
                    # Calculate simple relevance score
                    relevance = 1.0 - (rank / 10.0) if rank < 10.0 else 0.1

                    print(f"#{i} [Relevance: {relevance:.3f}]")
                    print(f"   Type: {memory.content_type}")
                    print(f"   Content: {memory.content[:200]}...")
                    if memory.keywords:
                        print(f"   Keywords: {', '.join(memory.keywords[:5])}")
                    print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("="*80)
        await pool.close()


async def interactive_mode():
    """Simple interactive search mode."""
    print("\n🎮 Simple Search Tester - Interactive Mode")
    print("(Using keyword-based FTS search only)")
    print("Enter queries or 'exit' to quit\n")

    pool = ConnectionPool("data/devstream.db")
    await pool.initialize()
    storage = MemoryStorage(pool)

    try:
        while True:
            try:
                query = input("\n🔍 Query: ").strip()

                if query.lower() in ['exit', 'quit', 'q']:
                    break

                if not query:
                    continue

                print("Searching...")
                fts_results = await storage.search_fts(query, k=5)

                if not fts_results:
                    print("❌ No results found")
                else:
                    for i, (memory_id, rank) in enumerate(fts_results, 1):
                        memory = await storage.get_memory(memory_id)
                        if memory:
                            relevance = 1.0 - (rank / 10.0) if rank < 10.0 else 0.1
                            print(f"\n#{i} [Relevance: {relevance:.3f}]")
                            print(f"Type: {memory.content_type}")
                            print(f"Content: {memory.content[:150]}...")

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    finally:
        await pool.close()
        print("\n👋 Bye!")


async def main():
    if len(sys.argv) > 1:
        # Single query mode
        query = " ".join(sys.argv[1:])
        await simple_search(query)
    else:
        # Interactive mode
        await interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())
