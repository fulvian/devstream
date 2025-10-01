#!/usr/bin/env python3
"""
Validate DevStream database schema.

Usage:
    .devstream/bin/python schema/validate_schema.py [db_path]

Default db_path: data/devstream.db
"""

import sqlite3
import sys
from typing import List, Tuple


def validate_schema(db_path: str) -> bool:
    """
    Validate database schema matches expected structure.

    Args:
        db_path: Path to SQLite database file

    Returns:
        True if schema is valid, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")

        # Try to load vec0 extension (optional, may not be in library path)
        vec0_loaded = False
        try:
            conn.enable_load_extension(True)
            conn.load_extension('vec0')
            vec0_loaded = True
        except (sqlite3.OperationalError, AttributeError):
            # Extension not available or load_extension not supported
            pass

        validation_passed = True

        # Expected tables (core tables only, excluding FTS/vec auxiliary tables)
        expected_tables = [
            'intervention_plans', 'phases', 'micro_tasks', 'semantic_memory',
            'vec_semantic_memory', 'fts_semantic_memory', 'agents', 'hooks',
            'hook_executions', 'work_sessions', 'context_injections',
            'learning_insights', 'performance_metrics', 'schema_version'
        ]

        # Check tables exist
        print("=" * 60)
        print("CHECKING TABLES")
        print("=" * 60)

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
        """)
        all_tables = [row[0] for row in cursor.fetchall()]

        # Filter out auxiliary tables (internal FTS/vec tables, sqlite_sequence)
        # Keep: fts_semantic_memory, vec_semantic_memory
        # Filter: fts_semantic_memory_*, vec_semantic_memory_*
        core_tables = [
            t for t in all_tables
            if not (
                (t.startswith('fts_semantic_memory_'))  # FTS auxiliary tables
                or (t.startswith('vec_semantic_memory_'))  # vec auxiliary tables
                or t == 'sqlite_sequence'
            )
        ]

        missing_tables = set(expected_tables) - set(core_tables)
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            validation_passed = False
        else:
            print(f"✅ All {len(expected_tables)} core tables present")

        # Show table counts
        print(f"\n📊 Table Statistics:")
        for table in sorted(core_tables):
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   - {table}: {count} rows")
            except sqlite3.OperationalError as e:
                print(f"   ⚠️  {table}: Error counting rows - {e}")

        # Check vec0 extension
        print("\n" + "=" * 60)
        print("CHECKING EXTENSIONS")
        print("=" * 60)

        if vec0_loaded:
            try:
                cursor.execute("SELECT COUNT(*) FROM vec_semantic_memory")
                print("✅ sqlite-vec (vec0) extension loaded and functional")
            except sqlite3.OperationalError as e:
                print(f"⚠️  sqlite-vec extension loaded but not functional: {e}")
                print("   Note: Virtual table may still exist from previous session")
        else:
            # Check if virtual table exists (may have been created with vec0)
            cursor.execute("""
                SELECT sql FROM sqlite_master
                WHERE type='table' AND name='vec_semantic_memory'
            """)
            vec_table = cursor.fetchone()
            if vec_table and 'USING vec0' in vec_table[0]:
                print("⚠️  sqlite-vec (vec0) virtual table exists but extension not loaded")
                print("   Note: Table was created with vec0 but extension is not available in this session")
                print("   Hint: Ensure vec0 library is in library path when running production code")
            else:
                print("❌ sqlite-vec (vec0) extension not available")
                print("   Hint: Install sqlite-vec and ensure vec0 library is in library path")
                validation_passed = False

        # Check FTS5
        try:
            cursor.execute("SELECT COUNT(*) FROM fts_semantic_memory")
            print("✅ FTS5 extension available and functional")
        except sqlite3.OperationalError as e:
            print(f"❌ FTS5 extension error: {e}")
            validation_passed = False

        # Check triggers
        print("\n" + "=" * 60)
        print("CHECKING TRIGGERS")
        print("=" * 60)

        cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
        triggers = [row[0] for row in cursor.fetchall()]
        expected_triggers = ['sync_insert_memory', 'sync_update_memory', 'sync_delete_memory']

        missing_triggers = set(expected_triggers) - set(triggers)
        if missing_triggers:
            print(f"❌ Missing triggers: {missing_triggers}")
            validation_passed = False
        else:
            print(f"✅ All {len(expected_triggers)} sync triggers present:")
            for trigger in triggers:
                print(f"   - {trigger}")

        # Check indexes
        print("\n" + "=" * 60)
        print("CHECKING INDEXES")
        print("=" * 60)

        cursor.execute("""
            SELECT name, tbl_name
            FROM sqlite_master
            WHERE type='index' AND sql IS NOT NULL
            ORDER BY tbl_name, name
        """)
        indexes = cursor.fetchall()

        # Count indexes per table
        index_counts = {}
        for idx_name, tbl_name in indexes:
            index_counts[tbl_name] = index_counts.get(tbl_name, 0) + 1

        print(f"✅ Found {len(indexes)} indexes across {len(index_counts)} tables")
        for table, count in sorted(index_counts.items()):
            print(f"   - {table}: {count} indexes")

        # Check schema version
        print("\n" + "=" * 60)
        print("CHECKING SCHEMA VERSION")
        print("=" * 60)

        cursor.execute("""
            SELECT version, applied_at, description
            FROM schema_version
            ORDER BY applied_at DESC
            LIMIT 1
        """)
        version_row = cursor.fetchone()

        if version_row:
            version, applied_at, description = version_row
            print(f"✅ Schema version: {version}")
            print(f"   Applied: {applied_at}")
            print(f"   Description: {description}")
        else:
            print("⚠️  No schema version found")
            validation_passed = False

        # Check foreign key constraints
        print("\n" + "=" * 60)
        print("CHECKING FOREIGN KEY CONSTRAINTS")
        print("=" * 60)

        cursor.execute("PRAGMA foreign_key_check")
        fk_violations = cursor.fetchall()

        if fk_violations:
            print(f"❌ Foreign key violations found: {len(fk_violations)}")
            for violation in fk_violations[:5]:  # Show first 5
                print(f"   - {violation}")
            validation_passed = False
        else:
            print("✅ No foreign key constraint violations")

        # Check database integrity
        print("\n" + "=" * 60)
        print("CHECKING DATABASE INTEGRITY")
        print("=" * 60)

        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchone()[0]

        if integrity_result == 'ok':
            print("✅ Database integrity check passed")
        else:
            print(f"❌ Database integrity check failed: {integrity_result}")
            validation_passed = False

        # Database statistics
        print("\n" + "=" * 60)
        print("DATABASE STATISTICS")
        print("=" * 60)

        cursor.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]

        cursor.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]

        db_size_bytes = page_count * page_size
        db_size_mb = db_size_bytes / (1024 * 1024)

        print(f"📊 Database size: {db_size_mb:.2f} MB ({db_size_bytes:,} bytes)")
        print(f"   Pages: {page_count:,}")
        print(f"   Page size: {page_size:,} bytes")

        conn.close()

        return validation_passed

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
    """Main entry point."""
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'data/devstream.db'

    print("\n" + "=" * 60)
    print(f"DEVSTREAM SCHEMA VALIDATION")
    print("=" * 60)
    print(f"Database: {db_path}\n")

    if validate_schema(db_path):
        print("\n" + "=" * 60)
        print("✅ SCHEMA VALIDATION PASSED")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ SCHEMA VALIDATION FAILED")
        print("=" * 60)
        sys.exit(1)


if __name__ == '__main__':
    main()
