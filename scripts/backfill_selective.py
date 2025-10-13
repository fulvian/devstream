#!/usr/bin/env python3
"""
Selective backfill - only semantic-rich content types
Excludes 'context' (task checkpoints) as they are metadata better suited for SQL queries
Processes: decision, code, learning, documentation, output, error (~1,040 records)
"""
import asyncio
import sys
import json
import time
sys.path.append('.claude/hooks/devstream/utils')
from sqlite_vec_helper import get_db_connection_with_vec

try:
    import aiohttp
except ImportError:
    import subprocess
    subprocess.run([".devstream/bin/python", "-m", "pip", "install", "aiohttp"], check=True)
    import aiohttp

# Content types to include (semantic-rich content only)
INCLUDE_TYPES = ['decision', 'code', 'learning', 'documentation', 'output', 'error']

async def generate_embedding(text: str) -> list:
    """Generate embedding via Ollama embeddinggemma:300m"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:11434/api/embed",
                json={
                    "model": "embeddinggemma:300m",
                    "input": text,
                    "keep_alive": "5m"
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["embeddings"][0]
                return None
    except Exception as e:
        print(f"⚠️ Embedding error: {e}")
        return None

async def main():
    """Main backfill logic"""
    conn = get_db_connection_with_vec('data/devstream.db')
    c = conn.cursor()

    # Get ONLY semantic-rich records not in vec
    types_placeholder = ','.join(['?' for _ in INCLUDE_TYPES])
    query = f"""
        SELECT id, content, content_type
        FROM semantic_memory
        WHERE id NOT IN (SELECT memory_id FROM vec_semantic_memory)
          AND content_type IN ({types_placeholder})
        ORDER BY content_type, created_at DESC
    """

    c.execute(query, INCLUDE_TYPES)
    records = c.fetchall()
    total = len(records)

    print(f"📊 Selective Backfill - Semantic-Rich Content Only")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Content types: {', '.join(INCLUDE_TYPES)}")
    print(f"Total records: {total:,}")
    print(f"Excluded 'context' type: ~11K task checkpoints (metadata)")
    print()

    if total == 0:
        print("✅ No records to process!")
        return

    success, failed, start = 0, 0, time.time()
    current_type = None

    for i, (rid, content, content_type) in enumerate(records, 1):
        # Print type header on change
        if content_type != current_type:
            if current_type:
                print()
            print(f"🔄 Processing '{content_type}' records...")
            current_type = content_type

        emb = await generate_embedding(content)

        if emb:
            c.execute(
                "UPDATE semantic_memory SET embedding = ? WHERE id = ?",
                (json.dumps(emb), rid)
            )
            conn.commit()
            success += 1
        else:
            failed += 1

        # Progress every 50 records
        if i % 50 == 0:
            elapsed = time.time() - start
            rate = i / elapsed if elapsed > 0 else 0
            eta = (total - i) / rate / 60 if rate > 0 else 0
            print(f"  {i}/{total} ({i/total*100:.1f}%) | {rate:.1f} rec/s | ETA: {eta:.1f}min")

    # Final stats
    elapsed = time.time() - start
    print()
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ Selective Backfill Complete!")
    print(f"Success: {success:,} | Failed: {failed:,}")
    print(f"Time: {elapsed/60:.1f} minutes | Rate: {success/elapsed:.1f} rec/s")
    print()

    # Verify final coverage
    total_sem = c.execute('SELECT COUNT(*) FROM semantic_memory').fetchone()[0]
    total_vec = c.execute('SELECT COUNT(*) FROM vec_semantic_memory').fetchone()[0]
    excluded_context = c.execute(
        "SELECT COUNT(*) FROM semantic_memory WHERE content_type = 'context'"
    ).fetchone()[0]

    print(f"📊 FINAL COVERAGE:")
    print(f"Total semantic_memory: {total_sem:,}")
    print(f"Total vec_semantic_memory: {total_vec:,}")
    print(f"Excluded 'context' records: {excluded_context:,}")
    print(f"Expected coverage: {(total_vec / (total_sem - excluded_context) * 100):.1f}%")
    print(f"  (excludes 'context' checkpoints from denominator)")

    conn.close()

if __name__ == "__main__":
    asyncio.run(main())
