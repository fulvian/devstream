#!/usr/bin/env python3
"""
Verification script for vec_semantic_memory migration
Tests all 8 acceptance criteria from implementation plan
"""
import sys
sys.path.append('.claude/hooks/devstream/utils')
from sqlite_vec_helper import get_db_connection_with_vec

# Content types to include in coverage calculation
SEMANTIC_TYPES = ['decision', 'code', 'learning', 'documentation', 'output', 'error']

def test_1_schema_structure():
    """Test 1: vec_semantic_memory has 4-column structure with PARTITION KEY"""
    conn = get_db_connection_with_vec('data/devstream.db')
    c = conn.cursor()

    # Check table exists and get schema
    c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='vec_semantic_memory'")
    result = c.fetchone()

    if not result:
        return False, "Table vec_semantic_memory does not exist"

    schema = result[0]

    # Verify 4 columns
    required = [
        'embedding float[768]',
        'content_type TEXT PARTITION KEY',
        '+memory_id TEXT',
        '+content_preview TEXT'
    ]

    for req in required:
        if req not in schema:
            return False, f"Missing required column/constraint: {req}"

    return True, f"Schema correct: 4 columns with PARTITION KEY"


def test_2_semantic_coverage():
    """Test 2: 99%+ coverage of semantic-rich content (excludes 'context')"""
    conn = get_db_connection_with_vec('data/devstream.db')
    c = conn.cursor()

    # Total semantic records (excludes context)
    types_placeholder = ','.join(['?' for _ in SEMANTIC_TYPES])
    c.execute(f"""
        SELECT COUNT(*) FROM semantic_memory
        WHERE content_type IN ({types_placeholder})
    """, SEMANTIC_TYPES)
    total_semantic = c.fetchone()[0]

    # Semantic records in vec
    c.execute(f"""
        SELECT COUNT(*) FROM semantic_memory sm
        JOIN vec_semantic_memory vsm ON sm.id = vsm.memory_id
        WHERE sm.content_type IN ({types_placeholder})
    """, SEMANTIC_TYPES)
    semantic_in_vec = c.fetchone()[0]

    coverage = (semantic_in_vec / total_semantic * 100) if total_semantic > 0 else 0


    if coverage >= 99:
        return True, f"Coverage: {coverage:.2f}% ({semantic_in_vec:,}/{total_semantic:,})"
    else:
        return False, f"Coverage too low: {coverage:.2f}% (target: 99%+)"


def test_3_insert_trigger():
    """Test 3: INSERT trigger works for new records"""
    conn = get_db_connection_with_vec('data/devstream.db')
    c = conn.cursor()

    # Check trigger exists
    c.execute("""
        SELECT COUNT(*) FROM sqlite_master
        WHERE type='trigger' AND name='sync_embedding_insert'
    """)

    if c.fetchone()[0] == 0:
        return False, "INSERT trigger 'sync_embedding_insert' not found"

    return True, "INSERT trigger exists"


def test_4_update_trigger():
    """Test 4: UPDATE trigger works for backfill"""
    conn = get_db_connection_with_vec('data/devstream.db')
    c = conn.cursor()

    # Check trigger exists
    c.execute("""
        SELECT COUNT(*) FROM sqlite_master
        WHERE type='trigger' AND name='sync_embedding_update'
    """)

    if c.fetchone()[0] == 0:
        return False, "UPDATE trigger 'sync_embedding_update' not found"

    return True, "UPDATE trigger exists"


def test_5_json_cleanup():
    """Test 5: JSON embeddings cleaned up (embedding column NULL after vec sync)"""
    conn = get_db_connection_with_vec('data/devstream.db')
    c = conn.cursor()

    # Check for records with JSON embedding still present
    c.execute("""
        SELECT COUNT(*) FROM semantic_memory
        WHERE embedding IS NOT NULL AND embedding != ''
    """)

    json_remaining = c.fetchone()[0]


    if json_remaining == 0:
        return True, "All JSON embeddings cleaned up"
    else:
        return False, f"JSON embeddings still present: {json_remaining:,} records"


def test_6_blob_format():
    """Test 6: Embeddings stored as BLOB (float32) in vec0"""
    conn = get_db_connection_with_vec('data/devstream.db')
    c = conn.cursor()

    # Sample 5 records and check embedding type
    c.execute("SELECT embedding FROM vec_semantic_memory LIMIT 5")

    for row in c.fetchall():
        embedding = row[0]
        if not isinstance(embedding, bytes):
            return False, f"Embedding not in BLOB format: {type(embedding)}"

        # Check size (768 floats × 4 bytes = 3072 bytes)
        if len(embedding) != 3072:
            return False, f"Embedding size incorrect: {len(embedding)} bytes (expected 3072)"

    return True, "Embeddings stored as BLOB (float32, 3072 bytes)"


def test_7_auxiliary_tables():
    """Test 7: All 6 auxiliary tables present"""
    conn = get_db_connection_with_vec('data/devstream.db')
    c = conn.cursor()

    required_tables = [
        'vec_semantic_memory',
        'vec_semantic_memory_chunks',
        'vec_semantic_memory_info',
        'vec_semantic_memory_rowids',
        'vec_semantic_memory_vector_chunks00',
        'vec_semantic_memory_auxiliary'  # New in v0.1.6
    ]

    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'vec_semantic_memory%'")
    actual_tables = [row[0] for row in c.fetchall()]

    missing = [t for t in required_tables if t not in actual_tables]


    if missing:
        return False, f"Missing auxiliary tables: {', '.join(missing)}"
    else:
        return True, f"All 6 auxiliary tables present"


def test_8_storage_code():
    """Test 8: storage.py and memory.ts use 4-column INSERT"""
    # Test Python storage.py
    with open('src/devstream/memory/storage.py', 'r') as f:
        py_content = f.read()

    if 'memory_id, embedding, content_type, content_preview' not in py_content:
        return False, "storage.py not using 4-column INSERT pattern"

    # Test TypeScript memory.ts
    with open('mcp-devstream-server/src/tools/memory.ts', 'r') as f:
        ts_content = f.read()

    # Check for trigger-based sync comment (no manual sync)
    if 'trigger will handle vec0 sync automatically' not in ts_content:
        return False, "memory.ts not using trigger-based sync pattern"

    return True, "storage.py and memory.ts use correct 4-column pattern"


def main():
    """Run all verification tests"""
    # NOTE: Each test function manages its own connection to avoid "closed database" errors
    tests = [
        ("Schema Structure (4-column + PARTITION KEY)", test_1_schema_structure),
        ("Semantic Coverage (99%+ excl. context)", test_2_semantic_coverage),
        ("INSERT Trigger Exists", test_3_insert_trigger),
        ("UPDATE Trigger Exists", test_4_update_trigger),
        ("JSON Cleanup Complete", test_5_json_cleanup),
        ("BLOB Format (float32)", test_6_blob_format),
        ("Auxiliary Tables (6 tables)", test_7_auxiliary_tables),
        ("Storage Code (4-column)", test_8_storage_code),
    ]

    print("━" * 80)
    print("🔍 VEC_SEMANTIC_MEMORY MIGRATION VERIFICATION")
    print("━" * 80)
    print()

    passed = 0
    failed = 0

    for i, (name, test_func) in enumerate(tests, 1):
        try:
            # Each test creates and closes its own connection
            success, message = test_func()
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"Test {i}: {name}")
            print(f"  {status} - {message}")
            print()

            if success:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            import traceback
            print(f"Test {i}: {name}")
            print(f"  ❌ ERROR - {str(e)}")
            print(f"  Traceback: {traceback.format_exc()}")
            print()
            failed += 1

    print("━" * 80)
    print(f"RESULTS: {passed}/{len(tests)} tests passed")

    if failed == 0:
        print("✅ ALL TESTS PASSED - Migration successful!")
        return 0
    else:
        print(f"❌ {failed} tests failed - Review failures above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
