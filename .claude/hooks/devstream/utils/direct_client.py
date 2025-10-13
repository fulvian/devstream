#!/usr/bin/env python3
"""
DevStream Direct Database Client

Replaces resource-intensive MCP server with direct SQLite connections.
Uses ConnectionManager for thread-safe database access with Context7 patterns.
Maintains 100% API compatibility with MCP client for seamless migration.

Key Features:
- Thread-safe database access via ConnectionManager
- Vector similarity search using sqlite-vec
- Interrupt handling for graceful cancellation
- Context7-inspired async patterns
- Full MCP API compatibility
"""

import asyncio
import json
import os
import sqlite3
import sys
import threading
import time
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime
import uuid
import logging

# Import DevStream utilities
sys.path.append(str(Path(__file__).parent))
from connection_manager import ConnectionManager
from logger import get_devstream_logger


class DatabaseException(Exception):
    """Database operation exception."""
    pass


class DevStreamDirectClient:
    """
    Direct database client replacing MCP server.

    Uses ConnectionManager for thread-safe database access with Context7 patterns.
    Maintains 100% API compatibility with MCP client for seamless migration.

    Args:
        db_path: Path to database file (validated)

    Attributes:
        connection_manager: Thread-safe connection manager instance

    Example:
        >>> client = DevStreamDirectClient()
        >>> await client.store_memory("content", "code", ["keyword"])
        'memory_id_123'
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """
        Initialize direct client with ConnectionManager.

        Args:
            db_path: Path to database file (validated)

        Raises:
            DatabaseException: If database connection fails
        """
        try:
            # Initialize connection manager
            self.connection_manager = ConnectionManager.get_instance(db_path)
            self.db_path = self.connection_manager.db_path
            self.logger = get_devstream_logger('direct_client')

            # Verify database schema compatibility
            self._verify_database_schema()

            self.logger.logger.info(
                "Direct database client initialized",
                extra={"db_path": self.db_path}
            )

        except Exception as e:
            raise DatabaseException(f"Failed to initialize direct client: {e}") from e

    def _verify_database_schema(self) -> None:
        """
        Verify database has required tables and create if missing.

        Direct client should be able to initialize its own schema if needed.
        """
        try:
            with self.connection_manager.get_connection() as conn:
                # Create semantic_memory table if not exists
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS semantic_memory (
                        id TEXT PRIMARY KEY,
                        content TEXT NOT NULL,
                        content_type TEXT NOT NULL,
                        keywords TEXT,
                        session_id TEXT,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP,
                        access_count INTEGER DEFAULT 0,
                        relevance_score REAL DEFAULT 1.0,
                        importance_score REAL DEFAULT 0.0,
                        last_accessed_at TIMESTAMP,
                        metadata TEXT,
                        source TEXT
                    )
                """)

                # Create FTS table for semantic_memory
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS fts_semantic_memory USING fts5(
                        content, content_type, memory_id, created_at
                    )
                """)

                # Create tasks table if not exists
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        description TEXT,
                        task_type TEXT,
                        priority INTEGER,
                        status TEXT DEFAULT 'pending',
                        phase_name TEXT,
                        project TEXT,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP
                    )
                """)

                # Create checkpoints table if not exists
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS checkpoints (
                        id TEXT PRIMARY KEY,
                        reason TEXT,
                        triggered_at TIMESTAMP,
                        status TEXT DEFAULT 'completed'
                    )
                """)

                # Thread-safe check for sqlite-vec extension
                self._check_vector_availability(conn)

        except Exception as e:
            raise DatabaseException(f"Schema verification failed: {e}") from e

    def _check_vector_availability(self, conn: sqlite3.Connection) -> None:
        """
        Thread-safe check for vector search availability.

        Args:
            conn: Database connection to use for checking
        """
        try:
            cursor = conn.execute("SELECT rowid FROM vec_semantic_memory LIMIT 1")
            cursor.fetchone()
            self.vector_search_available = True
        except sqlite3.OperationalError as e:
            if "no such module" in str(e):
                self.logger.logger.warning(
                    "sqlite-vec extension not available, using fallback search"
                )
                self.vector_search_available = False
            else:
                # Vector table doesn't exist, create a simple one
                self.vector_search_available = False

    async def store_memory(
        self,
        content: str,
        content_type: str,
        keywords: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Store content in semantic_memory table directly.

        Args:
            content: Content to store
            content_type: Type of content (code, documentation, context, etc.)
            keywords: Associated keywords for search
            session_id: Session ID for tracking

        Returns:
            Dictionary with stored memory ID and metadata

        Raises:
            DatabaseException: If storage operation fails
        """
        start_time = time.time()

        try:
            memory_id = str(uuid.uuid4())
            current_time = datetime.now().isoformat()

            # Prepare data for storage
            keywords_json = json.dumps(keywords or [])
            session_id_clean = session_id or os.getenv('CLAUDE_SESSION_ID', '')

            with self.connection_manager.get_connection() as conn:
                # Insert memory record
                cursor = conn.execute("""
                    INSERT INTO semantic_memory (
                        id, content, content_type, keywords, session_id,
                        created_at, updated_at, access_count, relevance_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 1.0)
                """, (
                    memory_id, content, content_type, keywords_json,
                    session_id_clean, current_time, current_time
                ))

                # Update full-text search index with error handling
                try:
                    cursor.execute("""
                        INSERT INTO fts_semantic_memory (content, content_type, memory_id, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (content, content_type, memory_id, current_time))
                except sqlite3.Error as fts_error:
                    # Log warning but don't fail the entire operation
                    self.logger.logger.warning(
                        f"Failed to update FTS index for memory {memory_id}: {fts_error}",
                        extra={
                            "memory_id": memory_id,
                            "content_type": content_type,
                            "error": str(fts_error)
                        }
                    )
                    # Memory is stored but not searchable via FTS

                # Note: Vector embedding would be handled by a background process
                # or using a simpler embedding model for direct access

            duration = (time.time() - start_time) * 1000

            self.logger.log_direct_call(
                operation="store_memory",
                parameters={
                    "content_type": content_type,
                    "keywords_count": len(keywords or []),
                    "session_id": session_id_clean
                },
                success=True,
                duration_ms=duration,
                result={"memory_id": memory_id}
            )

            return {
                "success": True,
                "memory_id": memory_id,
                "content_type": content_type,
                "created_at": current_time
            }

        except Exception as e:
            duration = (time.time() - start_time) * 1000

            self.logger.log_direct_call(
                operation="store_memory",
                parameters={
                    "content_type": content_type,
                    "keywords_count": len(keywords or []),
                    "session_id": session_id
                },
                success=False,
                duration_ms=duration,
                error=str(e)
            )

            raise DatabaseException(f"Memory storage failed: {e}") from e

    async def search_memory(
        self,
        query: str,
        content_type: Optional[str] = None,
        limit: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        Search semantic_memory with vector similarity.

        Args:
            query: Search query
            content_type: Filter by content type
            limit: Maximum results to return

        Returns:
            Dictionary with search results and metadata

        Raises:
            DatabaseException: If search operation fails
        """
        start_time = time.time()

        try:
            with self.connection_manager.get_connection() as conn:
                # Try vector search first if available
                if hasattr(self, 'vector_search_available') and self.vector_search_available:
                    try:
                        results = self._vector_search(conn, query, content_type, limit)
                    except sqlite3.OperationalError as e:
                        if "no such module" in str(e):
                            # Fallback to FTS search
                            results = self._fts_search(conn, query, content_type, limit)
                        else:
                            raise
                else:
                    # Use FTS search directly
                    results = self._fts_search(conn, query, content_type, limit)

                # Update access counts for found memories
                memory_ids = [result['id'] for result in results]
                if memory_ids:
                    placeholders = ','.join(['?' for _ in memory_ids])
                    conn.execute(
                        """
                        UPDATE semantic_memory
                        SET access_count = access_count + 1,
                            last_accessed_at = ?,
                            relevance_score = relevance_score * 0.95
                        WHERE id IN (""" + placeholders + """)
                        """,
                        [datetime.now().isoformat()] + memory_ids
                    )

            duration = (time.time() - start_time) * 1000

            self.logger.log_direct_call(
                operation="search_memory",
                parameters={
                    "query": query[:100],  # Truncate long queries
                    "content_type": content_type,
                    "limit": limit
                },
                success=True,
                duration_ms=duration,
                result={"results_count": len(results)}
            )

            return {
                "success": True,
                "results": results,
                "count": len(results),
                "query": query,
                "content_type": content_type,
                "search_method": "vector" if "vec_semantic_memory" in dir(conn) else "fts"
            }

        except Exception as e:
            duration = (time.time() - start_time) * 1000

            self.logger.log_direct_call(
                operation="search_memory",
                parameters={
                    "query": query[:100],
                    "content_type": content_type,
                    "limit": limit
                },
                success=False,
                duration_ms=duration,
                error=str(e)
            )

            raise DatabaseException(f"Memory search failed: {e}") from e

    def _vector_search(
        self,
        conn: sqlite3.Connection,
        query: str,
        content_type: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search using sqlite-vec.

        Args:
            conn: Database connection
            query: Search query
            content_type: Filter by content type
            limit: Maximum results

        Returns:
            List of memory records with similarity scores
        """
        # This is a simplified implementation
        # In production, you'd generate embeddings for the query
        # and perform proper vector similarity search

        query_embedding = self._generate_simple_embedding(query)

        sql = """
            SELECT
                sm.id, sm.content, sm.content_type, sm.keywords,
                sm.created_at, sm.access_count, sm.importance_score
            FROM vec_semantic_memory
            JOIN semantic_memory sm ON vec_semantic_memory.rowid = sm.rowid
            WHERE vec_semantic_memory MATCH ?
            ORDER BY distance
            LIMIT ?
        """

        params: List[Union[str, int]] = [query_embedding, limit]

        if content_type:
            sql = """
                SELECT
                    sm.id, sm.content, sm.content_type, sm.keywords,
                    sm.created_at, sm.access_count, sm.importance_score
                FROM vec_semantic_memory
                JOIN semantic_memory sm ON vec_semantic_memory.rowid = sm.rowid
                WHERE vec_semantic_memory MATCH ? AND sm.content_type = ?
                ORDER BY distance
                LIMIT ?
            """
            params = [query_embedding, content_type, limit]

        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def _fts_search(
        self,
        conn: sqlite3.Connection,
        query: str,
        content_type: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Perform full-text search using FTS5 with proper sanitization.

        Args:
            conn: Database connection
            query: Search query
            content_type: Filter by content type
            limit: Maximum results

        Returns:
            List of memory records with relevance scores
        """
        # Validate limit to prevent injection
        if not isinstance(limit, int) or limit < 1 or limit > 1000:
            limit = 10

        # Sanitize FTS5 query using Context7 research-backed approach
        sanitized_query = self._sanitize_fts5_query(query)

        if content_type:
            # Use parameter for content_type filtering
            sql = '''
                SELECT
                    sm.id, sm.content, sm.content_type, sm.keywords,
                    sm.created_at, sm.access_count, sm.importance_score,
                    fts_semantic_memory.rank as relevance_score
                FROM fts_semantic_memory
                JOIN semantic_memory sm ON fts_semantic_memory.memory_id = sm.id
                WHERE fts_semantic_memory MATCH ? AND sm.content_type = ?
                ORDER BY fts_semantic_memory.rank
                LIMIT ?
            '''
            params = [sanitized_query, content_type, limit]
        else:
            sql = '''
                SELECT
                    sm.id, sm.content, sm.content_type, sm.keywords,
                    sm.created_at, sm.access_count, sm.importance_score,
                    fts_semantic_memory.rank as relevance_score
                FROM fts_semantic_memory
                JOIN semantic_memory sm ON fts_semantic_memory.memory_id = sm.id
                WHERE fts_semantic_memory MATCH ?
                ORDER BY fts_semantic_memory.rank
                LIMIT ?
            '''
            params = [sanitized_query, limit]

        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            result = dict(row)
            # Parse keywords JSON
            if result['keywords']:
                try:
                    result['keywords'] = json.loads(result['keywords'])
                except json.JSONDecodeError:
                    result['keywords'] = []
            results.append(result)

        return results

    def _sanitize_fts5_query(self, query: str) -> str:
        """
        Sanitize FTS5 query using Context7 research-backed approach.

        Based on SQLite official docs + sqlite-vec best practices:
        - FTS5 interprets special characters as operators: `-` (NOT), `+` (phrase), `*` (prefix), `.` (column separator)
        - Solution: Use `content:` column prefix + double-quote wrapping
        - Join with OR operator for broad semantic matching

        Args:
            query: Raw search query

        Returns:
            Sanitized FTS5 query string
        """
        # Split query into terms
        terms = query.strip().split()
        terms = [term for term in terms if term]

        if not terms:
            return 'content:""'

        # Quote each term and escape internal quotes
        quoted_terms = []
        for term in terms:
            # Escape existing double-quotes with double double-quotes (SQL standard)
            escaped = term.replace('"', '""')
            # Wrap with content: prefix and double quotes
            quoted_terms.append(f'content:"{escaped}"')

        # Join with OR for broad matching
        return ' OR '.join(quoted_terms)

    def _generate_simple_embedding(self, text: str) -> str:
        """
        Generate simple embedding for text.

        This is a placeholder implementation. In production, you'd use
        a proper embedding model or external service.

        Args:
            text: Text to embed

        Returns:
            Simple embedding representation
        """
        # Simple approach: use word frequencies as pseudo-embedding
        words = text.lower().split()
        word_counts: Dict[str, int] = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1

        return json.dumps(word_counts)

    async def create_task(
        self,
        title: str,
        description: str,
        task_type: str,
        priority: int,
        phase_name: str,
        project: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create task via direct database access.

        Args:
            title: Task title
            description: Task description
            task_type: Type of task
            priority: Task priority
            phase_name: Phase name
            project: Project name

        Returns:
            Dictionary with created task information

        Raises:
            DatabaseException: If task creation fails
        """
        start_time = time.time()

        try:
            task_id = str(uuid.uuid4())
            current_time = datetime.now().isoformat()
            project_clean = project or "DevStream Development"

            with self.connection_manager.get_connection() as conn:
                # Check if tasks table exists, create if needed
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='tasks'
                """)
                if not cursor.fetchone():
                    # Create basic tasks table
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS tasks (
                            id TEXT PRIMARY KEY,
                            title TEXT NOT NULL,
                            description TEXT,
                            task_type TEXT,
                            priority INTEGER,
                            status TEXT DEFAULT 'pending',
                            phase_name TEXT,
                            project TEXT,
                            created_at TIMESTAMP,
                            updated_at TIMESTAMP
                        )
                    """)

                # Insert task
                cursor = conn.execute("""
                    INSERT INTO tasks (
                        id, title, description, task_type, priority,
                        status, phase_name, project, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_id, title, description, task_type, priority,
                    "pending", phase_name, project_clean, current_time, current_time
                ))

            duration = (time.time() - start_time) * 1000

            self.logger.log_direct_call(
                operation="create_task",
                parameters={
                    "title": title,
                    "task_type": task_type,
                    "priority": priority,
                    "phase_name": phase_name
                },
                success=True,
                duration_ms=duration,
                result={"task_id": task_id}
            )

            return {
                "success": True,
                "task_id": task_id,
                "status": "pending",
                "created_at": current_time
            }

        except Exception as e:
            duration = (time.time() - start_time) * 1000

            self.logger.log_direct_call(
                operation="create_task",
                parameters={
                    "title": title,
                    "task_type": task_type,
                    "priority": priority,
                    "phase_name": phase_name
                },
                success=False,
                duration_ms=duration,
                error=str(e)
            )

            raise DatabaseException(f"Task creation failed: {e}") from e

    async def list_tasks(
        self,
        status: Optional[str] = None,
        project: Optional[str] = None,
        priority: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        List tasks via direct database access.

        Args:
            status: Filter by status
            project: Filter by project
            priority: Filter by priority

        Returns:
            Dictionary with task list and metadata

        Raises:
            DatabaseException: If task listing fails
        """
        start_time = time.time()

        try:
            with self.connection_manager.get_connection() as conn:
                # Build query with filters
                sql = "SELECT * FROM tasks WHERE 1=1"
                params: List[Union[str, int]] = []

                if status:
                    sql += " AND status = ?"
                    params.append(status)

                if project:
                    sql += " AND project = ?"
                    params.append(project)

                if priority:
                    sql += " AND priority = ?"
                    params.append(priority)

                sql += " ORDER BY priority DESC, created_at ASC"

                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()

                tasks = [dict(row) for row in rows]

            duration = (time.time() - start_time) * 1000

            self.logger.log_direct_call(
                operation="list_tasks",
                parameters={
                    "status": status,
                    "project": project,
                    "priority": priority
                },
                success=True,
                duration_ms=duration,
                result={"tasks_count": len(tasks)}
            )

            return {
                "success": True,
                "tasks": tasks,
                "count": len(tasks)
            }

        except Exception as e:
            duration = (time.time() - start_time) * 1000

            self.logger.log_direct_call(
                operation="list_tasks",
                parameters={
                    "status": status,
                    "project": project,
                    "priority": priority
                },
                success=False,
                duration_ms=duration,
                error=str(e)
            )

            raise DatabaseException(f"Task listing failed: {e}") from e

    async def update_task(
        self,
        task_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update task status via direct database access.

        Args:
            task_id: Task ID to update
            status: New status
            notes: Update notes

        Returns:
            Dictionary with updated task information

        Raises:
            DatabaseException: If task update fails
        """
        start_time = time.time()

        try:
            current_time = datetime.now().isoformat()

            with self.connection_manager.get_connection() as conn:
                # Update task status
                cursor = conn.execute("""
                    UPDATE tasks
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                """, (status, current_time, task_id))

                if cursor.rowcount == 0:
                    raise DatabaseException(f"Task not found: {task_id}")

            duration = (time.time() - start_time) * 1000

            self.logger.log_direct_call(
                operation="update_task",
                parameters={
                    "task_id": task_id,
                    "status": status
                },
                success=True,
                duration_ms=duration,
                result={"task_id": task_id, "new_status": status}
            )

            return {
                "success": True,
                "task_id": task_id,
                "status": status,
                "updated_at": current_time
            }

        except Exception as e:
            duration = (time.time() - start_time) * 1000

            self.logger.log_direct_call(
                operation="update_task",
                parameters={
                    "task_id": task_id,
                    "status": status
                },
                success=False,
                duration_ms=duration,
                error=str(e)
            )

            raise DatabaseException(f"Task update failed: {e}") from e

    async def trigger_checkpoint(
        self,
        reason: str = "tool_trigger"
    ) -> Optional[Dict[str, Any]]:
        """
        Trigger immediate checkpoint for all active tasks via direct database access.

        Args:
            reason: Checkpoint reason ('tool_trigger', 'manual', 'shutdown')

        Returns:
            Dictionary with checkpoint result

        Raises:
            DatabaseException: If checkpoint operation fails
        """
        start_time = time.time()

        try:
            current_time = datetime.now().isoformat()
            checkpoint_id = str(uuid.uuid4())

            # Log checkpoint trigger
            with self.connection_manager.get_connection() as conn:
                # Create checkpoint log entry if table doesn't exist
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS checkpoints (
                        id TEXT PRIMARY KEY,
                        reason TEXT,
                        triggered_at TIMESTAMP,
                        status TEXT DEFAULT 'completed'
                    )
                """)

                conn.execute("""
                    INSERT INTO checkpoints (id, reason, triggered_at, status)
                    VALUES (?, ?, ?, 'completed')
                """, (checkpoint_id, reason, current_time))

            duration = (time.time() - start_time) * 1000

            self.logger.log_direct_call(
                operation="trigger_checkpoint",
                parameters={"reason": reason},
                success=True,
                duration_ms=duration,
                result={"checkpoint_id": checkpoint_id}
            )

            return {
                "success": True,
                "checkpoint_id": checkpoint_id,
                "reason": reason,
                "triggered_at": current_time
            }

        except Exception as e:
            duration = (time.time() - start_time) * 1000

            self.logger.log_direct_call(
                operation="trigger_checkpoint",
                parameters={"reason": reason},
                success=False,
                duration_ms=duration,
                error=str(e)
            )

            raise DatabaseException(f"Checkpoint trigger failed: {e}") from e

    async def health_check(self) -> bool:
        """
        Check if direct database client is healthy.

        Returns:
            True if database is accessible and responding
        """
        try:
            with self.connection_manager.get_connection() as conn:
                cursor = conn.execute("SELECT 1")
                result = cursor.fetchone()
                return result is not None and result[0] == 1
        except Exception as e:
            self.logger.logger.error(f"Health check failed: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get connection manager statistics.

        Returns:
            Dictionary with database connection statistics
        """
        stats: Dict[str, Any] = self.connection_manager.get_stats()
        stats.update({
            "client_type": "direct",
            "api_compatibility": "mcp",
            "features": {
                "vector_search": getattr(self, 'vector_search_available', False),
                "fts_search": True,
                "memory_storage": True,
                "task_management": True,
                "checkpoint_trigger": True
            }
        })
        return stats


# Singleton instance for hook usage
_direct_client = None

def get_direct_client() -> DevStreamDirectClient:
    """
    Get singleton direct client instance.

    Returns:
        DevStreamDirectClient instance
    """
    global _direct_client
    if _direct_client is None:
        _direct_client = DevStreamDirectClient()
    return _direct_client


# Convenience async functions for hooks
async def store_memory_async(
    content: str,
    content_type: str,
    keywords: Optional[List[str]] = None,
    session_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Async convenience function for memory storage.

    Args:
        content: Content to store
        content_type: Type of content
        keywords: Associated keywords
        session_id: Session ID

    Returns:
        Direct database response or None
    """
    client = get_direct_client()
    return await client.store_memory(content, content_type, keywords, session_id)


async def search_memory_async(
    query: str,
    content_type: Optional[str] = None,
    limit: int = 10
) -> Optional[Dict[str, Any]]:
    """
    Async convenience function for memory search.

    Args:
        query: Search query
        content_type: Filter by content type
        limit: Maximum results

    Returns:
        Direct database response or None
    """
    client = get_direct_client()
    return await client.search_memory(query, content_type, limit)


# Test function
async def test_direct_client() -> None:
    """Test direct client functionality."""
    client = get_direct_client()

    print("🧪 Testing DevStream Direct Client...")

    # Health check
    print("1. Health check...")
    is_healthy = await client.health_check()
    print(f"   ✅ Database healthy: {is_healthy}")

    if not is_healthy:
        print("   ⚠️  Database not responding - check database status")
        return

    # Test memory storage
    print("2. Testing memory storage...")
    store_result = await client.store_memory(
        content="Test memory storage from direct client",
        content_type="context",
        keywords=["test", "direct-client", "database"],
        session_id="test-session"
    )
    print(f"   ✅ Memory stored: {store_result is not None}")

    # Test memory search
    print("3. Testing memory search...")
    search_result = await client.search_memory(
        query="direct client test",
        limit=5
    )
    print(f"   ✅ Memory searched: {search_result is not None}")

    # Test task listing
    print("4. Testing task operations...")
    task_result = await client.create_task(
        title="Test Direct Client Task",
        description="Testing task creation via direct client",
        task_type="testing",
        priority=5,
        phase_name="Direct Client Testing"
    )
    print(f"   ✅ Task created: {task_result is not None}")

    # List tasks
    tasks_result = await client.list_tasks()
    print(f"   ✅ Tasks listed: {tasks_result is not None}")

    # Stats
    stats = client.get_stats()
    print(f"   ✅ Stats retrieved: {stats['client_type']} client, {stats['active_connections']} connections")

    print("🎉 Direct client test completed!")


if __name__ == "__main__":
    asyncio.run(test_direct_client())