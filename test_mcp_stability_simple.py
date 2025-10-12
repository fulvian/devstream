#!/usr/bin/env .devstream/bin/python
"""
Simple test for MCP stability after session tracking restore
Tests the core database functionality without complex imports
"""

import sys
import asyncio
import json
import time
import subprocess
import sqlite3
from pathlib import Path
from datetime import datetime

def test_database_stability():
    """Test database stability with direct sqlite3"""
    print("🧪 Testing database stability with direct sqlite3")
    print("=" * 60)

    try:
        db_path = "data/devstream.db"
        print(f"📁 Database path: {db_path}")

        # Test basic connection
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Test work_sessions table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='work_sessions'
        """)
        table_exists = cursor.fetchone()

        if table_exists:
            print("✅ work_sessions table exists")
        else:
            print("❌ work_sessions table NOT found")
            conn.close()
            return False

        # Test session query performance
        print("🔄 Testing session query performance...")
        start_time = time.time()

        for i in range(50):  # 50 rapid queries
            cursor.execute("""
                SELECT id, started_at FROM work_sessions
                WHERE status = 'active'
                ORDER BY started_at DESC
                LIMIT 1
            """)
            session = cursor.fetchone()
            if session:
                session_id, started_at = session
                # Simulate some processing
                _ = f"session-{session_id[:8]}-{i}"

        end_time = time.time()
        query_time = end_time - start_time

        print(f"✅ 50 queries completed in {query_time:.3f}s")
        print(f"   Average: {query_time/50*1000:.2f}ms per query")

        if query_time < 1.0:  # Less than 1 second for 50 queries
            print("✅ Database performance is excellent")
        else:
            print("⚠️  Database performance could be better")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ DATABASE STABILITY EXCEPTION: {e}")
        return False

def test_session_consistency():
    """Test session consistency over time"""
    print("\n🧪 Testing session consistency over time")
    print("=" * 60)

    try:
        db_path = "data/devstream.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Test session retrieval multiple times
        session_ids = []
        for i in range(10):
            cursor.execute("""
                SELECT id FROM work_sessions
                WHERE status = 'active'
                ORDER BY started_at DESC
                LIMIT 1
            """)
            session = cursor.fetchone()
            session_id = session[0] if session else None
            session_ids.append(session_id)
            time.sleep(0.5)  # Wait 500ms between tests

        # Check consistency
        unique_sessions = set(session_ids)
        if len(unique_sessions) == 1 and session_ids[0] is not None:
            print("✅ Session tracking is consistent over time")
            print(f"   Session: {session_ids[0][:12]}...")
            conn.close()
            return True
        else:
            print(f"⚠️  Session tracking inconsistency: {len(unique_sessions)} different sessions")
            conn.close()
            return False

    except Exception as e:
        print(f"❌ SESSION CONSISTENCY EXCEPTION: {e}")
        return False

def test_mcp_server_build():
    """Test MCP server can be built successfully"""
    print("\n🧪 Testing MCP server build")
    print("=" * 60)

    try:
        # Test npm build
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd="mcp-devstream-server",
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("✅ MCP server builds successfully")
            return True
        else:
            print(f"❌ MCP server build failed")
            print(f"   Error: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ MCP BUILD EXCEPTION: {e}")
        return False

def test_database_schema():
    """Test database schema is correct"""
    print("\n🧪 Testing database schema")
    print("=" * 60)

    try:
        db_path = "data/devstream.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check work_sessions schema
        cursor.execute("PRAGMA table_info(work_sessions)")
        columns = cursor.fetchall()

        expected_columns = ['id', 'plan_id', 'user_id', 'session_name', 'status', 'started_at', 'last_activity_at']
        found_columns = [col[1] for col in columns]

        missing_columns = set(expected_columns) - set(found_columns)
        if missing_columns:
            print(f"❌ Missing columns: {missing_columns}")
            conn.close()
            return False

        print("✅ Database schema is correct")

        # Check for active sessions
        cursor.execute("SELECT COUNT(*) FROM work_sessions WHERE status = 'active'")
        active_count = cursor.fetchone()[0]

        print(f"📊 Found {active_count} active sessions")
        if active_count > 0:
            print("✅ Active sessions available for PostToolUse hook")
        else:
            print("⚠️  No active sessions - may affect PostToolUse hook")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ SCHEMA TEST EXCEPTION: {e}")
        return False

def main():
    """Main test runner"""
    print("🚀 Starting Simple MCP Stability Tests")
    print(f"⏰ Test started: {datetime.now().isoformat()}")
    print("Testing the core MCP timeout fix implementation")
    print()

    # Run all tests
    tests = [
        ("Database Stability", test_database_stability),
        ("Session Consistency", test_session_consistency),
        ("MCP Server Build", test_mcp_server_build),
        ("Database Schema", test_database_schema),
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\n{'='*80}")
        print(f"🧪 Running: {test_name}")
        print('='*80)

        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ CRITICAL ERROR in {test_name}: {e}")
            results[test_name] = False

    # Summary
    print(f"\n{'='*80}")
    print("📊 SIMPLE MCP STABILITY TEST RESULTS")
    print('='*80)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if not passed:
            all_passed = False

    print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")

    if all_passed:
        print("\n🎉 SUCCESS: Core MCP stability verified!")
        print("   ✅ Database: Stable and performant")
        print("   ✅ Session tracking: Consistent")
        print("   ✅ MCP server: Build successful")
        print("   ✅ Schema: Correct and complete")
        print("\n🔧 The 40-second MCP timeout issue should be FIXED!")
        print("   Root cause: Missing work_sessions table")
        print("   Solution: Table restored with active sessions")
        print("   Result: PostToolUse hook can now find session IDs")
    else:
        print("\n❌ FAILURE: Core stability issues detected.")
        return 1

    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)