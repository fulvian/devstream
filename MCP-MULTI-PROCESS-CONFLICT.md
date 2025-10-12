# MCP MULTI-PROCESS CONFLICT - ROOT CAUSE ANALYSIS

**Date**: 2025-10-13
**Status**: ✅ RESOLVED
**Root Cause**: Multiple MCP server configurations causing process conflicts

## 🔍 Problem Analysis

### Initial Symptoms
- DevStream MCP server disconnecting continuously
- Multiple "Not connected" errors after initial successful connection
- Server works for ~9 seconds then fails

### Root Cause Discovery

**Multiple MCP Configurations Active Simultaneously**:

1. **Global Configuration** (`~/.claude/claude_desktop_config.json`)
   - ❌ **REMOVED**: DevStream server configuration
   - ✅ **KEPT**: Context7 (global service)

2. **Project Configuration** (`./.mcp.json`)
   - ✅ **CORRECT**: DevStream server with proper database path argument
   - ✅ **KEPT**: Only DevStream (project-specific service)

3. **Local Project Configuration** (`./.claude/mcp_servers.json`)
   - ❌ **REMOVED**: Duplicate DevStream configuration
   - ✅ **KEPT**: Context7 (if needed locally)

### Configuration Conflicts

**Before Fix**:
```bash
# Multiple processes spawned simultaneously
PID 36606: node .../index.js /Users/fulvioventura/devstream/mcp-devstream-server/data/devstream.db
PID 36708: node .../index.js /Users/fulvioventura/devstream/mcp-devstream-server/data/devstream.db

# Wrong database paths (using relative path instead of absolute)
# Expected: /Users/fulvioventura/devstream/data/devstream.db
# Actual:   /Users/fulvioventura/devstream/mcp-devstream-server/data/devstream.db
```

**After Fix**:
```bash
# Single process with correct configuration
# Only one DevStream MCP server instance
# Correct database path: /Users/fulvioventura/devstream/data/devstream.db
```

## 🔧 Solution Applied

### 1. Clean Global Configuration
**File**: `~/.claude/claude_desktop_config.json`
```json
// REMOVED entire devstream configuration block
{
  "mcpServers": {
    "context7": { /* kept */ },
    // "devstream": { /* REMOVED - conflicts with project config */ }
  }
}
```

### 2. Clean Local Project Configuration
**File**: `./.claude/mcp_servers.json`
```json
// REMOVED duplicate devstream configuration
{
  "mcpServers": {
    "context7": { /* kept */ },
    // "devstream": { /* REMOVED - duplicate of .mcp.json */ }
  }
}
```

### 3. Keep Only Project Configuration
**File**: `./.mcp.json` (CORRECT - NO CHANGES)
```json
{
  "mcpServers": {
    "devstream": {
      "command": "node",
      "args": [
        "/Users/fulvioventura/devstream/mcp-devstream-server/dist/index.js",
        "/Users/fulvioventura/devstream/data/devstream.db"  // ✅ Correct absolute path
      ],
      "env": {
        "NODE_ENV": "development",
        "DEBUG": "mcp*"
      }
    }
  }
}
```

## 📊 Configuration Architecture (Final)

```
Global Level (~/.claude/claude_desktop_config.json)
├── context7 (Global knowledge service)
└── No DevStream (project-specific servers don't belong globally)

Project Level (./.mcp.json)
├── devstream (Project task management)
└── No Context7 (global services don't belong to projects)

Local Project Level (./.claude/mcp_servers.json)
├── context7 (Optional local override)
└── No DevStream (duplicate of project config)
```

## 🧪 Verification

### Process Management
```bash
# Before: Multiple processes
ps aux | grep devstream
# PID 36606 node .../index.js wrong_path/db
# PID 36708 node .../index.js wrong_path/db

# After: Single process
ps aux | grep devstream
# PID 37891 node .../index.js /Users/fulvioventura/devstream/data/devstream.db
```

### MCP Connection Log
```json
{
  "debug": "Successfully connected to stdio server in 139ms",
  "debug": "Connection established with capabilities: {...}",
  // No more "Not connected" errors
}
```

## 🎯 Best Practices Applied

1. **Single Source of Truth**: One MCP configuration per server scope
2. **Scope Separation**: Global vs project-specific servers properly isolated
3. **Path Consistency**: Absolute paths passed as CLI arguments, not just env vars
4. **Conflict Prevention**: Remove duplicate configurations across multiple files

## 📈 Impact

- ✅ **Zero disconnections** after configuration cleanup
- ✅ **Single process instance** (no resource conflicts)
- ✅ **Correct database path** resolution
- ✅ **Stable MCP connection** maintained

## 🔮 Prevention

**Configuration Rules**:
1. **Global servers** (Context7): Only in `~/.claude/claude_desktop_config.json`
2. **Project servers** (DevStream): Only in `./.mcp.json`
3. **Never duplicate** server configurations across multiple scopes
4. **Always use absolute paths** for critical resources like databases

**Monitoring Commands**:
```bash
# Check for multiple processes
ps aux | grep -E "(node.*devstream|mcp.*devstream)" | grep -v grep

# Verify MCP connections
/mcp  # Should show single devstream server connected
```

---

**Resolution**: ✅ **COMPLETE** - MCP server stability achieved through elimination of configuration conflicts.