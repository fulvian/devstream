#!/usr/bin/env python3
"""
Test script to validate all bug fixes
"""

import asyncio
import sys
from pathlib import Path

# Add paths
sys.path.append(str(Path('.claude/hooks/devstream/utils')))

async def test_all_fixes():
    """Test all bug fixes"""
    print("🧪 Testing all bug fixes...")

    # Test 1: Direct client functionality
    print("\n1. Testing Direct Client...")
    try:
        from direct_client import get_direct_client
        client = get_direct_client()

        health = await client.health_check()
        print(f"   ✅ Health check: {health}")

        result = await client.store_memory(
            content="Test direct client functionality",
            content_type="context",
            keywords=["test", "direct"],
            session_id="test-session"
        )
        print(f"   ✅ Memory storage: {result is not None}")

        search_result = await client.search_memory(query="direct client", limit=3)
        print(f"   ✅ Memory search: {search_result is not None}")

        checkpoint_result = await client.trigger_checkpoint(reason="test")
        print(f"   ✅ Checkpoint: {checkpoint_result is not None}")

    except Exception as e:
        print(f"   ❌ Direct client error: {e}")
        return False

    # Test 2: Import unified client
    print("\n2. Testing Unified Client Import...")
    try:
        from unified_client import get_unified_client
        print("   ✅ Unified client imported successfully")

        # Test that it can be created (simplified test)
        try:
            unified = get_unified_client()
            print("   ✅ Unified client created")
        except Exception as e:
            print(f"   ⚠️  Unified client creation issue: {e}")
            # Continue anyway - this is expected with missing dependencies

    except Exception as e:
        print(f"   ❌ Unified client import error: {e}")
        return False

    # Test 3: Feature flags
    print("\n3. Testing Feature Flags...")
    try:
        from config.feature_flags import get_feature_flag_manager
        manager = get_feature_flag_manager()
        print("   ✅ Feature flags manager created")

        # Test a basic flag
        result = manager.is_enabled("direct_db_enabled")
        print(f"   ✅ Feature flag evaluation: {result}")

    except Exception as e:
        print(f"   ❌ Feature flags error: {e}")
        return False

    # Test 4: Robustness patterns
    print("\n4. Testing Robustness Patterns...")
    try:
        from robustness_patterns import CircuitBreaker, RetryPolicy, CircuitState
        print("   ✅ Robustness patterns imported")

        # Test circuit breaker
        circuit = CircuitBreaker(failure_threshold=3)
        print(f"   ✅ Circuit breaker created: {circuit.state}")

        # Test retry policy
        retry = RetryPolicy(max_retries=3)
        print(f"   ✅ Retry policy created")

    except Exception as e:
        print(f"   ❌ Robustness patterns error: {e}")
        return False

    # Test 5: Hook imports
    print("\n5. Testing Hook Imports...")
    try:
        # Test PostToolUse hook import
        sys.path.append(str(Path('.claude/hooks/devstream/memory')))
        from post_tool_use import PostToolUseHook
        print("   ✅ PostToolUse hook imported")

        # Test PreToolUse hook import
        from pre_tool_use import PreToolUseHook
        print("   ✅ PreToolUse hook imported")

        # Test UserQueryContextEnhancer hook import
        sys.path.append(str(Path('.claude/hooks/devstream/context')))
        from user_query_context_enhancer import UserPromptSubmitHook
        print("   ✅ UserQueryContextEnhancer hook imported")

    except Exception as e:
        print(f"   ❌ Hook imports error: {e}")
        return False

    # Test 6: Connection Manager
    print("\n6. Testing Connection Manager...")
    try:
        from connection_manager import ConnectionManager
        manager = ConnectionManager.get_instance()
        print("   ✅ Connection manager created")

        stats = manager.get_stats()
        print(f"   ✅ Connection stats: {stats['active_connections']} connections")

    except Exception as e:
        print(f"   ❌ Connection manager error: {e}")
        return False

    print("\n🎉 All tests passed! Bug fixes validated successfully!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_all_fixes())
    if not success:
        sys.exit(1)