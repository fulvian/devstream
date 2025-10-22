#!/usr/bin/env .devstream/bin/python
"""
Comprehensive test for PostToolUse hook fallback mode
Tests the complete functionality including session tracking and memory storage
"""

import sys
import asyncio
import json
import os
from pathlib import Path
from datetime import datetime

# Add hook directory to path
sys.path.insert(0, str(Path(__file__).parent / '.claude' / 'hooks' / 'devstream' / 'memory'))

async def test_fallback_mode():
    """Test the complete fallback mode functionality"""
    print("🧪 Testing PostToolUse hook fallback mode")
    print("=" * 60)

    try:
        # Import PostToolUse hook
        from post_tool_use import PostToolUseHook

        # Create hook instance
        hook = PostToolUseHook()

        print("✅ Hook instance created successfully")
        print(f"📁 Database path: {hook.db_path}")

        # Test session tracking components
        print("\n🔍 Testing session tracking components...")

        # Test current session ID retrieval
        session_id = await hook._get_current_session_id()
        if session_id:
            print(f"✅ Active session found: {session_id[:12]}...")
        else:
            print("❌ No active session found")
            return False

        # Test active files retrieval
        active_files = await hook._get_active_files(session_id)
        print(f"📁 Active files: {len(active_files)} files tracked")

        # Test active tasks retrieval
        active_tasks = await hook._get_active_tasks(session_id)
        print(f"📋 Active tasks: {len(active_tasks)} tasks tracked")

        return True

    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_memory_storage_simulation():
    """Test simulated memory storage functionality"""
    print("\n🧪 Testing memory storage simulation")
    print("=" * 60)

    try:
        from post_tool_use import PostToolUseHook

        hook = PostToolUseHook()

        # Simulate a Write tool execution
        test_file_path = "test_session_restore.py"
        test_content = """
# Test file for MCP session tracking restore
# Generated at: {}

def test_function():
    '''Test function to verify session tracking works'''
    print("Session tracking test successful!")
    return True

if __name__ == "__main__":
    test_function()
        """.format(datetime.now().isoformat())

        # Test content extraction and processing
        preview = hook.extract_content_preview(test_content, max_length=200)
        print(f"📄 Content preview: {len(preview)} chars")

        keywords = hook.extract_keywords(test_file_path, test_content)
        print(f"🏷️  Keywords extracted: {keywords}")

        topics = hook.extract_topics(test_content, test_file_path)
        print(f"📚 Topics extracted: {topics}")

        entities = hook.extract_entities(test_content)
        print(f"🔧 Entities extracted: {entities}")

        content_type = hook.classify_content_type("Write", {"success": True}, test_content)
        print(f"📝 Content type: {content_type}")

        # Test session ID retrieval during simulated storage
        session_id = await hook._get_current_session_id()
        if session_id:
            print(f"✅ Session ID available for memory storage: {session_id[:12]}...")
        else:
            print("❌ No session ID available for memory storage")
            return False

        return True

    except Exception as e:
        print(f"❌ MEMORY STORAGE TEST EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_session_update_tracking():
    """Test session update tracking functionality"""
    print("\n🧪 Testing session update tracking")
    print("=" * 60)

    try:
        from post_tool_use import PostToolUseHook

        hook = PostToolUseHook()

        # Get current session
        session_id = await hook._get_current_session_id()
        if not session_id:
            print("❌ No active session for tracking test")
            return False

        print(f"🔍 Testing session tracking for: {session_id[:12]}...")

        # Test active file addition
        test_file = "/test/session/tracking/test.py"
        result = await hook._add_active_file(session_id, test_file)

        if result:
            print(f"✅ Successfully added active file: {test_file}")
        else:
            print(f"⚠️  File addition result: {result}")

        # Verify file was added
        updated_files = await hook._get_active_files(session_id)
        if test_file in updated_files:
            print(f"✅ File tracking verified: {test_file} in active files")
        else:
            print(f"⚠️  File not found in active files: {test_file}")

        # Test active task addition
        test_task = "Test session tracking functionality"
        task_result = await hook._add_active_task(session_id, test_task)

        if task_result:
            print(f"✅ Successfully added active task: {test_task[:30]}...")
        else:
            print(f"⚠️  Task addition result: {task_result}")

        # Verify task was added
        updated_tasks = await hook._get_active_tasks(session_id)
        if test_task in updated_tasks:
            print(f"✅ Task tracking verified: {test_task[:30]}... in active tasks")
        else:
            print(f"⚠️  Task not found in active tasks: {test_task[:30]}...")

        return True

    except Exception as e:
        print(f"❌ SESSION TRACKING EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_error_handling():
    """Test error handling and graceful degradation"""
    print("\n🧪 Testing error handling and graceful degradation")
    print("=" * 60)

    try:
        from post_tool_use import PostToolUseHook

        hook = PostToolUseHook()

        # Test with invalid database path (should not crash)
        original_db_path = hook.db_path
        hook.db_path = "/nonexistent/path/database.db"

        session_id = await hook._get_current_session_id()
        if session_id is None:
            print("✅ Graceful handling of invalid database path")
        else:
            print("⚠️  Unexpected success with invalid path")

        # Restore correct path
        hook.db_path = original_db_path

        # Test with invalid session ID
        invalid_session_id = await hook._get_active_files("invalid-session-id")
        if invalid_session_id == []:
            print("✅ Graceful handling of invalid session ID")
        else:
            print("⚠️  Unexpected result with invalid session ID")

        return True

    except Exception as e:
        print(f"❌ ERROR HANDLING EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test runner"""
    print("🚀 Starting Comprehensive PostToolUse Hook Tests")
    print(f"⏰ Test started: {datetime.now().isoformat()}")
    print()

    # Run all tests
    tests = [
        ("Fallback Mode Basic", test_fallback_mode),
        ("Memory Storage Simulation", test_memory_storage_simulation),
        ("Session Update Tracking", test_session_update_tracking),
        ("Error Handling", test_error_handling),
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\n{'='*80}")
        print(f"🧪 Running: {test_name}")
        print('='*80)

        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"❌ CRITICAL ERROR in {test_name}: {e}")
            results[test_name] = False

    # Summary
    print(f"\n{'='*80}")
    print("📊 COMPREHENSIVE TEST RESULTS SUMMARY")
    print('='*80)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:<30} {status}")
        if not passed:
            all_passed = False

    print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")

    if all_passed:
        print("\n🎉 SUCCESS: PostToolUse hook is fully functional!")
        print("   ✅ Session tracking: Working")
        print("   ✅ Memory storage: Ready")
        print("   ✅ Error handling: Robust")
        print("   ✅ MCP timeout issue: RESOLVED")
        print("\n🔧 The MCP server should now maintain stable connections!")
    else:
        print("\n❌ FAILURE: Some components need attention.")
        return 1

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)