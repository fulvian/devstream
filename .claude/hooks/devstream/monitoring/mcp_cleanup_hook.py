#!/usr/bin/env python3
"""
MCP Cleanup Hook - Kills zombie MCP processes before PreToolUse execution.

This hook runs before EVERY tool execution to ensure no zombie MCP processes
exist that could cause database lock contention.

Integrated into PreToolUse hook chain for automatic cleanup.

Usage:
    .devstream/bin/python .claude/hooks/devstream/monitoring/mcp_cleanup_hook.py
"""

import asyncio
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import structlog

# Setup structured logging
logger = structlog.get_logger("mcp_cleanup_hook")


class MCPCleanupHook:
    """Cleanup hook to prevent zombie MCP processes."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.parent.parent
        self.mcp_server_path = self.project_root / "mcp-devstream-server" / "dist" / "index.js"
        self.max_instances = 2  # Allow max 2 instances
        self.log_file = self.project_root / ".claude" / "logs" / "devstream" / "mcp_cleanup_hook.jsonl"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    async def get_mcp_process_count(self) -> int:
        """
        Get count of running MCP server processes.

        Returns:
            Number of running MCP processes
        """
        try:
            result = subprocess.run(
                ["pgrep", "-f", str(self.mcp_server_path)],
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.returncode != 0:
                return 0

            # Count non-empty lines
            return len([line for line in result.stdout.strip().split("\n") if line])

        except subprocess.TimeoutExpired:
            logger.error("Process count check timed out")
            return 0
        except Exception as e:
            logger.error("Failed to count MCP processes", error=str(e))
            return 0

    async def kill_excess_processes(self) -> Dict[str, Any]:
        """
        Kill excess MCP processes, keeping only the most recent ones.

        Returns:
            Dictionary with cleanup status
        """
        try:
            # Get all MCP process PIDs sorted by start time
            result = subprocess.run(
                ["pgrep", "-f", str(self.mcp_server_path)],
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.returncode != 0:
                return {"killed_count": 0, "remaining_count": 0, "status": "no_processes"}

            pids = [int(pid) for pid in result.stdout.strip().split("\n") if pid]

            if len(pids) <= self.max_instances:
                return {
                    "killed_count": 0,
                    "remaining_count": len(pids),
                    "status": "ok"
                }

            # Get process start times
            process_info = []
            for pid in pids:
                ps_result = subprocess.run(
                    ["ps", "-p", str(pid), "-o", "lstart="],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if ps_result.returncode == 0:
                    start_time = ps_result.stdout.strip()
                    process_info.append({"pid": pid, "start_time": start_time})

            # Sort by start time (oldest first)
            process_info.sort(key=lambda p: p["start_time"])

            # Kill oldest processes, keep newest
            to_kill = process_info[:-self.max_instances]
            killed_count = 0

            for proc in to_kill:
                try:
                    subprocess.run(
                        ["kill", "-9", str(proc["pid"])],
                        check=True,
                        timeout=2
                    )
                    logger.warning(
                        "Cleanup killed zombie MCP process",
                        pid=proc["pid"],
                        start_time=proc["start_time"]
                    )
                    killed_count += 1
                except Exception as e:
                    logger.error(
                        "Failed to kill process",
                        pid=proc["pid"],
                        error=str(e)
                    )

            return {
                "killed_count": killed_count,
                "remaining_count": len(pids) - killed_count,
                "status": "cleaned" if killed_count > 0 else "ok"
            }

        except Exception as e:
            logger.error("Cleanup failed", error=str(e))
            return {"killed_count": 0, "remaining_count": 0, "status": "error", "error": str(e)}

    async def run_cleanup(self) -> Dict[str, Any]:
        """
        Run cleanup check and log results.

        Returns:
            Cleanup result dictionary
        """
        start_time = datetime.utcnow()
        initial_count = await self.get_mcp_process_count()

        result = {
            "timestamp": start_time.isoformat() + "Z",
            "initial_process_count": initial_count,
            "cleanup_required": initial_count > self.max_instances
        }

        if initial_count > self.max_instances:
            cleanup_result = await self.kill_excess_processes()
            result.update(cleanup_result)

            # Log to file
            import json
            with open(self.log_file, "a") as f:
                f.write(json.dumps(result) + "\n")

            logger.info(
                "MCP cleanup executed",
                initial_count=initial_count,
                killed=cleanup_result["killed_count"],
                remaining=cleanup_result["remaining_count"]
            )
        else:
            result.update({
                "killed_count": 0,
                "remaining_count": initial_count,
                "status": "ok"
            })

        return result


async def main():
    """Main entry point for cleanup hook."""
    cleanup = MCPCleanupHook()
    result = await cleanup.run_cleanup()

    # Exit with non-zero if cleanup failed
    if result.get("status") == "error":
        sys.exit(1)

    # Silent success (don't pollute hook output)
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
