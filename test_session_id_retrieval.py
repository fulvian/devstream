#!/usr/bin/env .devstream/bin/python
"""
Test script for PostToolUse hook _get_current_session_id() method
Tests the critical session ID retrieval functionality after work_sessions table restore
"""

import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime

# Add hook directory to path
sys.path.insert(0, str(Path(__file__).parent / '.claude' / 'hooks' / 'devstream' / 'memory'))

async def test_session_id_retrieval():
    """Test the _get_current_session_id method directly"""
    print("🧪 Testing PostToolUse hook _get_current_session_id() method")
    print("=" * 60)

    try:
        # Import PostToolUse hook
        from post_tool_use import PostToolUseHook

        # Create hook instance
        hook = PostToolUseHook()

        print(f"📁 Database path: {hook.db_path}")

        # Test session ID retrieval
        print("🔍 Testing _get_current_session_id()...")
        session_id = await hook._get_current_session_id()

        if session_id:
            print(f"✅ SUCCESS: Found active session: {session_id}")
            print(f"   Session ID length: {len(session_id)}")
            print(f"   Session ID prefix: {session_id[:8]}...")
        else:
            print("❌ FAILED: No active session found")
            return False

        # Test multiple consecutive calls
        print("\n🔄 Testing multiple consecutive calls...")
        for i in range(3):
            session_id_test = await hook._get_current_session_id()
            if session_id_test == session_id:
                print(f"   Call {i+1}: ✅ Consistent session ID")
            else:
                print(f"   Call {i+1}: ❌ Inconsistent session ID: {session_id_test}")
                return False

        return True

    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_database_direct_query():
    """Test direct database query to verify work_sessions table"""
    print("\n🧪 Testing direct database query")
    print("=" * 60)

    try:
        import aiosqlite

        db_path = "data/devstream.db"
        print(f"📁 Database path: {db_path}")

        async with aiosqlite.connect(db_path) as db:
            # Test table exists
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='work_sessions'"
            )
            table_exists = await cursor.fetchone()

            if table_exists:
                print("✅ work_sessions table exists")
            else:
                print("❌ work_sessions table NOT found")
                return False

            # Test active sessions
            cursor = await db.execute("""
                SELECT id, status, started_at, last_activity_at
                FROM work_sessions
                WHERE status = 'active'
                ORDER BY started_at DESC
                LIMIT 3
            """)

            sessions = await cursor.fetchall()

            print(f"📊 Found {len(sessions)} active sessions:")
            for i, (sid, status, started, last_activity) in enumerate(sessions, 1):
                print(f"   {i}. {sid[:12]}... ({status})")
                print(f"      Started: {started}")
                print(f"      Last activity: {last_activity}")

            if not sessions:
                print("⚠️  No active sessions found")
                return False

        return True

    except Exception as e:
        print(f"❌ DATABASE EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test runner"""
    print("🚀 Starting PostToolUse Hook Session ID Tests")
    print(f"⏰ Test started: {datetime.now().isoformat()}")
    print()

    # Test 1: Direct database query
    db_success = await test_database_direct_query()

    # Test 2: Hook method functionality
    hook_success = await test_session_id_retrieval()

    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Database Query: {'✅ PASS' if db_success else '❌ FAIL'}")
    print(f"Hook Method:    {'✅ PASS' if hook_success else '❌ FAIL'}")

    overall_success = db_success and hook_success
    print(f"Overall:        {'✅ ALL TESTS PASSED' if overall_success else '❌ TESTS FAILED'}")

    if overall_success:
        print("\n🎉 SUCCESS: PostToolUse hook session tracking is working correctly!")
        print("   The MCP timeout issue should now be resolved.")
    else:
        print("\n❌ FAILURE: Issues found that need to be addressed.")
        return 1

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)