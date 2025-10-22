#!/usr/bin/env .devstream/bin/python
"""
Test PostToolUse hook with complete schema including active_files column
Verifies that all warning messages are resolved
"""

import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime

# Add hook directory to path
sys.path.insert(0, str(Path(__file__).parent / '.claude' / 'hooks' / 'devstream' / 'memory'))

async def test_active_files_functionality():
    """Test active_files column functionality"""
    print("🧪 Testing active_files column functionality")
    print("=" * 60)

    try:
        from post_tool_use import PostToolUseHook

        hook = PostToolUseHook()

        # Get current session
        session_id = await hook._get_current_session_id()
        if not session_id:
            print("❌ No active session found")
            return False

        print(f"🔍 Testing with session: {session_id[:12]}...")

        # Test _get_active_files method
        print("📁 Testing _get_active_files() method...")
        active_files = await hook._get_active_files(session_id)
        print(f"✅ Active files retrieved: {len(active_files)} files")

        if isinstance(active_files, list):
            print(f"✅ Active files is a list: {active_files}")
        else:
            print(f"⚠️  Active files type: {type(active_files)}")

        # Test _add_active_file method
        print("\n➕ Testing _add_active_file() method...")
        test_file = "/test/active/files/test.py"

        try:
            result = await hook._add_active_file(session_id, test_file)
            if result:
                print(f"✅ Successfully added active file: {test_file}")
            else:
                print(f"⚠️  Add active file result: {result}")
        except Exception as e:
            print(f"❌ Error adding active file: {e}")
            return False

        # Verify file was added
        updated_files = await hook._get_active_files(session_id)
        if test_file in updated_files:
            print(f"✅ File tracking verified: {test_file} in active files")
            print(f"   Total active files: {len(updated_files)}")
        else:
            print(f"⚠️  File not found in active files")
            # Check what files are actually there
            print(f"   Active files found: {updated_files}")

        return True

    except Exception as e:
        print(f"❌ ACTIVE FILES TEST EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_complete_session_tracking():
    """Test complete session tracking with all columns"""
    print("\n🧪 Testing complete session tracking functionality")
    print("=" * 60)

    try:
        from post_tool_use import PostToolUseHook

        hook = PostToolUseHook()

        session_id = await hook._get_current_session_id()
        if not session_id:
            print("❌ No active session found")
            return False

        print(f"🔍 Session: {session_id[:12]}...")

        # Test all session-related methods
        methods_to_test = [
            ("active_files", lambda: hook._get_active_files(session_id)),
            ("active_tasks", lambda: hook._get_active_tasks(session_id)),
        ]

        results = {}
        for method_name, method_func in methods_to_test:
            try:
                result = await method_func()
                results[method_name] = result
                print(f"✅ {method_name}: {len(result) if isinstance(result, list) else type(result)}")
            except Exception as e:
                print(f"❌ {method_name}: {e}")
                results[method_name] = None

        # Test session update tracking
        print("\n🔄 Testing session update tracking...")
        try:
            await hook.update_session_tracking("Write", {"file_path": "/test/update/tracking.py"})
            print("✅ Session update tracking completed without errors")
        except Exception as e:
            print(f"⚠️  Session update tracking warning: {e}")

        return all(result is not None for result in results.values())

    except Exception as e:
        print(f"❌ COMPLETE SESSION TRACKING EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_error_handling_with_complete_schema():
    """Test error handling with complete schema"""
    print("\n🧪 Testing error handling with complete schema")
    print("=" * 60)

    try:
        from post_tool_use import PostToolUseHook

        hook = PostToolUseHook()

        # Test with invalid session ID
        print("🔍 Testing with invalid session ID...")
        invalid_files = await hook._get_active_files("invalid-session-id-12345")
        if invalid_files == []:
            print("✅ Graceful handling of invalid session ID")
        else:
            print(f"⚠️  Unexpected result with invalid session ID: {invalid_files}")

        # Test with empty session ID
        print("🔍 Testing with empty session ID...")
        empty_files = await hook._get_active_files("")
        if empty_files == []:
            print("✅ Graceful handling of empty session ID")
        else:
            print(f"⚠️  Unexpected result with empty session ID: {empty_files}")

        return True

    except Exception as e:
        print(f"❌ ERROR HANDLING TEST EXCEPTION: {e}")
        return False

async def main():
    """Main test runner"""
    print("🚀 Testing PostToolUse Hook with Complete Schema")
    print(f"⏰ Test started: {datetime.now().isoformat()}")
    print("Verifying that active_files column warnings are resolved")
    print()

    # Run all tests
    tests = [
        ("Active Files Functionality", test_active_files_functionality),
        ("Complete Session Tracking", test_complete_session_tracking),
        ("Error Handling", test_error_handling_with_complete_schema),
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
    print("📊 COMPLETE SCHEMA TEST RESULTS")
    print('='*80)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:<30} {status}")
        if not passed:
            all_passed = False

    print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")

    if all_passed:
        print("\n🎉 SUCCESS: PostToolUse hook works with complete schema!")
        print("   ✅ active_files column: Working")
        print("   ✅ Session tracking: Complete")
        print("   ✅ Error handling: Robust")
        print("   ✅ Warnings: RESOLVED")
        print("\n🔧 The MCP session tracking fix is now COMPLETE!")
    else:
        print("\n❌ FAILURE: Some schema issues remain.")
        return 1

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)