#!/usr/bin/env python3
"""
Test token budget enforcement in pre_tool_use.py

Validates that:
1. Token estimation works correctly
2. Budget-aware formatting stays within limits
3. Results are truncated intelligently
4. Token count is visible in output
"""

import sys
from pathlib import Path

# Add hooks to path
sys.path.insert(0, str(Path(__file__).parent.parent / '.claude/hooks/devstream/memory'))

from pre_tool_use import PreToolUseHook


def test_token_estimation():
    """Test token estimation utility."""
    hook = PreToolUseHook()

    # Test cases: (text, expected_tokens)
    test_cases = [
        ("", 0),
        ("a" * 4, 1),  # 4 chars = 1 token
        ("a" * 400, 100),  # 400 chars = 100 tokens
        ("Hello world! " * 50, 162),  # ~650 chars = ~162 tokens
    ]

    print("Testing token estimation:")
    for text, expected in test_cases:
        actual = hook._estimate_tokens(text)
        status = "✅" if actual == expected else "❌"
        print(f"  {status} Text length {len(text)} -> {actual} tokens (expected {expected})")
    print()


def test_budget_enforcement():
    """Test budget-aware memory formatting."""
    hook = PreToolUseHook()

    # Create mock memory results
    memory_items = [
        {
            "content": "a" * 2000,  # 500 tokens
            "relevance_score": 0.95
        },
        {
            "content": "b" * 2000,  # 500 tokens
            "relevance_score": 0.85
        },
        {
            "content": "c" * 2000,  # 500 tokens
            "relevance_score": 0.75
        },
        {
            "content": "d" * 2000,  # 500 tokens (should not fit)
            "relevance_score": 0.65
        }
    ]

    # Test with 2000 token budget
    print("Testing budget enforcement (2000 token limit):")
    formatted = hook._format_memory_with_budget(memory_items, max_tokens=2000)

    # Verify token count
    actual_tokens = hook._estimate_tokens(formatted)
    print(f"  Total tokens: {actual_tokens}")
    print(f"  Budget: 2000")
    print(f"  Within budget: {'✅' if actual_tokens <= 2000 else '❌'}")

    # Verify token count is visible
    has_token_info = "*Total tokens used:" in formatted
    print(f"  Token info visible: {'✅' if has_token_info else '❌'}")

    # Count results included
    result_count = formatted.count("## Result")
    print(f"  Results included: {result_count}")
    print()

    # Print sample output
    print("Sample output (first 500 chars):")
    print(formatted[:500])
    print("...")
    print()


def test_small_budget():
    """Test with very small budget to verify early termination."""
    hook = PreToolUseHook()

    memory_items = [
        {
            "content": "Small content item 1",
            "relevance_score": 0.95
        },
        {
            "content": "Small content item 2",
            "relevance_score": 0.85
        }
    ]

    print("Testing small budget (100 token limit):")
    formatted = hook._format_memory_with_budget(memory_items, max_tokens=100)

    actual_tokens = hook._estimate_tokens(formatted)
    print(f"  Total tokens: {actual_tokens}")
    print(f"  Budget: 100")
    print(f"  Within budget: {'✅' if actual_tokens <= 100 else '❌'}")
    print()


def test_configuration():
    """Test configuration reading."""
    hook = PreToolUseHook()

    print("Testing configuration:")
    print(f"  Memory token budget: {hook.memory_token_budget}")
    print(f"  Expected: 2000")
    print(f"  Match: {'✅' if hook.memory_token_budget == 2000 else '❌'}")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("Token Budget Enforcement Test Suite")
    print("=" * 60)
    print()

    test_token_estimation()
    test_budget_enforcement()
    test_small_budget()
    test_configuration()

    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)
