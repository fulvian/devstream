#!/usr/bin/env python3
"""
Migration script to fix vector search dimensions.

Issue: vec_semantic_memory was created with 384 dimensions but embeddinggemma:300m generates 768-dim embeddings.
Fix: Drop and recreate the virtual table with correct dimensions.

Usage: python scripts/migrations/001_fix_vector_dimensions.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from devstream.database.connection import ConnectionPool
from devstream.database.sqlite_vec_manager import vec_manager
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def fix_vector_dimensions(db_path: str) -> bool:
    """
    Fix vector table dimensions by dropping and recreating with correct dimensions.

    Args:
        db_path: Path to SQLite database

    Returns:
        True if migration succeeded
    """
    logger.info(f"Starting vector dimension fix for database: {db_path}")

    # Backup database first
    backup_path = f"{db_path}.backup-vector-fix-{int(asyncio.get_event_loop().time())}"
    import shutil
    shutil.copy2(db_path, backup_path)
    logger.info(f"Created database backup: {backup_path}")

    pool = ConnectionPool(db_path)
    await pool.initialize()

    try:
        async with pool.engine.begin() as conn:
            # Get raw connection for sqlite-vec operations
            raw_conn = await conn.get_raw_connection()

            # Load sqlite-vec extension
            if not vec_manager.load_extension(raw_conn):
                logger.error("Failed to load sqlite-vec extension")
                return False

            # Check current virtual table
            try:
                result = await conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='vec_semantic_memory'"))
                row = result.fetchone()
                table_sql = row[0] if row else None

                if table_sql:
                    logger.info(f"Current virtual table schema:\n{table_sql}")

                    # Check if it has wrong dimensions
                    if "float[384]" in table_sql:
                        logger.warning("Found 384-dimension vector table - will recreate with 768 dimensions")
                    elif "float[768]" in table_sql:
                        logger.info("Vector table already has correct 768 dimensions - no migration needed")
                        return True
                    else:
                        logger.warning(f"Unexpected vector table format: {table_sql}")
                else:
                    logger.info("No vec_semantic_memory table found - will create new one")

            except Exception as e:
                logger.warning(f"Could check current table schema: {e}")

            # Drop existing virtual table if it exists
            try:
                await conn.execute(text("DROP TABLE IF EXISTS vec_semantic_memory"))
                logger.info("Dropped existing vec_semantic_memory table")
            except Exception as e:
                logger.warning(f"Failed to drop table (may not exist): {e}")

            # Create new virtual table with correct dimensions
            try:
                success = vec_manager.create_vec_table(
                    raw_conn,
                    "vec_semantic_memory",
                    "content_embedding",
                    768  # Correct dimension for embeddinggemma:300m
                )

                if success:
                    logger.info("Successfully created vec_semantic_memory table with 768 dimensions")
                else:
                    logger.error("Failed to create new vector table")
                    return False

            except Exception as e:
                logger.error(f"Failed to create vector table: {e}")
                return False

            # Verify the new table structure
            try:
                result = await conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='vec_semantic_memory'"))
                row = result.fetchone()
                table_sql = row[0] if row else None
                logger.info(f"New virtual table schema:\n{table_sql}")

                if "float[768]" in table_sql:
                    logger.info("✅ Migration successful - vector table now has 768 dimensions")
                else:
                    logger.error("❌ Migration failed - table does not have expected 768 dimensions")
                    return False

            except Exception as e:
                logger.error(f"Failed to verify new table: {e}")
                return False

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

    finally:
        await pool.close()

    logger.info("Vector dimension fix completed successfully")
    return True


async def main():
    """Main migration function."""
    db_path = "data/devstream.db"

    # Check if database exists
    if not Path(db_path).exists():
        logger.error(f"Database not found: {db_path}")
        sys.exit(1)

    # Run migration
    success = await fix_vector_dimensions(db_path)

    if success:
        logger.info("🎉 Migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())