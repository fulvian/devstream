# DevStream Troubleshooting Guide

**Version**: 0.1.0-beta
**Last Updated**: 2025-10-01

This guide covers common issues and their solutions for DevStream.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Hook System Issues](#hook-system-issues)
- [Memory System Issues](#memory-system-issues)
- [Context7 Issues](#context7-issues)
- [Agent System Issues](#agent-system-issues)
- [Database Issues](#database-issues)
- [Performance Issues](#performance-issues)
- [Getting Help](#getting-help)

---

## Installation Issues

### Issue: Python 3.11 Not Found

**Symptom**:
```bash
./install.sh
# Error: Python 3.11+ not found
```

**Solution**:

**macOS**:
```bash
# Install via Homebrew
brew install python@3.11

# Verify installation
python3.11 --version
# Expected: Python 3.11.x

# Create symlink if needed
ln -sf /usr/local/bin/python3.11 /usr/local/bin/python3
```

**Ubuntu/Debian**:
```bash
# Add deadsnakes PPA
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3.11-dev

# Verify installation
python3.11 --version
```

**Fedora/RHEL**:
```bash
# Install Python 3.11
sudo dnf install python3.11

# Verify installation
python3.11 --version
```

### Issue: Virtual Environment Creation Failed

**Symptom**:
```bash
python3.11 -m venv .devstream
# Error: ensurepip is not available
```

**Solution**:

**Ubuntu/Debian** (missing venv module):
```bash
# Install python3.11-venv
sudo apt install python3.11-venv

# Recreate venv
python3.11 -m venv .devstream
```

**macOS** (permission issues):
```bash
# Fix permissions
sudo chown -R $(whoami) .devstream

# Or recreate in home directory
python3.11 -m venv ~/.devstream
ln -sf ~/.devstream .devstream
```

### Issue: Node.js Version Too Old

**Symptom**:
```bash
node --version
# v14.x (need v16+)
```

**Solution**:

**Using nvm** (recommended):
```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Reload shell
source ~/.bashrc  # or ~/.zshrc

# Install Node.js 20 LTS
nvm install 20
nvm use 20

# Verify
node --version  # v20.x
```

**Using package manager**:

**macOS**:
```bash
brew install node
```

**Ubuntu**:
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs
```

### Issue: MCP Server Build Failed

**Symptom**:
```bash
cd mcp-devstream-server
npm run build
# Error: TypeScript compilation failed
```

**Solution**:

```bash
# Clear node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Reinstall dependencies
npm install

# Check for TypeScript errors
npm run build 2>&1 | tee build.log

# If errors persist, check Node.js version
node --version  # Should be 16+

# Update TypeScript if needed
npm install -g typescript@latest
npm install typescript@latest
```

---

## Hook System Issues

### Issue: Hooks Not Executing

**Symptom**: No logs in `~/.claude/logs/devstream/`, no context injection

**Diagnosis**:
```bash
# Check if log directory exists
ls -la ~/.claude/logs/devstream/

# Check hook configuration
cat ~/.claude/settings.json | grep -A 20 "hooks"

# Check hook scripts exist
ls -la .claude/hooks/devstream/memory/
```

**Solutions**:

**1. Hook configuration missing**:
```bash
# Verify settings.json exists
cat ~/.claude/settings.json

# If missing or invalid, recreate:
cat > ~/.claude/settings.json << 'EOF'
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
EOF
```

**2. Hook scripts not executable**:
```bash
# Make hooks executable
chmod +x .claude/hooks/devstream/memory/*.py
chmod +x .claude/hooks/devstream/context/*.py
```

**3. Wrong Python interpreter**:
```bash
# Hooks MUST use .devstream/bin/python
# Check settings.json uses:
grep ".devstream/bin/python" ~/.claude/settings.json

# Should output:
# "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python ..."
```

**4. Test hooks manually**:
```bash
# Test PreToolUse hook
echo '{"tool_use": {"name": "Write", "input": {"file_path": "test.py"}}, "user_prompt": "test"}' | \
  .devstream/bin/python .claude/hooks/devstream/memory/pre_tool_use.py

# Check for errors
tail -50 ~/.claude/logs/devstream/pre_tool_use.log
```

### Issue: Import Errors in Hooks

**Symptom**:
```
ModuleNotFoundError: No module named 'cchooks'
```

**Solution**:
```bash
# Verify venv packages
.devstream/bin/python -m pip list | grep -E "(cchooks|aiohttp|structlog)"

# Reinstall critical packages
.devstream/bin/python -m pip install \
  "cchooks>=0.1.4" \
  "aiohttp>=3.8.0" \
  "structlog>=23.0.0" \
  "python-dotenv>=1.0.0"

# Verify import works
.devstream/bin/python -c "import cchooks; print(cchooks.__version__)"

# If still fails, recreate venv
rm -rf .devstream
python3.11 -m venv .devstream
.devstream/bin/python -m pip install -r requirements.txt
.devstream/bin/python -m pip install cchooks aiohttp structlog python-dotenv
```

### Issue: Hook Execution Timeout

**Symptom**: Hooks take > 30 seconds, Claude Code times out

**Solution**:

**1. Reduce Context7 token budget**:
```bash
# Edit .env.devstream
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=3000  # Reduced from 5000
```

**2. Reduce memory search limit**:
```python
# Edit .claude/hooks/devstream/memory/pre_tool_use.py
# Change search limit from 10 to 5
memory_results = await self.search_memory(query, limit=5)
```

**3. Disable Ollama embeddings temporarily**:
```bash
# Edit .env.devstream
OLLAMA_FALLBACK_MODE=graceful
# Stop Ollama service (hooks will skip embedding generation)
```

**4. Check database performance**:
```bash
# Enable WAL mode for better concurrency
sqlite3 data/devstream.db "PRAGMA journal_mode=WAL;"

# Rebuild indexes
sqlite3 data/devstream.db "REINDEX; ANALYZE;"
```

---

## Memory System Issues

### Issue: Memory Not Being Stored

**Symptom**: No new entries in `semantic_memory` table after file edits

**Diagnosis**:
```bash
# Check PostToolUse log
tail -50 ~/.claude/logs/devstream/post_tool_use.log

# Query memory table
sqlite3 data/devstream.db "SELECT COUNT(*) FROM semantic_memory;"

# Check recent entries
sqlite3 data/devstream.db "SELECT id, content_type, created_at FROM semantic_memory ORDER BY created_at DESC LIMIT 5;"
```

**Solutions**:

**1. Check memory is enabled**:
```bash
# Verify .env.devstream
grep DEVSTREAM_MEMORY_ENABLED .env.devstream
# Should be: DEVSTREAM_MEMORY_ENABLED=true
```

**2. Check database permissions**:
```bash
# Database must be writable
ls -l data/devstream.db
# Should show: rw-r--r-- or rw-rw-r--

# Fix permissions if needed
chmod 664 data/devstream.db
```

**3. Check PostToolUse hook logs for errors**:
```bash
tail -100 ~/.claude/logs/devstream/post_tool_use.log | grep -i error
```

**4. Test memory storage manually**:
```python
mcp__devstream__devstream_store_memory:
  content: "Test content"
  content_type: "code"
  keywords: ["test"]
```

### Issue: Memory Search Returns No Results

**Symptom**: Memory exists but search returns empty

**Diagnosis**:
```bash
# Check memory count
sqlite3 data/devstream.db "SELECT COUNT(*) FROM semantic_memory;"

# Check if FTS5 index populated
sqlite3 data/devstream.db "SELECT COUNT(*) FROM fts_semantic_memory;"

# Test FTS5 search
sqlite3 data/devstream.db "SELECT * FROM fts_semantic_memory WHERE fts_semantic_memory MATCH 'python' LIMIT 5;"
```

**Solutions**:

**1. Rebuild FTS5 index**:
```sql
-- Connect to database
sqlite3 data/devstream.db

-- Rebuild FTS5 index
INSERT INTO fts_semantic_memory(fts_semantic_memory) VALUES('rebuild');

-- Verify
SELECT COUNT(*) FROM fts_semantic_memory;
```

**2. Check relevance threshold**:
```bash
# Edit .env.devstream
DEVSTREAM_CONTEXT_RELEVANCE_THRESHOLD=0.3  # Lower threshold (was 0.5)
```

**3. Check embeddings exist**:
```bash
# Check if embeddings are NULL
sqlite3 data/devstream.db \
  "SELECT COUNT(*) FROM semantic_memory WHERE embedding IS NULL;"

# If many NULL, regenerate embeddings
.devstream/bin/python .claude/hooks/devstream/memory/backfill_embeddings.py
```

### Issue: Ollama Embeddings Failing

**Symptom**:
```
Warning: Embedding generation failed: Connection refused
```

**Diagnosis**:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Check if model installed
ollama list | grep nomic-embed-text
```

**Solutions**:

**1. Start Ollama service**:
```bash
# Start Ollama
ollama serve

# In another terminal, verify
curl http://localhost:11434/api/tags
```

**2. Install embedding model**:
```bash
ollama pull nomic-embed-text

# Verify
ollama list
# Should show: nomic-embed-text
```

**3. Test embedding generation**:
```bash
curl http://localhost:11434/api/embeddings -d '{
  "model": "nomic-embed-text",
  "prompt": "test embedding"
}'
```

**4. Configure fallback mode** (graceful degradation):
```bash
# Edit .env.devstream
OLLAMA_FALLBACK_MODE=graceful
# Hooks will continue without embeddings if Ollama unavailable
```

---

## Context7 Issues

### Issue: Context7 Not Retrieving Docs

**Symptom**: No Context7 documentation in PreToolUse logs

**Diagnosis**:
```bash
# Check PreToolUse log
tail -100 ~/.claude/logs/devstream/pre_tool_use.log | grep -i context7

# Check if Context7 enabled
grep DEVSTREAM_CONTEXT7_ENABLED .env.devstream

# Check MCP server running
curl http://localhost:3000/health
```

**Solutions**:

**1. Enable Context7**:
```bash
# Edit .env.devstream
DEVSTREAM_CONTEXT7_ENABLED=true
```

**2. Check MCP server running**:
```bash
# Start MCP server
cd mcp-devstream-server
npm start

# Verify server running
curl http://localhost:3000/health
# Expected: {"status": "ok"}
```

**3. Test Context7 manually**:
```python
# Resolve library ID
mcp__context7__resolve-library-id:
  libraryName: "fastapi"

# Expected: /tiangolo/fastapi

# Get library docs
mcp__context7__get-library-docs:
  context7CompatibleLibraryID: "/tiangolo/fastapi"
  tokens: 1000
```

**4. Check Context7 detection threshold**:
```bash
# Edit .env.devstream
DEVSTREAM_CONTEXT7_DETECTION_THRESHOLD=0.5  # Lower threshold (was 0.7)
```

---

## Agent System Issues

### Issue: Agent Not Responding

**Symptom**: `@python-specialist` invoked but no response

**Diagnosis**:
```bash
# Check agent files exist
ls -la .claude/agents/domain/python-specialist.md

# Check agent format
head -20 .claude/agents/domain/python-specialist.md
```

**Solutions**:

**1. Verify agent file exists**:
```bash
# List all agents
find .claude/agents -name "*.md"
```

**2. Check agent file format**:
```markdown
---
name: python-specialist
role: Python 3.11+ Domain Specialist
level: domain
tools: inherit_all
---

# Python Specialist

[... agent description ...]
```

**3. Recreate agent file if corrupted**:
```bash
# Backup current file
cp .claude/agents/domain/python-specialist.md .claude/agents/domain/python-specialist.md.bak

# Restore from git
git checkout .claude/agents/domain/python-specialist.md
```

### Issue: Auto-Delegation Not Working

**Symptom**: No agent suggestions for clear file patterns

**Diagnosis**:
```bash
# Check auto-delegation enabled
grep DEVSTREAM_AUTO_DELEGATION_ENABLED .env.devstream

# Check PreToolUse log for delegation analysis
tail -100 ~/.claude/logs/devstream/pre_tool_use.log | grep -i delegation
```

**Solutions**:

**1. Enable auto-delegation**:
```bash
# Edit .env.devstream
DEVSTREAM_AUTO_DELEGATION_ENABLED=true
DEVSTREAM_AUTO_DELEGATION_AUTO_APPROVE=0.95
DEVSTREAM_AUTO_DELEGATION_MIN_CONFIDENCE=0.85
```

**2. Check pattern matcher**:
```bash
# Test pattern matcher manually
.devstream/bin/python -c "
from agents.pattern_matcher import PatternMatcher
matcher = PatternMatcher()
result = matcher.match(['src/api/users.py'])
print(result)
"
```

**3. Lower confidence thresholds** (more delegation):
```bash
# Edit .env.devstream
DEVSTREAM_AUTO_DELEGATION_AUTO_APPROVE=0.90  # Was 0.95
```

---

## Database Issues

### Issue: Database Locked

**Symptom**:
```
Error: database is locked
```

**Solution**:

**1. Close connections**:
```bash
# Find processes using database
lsof data/devstream.db

# Kill if necessary
kill <PID>
```

**2. Enable WAL mode** (prevents locks):
```bash
sqlite3 data/devstream.db "PRAGMA journal_mode=WAL;"
```

**3. Check for corrupted WAL file**:
```bash
# Remove WAL files (ONLY if no active connections)
rm -f data/devstream.db-wal data/devstream.db-shm

# Rebuild database from backup if corrupted
```

### Issue: Missing Tables

**Symptom**:
```
Error: no such table: semantic_memory
```

**Solution**:

**1. Reinitialize database**:
```bash
# Backup current database
cp data/devstream.db data/devstream.db.bak

# Recreate database
.devstream/bin/python scripts/setup-db.py

# Verify tables created
sqlite3 data/devstream.db ".schema" | grep "CREATE TABLE"
```

**2. Check schema version**:
```bash
sqlite3 data/devstream.db \
  "SELECT version, applied_at FROM schema_version ORDER BY applied_at DESC LIMIT 1;"
```

### Issue: SQLite Extensions Not Loaded

**Symptom**:
```
Error: no such module: vec0
```

**Solution**:

**1. Check MCP server has sqlite-vec**:
```bash
cd mcp-devstream-server
npm list sqlite-vec
# Should show: sqlite-vec@x.x.x
```

**2. Reinstall sqlite-vec**:
```bash
cd mcp-devstream-server
npm install sqlite-vec
npm run build
```

**3. Verify extension in database**:
```bash
# sqlite-vec is loaded by MCP server, not directly in SQLite
# Test via MCP server
curl http://localhost:3000/api/search -d '{"query": "test"}'
```

---

## Performance Issues

### Issue: Slow Context Injection

**Symptom**: PreToolUse hook takes > 10 seconds

**Solutions**:

**1. Reduce token budgets**:
```bash
# Edit .env.devstream
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=3000  # Was 5000
DEVSTREAM_CONTEXT_MAX_TOKENS=1500     # Was 2000
```

**2. Reduce memory search limit**:
```python
# Edit .claude/hooks/devstream/memory/pre_tool_use.py
memory_results = await self.search_memory(query, limit=5)  # Was 10
```

**3. Optimize database**:
```bash
# Enable WAL mode
sqlite3 data/devstream.db "PRAGMA journal_mode=WAL;"

# Rebuild indexes
sqlite3 data/devstream.db "REINDEX; ANALYZE;"

# Vacuum database (compact)
sqlite3 data/devstream.db "VACUUM;"
```

**4. Disable Context7 temporarily**:
```bash
# Edit .env.devstream
DEVSTREAM_CONTEXT7_ENABLED=false
```

### Issue: High Memory Usage

**Symptom**: Python hooks consuming > 500MB RAM

**Solutions**:

**1. Limit embedding cache**:
```python
# Edit .claude/hooks/devstream/utils/ollama_client.py
# Reduce cache size from 1000 to 100
self.embedding_cache = LRUCache(maxsize=100)
```

**2. Clear database WAL files periodically**:
```bash
# Checkpoint WAL (merge to main db)
sqlite3 data/devstream.db "PRAGMA wal_checkpoint(TRUNCATE);"
```

**3. Restart MCP server** (clears memory):
```bash
cd mcp-devstream-server
npm restart
```

---

## Getting Help

If your issue is not covered here:

### 1. Check Logs

```bash
# Hook logs
tail -100 ~/.claude/logs/devstream/pre_tool_use.log
tail -100 ~/.claude/logs/devstream/post_tool_use.log

# MCP server logs
cd mcp-devstream-server
npm start 2>&1 | tee server.log
```

### 2. Run Diagnostics

```bash
# Comprehensive verification
.devstream/bin/python scripts/verify-install.py --verbose

# Export diagnostics
.devstream/bin/python scripts/verify-install.py --json > diagnostics.json
```

### 3. Review Documentation

- [Installation Guide](../../INSTALLATION.md)
- [Configuration Guide](configuration.md)
- [FAQ](faq.md)

### 4. Community Support

- **GitHub Issues**: Report bugs or ask questions
- **Project Wiki**: Additional troubleshooting tips
- **Discord/Slack**: Community chat (if available)

### 5. Provide Diagnostic Information

When reporting issues, include:

```bash
# System information
uname -a
python3.11 --version
node --version
sqlite3 --version

# DevStream version
cat .claude/state/version.txt

# Verification report
.devstream/bin/python scripts/verify-install.py --json

# Recent logs
tail -100 ~/.claude/logs/devstream/*.log
```

---

**For urgent issues**: Create GitHub issue with `[URGENT]` prefix and diagnostic information.

**For feature requests**: Create GitHub issue with `[FEATURE]` prefix and use case description.
