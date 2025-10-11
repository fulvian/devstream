#!/usr/bin/env python3
"""
Trigger sync for records with JSON embeddings (not yet in vec0)
Uses UPDATE to activate trigger in small batches
"""
import sys
sys.path.append('.claude/hooks/devstream/utils')
from sqlite_vec_helper import get_db_connection_with_vec

BATCH_SIZE = 50

conn = get_db_connection_with_vec('data/devstream.db')
cursor = conn.cursor()

# Get IDs of records with JSON embedding
cursor.execute("""
    SELECT id FROM semantic_memory
    WHERE embedding IS NOT NULL AND embedding != ''
    LIMIT 1000
""")

ids = [row[0] for row in cursor.fetchall()]
total = len(ids)

print(f"📊 Found {total} records with JSON embeddings")
print(f"Processing in batches of {BATCH_SIZE}...")
print()

synced = 0
for i in range(0, total, BATCH_SIZE):
    batch = ids[i:i+BATCH_SIZE]

    # UPDATE each record to trigger sync
    placeholders = ','.join(['?' for _ in batch])
    cursor.execute(f"""
        UPDATE semantic_memory
        SET embedding = embedding
        WHERE id IN ({placeholders})
    """, batch)

    conn.commit()
    synced += len(batch)

    print(f"Batch {i//BATCH_SIZE + 1}: {synced}/{total} synced ({synced/total*100:.1f}%)")

# Verify
vec_count = cursor.execute('SELECT COUNT(*) FROM vec_semantic_memory').fetchone()[0]
remaining_json = cursor.execute(
    "SELECT COUNT(*) FROM semantic_memory WHERE embedding IS NOT NULL AND embedding != ''"
).fetchone()[0]

print()
print(f"✅ Sync complete!")
print(f"Total in vec_semantic_memory: {vec_count:,}")
print(f"Remaining with JSON: {remaining_json:,}")

conn.close()
