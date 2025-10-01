# DevStream Installation Guide

**Version**: 0.1.0-beta
**Last Updated**: 2025-10-01
**Estimated Time**: 5-10 minutes

This guide covers installing and configuring DevStream, an integrated task management and cross-session memory system for Claude Code.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Installation Steps](#installation-steps)
- [Configuration](#configuration)
- [Verification](#verification)
- [Post-Installation](#post-installation)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before installing DevStream, ensure your system meets these requirements:

### Required Software

| Software | Minimum Version | Purpose | Installation |
|----------|----------------|---------|--------------|
| **Python** | 3.11+ | Core runtime | [python.org](https://www.python.org/downloads/) |
| **Node.js** | 16+ | MCP server | [nodejs.org](https://nodejs.org/) |
| **Git** | 2.x | Version control | [git-scm.com](https://git-scm.com/) |
| **Claude Code** | Latest | AI development tool | Anthropic (required) |

### Optional Software

| Software | Purpose | Installation |
|----------|---------|--------------|
| **Ollama** | Semantic embeddings (recommended) | [ollama.ai](https://ollama.ai/) |
| **sqlite3** | Database inspection | Usually pre-installed |

### System Requirements

- **OS**: macOS, Linux, or Windows (WSL2)
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 500MB free space
- **Network**: Internet connection for initial setup

### Verify Prerequisites

```bash
# Check Python version (must be 3.11+)
python3.11 --version
# Expected: Python 3.11.x

# Check Node.js version (must be 16+)
node --version
# Expected: v16.x or higher

# Check npm version
npm --version
# Expected: 8.x or higher

# Check Git version
git --version
# Expected: git version 2.x
```

---

## Quick Start

For experienced users who want to get started immediately:

```bash
# Clone repository
git clone <repository-url>
cd devstream

# Run automated installation
./install.sh

# Configure environment
cp .env.example .env.devstream
# Edit .env.devstream with your settings

# Configure Claude Code hooks (see Configuration section)
# Start MCP server
cd mcp-devstream-server && npm start
```

**Note**: If using Ollama for semantic search:
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull embedding model
ollama pull nomic-embed-text
```

---

## Installation Steps

### Step 1: Clone Repository

```bash
# Clone DevStream repository
git clone <repository-url>
cd devstream

# Verify project structure
ls -la
# You should see: .claude/, mcp-devstream-server/, data/, scripts/, etc.
```

### Step 2: Run Installation Script

The `install.sh` script automates the entire setup process:

```bash
# Standard installation
./install.sh

# Installation with verbose output
./install.sh --verbose

# Dry-run (preview without making changes)
./install.sh --dry-run

# Skip optional steps without prompts
./install.sh --skip-optional
```

**What the installation script does**:

1. **Checks Prerequisites** - Validates Python 3.11+, Node.js 16+, Git
2. **Creates Virtual Environment** - `.devstream` venv with Python 3.11
3. **Installs Python Dependencies** - From `requirements.txt` + critical packages
4. **Initializes Database** - Creates `data/devstream.db` with full schema
5. **Builds MCP Server** - Installs npm dependencies and builds TypeScript
6. **Configures Hooks** - Displays hook configuration instructions

### Step 3: Python Environment Verification

After installation, verify the Python environment:

```bash
# Verify venv exists
ls -la .devstream/
# You should see: bin/, lib/, pyvenv.cfg

# Check Python version in venv
.devstream/bin/python --version
# Expected: Python 3.11.x

# Verify critical packages
.devstream/bin/python -m pip list | grep -E "(cchooks|aiohttp|structlog)"
# Expected output:
# cchooks       0.1.4
# aiohttp       3.8.0
# structlog     23.0.0
```

### Step 4: Database Verification

Verify the database was created correctly:

```bash
# Check database exists
ls -lh data/devstream.db
# Expected: ~100-500 KB file

# Inspect database schema (requires sqlite3)
sqlite3 data/devstream.db ".schema" | head -20
# Expected: CREATE TABLE statements

# Count tables
sqlite3 data/devstream.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
# Expected: 14 tables
```

### Step 5: MCP Server Verification

Verify the MCP server was built successfully:

```bash
# Check MCP server directory
cd mcp-devstream-server

# Verify node_modules exists
ls -la node_modules/
# Should contain: @modelcontextprotocol, better-sqlite3, ollama, etc.

# Verify build artifacts
ls -la dist/
# Should contain: index.js and other compiled files

# Return to project root
cd ..
```

---

## Configuration

### Environment Configuration

1. **Copy example environment file**:

```bash
cp .env.example .env.devstream
```

2. **Edit `.env.devstream`** with your settings:

```bash
# ==============================================
# DevStream Configuration
# ==============================================

# Memory System (MANDATORY)
DEVSTREAM_MEMORY_ENABLED=true
DEVSTREAM_MEMORY_FEEDBACK_LEVEL=minimal

# Context7 Integration (MANDATORY)
DEVSTREAM_CONTEXT7_ENABLED=true
DEVSTREAM_CONTEXT7_AUTO_DETECT=true
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=5000

# Context Injection (MANDATORY)
DEVSTREAM_CONTEXT_INJECTION_ENABLED=true
DEVSTREAM_CONTEXT_MAX_TOKENS=2000
DEVSTREAM_CONTEXT_RELEVANCE_THRESHOLD=0.5

# Agent Auto-Delegation (Phase 3)
DEVSTREAM_AUTO_DELEGATION_ENABLED=true
DEVSTREAM_AUTO_DELEGATION_MIN_CONFIDENCE=0.85
DEVSTREAM_AUTO_DELEGATION_AUTO_APPROVE=0.95
DEVSTREAM_AUTO_DELEGATION_QUALITY_GATE=true

# Database (MANDATORY)
DEVSTREAM_DB_PATH=data/devstream.db

# Logging (RECOMMENDED)
DEVSTREAM_LOG_LEVEL=INFO
DEVSTREAM_LOG_PATH=~/.claude/logs/devstream/

# Ollama (OPTIONAL - for semantic search)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

### Hook Configuration (Claude Code)

**MANDATORY**: Configure hooks in Claude Code to enable automation.

1. **Open Claude Code settings**:

```bash
# Settings file location
~/.claude/settings.json
```

2. **Add hook configuration** (copy this entire block):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/memory/pre_tool_use.py"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "hooks": [
          {
            "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/memory/post_tool_use.py"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/context/user_query_context_enhancer.py"
          }
        ]
      }
    ]
  }
}
```

**Important Notes**:
- Hooks **MUST** use `.devstream/bin/python` (NOT system Python)
- `$CLAUDE_PROJECT_DIR` is automatically set by Claude Code
- Hook scripts are in `.claude/hooks/devstream/`

### MCP Server Configuration (Optional)

If you need to customize MCP server settings:

1. **Edit `mcp-devstream-server/package.json`**:

```json
{
  "name": "mcp-devstream-server",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "start": "node dist/index.js",
    "build": "tsc"
  }
}
```

2. **Rebuild after changes**:

```bash
cd mcp-devstream-server
npm run build
cd ..
```

---

## Verification

Run the comprehensive verification script to validate your installation:

```bash
# Run verification script
.devstream/bin/python scripts/verify-install.py

# Verbose output
.devstream/bin/python scripts/verify-install.py --verbose

# Skip optional checks (Ollama, Git)
.devstream/bin/python scripts/verify-install.py --skip-optional

# JSON output (for automation)
.devstream/bin/python scripts/verify-install.py --json
```

### Expected Output

```
DevStream Installation Verification
═══════════════════════════════════════

[✓] Python Environment - Virtual Environment
    Status: PASS
    Message: Virtual environment exists
    Details: Location: /path/to/.devstream/bin/python

[✓] Python Environment - Python Version
    Status: PASS
    Message: Python 3.11.x
    Details: Python 3.11.x detected

[✓] Database - Database File
    Status: PASS
    Message: Database file exists and accessible
    Details: Size: 123.4 KB

[✓] MCP Server - Build Artifacts
    Status: PASS
    Message: MCP server built successfully

[✓] Hook Configuration - Hook: PreToolUse
    Status: PASS
    Message: Configured correctly

Summary:
  Total Checks: 20
  Passed: 18
  Warnings: 2
  Failed: 0
```

### Verification Exit Codes

- **0**: All checks passed (success)
- **1**: Warnings present (installation may work with limitations)
- **2**: Critical failures (installation incomplete)

---

## Post-Installation

### First Steps

1. **Start MCP Server** (in separate terminal):

```bash
cd mcp-devstream-server
npm start
# Server should start on port 3000
# Look for: "MCP DevStream Server listening on port 3000"
```

2. **Test Hook System** (Claude Code session):

```
# Create a simple file to trigger hooks
Write a test file: src/test.py with content "print('hello')"

# Check logs to verify hooks executed
tail -f ~/.claude/logs/devstream/pre_tool_use.log
tail -f ~/.claude/logs/devstream/post_tool_use.log
```

3. **Test Memory Storage**:

```python
# In Claude Code session
@python-specialist Create a FastAPI hello world endpoint

# After implementation, search memory
mcp__devstream__devstream_search_memory:
  query: "FastAPI hello world"
  limit: 5
```

### Scan Existing Codebase (Optional)

If installing DevStream in an existing project:

```bash
# Scan and store existing code in memory
.devstream/bin/python scripts/scan-codebase.py --directory src/
```

### Test Agent System

```bash
# Test agent auto-delegation
@tech-lead Analyze project architecture

# Test specific specialist
@python-specialist Review Python code quality in src/
```

---

## Troubleshooting

### Issue: Python Virtual Environment Not Found

**Symptom**: `bash: .devstream/bin/python: No such file or directory`

**Solution**:
```bash
# Recreate virtual environment
python3.11 -m venv .devstream

# Reinstall dependencies
.devstream/bin/python -m pip install --upgrade pip
.devstream/bin/python -m pip install -r requirements.txt
.devstream/bin/python -m pip install "cchooks>=0.1.4" "aiohttp>=3.8.0" "structlog>=23.0.0"
```

### Issue: Database Initialization Failed

**Symptom**: `devstream.db` not created or empty

**Solution**:
```bash
# Manually initialize database
.devstream/bin/python scripts/setup-db.py

# Check database was created
ls -lh data/devstream.db

# Verify schema
sqlite3 data/devstream.db ".schema" | head -20
```

### Issue: MCP Server Build Failed

**Symptom**: `dist/` directory not created or npm errors

**Solution**:
```bash
# Clear node_modules and reinstall
cd mcp-devstream-server
rm -rf node_modules package-lock.json
npm install

# Rebuild
npm run build

# Verify dist/ created
ls -la dist/
```

### Issue: Hooks Not Executing

**Symptom**: No logs in `~/.claude/logs/devstream/`

**Solution**:

1. **Check hooks configuration**:
```bash
# Verify settings.json exists
cat ~/.claude/settings.json | grep -A 5 "hooks"

# Verify hook scripts exist
ls -la .claude/hooks/devstream/memory/
```

2. **Check Python interpreter**:
```bash
# Hooks MUST use .devstream/bin/python
# Verify hook command in settings.json uses:
"$CLAUDE_PROJECT_DIR"/.devstream/bin/python
```

3. **Test hook manually**:
```bash
# Test PreToolUse hook
.devstream/bin/python .claude/hooks/devstream/memory/pre_tool_use.py

# Check for errors
tail -100 ~/.claude/logs/devstream/pre_tool_use.log
```

### Issue: Ollama Not Responding

**Symptom**: `Ollama not running` warning during verification

**Solution**:

1. **Install Ollama** (if not installed):
```bash
# macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
ollama serve
```

2. **Pull embedding model**:
```bash
ollama pull nomic-embed-text

# Verify model installed
ollama list
# Should show: nomic-embed-text
```

3. **Test Ollama API**:
```bash
# Test Ollama is responding
curl http://localhost:11434/api/tags
# Should return JSON with models list
```

### Issue: SQLite Extension Not Found

**Symptom**: `sqlite-vec extension not loaded`

**Solution**:

DevStream uses `sqlite-vec` for vector search. This is handled automatically by the MCP server, but if you encounter issues:

```bash
# Verify sqlite-vec in MCP server
cd mcp-devstream-server
npm list sqlite-vec
# Should show: sqlite-vec@x.x.x

# Reinstall if missing
npm install sqlite-vec

# Rebuild MCP server
npm run build
```

### Issue: Import Errors in Hooks

**Symptom**: `ModuleNotFoundError: No module named 'cchooks'`

**Solution**:
```bash
# Verify critical packages installed in venv
.devstream/bin/python -m pip list | grep -E "(cchooks|aiohttp|structlog)"

# Reinstall critical packages
.devstream/bin/python -m pip install "cchooks>=0.1.4" "aiohttp>=3.8.0" "structlog>=23.0.0" "python-dotenv>=1.0.0"

# Verify installation
.devstream/bin/python -c "import cchooks; print(cchooks.__version__)"
```

### Issue: MCP Server Not Starting

**Symptom**: `Error: Cannot find module` when running `npm start`

**Solution**:
```bash
cd mcp-devstream-server

# Check package.json exists
cat package.json

# Verify dist/ directory exists
ls -la dist/

# Rebuild if missing
npm run build

# Check for errors in build
npm run build 2>&1 | tee build.log

# Start with verbose logging
NODE_ENV=development npm start
```

### Getting Help

If you encounter issues not covered here:

1. **Check logs**:
```bash
# Hook logs
tail -100 ~/.claude/logs/devstream/pre_tool_use.log
tail -100 ~/.claude/logs/devstream/post_tool_use.log

# MCP server logs
cd mcp-devstream-server && npm start 2>&1 | tee server.log
```

2. **Run diagnostics**:
```bash
# Comprehensive verification
.devstream/bin/python scripts/verify-install.py --verbose

# Export diagnostics as JSON
.devstream/bin/python scripts/verify-install.py --json > diagnostics.json
```

3. **Review documentation**:
- [`README.md`](./README.md) - Project overview
- [`CLAUDE.md`](./CLAUDE.md) - Development rules
- [`docs/user-guide/`](./docs/user-guide/) - User guides

4. **Community support**:
- GitHub Issues: Report bugs or ask questions
- Project Wiki: Additional troubleshooting tips

---

## Next Steps

After successful installation:

1. **Read User Guides**:
   - [Getting Started Guide](docs/user-guide/getting-started.md)
   - [Core Concepts](docs/user-guide/core-concepts.md)
   - [Agent System Guide](docs/user-guide/agents-guide.md)

2. **Configure Advanced Features**:
   - [Configuration Guide](docs/user-guide/configuration.md)
   - Agent auto-delegation settings
   - Memory system tuning

3. **Start Using DevStream**:
   - Create your first task
   - Test semantic memory search
   - Invoke specialized agents

4. **Join the Community**:
   - Share your experience
   - Contribute improvements
   - Report issues

---

**Installation Complete!** DevStream is now ready for use with Claude Code.

For questions or issues, refer to:
- [Troubleshooting Guide](docs/user-guide/troubleshooting.md)
- [FAQ](docs/user-guide/faq.md)
- [GitHub Issues](https://github.com/yourusername/devstream/issues)
