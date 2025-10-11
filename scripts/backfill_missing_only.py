#!/usr/bin/env python3
"""
Backfill ONLY records NOT in vec_semantic_memory
Skips records already processed (even if JSON was cleaned up)
"""
import asyncio
import sys
import json
sys.path.append('.claude/hooks/devstream/utils')
from sqlite_vec_helper import get_db_connection_with_vec

# Import production script components
sys.path.append('scripts')
import scripts.backfill_embeddings_production as prod

async def backfill_missing_only():
    """Backfill only records not in vec_semantic_memory"""

    conn = get_db_connection_with_vec('data/devstream.db')
    conn.row_factory = prod.sqlite3.Row
    cursor = conn.cursor()

    # Count records NOT in vec (this is the key query)
    cursor.execute("""
        SELECT id, content, content_type, created_at
        FROM semantic_memory
        WHERE id NOT IN (SELECT memory_id FROM vec_semantic_memory)
        ORDER BY created_at DESC
    """)

    records = cursor.fetchall()
    total = len(records)

    print(f"📊 Found {total:,} records NOT in vec_semantic_memory")
    print(f"Processing with batch size {prod.BATCH_SIZE}...")
    print()

    ollama = prod.OllamaClient()
    progress = prod.BackfillProgress(prod.Path.home() / ".claude" / "state" / "backfill_missing.json")
    progress.start_time = prod.time.time()

    # Process in batches
    for i in range(0, total, prod.BATCH_SIZE):
        batch = records[i:i+prod.BATCH_SIZE]

        print(f"Batch {i//prod.BATCH_SIZE + 1}/{(total + prod.BATCH_SIZE - 1)//prod.BATCH_SIZE}: ", end='', flush=True)

        await prod.backfill_batch(conn, batch, ollama, progress)

        print(f"{progress.processed}/{total} ({progress.processed/total*100:.1f}%)")

        if progress.processed % 100 == 0:
            elapsed = prod.time.time() - progress.start_time
            rate = progress.processed / elapsed
            eta = (total - progress.processed) / rate / 60 if rate > 0 else 0
            print(f"  Rate: {rate:.1f} rec/sec | ETA: {eta:.1f} min")

    print()
    print(f"✅ Backfill complete!")
    print(f"  Processed: {progress.processed:,}")
    print(f"  Success: {progress.successful:,}")
    print(f"  Failed: {progress.failed:,}")

    conn.close()

if __name__ == "__main__":
    asyncio.run(backfill_missing_only())
