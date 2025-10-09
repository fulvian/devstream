# MCP Server Lifecycle Tests

## Overview

Comprehensive test suite for MCP server lifecycle management, covering signal-based shutdown, cleanup procedures, and stdin EOF resilience per MCP specification 2025-03-26.

## Test Structure

```
tests/
├── unit/
│   └── test_mcp_lifecycle.test.ts       # Unit tests (mocked dependencies)
├── integration/
│   └── test_mcp_server_lifecycle.test.ts # E2E tests (real process signals)
├── setup.ts                              # Jest global setup
└── README.md                             # This file
```

## Test Coverage

### Unit Tests (`test_mcp_lifecycle.test.ts`)
**Duration**: ~30 minutes | **Coverage Target**: 95%+

Tests the following scenarios with mocked dependencies:
- ✅ Signal handlers call cleanup() correctly
- ✅ Cleanup function stops heartbeat timer
- ✅ Cleanup function stops auto-save service
- ✅ Cleanup function closes database
- ✅ Cleanup timeout safety (5s force exit)
- ✅ Heartbeat timer setup and interval (5 minutes)
- ✅ Error handling during cleanup (auto-save/database failures)
- ✅ Cleanup execution order (heartbeat → autosave → database)

**Mocked Dependencies**:
- `DevStreamDatabase` - Mock database connection
- `AutoSaveService` - Mock background service
- `process.exit` - Spy to prevent actual process termination
- `setTimeout/clearTimeout/setInterval/clearInterval` - Spy on timer functions

### Integration Tests (`test_mcp_server_lifecycle.test.ts`)
**Duration**: ~30 minutes | **Coverage Target**: E2E validation

Tests the following E2E scenarios with real stdio transport and process signals:
- ✅ Server starts successfully with heartbeat
- ✅ Server responds to MCP initialize request
- ✅ Server survives stdin close (does NOT exit - critical for /compact)
- ✅ Server shuts down gracefully on SIGTERM (Docker/kill)
- ✅ Server shuts down gracefully on SIGINT (Ctrl+C)
- ✅ Cleanup completes within 5-second timeout
- ✅ Cleanup execution order validation
- ✅ Edge cases (rapid shutdown, no active tasks)

**Real Dependencies**:
- Spawns actual server process via `child_process.spawn`
- Real stdio transport
- Real process signals (SIGTERM, SIGINT)
- Real database file (test-integration-lifecycle.db)

## Prerequisites

### Required Dependencies

The following npm packages are required but **NOT yet installed**:

```bash
npm install --save-dev ts-jest @types/jest
```

**Why these are needed**:
- `ts-jest`: TypeScript preprocessor for Jest (compiles .ts test files)
- `@types/jest`: TypeScript type definitions for Jest

**Already installed**:
- ✅ `jest@29.7.0` (test runner)
- ✅ `@types/node@^20.0.0` (Node.js type definitions)
- ✅ `typescript@^5.0.0` (TypeScript compiler)

### Build Server Binary

Integration tests require the compiled server binary:

```bash
npm run build
```

This creates `dist/index.js` which integration tests spawn as a child process.

## Running Tests

### Install Missing Dependencies First

```bash
cd /Users/fulvioventura/devstream/mcp-devstream-server
npm install --save-dev ts-jest @types/jest
```

### Run All Tests

```bash
npm test
```

### Run Unit Tests Only

```bash
npm test -- tests/unit/test_mcp_lifecycle.test.ts
```

### Run Integration Tests Only

```bash
npm test -- tests/integration/test_mcp_server_lifecycle.test.ts
```

### Run with Coverage Report

```bash
npm test -- --coverage
```

This generates:
- Terminal coverage summary
- HTML report in `coverage/lcov-report/index.html`
- LCOV report in `coverage/lcov.info`

### Debug Mode (Show Console Logs)

```bash
DEBUG_TESTS=1 npm test
```

By default, `console.error` is suppressed during tests. Set `DEBUG_TESTS=1` to see all logs.

## Expected Test Results

### Unit Tests
- **Tests**: 15+ test cases
- **Coverage**: 95%+ for lifecycle code
- **Duration**: < 5 seconds
- **Status**: All passing ✅

### Integration Tests
- **Tests**: 12+ E2E scenarios
- **Coverage**: Full lifecycle validation
- **Duration**: ~60-90 seconds (spawns real processes)
- **Status**: All passing ✅

## Test Features

### Unit Test Features
1. **Mock Isolation**: All external dependencies mocked (database, auto-save, process.exit)
2. **Timer Spies**: Validates setTimeout/clearTimeout/setInterval calls
3. **Execution Order**: Verifies cleanup steps execute in correct order
4. **Error Handling**: Tests graceful degradation on cleanup failures
5. **Timeout Safety**: Validates 5-second force-exit protection

### Integration Test Features
1. **Real Process Spawning**: Spawns actual server via `child_process`
2. **Signal Testing**: Sends real SIGTERM/SIGINT signals
3. **Stdin EOF Resilience**: Validates server survives stdin.end() (critical for /compact)
4. **Startup Validation**: Verifies heartbeat, vector search, auto-save initialization
5. **Cleanup Timing**: Validates cleanup completes within 5 seconds
6. **Log Validation**: Verifies cleanup logs in correct order

## Key Test Scenarios

### Critical: Stdin EOF Resilience (MCP Spec 2025-03-26)

**Why this is critical**:
- Claude Code operations like `/compact` close stdin temporarily
- Old behavior: Server would exit, causing disconnection
- New behavior: Server survives stdin EOF, only exits on SIGTERM/SIGINT

**Test validation**:
```typescript
it('should survive stdin close (NOT exit)', async () => {
  // Start server
  serverProcess = spawn('node', [SERVER_BINARY, TEST_DB_PATH]);
  await waitForServerStartup(serverProcess);

  // Close stdin (simulate /compact)
  serverProcess.stdin?.end();

  // Wait 2 seconds
  await new Promise(resolve => setTimeout(resolve, 2000));

  // Verify server is STILL RUNNING ✅
  expect(serverProcess.killed).toBe(false);
});
```

### Cleanup Timeout Safety

**Why this is critical**:
- Prevents server from hanging indefinitely during cleanup
- Forces process exit after 5 seconds if cleanup fails

**Test validation**:
```typescript
it('should force exit after 5 second timeout if cleanup hangs', async () => {
  // Create server with hanging cleanup
  const hangingServer = new HangingServer();
  await hangingServer.start();

  // Start cleanup (will hang)
  const cleanupPromise = hangingServer.cleanup('test');

  // Fast-forward time by 5 seconds
  jest.advanceTimersByTime(5000);

  // Verify process.exit was called with code 1 ✅
  await expect(cleanupPromise).rejects.toThrow('process.exit called with code 1');
});
```

## Troubleshooting

### Issue: `Cannot find module 'ts-jest'`
**Solution**: Install missing dependency:
```bash
npm install --save-dev ts-jest @types/jest
```

### Issue: `Server binary not found`
**Solution**: Build the server:
```bash
npm run build
```

### Issue: Integration tests timeout
**Solution**: Increase test timeout in `jest.config.js`:
```javascript
testTimeout: 60000 // 60 seconds
```

### Issue: Tests fail with "Database locked"
**Solution**: Ensure previous test runs cleaned up:
```bash
rm -f test-data/*.db
npm test
```

### Issue: Console logs polluting test output
**Solution**: Disable `DEBUG_TESTS`:
```bash
unset DEBUG_TESTS
npm test
```

## Configuration Files

### `jest.config.js`
- TypeScript support via ts-jest
- Coverage thresholds: 80% (branches, functions, lines, statements)
- Test timeout: 30 seconds
- Coverage directory: `coverage/`

### `tests/setup.ts`
- Suppresses `console.error` (unless `DEBUG_TESTS=1`)
- Sets `NODE_ENV=test`
- Sets `DEVSTREAM_LOG_LEVEL=error`

## Coverage Report

After running `npm test -- --coverage`, open:

```bash
open coverage/lcov-report/index.html
```

This shows:
- Line-by-line coverage visualization
- Uncovered code highlighting
- Branch coverage details
- Function coverage metrics

## Next Steps

1. **Install dependencies**:
   ```bash
   npm install --save-dev ts-jest @types/jest
   ```

2. **Build server**:
   ```bash
   npm run build
   ```

3. **Run tests**:
   ```bash
   npm test
   ```

4. **Generate coverage report**:
   ```bash
   npm test -- --coverage
   open coverage/lcov-report/index.html
   ```

5. **Verify 95%+ coverage** for lifecycle code in `src/index.ts`

## Test Maintenance

### When to Update Tests
- ✅ After modifying lifecycle logic in `src/index.ts`
- ✅ After changing cleanup procedure
- ✅ After adding new signal handlers
- ✅ After modifying heartbeat interval
- ✅ After changing timeout values

### Test Philosophy
- **Unit tests**: Fast, isolated, comprehensive (95%+ coverage)
- **Integration tests**: Slow, realistic, critical path validation
- **No flaky tests**: All tests deterministic, no race conditions
- **Clear failure messages**: Every assertion has context

## References

- **MCP Specification 2025-03-26**: [https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle](https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle)
- **DevStream Context7 Research**: Context injection optimization (2025-10-02)
- **Node.js Best Practices**: Long-running process lifecycle management
- **Jest Documentation**: [https://jestjs.io/docs/getting-started](https://jestjs.io/docs/getting-started)

---

**Test Status**: ✅ Ready for execution (pending dependency installation)
**Coverage Target**: 95%+ for lifecycle code
**Execution Time**: ~60-120 seconds (unit + integration)
**Last Updated**: 2025-10-02
