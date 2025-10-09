# Implementation Plan: Persistent MCP Server Connection

**Task ID**: TBD (da creare)
**Model**: Sonnet 4.5
**Type**: Refactoring + Architecture
**Priority**: 10/10 (Critical - Process Leak Fix)
**Phase**: Core Engine & Infrastructure
**Estimated Duration**: 180 minutes

---

## Executive Summary

**Problem**: Current MCP client creates a new Node.js subprocess for every tool call, causing process leaks (13+ zombie processes observed), database contention, and 30-second timeouts.

**Solution**: Implement persistent MCP server connection using STDIO transport with proper lifecycle management, connection pooling, health monitoring, and graceful shutdown.

**Expected Outcomes**:
- ✅ Single persistent Node.js process instead of hundreds
- ✅ Zero zombie processes
- ✅ Sub-second MCP tool response times (vs 30s timeout)
- ✅ Zero database contention
- ✅ Graceful shutdown with exit_stack pattern
- ✅ Automatic connection recovery on failures

---

## Context7 Research Findings

### Python Asyncio Subprocess Best Practices
- **Source**: Python 3.14 asyncio documentation
- **Key Findings**:
  - Always `await process.wait()` after `process.kill()` to prevent zombies
  - Use try-finally blocks for guaranteed cleanup
  - Proper timeout handling requires `proc.kill()` + `proc.communicate()`

### MCP Server Connection Patterns
- **Source**: MCP Ecosystem documentation, Node.js child_process docs
- **Key Findings**:
  - Persistent STDIO connections > subprocess spawn for performance
  - exit_stack pattern crucial for proper termination
  - STDIO transport supports multiple requests over single connection
  - Node.js spawn() is async and doesn't block event loop

---

## Architecture Design

### 1. Persistent Process Management

```python
class DevStreamMCPClient:
    def __init__(self):
        self._persistent_process: Optional[asyncio.subprocess.Process] = None
        self._stdin: Optional[asyncio.StreamWriter] = None
        self._stdout: Optional[asyncio.StreamReader] = None
        self._connection_lock = asyncio.Lock()
        self._startup_time: Optional[datetime] = None
        self._request_count = 0
        self._shutdown_event = asyncio.Event()

    async def _ensure_connection(self) -> bool:
        """Ensure persistent connection is alive, reconnect if needed."""
        async with self._connection_lock:
            if self._persistent_process is None or self._persistent_process.returncode is not None:
                await self._start_persistent_server()
            return self._persistent_process is not None
```

### 2. STDIO Communication Pattern

```python
async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
    """Send JSON-RPC request over persistent STDIO connection."""
    await self._ensure_connection()

    # Write request to stdin
    request_json = json.dumps(request) + '\n'
    self._stdin.write(request_json.encode('utf-8'))
    await self._stdin.drain()

    # Read response from stdout (line-delimited JSON)
    response_line = await asyncio.wait_for(
        self._stdout.readline(),
        timeout=30.0
    )
    return json.loads(response_line.decode('utf-8'))
```

### 3. Graceful Shutdown with exit_stack Pattern

```python
async def shutdown(self):
    """Gracefully shutdown persistent server (exit_stack pattern)."""
    if self._persistent_process:
        try:
            # 1. Close stdin to signal EOF
            self._stdin.close()
            await self._stdin.wait_closed()

            # 2. Wait for graceful exit (5s timeout)
            await asyncio.wait_for(
                self._persistent_process.wait(),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            # 3. Force kill if not graceful
            self._persistent_process.kill()
            await self._persistent_process.wait()  # Prevent zombie
        finally:
            self._persistent_process = None
```

### 4. Health Monitoring & Auto-Recovery

```python
async def _health_check(self) -> bool:
    """Check if persistent connection is healthy."""
    if not self._persistent_process or self._persistent_process.returncode is not None:
        return False

    try:
        # Send lightweight ping request
        response = await self._send_request({
            "jsonrpc": "2.0",
            "id": "health_check",
            "method": "tools/list",
            "params": {}
        })
        return response is not None
    except Exception:
        return False

async def _ensure_connection(self) -> bool:
    """Ensure connection is healthy, reconnect if needed."""
    if not await self._health_check():
        logger.warning("MCP connection unhealthy, reconnecting...")
        await self._start_persistent_server()
    return True
```

---

## TodoWrite Micro-Tasks (10-15 min each)

### Phase 1: Core Infrastructure (60 min)

1. **Add persistent process attributes to DevStreamMCPClient.__init__**
   - `_persistent_process`, `_stdin`, `_stdout`, `_connection_lock`
   - `_startup_time`, `_request_count`, `_shutdown_event`
   - Initialize all to None/default values

2. **Implement _start_persistent_server() method**
   - Spawn Node.js process with asyncio.create_subprocess_exec
   - Capture stdin/stdout pipes
   - Set startup_time
   - Add error handling and logging

3. **Implement _send_request() for STDIO communication**
   - Write JSON-RPC to stdin with newline delimiter
   - Read response from stdout.readline()
   - Parse JSON response
   - 30s timeout with proper error handling

4. **Implement _ensure_connection() with lock**
   - Acquire connection_lock
   - Check if process alive
   - Call _start_persistent_server() if dead
   - Release lock

### Phase 2: Health & Recovery (45 min)

5. **Implement _health_check() method**
   - Return False if process is None or returncode != None
   - Send tools/list ping request
   - Return True if response received
   - Catch all exceptions → False

6. **Refactor _ensure_connection() with health check**
   - Call _health_check() first
   - If unhealthy, log warning and restart
   - Track restart count for monitoring

7. **Implement automatic connection recovery in _call_mcp_server()**
   - Replace subprocess spawn with _send_request()
   - Wrap in try-except for connection errors
   - Retry once on connection failure
   - Log all connection events

### Phase 3: Graceful Shutdown (30 min)

8. **Implement shutdown() method with exit_stack pattern**
   - Close stdin to signal EOF
   - Wait for graceful exit (5s timeout)
   - Force kill if timeout
   - Always await process.wait() to prevent zombies

9. **Implement __aenter__ and __aexit__ for context manager**
   - __aenter__: Call _ensure_connection()
   - __aexit__: Call shutdown()
   - Enable `async with DevStreamMCPClient()` pattern

10. **Register atexit handler for emergency cleanup**
    - Register shutdown() with atexit module
    - Ensure cleanup even on unexpected exits
    - Log emergency shutdown events

### Phase 4: Migration & Compatibility (30 min)

11. **Update _call_mcp_server() to use persistent connection**
    - Remove subprocess spawn code
    - Replace with _send_request()
    - Maintain same return signature
    - Backward compatible with existing code

12. **Add process monitoring metrics**
    - Track request_count
    - Track uptime (startup_time)
    - Log metrics every 100 requests
    - Expose get_stats() method

### Phase 5: Testing & Validation (15 min)

13. **Create unit tests for connection lifecycle**
    - Test _start_persistent_server()
    - Test _health_check()
    - Test shutdown() with timeout
    - Test auto-recovery on connection failure

14. **Integration test with devstream_update_task**
    - Run update_task with persistent client
    - Verify single process created
    - Verify zero zombies after execution
    - Verify < 1s response time

---

## Acceptance Criteria

### Functional Requirements
- ✅ Single persistent Node.js process for all MCP operations
- ✅ Automatic connection recovery on failures
- ✅ Graceful shutdown with no zombie processes
- ✅ Context manager support (`async with` pattern)
- ✅ Backward compatible with existing code

### Performance Requirements
- ✅ MCP tool response time < 1 second (vs 30s timeout)
- ✅ Zero database contention (single connection)
- ✅ Connection startup time < 2 seconds
- ✅ Auto-recovery time < 3 seconds

### Quality Requirements
- ✅ 95%+ test coverage for new code
- ✅ Zero mypy --strict errors
- ✅ Structured logging for all lifecycle events
- ✅ Full type hints and docstrings
- ✅ Error handling for all failure scenarios

### Operational Requirements
- ✅ Process monitoring metrics (uptime, request count)
- ✅ Health check logging for diagnostics
- ✅ Emergency cleanup via atexit handler
- ✅ Connection state observable via get_stats()

---

## Risk Mitigation

### Risk 1: Connection Hangs on Startup
**Mitigation**: 5-second timeout on _start_persistent_server(), retry once, fallback to subprocess spawn if persistent fails

### Risk 2: Process Dies Unexpectedly
**Mitigation**: _health_check() before every request, automatic reconnection, log all failures

### Risk 3: Memory Leak in Persistent Process
**Mitigation**: Monitor request_count, restart after 1000 requests (configurable), expose get_stats() for monitoring

### Risk 4: Breaking Existing Code
**Mitigation**: Maintain identical public API, backward compatible, extensive integration tests

---

## Rollout Strategy

### Phase 1: Immediate Fix (NOW)
- Add proper process cleanup to existing subprocess pattern
- Always `await process.wait()` after operations
- Prevents zombie accumulation

### Phase 2: Persistent Connection (This Plan)
- Implement persistent server
- Run in parallel with subprocess fallback
- Environment variable to enable: `DEVSTREAM_PERSISTENT_MCP=true`

### Phase 3: Full Migration (After Testing)
- Enable persistent by default
- Remove subprocess spawn code
- Monitor production metrics

### Phase 4: Optimization (Future)
- Connection pooling for multiple DB backends
- Request queuing for high concurrency
- Load balancing for distributed setups

---

## Success Metrics

**Before (Current State)**:
- 🔴 13+ zombie Node.js processes
- 🔴 30-second timeout on MCP calls
- 🔴 Database contention errors
- 🔴 Process leak grows unbounded

**After (Target State)**:
- ✅ 1 persistent Node.js process
- ✅ < 1 second MCP response time
- ✅ Zero database contention
- ✅ Zero zombie processes
- ✅ Graceful shutdown on exit

---

## Dependencies

**Python Libraries** (already in requirements.txt):
- asyncio (stdlib)
- json (stdlib)
- atexit (stdlib)

**Node.js Server** (already exists):
- `mcp-devstream-server/dist/index.js`
- STDIO transport support (already implemented)

**No new external dependencies required** ✅

---

## Documentation Updates Required

1. **mcp_client.py docstrings**: Update with persistent connection behavior
2. **Architecture docs**: Add persistent connection pattern diagram
3. **Troubleshooting guide**: Add connection health monitoring commands
4. **CLAUDE.md**: Update MCP integration section with new pattern

---

## Estimated Timeline

- **Phase 1** (Core Infrastructure): 60 min
- **Phase 2** (Health & Recovery): 45 min
- **Phase 3** (Graceful Shutdown): 30 min
- **Phase 4** (Migration): 30 min
- **Phase 5** (Testing): 15 min

**Total**: 180 minutes (3 hours)

---

## Completion Checklist

- [ ] All 14 micro-tasks completed
- [ ] Tests pass 100%
- [ ] Coverage ≥ 95%
- [ ] mypy --strict passes
- [ ] devstream_update_task completes in < 1s
- [ ] Zero zombie processes after 100 operations
- [ ] Documentation updated
- [ ] @code-reviewer validation passed

---

**Ready to implement?** Start with Phase 1, Task 1. Execute precisely. Test thoroughly. Complete fully. 🚀
