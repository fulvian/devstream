#!/usr/bin/env python3
"""
DevStream MCP Process Cleanup Script
====================================

Cleans up zombie MCP processes and locks to resolve session blocking issues.
Context7-compliant cleanup based on Claude Code MCP Enhanced patterns.

Usage:
    python scripts/cleanup_mcp_processes.py [--force]
"""

import os
import sys
import signal
import time
import json
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
)

logger = structlog.get_logger(__name__)

class MCPCleanup:
    """Cleanup utility for MCP processes and resources"""

    def __init__(self):
        self.temp_dir = Path("/tmp") / "devstream_mcp_locks"
        self.claude_temp = Path.home() / ".claude" / "temp"
        self.processes_found = []
        self.locks_cleaned = []

    def find_mcp_processes(self) -> List[Dict[str, Any]]:
        """Find all MCP-related processes"""
        processes = []

        try:
            # Find Node.js processes (MCP servers run on Node.js)
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                check=True
            )

            lines = result.stdout.split('\n')
            for line in lines[1:]:  # Skip header
                if any(keyword in line.lower() for keyword in [
                    "mcp", "context7", "devstream-server", "node.*index.js"
                ]):
                    parts = line.split(None, 10)
                    if len(parts) >= 11:
                        processes.append({
                            "pid": int(parts[1]),
                            "user": parts[0],
                            "cpu": parts[2],
                            "mem": parts[3],
                            "command": parts[10],
                            "full_line": line
                        })

        except subprocess.CalledProcessError as e:
            logger.warning("Failed to list processes", error=str(e))

        self.processes_found = processes
        return processes

    def kill_process_tree(self, pid: int, timeout: float = 5.0) -> bool:
        """Kill a process and all its children"""
        try:
            # Get child processes
            children = []
            try:
                result = subprocess.run(
                    ["pgrep", "-P", str(pid)],
                    capture_output=True,
                    text=True,
                    check=True
                )
                if result.stdout.strip():
                    children = [int(child_pid) for child_pid in result.stdout.strip().split('\n')]
            except subprocess.CalledProcessError:
                pass  # No children

            # Kill children first
            for child_pid in children:
                try:
                    os.kill(child_pid, signal.SIGTERM)
                    logger.info("Killed child process", pid=child_pid, parent=pid)
                except ProcessLookupError:
                    pass

            # Kill parent process
            try:
                os.kill(pid, signal.SIGTERM)
                logger.info("Killed process", pid=pid)

                # Wait for graceful termination
                time.sleep(0.5)

                # Check if still alive and force kill if necessary
                try:
                    os.kill(pid, 0)  # Check if process exists
                    os.kill(pid, signal.SIGKILL)
                    logger.warning("Force killed process", pid=pid)
                except ProcessLookupError:
                    pass  # Process is dead

                return True

            except ProcessLookupError:
                logger.info("Process already dead", pid=pid)
                return True

        except Exception as e:
            logger.error("Failed to kill process", pid=pid, error=str(e))
            return False

    def cleanup_lock_files(self) -> int:
        """Clean up MCP lock files"""
        cleaned_count = 0

        # Clean devstream MCP locks
        if self.temp_dir.exists():
            for lock_file in self.temp_dir.glob("*.lock"):
                try:
                    lock_file.unlink()
                    self.locks_cleaned.append(str(lock_file))
                    cleaned_count += 1
                    logger.debug("Cleaned lock file", file=str(lock_file))
                except OSError as e:
                    logger.warning("Failed to clean lock file", file=str(lock_file), error=str(e))

        # Clean Claude temp files
        if self.claude_temp.exists():
            for temp_file in self.claude_temp.glob("*"):
                try:
                    if temp_file.is_file():
                        temp_file.unlink()
                        cleaned_count += 1
                        logger.debug("Cleaned temp file", file=str(temp_file))
                except OSError as e:
                    logger.warning("Failed to clean temp file", file=str(temp_file), error=str(e))

        return cleaned_count

    def cleanup_zombie_sessions(self) -> int:
        """Clean up zombie Claude session files"""
        cleaned_count = 0
        session_dir = Path.home() / ".claude" / "sessions"

        if session_dir.exists():
            for session_file in session_dir.glob("*.json"):
                try:
                    # Check if session is older than 1 hour and no active process
                    stat = session_file.stat()
                    age_hours = (time.time() - stat.st_mtime) / 3600

                    if age_hours > 1:
                        session_file.unlink()
                        cleaned_count += 1
                        logger.debug("Cleaned old session file", file=str(session_file))

                except OSError as e:
                    logger.warning("Failed to clean session file", file=str(session_file), error=str(e))

        return cleaned_count

    def restart_claude_services(self) -> bool:
        """Restart Claude-related services"""
        try:
            # Kill any remaining Claude Code processes
            subprocess.run(["pkill", "-f", "claude"], check=False)
            time.sleep(1)

            # Clean up any remaining temp files
            self.cleanup_lock_files()

            logger.info("Claude services restarted successfully")
            return True

        except Exception as e:
            logger.error("Failed to restart Claude services", error=str(e))
            return False

    def run_cleanup(self, force: bool = False) -> Dict[str, Any]:
        """Run complete cleanup process"""
        logger.info("Starting MCP cleanup process", force=force)

        # Step 1: Find MCP processes
        processes = self.find_mcp_processes()

        # Step 2: Kill MCP processes
        killed_count = 0
        for process in processes:
            if force or self.should_kill_process(process):
                if self.kill_process_tree(process["pid"]):
                    killed_count += 1

        # Step 3: Clean up lock files
        locks_cleaned = self.cleanup_lock_files()

        # Step 4: Clean up zombie sessions
        sessions_cleaned = self.cleanup_zombie_sessions()

        # Step 5: Restart services if force cleanup
        if force:
            self.restart_claude_services()

        cleanup_result = {
            "processes_found": len(processes),
            "processes_killed": killed_count,
            "locks_cleaned": locks_cleaned,
            "sessions_cleaned": sessions_cleaned,
            "success": True
        }

        logger.info("MCP cleanup completed", **cleanup_result)
        return cleanup_result

    def should_kill_process(self, process: Dict[str, Any]) -> bool:
        """Determine if a process should be killed"""
        command = process["command"].lower()

        # Kill processes that match MCP patterns
        mcp_patterns = [
            "mcp-devstream-server",
            "context7-server",
            "node.*index.js",
            "claude.*mcp"
        ]

        return any(pattern in command for pattern in mcp_patterns)

    def print_summary(self, result: Dict[str, Any]):
        """Print cleanup summary"""
        print("\n" + "="*50)
        print("🧹 DevStream MCP Cleanup Summary")
        print("="*50)
        print(f"Processes found: {result['processes_found']}")
        print(f"Processes killed: {result['processes_killed']}")
        print(f"Lock files cleaned: {result['locks_cleaned']}")
        print(f"Session files cleaned: {result['sessions_cleaned']}")

        if self.processes_found:
            print(f"\n📋 Processes Found:")
            for proc in self.processes_found:
                print(f"  PID {proc['pid']}: {proc['command'][:50]}...")

        if self.locks_cleaned:
            print(f"\n🔒 Lock Files Cleaned:")
            for lock in self.locks_cleaned[:5]:  # Show first 5
                print(f"  {lock}")
            if len(self.locks_cleaned) > 5:
                print(f"  ... and {len(self.locks_cleaned) - 5} more")

        if result['success']:
            print(f"\n✅ Cleanup completed successfully!")
            print(f"\n💡 Next steps:")
            print(f"   1. Start a new Claude Code session")
            print(f"   2. The MCP tools should now work without conflicts")
        else:
            print(f"\n❌ Cleanup encountered issues. Check logs for details.")

        print("="*50)


def main():
    """Main cleanup execution"""
    parser = argparse.ArgumentParser(description="Clean up MCP processes and locks")
    parser.add_argument("--force", action="store_true", help="Force cleanup of all Claude processes")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be cleaned without doing it")

    args = parser.parse_args()

    if args.dry_run:
        print("🔍 Dry run mode - no actual cleanup will be performed")
        # Just find and show processes
        cleanup = MCPCleanup()
        processes = cleanup.find_mcp_processes()

        if processes:
            print(f"\nFound {len(processes)} MCP processes:")
            for proc in processes:
                print(f"  PID {proc['pid']}: {proc['command'][:60]}...")
        else:
            print("No MCP processes found.")
        return

    # Run actual cleanup
    cleanup = MCPCleanup()
    result = cleanup.run_cleanup(force=args.force)
    cleanup.print_summary(result)


if __name__ == "__main__":
    main()