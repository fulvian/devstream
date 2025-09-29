#!/usr/bin/env python3
"""
Test script per verificare l'integrazione sqlite-vec con DevStream memory system
"""
import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from devstream.database.connection import ConnectionPool
from devstream.memory.storage import MemoryStorage
from devstream.memory.models import MemoryEntry, ContentType, ContentFormat
from devstream.memory.processing import TextProcessor
from devstream.memory.search import HybridSearchEngine
import numpy as np
import json


async def test_memory_system():
    """Test completo del memory system con virtual tables"""

    # Initialize components
    db_path = "devstream.db"
    connection_pool = ConnectionPool(f"sqlite+aiosqlite:///{db_path}")

    try:
        # Initialize database
        await connection_pool.initialize()
        print("✅ Database inizializzato")

        # Initialize storage
        storage = MemoryStorage(connection_pool)

        # Create virtual tables
        print("🔧 Creando virtual tables...")
        await storage.create_virtual_tables()
        print("✅ Virtual tables create")

        # Initialize text processor
        processor = TextProcessor()
        await processor.initialize()
        print("✅ Text processor inizializzato")

        # Test memory entry creation
        test_content = """
        def calculate_fibonacci(n):
            if n <= 1:
                return n
            return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
        """

        print("🧠 Processando contenuto...")
        processed = await processor.process_text(test_content)
        print(f"✅ Contenuto processato: {len(processed.keywords)} keywords")

        # Create memory entry
        memory = MemoryEntry(
            id="test_memory_001",
            content=test_content,
            content_type=ContentType.CODE,
            content_format=ContentFormat.CODE,
            keywords=processed.keywords,
            entities=processed.entities,
            sentiment=processed.sentiment,
            complexity_score=processed.complexity_score,
            embedding=processed.embedding,
            embedding_model="embeddinggemma",
            embedding_dimension=len(processed.embedding) if processed.embedding else None,
            context_snapshot={"test": True, "source": "integration_test"}
        )

        # Store memory
        print("💾 Salvando memory entry...")
        memory_id = await storage.store_memory(memory)
        print(f"✅ Memory salvata: {memory_id}")

        # Test retrieval
        print("🔍 Recuperando memory entry...")
        retrieved = await storage.get_memory(memory_id)
        if retrieved:
            print(f"✅ Memory recuperata: {retrieved.id}")
            print(f"📊 Keywords: {retrieved.keywords}")
        else:
            print("❌ Memory non trovata")
            return False

        # Test vector search
        if retrieved and retrieved.embedding:
            print("🎯 Testando vector search...")
            query_embedding = np.array(retrieved.embedding)
            vector_results = await storage.search_vectors(query_embedding, k=5)
            print(f"✅ Vector search: {len(vector_results)} risultati")
            for mem_id, distance in vector_results:
                print(f"   - {mem_id}: distance={distance:.4f}")

        # Test FTS search
        print("🔎 Testando FTS search...")
        fts_results = await storage.search_fts("fibonacci calculate", k=5)
        print(f"✅ FTS search: {len(fts_results)} risultati")
        for mem_id, rank in fts_results:
            print(f"   - {mem_id}: rank={rank:.4f}")

        # Initialize hybrid search engine
        print("⚡ Testando hybrid search...")
        search_engine = HybridSearchEngine(storage, processor)
        await search_engine.initialize()

        hybrid_results = await search_engine.search(
            query="fibonacci recursive function",
            k=5,
            vector_weight=0.7,
            keyword_weight=0.3
        )
        print(f"✅ Hybrid search: {len(hybrid_results)} risultati")
        for result in hybrid_results:
            print(f"   - {result['memory_id']}: score={result['score']:.4f}")

        print("\n🎉 Tutti i test completati con successo!")
        return True

    except Exception as e:
        print(f"❌ Errore durante i test: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await connection_pool.close()
        print("🔒 Database connection chiusa")


if __name__ == "__main__":
    success = asyncio.run(test_memory_system())
    sys.exit(0 if success else 1)