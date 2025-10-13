#!/usr/bin/env python3
"""
Monitor for wrong database path usage in MCP processes.
Alerts when wrong path is detected and provides automatic remediation.
"""

import subprocess
import sys
import signal
import time
from pathlib import Path
from datetime import datetime
import argparse

# Configuration
CORRECT_DB_PATH = "/Users/fulvioventura/devstream/data/devstream.db"
WRONG_DB_PATH_PATTERN = "mcp-devstream-server/data/devstream.db"
ALERT_LOG = Path.home() / ".claude" / "logs" / "devstream" / "wrong-path-alerts.log"
CLEANUP_HOOK = Path.home() / "/Users/fulvioventura/devstream/.claude/hooks/devstream/monitoring/mcp_cleanup_hook.py"

class WrongPathMonitor:
    """Monitor for wrong database path usage in MCP processes."""
    
    def __init__(self, continuous=False, interval=30):
        self.continuous = continuous
        self.interval = interval
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Ensure log directory exists
        ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        self.running = False
    
    def check_mcp_processes(self):
        """Check all running MCP processes."""
        try:
            result = subprocess.run(
                ["pgrep", "-af", "mcp-devstream-server/dist/index.js"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return []

            processes = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        pid, cmd = parts
                        processes.append({
                            "pid": int(pid),
                            "command": cmd,
                            "wrong_path": WRONG_DB_PATH_PATTERN in cmd
                        })

            return processes
        except Exception as e:
            print(f"Error checking processes: {e}", file=sys.stderr)
            return []
    
    def detect_wrong_path_usage(self, processes):
        """Detect wrong database path usage."""
        wrong_path_procs = []
        for proc in processes:
            if proc["wrong_path"]:
                wrong_path_procs.append(proc)
        return wrong_path_procs
    
    def send_alert(self, wrong_path_procs):
        """Log alert for wrong path detection and attempt cleanup."""
        with open(ALERT_LOG, "a") as f:
            timestamp = datetime.now().isoformat()
            f.write(f"\n{'='*80}\n")
            f.write(f"ALERT: Wrong Database Path Detected - {timestamp}\n")
            f.write(f"{'='*80}\n")

            for proc in wrong_path_procs:
                f.write(f"PID {proc['pid']}: {proc['command']}\n")

            f.write(f"\nCORRECT PATH: {CORRECT_DB_PATH}\n")
            f.write(f"WRONG PATTERN: {WRONG_DB_PATH_PATTERN}\n")
            f.write(f"\nAUTO-REMEDIATION: Running cleanup hook...\n")
            f.write(f"{'='*80}\n\n")

        print(f"\n⚠️  ALERT: {len(wrong_path_procs)} process(es) using WRONG path!", file=sys.stderr)
        print(f"   Details: {ALERT_LOG}", file=sys.stderr)
        
        # Attempt automatic remediation
        self.attempt_cleanup()
    
    def attempt_cleanup(self):
        """Attempt automatic cleanup using the cleanup hook."""
        try:
            if CLEANUP_HOOK.exists():
                print("🔧 Running automatic cleanup...", file=sys.stderr)
                result = subprocess.run(
                    [str(CLEANUP_HOOK)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    print("✅ Automatic cleanup completed", file=sys.stderr)
                else:
                    print(f"⚠️  Cleanup had issues: {result.stderr}", file=sys.stderr)
            else:
                print(f"❌ Cleanup hook not found: {CLEANUP_HOOK}", file=sys.stderr)
        except Exception as e:
            print(f"❌ Cleanup failed: {e}", file=sys.stderr)
    
    def run_check(self):
        """Run a single monitoring check."""
        processes = self.check_mcp_processes()

        if not processes:
            print("No MCP processes running")
            return 0

        print(f"Found {len(processes)} MCP process(es)")

        wrong_path_procs = self.detect_wrong_path_usage(processes)

        if wrong_path_procs:
            self.send_alert(wrong_path_procs)
            return 1
        else:
            print("✅ All MCP processes using correct database path")
            return 0
    
    def run_continuous(self):
        """Run continuous monitoring."""
        print(f"Starting continuous monitoring (interval: {self.interval}s)")
        print("Press Ctrl+C to stop")
        
        while self.running:
            try:
                exit_code = self.run_check()
                if self.continuous and self.running:
                    for remaining in range(self.interval, 0, -1):
                        if not self.running:
                            break
                        print(f"\rNext check in {remaining}s... ", end="", flush=True)
                        time.sleep(1)
                    print()  # New line after countdown
                else:
                    break
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Monitor error: {e}", file=sys.stderr)
                if self.continuous:
                    time.sleep(self.interval)
        
        print("\nMonitoring stopped")
    
    def main(self):
        """Main monitoring function."""
        if self.continuous:
            self.run_continuous()
        else:
            return self.run_check()

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Monitor MCP processes for wrong database path usage")
    parser.add_argument("--continuous", "-c", action="store_true", 
                       help="Run continuous monitoring")
    parser.add_argument("--interval", "-i", type=int, default=30,
                       help="Monitoring interval in seconds (default: 30)")
    
    args = parser.parse_args()
    
    monitor = WrongPathMonitor(continuous=args.continuous, interval=args.interval)
    
    if args.continuous:
        monitor.main()
        return 0
    else:
        return monitor.main()

if __name__ == "__main__":
    sys.exit(main())
