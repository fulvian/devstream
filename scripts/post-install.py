#!/usr/bin/env python3
"""
DevStream Post-Install Configuration Script
Automatically configures Claude Code settings.json with hook system
Version: 0.1.0-beta

This script is called automatically after installation to ensure
settings.json is properly configured with absolute paths.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


class PostInstallConfig:
    """
    Post-installation configuration for DevStream hook system.

    Handles automatic creation and validation of Claude Code settings.json
    with proper hook configuration and absolute paths.
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize post-install configuration.

        Args:
            project_root: Optional project root path (auto-detected if not provided)
        """
        self.project_root = project_root or self._detect_project_root()
        self.claude_config_dir = Path.home() / '.claude'
        self.settings_file = self.claude_config_dir / 'settings.json'
        self.venv_python = self.project_root / '.devstream' / 'bin' / 'python'

    def _detect_project_root(self) -> Path:
        """
        Detect project root by searching for .claude directory.

        Returns:
            Path: Project root directory

        Raises:
            FileNotFoundError: If project root cannot be detected
        """
        current = Path(__file__).resolve().parent.parent

        # Search up to 3 levels
        for _ in range(3):
            if (current / '.claude').exists():
                return current
            current = current.parent

        raise FileNotFoundError(
            "Could not detect project root. "
            "Ensure .claude directory exists in project."
        )

    def log_info(self, message: str) -> None:
        """Log info message."""
        print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")

    def log_success(self, message: str) -> None:
        """Log success message."""
        print(f"{Colors.GREEN}[✓]{Colors.NC} {message}")

    def log_warning(self, message: str) -> None:
        """Log warning message."""
        print(f"{Colors.YELLOW}[⚠]{Colors.NC} {message}")

    def log_error(self, message: str) -> None:
        """Log error message."""
        print(f"{Colors.RED}[✗]{Colors.NC} {message}", file=sys.stderr)

    def backup_existing_settings(self) -> Optional[Path]:
        """
        Backup existing settings.json if present.

        Returns:
            Optional[Path]: Backup file path if created, None otherwise
        """
        if not self.settings_file.exists():
            return None

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = self.settings_file.with_suffix(f'.json.backup.{timestamp}')

        self.settings_file.rename(backup_file)
        self.log_warning(f"Existing settings.json backed up to:")
        print(f"           {backup_file}")

        return backup_file

    def verify_hook_files(self) -> bool:
        """
        Verify all required hook files exist.

        Returns:
            bool: True if all hooks exist, False otherwise
        """
        self.log_info("Verifying hook files...")

        hooks = [
            '.claude/hooks/devstream/memory/pre_tool_use.py',
            '.claude/hooks/devstream/memory/post_tool_use.py',
            '.claude/hooks/devstream/context/user_query_context_enhancer.py',
            '.claude/hooks/devstream/context/session_start.py',
        ]

        all_ok = True
        for hook in hooks:
            hook_path = self.project_root / hook
            if hook_path.exists():
                hook_path.chmod(0o755)  # Make executable
                self.log_success(f"Hook verified: {hook}")
            else:
                self.log_error(f"Hook missing: {hook}")
                all_ok = False

        return all_ok

    def verify_venv(self) -> bool:
        """
        Verify Python virtual environment exists.

        Returns:
            bool: True if venv is valid, False otherwise
        """
        self.log_info("Verifying Python virtual environment...")

        if not self.venv_python.exists():
            self.log_error(f"Python venv not found at {self.venv_python}")
            self.log_error("Please run ./install.sh first")
            return False

        # Test Python version
        import subprocess
        result = subprocess.run(
            [str(self.venv_python), '--version'],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            self.log_error("Python venv verification failed")
            return False

        self.log_success(f"Python venv found: {result.stdout.strip()}")
        return True

    def create_settings_json(self) -> Dict[str, Any]:
        """
        Create settings.json configuration with dynamic paths using environment variables.

        Returns:
            Dict[str, Any]: Settings configuration dictionary
        """
        self.log_info("Creating settings.json configuration with dynamic paths...")

        # Use environment variables and relative paths (Context7 best practice)
        # This makes the configuration universal and project-agnostic
        # New Claude Code hooks format with matchers (Context7 compliant)
        settings = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": '"$CLAUDE_PROJECT_DIR/.devstream/bin/python" "$CLAUDE_PROJECT_DIR/.claude/hooks/devstream/memory/pre_tool_use.py"'
                            }
                        ]
                    }
                ],
                "PostToolUse": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": '"$CLAUDE_PROJECT_DIR/.devstream/bin/python" "$CLAUDE_PROJECT_DIR/.claude/hooks/devstream/memory/post_tool_use.py"'
                            }
                        ]
                    }
                ],
                "UserPromptSubmit": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": '"$CLAUDE_PROJECT_DIR/.devstream/bin/python" "$CLAUDE_PROJECT_DIR/.claude/hooks/devstream/context/user_query_context_enhancer.py"'
                            }
                        ]
                    }
                ],
                "SessionStart": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": '"$CLAUDE_PROJECT_DIR/.devstream/bin/python" "$CLAUDE_PROJECT_DIR/.claude/hooks/devstream/context/session_start.py"'
                            }
                        ]
                    }
                ]
            }
        }

        return settings

    def copy_context7_api_key(self) -> None:
        """
        Copy Context7 API key from DevStream repository .env to project .env.devstream.

        This ensures universal Context7 MCP configuration across all projects.
        """
        self.log_info("Copying Context7 API key from DevStream repository...")

        # Try to find DevStream repository .env file
        devstream_env_paths = [
            # Check if we're in the DevStream repository itself
            Path(__file__).resolve().parent.parent / ".env",
            # Check common DevStream installation locations
            Path.home() / "devstream" / ".env",
            Path("/Users/fulvioventura/devstream/.env"),
        ]

        context7_api_key: Optional[str] = None

        for env_path in devstream_env_paths:
            if env_path.exists():
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.startswith('CONTEXT7_API_KEY='):
                            context7_api_key = line.split('=', 1)[1].strip()
                            self.log_success(f"Found Context7 API key in {env_path}")
                            break
                if context7_api_key:
                    break

        if not context7_api_key:
            self.log_warning("Context7 API key not found in DevStream repository")
            return

        # Write to project .env.devstream
        project_env_file = self.project_root / ".env.devstream"

        # Read existing content or start fresh
        existing_content = ""
        if project_env_file.exists():
            with open(project_env_file, 'r') as f:
                existing_content = f.read()

        # Remove existing CONTEXT7_API_KEY line if present
        lines = existing_content.split('\n')
        lines = [line for line in lines if not line.startswith('CONTEXT7_API_KEY=')]

        # Add the new API key
        lines.append(f"CONTEXT7_API_KEY={context7_api_key}")

        # Write back to file
        with open(project_env_file, 'w') as f:
            f.write('\n'.join(lines))
            if lines and lines[-1]:  # Ensure trailing newline
                f.write('\n')

        self.log_success(f"Context7 API key copied to {project_env_file}")

    def configure_context7_mcp(self, settings: Dict[str, Any]) -> None:
        """
        Add Context7 MCP server to Claude Code settings.

        Args:
            settings: Claude Code settings dictionary

        Note:
            Copies CONTEXT7_API_KEY from DevStream repository .env to project .env.devstream.
            Reads CONTEXT7_API_KEY from .env.devstream file after copying.
            Skips configuration if API key not found.
        """
        self.log_info("Configuring Context7 MCP server...")

        # First, try to copy the API key from DevStream repository
        self.copy_context7_api_key()

        # Read API key from .env.devstream
        env_file = self.project_root / ".env.devstream"
        context7_api_key: Optional[str] = None

        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('CONTEXT7_API_KEY='):
                        context7_api_key = line.split('=', 1)[1].strip()
                        break

        if not context7_api_key:
            self.log_warning("Context7 API key not found in .env.devstream - skipping")
            print("   ⚠️  Context7 MCP not configured (API key missing)")
            print("   Add CONTEXT7_API_KEY to .env.devstream to enable")
            print()
            return

        # Initialize mcpServers if not exists
        if "mcpServers" not in settings:
            settings["mcpServers"] = {}

        # Add Context7 configuration
        settings["mcpServers"]["context7"] = {
            "command": "npx",
            "args": ["-y", "@upstash/context7-mcp", "--api-key", context7_api_key]
        }

        self.log_success("Context7 MCP server configured")
        print()

    def write_settings(self, settings: Dict[str, Any]) -> None:
        """
        Write settings to settings.json file.

        Args:
            settings: Settings configuration dictionary
        """
        # Ensure directory exists
        self.claude_config_dir.mkdir(parents=True, exist_ok=True)

        # Write settings with pretty formatting
        with open(self.settings_file, 'w') as f:
            json.dump(settings, f, indent=2)

        self.log_success(f"settings.json created at: {self.settings_file}")

    def print_header(self) -> None:
        """Print script header."""
        print()
        print("=" * 60)
        print("  DevStream Post-Install Configuration")
        print("  Automatic Hook System Setup")
        print("=" * 60)
        print()

    def print_next_steps(self) -> None:
        """Print next steps after configuration."""
        print()
        print("=" * 60)
        print("  ✅ Post-Install Configuration Complete!")
        print("=" * 60)
        print()
        print("📋 Configuration Details:")
        print(f"   → Settings file: {self.settings_file}")
        print(f"   → Project root:  {self.project_root}")
        print(f"   → Python venv:   {self.venv_python}")
        print()
        print("🔄 CRITICAL NEXT STEP:")
        print()
        print("   ⚠️  RESTART Claude Code now!")
        print()
        print("   Why? Claude Code only loads settings.json at startup.")
        print("   Your hooks will NOT work until you restart.")
        print()
        print("📖 After Restart:")
        print("   → Run: ./scripts/verify-install.py")
        print("   → Check hook logs in ~/.claude/logs/devstream/")
        print()
        print("=" * 60)
        print()

    def run(self) -> int:
        """
        Run post-install configuration.

        Returns:
            int: Exit code (0 = success, 1 = failure)
        """
        self.print_header()

        self.log_info(f"Project root: {self.project_root}")
        print()

        # Verify prerequisites
        if not self.verify_venv():
            return 1

        if not self.verify_hook_files():
            self.log_error("Hook verification failed. Installation incomplete.")
            return 1

        # Backup existing settings
        self.backup_existing_settings()

        # Create and write settings
        settings = self.create_settings_json()

        # Configure Context7 MCP server
        self.configure_context7_mcp(settings)

        self.write_settings(settings)

        self.print_next_steps()

        self.log_success("Post-install configuration completed successfully!")
        return 0


def main() -> int:
    """
    Main entry point for post-install configuration.

    Returns:
        int: Exit code
    """
    try:
        config = PostInstallConfig()
        return config.run()
    except Exception as e:
        print(f"{Colors.RED}[✗]{Colors.NC} Fatal error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
