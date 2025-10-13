# MCP Configuration Cache Behavior Guide

**Overview**: This document explains Claude Code's MCP configuration caching behavior and provides procedures for resolving cache-related issues.

## Issue Summary

### Problem
Claude Code maintains an in-memory cache of `.mcp.json` configuration that persists across file edits until the application is fully restarted. This can cause MCP server instances to spawn with outdated configuration.

### Root Cause
1. Claude Code loads `.mcp.json` into memory on session start
2. Configuration cache persists across file modifications  
3. MCP server auto-respawn uses cached configuration, not disk file
4. No hot-reload capability for `.mcp.json` changes

### Symptoms
- Multiple MCP processes running simultaneously
- Processes using outdated database paths
- Auto-respawn loop after cleanup
- Configuration changes not taking effect

## Resolution Procedures

### Primary Solution: Full Application Restart

**CRITICAL**: File edits alone are insufficient to resolve cache issues.

#### Step-by-Step Procedure

1. **Save all work** in Claude Code
2. **Completely quit Claude Code**:
   - macOS: `Cmd+Q` or `File → Quit`
   - Windows/Linux: `File → Exit` or close window
3. **Wait 10 seconds** for full process termination
4. **Verify no MCP processes running**:
   ```bash
   pgrep -f 'mcp-devstream-server/dist/index.js'
   ```
5. **Kill any remaining processes**:
   ```bash
   pkill -9 -f 'mcp-devstream-server/dist/index.js'
   ```
6. **Relaunch Claude Code application**
7. **Wait at start screen** (do not open project immediately)
8. **Open project** after 5 seconds

#### Verification
After restart, verify:
- Exactly 1 MCP process running
- Process uses correct database path
- All MCP functionality working

### Secondary Solution: Enhanced Cleanup

If immediate restart is not possible, use enhanced cleanup:

```bash
# Kill all processes
/Users/fulvioventura/devstream/.claude/hooks/devstream/monitoring/mcp_cleanup_hook.py

# Manual force kill if needed
pkill -9 -f 'mcp-devstream-server/dist/index.js'

# Monitor for respawn
watch -n 5 'pgrep -af mcp-devstream-server/dist/index.js'
```

## Prevention & Monitoring

### Enhanced Cleanup Hook

The cleanup hook now includes wrong-path detection:

- **Detection**: Automatically identifies wrong database path usage
- **Logging**: Records all detections in `~/.claude/logs/devstream/wrong-path-detections.log`
- **Cleanup**: Terminates processes using wrong paths immediately
- **Priority**: Wrong-path processes killed before normal cleanup

### Pre-Launch Validation

The startup script includes configuration validation:

- **Path Validation**: Ensures `.mcp.json` contains correct database path
- **File Verification**: Confirms database file exists and is expected size
- **Early Detection**: Prevents startup with wrong configuration

### Monitoring Scripts

#### Wrong Path Monitor
```bash
# Single check
/Users/fulvioventura/devstream/.claude/hooks/devstream/monitoring/wrong_path_monitor.py

# Continuous monitoring
/Users/fulvioventura/devstream/.claude/hooks/devstream/monitoring/wrong_path_monitor.py --continuous
```

#### Verification Script
```bash
# Full verification after restart
./verify-mcp-fix.sh
```

## Configuration Files

### .mcp.json Structure
```json
{
  "mcpServers": {
    "devstream": {
      "command": "node",
      "args": ["/Users/fulvioventura/devstream/mcp-devstream-server/dist/index.js"],
      "env": {
        "DEVSTREAM_DB_PATH": "/Users/fulvioventura/devstream/data/devstream.db"
      }
    }
  }
}
```

### Critical Paths
- **Correct Database**: `/Users/fulvioventura/devstream/data/devstream.db` (~525MB)
- **Wrong Database**: `/Users/fulvioventura/devstream/mcp-devstream-server/data/devstream.db` (~56KB)

## Troubleshooting

### Issue Persists After Restart

1. **Verify Complete Shutdown**:
   ```bash
   ps aux | grep -i claude
   ```
   Kill any remaining Claude Code processes

2. **Check for Multiple Claude Code Instances**:
   ```bash
   ps aux | grep -i "claude\|anthropic"
   ```

3. **Clear Configuration Cache** (last resort):
   ```bash
   # Backup current config
   cp ~/.claude/config.json ~/.claude/config.json.backup
   
   # Remove and restart Claude Code (it will recreate)
   rm ~/.claude/config.json
   ```

### Database File Issues

1. **Verify Correct Database**:
   ```bash
   ls -lh /Users/fulvioventura/devstream/data/devstream.db
   # Should be ~525MB
   
   ls -lh /Users/fulvioventura/devstream/mcp-devstream-server/data/devstream.db
   # Should be ~56KB (legacy, unused)
   ```

2. **Test Database Accessibility**:
   ```bash
   sqlite3 /Users/fulvioventura/devstream/data/devstream.db "SELECT COUNT(*) FROM memory_records;"
   # Should return ~113,000+
   ```

## Monitoring Logs

### Wrong Path Detections
- **Location**: `~/.claude/logs/devstream/wrong-path-detections.log`
- **Format**: `timestamp | PID | WRONG PATH | command_line`
- **Action**: Immediate process termination

### Cleanup Hook Activity
- **Location**: `~/.claude/logs/devstream/mcp_cleanup_hook.jsonl`
- **Format**: JSON with process counts and cleanup results
- **Content**: All cleanup activity and decisions

## Best Practices

### Configuration Changes
1. **Edit .mcp.json** with correct paths
2. **Save changes**
3. **Restart Claude Code completely** (not just session)
4. **Verify with monitoring scripts**

### Regular Monitoring
1. **Daily check**: Run wrong-path monitor
2. **Weekly review**: Check cleanup logs
3. **Monthly audit**: Verify database integrity

### Incident Response
1. **Detection**: Monitor alerts or unusual behavior
2. **Immediate action**: Kill wrong-path processes
3. **Root cause**: Check for cache issues
4. **Prevention**: Verify configuration and restart if needed

## Emergency Procedures

### Multiple Instance Detected
```bash
# Immediate cleanup
/Users/fulvioventura/devstream/.claude/hooks/devstream/monitoring/mcp_cleanup_hook.py

# Force termination
pkill -9 -f 'mcp-devstream-server/dist/index.js'

# Full application restart
# (Quit Claude Code completely, then relaunch)
```

### Wrong Path in Production
```bash
# Stop all processes
./start-devstream.sh stop

# Verify configuration
cat .mcp.json | grep DEVSTREAM_DB_PATH

# Restart with validation
./start-devstream.sh start
```

## Support Information

### Related Files
- **Cleanup Hook**: `.claude/hooks/devstream/monitoring/mcp_cleanup_hook.py`
- **Monitor Script**: `.claude/hooks/devstream/monitoring/wrong_path_monitor.py`
- **Startup Script**: `start-devstream.sh`
- **Verification Script**: `verify-mcp-fix.sh`

### Log Locations
- **Wrong Path Log**: `~/.claude/logs/devstream/wrong-path-detections.log`
- **Cleanup Log**: `~/.claude/logs/devstream/mcp_cleanup_hook.jsonl`
- **Server Log**: `devstream-server.log`

### Contact Information
For issues related to MCP configuration caching:
1. Check this documentation first
2. Review monitoring logs
3. Run verification script
4. Report with logs and configuration details

---

**Version**: 1.0  
**Last Updated**: 2025-10-13  
**Status**: Production Ready
