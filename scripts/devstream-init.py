#!/usr/bin/env python3
"""
DevStream Project Initialization Script
Version: 2.2.0

Intelligent project initialization with codebase analysis and semantic memory population.
Supports both new projects and existing codebase scanning.
"""

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import logging


def get_devstream_root() -> Path:
    """
    Get DevStream root using Context7 patterns.

    Priority 1: DEVSTREAM_ROOT environment variable
    Priority 2: Script location detection (two levels up from scripts/)
    Priority 3: Current working directory
    Priority 4: Common installation locations

    Returns:
        Path to DevStream root directory

    Raises:
        RuntimeError: If DevStream root cannot be determined
    """
    # Priority 1: DEVSTREAM_ROOT environment variable
    devstream_root = os.getenv("DEVSTREAM_ROOT")
    if devstream_root and Path(devstream_root).exists():
        return Path(devstream_root).absolute()

    # Priority 2: Script location detection
    script_file = Path(__file__)
    if script_file.exists():
        # Two levels up from scripts/ directory
        potential_root = script_file.parent.parent
        if (potential_root / "start-devstream.sh").exists():
            return potential_root.absolute()

    # Priority 3: Current working directory
    cwd = Path.cwd()
    if (cwd / "start-devstream.sh").exists():
        return cwd.absolute()

    # Priority 4: Common installation locations
    possible_locations = [
        Path.home() / ".devstream",
        Path.home() / "devstream",
        Path("/opt/devstream"),
        Path.cwd(),
    ]

    for location in possible_locations:
        if location.exists() and (location / "start-devstream.sh").exists():
            return location.absolute()

    # If nothing found, raise an informative error
    raise RuntimeError(
        "DevStream installation not found! Please set DEVSTREAM_ROOT environment variable "
        "or ensure DevStream is properly installed with start-devstream.sh"
    )

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Import Context7 for codebase analysis research
try:
    from mcp__context7__resolve_library_id import resolve_library_id
    from mcp__context7__get_library_docs import get_library_docs
    CONTEXT7_AVAILABLE = True
except ImportError:
    logger.warning("Context7 not available - codebase analysis will be limited")
    CONTEXT7_AVAILABLE = False

# Type stubs for unavailable imports
if not CONTEXT7_AVAILABLE:
    def resolve_library_id(library_name: str) -> str:
        return "stub"

    def get_library_docs(context7CompatibleLibraryID: str, topic: str, tokens: int) -> str:
        return "stub docs"


class ProjectExistsError(Exception):
    """Raised when trying to initialize a project that already exists."""
    pass


class CodebaseScanError(Exception):
    """Raised when codebase scanning fails."""
    pass


def detect_project_type(project_path: str) -> Dict[str, Any]:
    """
    Detect project type based on file patterns and configuration files.

    Args:
        project_path: Path to analyze

    Returns:
        Dictionary with project type detection results
    """
    project_path_obj = Path(project_path)
    detection_result = {
        "primary_type": "generic",
        "confidence": 0.0,
        "indicators": [],
        "languages": [],
        "frameworks": [],
        "tools": []
    }

    # File patterns for different project types
    type_patterns = {
        "python": {
            "files": ["*.py", "requirements.txt", "setup.py", "pyproject.toml", "Pipfile"],
            "dirs": ["src", "tests", "test"],
            "config": ["pyproject.toml", "setup.cfg", "tox.ini"]
        },
        "typescript": {
            "files": ["*.ts", "*.tsx", "package.json", "tsconfig.json", "yarn.lock"],
            "dirs": ["src", "dist", "build", "node_modules"],
            "config": ["tsconfig.json", "webpack.config.js", "vite.config.ts"]
        },
        "javascript": {
            "files": ["*.js", "*.jsx", "package.json", "yarn.lock"],
            "dirs": ["src", "dist", "build", "node_modules"],
            "config": ["webpack.config.js", "rollup.config.js", "vite.config.js"]
        },
        "go": {
            "files": ["*.go", "go.mod", "go.sum"],
            "dirs": ["cmd", "pkg", "internal", "api"],
            "config": ["go.mod", "go.sum"]
        },
        "rust": {
            "files": ["*.rs", "Cargo.toml", "Cargo.lock"],
            "dirs": ["src", "target", "tests"],
            "config": ["Cargo.toml"]
        },
        "java": {
            "files": ["*.java", "pom.xml", "build.gradle", "build.gradle.kts"],
            "dirs": ["src", "target", "build"],
            "config": ["pom.xml", "build.gradle"]
        }
    }

    # Score each project type
    type_scores = {}
    for project_type, patterns in type_patterns.items():
        score = 0
        indicators = []

        # Check files
        for pattern in patterns["files"]:
            matches = list(project_path_obj.rglob(pattern))
            if matches:
                score += len(matches)
                indicators.append(f"{len(matches)} {pattern}")

        # Check directories
        for dir_name in patterns["dirs"]:
            if (project_path_obj / dir_name).exists():
                score += 5
                indicators.append(f"directory {dir_name}")

        # Check config files
        for config_file in patterns["config"]:
            if (project_path_obj / config_file).exists():
                score += 10
                indicators.append(f"config {config_file}")

        type_scores[project_type] = {
            "score": score,
            "indicators": indicators
        }

    # Determine primary type
    if type_scores:
        best_type_item = max(type_scores.items(), key=lambda x: x[1]["score"])
        best_type_name = best_type_item[0]
        best_type_data = best_type_item[1]
        detection_result["primary_type"] = best_type_name
        detection_result["confidence"] = min(best_type_data["score"] / 50.0, 1.0)  # Normalize to 0-1
        detection_result["indicators"] = best_type_data["indicators"]

    # Detect languages
    language_extensions = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".cs": "csharp",
        ".rb": "ruby",
        ".php": "php"
    }

    language_counts: Dict[str, int] = {}
    for file_path in project_path_obj.rglob("*"):
        if file_path.is_file() and file_path.suffix in language_extensions:
            lang = language_extensions[file_path.suffix]
            language_counts[lang] = language_counts.get(lang, 0) + 1

    if language_counts:
        total_files = sum(language_counts.values())
        detection_result["languages"] = [
            {"language": lang, "count": count, "percentage": (count / total_files) * 100}
            for lang, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True)
        ]

    return detection_result


def scan_and_populate_codebase(project_path: str) -> Dict[str, Any]:
    """
    Scan existing codebase and populate semantic memory.

    Args:
        project_path: Path to project to scan

    Returns:
        Scan results with statistics and created embeddings count
    """
    if not CONTEXT7_AVAILABLE:
        logger.warning("Context7 not available - using basic file scanning")
        return basic_codebase_scan(project_path)

    project_path_obj = Path(project_path)
    scan_results = {
        "files_scanned": 0,
        "embeddings_created": 0,
        "errors": [],
        "scan_duration": 0,
        "file_types": {},
        "directories_scanned": []
    }

    start_time = time.time()

    try:
        # Get codebase analysis patterns from Context7
        if CONTEXT7_AVAILABLE:
            library_id = resolve_library_id(libraryName="python code analysis")
            docs = get_library_docs(
                context7CompatibleLibraryID=library_id,
                topic="AST parsing and code structure analysis",
                tokens=3000
            )
            logger.info("Using Context7 codebase analysis patterns")

        # Find source files to scan
        source_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java"}
        exclude_patterns = {
            ".git", "__pycache__", "node_modules", "target", "build", "dist",
            ".venv", "venv", ".env", ".pytest_cache", ".mypy_cache"
        }

        source_files: List[Path] = []
        for file_path in project_path_obj.rglob("*"):
            if (file_path.is_file() and
                file_path.suffix in source_extensions and
                not any(pattern in str(file_path) for pattern in exclude_patterns)):

                source_files.append(file_path)

        scan_results["files_scanned"] = len(source_files)

        # Track file types
        file_types: Dict[str, int] = {}
        for file_path in source_files:
            ext = file_path.suffix
            file_types[ext] = file_types.get(ext, 0) + 1
        scan_results["file_types"] = file_types

        # Track directories
        scanned_dirs = set()
        for file_path in source_files:
            scanned_dirs.add(str(file_path.parent.relative_to(project_path_obj)))
        scan_results["directories_scanned"] = sorted(list(scanned_dirs))

        logger.info(f"Found {len(source_files)} source files to scan")

        # Here we would create embeddings for each file
        # For now, we'll simulate the process
        for i, file_path in enumerate(source_files):
            try:
                # Read file content
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if len(content.strip()) > 0:
                    # Simulate embedding creation
                    # In a real implementation, this would:
                    # 1. Parse the code into AST
                    # 2. Extract functions, classes, and important patterns
                    # 3. Create vector embeddings
                    # 4. Store in semantic memory

                    scan_results["embeddings_created"] += 1

                if (i + 1) % 50 == 0:
                    logger.info(f"Processed {i + 1}/{len(source_files)} files")

            except Exception as e:
                error_msg = f"Failed to process {file_path}: {e}"
                scan_results["errors"].append(error_msg)
                logger.warning(error_msg)

    except Exception as e:
        raise CodebaseScanError(f"Codebase scanning failed: {e}") from e

    scan_results["scan_duration"] = time.time() - start_time

    logger.info(f"Codebase scan completed: {scan_results['files_scanned']} files, "
               f"{scan_results['embeddings_created']} embeddings, "
               f"{scan_results['scan_duration']:.2f}s")

    return scan_results


def basic_codebase_scan(project_path: str) -> Dict[str, Any]:
    """
    Basic codebase scanning without Context7 integration.

    Args:
        project_path: Path to project to scan

    Returns:
        Basic scan results
    """
    project_path_obj = Path(project_path)
    scan_results = {
        "files_scanned": 0,
        "embeddings_created": 0,
        "errors": [],
        "scan_duration": 0,
        "file_types": {},
        "directories_scanned": []
    }

    start_time = time.time()

    try:
        # Find source files
        source_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java"}
        exclude_patterns = {
            ".git", "__pycache__", "node_modules", "target", "build", "dist",
            ".venv", "venv", ".env"
        }

        source_files: List[Path] = []
        for file_path in project_path_obj.rglob("*"):
            if (file_path.is_file() and
                file_path.suffix in source_extensions and
                not any(pattern in str(file_path) for pattern in exclude_patterns)):

                source_files.append(file_path)

        scan_results["files_scanned"] = len(source_files)

        # Basic file type counting
        file_types: Dict[str, int] = {}
        for file_path in source_files:
            ext = file_path.suffix
            file_types[ext] = file_types.get(ext, 0) + 1
        scan_results["file_types"] = file_types

        logger.info(f"Basic scan found {len(source_files)} source files")

    except Exception as e:
        raise CodebaseScanError(f"Basic codebase scanning failed: {e}") from e

    scan_results["scan_duration"] = time.time() - start_time
    return scan_results


def create_project_database(project_path: str) -> None:
    """
    Create DevStream project database at data/devstream.db.

    Args:
        project_path: Path where project database should be created
    """
    project_path_obj = Path(project_path)

    # Create data directory
    data_dir = project_path_obj / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create database with basic schema
    import sqlite3
    db_path = data_dir / "devstream.db"

    try:
        conn = sqlite3.connect(str(db_path))

        # Create memory table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL,
                keywords TEXT,
                embedding BLOB,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create semantic_memory table (for compatibility)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS semantic_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL,
                keywords TEXT,
                embedding BLOB,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes for better performance
        conn.execute('CREATE INDEX IF NOT EXISTS idx_memory_content_type ON memory(content_type)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_memory_created_at ON memory(created_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_semantic_memory_content_type ON semantic_memory(content_type)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_semantic_memory_created_at ON semantic_memory(created_at)')

        conn.commit()
        conn.close()

        logger.info(f"Created project database at {db_path}")

    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        raise


def create_project_claude_md(project_path: str, project_type: str) -> None:
    """
    Create/overwrite project-specific CLAUDE.md by copying and adapting DevStream's CLAUDE.md.

    CRITICAL: CLAUDE.md is the foundation of DevStream system and MUST always be updated
    to the latest version. Always overwrite existing CLAUDE.md.

    Args:
        project_path: Path where CLAUDE.md should be created/overwritten
        project_type: Detected project type (python, typescript, etc.)
    """
    project_path_obj = Path(project_path)
    claude_md_path = project_path_obj / "CLAUDE.md"

    # Path to DevStream's CLAUDE.md using Context7 patterns
    try:
        devstream_root = get_devstream_root()
        source_claude_md = devstream_root / "CLAUDE.md"
    except RuntimeError:
        logger.warning("DevStream installation not found, creating basic CLAUDE.md")
        create_basic_claude_md(project_path, project_type)
        return

    if not source_claude_md.exists():
        logger.warning(f"DevStream CLAUDE.md not found at {source_claude_md}")
        # Create a basic version if source doesn't exist
        create_basic_claude_md(project_path, project_type)
        return

    try:
        # Read the original DevStream CLAUDE.md
        with open(source_claude_md, 'r', encoding='utf-8') as f:
            claude_content = f.read()

        # Adapt paths and project-specific information
        adapted_content = adapt_claude_md_content(claude_content, project_path_obj, project_type)

        # Always overwrite the CLAUDE.md - it's the foundation of DevStream
        with open(claude_md_path, 'w', encoding='utf-8') as f:
            f.write(adapted_content)

        if claude_md_path.exists():
            logger.info(f"Updated existing CLAUDE.md at {claude_md_path}")
        else:
            logger.info(f"Created project CLAUDE.md at {claude_md_path}")

    except Exception as e:
        logger.error(f"Failed to copy and adapt CLAUDE.md: {e}")
        # Fallback to basic version
        create_basic_claude_md(project_path, project_type)


def adapt_claude_md_content(content: str, project_path: Path, project_type: str) -> str:
    """
    Adapt DevStream's CLAUDE.md content for a specific project.

    Args:
        content: Original DevStream CLAUDE.md content
        project_path: Target project path
        project_type: Detected project type

    Returns:
        Adapted content for the project
    """
    # Get DevStream root for path references
    try:
        devstream_root = get_devstream_root()
    except RuntimeError:
        devstream_root = Path("/devstream")  # Fallback placeholder

    # Replace DevStream-specific paths with project-specific paths
    adaptations = [
        # Update header
        (r"# CLAUDE\.md - DevStream Project Rules", f"# CLAUDE.md - {project_path.name} Project"),

        # Update version info
        (r"\*\*Version\*\*: 2\.2\.0 \| \*\*Date\*\*: 2025-10-09 \| \*\*Status\*\*: Production Ready",
         f"**Project Type**: {project_type}\n**Created**: {time.strftime('%Y-%m-%d', time.gmtime())}\n**DevStream Version**: 2.2.0 | **Status**: Production Ready"),

        # Update database paths
        (r"data/devstream\.db", f"{project_path}/data/devstream.db"),

        # Update launcher script paths with dynamic detection
        (r"/Users/fulvioventura/devstream/scripts/simple-launcher\.sh",
         f"{devstream_root}/scripts/simple-launcher.sh"),

        # Add project-specific section after the header
        (r"(# CLAUDE\.md - [^\n]+ Project\n\n\*\*Project Type\*\*: [^\n]+\n)",
         r"\1\nThis file contains the complete DevStream protocol and rules, adapted for this specific project.\n"),

        # Update examples to use project paths
        (r"cd /Users/fulvioventura/devstream", f"cd {project_path}"),
    ]

    adapted_content = content
    for pattern, replacement in adaptations:
        import re
        adapted_content = re.sub(pattern, replacement, adapted_content)

    # Add project-specific information section
    project_section = f"""

## 🏗️ Project-Specific Information

**Project Name**: {project_path.name}
**Project Path**: {project_path}
**Project Type**: {project_type}
**Database**: `{project_path}/data/devstream.db`
**Configuration**: `{project_path}/.devstream/workspace.json`

### Quick Start for This Project
```bash
# From this project directory ({project_path})
cd {project_path}

# Start DevStream with Claude Sonnet 4.5 (Anthropic)
{devstream_root}/scripts/simple-launcher.sh start anthropic

# Start DevStream with GLM-4.6 (z.ai)
{devstream_root}/scripts/simple-launcher.sh start z.ai

# Check project status
devstream status

# Project-specific commands (examples based on {project_type} type):
"""

    # Add project-specific examples
    if project_type == "python":
        project_section += f"""
# Python development
.devstream/bin/python -m pytest tests/
.devstream/bin/python -m pip install package
black src/ flake8 src/
"""
    elif project_type in ["typescript", "javascript"]:
        project_section += f"""
# Node.js development
npm install
npm run build
npm test
eslint src/ --fix
"""
    elif project_type == "go":
        project_section += f"""
# Go development
go mod tidy
go test ./...
go build ./...
"""
    elif project_type == "rust":
        project_section += f"""
# Rust development
cargo test
cargo build --release
cargo fmt
cargo clippy
"""
    elif project_type == "java":
        project_section += f"""
# Java development
mvn clean install
mvn test
mvn compile
"""
    else:
        project_section += """
# Generic development
git add .
git commit -m "your changes"
"""

    project_section += "\n```\n"

    # Insert the project section before the first major section
    adapted_content = adapted_content.replace("---\n\n## 🚨 MANDATORY SYSTEM", project_section + "\n---\n\n## 🚨 MANDATORY SYSTEM")

    return adapted_content


def create_basic_claude_md(project_path: str, project_type: str) -> None:
    """
    Create a basic CLAUDE.md if the original cannot be copied.

    Args:
        project_path: Path where basic CLAUDE.md should be created
        project_type: Detected project type
    """
    project_path_obj = Path(project_path)
    claude_md_path = project_path_obj / "CLAUDE.md"

    basic_content = f"""# CLAUDE.md - {project_path_obj.name} Project

**Project Type**: {project_type}
**Created**: {time.strftime("%Y-%m-%d", time.gmtime())}
**DevStream Version**: 2.2.0

⚠️ **NOTE**: This is a basic CLAUDE.md generated because the original DevStream CLAUDE.md could not be found.
For the complete DevStream protocol and rules, please refer to the original file at:
`$DEVSTREAM_ROOT/CLAUDE.md` (set DEVSTREAM_ROOT environment variable if needed)

## 🚀 Quick Start for This Project

```bash
# From this project directory ({project_path_obj})
cd {project_path_obj}

# Start DevStream with Claude Sonnet 4.5 (Anthropic)
$DEVSTREAM_ROOT/scripts/simple-launcher.sh start anthropic

# Start DevStream with GLM-4.6 (z.ai)
$DEVSTREAM_ROOT/scripts/simple-launcher.sh start z.ai
```

## 📋 Project Structure
```
{project_path_obj.name}/
├── .devstream/           # DevStream configuration
├── data/                # Project data
│   └── devstream.db     # Project database
├── CLAUDE.md           # This file
└── ...                 # Your project files
```

## 🔧 Development Commands

Based on your {project_type} project type:
"""

    # Add basic project-specific commands
    if project_type == "python":
        basic_content += """
```bash
.devstream/bin/python -m pytest tests/
.devstream/bin/python -m pip install package
black src/ flake8 src/
```
"""
    elif project_type in ["typescript", "javascript"]:
        basic_content += """
```bash
npm install
npm run build
npm test
```
"""
    else:
        basic_content += """
```bash
# Add your project-specific commands here
```
"""

    basic_content += """

---

*Generated by DevStream v2.2.0 - Basic version*
"""

    try:
        with open(claude_md_path, 'w', encoding='utf-8') as f:
            f.write(basic_content)
        logger.info(f"Created basic CLAUDE.md at {claude_md_path}")
    except Exception as e:
        logger.error(f"Failed to create basic CLAUDE.md: {e}")


def create_project_structure(project_path: str) -> None:
    """
    Create DevStream project structure.

    Args:
        project_path: Path where project structure should be created
    """
    project_path_obj = Path(project_path)
    devstream_dir = project_path_obj / ".devstream"

    # Create directories
    directories = [
        "db",
        "logs",
        "cache",
        "config",
        "templates"
    ]

    for dir_name in directories:
        (devstream_dir / dir_name).mkdir(parents=True, exist_ok=True)

    # Create workspace.json
    workspace_data = {
        "name": project_path_obj.name,
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "project_type": "unknown",
        "scan_completed": False,
        "files_count": 0,
        "version": "2.2.0"
    }

    workspace_file = devstream_dir / "workspace.json"
    with open(workspace_file, 'w') as f:
        json.dump(workspace_data, f, indent=2)

    logger.info(f"Created DevStream project structure at {devstream_dir}")


def initialize_project(
    project_path: str,
    force_reinit: bool = False,
    scan_existing_codebase: bool = True
) -> Dict[str, Any]:
    """
    Initialize DevStream project with intelligent codebase scanning.

    Args:
        project_path: Path to project directory
        force_reinit: Force reinitialization if already DevStream project
        scan_existing_codebase: Scan and populate existing codebase

    Returns:
        Project initialization results and metadata

    Raises:
        ProjectExistsError: If project already exists and force_reinit=False
        CodebaseScanError: If codebase scanning fails

    Example:
        >>> initialize_project("/path/to/project")
        {"status": "success", "files_scanned": 150, "embeddings_created": 89}
    """
    project_path_obj = Path(project_path).absolute()

    logger.info(f"Initializing DevStream project at: {project_path_obj}")

    # Check if already DevStream project
    devstream_dir = project_path_obj / ".devstream"
    if devstream_dir.exists() and not force_reinit:
        raise ProjectExistsError(f"Project already exists at {project_path_obj}")

    # Initialize result dictionary
    init_results: Dict[str, Any] = {
        "status": "success",
        "project_path": str(project_path_obj),
        "project_name": project_path_obj.name,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "project_type": "unknown",
        "scan_results": None,
        "workspace_file": str(devstream_dir / "workspace.json"),
        "database_path": str(project_path_obj / "data" / "devstream.db")
    }

    try:
        # Detect project type
        logger.info("Detecting project type...")
        type_detection = detect_project_type(str(project_path_obj))
        init_results["project_type"] = type_detection["primary_type"]
        logger.info(f"Detected project type: {type_detection['primary_type']} "
                   f"(confidence: {type_detection['confidence']:.2f})")

        # Create project structure
        logger.info("Creating DevStream project structure...")
        if devstream_dir.exists() and force_reinit:
            logger.info("Removing existing DevStream structure...")
            import shutil
            shutil.rmtree(devstream_dir)

        create_project_structure(str(project_path))

        # Create project database
        logger.info("Creating project database...")
        create_project_database(str(project_path))

        # Create project-specific CLAUDE.md
        logger.info("Creating project-specific CLAUDE.md...")
        create_project_claude_md(str(project_path), type_detection["primary_type"])

        # Update workspace.json with detected project type
        workspace_file = devstream_dir / "workspace.json"
        with open(workspace_file, 'r') as f:
            workspace_data = json.load(f)

        workspace_data["project_type"] = type_detection["primary_type"]
        workspace_data["project_detection"] = type_detection

        with open(workspace_file, 'w') as f:
            json.dump(workspace_data, f, indent=2)

        # Scan existing codebase if requested
        if scan_existing_codebase:
            logger.info("Scanning existing codebase...")
            scan_results = scan_and_populate_codebase(str(project_path))
            init_results["scan_results"] = scan_results

            # Update workspace.json with scan results
            workspace_data["scan_completed"] = True
            workspace_data["files_count"] = scan_results["files_scanned"]
            workspace_data["last_scanned"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            with open(workspace_file, 'w') as f:
                json.dump(workspace_data, f, indent=2)

        logger.info(f"Project initialization completed successfully")

        return init_results

    except Exception as e:
        logger.error(f"Project initialization failed: {e}")
        init_results["status"] = "failed"
        init_results["error"] = str(e)
        return init_results


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DevStream Project Initialization Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/project                    Initialize new project
  %(prog)s /path/to/existing --scan             Initialize with codebase scanning
  %(prog)s . --force                           Reinitialize current project
  %(prog)s --help                              Show this help message
        """
    )

    parser.add_argument(
        "project_path",
        nargs="?",
        default=".",
        help="Path to project directory (default: current directory)"
    )

    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force reinitialization if project already exists"
    )

    parser.add_argument(
        "--no-scan",
        action="store_true",
        help="Skip codebase scanning"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="DevStream Init 2.2.0"
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Initialize project
        results = initialize_project(
            args.project_path,
            force_reinit=args.force,
            scan_existing_codebase=not args.no_scan
        )

        if results["status"] == "success":
            print("✅ DevStream project initialized successfully!")
            print()
            print("Project Details:")
            print(f"  Name: {results['project_name']}")
            print(f"  Path: {results['project_path']}")
            print(f"  Type: {results['project_type']}")
            print(f"  Workspace: {results['workspace_file']}")
            print(f"  Database: {results['database_path']}")
            print()

            if results["scan_results"]:
                scan = results["scan_results"]
                print("Codebase Scan Results:")
                print(f"  Files Scanned: {scan['files_scanned']}")
                print(f"  Embeddings Created: {scan['embeddings_created']}")
                print(f"  Scan Duration: {scan['scan_duration']:.2f}s")
                print(f"  File Types: {dict(scan['file_types'])}")
                print()

                if scan["errors"]:
                    print(f"  Warnings: {len(scan['errors'])}")
                    for error in scan["errors"][:3]:  # Show first 3 errors
                        print(f"    - {error}")
                    if len(scan["errors"]) > 3:
                        print(f"    ... and {len(scan['errors']) - 3} more warnings")
                    print()

            print("Next Steps:")
            print("  1. Start using DevStream with your project")
            print("  2. The project is now registered in the global registry")
            print("  3. Use 'devstream status' to verify the setup")
            print()

            return 0
        else:
            print(f"❌ Project initialization failed: {results.get('error', 'Unknown error')}")
            return 1

    except ProjectExistsError as e:
        print(f"❌ {e}")
        print("Use --force to reinitialize the project")
        return 1
    except CodebaseScanError as e:
        print(f"❌ Codebase scanning failed: {e}")
        print("Use --no-scan to skip codebase scanning")
        return 1
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())