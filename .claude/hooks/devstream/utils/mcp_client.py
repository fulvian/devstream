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
import atexit
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
            db_path: Path to DevStream database (validated for security)
            
        Raises:
            PathValidationError: If db_path validation fails (security violation)
            
        Security:
            Database paths are validated to prevent path traversal attacks.
            Paths must be within project directory and have .db extension.
        """
        # Import path validator
        from path_validator import validate_db_path, PathValidationError
        
        # Get path from parameter, environment, or default
        raw_path = db_path or os.getenv(
            'DEVSTREAM_DB_PATH',
            'data/devstream.db'  # Changed to relative path (project-root relative)
        )
        
        # SECURITY: Validate database path
        try:
            self.db_path = validate_db_path(raw_path)
        except PathValidationError as e:
            # Log security violation and re-raise
            logger = get_devstream_logger('mcp_client')
            logger.logger.error(
                f"Database path validation failed: {e}",
                extra={"raw_path": raw_path}
            )
            raise
        
        # Calculate correct path to MCP server: from hooks/devstream/utils/mcp_client.py -> ../../mcp-devstream-server
        self.mcp_server_path = Path(__file__).parent.parent.parent.parent.parent / 'mcp-devstream-server' / 'dist' / 'index.js'
        self.logger = get_devstream_logger('mcp_client')

        # Persistent connection attributes (Context7 Pattern: STDIO persistent connection)
        self._persistent_process: Optional[asyncio.subprocess.Process] = None
        self._stdin: Optional[asyncio.StreamWriter] = None
        self._stdout: Optional[asyncio.StreamReader] = None
        self._connection_lock = asyncio.Lock()
        self._startup_time: Optional[datetime] = None
        self._request_count = 0
        self._shutdown_event = asyncio.Event()
        self._restart_count = 0  # Track connection restarts for monitoring

        # Check if persistent mode is enabled (default: False for backward compatibility)
        self._persistent_enabled = os.getenv('DEVSTREAM_PERSISTENT_MCP', 'false').lower() == 'true'

        # Register atexit handler for emergency cleanup (Context7 Pattern: exit_stack)
        if self._persistent_enabled:
            def cleanup_on_exit():
                """Emergency cleanup if process exits without proper shutdown."""
                if self._persistent_process and self._persistent_process.returncode is None:
                    try:
                        self._persistent_process.kill()
                        # Note: Can't use await in atexit, so use synchronous wait
                        import subprocess
                        subprocess.run(['kill', '-9', str(self._persistent_process.pid)], timeout=1)
                    except Exception:
                        pass

            atexit.register(cleanup_on_exit)


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

    async def trigger_checkpoint(
        self,
        reason: str = "tool_trigger"
    ) -> Optional[Dict[str, Any]]:
        """
        Trigger immediate checkpoint for all active tasks via MCP.

        Context7 Pattern: Non-blocking checkpoint trigger for PostToolUse hook.
        Used after critical tool executions (Write, Edit, Bash, TodoWrite).

        Args:
            reason: Checkpoint reason ('tool_trigger', 'manual', 'shutdown')

        Returns:
            MCP response or None on failure
        """
        mcp_request = {
            "jsonrpc": "2.0",
            "id": f"checkpoint_{datetime.now().timestamp()}",
            "method": "tools/call",
            "params": {
                "name": "devstream_trigger_checkpoint",
                "arguments": {
                    "reason": reason
                }
            }
        }

        try:
            response = await self._call_mcp_server(mcp_request)

            if response and response.get("result"):
                self.logger.log_mcp_call(
                    tool="devstream_trigger_checkpoint",
                    parameters=mcp_request["params"]["arguments"],
                    success=True,
                    response=response.get("result")
                )
                return response.get("result")
            else:
                self.logger.log_mcp_call(
                    tool="devstream_trigger_checkpoint",
                    parameters=mcp_request["params"]["arguments"],
                    success=False,
                    error="No result in MCP response"
                )
                return None

        except Exception as e:
            # Context7 Pattern: Graceful degradation - log but don't fail
            self.logger.log_mcp_call(
                tool="devstream_trigger_checkpoint",
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

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generic MCP tool invocation method.

        Provides a unified interface for calling any MCP tool dynamically.
        Follows the same JSON-RPC pattern as specialized methods.

        Args:
            tool_name: MCP tool name (e.g., "mcp__context7__get-library-docs")
            arguments: Tool-specific arguments as dictionary

        Returns:
            Tool result dictionary from MCP server

        Raises:
            ValueError: If tool_name is empty or arguments is None
            RuntimeError: If MCP server communication fails

        Example:
            >>> result = await client.call_tool(
            ...     "mcp__context7__get-library-docs",
            ...     {"context7CompatibleLibraryID": "/fastapi/fastapi", "tokens": 5000}
            ... )
        """
        # Validate inputs
        if not tool_name or not tool_name.strip():
            raise ValueError("tool_name cannot be empty")
        if arguments is None:
            raise ValueError("arguments cannot be None (use {} for no arguments)")

        # Build MCP request following JSON-RPC 2.0 specification
        mcp_request = {
            "jsonrpc": "2.0",
            "id": f"{tool_name}-{hash(str(arguments))}-{datetime.now().timestamp()}",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        try:
            # Execute MCP server call
            response = await self._call_mcp_server(mcp_request)

            if response and response.get("result"):
                # Success - log and return result
                self.logger.log_mcp_call(
                    tool=tool_name,
                    parameters=arguments,
                    success=True,
                    response={"status": "success"}  # Avoid logging large responses
                )
                return response.get("result")
            else:
                # No result in response
                error_msg = "No result in MCP response"
                self.logger.log_mcp_call(
                    tool=tool_name,
                    parameters=arguments,
                    success=False,
                    error=error_msg
                )
                raise RuntimeError(f"MCP tool '{tool_name}' returned no result")

        except ValueError as e:
            # Re-raise validation errors
            raise
        except Exception as e:
            # Log and raise communication errors
            self.logger.log_mcp_call(
                tool=tool_name,
                parameters=arguments,
                success=False,
                error=str(e)
            )
            raise RuntimeError(f"MCP tool '{tool_name}' failed: {str(e)}") from e

    def _parse_mcp_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Multi-strategy JSON parser for MCP server responses.
        Handles single-line, multiline, and embedded JSON formats.

        Strategy 1: Full JSON parse (handles pretty-printed multiline)
        Strategy 2: Bracket-counting extraction (finds complete JSON object)
        Strategy 3: Reverse line iteration (fallback for line-delimited JSON)

        Args:
            response_text: Raw output from MCP server subprocess

        Returns:
            Parsed JSON dict or None if all strategies fail
        """
        if not response_text or not response_text.strip():
            return None

        response_text = response_text.strip()

        # STRATEGY 1: Parse entire output as JSON (handles multiline)
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # STRATEGY 2: Bracket-counting extraction (find complete JSON object)
        json_start = response_text.rfind('{')
        if json_start != -1:
            bracket_count = 0
            for i, char in enumerate(response_text[json_start:], start=json_start):
                if char == '{':
                    bracket_count += 1
                elif char == '}':
                    bracket_count -= 1
                    if bracket_count == 0:
                        # Found matching closing brace
                        json_candidate = response_text[json_start:i+1]
                        try:
                            return json.loads(json_candidate)
                        except json.JSONDecodeError:
                            pass
                        break

        # STRATEGY 3: Reverse line iteration (fallback for line-delimited JSON)
        lines = response_text.split('\n')
        for line in reversed(lines):
            line = line.strip()
            if line and line.startswith('{'):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue

        # All strategies failed - enhanced error logging
        self.logger.logger.error(
            "MCP JSON parsing failed after all strategies",
            extra={
                "output_preview": response_text[:200],
                "output_length": len(response_text),
                "starts_with": response_text[:50] if len(response_text) > 50 else response_text,
                "ends_with": response_text[-50:] if len(response_text) > 50 else response_text
            }
        )
        return None

    async def _call_mcp_server(self, mcp_request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Make actual MCP server call via subprocess OR persistent connection.

        Context7 Pattern: Adaptive routing based on DEVSTREAM_PERSISTENT_MCP flag.
        Falls back to subprocess if persistent mode fails.

        Args:
            mcp_request: MCP request object

        Returns:
            MCP response or None on failure
        """
        # Use persistent connection if enabled
        if self._persistent_enabled:
            try:
                # Ensure connection is alive
                if not await self._ensure_connection():
                    self.logger.logger.warning("Persistent connection unavailable, falling back to subprocess")
                else:
                    # Send request over persistent connection
                    response = await self._send_request(mcp_request)
                    return response

            except Exception as e:
                self.logger.logger.warning(
                    f"Persistent connection failed: {e}, falling back to subprocess",
                    extra={"error_type": type(e).__name__}
                )
                # Fall through to subprocess

        # Fallback: Use traditional subprocess pattern
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

            # Send MCP request with 30 second timeout
            request_json = json.dumps(mcp_request) + '\n'
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(request_json.encode('utf-8')),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                # Kill hung process
                process.kill()
                await process.wait()  # CRITICAL: Prevent zombie
                self.logger.logger.error(
                    "MCP server timeout (30s)",
                    extra={
                        "method": mcp_request.get("method"),
                        "server_path": str(self.mcp_server_path)
                    }
                )
                return None

            # CRITICAL: Always wait for process to prevent zombies
            if process.returncode is None:
                await process.wait()

            if process.returncode != 0:
                error_msg = stderr.decode('utf-8') if stderr else 'Unknown MCP server error'
                self.logger.logger.error(f"MCP server error: {error_msg}")
                return None

            # Parse response using multi-strategy parser
            if stdout:
                response_text = stdout.decode('utf-8').strip()
                if response_text:
                    return self._parse_mcp_response(response_text)

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

    async def _start_persistent_server(self) -> bool:
        """
        Start persistent MCP server process with STDIO transport.

        Context7 Pattern: Persistent STDIO connection for multiple requests.
        Spawns Node.js process once and maintains stdin/stdout pipes.

        Returns:
            True if server started successfully, False otherwise

        Raises:
            FileNotFoundError: If MCP server executable not found
            asyncio.TimeoutError: If server startup exceeds 5 seconds
        """
        try:
            # Verify server executable exists
            if not self.mcp_server_path.exists():
                self.logger.logger.error(
                    "MCP server executable not found",
                    extra={"path": str(self.mcp_server_path)}
                )
                raise FileNotFoundError(f"MCP server not found: {self.mcp_server_path}")

            # Prepare command
            cmd = [
                'node',
                str(self.mcp_server_path),
                str(self.db_path)
            ]

            self.logger.logger.info(
                "Starting persistent MCP server",
                extra={"command": " ".join(cmd)}
            )

            # Spawn persistent process with STDIO pipes
            self._persistent_process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={**os.environ, 'NODE_ENV': 'production'}
                ),
                timeout=5.0
            )

            # Capture stdin/stdout for communication
            self._stdin = self._persistent_process.stdin
            self._stdout = self._persistent_process.stdout

            # Record startup time and reset counters
            self._startup_time = datetime.now()
            self._request_count = 0

            self.logger.logger.info(
                "Persistent MCP server started",
                extra={
                    "pid": self._persistent_process.pid,
                    "startup_time": self._startup_time.isoformat()
                }
            )

            return True

        except asyncio.TimeoutError:
            self.logger.logger.error("MCP server startup timeout (5s)")
            # Cleanup failed process
            if self._persistent_process:
                self._persistent_process.kill()
                await self._persistent_process.wait()
                self._persistent_process = None
            return False

        except Exception as e:
            self.logger.logger.error(
                f"Failed to start persistent MCP server: {e}",
                extra={"error_type": type(e).__name__}
            )
            return False

    async def _send_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Send JSON-RPC request over persistent STDIO connection.

        Context7 Pattern: Line-delimited JSON over STDIO pipes.
        Writes request to stdin, reads response from stdout.

        Args:
            request: JSON-RPC request object

        Returns:
            Parsed JSON response or None on failure

        Raises:
            RuntimeError: If connection not established or communication fails
            asyncio.TimeoutError: If response not received within 30 seconds
        """
        if not self._stdin or not self._stdout:
            raise RuntimeError("Persistent connection not established")

        if self._persistent_process.returncode is not None:
            raise RuntimeError(f"MCP server process died (returncode: {self._persistent_process.returncode})")

        try:
            # Write request to stdin (line-delimited JSON)
            request_json = json.dumps(request) + '\n'
            self._stdin.write(request_json.encode('utf-8'))
            await self._stdin.drain()

            self.logger.logger.debug(
                "Sent MCP request",
                extra={
                    "method": request.get("method"),
                    "id": request.get("id")
                }
            )

            # Read response from stdout (line-delimited JSON)
            # CRITICAL: Skip non-JSON lines (e.g., console.log from server startup)
            response = None
            max_attempts = 10  # Prevent infinite loop
            for attempt in range(max_attempts):
                response_line = await asyncio.wait_for(
                    self._stdout.readline(),
                    timeout=30.0
                )

                if not response_line:
                    raise RuntimeError("MCP server closed connection (empty response)")

                response_text = response_line.decode('utf-8').strip()

                # Skip empty lines
                if not response_text:
                    continue

                # Try to parse as JSON
                try:
                    response = json.loads(response_text)
                    break  # Successfully parsed JSON
                except json.JSONDecodeError:
                    # Not JSON - likely console.log output from server
                    self.logger.logger.debug(f"Skipping non-JSON line: {response_text[:100]}")
                    continue

            if not response:
                raise RuntimeError("No valid JSON response after 10 attempts")

            # Increment request counter
            self._request_count += 1

            self.logger.logger.debug(
                "Received MCP response",
                extra={
                    "id": response.get("id"),
                    "has_result": "result" in response,
                    "has_error": "error" in response
                }
            )

            return response

        except asyncio.TimeoutError:
            self.logger.logger.error(
                "MCP request timeout (30s)",
                extra={"method": request.get("method")}
            )
            raise

        except json.JSONDecodeError as e:
            self.logger.logger.error(
                f"Invalid JSON in MCP response: {e}",
                extra={"response_preview": response_line[:200] if response_line else ""}
            )
            raise RuntimeError(f"Invalid JSON from MCP server: {e}")

        except Exception as e:
            self.logger.logger.error(
                f"MCP communication error: {e}",
                extra={"error_type": type(e).__name__}
            )
            raise

    async def _ensure_connection(self) -> bool:
        """
        Ensure persistent connection is alive, reconnect if needed.

        Context7 Pattern: Connection pooling with health monitoring.
        Acquires lock, checks health, restarts if necessary.

        Returns:
            True if connection is healthy, False on failure
        """
        async with self._connection_lock:
            # Check if process is alive
            if self._persistent_process is None or self._persistent_process.returncode is not None:
                self.logger.logger.warning("MCP connection unhealthy, reconnecting...")
                self._restart_count += 1
                success = await self._start_persistent_server()
                if not success:
                    self.logger.logger.error("Failed to reconnect to MCP server")
                    return False

            return True

    async def _health_check_persistent(self) -> bool:
        """
        Check if persistent connection is healthy.

        Returns:
            True if connection responding, False otherwise
        """
        if not self._persistent_process or self._persistent_process.returncode is not None:
            return False

        if not self._stdin or not self._stdout:
            return False

        try:
            # Send lightweight ping request
            ping_request = {
                "jsonrpc": "2.0",
                "id": "health_check_persistent",
                "method": "tools/list",
                "params": {}
            }

            response = await asyncio.wait_for(
                self._send_request(ping_request),
                timeout=5.0
            )

            return response is not None

        except Exception as e:
            self.logger.logger.debug(f"Health check failed: {e}")
            return False

    async def shutdown(self):
        """
        Gracefully shutdown persistent MCP server (exit_stack pattern).

        Context7 Pattern: Proper cleanup to prevent zombie processes.
        1. Close stdin (signal EOF)
        2. Wait for graceful exit (5s timeout)
        3. Force kill if needed
        4. Always await process.wait() to prevent zombies
        """
        if not self._persistent_process:
            return

        try:
            self.logger.logger.info(
                "Shutting down persistent MCP server",
                extra={
                    "pid": self._persistent_process.pid,
                    "uptime_seconds": (datetime.now() - self._startup_time).total_seconds() if self._startup_time else 0,
                    "requests_served": self._request_count
                }
            )

            # Step 1: Close stdin to signal EOF
            if self._stdin:
                self._stdin.close()
                await self._stdin.wait_closed()

            # Step 2: Wait for graceful exit (5s timeout)
            try:
                await asyncio.wait_for(
                    self._persistent_process.wait(),
                    timeout=5.0
                )
                self.logger.logger.info("MCP server exited gracefully")

            except asyncio.TimeoutError:
                # Step 3: Force kill if not graceful
                self.logger.logger.warning("MCP server didn't exit gracefully, forcing kill")
                self._persistent_process.kill()
                await self._persistent_process.wait()  # CRITICAL: Prevent zombie

        except Exception as e:
            self.logger.logger.error(f"Error during MCP server shutdown: {e}")

        finally:
            # Reset connection state
            self._persistent_process = None
            self._stdin = None
            self._stdout = None
            self._shutdown_event.set()

    async def __aenter__(self):
        """Context manager entry: ensure connection."""
        await self._ensure_connection()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: shutdown connection."""
        await self.shutdown()
        return False  # Don't suppress exceptions

    def get_stats(self) -> Dict[str, Any]:
        """
        Get connection monitoring statistics.

        Returns:
            Dictionary with uptime, request count, restart count
        """
        uptime_seconds = 0
        if self._startup_time:
            uptime_seconds = (datetime.now() - self._startup_time).total_seconds()

        return {
            "persistent_enabled": self._persistent_enabled,
            "connected": self._persistent_process is not None and self._persistent_process.returncode is None,
            "pid": self._persistent_process.pid if self._persistent_process else None,
            "uptime_seconds": uptime_seconds,
            "request_count": self._request_count,
            "restart_count": self._restart_count,
            "startup_time": self._startup_time.isoformat() if self._startup_time else None
        }

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