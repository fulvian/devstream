# 🚀 DevStream Startup Guide

Quick reference guide for starting and managing DevStream MCP Server.

---

## 🎯 Quick Start

### Start DevStream (Full Setup)
```bash
./start-devstream.sh
```

This will:
1. ✅ Check all prerequisites (Node.js, Database, Ollama)
2. 🚀 Start the MCP server with monitoring
3. 🔧 Configure Context7 integration
4. 📊 Display server status and endpoints
5. 🎨 Launch Claude Code

### Other Commands

```bash
# Stop the server
./start-devstream.sh stop

# Check server status
./start-devstream.sh status

# Restart the server
./start-devstream.sh restart
```

---

## 📋 Prerequisites

Before starting DevStream, ensure you have:

1. **Node.js v22+**
   ```bash
   node --version  # Should be v22.15.0 or later
   ```

2. **Database**
   ```bash
   ls -lh data/devstream.db  # Should exist
   ```

3. **Ollama Running**
   ```bash
   brew services start ollama
   curl http://localhost:11434/api/tags  # Should respond
   ```

4. **MCP Server Built**
   ```bash
   cd mcp-devstream-server
   npm run build  # If dist/ doesn't exist
   ```

---

## 📊 Monitoring Endpoints

Once started, DevStream exposes these endpoints:

| Endpoint | URL | Description |
|----------|-----|-------------|
| **Health** | `http://localhost:9090/health` | Server health status |
| **Metrics** | `http://localhost:9090/metrics` | Prometheus metrics |
| **Quality** | `http://localhost:9090/quality` | Search quality metrics |
| **Errors** | `http://localhost:9090/errors` | Error statistics |

### Example: Check Health

```bash
curl http://localhost:9090/health | jq .
```

```json
{
  "status": "healthy",
  "timestamp": "2025-09-30T00:00:00.000Z",
  "uptime": 123.456
}
```

---

## 📝 Log Files

DevStream creates log files in the project root:

```bash
# View real-time logs
tail -f devstream-server.log

# View last 50 lines
tail -50 devstream-server.log

# Search logs for errors
grep -i error devstream-server.log
```

---

## 🔧 Manual Server Management

If you prefer to manage the server manually:

### Start Server Only (No Claude Code)

```bash
cd mcp-devstream-server
node start-production.js
```

### Start in Background

```bash
cd mcp-devstream-server
nohup node start-production.js > ../devstream-server.log 2>&1 &
```

### Stop Background Server

```bash
# Find process ID
lsof -t -i:9090

# Kill process
kill $(lsof -t -i:9090)
```

---

## 🧪 Testing

### Run Smoke Tests

```bash
cd mcp-devstream-server
node smoke-test.js
```

**Expected output:**
```
🧪 DevStream Production Smoke Tests
======================================================================
✅ Database Connection: Connected and verified schema
✅ Ollama Service: Model: embeddinggemma:300m
✅ Vector Search Extension: Version: v0.1.6
✅ Hybrid Search - Simple Query: 10 results, top score: 0.016393
✅ Hybrid Search - Complex Query: 10 results, 5 content types
✅ Metrics Server: Health: healthy, Uptime: 142s
======================================================================
📊 Test Results: 6/6 passed
✅ All tests passed - System is production ready!
```

### Run Unit Tests

```bash
cd mcp-devstream-server
npm test
```

---

## 🎨 Using DevStream in Claude Code

### DevStream Features

Once started, DevStream provides:

- **🧠 Semantic Memory** - Hybrid search with vector + keyword search
- **📋 Task Management** - AI-powered intervention planning
- **🔍 Context7 Integration** - Up-to-date library documentation
- **📊 Monitoring** - Real-time metrics and quality tracking

### Context7 Usage

To use Context7 in your prompts:

```
Hey Claude, use context7 to find the latest documentation for sqlite-vec
```

Context7 will:
1. Resolve the library name to a Context7-compatible ID
2. Fetch the latest documentation
3. Provide code examples and best practices

---

## 🐛 Troubleshooting

### Server Won't Start

**Check prerequisites:**
```bash
./start-devstream.sh status
```

**Common issues:**

1. **Port 9090 already in use**
   ```bash
   # Find process using port 9090
   lsof -i :9090

   # Kill the process
   kill $(lsof -t -i:9090)
   ```

2. **Ollama not running**
   ```bash
   brew services start ollama
   ```

3. **Database not found**
   ```bash
   # Check database exists
   ls -lh data/devstream.db
   ```

4. **MCP server not built**
   ```bash
   cd mcp-devstream-server
   npm run build
   ```

### Check Server Logs

```bash
# View logs
tail -f devstream-server.log

# Search for errors
grep -i error devstream-server.log
```

### Verify Ollama Connection

```bash
# List available models
curl http://localhost:11434/api/tags | jq .

# Generate test embedding
curl http://localhost:11434/api/embeddings -d '{
  "model": "embeddinggemma:300m",
  "prompt": "test query"
}'
```

### Database Issues

```bash
# Check database file
sqlite3 data/devstream.db ".tables"

# Verify vec extension can be loaded
sqlite3 data/devstream.db "SELECT vec_version();"
```

---

## 📚 Documentation

Full documentation available in `mcp-devstream-server/`:

| Document | Description |
|----------|-------------|
| **PRODUCTION_DEPLOYMENT.md** | Complete deployment summary |
| **MONITORING.md** | Metrics and observability guide (550+ lines) |
| **DEPLOYMENT.md** | Deployment procedures (350+ lines) |
| **OPERATIONAL_RUNBOOK.md** | Operations manual (400+ lines) |
| **HYBRID_SEARCH.md** | Architecture and implementation |

---

## 🎯 Development Workflow

### Typical Workflow

1. **Start DevStream**
   ```bash
   ./start-devstream.sh
   ```

2. **Work in Claude Code**
   - Use semantic memory for context
   - Leverage task management features
   - Query Context7 for documentation

3. **Monitor Performance**
   ```bash
   # View quality metrics
   curl http://localhost:9090/quality | jq .

   # Check error rates
   curl http://localhost:9090/errors | jq .
   ```

4. **Stop When Done**
   ```bash
   ./start-devstream.sh stop
   ```

---

## 🚀 Advanced Usage

### Custom Environment Variables

Create a `.env` file in the project root:

```bash
# Database
DEVSTREAM_DB_PATH=/custom/path/to/devstream.db

# Ollama
OLLAMA_HOST=http://custom-host:11434
OLLAMA_MODEL=custom-embedding-model

# Monitoring
METRICS_PORT=9090
LOG_LEVEL=debug
```

### PM2 Process Management

For production deployments with auto-restart:

```bash
# Install PM2
npm install -g pm2

# Start with PM2
cd mcp-devstream-server
pm2 start start-production.js --name devstream-mcp

# Save configuration
pm2 save

# Setup auto-start on boot
pm2 startup
```

### Docker Deployment

See `mcp-devstream-server/DEPLOYMENT.md` for Docker deployment instructions.

---

## 📊 Metrics & Monitoring

### Key Metrics to Watch

1. **Query Performance**
   - `devstream_query_duration_seconds` - Query latency
   - `devstream_active_queries` - Concurrent queries

2. **Search Quality**
   - `devstream_search_quality_score` - RRF ranking scores
   - `devstream_zero_results_total` - Queries with no results

3. **System Health**
   - `devstream_embedding_generation_duration_seconds` - Ollama performance
   - `devstream_vector_index_size` - Number of indexed vectors
   - `devstream_fts5_index_size` - Number of indexed documents

### Grafana Dashboard

For visual monitoring, import the Grafana dashboard from `mcp-devstream-server/MONITORING.md`.

---

## 🎉 Success Indicators

DevStream is running correctly when:

- ✅ Health endpoint returns `{"status": "healthy"}`
- ✅ Metrics endpoint shows `devstream_*` metrics
- ✅ Smoke tests pass (6/6)
- ✅ Query latency < 100ms
- ✅ No errors in logs

---

*Last updated: 2025-09-30*
*DevStream v1.4.0 - Production Ready*