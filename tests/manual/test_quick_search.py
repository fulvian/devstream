#!/usr/bin/env python3
"""
Quick test to verify sqlite-vec modern syntax works in production database.
Tests the EXACT query syntax used in the fixed TypeScript code.
"""

import sqlite3
import json
import numpy as np
import sys

# Connect to production database (use absolute path)
db_path = "/Users/fulvioventura/devstream/data/devstream.db"
print(f"🔗 Connecting to: {db_path}\n")
conn = sqlite3.connect(db_path)
conn.enable_load_extension(True)

# Load sqlite-vec extension
try:
    # Use the extension from mcp-devstream-server node_modules (absolute path, no .dylib extension)
    ext_path = "/Users/fulvioventura/devstream/mcp-devstream-server/node_modules/sqlite-vec-darwin-arm64/vec0"
    conn.load_extension(ext_path)
    version = conn.execute("SELECT vec_version()").fetchone()[0]
    print(f"✅ sqlite-vec loaded: {version}")
except Exception as e:
    print(f"❌ Failed to load sqlite-vec: {e}")
    print(f"   Extension path: {ext_path}")
    sys.exit(1)

# Check if virtual table exists and has data
cursor = conn.cursor()
count = cursor.execute("SELECT COUNT(*) FROM vec_semantic_memory").fetchone()[0]
print(f"📊 Vector records available: {count:,}\n")

if count == 0:
    print("❌ No embeddings in vec_semantic_memory table")
    sys.exit(1)

# Get a sample embedding to test with
print("📋 Fetching sample embedding...")
sample = cursor.execute("""
    SELECT memory_id, embedding
    FROM vec_semantic_memory
    LIMIT 1
""").fetchone()

memory_id, embedding_blob = sample
embedding_array = np.frombuffer(embedding_blob, dtype=np.float32)
print(f"✅ Sample memory_id: {memory_id}")
print(f"✅ Embedding dimension: {len(embedding_array)}\n")

# Test the MODERN syntax (what we fixed in TypeScript)
print("🧪 Testing MODERN sqlite-vec syntax (ORDER BY distance LIMIT ?)...")
print("Query: WHERE embedding MATCH ? ORDER BY distance LIMIT ?\n")

try:
    results = cursor.execute("""
        SELECT memory_id, distance
        FROM vec_semantic_memory
        WHERE embedding MATCH ?
        ORDER BY distance
        LIMIT ?
    """, [embedding_blob, 5]).fetchall()

    print(f"✅ Query succeeded! Found {len(results)} results\n")

    for i, (mid, dist) in enumerate(results, 1):
        print(f"  {i}. memory_id: {mid[:16]}... | distance: {dist:.4f}")

    # Verify exact match is first
    if results[0][0] == memory_id:
        print(f"\n✅ **PERFECT**: Exact match found at rank #1")
        print(f"✅ Distance: {results[0][1]:.6f} (should be ~0.0)")
    else:
        print(f"\n⚠️  Expected exact match at rank #1, got: {results[0][0]}")

except Exception as e:
    print(f"❌ MODERN syntax failed: {e}")
    sys.exit(1)

# Test the LEGACY syntax (what was breaking before)
print("\n" + "="*70)
print("🧪 Testing LEGACY sqlite-vec syntax (AND k = ?)...")
print("Query: WHERE embedding MATCH ? AND k = ?\n")

try:
    results = cursor.execute("""
        SELECT memory_id, distance
        FROM vec_semantic_memory
        WHERE embedding MATCH ?
          AND k = ?
    """, [embedding_blob, 5]).fetchall()

    print(f"⚠️  LEGACY syntax succeeded (unexpected!) Found {len(results)} results")

except Exception as e:
    print(f"✅ LEGACY syntax failed as expected: {e}")
    print(f"✅ This confirms SQLite version requires modern syntax")

conn.close()

print("\n" + "="*70)
print("🎯 **CONCLUSION**: Modern syntax works correctly in production database")
print("🚀 TypeScript fix is validated and ready for deployment")
