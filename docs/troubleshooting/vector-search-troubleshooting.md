# DevStream Vector Search System - Troubleshooting Guide

This guide covers common issues and solutions for DevStream's semantic search system, including vector search functionality, embedding generation, and database operations.

## Table of Contents

1. [Quick Health Check](#quick-health-check)
2. [Common Issues](#common-issues)
   - [Vector Search Not Working](#vector-search-not-working)
   - [Missing Embeddings](#missing-embeddings)
   - [Database Connection Issues](#database-connection-issues)
   - [Ollama Embedding Service](#ollama-embedding-service)
   - [MCP Server Issues](#mcp-server-issues)
3. [Performance Issues](#performance-issues)
4. [Monitoring and Debugging](#monitoring-and-debugging)
5. [Recovery Procedures](#recovery-procedures)

## Quick Health Check

### Step 1: Check System Status

```bash
# 1. Check MCP health endpoint
curl -s http://localhost:9090/health | jq .

# 2. Check embedding coverage
.devstream/bin/python .claude/hooks/devstream/utils/embedding_coverage_monitor.py data/devstream.db

# 3. Verify Ollama service
curl -s http://localhost:11434/api/tags | jq '.models[].name'

# 4. Check database integrity
.devstream/bin/python -c "
import sqlite3
import sqlite_vec
db = sqlite3.connect('data/devstream.db')
db.enable_load_extension(True)
sqlite_vec.load(db)
print('✅ Database and extensions working')
"
```

### Expected Results

✅ **Healthy System**: All checks pass with no errors
✅ **Embedding Coverage**: Should be ≥95% for production
✅ **Ollama**: Should list `embeddinggemma:300m` model
✅ **Database**: Should load sqlite-vec extension successfully

---

## Common Issues

### Vector Search Not Working

#### Issue: "Vector search returns no results"

**Symptoms:**
- Hybrid search returns empty or incomplete results
- `sqlite3.OperationalError: no such module: vec0` errors
- Context7 search fails silently

**Root Causes:**
1. sqlite-vec extension not loaded
2. Missing embeddings in database
3. Incorrect database path configuration
4. MCP server using wrong database

**Solutions:**

##### Solution 1: Verify sqlite-vec Extension Loading

```bash
# Test extension loading
.devstream/bin/python -c "
import sqlite3
import sqlite_vec
db = sqlite3.connect('data/devstream.db')
db.enable_load_extension(True)
sqlite_vec.load(db)  # NOT: db.load_extension('vec0')
print('✅ sqlite-vec loaded successfully')

# Test vec0 function
result = db.execute('SELECT vec_length(json(\"[0.1, 0.2, 0.3]\"))').fetchone()
print(f'Veclen function working: {result}')
"
```

**If this fails:**
```bash
# Install sqlite-vec in correct environment
.devstream/bin/python -m pip install sqlite-vec
```

##### Solution 2: Check MCP Configuration

```bash
# Verify MCP server database path
cat .claude/mcp_servers.json
# Should show: "DEVSTREAM_DB_PATH": "${CLAUDE_PROJECT_DIR}/data/devstream.db"

# Restart MCP server if needed
pkill -f "node.*mcp-devstream-server"
# MCP will restart automatically on next request
```

##### Solution 3: Check Database Path Consistency

```bash
# Verify database path exists and is correct
ls -la data/devstream.db
file data/devstream.db  # Should show: SQLite 3.x database

# Check if database has required tables
.devstream/bin/python -c "
import sqlite3
db = sqlite3.connect('data/devstream.db')
tables = db.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
print('Tables:', [t[0] for t in tables])
print('Has semantic_memory:', 'semantic_memory' in [t[0] for t in tables])
"
```

### Missing Embeddings

#### Issue: "No embeddings in database"

**Symptoms:**
- Vector search returns text-only results
- Coverage monitor shows 0% or very low percentage
- Embedding generation failures in PostToolUse hook

**Root Causes:**
1. Ollama embedding service not running
2. Backfill process not started or failed
3. PostToolUse hook failures (retry issues)
4. Insufficient storage or permissions

**Solutions:**

##### Solution 1: Start Ollama Service

```bash
# Start Ollama with embedding model
docker run -d --gpus all -v ollama:/root/.ollama -p 11434:11434 ollama/ollama

# Pull embedding model
docker exec ollama ollama pull embeddinggemma:300m

# Verify service
curl -s http://localhost:11434/api/tags | jq '.models[].name'
# Should include: "embeddinggemma:300m"
```

##### Solution 2: Run Backfill Process

```bash
# Test backfill with small sample
.devstream/bin/python test-backfill-dryrun.py

# Run full backfill if dry-run succeeds
.devstream/bin/python full-backfill.py

# Monitor progress
tail -f full-backfill.log  # or watch the terminal output
```

##### Solution 3: Check PostToolUse Hook Retry Logic

```bash
# Test PostToolUse hook with retry logic
.devstream/bin/python test-retry-simple.py

# Verify hook logs
tail -f ~/.claude/logs/devstream/hook_execution.log | grep -E "(retry|error|embed)"
```

### Database Connection Issues

#### Issue: "Database connection failed"

**Symptoms:**
- `sqlite3.OperationalError: unable to open database file`
- MCP server fails to start
- Hook execution fails with database errors

**Root Causes:**
1. Incorrect database path
2. Missing database file
3. Permission issues
4. Database corruption

**Solutions:**

##### Solution 1: Verify Database Path

```bash
# Check current working directory
pwd
ls -la data/

# Verify database exists
if [ -f "data/devstream.db" ]; then
    echo "✅ Database exists"
else
    echo "❌ Database not found"
    # Initialize database if needed
fi

# Check database integrity
.devstream/bin/python -c "
import sqlite3
try:
    db = sqlite3.connect('data/devstream.db')
    result = db.execute('PRAGMA integrity_check').fetchall()
    print('✅ Database integrity OK')
except Exception as e:
    print(f'❌ Database error: {e}')
"
```

##### Solution 2: Fix Permissions

```bash
# Check database file permissions
ls -la data/devstream.db
# Should be readable/writable by current user

# Fix permissions if needed
chmod 664 data/devstream.db
chown $USER:$USER data/devstream.db

# Check directory permissions
ls -ld data/
```

##### Solution 3: Database Recovery

```bash
# Backup existing database
cp data/devstream.db data/devstream.db.backup.$(date +%Y%m%d_%H%M%S)

# Check database for corruption
.devstream/bin/python -c "
import sqlite3
db = sqlite3.connect('data/devstream.db')
try:
    db.execute('SELECT COUNT(*) FROM semantic_memory')
    print('✅ Database accessible')
except sqlite3.DatabaseError as e:
    print(f'❌ Database corrupted: {e}')
    # May need to restore from backup
"
```

### Ollama Embedding Service

#### Issue: "Ollama embedding generation failed"

**Symptoms:**
- PostToolUse hook shows embedding generation errors
- Backfill process fails with connection errors
- Timeout errors during embedding generation

**Root Causes:**
1. Ollama service not running
2. Wrong embedding model name
3. Network connectivity issues
4. Insufficient GPU/CPU resources

**Solutions:**

##### Solution 1: Start Ollama Service

```bash
# Start Ollama with proper configuration
docker run -d --name ollama \
  --gpus all \
  -v ollama:/root/.ollama \
  -p 11434:11434 \
  ollama/ollama serve

# Verify service is running
curl -s http://localhost:11434/api/tags

# Pull required embedding model
docker exec ollama ollama pull embeddinggemma:300m
```

##### Solution 2: Verify Model Availability

```bash
# List available models
curl -s http://localhost:11434/api/tags | jq '.models[] | select(.name, .size)'

# Verify embeddinggemma:300m is available
if curl -s http://localhost:11434/api/tags | grep -q "embeddinggemma:300m"; then
    echo "✅ embeddinggemma:300m available"
else
    echo "❌ embeddinggemma:300m not found, pulling..."
    docker exec ollama ollama pull embeddinggemma:300m
fi
```

##### Solution 3: Test Embedding Generation

```bash
# Test embedding generation
curl -s http://localhost:11434/api/embed \
  -H "Content-Type: application/json" \
  -d '{
    "model": "embeddinggemma:300m",
    "input": "test embedding generation"
  }' | jq '.embeddings[0] | length'

# Should return: 768 (embedding dimension)
```

### MCP Server Issues

#### Issue: "MCP server not responding"

**Symptoms:**
- Claude Code shows "MCP unavailable" errors
- Memory storage fails silently
- Context injection not working

**Root Causes:**
1. MCP server not started
2. Port conflicts
3. Database connection issues
4. Configuration errors

**Solutions:**

##### Solution 1: Check MCP Server Status

```bash
# Check if MCP server process is running
ps aux | grep "mcp-devstream-server"

# Check health endpoint
curl -s http://localhost:9090/health | jq '.status'

# Check logs
tail -f ~/.claude/logs/devstream/mcp_server.log
```

##### Solution 2: Restart MCP Server

```bash
# Kill existing MCP server processes
pkill -f "node.*mcp-devstream-server"

# MCP will restart automatically on next request
# Or manually start:
cd mcp-devstream-server && npm run start

# Verify startup
curl -s http://localhost:9090/health
```

##### Solution 3: Check Configuration

```bash
# Verify MCP configuration
cat .claude/mcp_servers.json

# Check database path
grep "DEVSTREAM_DB_PATH" .claude/mcp_servers.json

# Verify database exists at configured path
ls -la "$(grep -o 'data/devstream.db' .claude/mcp_servers.json | head -1)"
```

---

## Performance Issues

### Slow Search Performance

#### Issue: "Vector search queries are slow"

**Symptoms:**
- Hybrid search takes >5 seconds
- Timeouts during context injection
- Poor user experience

**Root Causes:**
1. Large database without proper indexing
2. Too many embeddings without filtering
3. Network latency to Ollama
4. Insufficient vector search optimization

**Solutions:**

##### Solution 1: Optimize Search Queries

```bash
# Monitor search performance
curl -s "http://localhost:9090/health" | jq '.metrics'

# Check embedding coverage - may need filtering
.devstream/bin/python .claude/hooks/devstream/utils/embedding_coverage_monitor.py data/devstream.db

# Add content type filtering to searches
# Example: Search only code and documentation
```

##### Solution 2: Database Optimization

```sql
-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_semantic_memory_content_type ON semantic_memory(content_type);
CREATE INDEX IF NOT EXISTS idx_semantic_memory_keywords ON semantic_memory(keywords);

-- Check database size and fragmentation
PRAGMA page_count;
PRAGMA page_size;
```

##### Solution 3: Reduce Context Injection Scope

```bash
# Adjust context injection settings in .env.devstream
# Reduce token budgets for faster responses
DEVSTREAM_CONTEXT7_TOKEN_BUDGET=3000  # Reduced from 5000
DEVSTREAM_CONTEXT_MAX_TOKENS=1500    # Reduced from 2000
DEVSTREAM_CONTEXT_RELEVANCE_THRESHOLD=0.05  # Increased from 0.03
```

### Memory Usage Issues

#### Issue: "High memory consumption"

**Symptoms:**
- System becomes slow during backfill
- OOM (Out of Memory) errors
- Database grows too large

**Root Causes:**
1. Backfill processing too many records at once
2. Embedding vectors stored inefficiently
3. Memory leaks in hooks

**Solutions:**

##### Solution 1: Optimize Backfill Batch Size

```python
# In full-backfill.py, adjust batch_size if needed
self.batch_size = 16  # Reduce from 32 if memory issues
```

##### Solution 2: Monitor Memory Usage

```bash
# Monitor system memory during backfill
watch -n 5 'free -h; echo "---"; ps aux | grep full-backfill'

# Monitor database size
watch -n 30 'ls -lh data/devstream.db'
```

---

## Monitoring and Debugging

### Real-time Monitoring

#### Embedding Coverage Monitor

```bash
# Generate real-time coverage report
.devstream/bin/python .claude/hooks/devstream/utils/embedding_coverage_monitor.py data/devstream.db

# Store coverage snapshots for trend analysis
# (Automatically stores to embedding_coverage_history table)
```

#### Health Endpoint Monitoring

```bash
# Continuous health monitoring
watch -n 30 'curl -s http://localhost:9090/health | jq ".status, .timestamp, .metrics.coverage_percent"'
```

#### Hook Execution Logs

```bash
# Monitor PostToolUse hook execution
tail -f ~/.claude/logs/devstream/hook_execution.log | grep -E "(retry|embed|error)"

# Monitor memory operations
tail -f ~/.claude/logs/devstream/hook_execution.log | grep -E "(store_memory|embedding)"
```

### Debug Commands

#### Vector Search Debugging

```bash
# Test vector search directly
.devstream/bin/python -c "
import sqlite3
import sqlite_vec
import json

db = sqlite3.connect('data/devstream.db')
db.enable_load_extension(True)
sqlite_vec.load(db)

# Test vector search with known embedding
test_embedding = json.dumps([0.1] * 768)
result = db.execute('''
    SELECT COUNT(*) as count
    FROM vec_semantic_memory
    WHERE distance(embedding, ?) < 0.5
''', (test_embedding,)).fetchone()

print(f'Veсtor search test: {result[0]} matches found')
"
```

#### Memory Search Debugging

```bash
# Test memory search via MCP
.devstream/bin/python -c "
import sys
sys.path.append('.claude/hooks/devstream/utils')
from hybrid_search import HybridSearch

searcher = HybridSearch('data/devstream.db')
results = searcher.hybrid_search('test query', limit=5)
print(f'Found {len(results)} results')
for r in results:
    print(f'  - {r[\"content_type\"]}: {r[\"content\"][:100]}...')
"
```

---

## Recovery Procedures

### Complete System Reset

#### Step 1: Backup Current Data

```bash
# Create backup directory
mkdir -p backups/$(date +%Y%m%d_%H%M%S)

# Backup database
cp data/devstream.db backups/$(date +%Y%m%d_%H%M%S)/

# Backup configuration
cp -r .claude backups/$(date +%Y%m%d_%H%M%S)/

# Backup MCP server
cp -r mcp-devstream-server backups/$(date +%Y%m%d_%H%M%S)/
```

#### Step 2: Stop All Services

```bash
# Stop backfill process if running
pkill -f full-backfill.py

# Stop Ollama
docker stop ollama 2>/dev/null || true

# Stop MCP server
pkill -f "node.*mcp-devstream-server"
```

#### Step 3: Reset and Restart

```bash
# Reset to clean state
# (Optional: Only if database is corrupted)

# Restart Ollama
docker run -d --gpus all -v ollama:/root/.ollama -p 11434:11434 ollama/ollama
docker exec ollama ollama pull embeddinggemma:300m

# MCP server will restart automatically on first request
# Verify health
curl -s http://localhost:9090/health

# Restart backfill if needed
.devstream/bin/python full-backfill.py
```

### Partial Recovery

#### Recover from Partial Backfill Failure

```bash
# Check current progress
.devstream/bin/python .claude/hooks/devstream/utils/embedding_coverage_monitor.py data/devstream.db

# Identify stuck batches
sqlite3 data/devstream.db "
SELECT
    content_type,
    COUNT(*) as missing_count
FROM semantic_memory
WHERE embedding IS NULL OR embedding = ''
GROUP BY content_type
ORDER BY missing_count DESC
"

# Restart backfill from last successful batch
# The backfill script automatically resumes from where it left off
.devstream/bin/python full-backfill.py
```

#### Recover Hook Failures

```bash
# Check hook logs for errors
tail -100 ~/.claude/logs/devstream/hook_execution.log | grep -A5 -B5 "error"

# Test hook functionality
.devstream/bin/python .claude/hooks/devstream/memory/post_tool_use.py

# Reset MCP connection if needed
pkill -f "node.*mcp-devstream-server"
```

---

## Contact and Support

### Getting Help

If you encounter issues not covered in this guide:

1. **Check Logs First**: Always check the relevant log files
2. **Run Health Checks**: Use the built-in monitoring tools
3. **Gather Information**: Collect error messages and system status
4. **Provide Context**: Include what you were trying to do when the error occurred

### Log Files to Check

- `~/.claude/logs/devstream/hook_execution.log` - Hook execution logs
- `~/.claude/logs/devstream/mcp_server.log` - MCP server logs
- `full-backfill.log` - Backfill process logs (if running)
- Ollama Docker logs: `docker logs ollama`

### Health Check Summary

```bash
echo "=== DevStream Vector Search Health Check ==="

# 1. Database Status
echo "1. Database:"
if [ -f "data/devstream.db" ]; then
    echo "   ✅ Database file exists"
    size=$(stat -f%z data/devstream.db)
    echo "   📊 Size: $((size / 1024 / 1024))MB"
else
    echo "   ❌ Database file missing"
fi

# 2. sqlite-vec Extension
echo -e "\n2. sqlite-vec Extension:"
.devstream/bin/python -c "
try:
    import sqlite3
    import sqlite_vec
    db = sqlite3.connect('data/devstream.db')
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    print('   ✅ Extension loaded successfully')
except Exception as e:
    print(f'   ❌ Extension failed: {e}')
" 2>/dev/null

# 3. Embedding Coverage
echo -e "\n3. Embedding Coverage:"
if .devstream/bin/python .claude/hooks/devstream/utils/embedding_coverage_monitor.py data/devstream.db 2>/dev/null; then
    echo "   ✅ Coverage monitor working"
else
    echo "   ❌ Coverage monitor failed"
fi

# 4. Ollama Service
echo -e "\n4. Ollama Service:"
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    models=$(curl -s http://localhost:11434/api/tags | jq -r '.models[].name' 2>/dev/null | grep embedding || echo "No embedding models")
    if echo "$models" | grep -q "embeddinggemma:300m"; then
        echo "   ✅ embeddinggemma:300m available"
    else
        echo "   ❌ embeddinggemma:300m not found"
    fi
else
    echo "   ❌ Ollama service not responding"
fi

# 5. MCP Server
echo -e "\n5. MCP Server:"
if curl -s http://localhost:9090/health >/dev/null 2>&1; then
    status=$(curl -s http://localhost:9090/health | jq -r '.status' 2>/dev/null)
    echo "   Status: $status"
else
    echo "   ❌ MCP health endpoint not responding"
fi

echo -e "\n=== Health Check Complete ==="
```

This comprehensive troubleshooting guide should help resolve most common issues with DevStream's vector search system. For additional support, refer to the specific error messages and log files mentioned throughout this guide.

---

**Version**: 1.0
**Updated**: 2025-10-10
**Status**: Production Ready ✅