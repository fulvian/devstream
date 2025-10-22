#!/usr/bin/env python3
"""
DevStream Database Setup Script

Purpose: Initialize SQLite database from schema.sql with comprehensive validation.

Features:
- Schema loading and execution
- sqlite-vec extension support
- Comprehensive verification (tables, indexes, triggers, virtual tables)
- Error handling with rollback
- CLI with multiple options

Usage:
    .devstream/bin/python scripts/setup-db.py [OPTIONS]

Examples:
    .devstream/bin/python scripts/setup-db.py
    .devstream/bin/python scripts/setup-db.py --force --verbose
    .devstream/bin/python scripts/setup-db.py --db-path /custom/path/db.db
"""

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer() if "--json" in sys.argv else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class SchemaLoadError(Exception):
    """Raised when schema loading fails."""
    pass


class DatabaseSetupError(Exception):
    """Raised when database setup fails."""
    pass


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments namespace

    Note:
        Supports custom schema/db paths, force overwrite, and verbose mode
    """
    parser = argparse.ArgumentParser(
        description="Initialize DevStream SQLite database from schema.sql",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Standard setup
  %(prog)s --force --verbose                  # Force overwrite with detailed output
  %(prog)s --schema-file custom.sql           # Use custom schema file
  %(prog)s --db-path /tmp/devstream.db        # Custom database location
        """,
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite existing database (no confirmation prompt)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output with detailed logging",
    )
    parser.add_argument(
        "--schema-file",
        type=Path,
        default=Path("schema/schema.sql"),
        help="Path to schema.sql file (default: schema/schema.sql)",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("data/devstream.db"),
        help="Path to database file (default: data/devstream.db)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output logs in JSON format",
    )
    return parser.parse_args()


def read_schema_file(schema_path: Path) -> str:
    """
    Read and validate schema.sql file.

    Args:
        schema_path: Path to schema.sql file

    Returns:
        Full schema SQL content

    Raises:
        SchemaLoadError: If file doesn't exist or can't be read
    """
    if not schema_path.exists():
        raise SchemaLoadError(f"Schema file not found: {schema_path}")

    if not schema_path.is_file():
        raise SchemaLoadError(f"Schema path is not a file: {schema_path}")

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            raise SchemaLoadError("Schema file is empty")

        logger.info("schema_loaded", path=str(schema_path), size_bytes=len(content))
        return content

    except IOError as e:
        raise SchemaLoadError(f"Failed to read schema file: {e}")


def check_database_exists(db_path: Path, force: bool) -> bool:
    """
    Check if database exists and prompt for overwrite confirmation.

    Args:
        db_path: Path to database file
        force: If True, skip confirmation prompt

    Returns:
        True if should proceed with overwrite, False otherwise

    Note:
        If force=False and database exists, prompts user for confirmation
    """
    if not db_path.exists():
        return True

    if force:
        logger.warning("database_exists_force_overwrite", path=str(db_path))
        return True

    print(f"\n⚠️  Database already exists: {db_path}")
    print("This will DELETE all existing data.")
    response = input("Continue? [y/N]: ").strip().lower()

    if response not in ("y", "yes"):
        logger.info("setup_cancelled_by_user")
        return False

    logger.info("user_confirmed_overwrite")
    return True


def create_database_directory(db_path: Path) -> None:
    """
    Create parent directory for database if it doesn't exist.

    Args:
        db_path: Path to database file

    Raises:
        DatabaseSetupError: If directory creation fails
    """
    db_dir = db_path.parent
    if not db_dir.exists():
        try:
            db_dir.mkdir(parents=True, exist_ok=True)
            logger.info("directory_created", path=str(db_dir))
        except OSError as e:
            raise DatabaseSetupError(f"Failed to create directory {db_dir}: {e}")


def load_sqlite_vec_extension(conn: sqlite3.Connection) -> bool:
    """
    Load sqlite-vec extension for vector search using Context7-compliant method.

    Args:
        conn: SQLite database connection

    Returns:
        True if extension loaded successfully, False otherwise

    Note:
        Context7 best practice: Use sqlite_vec.load() instead of load_extension()
        Not a fatal error if extension fails to load (virtual table creation will fail later)
    """
    try:
        # Context7-compliant approach: Use sqlite_vec module instead of load_extension
        import sqlite_vec

        # Enable extension loading temporarily for Context7 approach
        conn.enable_load_extension(True)

        # Try Context7-compliant loading first
        try:
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)

            # Verify vec_version() function works
            vec_version = conn.execute('select vec_version()').fetchone()[0]
            logger.info("sqlite_vec_loaded", version=vec_version, method="Context7 sqlite_vec.load()")
            return True

        except Exception as vec_e:
            logger.warning("sqlite_vec_context7_failed", error=str(vec_e))
            conn.enable_load_extension(False)

            # Fallback: try traditional extension loading
            extension_names = ["vec0", "vector0", "sqlite-vec"]
            for ext_name in extension_names:
                try:
                    conn.load_extension(ext_name)
                    logger.info("sqlite_vec_loaded", extension=ext_name, method="Traditional load_extension")
                    return True
                except sqlite3.OperationalError:
                    continue

        logger.warning(
            "sqlite_vec_not_loaded",
            message="Vector search will not be available - both Context7 and traditional methods failed",
            attempted_names=extension_names,
            context7_error=str(vec_e) if 'vec_e' in locals() else "N/A"
        )
        return False

    except ImportError:
        logger.warning("sqlite_vec_module_not_available", message="sqlite-vec package not installed")
        return False
    except sqlite3.OperationalError as e:
        logger.warning("sqlite_vec_load_failed", error=str(e))
        return False
    except Exception as e:
        logger.error("sqlite_vec_unexpected_error", error=str(e))
        return False
    finally:
        try:
            conn.enable_load_extension(False)
        except:
            pass


def execute_schema(conn: sqlite3.Connection, schema_sql: str, vec_loaded: bool) -> None:
    """
    Execute schema.sql using executescript().

    Args:
        conn: SQLite database connection
        schema_sql: Full schema SQL content
        vec_loaded: Whether sqlite-vec extension was loaded successfully

    Raises:
        DatabaseSetupError: If schema execution fails

    Note:
        Uses executescript() to handle multi-statement execution.
        If vec_loaded=False, removes vec0 virtual table creation from schema.
    """
    try:
        # If vec0 extension not loaded, remove vec_semantic_memory virtual table
        if not vec_loaded:
            logger.warning("removing_vec0_virtual_table_from_schema")
            # Remove CREATE VIRTUAL TABLE vec_semantic_memory block
            import re
            schema_sql = re.sub(
                r'CREATE VIRTUAL TABLE IF NOT EXISTS vec_semantic_memory USING vec0\([^;]+\);',
                '-- vec0 extension not available, virtual table removed',
                schema_sql,
                flags=re.DOTALL
            )
            # Remove vec-related triggers
            schema_sql = re.sub(
                r'INSERT INTO vec_semantic_memory[^;]+;',
                '-- vec0 insert removed',
                schema_sql,
                flags=re.DOTALL
            )
            schema_sql = re.sub(
                r'DELETE FROM vec_semantic_memory[^;]+;',
                '-- vec0 delete removed',
                schema_sql,
                flags=re.DOTALL
            )

        cursor = conn.cursor()
        cursor.executescript(schema_sql)
        conn.commit()
        logger.info("schema_executed_successfully")

    except sqlite3.Error as e:
        conn.rollback()
        raise DatabaseSetupError(f"Failed to execute schema: {e}")


def verify_tables(conn: sqlite3.Connection) -> List[str]:
    """
    Verify core tables exist in database.

    Args:
        conn: SQLite database connection

    Returns:
        List of table names found

    Raises:
        DatabaseSetupError: If verification query fails

    Note:
        Expected core tables: 14 (excluding virtual tables)
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name NOT LIKE 'sqlite_%'
              AND name NOT LIKE 'vec_%'
              AND name NOT LIKE 'fts_%'
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        logger.info("tables_verified", count=len(tables), tables=tables)
        return tables

    except sqlite3.Error as e:
        raise DatabaseSetupError(f"Failed to verify tables: {e}")


def verify_virtual_tables(conn: sqlite3.Connection) -> Dict[str, str]:
    """
    Verify virtual tables (vec0, FTS5) exist and get their types.

    Args:
        conn: SQLite database connection

    Returns:
        Dictionary mapping virtual table name to type

    Note:
        Expected virtual tables: vec_semantic_memory (vec0), fts_semantic_memory (fts5)
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, sql
            FROM sqlite_master
            WHERE type='table'
              AND (name LIKE 'vec_%' OR name LIKE 'fts_%')
            ORDER BY name
        """)

        virtual_tables = {}
        for row in cursor.fetchall():
            name = row[0]
            sql = row[1] or ""

            if "USING vec0" in sql.upper():
                table_type = "vec0 (vector search)"
            elif "USING fts5" in sql.upper():
                table_type = "fts5 (full-text search)"
            else:
                table_type = "unknown"

            virtual_tables[name] = table_type

        logger.info("virtual_tables_verified", count=len(virtual_tables), tables=virtual_tables)
        return virtual_tables

    except sqlite3.Error as e:
        logger.warning("virtual_tables_check_failed", error=str(e))
        return {}


def verify_triggers(conn: sqlite3.Connection) -> List[str]:
    """
    Verify triggers exist for automatic sync between tables.

    Args:
        conn: SQLite database connection

    Returns:
        List of trigger names found

    Note:
        Expected triggers: 3 (sync_insert_memory, sync_update_memory, sync_delete_memory)
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='trigger'
            ORDER BY name
        """)
        triggers = [row[0] for row in cursor.fetchall()]
        logger.info("triggers_verified", count=len(triggers), triggers=triggers)
        return triggers

    except sqlite3.Error as e:
        raise DatabaseSetupError(f"Failed to verify triggers: {e}")


def verify_indexes(conn: sqlite3.Connection) -> List[str]:
    """
    Verify indexes exist for performance optimization.

    Args:
        conn: SQLite database connection

    Returns:
        List of index names found

    Note:
        Expected indexes: 37 (defined in schema.sql)
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='index'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        logger.info("indexes_verified", count=len(indexes))
        return indexes

    except sqlite3.Error as e:
        raise DatabaseSetupError(f"Failed to verify indexes: {e}")


def verify_schema_version(conn: sqlite3.Connection) -> Optional[str]:
    """
    Verify schema_version table contains initial version record.

    Args:
        conn: SQLite database connection

    Returns:
        Schema version string if found, None otherwise

    Note:
        Initial version should be '2.1.0'
    """
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT version, description FROM schema_version ORDER BY applied_at DESC LIMIT 1")
        row = cursor.fetchone()

        if row:
            version: str = row[0]
            description: str = row[1]
            logger.info("schema_version_verified", version=version, description=description)
            return version
        else:
            logger.warning("schema_version_not_found")
            return None

    except sqlite3.Error as e:
        logger.warning("schema_version_check_failed", error=str(e))
        return None


def ensure_context7_tables(conn: sqlite3.Connection) -> None:
    """
    Ensure Context7-era tables and columns required by hooks exist.

    Currently enforces the schema for:
      - sessions (work session tracking used by SessionStartHook)
      - implementation_plans (needed by plan management hooks)
      - semantic_memory (direct DB access used by bootstrap and hooks)
    """
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables: Set[str] = {row[0] for row in cursor.fetchall()}

    updated_tables: List[str] = []

    # Ensure sessions table has expected columns
    required_session_columns = {
        "id",
        "tokens_used",
        "status",
        "started_at",
        "ended_at",
        "files_modified",
        "tasks_completed",
        "metadata",
    }
    recreate_sessions = False

    if "sessions" not in existing_tables:
        logger.info("sessions_table_missing", action="create")
        recreate_sessions = True
    else:
        cursor.execute("PRAGMA table_info(sessions)")
        current_columns = {row[1] for row in cursor.fetchall()}
        if not required_session_columns.issubset(current_columns):
            logger.warning(
                "sessions_table_outdated",
                missing=list(required_session_columns - current_columns),
                existing=list(current_columns),
            )
            cursor.execute("DROP TABLE IF EXISTS sessions")
            recreate_sessions = True

    if recreate_sessions:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                tokens_used INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                started_at TEXT NOT NULL,
                ended_at TEXT,
                files_modified INTEGER DEFAULT 0,
                tasks_completed INTEGER DEFAULT 0,
                metadata TEXT
            )
            """
        )
        updated_tables.append("sessions")

    # Ensure supporting indexes exist (idempotent)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at)")

    # Ensure implementation_plans table schema
    required_impl_columns = {
        "id",
        "task_id",
        "model_type",
        "plan_title",
        "plan_content",
        "plan_status",
        "created_at",
        "updated_at",
        "metadata",
    }
    recreate_impl = False

    if "implementation_plans" not in existing_tables:
        logger.info("implementation_plans_table_missing", action="create")
        recreate_impl = True
    else:
        cursor.execute("PRAGMA table_info(implementation_plans)")
        current_columns = {row[1] for row in cursor.fetchall()}
        if not required_impl_columns.issubset(current_columns):
            logger.warning(
                "implementation_plans_table_outdated",
                missing=list(required_impl_columns - current_columns),
                existing=list(current_columns),
            )
            cursor.execute("DROP TABLE IF EXISTS implementation_plans")
            recreate_impl = True

    if recreate_impl:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS implementation_plans (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                model_type TEXT NOT NULL,
                plan_title TEXT NOT NULL,
                plan_content TEXT,
                plan_status TEXT DEFAULT 'draft',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                metadata TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks (id)
            )
            """
        )
        updated_tables.append("implementation_plans")

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_implementation_plans_task_id ON implementation_plans(task_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_implementation_plans_status ON implementation_plans(plan_status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_implementation_plans_model_type ON implementation_plans(model_type)"
    )

    # Ensure semantic_memory table schema aligns with direct_client expectations
    required_semantic_columns: Dict[str, str] = {
        "content": "TEXT NOT NULL",
        "content_type": "TEXT NOT NULL",
        "keywords": "TEXT",
        "session_id": "TEXT",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "access_count": "INTEGER DEFAULT 0",
        "relevance_score": "REAL DEFAULT 1.0",
        "importance_score": "REAL DEFAULT 0.0",
        "last_accessed_at": "TIMESTAMP",
        "metadata": "TEXT",
        "source": "TEXT",
        "embedding_blob": "BLOB",
        "embedding_model": "TEXT",
        "embedding_dimension": "INTEGER",
    }

    semantic_columns_added: List[str] = []

    if "semantic_memory" not in existing_tables:
        logger.info("semantic_memory_table_missing", action="create")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS semantic_memory (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL,
                keywords TEXT,
                session_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                relevance_score REAL DEFAULT 1.0,
                importance_score REAL DEFAULT 0.0,
                last_accessed_at TIMESTAMP,
                metadata TEXT,
                source TEXT,
                embedding_blob BLOB,
                embedding_model TEXT,
                embedding_dimension INTEGER
            )
            """
        )
        updated_tables.append("semantic_memory")
    else:
        cursor.execute("PRAGMA table_info(semantic_memory)")
        current_columns = {row[1] for row in cursor.fetchall()}
        for column, definition in required_semantic_columns.items():
            if column not in current_columns:
                cursor.execute(f"ALTER TABLE semantic_memory ADD COLUMN {column} {definition}")
                semantic_columns_added.append(column)

    if semantic_columns_added:
        logger.info(
            "semantic_memory_columns_added",
            missing=semantic_columns_added
        )
        updated_tables.append("semantic_memory")

    # Ensure FTS table matches expected layout (drop/recreate if outdated)
    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='fts_semantic_memory'"
    )
    fts_definition_row = cursor.fetchone()
    expected_tokens = ("content", "content_type", "memory_id", "created_at")
    needs_fts_refresh = False
    if not fts_definition_row or fts_definition_row[0] is None:
        needs_fts_refresh = True
    else:
        definition_sql = fts_definition_row[0]
        if any(token not in definition_sql for token in expected_tokens) or "keywords" in definition_sql:
            needs_fts_refresh = True

    if needs_fts_refresh:
        cursor.execute("DROP TABLE IF EXISTS fts_semantic_memory")
        cursor.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_semantic_memory USING fts5(
                content,
                content_type UNINDEXED,
                memory_id UNINDEXED,
                created_at UNINDEXED
            )
            """
        )
        updated_tables.append("fts_semantic_memory")

    if updated_tables:
        conn.commit()
        logger.info("context7_tables_updated", tables=updated_tables)
    else:
        logger.info("context7_tables_already_current")


def print_summary_report(
    tables: List[str],
    virtual_tables: Dict[str, str],
    triggers: List[str],
    indexes: List[str],
    schema_version: Optional[str],
    vec_loaded: bool,
) -> None:
    """
    Print comprehensive setup summary report.

    Args:
        tables: List of core table names
        virtual_tables: Dictionary of virtual table names to types
        triggers: List of trigger names
        indexes: List of index names
        schema_version: Schema version string or None
        vec_loaded: Whether sqlite-vec extension was loaded

    Note:
        Expected counts: 12 regular tables, 1-2 virtual tables (depending on vec0),
        3 triggers, 37 indexes. FTS5 creates additional internal tables (_config, _data, etc.)
    """
    print("\n" + "=" * 80)
    print("📊 DevStream Database Setup Summary")
    print("=" * 80)

    # Core Tables
    print(f"\n✅ Core Tables ({len(tables)}/12 expected):")
    for table in tables:
        print(f"   - {table}")

    # Virtual Tables (FTS5 creates multiple internal tables per virtual table)
    fts_count = sum(1 for name in virtual_tables.keys() if name.startswith('fts_semantic_memory'))
    vec_count = sum(1 for name in virtual_tables.keys() if name.startswith('vec_semantic_memory'))
    expected_virtual = 2 if vec_loaded else 1
    print(f"\n✅ Virtual Tables ({fts_count + vec_count} FTS5 tables, {expected_virtual} virtual table(s) expected):")
    print(f"   FTS5 (full-text search): {fts_count} internal tables")
    if vec_count > 0:
        print(f"   vec0 (vector search): {vec_count} internal tables")
    else:
        print(f"   vec0 (vector search): Not available (extension not loaded)")

    # Triggers
    print(f"\n✅ Triggers ({len(triggers)}/3 expected):")
    for trigger in triggers:
        print(f"   - {trigger}")

    # Indexes
    print(f"\n✅ Indexes ({len(indexes)}/37 expected)")

    # Schema Version
    print(f"\n✅ Schema Version: {schema_version or 'NOT FOUND'}")

    print("\n" + "=" * 80)

    # Validation Warnings
    warnings = []
    if len(tables) != 12:
        warnings.append(f"Expected 12 core tables, found {len(tables)}")
    if len(triggers) != 3:
        warnings.append(f"Expected 3 triggers, found {len(triggers)}")
    if len(indexes) != 37:
        warnings.append(f"Expected 37 indexes, found {len(indexes)}")
    if not schema_version:
        warnings.append("Schema version not found in database")

    if warnings:
        for warning in warnings:
            print(f"⚠️  Warning: {warning}")
        print("=" * 80 + "\n")
    else:
        print("✅ All validation checks passed!")
        print("=" * 80 + "\n")


def setup_database(
    schema_path: Path,
    db_path: Path,
    force: bool = False,
    verbose: bool = False,
) -> Tuple[bool, str]:
    """
    Main database setup orchestration function.

    Args:
        schema_path: Path to schema.sql file
        db_path: Path to database file to create
        force: Skip confirmation prompts
        verbose: Enable verbose logging

    Returns:
        Tuple of (success: bool, message: str)

    Raises:
        SchemaLoadError: If schema file can't be loaded
        DatabaseSetupError: If database setup fails

    Note:
        Performs full setup: load schema, create DB, execute schema, verify
    """
    try:
        # Step 1: Read schema file
        logger.info("step_1_reading_schema", path=str(schema_path))
        schema_sql = read_schema_file(schema_path)

        # Step 2: Check if database exists
        logger.info("step_2_checking_database_exists", path=str(db_path))
        if not check_database_exists(db_path, force):
            return False, "Setup cancelled by user"

        # Step 3: Create database directory
        logger.info("step_3_creating_directory")
        create_database_directory(db_path)

        # Step 4: Remove existing database if force=True
        if db_path.exists():
            logger.info("removing_existing_database", path=str(db_path))
            db_path.unlink()

        # Step 5: Create database connection
        logger.info("step_4_creating_database", path=str(db_path))
        conn = sqlite3.connect(str(db_path))

        try:
            # Step 6: Load sqlite-vec extension
            logger.info("step_5_loading_sqlite_vec")
            vec_loaded = load_sqlite_vec_extension(conn)
            if not vec_loaded:
                logger.warning("vector_search_unavailable")

            # Step 7: Execute schema
            logger.info("step_6_executing_schema")
            execute_schema(conn, schema_sql, vec_loaded)

            # Step 7b: Ensure Context7 supplemental tables/columns exist
            logger.info("step_6b_ensuring_context7_tables")
            ensure_context7_tables(conn)

            # Step 8: Verification
            logger.info("step_7_verifying_database")
            tables = verify_tables(conn)
            virtual_tables = verify_virtual_tables(conn)
            triggers = verify_triggers(conn)
            indexes = verify_indexes(conn)
            schema_version = verify_schema_version(conn)

            # Step 9: Print summary
            if verbose:
                print_summary_report(tables, virtual_tables, triggers, indexes, schema_version, vec_loaded)

            # Validation
            if len(tables) < 12:
                logger.warning("incomplete_setup", expected=12, actual=len(tables))
                return False, f"Incomplete setup: only {len(tables)}/12 tables created"

            logger.info("setup_completed_successfully", db_path=str(db_path))
            return True, f"Database created successfully: {db_path}"

        finally:
            conn.close()

    except (SchemaLoadError, DatabaseSetupError) as e:
        logger.error("setup_failed", error=str(e), error_type=type(e).__name__)
        return False, str(e)

    except Exception as e:
        logger.error("unexpected_error", error=str(e), error_type=type(e).__name__)
        return False, f"Unexpected error: {e}"


def main() -> int:
    """
    Main entry point for CLI execution.

    Returns:
        Exit code (0=success, 1=error)

    Note:
        Parses arguments, runs setup, handles errors
    """
    args = parse_arguments()

    print("\n🚀 DevStream Database Setup")
    print(f"   Schema: {args.schema_file}")
    print(f"   Database: {args.db_path}\n")

    success, message = setup_database(
        schema_path=args.schema_file,
        db_path=args.db_path,
        force=args.force,
        verbose=args.verbose,
    )

    if success:
        print(f"✅ {message}\n")
        return 0
    else:
        print(f"❌ {message}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
