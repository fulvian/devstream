#!/usr/bin/env python3
"""
DevStream Session Data Extractor - Context7 Compliant

Triple-source data extraction for accurate session summaries.
Implements Context7 aiosqlite async patterns with row_factory.

Data Sources:
1. work_sessions → Session metadata, timestamps, tasks
2. semantic_memory → Files modified, decisions, learnings
3. micro_tasks → Task execution history, status changes

Context7 Patterns:
- aiosqlite: async with context managers, Row factory
- Time-range queries for session-scoped data extraction
"""

import sys
import aiosqlite
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

# Add utils to path
sys.path.append(str(Path(__file__).parent.parent / 'utils'))
from logger import get_devstream_logger
from sqlite_vec_helper import get_db_connection_with_vec


@dataclass
class SessionData:
    """Session metadata from work_sessions table."""
    session_id: str
    session_name: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    tokens_used: int = 0
    active_tasks: List[str] = field(default_factory=list)
    completed_tasks: List[str] = field(default_factory=list)
    status: str = "unknown"


@dataclass
class MemoryStats:
    """Aggregated statistics from semantic_memory."""
    files_modified: int = 0
    decisions_made: int = 0
    learnings_captured: int = 0
    total_records: int = 0
    file_list: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    learnings: List[str] = field(default_factory=list)


@dataclass
class TaskStats:
    """Aggregated statistics from micro_tasks."""
    total_tasks: int = 0
    completed: int = 0
    active: int = 0
    failed: int = 0
    task_titles: List[str] = field(default_factory=list)


class SessionDataExtractor:
    """
    Extract session data from multiple sources using Context7 patterns.

    Implements async aiosqlite patterns with row_factory for clean data access.
    Performs time-range queries to extract session-scoped data.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize SessionDataExtractor.

        Args:
            db_path: Path to DevStream database (defaults to data/devstream.db)
        """
        self.structured_logger = get_devstream_logger('session_data_extractor')
        self.logger = self.structured_logger.logger

        # Database configuration
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent.parent.parent
            self.db_path = str(project_root / 'data' / 'devstream.db')
        else:
            self.db_path = db_path

        self.logger.info(f"SessionDataExtractor initialized with DB: {self.db_path}")

    async def get_session_metadata(self, session_id: str) -> Optional[SessionData]:
        """
        Extract session metadata from work_sessions table.

        Context7 Pattern: async with + row_factory for clean access.

        Args:
            session_id: Session identifier

        Returns:
            SessionData if found, None otherwise
        """
        try:
            # Context7 Pattern: async with aiosqlite.connect()
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row  # Dictionary-like access

                async with db.execute(
                    """
                    SELECT id, session_name, started_at, ended_at, tokens_used,
                           active_tasks, completed_tasks, status
                    FROM work_sessions
                    WHERE id = ?
                    """,
                    (session_id,)
                ) as cursor:
                    row = await cursor.fetchone()

                    if row is None:
                        self.logger.warning(f"No session found: {session_id}")
                        return None

                    # Parse JSON fields
                    import json
                    active_tasks = json.loads(row['active_tasks']) if row['active_tasks'] else []
                    completed_tasks = json.loads(row['completed_tasks']) if row['completed_tasks'] else []

                    return SessionData(
                        session_id=row['id'],
                        session_name=row['session_name'],
                        started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
                        ended_at=datetime.fromisoformat(row['ended_at']) if row['ended_at'] else None,
                        tokens_used=row['tokens_used'],
                        active_tasks=active_tasks,
                        completed_tasks=completed_tasks,
                        status=row['status']
                    )

        except Exception as e:
            self.logger.error(f"Failed to extract session metadata: {e}")
            return None

    async def get_memory_stats(
        self,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> MemoryStats:
        """
        Extract memory statistics for time range.

        Context7 Pattern: async with + row_factory + GROUP BY aggregation.

        Args:
            start_time: Session start timestamp
            end_time: Session end timestamp (default: now)

        Returns:
            MemoryStats with aggregated counts and samples
        """
        if end_time is None:
            end_time = datetime.now()

        stats = MemoryStats()

        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row

                # Get aggregated counts by content_type
                async with db.execute(
                    """
                    SELECT content_type, COUNT(*) as count
                    FROM semantic_memory
                    WHERE created_at BETWEEN ? AND ?
                    GROUP BY content_type
                    """,
                    (start_time.isoformat(), end_time.isoformat())
                ) as cursor:
                    async for row in cursor:
                        content_type = row['content_type']
                        count = row['count']

                        if content_type == 'code':
                            stats.files_modified = count
                        elif content_type == 'decision':
                            stats.decisions_made = count
                        elif content_type == 'learning':
                            stats.learnings_captured = count

                        stats.total_records += count

                # Get sample file names (top 10)
                async with db.execute(
                    """
                    SELECT DISTINCT content
                    FROM semantic_memory
                    WHERE content_type = 'code'
                      AND created_at BETWEEN ? AND ?
                    ORDER BY created_at DESC
                    LIMIT 10
                    """,
                    (start_time.isoformat(), end_time.isoformat())
                ) as cursor:
                    async for row in cursor:
                        # Extract filename from content (first line usually has it)
                        content = row['content']
                        first_line = content.split('\n')[0] if content else ''
                        if 'File Modified:' in first_line:
                            filename = first_line.split('File Modified:')[1].strip()
                            stats.file_list.append(filename)

                # Get decisions (top 5)
                async with db.execute(
                    """
                    SELECT content
                    FROM semantic_memory
                    WHERE content_type = 'decision'
                      AND created_at BETWEEN ? AND ?
                    ORDER BY created_at DESC
                    LIMIT 5
                    """,
                    (start_time.isoformat(), end_time.isoformat())
                ) as cursor:
                    async for row in cursor:
                        stats.decisions.append(row['content'][:200])  # First 200 chars

                # Get learnings (top 5)
                async with db.execute(
                    """
                    SELECT content
                    FROM semantic_memory
                    WHERE content_type = 'learning'
                      AND created_at BETWEEN ? AND ?
                    ORDER BY created_at DESC
                    LIMIT 5
                    """,
                    (start_time.isoformat(), end_time.isoformat())
                ) as cursor:
                    async for row in cursor:
                        stats.learnings.append(row['content'][:200])

            self.logger.debug(
                f"Memory stats extracted: {stats.total_records} records, "
                f"{stats.files_modified} files, {stats.decisions_made} decisions"
            )

            return stats

        except Exception as e:
            self.logger.error(f"Failed to extract memory stats: {e}")
            return stats

    async def get_task_stats(
        self,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> TaskStats:
        """
        Extract task statistics for time range.

        Context7 Pattern: async with + row_factory + GROUP BY aggregation.

        Args:
            start_time: Session start timestamp
            end_time: Session end timestamp (default: now)

        Returns:
            TaskStats with aggregated counts and task titles
        """
        if end_time is None:
            end_time = datetime.now()

        stats = TaskStats()

        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row

                # Get counts by status
                async with db.execute(
                    """
                    SELECT status, COUNT(*) as count
                    FROM micro_tasks
                    WHERE created_at BETWEEN ? AND ?
                    GROUP BY status
                    """,
                    (start_time.isoformat(), end_time.isoformat())
                ) as cursor:
                    async for row in cursor:
                        status = row['status']
                        count = row['count']

                        stats.total_tasks += count

                        if status == 'completed':
                            stats.completed = count
                        elif status == 'active':
                            stats.active = count
                        elif status == 'failed':
                            stats.failed = count

                # Get task titles (top 10 completed)
                async with db.execute(
                    """
                    SELECT title
                    FROM micro_tasks
                    WHERE created_at BETWEEN ? AND ?
                      AND status = 'completed'
                    ORDER BY completed_at DESC
                    LIMIT 10
                    """,
                    (start_time.isoformat(), end_time.isoformat())
                ) as cursor:
                    async for row in cursor:
                        stats.task_titles.append(row['title'])

            self.logger.debug(
                f"Task stats extracted: {stats.total_tasks} total, "
                f"{stats.completed} completed"
            )

            return stats

        except Exception as e:
            self.logger.error(f"Failed to extract task stats: {e}")
            return stats


if __name__ == "__main__":
    # Test script
    import asyncio

    async def test():
        print("DevStream Session Data Extractor Test")
        print("=" * 50)

        extractor = SessionDataExtractor()

        # Test with last hour of data
        from datetime import timedelta
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)

        print(f"\n1. Testing memory stats extraction...")
        print(f"   Time range: {start_time} to {end_time}")
        memory_stats = await extractor.get_memory_stats(start_time, end_time)
        print(f"   Total records: {memory_stats.total_records}")
        print(f"   Files modified: {memory_stats.files_modified}")
        print(f"   Decisions: {memory_stats.decisions_made}")
        print(f"   Learnings: {memory_stats.learnings_captured}")

        print(f"\n2. Testing task stats extraction...")
        task_stats = await extractor.get_task_stats(start_time, end_time)
        print(f"   Total tasks: {task_stats.total_tasks}")
        print(f"   Completed: {task_stats.completed}")
        print(f"   Active: {task_stats.active}")

        print("\n" + "=" * 50)
        print("Test completed!")

    asyncio.run(test())