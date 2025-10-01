# Development Environment Setup

**Target Audience**: New contributors, developers
**Level**: Intermediate
**Type**: How-To Guide

## Prerequisites

Before setting up DevStream development environment, ensure you have:

- **Python 3.11+** - DevStream requires Python 3.11 or higher
- **Node.js 18+** - For MCP server development
- **Git** - Version control
- **SQLite 3.45+** - Built-in or via system package manager
- **Ollama** (optional) - For embedding generation (can run without)
- **Claude Code CLI** - Required for hook integration

### Verify Prerequisites

```bash
# Python version (must be 3.11+)
python3.11 --version  # Should output: Python 3.11.x

# Node.js version (must be 18+)
node --version  # Should output: v18.x or higher

# SQLite version (must be 3.45+)
sqlite3 --version  # Should output: 3.45.x or higher

# Git
git --version

# Ollama (optional)
ollama --version  # Optional - DevStream gracefully degrades without it
```

## Quick Start (5 Minutes)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/devstream.git
cd devstream

# 2. Run setup script (creates venv, installs dependencies)
./scripts/setup-development.sh

# 3. Initialize database
.devstream/bin/python scripts/initialize-database.py

# 4. Start MCP server (in separate terminal)
cd mcp-devstream-server
npm install
npm run build
npm run dev

# 5. Verify installation
./scripts/smoke-test.sh
```

**Expected output**: All tests pass, MCP server running, hooks active.

## Detailed Setup

### Step 1: Repository Setup

```bash
# Clone repository
git clone https://github.com/yourusername/devstream.git
cd devstream

# Create feature branch
git checkout -b feature/your-feature-name
```

### Step 2: Python Virtual Environment

**CRITICAL**: DevStream uses `.devstream` venv for ALL Python operations.

```bash
# Create virtual environment
python3.11 -m venv .devstream

# Activate venv (for manual testing)
source .devstream/bin/activate  # Linux/macOS
# .devstream\Scripts\activate  # Windows

# Verify Python version inside venv
.devstream/bin/python --version  # Must be 3.11.x

# Upgrade pip
.devstream/bin/python -m pip install --upgrade pip

# Install hook dependencies
.devstream/bin/python -m pip install -r requirements.txt

# Verify critical dependencies
.devstream/bin/python -m pip list | grep -E "(cchooks|aiohttp|structlog|ollama|sqlite-vec)"
```

**Expected output**:
```
cchooks               0.1.4
aiohttp               3.8.6
structlog             23.2.0
ollama                0.1.9
sqlite-vec            0.1.6
```

### Step 3: Database Initialization

```bash
# Initialize database with schema
.devstream/bin/python scripts/initialize-database.py

# Verify database created
ls -lh data/devstream.db  # Should exist

# Verify schema version
sqlite3 data/devstream.db "SELECT * FROM schema_version;"
# Expected output: 2.1.0|2025-10-01|Initial production schema

# Verify extensions loaded (optional)
.devstream/bin/python -c "
import sqlite3
from pathlib import Path

conn = sqlite3.connect('data/devstream.db')
conn.enable_load_extension(True)
conn.load_extension('vec0')
print('✅ vec0 extension loaded successfully')
conn.close()
"
```

### Step 4: MCP Server Setup

```bash
cd mcp-devstream-server

# Install Node dependencies
npm install

# Verify TypeScript compilation
npm run build

# Verify output files
ls -la dist/  # Should contain index.js, database.js, etc.

# Run smoke tests
npm run test
```

**Expected output**: All MCP server tests pass.

### Step 5: Hook System Configuration

**Location**: `.claude/settings.json`

```json
{
  "hooks": {
    "PreToolUse": [{
      "hooks": [{
        "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/memory/pre_tool_use.py"
      }]
    }],
    "PostToolUse": [{
      "hooks": [{
        "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/memory/post_tool_use.py"
      }]
    }]
  }
}
```

**Verify hook configuration**:
```bash
# Check settings.json exists
cat .claude/settings.json | jq '.hooks'

# Verify hook scripts executable
ls -l .claude/hooks/devstream/memory/*.py

# Test hook execution manually
.devstream/bin/python .claude/hooks/devstream/memory/pre_tool_use.py --help
```

### Step 6: Environment Configuration

**Location**: `.env.devstream`

```bash
# Copy example configuration
cp .env.example .env.devstream

# Edit configuration (use your preferred editor)
nano .env.devstream
```

**Development Configuration**:
```bash
# Memory System (ENABLED for development)
DEVSTREAM_MEMORY_ENABLED=true
DEVSTREAM_MEMORY_FEEDBACK_LEVEL=verbose  # verbose for development

# Context7 Integration
DEVSTREAM_CONTEXT7_ENABLED=true
DEVSTREAM_CONTEXT7_AUTO_DETECT=true
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=5000

# Context Injection
DEVSTREAM_CONTEXT_INJECTION_ENABLED=true
DEVSTREAM_CONTEXT_MAX_TOKENS=2000
DEVSTREAM_CONTEXT_RELEVANCE_THRESHOLD=0.5

# Agent Auto-Delegation
DEVSTREAM_AUTO_DELEGATION_ENABLED=true
DEVSTREAM_AUTO_DELEGATION_MIN_CONFIDENCE=0.85
DEVSTREAM_AUTO_DELEGATION_AUTO_APPROVE=0.95
DEVSTREAM_AUTO_DELEGATION_QUALITY_GATE=true

# Database
DEVSTREAM_DB_PATH=data/devstream.db

# Logging (DEBUG for development)
DEVSTREAM_LOG_LEVEL=DEBUG
DEVSTREAM_LOG_PATH=~/.claude/logs/devstream/

# Ollama (optional - graceful degradation if unavailable)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=nomic-embed-text
OLLAMA_TIMEOUT=30
```

### Step 7: Ollama Setup (Optional)

**Note**: DevStream works without Ollama but semantic search requires embeddings.

```bash
# Install Ollama (macOS)
brew install ollama

# Start Ollama service
ollama serve &

# Pull embedding model
ollama pull nomic-embed-text

# Verify model
ollama list  # Should show nomic-embed-text

# Test embedding generation
curl http://localhost:11434/api/embeddings -d '{
  "model": "nomic-embed-text",
  "prompt": "test embedding"
}'
```

**Expected output**: JSON with `embedding` array (768 dimensions).

## IDE Configuration

### VS Code Setup

**Extensions**:
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- TypeScript (built-in)
- SQLite Viewer (alexcvzz.vscode-sqlite)

**Settings** (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.devstream/bin/python",
  "python.linting.enabled": true,
  "python.linting.mypyEnabled": true,
  "python.linting.mypyArgs": [
    "--strict",
    "--ignore-missing-imports"
  ],
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "tests",
    "-v"
  ],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

**Launch Configuration** (`.vscode/launch.json`):
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Debug Hook",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "env": {
        "DEVSTREAM_LOG_LEVEL": "DEBUG",
        "DEVSTREAM_MEMORY_ENABLED": "true"
      }
    },
    {
      "name": "Node: Debug MCP Server",
      "type": "node",
      "request": "launch",
      "program": "${workspaceFolder}/mcp-devstream-server/dist/index.js",
      "args": ["${workspaceFolder}/data/devstream.db"],
      "console": "integratedTerminal"
    }
  ]
}
```

### PyCharm Setup

1. **Configure Interpreter**:
   - Settings → Project → Python Interpreter
   - Add Interpreter → Existing Environment
   - Select `.devstream/bin/python`

2. **Enable mypy**:
   - Settings → Tools → Python Integrated Tools
   - Type Checker: mypy
   - mypy arguments: `--strict --ignore-missing-imports`

3. **Configure pytest**:
   - Settings → Tools → Python Integrated Tools
   - Default test runner: pytest
   - pytest arguments: `tests -v`

## Debugging Techniques

### Debug Hook Execution

**Method 1: Verbose Logging**
```bash
# Enable DEBUG logging
export DEVSTREAM_LOG_LEVEL=DEBUG
export DEVSTREAM_MEMORY_FEEDBACK_LEVEL=verbose

# Trigger hook manually
echo '{"tool_name": "Write", "tool_input": {"file_path": "test.py", "content": "print(\"hello\")"}}' | \
  .devstream/bin/python .claude/hooks/devstream/memory/pre_tool_use.py

# Check logs
tail -f ~/.claude/logs/devstream/pre_tool_use.log
```

**Method 2: Interactive Debugging (pdb)**
```python
# Add breakpoint in hook code
import pdb; pdb.set_trace()

# Run hook
.devstream/bin/python .claude/hooks/devstream/memory/pre_tool_use.py
```

**Method 3: VS Code Debugger**
```bash
# Set breakpoint in hook file (click left margin in VS Code)
# Launch "Python: Debug Hook" configuration (F5)
# Hook will pause at breakpoint
```

### Debug MCP Server

**Method 1: Console Logging**
```typescript
// Add console.error() in MCP server code (stdout reserved for MCP protocol)
console.error('DEBUG: Variable value:', myVariable);

// Restart server
npm run dev

// Logs appear in terminal
```

**Method 2: Node Debugger**
```bash
# Start server in debug mode
node --inspect-brk dist/index.js data/devstream.db

# Attach Chrome DevTools
# Open chrome://inspect
# Click "inspect" on target
```

**Method 3: VS Code Debugger**
```bash
# Set breakpoint in TypeScript source
# Launch "Node: Debug MCP Server" configuration (F5)
# Server will pause at breakpoint
```

### Debug Database Queries

**Method 1: SQLite CLI**
```bash
# Open database
sqlite3 data/devstream.db

# Enable query timing
.timer on

# Test query
SELECT COUNT(*) FROM semantic_memory;

# View execution plan
EXPLAIN QUERY PLAN SELECT * FROM vec_semantic_memory WHERE embedding MATCH ? AND k = 10;

# Exit
.quit
```

**Method 2: Database Logging**
```python
# Enable SQLite trace (add to database.py)
conn.set_trace_callback(lambda query: print(f"SQL: {query}"))
```

## Local Testing Workflow

### Unit Tests

```bash
# Run all unit tests
.devstream/bin/python -m pytest tests/unit/ -v

# Run specific test file
.devstream/bin/python -m pytest tests/unit/test_memory.py -v

# Run with coverage
.devstream/bin/python -m pytest tests/unit/ --cov=.claude/hooks/devstream --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
# xdg-open htmlcov/index.html  # Linux
```

### Integration Tests

```bash
# Run integration tests (requires MCP server running)
.devstream/bin/python -m pytest tests/integration/ -v

# Run specific integration test
.devstream/bin/python -m pytest tests/integration/test_end_to_end.py -v
```

### MCP Server Tests

```bash
cd mcp-devstream-server

# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run specific test
npm test -- test_hybrid_search.js
```

### Manual Smoke Test

```bash
# Run comprehensive smoke test
./scripts/smoke-test.sh

# Expected output:
# ✅ Python version check
# ✅ Node.js version check
# ✅ Database schema validation
# ✅ Hook execution test
# ✅ MCP server connectivity
# ✅ Embedding generation test
# ✅ Vector search test
# ✅ Memory storage test
```

## Performance Profiling

### Profile Hook Execution

```bash
# Profile with py-spy
.devstream/bin/python -m pip install py-spy

# Record hook execution
py-spy record -o profile.svg -- .devstream/bin/python .claude/hooks/devstream/memory/pre_tool_use.py

# View flamegraph
open profile.svg
```

### Profile Database Queries

```bash
# Enable SQLite profiling
sqlite3 data/devstream.db

.eqp on  # Enable query plan display
.timer on  # Enable timing

# Run query
SELECT memory_id, distance
FROM vec_semantic_memory
WHERE embedding MATCH ? AND k = 10;

# View execution time and query plan
```

## Common Issues and Solutions

### Issue 1: Hook Not Executing

**Symptoms**: No context injection, no memory storage

**Diagnosis**:
```bash
# Check hook configuration
cat .claude/settings.json | jq '.hooks'

# Verify hook scripts exist
ls -l .claude/hooks/devstream/memory/

# Test hook execution manually
.devstream/bin/python .claude/hooks/devstream/memory/pre_tool_use.py
```

**Solution**:
```bash
# Verify .devstream venv exists
ls -la .devstream/bin/python

# Reinstall dependencies
.devstream/bin/python -m pip install -r requirements.txt

# Check environment variables
cat .env.devstream | grep ENABLED

# Restart Claude Code
claude code restart
```

### Issue 2: MCP Server Not Responding

**Symptoms**: Tools not available in Claude Code

**Diagnosis**:
```bash
# Check server process
ps aux | grep "node.*mcp-devstream-server"

# Check server logs
tail -f mcp-devstream-server/devstream-server.log

# Test server connectivity
echo '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' | \
  node mcp-devstream-server/dist/index.js data/devstream.db
```

**Solution**:
```bash
# Rebuild server
cd mcp-devstream-server
npm run build

# Check database path
ls -la data/devstream.db  # Must exist

# Restart server
npm run dev
```

### Issue 3: Vector Search Not Working

**Symptoms**: Semantic search returns no results

**Diagnosis**:
```bash
# Verify vec0 extension loaded
sqlite3 data/devstream.db "SELECT vec_version();"

# Check embeddings exist
sqlite3 data/devstream.db "SELECT COUNT(*) FROM vec_semantic_memory;"
```

**Solution**:
```bash
# Rebuild vec_semantic_memory
.devstream/bin/python scripts/rebuild-vector-index.py

# Verify Ollama running
curl http://localhost:11434/api/tags

# Regenerate embeddings
.devstream/bin/python scripts/regenerate-embeddings.py
```

### Issue 4: Import Errors in Hooks

**Symptoms**: `ModuleNotFoundError` when running hooks

**Diagnosis**:
```bash
# Check Python path
.devstream/bin/python -c "import sys; print('\n'.join(sys.path))"

# Verify dependencies installed
.devstream/bin/python -m pip list
```

**Solution**:
```bash
# Reinstall all dependencies
.devstream/bin/python -m pip install -r requirements.txt --force-reinstall

# Verify cchooks version (must be 0.1.4+)
.devstream/bin/python -m pip show cchooks

# Add missing dependencies to requirements.txt
echo "missing-package>=1.0.0" >> requirements.txt
.devstream/bin/python -m pip install -r requirements.txt
```

## Development Best Practices

### Code Quality Checklist

- ✅ All functions have type hints (`def func(arg: str) -> bool:`)
- ✅ All functions have docstrings (Google style)
- ✅ Code passes mypy strict mode (`mypy --strict hooks/`)
- ✅ Code formatted with black (`black .claude/hooks/`)
- ✅ Imports sorted with isort (`isort .claude/hooks/`)
- ✅ Tests written for new functionality (95%+ coverage)
- ✅ No print() statements (use structlog)
- ✅ Error handling with try/except and logging
- ✅ Configuration via environment variables (not hardcoded)
- ✅ Graceful degradation for optional features

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes
# ... edit files ...

# Run quality checks
./scripts/quality-check.sh

# Commit with conventional commit message
git add .
git commit -m "feat: add semantic memory hybrid search"

# Push and create PR
git push origin feature/your-feature-name
```

### Testing Before Commit

```bash
# Run all tests
./scripts/run-all-tests.sh

# Expected output:
# ✅ Unit tests: 45/45 passed
# ✅ Integration tests: 12/12 passed
# ✅ Type checking: 0 errors
# ✅ Code formatting: OK
# ✅ Linting: 0 warnings
```

## Next Steps

- Read [Hook System Deep Dive](./hook-system.md) for hook development
- Read [Testing Guide](./testing.md) for testing strategies
- Read [MCP Server Guide](./mcp-server.md) for MCP server development
- Join contributor Slack channel for questions

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-01
**Contributors**: DevStream Team
