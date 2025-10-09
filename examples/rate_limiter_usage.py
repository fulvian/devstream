#!/usr/bin/env python3
"""
DevStream Rate Limiter Usage Examples.

Demonstrates:
1. Basic blocking rate limiting
2. Non-blocking capacity checks (graceful degradation)
3. Statistics tracking
4. Integration with memory operations
5. Integration with Ollama operations
"""

import asyncio
import sys
from pathlib import Path

# Add .claude/hooks to path
sys.path.insert(0, str(Path(__file__).parent.parent / ".claude/hooks"))

from devstream.utils.rate_limiter import (
    memory_rate_limiter,
    ollama_rate_limiter,
    has_memory_capacity,
    has_ollama_capacity,
    get_memory_stats,
    get_ollama_stats,
)


async def example_basic_blocking():
    """Example 1: Basic blocking rate limiting."""
    print("=" * 60)
    print("EXAMPLE 1: Basic Blocking Rate Limiting")
    print("=" * 60)

    print("\nExecuting 5 memory operations with 10 ops/sec limit...")
    for i in range(5):
        async with memory_rate_limiter:
            print(f"  Operation {i+1} completed")
            # Simulate memory operation
            await asyncio.sleep(0.01)

    stats = get_memory_stats()
    print(f"\nStatistics: {stats['total_operations']} operations, "
          f"{stats['throttle_rate']} throttled")


async def example_non_blocking_graceful():
    """Example 2: Non-blocking capacity check with graceful degradation."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Non-Blocking Graceful Degradation")
    print("=" * 60)

    executed = 0
    skipped = 0

    print("\nAttempting 10 operations with graceful degradation...")
    for i in range(10):
        if has_memory_capacity():
            async with memory_rate_limiter:
                print(f"  ✅ Operation {i+1} executed")
                executed += 1
                await asyncio.sleep(0.01)
        else:
            print(f"  ⏭️  Operation {i+1} skipped (rate limit)")
            skipped += 1

    print(f"\nResult: {executed} executed, {skipped} skipped")


async def example_statistics_monitoring():
    """Example 3: Statistics tracking and monitoring."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Statistics Tracking")
    print("=" * 60)

    # Execute operations
    print("\nExecuting 15 operations...")
    for i in range(15):
        async with memory_rate_limiter:
            await asyncio.sleep(0.01)

        # Print stats every 5 operations
        if (i + 1) % 5 == 0:
            stats = get_memory_stats()
            print(f"\nAfter {i+1} operations:")
            print(f"  Total: {stats['total_operations']}")
            print(f"  Throttled: {stats['throttled_operations']}")
            print(f"  Throttle Rate: {stats['throttle_rate']}")


async def example_ollama_integration():
    """Example 4: Ollama embedding rate limiting."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Ollama Embedding Rate Limiting")
    print("=" * 60)

    print("\nExecuting 10 embedding operations with 5 ops/sec limit...")
    for i in range(10):
        async with ollama_rate_limiter:
            print(f"  Embedding {i+1} generated")
            # Simulate embedding generation (100-200ms)
            await asyncio.sleep(0.15)

    stats = get_ollama_stats()
    print(f"\nStatistics: {stats['total_operations']} operations, "
          f"{stats['throttle_rate']} throttled")


async def example_mixed_operations():
    """Example 5: Mixed memory and Ollama operations."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Mixed Memory + Ollama Operations")
    print("=" * 60)

    async def memory_operation(idx: int):
        """Simulate memory storage."""
        if has_memory_capacity():
            async with memory_rate_limiter:
                print(f"  💾 Memory operation {idx}")
                await asyncio.sleep(0.01)
        else:
            print(f"  ⏭️  Memory operation {idx} skipped")

    async def ollama_operation(idx: int):
        """Simulate embedding generation."""
        if has_ollama_capacity():
            async with ollama_rate_limiter:
                print(f"  🧠 Ollama operation {idx}")
                await asyncio.sleep(0.15)
        else:
            print(f"  ⏭️  Ollama operation {idx} skipped")

    print("\nExecuting mixed operations concurrently...")
    tasks = []
    for i in range(5):
        tasks.append(memory_operation(i))
        tasks.append(ollama_operation(i))

    await asyncio.gather(*tasks)

    print(f"\nMemory Stats: {get_memory_stats()['throttle_rate']} throttled")
    print(f"Ollama Stats: {get_ollama_stats()['throttle_rate']} throttled")


async def example_real_world_hook_pattern():
    """Example 6: Real-world PostToolUse hook pattern."""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Real-World Hook Integration Pattern")
    print("=" * 60)

    async def post_tool_use_hook(tool_name: str, content: str):
        """Simulate PostToolUse hook with rate limiting."""
        print(f"\nPostToolUse triggered: {tool_name}")

        # Check capacity first (graceful degradation)
        if not has_memory_capacity():
            print("  ⚠️  Rate limit exceeded, skipping memory storage")
            return

        # Store in memory with rate limiting
        async with memory_rate_limiter:
            print(f"  💾 Storing content ({len(content)} chars)")
            await asyncio.sleep(0.01)  # Simulate MCP call

        # Generate embedding with rate limiting
        if has_ollama_capacity():
            async with ollama_rate_limiter:
                print(f"  🧠 Generating embedding")
                await asyncio.sleep(0.15)  # Simulate Ollama call
        else:
            print("  ⚠️  Ollama rate limit, deferring embedding")

    # Simulate rapid tool executions
    print("\nSimulating 8 rapid tool executions...")
    for i in range(8):
        await post_tool_use_hook(f"Tool{i}", f"Content for tool {i}")

    print(f"\nFinal Stats:")
    print(f"  Memory: {get_memory_stats()['total_operations']} ops, "
          f"{get_memory_stats()['throttle_rate']} throttled")
    print(f"  Ollama: {get_ollama_stats()['total_operations']} ops, "
          f"{get_ollama_stats()['throttle_rate']} throttled")


async def main():
    """Run all examples."""
    print("\n🚀 DevStream Rate Limiter Usage Examples")
    print("Based on Context7: /mjpieters/aiolimiter (GCRA algorithm)\n")

    await example_basic_blocking()
    await example_non_blocking_graceful()
    await example_statistics_monitoring()
    await example_ollama_integration()
    await example_mixed_operations()
    await example_real_world_hook_pattern()

    print("\n" + "=" * 60)
    print("✅ ALL EXAMPLES COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
