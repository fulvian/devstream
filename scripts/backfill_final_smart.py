#!/usr/bin/env python3
"""Final smart backfill - only missing records"""
import asyncio, sys, json, time
sys.path.append('.claude/hooks/devstream/utils')
from sqlite_vec_helper import get_db_connection_with_vec

try:
    import aiohttp
except ImportError:
    import subprocess
    subprocess.run([".devstream/bin/python", "-m", "pip", "install", "aiohttp"], check=True)
    import aiohttp

async def generate_embedding(text):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:11434/api/embed", json={"model": "embeddinggemma:300m", "input": text, "keep_alive": "5m"}, timeout=aiohttp.ClientTimeout(total=30)) as response:
                return (await response.json())["embeddings"][0] if response.status == 200 else None
    except:
        return None

async def main():
    conn = get_db_connection_with_vec('data/devstream.db')
    c = conn.cursor()

    # Get ONLY records not in vec
    c.execute("SELECT id, content FROM semantic_memory WHERE id NOT IN (SELECT memory_id FROM vec_semantic_memory) ORDER BY created_at DESC")
    records = c.fetchall()
    total = len(records)

    print(f"📊 {total:,} records to backfill")

    success, failed, start = 0, 0, time.time()

    for i, (rid, content) in enumerate(records, 1):
        emb = await generate_embedding(content)

        if emb:
            c.execute("UPDATE semantic_memory SET embedding = ? WHERE id = ?", (json.dumps(emb), rid))
            conn.commit()
            success += 1
        else:
            failed += 1

        if i % 100 == 0:
            rate = i / (time.time() - start)
            eta = (total - i) / rate / 60 if rate > 0 else 0
            print(f"{i}/{total} ({i/total*100:.1f}%) | {rate:.1f} rec/s | ETA: {eta:.1f}min")

    print(f"\n✅ Done! Success: {success:,} | Failed: {failed:,}")
    conn.close()

if __name__ == "__main__":
    asyncio.run(main())
