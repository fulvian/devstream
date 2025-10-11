"""Check properties of stored embeddings in database."""

import sqlite3
import sqlite_vec
import json
import numpy as np

db = sqlite3.connect('data/devstream.db')
db.enable_load_extension(True)
sqlite_vec.load(db)

print("🔍 Checking Stored Embeddings Properties\n")

# Get sample stored embeddings
cursor = db.execute('''
    SELECT v.memory_id, v.content_preview, s.embedding, s.embedding_model, s.embedding_dimension
    FROM vec_semantic_memory v
    JOIN semantic_memory s ON s.id = v.memory_id
    WHERE s.embedding IS NOT NULL
    LIMIT 5
''')

results = cursor.fetchall()

if not results:
    print("❌ No embeddings found in database!")
    exit(1)

print(f"Found {len(results)} sample embeddings\n")

for i, (mem_id, preview, emb_json, model, dim) in enumerate(results, 1):
    print(f"📊 Sample {i}:")
    print(f"   Preview: {preview[:60]}...")
    print(f"   Model: {model}")
    print(f"   Dimension: {dim}")

    if emb_json:
        try:
            embedding = json.loads(emb_json)
            emb_array = np.array(embedding, dtype=np.float32)
            magnitude = np.linalg.norm(emb_array)
            mean = np.mean(emb_array)
            std = np.std(emb_array)

            is_normalized = abs(magnitude - 1.0) < 0.01

            print(f"   Magnitude: {magnitude:.6f}")
            print(f"   Mean: {mean:.6f}")
            print(f"   Std Dev: {std:.6f}")
            print(f"   Normalized: {'✅ YES' if is_normalized else f'❌ NO (magnitude = {magnitude:.6f})'}")
            print(f"   First 5: {[round(v, 6) for v in embedding[:5]]}")
            print()
        except Exception as e:
            print(f"   ❌ Error parsing embedding: {e}\n")
    else:
        print(f"   ❌ No embedding data\n")

db.close()
