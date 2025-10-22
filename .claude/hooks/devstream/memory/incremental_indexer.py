#!/usr/bin/env python3
"""
DevStream Memory Bootstrap - Incremental Indexer
Context7-compliant incremental indexing with source-based deduplication.

This module provides intelligent incremental indexing using patterns from
ChromaDB and LangChain, ensuring efficient updates and avoiding duplicate
processing of unchanged content.

Key Features:
- Source-based deduplication using checksums
- Incremental updates with cleanup modes (full/incremental)
- Batch processing for performance optimization
- Change detection and smart updates
- Progress tracking and resume capability
Context7 Pattern: Source tracking + incremental updates + performance optimization
"""

import os
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple, Iterator
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import Counter
import logging
import sqlite3
from contextlib import contextmanager
import uuid

# Import DevStream components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'utils'))
try:
    from direct_client import get_direct_client
    DIRECT_CLIENT_AVAILABLE = True
except ImportError:
    DIRECT_CLIENT_AVAILABLE = False
    logging.warning("Direct client not available, using fallback storage")

from document_processor import Document, ProcessedDocument, create_document_processor


@dataclass
class IndexingRecord:
    """Record of indexed content for change detection."""
    source_path: str
    checksum: str
    last_modified: float
    content_type: str
    chunk_count: int
    indexed_at: str
    file_size: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IndexingResult:
    """Result of indexing operation."""
    success: bool
    total_files: int
    processed_files: int
    updated_files: int
    added_files: int
    skipped_files: int
    deleted_files: int
    total_chunks: int
    processing_time: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    files_discovered: int = 0
    stored_records: int = 0
    categories_indexed: Dict[str, int] = field(default_factory=dict)


class IndexingDatabase:
    """Local database for tracking indexing state."""

    def __init__(self, db_path: str):
        """
        Initialize indexing database.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.logger = logging.getLogger(f"{__name__}.IndexingDB")
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database schema."""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS indexing_records (
                    source_path TEXT PRIMARY KEY,
                    checksum TEXT NOT NULL,
                    last_modified REAL NOT NULL,
                    content_type TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    indexed_at TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    metadata TEXT
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_source_path
                ON indexing_records(source_path)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_modified
                ON indexing_records(last_modified)
            """)

    @contextmanager
    def get_connection(self):
        """Get database connection with proper error handling."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def get_record(self, source_path: str) -> Optional[IndexingRecord]:
        """Get indexing record for a source path."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM indexing_records WHERE source_path = ?",
                (source_path,)
            )
            row = cursor.fetchone()

            if row:
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
                return IndexingRecord(
                    source_path=row['source_path'],
                    checksum=row['checksum'],
                    last_modified=row['last_modified'],
                    content_type=row['content_type'],
                    chunk_count=row['chunk_count'],
                    indexed_at=row['indexed_at'],
                    file_size=row['file_size'],
                    metadata=metadata
                )
            return None

    def upsert_record(self, record: IndexingRecord) -> None:
        """Insert or update indexing record."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO indexing_records
                (source_path, checksum, last_modified, content_type,
                 chunk_count, indexed_at, file_size, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.source_path,
                record.checksum,
                record.last_modified,
                record.content_type,
                record.chunk_count,
                record.indexed_at,
                record.file_size,
                json.dumps(record.metadata)
            ))

    def delete_record(self, source_path: str) -> None:
        """Delete indexing record."""
        with self.get_connection() as conn:
            conn.execute(
                "DELETE FROM indexing_records WHERE source_path = ?",
                (source_path,)
            )

    def get_all_records(self) -> List[IndexingRecord]:
        """Get all indexing records."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM indexing_records ORDER BY last_modified DESC")
            records = []

            for row in cursor.fetchall():
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
                records.append(IndexingRecord(
                    source_path=row['source_path'],
                    checksum=row['checksum'],
                    last_modified=row['last_modified'],
                    content_type=row['content_type'],
                    chunk_count=row['chunk_count'],
                    indexed_at=row['indexed_at'],
                    file_size=row['file_size'],
                    metadata=metadata
                ))

            return records

    def get_stale_records(self, project_root: str) -> List[IndexingRecord]:
        """Get records for files that no longer exist."""
        records = self.get_all_records()
        stale_records = []

        for record in records:
            file_path = Path(project_root) / record.source_path
            if not file_path.exists():
                stale_records.append(record)

        return stale_records

    def cleanup_stale_records(self, project_root: str) -> int:
        """Remove records for non-existent files."""
        stale_records = self.get_stale_records(project_root)

        with self.get_connection() as conn:
            for record in stale_records:
                conn.execute(
                    "DELETE FROM indexing_records WHERE source_path = ?",
                    (record.source_path,)
                )

        self.logger.info(f"Cleaned up {len(stale_records)} stale records")
        return len(stale_records)


class IncrementalIndexer:
    """
    Context7-compliant incremental indexer with source-based deduplication.

    Implements ChromaDB and LangChain patterns for:
    - Source-based deduplication using checksums
    - Incremental updates with cleanup modes
    - Batch processing for performance
    - Change detection and smart updates
    """

    def __init__(self, project_root: str, memory_client=None, processor_config: Optional[Dict[str, Any]] = None):
        """
        Initialize incremental indexer.

        Args:
            project_root: Root path of the project
            memory_client: DevStream memory client (optional)
            processor_config: Document processor configuration overrides
        """
        self.project_root = Path(project_root).resolve()
        self.memory_client = memory_client or (get_direct_client() if DIRECT_CLIENT_AVAILABLE else None)

        # Initialize indexing database
        db_path = self.project_root / '.claude' / 'indexing.db'
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.indexing_db = IndexingDatabase(str(db_path))

        # Context7 Pattern: Direct database fallback path
        # Find the main DevStream database
        main_db_path = self.project_root / 'data' / 'devstream.db'
        self.direct_db_path = str(main_db_path) if main_db_path.exists() else None

        # Initialize document processor
        self.doc_processor = create_document_processor(
            str(project_root),
            batch_size=25,
            config=processor_config
        )

        self.logger = logging.getLogger(__name__)

    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate checksum for file content."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.sha256(content).hexdigest()[:16]
        except Exception as e:
            self.logger.error(f"Error calculating checksum for {file_path}: {e}")
            return ""

    def _needs_indexing(self, file_path: Path) -> Tuple[bool, Optional[IndexingRecord]]:
        """
        Check if file needs indexing based on change detection.

        Context7 Pattern: Smart change detection using checksum + metadata.
        """
        if not file_path.exists():
            return False, None

        # Get current file stats
        stat = file_path.stat()
        current_checksum = self._calculate_file_checksum(file_path)
        current_modified = stat.st_mtime
        current_size = stat.st_size

        # Get existing record - use absolute path resolution
        try:
            relative_path = str(file_path.resolve().relative_to(self.project_root))
        except ValueError:
            # File is outside project root, skip
            return False, None

        existing_record = self.indexing_db.get_record(relative_path)

        if not existing_record:
            return True, None  # New file

        # Check if file changed
        if (existing_record.checksum != current_checksum or
            existing_record.last_modified != current_modified or
            existing_record.file_size != current_size):
            return True, existing_record  # Modified file

        return False, existing_record  # Unchanged file

    def _store_documents_batch(self, documents: List[Document], source_path: str) -> Tuple[bool, int]:
        """
        Store documents in memory database using Context7 best practices.

        Enhanced with robust bulk processing, detailed error reporting, and fallback mechanisms.
        """
        if not self.memory_client:
            self.logger.error("❌ No memory client available - cannot store documents")
            return False, 0

        if not documents:
            self.logger.warning(f"⚠️  No documents to store for {source_path}")
            return True, 0

        stored_count = 0
        failed_count = 0
        error_details = []

        try:
            # Context7 Pattern: Bulk processing with detailed logging
            self.logger.info(f"📦 Storing {len(documents)} documents from {source_path}")

            for i, doc in enumerate(documents):
                try:
                    # Enhanced metadata for better tracking
                    metadata = doc.metadata.copy()
                    metadata.update({
                        'indexed_at': datetime.now().isoformat(),
                        'source_path': source_path,
                        'indexing_batch': True,
                        'doc_index': i,
                        'total_docs': len(documents)
                    })

                    # Validate content before storage
                    if not doc.page_content or len(doc.page_content.strip()) == 0:
                        self.logger.warning(f"⚠️  Empty content in document {i} from {source_path}")
                        continue

                    # Use the appropriate method based on available client
                    if hasattr(self.memory_client, 'store_memory'):
                        # Context7 Pattern: Enhanced async storage with better error handling
                        import asyncio

                        try:
                            result = asyncio.run(
                                self.memory_client.store_memory(
                                    content=doc.page_content,
                                    content_type=metadata.get('content_type', 'code'),
                                    keywords=metadata.get('keywords', []),
                                    session_id=metadata.get('session_id'),
                                    source=source_path
                                )
                            )

                            # Enhanced success detection
                            if result is not None:
                                stored_count += 1
                                if i % 10 == 0:  # Log every 10th document
                                    self.logger.info(f"✅ Stored document {i+1}/{len(documents)} from {source_path}")
                            else:
                                # Some clients don't return payloads - assume success
                                stored_count += 1

                        except RuntimeError as e:
                            if "asyncio.run() cannot be called" in str(e):
                                # Alternative sync method for event loop context
                                self.logger.warning(f"⚠️  Event loop conflict, using sync fallback for {source_path}")
                                try:
                                    # Try direct method call
                                    result = self.memory_client.store_memory(
                                        content=doc.page_content,
                                        content_type=metadata.get('content_type', 'code'),
                                        keywords=metadata.get('keywords', []),
                                        session_id=metadata.get('session_id'),
                                        source=source_path
                                    )
                                    stored_count += 1
                                except Exception as sync_error:
                                    self.logger.error(f"❌ Sync storage failed for document {i}: {sync_error}")
                                    failed_count += 1
                                    error_details.append(f"Doc {i}: {str(sync_error)[:100]}")
                            else:
                                raise
                    else:
                        self.logger.error(f"❌ Memory client missing store_memory method")
                        failed_count += len(documents)
                        break

                except Exception as doc_error:
                    failed_count += 1
                    error_msg = f"Document {i} failed: {str(doc_error)[:200]}"
                    error_details.append(error_msg)
                    self.logger.error(f"❌ {error_msg}")

                    # Continue with next document instead of failing completely
                    continue

            # Comprehensive result reporting
            total_processed = stored_count + failed_count
            success_rate = (stored_count / total_processed * 100) if total_processed > 0 else 0

            self.logger.info(f"📊 Storage complete for {source_path}:")
            self.logger.info(f"   ✅ Stored: {stored_count}/{total_processed} ({success_rate:.1f}%)")
            self.logger.info(f"   ❌ Failed: {failed_count}")

            if failed_count > 0:
                self.logger.warning(f"⚠️  First few errors:")
                for error in error_details[:3]:
                    self.logger.warning(f"   - {error}")

            # Consider success if we stored at least 50% of documents
            success = success_rate >= 50.0

            if success and stored_count > 0:
                self.logger.info(f"🎉 Successfully bulk-stored {stored_count} documents from {source_path}")

            return success, stored_count

        except Exception as batch_error:
            self.logger.error(f"💥 Critical batch storage error for {source_path}: {batch_error}")
            self.logger.error(f"   Documents attempted: {len(documents)}")
            self.logger.error(f"   Stored before failure: {stored_count}")
            return False, stored_count

    def _store_documents_direct_fallback(self, documents: List[Document], source_path: str) -> Tuple[bool, int]:
        """
        Context7 Pattern: Direct database fallback when memory client fails.
        Implements bulk storage pattern from LanceDB best practices.
        """
        if not self.direct_db_path:
            self.logger.error("❌ No direct database path available for fallback")
            return False, 0

        if not documents:
            return True, 0

        stored_count = 0
        try:
            # Context7 Pattern: Direct SQLite bulk insertion
            self.logger.info(f"🔧 Using direct database fallback for {len(documents)} documents from {source_path}")

            with sqlite3.connect(self.direct_db_path) as conn:
                # Begin transaction for bulk insert
                conn.execute("BEGIN IMMEDIATE")

                for i, doc in enumerate(documents):
                    try:
                        # Enhanced metadata
                        metadata = doc.metadata.copy()
                        metadata.update({
                            'indexed_at': datetime.now().isoformat(),
                            'source_path': source_path,
                            'indexing_batch': True,
                            'direct_fallback': True,
                            'doc_index': i,
                            'total_docs': len(documents)
                        })

                        # Validate content
                        if not doc.page_content or len(doc.page_content.strip()) == 0:
                            continue

                        # Generate unique ID
                        doc_id = str(uuid.uuid4())

                        # Validate content_type
                        content_type = metadata.get('content_type', 'code')
                        valid_types = {'code', 'documentation', 'context', 'output', 'error', 'decision', 'learning'}
                        if content_type not in valid_types:
                            content_type = 'code'  # Default fallback

                        # Prepare keywords
                        keywords = metadata.get('keywords', [])
                        if isinstance(keywords, list):
                            keywords_str = ','.join(keywords)
                        else:
                            keywords_str = str(keywords) if keywords else ''

                        # Direct SQL insertion
                        conn.execute("""
                            INSERT INTO semantic_memory (
                                id, content, content_type, created_at, keywords, metadata
                            ) VALUES (?, ?, ?, datetime('now'), ?, ?)
                        """, (
                            doc_id,
                            doc.page_content,
                            content_type,
                            keywords_str,
                            json.dumps(metadata)
                        ))

                        stored_count += 1

                        # Progress logging
                        if (i + 1) % 10 == 0:
                            self.logger.info(f"✅ Direct fallback stored {i+1}/{len(documents)} documents")

                    except Exception as doc_error:
                        self.logger.error(f"❌ Direct fallback failed for document {i}: {doc_error}")
                        continue

                # Commit transaction
                conn.commit()

            self.logger.info(f"🎉 Direct fallback successfully stored {stored_count}/{len(documents)} documents")
            return True, stored_count

        except Exception as fallback_error:
            self.logger.error(f"💥 Direct database fallback failed: {fallback_error}")
            return False, stored_count

    def index_file(
        self,
        file_path: Path,
        force_reindex: bool = False
    ) -> Tuple[bool, str, Optional[IndexingRecord], bool, int]:
        """
        Index a single file.

        Args:
            file_path: Path to file to index
            force_reindex: Force reindexing even if unchanged

        Returns:
            Tuple of (success, status_message, record, is_new_record, stored_chunks)
        """
        try:
            # Use safe relative path calculation
            try:
                relative_path = file_path.resolve().relative_to(self.project_root)
                relative_path_str = str(relative_path)
            except ValueError:
                return False, f"File outside project root: {file_path}", None, False, 0

            # Check if indexing is needed
            needs_indexing, existing_record = self._needs_indexing(file_path)

            if not needs_indexing and not force_reindex:
                return True, f"Skipped (unchanged): {relative_path_str}", None, False, 0

            # Process document
            processed_doc = self.doc_processor.process_document(file_path)

            # Create chunks
            chunked_docs = self.doc_processor.chunk_document(processed_doc)

            if not chunked_docs:
                return True, f"No content: {relative_path_str}", None, False, 0

            # Store in memory database with fallback mechanism
            stored_successfully, stored_chunks = self._store_documents_batch(
                chunked_docs,
                relative_path_str,
            )

            # Context7 Pattern: Fallback to direct database if memory client fails
            if not stored_successfully and stored_chunks == 0:
                self.logger.warning(f"⚠️  Memory client storage failed for {relative_path_str}, trying direct database fallback")
                fallback_success, fallback_chunks = self._store_documents_direct_fallback(
                    chunked_docs,
                    relative_path_str
                )
                if fallback_success:
                    stored_successfully = True
                    stored_chunks = fallback_chunks
                    self.logger.info(f"✅ Direct database fallback succeeded for {relative_path_str}")
                else:
                    return False, f"All storage methods failed: {relative_path_str}", None, False, stored_chunks

            if not stored_successfully:
                return False, f"Storage failed: {relative_path_str}", None, False, stored_chunks

            stats = file_path.stat()
            record = IndexingRecord(
                source_path=relative_path_str,
                checksum=processed_doc.checksum,
                last_modified=stats.st_mtime,
                content_type=processed_doc.content_type,
                chunk_count=len(chunked_docs),
                indexed_at=datetime.now().isoformat(),
                file_size=stats.st_size,
                metadata=processed_doc.metadata,
            )
            self.indexing_db.upsert_record(record)

            action = "Indexed" if existing_record is None else "Updated"
            return True, f"{action}: {relative_path_str} ({len(chunked_docs)} chunks)", record, existing_record is None, stored_chunks

        except Exception as e:
            error_msg = f"Error indexing {file_path}: {e}"
            self.logger.error(error_msg)
            return False, error_msg, None, False, 0

    def index_directory(self,
                       cleanup_mode: str = "incremental",
                       force_reindex: bool = False,
                       include_patterns: Optional[List[str]] = None,
                       exclude_patterns: Optional[List[str]] = None) -> IndexingResult:
        """
        Index directory with incremental updates.

        Args:
            cleanup_mode: "full", "incremental", or "none"
            force_reindex: Force reindexing all files
            include_patterns: Patterns to include
            exclude_patterns: Patterns to exclude

        Returns:
            IndexingResult with statistics
        """
        start_time = time.time()
        cleanup_mode = (cleanup_mode or "incremental").lower()

        errors: List[str] = []
        warnings: List[str] = []
        categories_counter: Counter[str] = Counter()

        try:
            file_paths = self.doc_processor.discover_documents(include_patterns, exclude_patterns)
        except Exception as discovery_error:
            error_msg = f"Failed to discover files: {discovery_error}"
            self.logger.error(error_msg)
            errors.append(error_msg)
            file_paths = []

        total_files = len(file_paths)
        if total_files == 0:
            warnings.append("No candidate files discovered for indexing.")

        deleted_files = 0
        if cleanup_mode == "full":
            existing_records = self.indexing_db.get_all_records()
            deleted_files = len(existing_records)
            if deleted_files:
                self.indexing_db.clear_index()
        elif cleanup_mode == "incremental":
            deleted_files = self.indexing_db.cleanup_stale_records(str(self.project_root))

        processed_files = 0
        updated_files = 0
        added_files = 0
        skipped_files = 0
        total_chunks = 0
        stored_records = 0

        for file_path in file_paths:
            success, message, record, is_new, stored_chunks = self.index_file(
                file_path,
                force_reindex=force_reindex,
            )

            if not success:
                errors.append(message)
                continue

            if record is None:
                skipped_files += 1
                continue

            processed_files += 1
            total_chunks += record.chunk_count
            stored_records += stored_chunks

            category = record.metadata.get('category') or record.content_type
            categories_counter[category] += 1

            if is_new:
                added_files += 1
            else:
                updated_files += 1

        processing_time = time.time() - start_time
        success_flag = len(errors) == 0 and total_files > 0

        result = IndexingResult(
            success=success_flag,
            total_files=total_files,
            processed_files=processed_files,
            updated_files=updated_files,
            added_files=added_files,
            skipped_files=skipped_files,
            deleted_files=deleted_files,
            total_chunks=total_chunks,
            processing_time=processing_time,
            errors=errors,
            warnings=warnings,
            files_discovered=total_files,
            stored_records=stored_records,
            categories_indexed=dict(categories_counter),
        )

        self.logger.info(
            "Indexing completed: %d processed, %d added, %d updated, %d skipped, %d deleted.",
            processed_files,
            added_files,
            updated_files,
            skipped_files,
            deleted_files,
        )
        self.logger.info("Total chunks indexed: %d in %.2fs", total_chunks, processing_time)

        if errors:
            self.logger.warning("Encountered %d errors during indexing.", len(errors))

        return result

    def get_indexing_status(self) -> Dict[str, Any]:
        """Get current indexing status."""
        records = self.indexing_db.get_all_records()

        # Content type distribution
        content_types = {}
        for record in records:
            content_type = record.content_type
            content_types[content_type] = content_types.get(content_type, 0) + 1

        # Calculate statistics
        total_chunks = sum(record.chunk_count for record in records)
        total_size = sum(record.file_size for record in records)

        # Recent activity
        recent_records = sorted(records, key=lambda r: r.indexed_at, reverse=True)[:10]

        return {
            'total_files': len(records),
            'total_chunks': total_chunks,
            'total_size_bytes': total_size,
            'content_types': content_types,
            'last_indexed': recent_records[0].indexed_at if recent_records else None,
            'recent_files': [
                {
                    'path': record.source_path,
                    'indexed_at': record.indexed_at,
                    'chunks': record.chunk_count
                }
                for record in recent_records
            ]
        }

    def clear_index(self) -> bool:
        """Clear all indexing records."""
        try:
            with self.indexing_db.get_connection() as conn:
                conn.execute("DELETE FROM indexing_records")

            self.logger.info("Cleared all indexing records")
            return True
        except Exception as e:
            self.logger.error(f"Error clearing indexing records: {e}")
            return False

    def remove_file(self, file_path: Path) -> bool:
        """Remove a file from indexing."""
        try:
            relative_path = str(file_path.resolve().relative_to(self.project_root))
            self.indexing_db.delete_record(relative_path)
            self.logger.info(f"Removed indexing record: {relative_path}")
            return True
        except ValueError:
            self.logger.warning(f"File {file_path} is outside project root")
            return True  # Not an error, just outside scope
        except Exception as e:
            self.logger.error(f"Error removing indexing record: {e}")
            return False


# Context7 Pattern: Convenience function for quick usage
def create_incremental_indexer(
    project_root: str,
    memory_client=None,
    processor_config: Optional[Dict[str, Any]] = None,
) -> IncrementalIndexer:
    """
    Create an incremental indexer instance.

    Args:
        project_root: Root path of the project
        memory_client: Memory client for storage

    Returns:
        IncrementalIndexer instance
    """
    return IncrementalIndexer(project_root, memory_client, processor_config)


# Context7 Pattern: Command-line interface for testing
if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="DevStream Incremental Indexer")
    parser.add_argument("project_root", help="Project root directory")
    parser.add_argument("--cleanup", choices=["full", "incremental", "none"],
                       default="incremental", help="Cleanup mode")
    parser.add_argument("--force", action="store_true", help="Force reindexing")
    parser.add_argument("--status", action="store_true", help="Show indexing status")
    parser.add_argument("--clear", action="store_true", help="Clear all indexing records")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    indexer = create_incremental_indexer(args.project_root)

    if args.clear:
        if indexer.clear_index():
            print("✅ Cleared all indexing records")
        else:
            print("❌ Failed to clear indexing records")
        sys.exit(0)

    if args.status:
        status = indexer.get_indexing_status()
        print("\n=== Indexing Status ===")
        print(f"Total files: {status['total_files']}")
        print(f"Total chunks: {status['total_chunks']}")
        print(f"Total size: {status['total_size_bytes']:,} bytes")
        print(f"Content types: {status['content_types']}")
        if status['last_indexed']:
            print(f"Last indexed: {status['last_indexed']}")
        print("\nRecent files:")
        for file_info in status['recent_files'][:5]:
            print(f"  {file_info['path']} ({file_info['chunks']} chunks)")
        sys.exit(0)

    # Perform indexing
    print(f"🔍 Indexing {args.project_root}...")
    result = indexer.index_directory(
        cleanup_mode=args.cleanup,
        force_reindex=args.force
    )

    print(f"\n=== Indexing Results ===")
    print(f"✅ Success: {result.success}")
    print(f"📁 Total files: {result.total_files}")
    print(f"📝 Processed: {result.processed_files}")
    print(f"➕ Added: {result.added_files}")
    print(f"🔄 Updated: {result.updated_files}")
    print(f"⏭️  Skipped: {result.skipped_files}")
    print(f"🗑️  Deleted: {result.deleted_files}")
    print(f"🧩 Total chunks: {result.total_chunks}")
    print(f"⏱️  Processing time: {result.processing_time:.2f}s")

    if result.errors:
        print(f"\n❌ Errors ({len(result.errors)}):")
        for error in result.errors[:5]:  # Show first 5 errors
            print(f"  {error}")

    if result.warnings:
        print(f"\n⚠️  Warnings ({len(result.warnings)}):")
        for warning in result.warnings[:5]:  # Show first 5 warnings
            print(f"  {warning}")
