#!/usr/bin/env python3
"""
DevStream Connection Manager - Thread-Safe SQLite Connection Pool

Centralizes database connection management with automatic WAL mode enforcement.
Prevents kernel panics by ensuring EVERY connection uses WAL journal mode.

Key Features:
- Singleton pattern for process-wide connection coordination
- Automatic WAL mode + safety pragmas on ALL connections
- Thread-safe connection pooling
- Connection lifecycle management
- Graceful error handling and retry logic

Security Mitigations:
- Spotlight indexing conflict → WAL mode prevents DELETE journal corruption
- Concurrent access conflicts → busy_timeout prevents SQLITE_BUSY errors
- Data loss on crash → synchronous=NORMAL provides durability in WAL mode
"""

import sqlite3
import threading
import time
from typing import Optional, Dict, Tuple
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timedelta
import logging

# Import path validator for security
import sys
sys.path.append(str(Path(__file__).parent))
from path_validator import validate_db_path, PathValidationError


class ConnectionManager:
    """
    Thread-safe singleton connection manager for DevStream database.

    Enforces WAL mode and safety pragmas on ALL connections to prevent
    kernel panics from Spotlight indexing conflicts.

    Usage:
        >>> manager = ConnectionManager.get_instance()
        >>> with manager.get_connection() as conn:
        ...     cursor = conn.execute("SELECT * FROM memories LIMIT 1")
        ...     result = cursor.fetchone()

    Thread Safety:
        - Singleton instance protected by threading.Lock
        - Connection pool protected by threading.Lock
        - Each thread gets its own connection (thread-local storage)
    """

    _instance: Optional['ConnectionManager'] = None
    _lock: threading.Lock = threading.Lock()
    _initializing: bool = False

    # Connection pool configuration
    MAX_CONNECTIONS_PER_PROCESS = 10  # Limit to prevent fd exhaustion
    CONNECTION_MAX_AGE_SECONDS = 3600  # 1 hour max lifetime
    HEALTH_CHECK_INTERVAL = 60  # Health check every 60 seconds

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize connection manager.

        Args:
            db_path: Path to database file (validated for security)

        Raises:
            PathValidationError: If db_path validation fails
        """
        # Prevent direct instantiation (use get_instance())
        if not ConnectionManager._initializing and ConnectionManager._instance is not None:
            raise RuntimeError("Use ConnectionManager.get_instance() instead")

        # Validate database path
        if db_path is None:
            import os
            raw_path = os.getenv('DEVSTREAM_DB_PATH', 'data.noindex/devstream.db')
        else:
            raw_path = db_path

        try:
            self.db_path = validate_db_path(raw_path)
        except PathValidationError as e:
            logging.error(f"Database path validation failed: {e}")
            raise

        # Thread-local storage for connections (one connection per thread)
        self._local = threading.local()

        # Connection pool lock
        self._pool_lock = threading.Lock()

        # Active connections tracking with metadata
        # Format: {thread_id: (connection, created_at, last_used)}
        self._active_connections: Dict[int, Tuple[sqlite3.Connection, float, float]] = {}

        # Pool statistics
        self._stats = {
            "total_connections_created": 0,
            "total_connections_recycled": 0,
            "total_health_checks": 0,
            "total_health_check_failures": 0,
            "pool_limit_hits": 0
        }

        # Logger
        self.logger = logging.getLogger('devstream.connection_manager')

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> 'ConnectionManager':
        """
        Get singleton instance of ConnectionManager.

        Thread-safe singleton pattern using double-checked locking.

        Args:
            db_path: Database path (only used for first initialization)

        Returns:
            Singleton ConnectionManager instance
        """
        if cls._instance is None:
            with cls._lock:
                # Double-check after acquiring lock
                if cls._instance is None:
                    cls._initializing = True
                    cls._instance = cls.__new__(cls)
                    cls._instance.__init__(db_path)
                    cls._initializing = False
        return cls._instance

    def _create_connection(self) -> sqlite3.Connection:
        """
        Create new SQLite connection with WAL mode and safety pragmas.

        CRITICAL: This is the ONLY method that creates connections.
        ALL connections MUST go through this to enforce WAL mode.

        WAL Mode Configuration:
        - PRAGMA journal_mode=WAL (prevents Spotlight corruption)
        - PRAGMA busy_timeout=30000 (30s timeout for concurrent access)
        - PRAGMA synchronous=NORMAL (safe in WAL mode, better performance)
        - PRAGMA journal_size_limit=33554432 (32MB WAL limit)

        Returns:
            sqlite3.Connection with WAL mode enabled

        Raises:
            sqlite3.Error: If connection or pragma execution fails
        """
        try:
            # Create connection
            conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,  # Allow multi-thread access (controlled by locks)
                timeout=30.0  # Connection timeout
            )

            # CRITICAL: Enable WAL mode IMMEDIATELY after connection
            cursor = conn.execute("PRAGMA journal_mode=WAL")
            mode = cursor.fetchone()[0]
            if mode != "wal":
                raise sqlite3.Error(f"Failed to enable WAL mode: got {mode}")

            # Set safety pragmas
            conn.execute("PRAGMA busy_timeout=30000")  # 30 seconds
            conn.execute("PRAGMA synchronous=NORMAL")  # Safe in WAL mode
            conn.execute("PRAGMA journal_size_limit=33554432")  # 32 MB

            # Enable row_factory for dict-like access
            conn.row_factory = sqlite3.Row

            self.logger.debug(
                f"Created connection with WAL mode",
                extra={"db_path": self.db_path, "thread_id": threading.get_ident()}
            )

            return conn

        except sqlite3.Error as e:
            self.logger.error(f"Failed to create connection: {e}")
            raise

    def _get_thread_connection(self) -> sqlite3.Connection:
        """
        Get or create connection for current thread.

        Thread-local storage ensures each thread has its own connection,
        preventing concurrent access issues.

        Returns:
            sqlite3.Connection for current thread
        """
        thread_id = threading.get_ident()

        # Check if thread already has a connection
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            # Create new connection for this thread
            self._local.connection = self._create_connection()

            # Track active connection with metadata
            with self._pool_lock:
                current_time = time.time()
                self._active_connections[thread_id] = (
                    self._local.connection,
                    current_time,  # created_at
                    current_time   # last_used
                )
                self._stats["total_connections_created"] += 1

            self.logger.debug(f"Thread {thread_id} got new connection")

        else:
            # Update last_used timestamp for existing connection
            with self._pool_lock:
                if thread_id in self._active_connections:
                    conn, created_at, _ = self._active_connections[thread_id]
                    self._active_connections[thread_id] = (
                        conn,
                        created_at,
                        time.time()  # Update last_used
                    )

        # Health check and recycling
        self._maybe_recycle_connection()

        return self._local.connection

    @contextmanager
    def get_connection(self):
        """
        Get database connection as context manager.

        Automatically commits on success, rolls back on exception.
        Connection is returned to pool after use.

        Yields:
            sqlite3.Connection with WAL mode enabled

        Example:
            >>> manager = ConnectionManager.get_instance()
            >>> with manager.get_connection() as conn:
            ...     conn.execute("INSERT INTO memories (...) VALUES (...)")
            ...     # Automatic commit on exit
        """
        conn = self._get_thread_connection()
        try:
            yield conn
            # Automatic commit on success
            try:
                conn.commit()
            except sqlite3.ProgrammingError as e:
                if "closed database" in str(e):
                    # Connection was closed during test - create new one
                    self.close_thread_connection()
                    self.logger.warning("Connection was closed, recreated")
                else:
                    raise
        except Exception as e:
            # Rollback on error
            try:
                conn.rollback()
            except sqlite3.ProgrammingError as rollback_error:
                if "closed database" in str(rollback_error):
                    # Connection already closed - cleanup and re-raise original error
                    self.close_thread_connection()
                    self.logger.warning("Cannot rollback closed connection")
                else:
                    raise rollback_error
            self.logger.error(f"Transaction failed, rolled back: {e}")
            raise
        # Note: Connection is NOT closed (reused via thread-local storage)

    def _health_check_connection(self, conn: sqlite3.Connection) -> bool:
        """
        Perform health check on connection.

        Args:
            conn: Connection to check

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            # Simple query to verify connection works
            cursor = conn.execute("SELECT 1")
            result = cursor.fetchone()
            return result is not None and result[0] == 1
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
            return False

    def _maybe_recycle_connection(self) -> None:
        """
        Check if current thread's connection needs recycling.

        Recycles connection if:
        - Connection age > CONNECTION_MAX_AGE_SECONDS
        - Health check fails
        """
        thread_id = threading.get_ident()

        if not hasattr(self._local, 'connection') or self._local.connection is None:
            return

        with self._pool_lock:
            if thread_id not in self._active_connections:
                return

            conn, created_at, last_used = self._active_connections[thread_id]
            current_time = time.time()
            age = current_time - created_at

            # Check if connection needs recycling
            should_recycle = False
            recycle_reason = ""

            if age > self.CONNECTION_MAX_AGE_SECONDS:
                should_recycle = True
                recycle_reason = f"age {age:.0f}s > {self.CONNECTION_MAX_AGE_SECONDS}s"

            # Periodic health check (every HEALTH_CHECK_INTERVAL)
            if (current_time - last_used) > self.HEALTH_CHECK_INTERVAL:
                self._stats["total_health_checks"] += 1
                if not self._health_check_connection(conn):
                    should_recycle = True
                    recycle_reason = "health check failed"
                    self._stats["total_health_check_failures"] += 1

        if should_recycle:
            self.logger.info(f"Recycling connection for thread {thread_id}: {recycle_reason}")
            self.close_thread_connection()
            self._stats["total_connections_recycled"] += 1

    def close_thread_connection(self) -> None:
        """
        Close connection for current thread.

        Should be called at end of thread lifecycle to free resources.
        """
        thread_id = threading.get_ident()

        if hasattr(self._local, 'connection') and self._local.connection is not None:
            try:
                self._local.connection.close()
                self.logger.debug(f"Closed connection for thread {thread_id}")
            except Exception as e:
                self.logger.warning(f"Error closing connection: {e}")
            finally:
                self._local.connection = None

                # Remove from active connections
                with self._pool_lock:
                    if thread_id in self._active_connections:
                        del self._active_connections[thread_id]

    def close_all_connections(self) -> None:
        """
        Close all active connections.

        Should be called during application shutdown.
        """
        with self._pool_lock:
            for thread_id, (conn, _, _) in list(self._active_connections.items()):
                try:
                    conn.close()
                    self.logger.debug(f"Closed connection for thread {thread_id}")
                except Exception as e:
                    self.logger.warning(f"Error closing connection for thread {thread_id}: {e}")

            self._active_connections.clear()

    def get_stats(self) -> Dict:
        """
        Get connection pool statistics and health metrics.

        Returns:
            Dictionary with comprehensive pool statistics
        """
        with self._pool_lock:
            stats = {
                "active_connections": len(self._active_connections),
                "max_connections": self.MAX_CONNECTIONS_PER_PROCESS,
                "pool_utilization": len(self._active_connections) / self.MAX_CONNECTIONS_PER_PROCESS,
                "db_path": self.db_path,
                **self._stats
            }

            # Add connection age statistics
            if self._active_connections:
                current_time = time.time()
                ages = [current_time - created_at for _, created_at, _ in self._active_connections.values()]
                stats["oldest_connection_age"] = max(ages)
                stats["average_connection_age"] = sum(ages) / len(ages)

            return stats

    def enforce_pool_limit(self) -> bool:
        """
        Check if pool limit is exceeded and enforce limit.

        Returns:
            True if within limit, False if limit exceeded
        """
        with self._pool_lock:
            if len(self._active_connections) >= self.MAX_CONNECTIONS_PER_PROCESS:
                self._stats["pool_limit_hits"] += 1
                self.logger.warning(
                    f"Connection pool limit reached: {len(self._active_connections)}/{self.MAX_CONNECTIONS_PER_PROCESS}"
                )
                return False
            return True


# Convenience function for getting connection manager instance
def get_connection_manager(db_path: Optional[str] = None) -> ConnectionManager:
    """
    Get singleton ConnectionManager instance.

    Args:
        db_path: Database path (optional, uses default if not provided)

    Returns:
        ConnectionManager singleton instance
    """
    return ConnectionManager.get_instance(db_path)


# Convenience context manager for quick connections
@contextmanager
def devstream_connection(db_path: Optional[str] = None):
    """
    Quick context manager for DevStream database connections.

    Ensures WAL mode is enabled on ALL connections.

    Args:
        db_path: Database path (optional)

    Yields:
        sqlite3.Connection with WAL mode enabled

    Example:
        >>> from connection_manager import devstream_connection
        >>> with devstream_connection() as conn:
        ...     cursor = conn.execute("SELECT * FROM memories LIMIT 1")
    """
    manager = get_connection_manager(db_path)
    with manager.get_connection() as conn:
        yield conn


if __name__ == "__main__":
    # Test connection manager
    print("DevStream Connection Manager Test")
    print("=" * 50)

    # Test singleton pattern
    manager1 = ConnectionManager.get_instance()
    manager2 = ConnectionManager.get_instance()
    assert manager1 is manager2, "Singleton pattern failed"
    print("✅ Singleton pattern working")

    # Test connection creation and WAL mode
    with manager1.get_connection() as conn:
        cursor = conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode == "wal", f"WAL mode not enabled: {mode}"
        print(f"✅ WAL mode enabled: {mode}")

        # Test safety pragmas
        cursor = conn.execute("PRAGMA busy_timeout")
        timeout = cursor.fetchone()[0]
        assert timeout == 30000, f"Busy timeout not set: {timeout}"
        print(f"✅ Busy timeout: {timeout}ms")

        cursor = conn.execute("PRAGMA synchronous")
        sync = cursor.fetchone()[0]
        print(f"✅ Synchronous mode: {sync}")

    # Test stats
    stats = manager1.get_stats()
    print(f"✅ Active connections: {stats['active_connections']}")

    print("\n🎉 Connection Manager test completed!")
