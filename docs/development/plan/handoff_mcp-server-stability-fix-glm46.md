# Handoff Prompt - GLM-4.6 MCP Server Stability Fix

**Handoff From**: Sonnet 4.5 (Architectural Analysis)
**Handoff To**: GLM-4.6 (Execution Model)
**Date**: 2025-10-13
**Context**: DevStream Protocol v2.2.0 - MCP Server Critical Issue Resolution

---

## 🎯 CONTEXT TRANSFER

### Problem Summary (Already Solved by Sonnet 4.5)
✅ **Multi-instance Problem Identified**: 10+ MCP processes running concurrently
✅ **Root Cause Found**: Claude Code configuration cache + wrong database path (56KB vs 502MB)
✅ **Architecture Analysis Completed**: Worker Pool already implemented, solid base for fixes
✅ **Solution Strategy Determined**: Fix existing server (not rewrite) - 2-4 hours vs 40-60 hours

### Implementation Plan Ready (Already Created)
📄 **Plan File**: `docs/development/plan/piano_mcp-server-stability-fix.md`
⏱️ **Estimated Duration**: 135 minutes (2h 15min)
🎯 **Success Criteria**: Single process, correct database, zero disconnections
🔧 **Risk Level**: LOW (conservative approach with rollback options)

### Current System State
- ✅ **Architecture Solid**: Worker Pool + Piscina implemented and functional
- ✅ **Database Correct**: 502MB production database ready
- ✅ **Configuration Validated**: .mcp.json contains correct paths
- ❌ **Runtime Issues**: Multi-instance spawn, cache persistence, session tracking missing

---

## 🚀 GLM-4.6 EXECUTION TASK

### Primary Objective
Implement the MCP server stability fix according to the detailed plan in `piano_mcp-server-stability-fix.md`. This is a **CRITICAL** issue affecting system usability.

### Execution Model Instructions
You are **GLM-4.6** execution model. Follow this approach:

1. **Precision First**: Execute code exactly as specified
2. **Micro-Task Focus**: Complete each phase completely before proceeding
3. **Validation-Driven**: Test each component before moving forward
4. **Syntax Precision**: Pay attention to TypeScript syntax, imports, file paths
5. **Step-by-Step**: Follow the exact phase sequence as documented

### Phase Execution Priority

**PHASE 1 - IMMEDIATE (25 min)**: Multi-Instance Resolution
- **1.1**: Emergency Process Cleanup (5 min)
- **1.2**: PID File Lock Implementation (10 min)
- **1.3**: Server Entry Point Integration (5 min)
- **1.4**: Database Path Validation (5 min)

**PHASE 2 - HIGH PRIORITY (30 min)**: Session Tracking Restoration
- **2.1**: Database Migration Script (10 min)
- **2.2**: Session Manager Implementation (15 min)
- **2.3**: MCP Server Integration (5 min)

**PHASE 3 - MEDIUM PRIORITY (35 min)**: Enhanced Error Handling
- **3.1**: Circuit Breaker Implementation (15 min)
- **3.2**: Database Operations with Circuit Breaker (10 min)
- **3.3**: Tool Handlers with Enhanced Error Handling (10 min)

**PHASE 4 - LOW PRIORITY (30 min)**: Health Monitoring
- **4.1**: Health Endpoint Implementation (15 min)
- **4.2**: MCP Server Health Integration (10 min)
- **4.3**: Monitoring Script (5 min)

**PHASE 5 - VALIDATION (15 min)**: Testing & Validation
- **5.1**: Integration Tests (10 min)
- **5.2**: Performance Tests (5 min)

### Critical Technical Implementation Details

#### File Structure and Paths
```
mcp-devstream-server/src/
├── core/
│   ├── process-manager.ts (NUOVO)
│   ├── session-manager.ts (NUOVO)
│   ├── circuit-breaker.ts (NUOVO)
│   ├── resilient-database.ts (NUOVO)
│   └── database-pool.ts (ESISTENTE - non modificare)
├── health-server.ts (NUOVO)
├── index.ts (MODIFICARE - aggiungere process manager)
├── tools/
│   ├── memory.ts (MODIFICARE - retry logic)
│   ├── tasks.ts (MODIFICARE - retry logic)
│   └── ... (altri tools con retry logic)
└── workers/
    └── database-worker.ts (ESISTENTE - non modificare)

migrations/
└── 005_restore_work_sessions.sql (NUOVO)

tests/
├── integration/
│   └── mcp-server-stability.test.ts (NUOVO)
└── stress/
    └── mcp-load-test.ts (NUOVO)

scripts/
└── monitor-mcp-server.sh (NUOVO)
```

#### Key Implementation Requirements

1. **ProcessManager**: PID file locking at `/tmp/devstream-mcp-server.pid`
2. **SessionManager**: Database-backed session state with work_sessions table
3. **CircuitBreaker**: 5 failure threshold, 30s recovery timeout
4. **HealthServer**: Express server on port 9090 with `/health`, `/metrics`, `/status` endpoints
5. **Error Handling**: Exponential backoff retry with structured logging

#### Database Integration Points
- **Migration**: `CREATE TABLE IF NOT EXISTS work_sessions` with proper indexes
- **Session Storage**: Store session state in work_sessions table
- **Cleanup**: Graceful session marking as completed on shutdown

#### TypeScript Implementation Standards
- **Full Type Safety**: All functions with proper type hints
- **Error Handling**: try-catch with specific error types
- **Logging**: Structured logging using console.error with context
- **Async/Await**: Proper async patterns for database operations
- **Resource Management**: Proper cleanup in finally blocks

### Success Validation Criteria

#### After Each Phase:
- **Phase 1**: Single MCP process, correct database (502MB)
- **Phase 2**: Session tracking functional, work_sessions table populated
- **Phase 3**: Circuit breaker functional, graceful degradation working
- **Phase 4**: Health endpoints responding, metrics collecting
- **Phase 5**: All tests passing, load test with 100+ concurrent requests

#### Final Success Metrics:
- ✅ **Zero disconnections** in 2+ hour stability test
- ✅ **Single process guarantee** via PID locking
- ✅ **Session tracking** functional for PostToolUse hook
- ✅ **Circuit breaker** prevents cascade failures
- ✅ **Health monitoring** with detailed metrics
- ✅ **95%+ test coverage** for new components

### Error Handling Strategy

#### Database Errors:
- Use circuit breaker wrapper for all database operations
- Implement retry logic with exponential backoff
- Log detailed error context for troubleshooting
- Graceful degradation when possible

#### Process Management:
- Validate PID file lock before starting
- Clean shutdown handling for all signals (SIGINT, SIGTERM)
- Force cleanup with timeout protection
- Monitor process health continuously

#### Session Management:
- Validate session existence in database
- Create new sessions only when necessary
- Update session activity timestamps
- Clean up stale sessions automatically

### Testing Requirements

#### Unit Tests:
- Process Manager lock acquisition/release
- Session Manager session creation/reuse
- Circuit breaker state transitions
- Health endpoint responses

#### Integration Tests:
- Multi-instance prevention
- Session tracking end-to-end
- Database operations with circuit breaker
- Health monitoring functionality

#### Stress Tests:
- 100+ concurrent session requests
- Long-running stability test (2+ hours)
- Circuit breaker behavior under load
- Graceful shutdown under load

### Documentation Requirements

#### Code Documentation:
- JSDoc comments for all new classes and methods
- Type definitions for all interfaces
- Inline comments for complex logic
- README updates for new monitoring

#### Operational Documentation:
- Troubleshooting guide for common issues
- Monitoring guide for health metrics
- Runbook for incident response
- Rollback procedures for each component

### Monitoring Implementation

#### Health Checks:
- Process status (single instance enforcement)
- Database connectivity and path validation
- Session tracking functionality
- Circuit breaker state and statistics

#### Metrics Collection:
- Request/response times and success rates
- Circuit breaker state transitions
- Session lifecycle metrics
- Database operation performance

#### Alerting Conditions:
- Multi-instance detection
- Database connectivity failures
- Circuit breaker openings
- Session tracking anomalies

### Rollback Procedures

#### Immediate Rollback (< 1 minute):
```bash
export DEVSTREAM_WORKER_POOL_ENABLED=false
export DEVSTREAM_SESSION_MANAGER_ENABLED=false
killall -9 node && npm start
```

#### Database Rollback:
```bash
sqlite3 data/devstream.db "DROP TABLE IF EXISTS work_sessions;"
git checkout HEAD~1 -- mcp-devstream-server/src/
npm run build && npm start
```

### Implementation Notes from Sonnet 4.5

#### Architecture Insights:
- **Worker Pool Already Functional**: Piscina implementation is production-ready
- **Database Schema Solid**: Existing schema supports session tracking
- **Feature Flag System**: Use DEVSTREAM_WORKER_POOL_ENABLED for safe rollbacks
- **Logging System**: Structured logging already implemented

#### Critical Dependencies:
- **Node.js Process Management**: Use built-in process events for signal handling
- **SQLite Operations**: Better-sqlite3 with WAL mode for concurrency
- **TypeScript**: Strict type checking required for production quality
- **Express.js**: Lightweight HTTP server for health endpoints

#### Performance Considerations:
- **Circuit Breaker**: Prevents cascade failures under load
- **Session Caching**: Reduces database lookups for session operations
- **Health Monitoring**: Lightweight checks with minimal overhead
- **Process Cleanup**: Prevents zombie processes and resource leaks

---

## 🎯 EXECUTION START COMMANDS

### Environment Setup
```bash
# Verify Node.js and TypeScript versions
node --version  # Should be 18+
npm --version   # Should be 9+

# Verify database exists and is correct size
ls -lh /Users/fulvioventura/devstream/data/devstream.db  # Should be ~502MB

# Verify MCP server not running
pgrep -f "mcp-devstream-server/dist/index.js" | wc -l  # Should be 0
```

### Starting Implementation
Execute phases sequentially as documented in `piano_mcp-server-stability.md`.

**Remember**: This is a CRITICAL fix for system stability. Execute carefully and validate each phase before proceeding.

### Validation Commands
```bash
# After Phase 1:
pgrep -f "mcp-devstream-server" | wc -l  # Should be 1
ls -lh /Users/fulvioventura/devstream/data/devstream.db  # Should be 502MB

# After Phase 2:
sqlite3 /Users/fulvioventura/devstream/data/devstream.db "SELECT COUNT(*) FROM work_sessions;"  # Should be > 0

# After Phase 4:
curl -s http://localhost:9090/health | jq '.status'  # Should be "healthy"
curl -s http://localhost:9090/metrics  # Should return Prometheus metrics
```

---

## 🤖 GLM-4.6 EXECUTION INSTRUCTIONS

### Step 1: Review and Plan
- Read the complete implementation plan in `piano_mcp-server-stability-fix.md`
- Understand the phase sequence and dependencies
- Identify any prerequisites or setup requirements

### Step 2: Execute Phase 1 First
- **CRITICAL**: Start with emergency cleanup and multi-instance resolution
- Validate that only one MCP process is running
- Confirm correct database path is being used

### Step 3: Execute Sequentially
- Complete each phase completely before starting the next
- Run validation tests after each phase
- Stop immediately if a phase fails and investigate

### Step 4: Final Validation
- Run complete integration test suite
- Execute stress tests with concurrent requests
- Monitor health metrics for stability
- Document any deviations from expected results

### Step 5: Completion and Documentation
- Update documentation with any implementation changes
- Create summary of fixes implemented
- Provide final success metrics and validation results

---

## 📞 SUPPORT AND COMMUNICATION

If you encounter issues during implementation:

1. **Check Logs**: Look for structured error messages in console output
2. **Validate Database**: Ensure database schema changes applied correctly
3. **Verify Processes**: Confirm only one MCP process is running
4. **Test Health Endpoints**: Validate monitoring functionality
5. **Review Code**: Compare implementation with plan specifications

### Emergency Contacts
- **Rollback Procedures**: Documented in plan (Section: Rollback Procedures)
- **Database Recovery**: Backup files available in standard location
- **Process Management**: PID files and cleanup scripts provided

---

**Prepared By**: Sonnet 4.5 (Architectural Analysis + Planning)
**Execution Model**: GLM-4.6 (Precise Implementation)
**Date**: 2025-10-13
**Priority**: CRITICAL (System Stability Issue)
**Estimated Duration**: 135 minutes (2h 15min)
**Success Criteria**: Single MCP process, zero disconnections, session tracking functional

---

**Ready for GLM-4.6 Execution** 🚀