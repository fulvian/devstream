#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.0.0",
#     "aiohttp>=3.8.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
DevStream MCP Client - Real MCP Integration
Context7-compliant MCP client per actual DevStream server communication.
"""

import json
import asyncio
import subprocess
import os
import sys
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import logging

# Import DevStream utilities
sys.path.append(str(Path(__file__).parent))
from logger import get_devstream_logger

class DevStreamMCPClient:
    """
    Real MCP client for DevStream server communication.
    Implements Context7-validated patterns per MCP integration.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize MCP client.

        Args:
            db_path: Path to DevStream database
        """
        self.db_path = db_path or os.getenv(
            'DEVSTREAM_DB_PATH',
            '/Users/fulvioventura/devstream/data/devstream.db'
        )
        # Calculate correct path to MCP server: from hooks/devstream/utils/mcp_client.py -> ../../mcp-devstream-server
        self.mcp_server_path = Path(__file__).parent.parent.parent.parent.parent / 'mcp-devstream-server' / 'dist' / 'index.js'
        self.logger = get_devstream_logger('mcp_client')

    async def store_memory(
        self,
        content: str,
        content_type: str,
        keywords: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Store content in DevStream memory via MCP.

        Args:
            content: Content to store
            content_type: Type of content
            keywords: Associated keywords
            session_id: Session ID for tracking

        Returns:
            MCP response or None on failure
        """
        mcp_request = {
            "jsonrpc": "2.0",
            "id": f"store_{datetime.now().timestamp()}",
            "method": "tools/call",
            "params": {
                "name": "devstream_store_memory",
                "arguments": {
                    "content": content,
                    "content_type": content_type,
                    "keywords": keywords or []
                }
            }
        }

        try:
            response = await self._call_mcp_server(mcp_request)

            if response and response.get("result"):
                self.logger.log_mcp_call(
                    tool="devstream_store_memory",
                    parameters=mcp_request["params"]["arguments"],
                    success=True,
                    response=response.get("result")
                )
                return response.get("result")
            else:
                self.logger.log_mcp_call(
                    tool="devstream_store_memory",
                    parameters=mcp_request["params"]["arguments"],
                    success=False,
                    error="No result in MCP response"
                )
                return None

        except Exception as e:
            self.logger.log_mcp_call(
                tool="devstream_store_memory",
                parameters=mcp_request["params"]["arguments"],
                success=False,
                error=str(e)
            )
            return None

    async def search_memory(
        self,
        query: str,
        content_type: Optional[str] = None,
        limit: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        Search DevStream memory via MCP.

        Args:
            query: Search query
            content_type: Filter by content type
            limit: Maximum results to return

        Returns:
            MCP search response or None on failure
        """
        mcp_request = {
            "jsonrpc": "2.0",
            "id": f"search_{datetime.now().timestamp()}",
            "method": "tools/call",
            "params": {
                "name": "devstream_search_memory",
                "arguments": {
                    "query": query,
                    "content_type": content_type,
                    "limit": limit
                }
            }
        }

        try:
            response = await self._call_mcp_server(mcp_request)

            if response and response.get("result"):
                self.logger.log_mcp_call(
                    tool="devstream_search_memory",
                    parameters=mcp_request["params"]["arguments"],
                    success=True,
                    response={"result_count": "retrieved"}
                )
                return response.get("result")
            else:
                self.logger.log_mcp_call(
                    tool="devstream_search_memory",
                    parameters=mcp_request["params"]["arguments"],
                    success=False,
                    error="No result in MCP response"
                )
                return None

        except Exception as e:
            self.logger.log_mcp_call(
                tool="devstream_search_memory",
                parameters=mcp_request["params"]["arguments"],
                success=False,
                error=str(e)
            )
            return None

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
        Create task via MCP.

        Args:
            title: Task title
            description: Task description
            task_type: Type of task
            priority: Task priority
            phase_name: Phase name
            project: Project name

        Returns:
            MCP response or None on failure
        """
        mcp_request = {
            "jsonrpc": "2.0",
            "id": f"task_{datetime.now().timestamp()}",
            "method": "tools/call",
            "params": {
                "name": "devstream_create_task",
                "arguments": {
                    "title": title,
                    "description": description,
                    "task_type": task_type,
                    "priority": priority,
                    "phase_name": phase_name,
                    "project": project or "DevStream Development"
                }
            }
        }

        try:
            response = await self._call_mcp_server(mcp_request)

            if response:
                self.logger.log_mcp_call(
                    tool="devstream_create_task",
                    parameters=mcp_request["params"]["arguments"],
                    success=True,
                    response=response.get("result", {})
                )
                return response.get("result")
            else:
                self.logger.log_mcp_call(
                    tool="devstream_create_task",
                    parameters=mcp_request["params"]["arguments"],
                    success=False,
                    error="No response from MCP server"
                )
                return None

        except Exception as e:
            self.logger.log_mcp_call(
                tool="devstream_create_task",
                parameters=mcp_request["params"]["arguments"],
                success=False,
                error=str(e)
            )
            return None

    async def list_tasks(
        self,
        status: Optional[str] = None,
        project: Optional[str] = None,
        priority: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        List tasks via MCP.

        Args:
            status: Filter by status
            project: Filter by project
            priority: Filter by priority

        Returns:
            MCP response or None on failure
        """
        mcp_request = {
            "jsonrpc": "2.0",
            "id": f"list_tasks_{datetime.now().timestamp()}",
            "method": "tools/call",
            "params": {
                "name": "devstream_list_tasks",
                "arguments": {}
            }
        }

        # Add filters if provided
        if status:
            mcp_request["params"]["arguments"]["status"] = status
        if project:
            mcp_request["params"]["arguments"]["project"] = project
        if priority:
            mcp_request["params"]["arguments"]["priority"] = priority

        try:
            response = await self._call_mcp_server(mcp_request)

            if response:
                self.logger.log_mcp_call(
                    tool="devstream_list_tasks",
                    parameters=mcp_request["params"]["arguments"],
                    success=True,
                    response={"tasks_retrieved": "success"}
                )
                return response.get("result")
            else:
                self.logger.log_mcp_call(
                    tool="devstream_list_tasks",
                    parameters=mcp_request["params"]["arguments"],
                    success=False,
                    error="No response from MCP server"
                )
                return None

        except Exception as e:
            self.logger.log_mcp_call(
                tool="devstream_list_tasks",
                parameters=mcp_request["params"]["arguments"],
                success=False,
                error=str(e)
            )
            return None

    async def update_task(
        self,
        task_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update task status via MCP.

        Args:
            task_id: Task ID to update
            status: New status
            notes: Update notes

        Returns:
            MCP response or None on failure
        """
        mcp_request = {
            "jsonrpc": "2.0",
            "id": f"update_task_{datetime.now().timestamp()}",
            "method": "tools/call",
            "params": {
                "name": "devstream_update_task",
                "arguments": {
                    "task_id": task_id,
                    "status": status
                }
            }
        }

        if notes:
            mcp_request["params"]["arguments"]["notes"] = notes

        try:
            response = await self._call_mcp_server(mcp_request)

            if response:
                self.logger.log_mcp_call(
                    tool="devstream_update_task",
                    parameters=mcp_request["params"]["arguments"],
                    success=True,
                    response=response.get("result", {})
                )
                return response.get("result")
            else:
                self.logger.log_mcp_call(
                    tool="devstream_update_task",
                    parameters=mcp_request["params"]["arguments"],
                    success=False,
                    error="No response from MCP server"
                )
                return None

        except Exception as e:
            self.logger.log_mcp_call(
                tool="devstream_update_task",
                parameters=mcp_request["params"]["arguments"],
                success=False,
                error=str(e)
            )
            return None

    async def _call_mcp_server(self, mcp_request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Make actual MCP server call via subprocess.

        Args:
            mcp_request: MCP request object

        Returns:
            MCP response or None on failure
        """
        try:
            # Prepare the MCP server command
            cmd = [
                'node',
                str(self.mcp_server_path),
                str(self.db_path)
            ]

            # Create subprocess for MCP communication
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, 'NODE_ENV': 'production'}
            )

            # Send MCP request
            request_json = json.dumps(mcp_request) + '\n'
            stdout, stderr = await process.communicate(request_json.encode('utf-8'))

            if process.returncode != 0:
                error_msg = stderr.decode('utf-8') if stderr else 'Unknown MCP server error'
                self.logger.logger.error(f"MCP server error: {error_msg}")
                return None

            # Parse response
            if stdout:
                response_text = stdout.decode('utf-8').strip()
                if response_text:
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError as e:
                        self.logger.logger.error(f"Failed to parse MCP response: {e}")
                        return None

            return None

        except Exception as e:
            self.logger.logger.error(f"MCP server communication failed: {e}")
            return None

    async def health_check(self) -> bool:
        """
        Check if MCP server is healthy.

        Returns:
            True if server is responding
        """
        try:
            # Check if MCP server file exists first
            if not self.mcp_server_path.exists():
                self.logger.logger.debug(f"MCP server not found at {self.mcp_server_path}")
                return False

            # Simple ping-like request
            test_request = {
                "jsonrpc": "2.0",
                "id": "health_check",
                "method": "tools/list",
                "params": {}
            }

            response = await self._call_mcp_server(test_request)
            return response is not None

        except Exception:
            return False

# Singleton instance for hook usage
_mcp_client = None

def get_mcp_client() -> DevStreamMCPClient:
    """
    Get singleton MCP client instance.

    Returns:
        DevStreamMCPClient instance
    """
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = DevStreamMCPClient()
    return _mcp_client

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
        MCP response or None
    """
    client = get_mcp_client()
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
        MCP response or None
    """
    client = get_mcp_client()
    return await client.search_memory(query, content_type, limit)

# Test function
async def test_mcp_integration():
    """Test MCP integration functionality."""
    client = get_mcp_client()

    print("🧪 Testing DevStream MCP Integration...")

    # Health check
    print("1. Health check...")
    is_healthy = await client.health_check()
    print(f"   ✅ MCP server healthy: {is_healthy}")

    if not is_healthy:
        print("   ⚠️  MCP server not responding - check server status")
        return

    # Test memory storage
    print("2. Testing memory storage...")
    store_result = await client.store_memory(
        content="Test memory storage from hook integration",
        content_type="context",
        keywords=["test", "mcp-integration", "hook-system"],
        session_id="test-session"
    )
    print(f"   ✅ Memory stored: {store_result is not None}")

    # Test memory search
    print("3. Testing memory search...")
    search_result = await client.search_memory(
        query="hook integration test",
        limit=5
    )
    print(f"   ✅ Memory searched: {search_result is not None}")

    # Test task listing
    print("4. Testing task listing...")
    tasks_result = await client.list_tasks()
    print(f"   ✅ Tasks listed: {tasks_result is not None}")

    print("🎉 MCP integration test completed!")

if __name__ == "__main__":
    asyncio.run(test_mcp_integration())