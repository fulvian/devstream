#!/usr/bin/env python3
"""
Benchmark script for Ollama embedding cache performance.

Demonstrates latency improvement from SHA256-based LRU cache.

Expected Results:
- Cache miss: ~100ms (Ollama API call)
- Cache hit: <1ms (memory lookup)
- 90%+ latency reduction for cached content
"""

import sys
import time
import statistics
from pathlib import Path

# Add utils to path
sys.path.append(str(Path(__file__).parent.parent.parent / ".claude/hooks/devstream/utils"))

from ollama_client import OllamaEmbeddingClient


def benchmark_cache_performance():
    """
    Benchmark cache performance with realistic workload.
    """
    print("=" * 70)
    print("Ollama Embedding Cache Performance Benchmark")
    print("=" * 70)

    client = OllamaEmbeddingClient()

    # Test connection first
    print("\n1. Testing Ollama connection...")
    if not client.test_connection():
        print("   ❌ Ollama not available - skipping benchmark")
        return

    print("   ✅ Ollama connected\n")

    # Benchmark 1: Cache miss latency (first call)
    print("2. Benchmark: Cache Miss Latency (Ollama API call)")
    print("   " + "-" * 65)

    test_texts = [
        "DevStream is a task management system for Claude Code",
        "Python 3.11 introduces new syntax features",
        "Machine learning models require large datasets",
        "Docker containers provide isolated environments",
        "TypeScript adds static typing to JavaScript"
    ]

    miss_latencies = []
    for i, text in enumerate(test_texts, 1):
        start_time = time.time()
        embedding = client.generate_embedding(text)
        latency = (time.time() - start_time) * 1000  # ms

        miss_latencies.append(latency)
        print(f"   Text {i}: {latency:.2f}ms (embedding dim: {len(embedding)})")

    avg_miss_latency = statistics.mean(miss_latencies)
    print(f"\n   Average cache miss latency: {avg_miss_latency:.2f}ms")

    # Benchmark 2: Cache hit latency (repeat calls)
    print("\n3. Benchmark: Cache Hit Latency (memory lookup)")
    print("   " + "-" * 65)

    hit_latencies = []
    for i, text in enumerate(test_texts, 1):
        start_time = time.time()
        embedding = client.generate_embedding(text)
        latency = (time.time() - start_time) * 1000  # ms

        hit_latencies.append(latency)
        print(f"   Text {i}: {latency:.2f}ms (cache hit)")

    avg_hit_latency = statistics.mean(hit_latencies)
    print(f"\n   Average cache hit latency: {avg_hit_latency:.2f}ms")

    # Performance comparison
    print("\n4. Performance Comparison")
    print("   " + "-" * 65)

    speedup = avg_miss_latency / avg_hit_latency
    latency_reduction = ((avg_miss_latency - avg_hit_latency) / avg_miss_latency) * 100

    print(f"   Cache miss avg:      {avg_miss_latency:.2f}ms")
    print(f"   Cache hit avg:       {avg_hit_latency:.2f}ms")
    print(f"   Speedup:             {speedup:.1f}×")
    print(f"   Latency reduction:   {latency_reduction:.1f}%")

    # Benchmark 3: Realistic workload (mixed hit/miss)
    print("\n5. Benchmark: Realistic Workload (80% cache hit rate)")
    print("   " + "-" * 65)

    # Simulate realistic workload: 80% repeated content, 20% new
    realistic_texts = []
    for _ in range(40):  # 40 hits
        realistic_texts.append(test_texts[0])  # Repeated content
    for i in range(10):  # 10 misses
        realistic_texts.append(f"Unique text {i}")

    # Clear cache for clean test
    client.clear_cache()

    # Warm cache with first text
    client.generate_embedding(test_texts[0])

    realistic_latencies = []
    start_time = time.time()
    for text in realistic_texts:
        t0 = time.time()
        client.generate_embedding(text)
        realistic_latencies.append((time.time() - t0) * 1000)
    total_time = (time.time() - start_time) * 1000

    avg_realistic_latency = statistics.mean(realistic_latencies)
    p95_latency = statistics.quantiles(realistic_latencies, n=20)[18]  # 95th percentile

    print(f"   Total requests:      50")
    print(f"   Total time:          {total_time:.2f}ms")
    print(f"   Avg latency:         {avg_realistic_latency:.2f}ms")
    print(f"   p95 latency:         {p95_latency:.2f}ms")

    # Cache statistics
    print("\n6. Cache Statistics")
    print("   " + "-" * 65)

    stats = client.get_cache_stats()
    print(f"   Cache size:          {stats['size']}/{stats['max_size']}")
    print(f"   Cache hits:          {stats['hits']}")
    print(f"   Cache misses:        {stats['misses']}")
    print(f"   Cache evictions:     {stats['evictions']}")
    print(f"   Hit rate:            {stats['hit_rate']:.1f}%")

    # Final verdict
    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS")
    print("=" * 70)

    if latency_reduction >= 90:
        verdict = "✅ EXCELLENT"
    elif latency_reduction >= 80:
        verdict = "✅ GOOD"
    else:
        verdict = "⚠️  NEEDS IMPROVEMENT"

    print(f"\nCache Performance: {verdict}")
    print(f"Latency Reduction: {latency_reduction:.1f}%")
    print(f"Speedup Factor:    {speedup:.1f}×")

    if speedup >= 50:
        print("\n💡 Cache provides significant performance improvement!")
        print("   Recommended for production use.")
    elif speedup >= 10:
        print("\n💡 Cache provides moderate performance improvement.")
        print("   Consider enabling for high-traffic scenarios.")
    else:
        print("\n⚠️  Cache performance lower than expected.")
        print("   Check Ollama API latency and cache configuration.")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        benchmark_cache_performance()
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
