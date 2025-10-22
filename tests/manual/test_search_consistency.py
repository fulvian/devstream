"""
Test search consistency: Use SAME embedding to search in Python and check distances.
Then we'll use the same embedding via MCP to compare results.
"""

import sqlite3
import sqlite_vec
import json

# Load the embedding we generated earlier
with open('embedding_python.json', 'r') as f:
    data = json.load(f)
    query_embedding = data['embedding']

print(f"🔍 Testing Search Consistency")
print(f"Query: \"{data['query']}\"")
print(f"Embedding dimensions: {len(query_embedding)}\n")

# Connect to database
db = sqlite3.connect('data/devstream.db')
db.enable_load_extension(True)
sqlite_vec.load(db)

# Search using Python direct
print("📊 Python Direct Search (vec_semantic_memory):")
cursor = db.execute('''
    SELECT memory_id, distance, content_preview, content_type
    FROM vec_semantic_memory
    WHERE embedding MATCH vec_f32(?)
      AND k = 10
    ORDER BY distance
''', [json.dumps(query_embedding)])

results = cursor.fetchall()
print(f"Found: {len(results)} results\n")

for i, (mem_id, dist, preview, ctype) in enumerate(results[:5], 1):
    print(f"{i}. distance={dist:.4f} | {ctype} | {preview[:60]}...")

# Save embedding to file for MCP test
with open('test_query_embedding.json', 'w') as f:
    json.dump({
        'query': data['query'],
        'embedding': query_embedding,
        'dimensions': len(query_embedding)
    }, f, indent=2)

print(f"\n💾 Query embedding saved to test_query_embedding.json")
print(f"🔄 Now test via MCP with the SAME embedding to compare distances.")

db.close()
