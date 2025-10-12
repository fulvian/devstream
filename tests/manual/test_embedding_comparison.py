"""
Direct comparison test: Python vs TypeScript embedding generation

Tests if ollama-python and ollama-js generate identical embeddings
for the same input text using the same model.
"""

import json
import numpy as np
import requests
from pathlib import Path

TEST_QUERY = "session summary atomic write marker file"
MODEL = "embeddinggemma:300m"


def generate_embedding_python():
    """Generate embedding using Python requests (same as Python hooks)."""
    print("🔍 Testing Embedding Generation Consistency\n")
    print(f'Query: "{TEST_QUERY}"')
    print(f"Model: {MODEL}\n")

    try:
        # Generate embedding using direct HTTP request (same as Python hooks)
        print("📊 Generating embedding with Python (requests)...")

        response = requests.post(
            "http://localhost:11434/api/embed",
            json={
                "model": MODEL,
                "input": TEST_QUERY
            },
            timeout=30
        )

        response.raise_for_status()
        data = response.json()

        # Extract embedding from response
        embedding = data["embeddings"][0]

        print(f"✅ Embedding generated")
        print(f"📐 Dimensions: {len(embedding)}")
        print(f"📊 First 5 values: {[round(v, 6) for v in embedding[:5]]}")
        print(f"📊 Last 5 values: {[round(v, 6) for v in embedding[-5:]]}")

        # Calculate statistics
        embedding_array = np.array(embedding, dtype=np.float32)
        mean = float(np.mean(embedding_array))
        std_dev = float(np.std(embedding_array))
        min_val = float(np.min(embedding_array))
        max_val = float(np.max(embedding_array))
        magnitude = float(np.linalg.norm(embedding_array))

        print(f"\n📊 Statistics:")
        print(f"   Mean: {mean:.6f}")
        print(f"   Std Dev: {std_dev:.6f}")
        print(f"   Min: {min_val:.6f}")
        print(f"   Max: {max_val:.6f}")
        print(f"   Magnitude (L2 norm): {magnitude:.6f}")

        # Check if normalized
        is_normalized = abs(magnitude - 1.0) < 0.01
        print(f"   Normalized: {'✅ YES' if is_normalized else '❌ NO'}")

        # Save to file
        result = {
            "query": TEST_QUERY,
            "model": MODEL,
            "embedding": embedding,
            "statistics": {
                "dimensions": len(embedding),
                "mean": mean,
                "stdDev": std_dev,
                "min": min_val,
                "max": max_val,
                "magnitude": magnitude,
                "isNormalized": is_normalized
            }
        }

        with open("embedding_python.json", "w") as f:
            json.dump(result, f, indent=2)

        print(f"\n💾 Embedding saved to embedding_python.json")

        # Compare with TypeScript if available
        ts_file = Path("embedding_typescript.json")
        if ts_file.exists():
            print("\n🔍 Comparing with TypeScript embedding...")
            compare_embeddings(embedding)
        else:
            print("\n⚠️ TypeScript embedding not found. Run test_embedding_comparison.js first.")

    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)


def compare_embeddings(python_embedding):
    """Compare Python and TypeScript embeddings."""
    try:
        with open("embedding_typescript.json", "r") as f:
            ts_data = json.load(f)

        ts_embedding = ts_data["embedding"]
        py_array = np.array(python_embedding, dtype=np.float32)
        ts_array = np.array(ts_embedding, dtype=np.float32)

        print(f"\n📊 Comparison Results:")
        print(f"   Python dimensions: {len(python_embedding)}")
        print(f"   TypeScript dimensions: {len(ts_embedding)}")

        if len(python_embedding) != len(ts_embedding):
            print(f"   ❌ DIMENSION MISMATCH!")
            return

        # Calculate differences
        diff = py_array - ts_array
        abs_diff = np.abs(diff)
        max_diff = float(np.max(abs_diff))
        mean_diff = float(np.mean(abs_diff))
        are_identical = np.allclose(py_array, ts_array, rtol=1e-5, atol=1e-8)

        print(f"\n🔬 Difference Analysis:")
        print(f"   Max absolute difference: {max_diff:.10f}")
        print(f"   Mean absolute difference: {mean_diff:.10f}")
        print(f"   Identical (within tolerance): {'✅ YES' if are_identical else '❌ NO'}")

        if not are_identical:
            print(f"\n⚠️ Embeddings are DIFFERENT!")
            print(f"   First 5 differences: {[round(d, 10) for d in diff[:5]]}")
            print(f"   Indices with largest differences:")
            largest_diff_indices = np.argsort(abs_diff)[-5:][::-1]
            for idx in largest_diff_indices:
                print(f"      Index {idx}: Python={py_array[idx]:.10f}, TypeScript={ts_array[idx]:.10f}, Diff={diff[idx]:.10f}")

            # Cosine similarity
            cosine_sim = float(np.dot(py_array, ts_array) / (np.linalg.norm(py_array) * np.linalg.norm(ts_array)))
            print(f"\n   Cosine similarity: {cosine_sim:.10f}")
            print(f"   {'✅ HIGH similarity (>0.999)' if cosine_sim > 0.999 else '⚠️ LOW similarity'}")
        else:
            print(f"\n✅ Embeddings are IDENTICAL (within floating-point tolerance)!")

        # Statistics comparison
        py_stats = {
            "mean": float(np.mean(py_array)),
            "std": float(np.std(py_array)),
            "magnitude": float(np.linalg.norm(py_array))
        }
        ts_stats = ts_data["statistics"]

        print(f"\n📊 Statistics Comparison:")
        print(f"   Python Mean: {py_stats['mean']:.6f} | TypeScript Mean: {ts_stats['mean']:.6f}")
        print(f"   Python Std: {py_stats['std']:.6f} | TypeScript Std: {ts_stats['stdDev']:.6f}")
        print(f"   Python Magnitude: {py_stats['magnitude']:.6f} | TypeScript Magnitude: {ts_stats['magnitude']:.6f}")

    except Exception as e:
        print(f"❌ Comparison error: {e}")


if __name__ == "__main__":
    generate_embedding_python()
