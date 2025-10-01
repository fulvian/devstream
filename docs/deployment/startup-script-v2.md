# DevStream Startup Script v2.0

**Version**: 2.0.0
**Date**: 2025-10-01
**Status**: Production Ready ✅

## Overview

Il `start-devstream.sh` v2.0 è il launcher di produzione completamente integrato con il sistema Agent Auto-Delegation Phase 3. Gestisce l'avvio completo dell'infrastruttura DevStream con verifiche automatiche, configurazione e diagnostica.

## Nuove Funzionalità v2.0

### 🤖 Agent Auto-Delegation Integration

**Verifica Automatica Sistema**:
- Check esistenza moduli (`pattern_matcher.py`, `agent_router.py`)
- Test import Python dei moduli di delegazione
- Validazione configurazione `.env.devstream`
- Display status 17 agenti disponibili

**Output**:
```bash
[STATUS] Verifying Agent Auto-Delegation System...
[STATUS] ✅ Agent Auto-Delegation System verified
[STATUS] ✅ Agent Auto-Delegation System ready
```

### 🐍 Python Virtual Environment Management

**Auto-Setup**:
- Creazione automatica venv `.devstream` se mancante
- Verifica Python 3.11.x
- Installazione automatica dipendenze hook (cchooks, aiohttp, structlog)

**Output**:
```bash
[STATUS] Checking Python virtual environment...
[INFO] Python: 3.11.13
[STATUS] Checking hook dependencies...
[INFO] Hook dependencies: OK
```

### 🔧 MCP Configuration Helper

**Fix Warning MCP** (Issue #1):
- ❌ **PRIMA**: `claude mcp add` falliva con warning confuso
- ✅ **DOPO**: Istruzioni chiare per configurazione manuale

**Output**:
```bash
[STATUS] Configuring Claude Code MCP servers...
[INFO] DevStream MCP configuration:
[INFO]   Add to ~/.claude/config.json manually:
[INFO]   "devstream": {
[INFO]     "command": "node",
[INFO]     "args": ["/path/to/mcp-devstream-server/dist/index.js"],
[INFO]     "env": {
[INFO]       "DEVSTREAM_DB_PATH": "/path/to/data/devstream.db"
[INFO]     }
[INFO]   }
```

### 📊 Enhanced Status Display

**Nuovo comando `status`**:
```bash
./start-devstream.sh status
```

**Mostra**:
- Server health + uptime
- Monitoring endpoints
- Agent Auto-Delegation status (17 agenti)
- Pattern-based routing configuration
- Quality gates configuration

## Usage

### Start DevStream

```bash
./start-devstream.sh start
```

**Sequence**:
1. Check Python venv (auto-create se necessario)
2. Load `.env.devstream` configuration
3. Check prerequisites (Node.js, Database, Ollama)
4. **Verify Agent Auto-Delegation System** ✨
5. Initialize Context7
6. Start MCP Server (port 9090)
7. Show server + agent status
8. Provide MCP configuration instructions
9. Launch Claude Code

### Stop DevStream

```bash
./start-devstream.sh stop
```

Ferma il MCP server (port 9090).

### Check Status

```bash
./start-devstream.sh status
```

Mostra:
- Server health
- Agent Auto-Delegation configuration
- Available agents (17 total)
- Quality gates status

### Restart

```bash
./start-devstream.sh restart
```

Stop + Start sequence.

## Configuration Files

### Required Files

**1. `.env.devstream`** (MANDATORY):
```bash
# Agent Auto-Delegation
DEVSTREAM_AGENT_AUTO_DELEGATION_ENABLED=true
DEVSTREAM_AGENT_AUTO_DELEGATION_CONFIDENCE_THRESHOLD=0.85
DEVSTREAM_AGENT_AUTO_DELEGATION_AUTO_APPROVE_THRESHOLD=0.95
DEVSTREAM_AGENT_AUTO_DELEGATION_LOG_DECISIONS=true

# Memory System
DEVSTREAM_MEMORY_ENABLED=true

# Context7
DEVSTREAM_CONTEXT7_ENABLED=true
```

**2. `context7-wrapper.sh`** (OPTIONAL):
```bash
#!/bin/bash
npx -y @upstash/context7-mcp --api-key "$CONTEXT7_API_KEY" "$@"
```

**3. `~/.claude/config.json`** (User Configuration):
```json
{
  "mcpServers": {
    "devstream": {
      "command": "node",
      "args": ["/path/to/devstream/mcp-devstream-server/dist/index.js"],
      "env": {
        "DEVSTREAM_DB_PATH": "/path/to/devstream/data/devstream.db"
      }
    },
    "context7": {
      "command": "bash",
      "args": ["/path/to/devstream/context7-wrapper.sh"]
    }
  }
}
```

## Startup Sequence

### Phase 1: Environment Setup
1. **Check Python venv** → Create if missing
2. **Verify Python 3.11.x** → Exit if wrong version
3. **Check hook dependencies** → Auto-install if missing

### Phase 2: Configuration Loading
1. **Load `.env.devstream`** → Export environment variables
2. **Verify Agent Auto-Delegation** → Check ENABLED flag
3. **Verify Memory System** → Check ENABLED flag
4. **Verify Context7** → Check ENABLED flag

### Phase 3: Prerequisites Validation
1. **Node.js** → Exit if missing
2. **Database** → Exit if missing
3. **Ollama** → Warning only (non-blocking)
4. **MCP Server Build** → Auto-build if missing

### Phase 4: Agent System Verification ✨
1. **Check pattern_matcher.py** → Exit if missing
2. **Check agent_router.py** → Exit if missing
3. **Test Python import** → Exit if import fails
4. **Display verification success**

### Phase 5: Context7 Initialization
1. **Check `.config/context7.json`** → Create if missing
2. **Set environment variables** → CONTEXT7_SESSION_ID
3. **Verify npx availability** → Warning if missing

### Phase 6: MCP Server Startup
1. **Check port 9090** → Skip if already running
2. **Start server** → `node --max-old-space-size=8192 --expose-gc`
3. **Wait for health check** → Max 30 seconds
4. **Display endpoints**

### Phase 7: Status Display
1. **Server health** → Uptime, health check
2. **Monitoring endpoints** → Metrics, quality, errors
3. **Agent status** → 17 agents, configuration
4. **Pattern routing** → Active status, thresholds

### Phase 8: MCP Configuration Help
1. **Check existing config** → Read `~/.claude/config.json`
2. **Provide instructions** → Manual configuration steps
3. **Show example JSON** → DevStream + Context7

### Phase 9: Launch Claude Code
1. **Display welcome message** → Features, usage tips
2. **Start Claude Code** → `claude` command
3. **Agent Auto-Delegation** → Now active in session

## Output Colors

- **GREEN** `[STATUS]` - Major milestones
- **BLUE** `[INFO]` - Informational messages
- **YELLOW** `[WARNING]` - Non-blocking issues
- **RED** `[ERROR]` - Critical errors
- **CYAN** `[FEATURE]` - Feature status

## Error Handling

### Critical Errors (Exit 1)

**Node.js not found**:
```bash
[ERROR] Node.js not found
[ERROR] Critical prerequisites not met.
```
**Fix**: Install Node.js 22+

**Database not found**:
```bash
[ERROR] Database not found at data/devstream.db
```
**Fix**: Create database or check path

**Agent delegation verification failed**:
```bash
[ERROR] Pattern matcher not found
[ERROR] Agent Auto-Delegation verification failed
```
**Fix**: Ensure Phase 3 code committed and available

### Non-Critical Warnings (Continue)

**Ollama not running**:
```bash
[WARNING] Ollama service not responding at http://localhost:11434
[INFO] Start Ollama: brew services start ollama
[INFO] Continuing without Ollama (embeddings will be disabled)
```
**Fix**: `brew services start ollama` (optional)

**Context7 API key missing**:
```bash
[WARNING] ⚠️  CONTEXT7_API_KEY not set in environment
```
**Fix**: Add to `.env` (optional for Context7 features)

## Performance Optimizations

### Memory Management
```bash
node --max-old-space-size=8192 --expose-gc start-production.js
```
- **8GB heap** → Prevents OOM during agent execution
- **Explicit GC** → Better memory cleanup

### Fast Startup
- **Parallel checks** → Prerequisites verified concurrently
- **Conditional builds** → Only build if `dist/` missing
- **Port reuse detection** → Skip startup if already running

## Troubleshooting

### Server won't start

**Check logs**:
```bash
tail -f devstream-server.log
```

**Common issues**:
- Port 9090 already in use → `lsof -i :9090` then kill process
- Database locked → Close other connections
- Build failed → `cd mcp-devstream-server && npm run build`

### Agent delegation not working

**Verify system**:
```bash
./start-devstream.sh status
```

**Check**:
- `[FEATURE] ✅ Agent Auto-Delegation: ENABLED`
- `[STATUS] ✅ Pattern-based routing ACTIVE`

**If disabled**:
```bash
# Check .env.devstream
grep AGENT_AUTO_DELEGATION .env.devstream
```

### MCP configuration issues

**Manual setup**:
1. Edit `~/.claude/config.json`
2. Add `devstream` server configuration
3. Restart Claude Code
4. Verify with `claude mcp list` (if available)

## Changelog

### v2.0.0 (2025-10-01)

**Added**:
- ✨ Agent Auto-Delegation System verification
- ✨ Python virtual environment management
- ✨ Enhanced status display (17 agents)
- ✨ MCP configuration helper (clear instructions)
- ✨ Configuration loading from `.env.devstream`

**Fixed**:
- 🐛 MCP server registration warnings (removed confusing CLI attempts)
- 🐛 Context7 wrapper missing warnings (graceful degradation)
- 🐛 Non-blocking Ollama check (continues without embeddings)

**Changed**:
- 🔄 Startup sequence reorganized (8 phases)
- 🔄 Color coding enhanced (CYAN for features)
- 🔄 Status command shows agent configuration

**Removed**:
- ❌ Deprecated `claude mcp add` commands (replaced with manual instructions)

### v1.0.0 (2025-09-28)

- Initial production launcher
- Context7 integration
- MCP server startup
- Health monitoring

## Best Practices

### Production Deployment

**1. Configuration Management**:
```bash
# Use environment-specific configs
cp .env.devstream.example .env.devstream
# Edit with production values
```

**2. Log Management**:
```bash
# Rotate logs
mv devstream-server.log devstream-server.log.$(date +%Y%m%d)
```

**3. Monitoring**:
```bash
# Health check endpoint
curl http://localhost:9090/health

# Metrics endpoint
curl http://localhost:9090/metrics
```

**4. Restart Policy**:
```bash
# Graceful restart
./start-devstream.sh restart

# Or use systemd/launchd for auto-restart
```

## See Also

- [Agent Auto-Delegation System](../../.claude/hooks/devstream/agents/README.md)
- [CLAUDE.md - DevStream Rules](../../CLAUDE.md)
- [MCP Server Documentation](../../mcp-devstream-server/README.md)
- [Context7 Integration](../guides/context7-integration.md)

---

**Version**: 2.0.0
**Maintained by**: DevStream Team
**Last Updated**: 2025-10-01
