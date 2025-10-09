# DevStream Kernel Panic Prevention - Complete Implementation Plan

**Task ID**: `kernel-panic-prevention-2025-10-08`
**Priority**: 10/10 (CRITICAL)
**Phase**: System Stability & Crash Prevention
**Estimated Duration**: 3 hours (180 minutes)
**Status**: Ready for Implementation

---

## 🚨 EXECUTIVE SUMMARY

### Problem Statement
DevStream is causing macOS kernel panics through SQLite database corruption and Spotlight indexing conflicts. Multiple concurrent sessions exacerbate the issue, leading to system-wide instability.

### Root Cause Analysis
1. **SQLite DELETE Mode**: No WAL mode, `busy_timeout=0`, causing race conditions
2. **Spotlight Conflict**: mds process indexing database during write operations
3. **Concurrent Access**: 11+ processes accessing same database without coordination
4. **Resource Exhaustion**: File descriptor leaks and memory pressure

### Solution Architecture
Three-phase implementation addressing immediate protection, connection management, and session coordination.

---

## 📋 IMPLEMENTATION PHASES

### FASE 1: Immediate Protection (30 minutes)
**Objective**: Stop kernel panics immediately with minimal code changes
**Risk Level**: LOW (reversible changes)
**Dependencies**: None

#### FASE 1.1: Spotlight Exclusion (10 minutes)
**Agent**: @devops-specialist
**File**: `scripts/setup_spotlight_exclusion.sh` (NEW)

**Micro-tasks**:
1. Create exclusion script with `.noindex` directory handling
2. Implement atomic directory rename with symlink fallback
3. Add xattr metadata defense-in-depth
4. Verify exclusion effectiveness with `mdls`
5. Make script idempotent and error-handled

**Acceptance Criteria**:
- ✅ `data/` renamed to `data.noindex/`
- ✅ All database paths updated in codebase
- ✅ xattr attributes applied to DB files
- ✅ Spotlight exclusion verified
- ✅ Script can be run multiple times safely

#### FASE 1.2: SQLite WAL Mode Implementation (10 minutes)
**Agent**: @python-specialist
**Files**:
- `.claude/hooks/devstream/utils/sqlite_vec_helper.py` (MODIFY)
- `.claude/hooks/devstream/sessions/work_session_manager.py` (MODIFY)

**Micro-tasks**:
1. Add WAL pragmas to `get_db_connection_with_vec()`
2. Implement `busy_timeout=30000` and `synchronous=NORMAL`
3. Update async connection patterns in work_session_manager
4. Add WAL mode verification in connection setup
5. Test backward compatibility

**Acceptance Criteria**:
- ✅ All connections use WAL mode
- ✅ 30-second busy timeout configured
- ✅ sqlite-vec functionality preserved
- ✅ Async patterns updated

#### FASE 1.3: Database Path Updates (10 minutes)
**Agent**: @python-specialist
**Files**: 6 files with hardcoded `data/` paths

**Micro-tasks**:
1. Update sqlite_vec_helper.py to use `data.noindex/`
2. Update work_session_manager.py paths
3. Update post_tool_use.py paths
4. Update session_data_extractor.py paths
5. Update backfill_embeddings.py paths
6. Update checkpoint_manager.py paths

**Acceptance Criteria**:
- ✅ All paths use `data.noindex/`
- ✅ Backward compatibility maintained
- ✅ No hardcoded paths remain

---

### FASE 2: Connection Management (60 minutes)
**Objective**: Centralized SQLite connection handling with WAL enforcement
**Risk Level**: MEDIUM (requires refactoring)
**Dependencies**: FASE 1 complete

#### FASE 2.1: Connection Manager Creation (20 minutes)
**Agent**: @python-specialist
**File**: `.claude/hooks/devstream/utils/sqlite_connection_manager.py` (NEW)

**Micro-tasks**:
1. Create SQLiteConnectionManager singleton class
2. Implement WAL pragma enforcement in all connections
3. Add sqlite-vec extension loading support
4. Create async context manager for connections
5. Add connection lifecycle management

**Acceptance Criteria**:
- ✅ Singleton pattern implemented
- ✅ WAL pragmas enforced on all connections
- ✅ sqlite-vec extension support
- ✅ Async context manager working
- ✅ Type hints and docstrings complete

#### FASE 2.2: Legacy Code Refactoring (20 minutes)
**Agent**: @python-specialist
**Files**: Update 21+ connection points

**Micro-tasks**:
1. Refactor sqlite_vec_helper.py to use connection manager
2. Update work_session_manager.py async connections
3. Replace direct sqlite3.connect() calls
4. Update post_tool_use.py connections
5. Update session_data_extractor.py connections
6. Update backfill_embeddings.py connections
7. Update checkpoint_manager.py connections

**Acceptance Criteria**:
- ✅ All 21+ connection points refactored
- ✅ No direct sqlite3.connect() calls remain
- ✅ Connection manager used everywhere
- ✅ Error handling preserved

#### FASE 2.3: Connection Pool Implementation (20 minutes)
**Agent**: @python-specialist
**File**: Enhancement to sqlite_connection_manager.py

**Micro-tasks**:
1. Add connection pooling with size limits
2. Implement health check for stale connections
3. Add automatic connection recycling
4. Create connection metrics monitoring
5. Add graceful degradation on pool exhaustion

**Acceptance Criteria**:
- ✅ Connection pool with configurable size
- ✅ Health checks implemented
- ✅ Automatic recycling working
- ✅ Metrics collection active
- ✅ Graceful degradation functional

---

### FASE 3: Session Coordination (45 minutes)
**Objective**: Multi-session tracking and coordination to prevent conflicts
**Risk Level**: MEDIUM (new system components)
**Dependencies**: FASE 2 complete

#### FASE 3.1: Session Coordinator Implementation (25 minutes)
**Agent**: @python-specialist
**File**: `.claude/hooks/devstream/utils/session_coordinator.py` (NEW)

**Micro-tasks**:
1. Create SessionCoordinator class with PID tracking
2. Implement session registry with atomic file operations
3. Add heartbeat mechanism for stale session detection
4. Create file locking with fcntl for critical operations
5. Add session health monitoring and cleanup

**Acceptance Criteria**:
- ✅ PID tracking system working
- ✅ Atomic session registry implemented
- ✅ Heartbeat mechanism functional
- ✅ File locking with fcntl working
- ✅ Stale session cleanup active

#### FASE 3.2: Hook Integration (10 minutes)
**Agent**: @python-specialist
**Files**:
- `.claude/hooks/devstream/sessions/session_start.py` (MODIFY)
- `.claude/hooks/devstream/sessions/session_end.py` (MODIFY)

**Micro-tasks**:
1. Integrate session registration in session_start.py
2. Add session unregistration in session_end.py
3. Add error handling for registration failures
4. Log session coordination events
5. Test hook integration

**Acceptance Criteria**:
- ✅ Session registration on startup
- ✅ Session unregistration on exit
- ✅ Error handling robust
- ✅ Structured logging added
- ✅ Hook integration tested

#### FASE 3.3: Session Limits Implementation (10 minutes)
**Agent**: @python-specialist
**File**: Enhancement to session_coordinator.py

**Micro-tasks**:
1. Add configurable session limits
2. Implement session queuing mechanism
3. Add graceful degradation when limits exceeded
4. Create session priority system
5. Add monitoring and alerting

**Acceptance Criteria**:
- ✅ Session limits configurable
- ✅ Queuing mechanism working
- ✅ Graceful degradation implemented
- ✅ Priority system functional
- ✅ Monitoring active

---

### FASE 4: Testing & Validation (45 minutes)
**Objective**: Comprehensive testing to ensure crash prevention works
**Risk Level**: LOW (testing only)
**Dependencies**: FASE 3 complete

#### FASE 4.1: Unit Tests (15 minutes)
**Agent**: @testing-specialist
**File**: `tests/unit/test_sqlite_connection_manager.py` (NEW)

**Micro-tasks**:
1. Test singleton pattern enforcement
2. Verify WAL mode configuration
3. Test connection pooling functionality
4. Validate async context managers
5. Test error handling and edge cases

**Acceptance Criteria**:
- ✅ 95%+ test coverage
- ✅ All WAL pragmas verified
- ✅ Connection pool tested
- ✅ Async patterns validated
- ✅ Error cases covered

#### FASE 4.2: Integration Tests (15 minutes)
**Agent**: @testing-specialist
**File**: `tests/integration/test_multi_session_crash_prevention.py` (NEW)

**Micro-tasks**:
1. Test 2 concurrent sessions writing to DB
2. Validate session coordination
3. Test Spotlight exclusion effectiveness
4. Verify file locking mechanisms
5. Test graceful degradation scenarios

**Acceptance Criteria**:
- ✅ 2+ concurrent sessions working
- ✅ Session coordination validated
- ✅ Spotlight exclusion verified
- ✅ File locking tested
- ✅ Degradation scenarios handled

#### FASE 4.3: Stress Testing (15 minutes)
**Agent**: @testing-specialist
**File**: `tests/integration/test_stress_multi_session.py` (NEW)

**Micro-tasks**:
1. Create 5 concurrent session stress test
2. Run 10-minute sustained load test
3. Monitor system resources during test
4. Validate database integrity after stress
5. Check for memory leaks or fd exhaustion

**Acceptance Criteria**:
- ✅ 5 sessions sustained for 10 minutes
- ✅ System resources stable
- ✅ Database integrity maintained
- ✅ No memory leaks detected
- ✅ File descriptors within limits

---

## 🎯 AGENT DELEGATION MATRIX

| Phase | Agent | Responsibility | Tools Required |
|-------|-------|----------------|----------------|
| FASE 1.1 | @devops-specialist | Spotlight exclusion script | Bash, file system operations |
| FASE 1.2 | @python-specialist | SQLite WAL mode implementation | Python, SQLite, type hints |
| FASE 1.3 | @python-specialist | Database path updates | Python, refactoring |
| FASE 2.1 | @python-specialist | Connection manager creation | Python, async patterns, SQLite |
| FASE 2.2 | @python-specialist | Legacy code refactoring | Python, code analysis |
| FASE 2.3 | @python-specialist | Connection pooling | Python, concurrency patterns |
| FASE 3.1 | @python-specialist | Session coordinator | Python, fcntl, psutil |
| FASE 3.2 | @python-specialist | Hook integration | Python, existing hooks |
| FASE 3.3 | @python-specialist | Session limits | Python, configuration |
| FASE 4.1 | @testing-specialist | Unit tests | pytest, mocking |
| FASE 4.2 | @testing-specialist | Integration tests | pytest, async testing |
| FASE 4.3 | @testing-specialist | Stress tests | pytest, performance testing |

---

## 📊 SUCCESS METRICS & ACCEPTANCE CRITERIA

### Functional Requirements
- ✅ Zero kernel panics in 24-hour testing
- ✅ 5+ concurrent sessions supported
- ✅ Database integrity maintained
- ✅ Performance impact <5%

### Quality Requirements
- ✅ 95%+ test coverage for new code
- ✅ 100% type hints coverage
- ✅ Structured logging throughout
- ✅ Error handling for all edge cases

### System Requirements
- ✅ Backward compatibility maintained
- ✅ Rollback procedures documented
- ✅ Monitoring dashboards active
- ✅ Resource limits enforced

---

## 🚨 RISK MITIGATION STRATEGIES

### Technical Risks
- **SQLite WAL incompatibility**: Comprehensive testing before deployment
- **Performance degradation**: Benchmark before/after implementation
- **Connection leaks**: Resource monitoring and automatic cleanup

### Operational Risks
- **Deployment failure**: Atomic rollback procedures ready
- **System instability**: Gradual rollout with monitoring
- **Data corruption**: Full backups before implementation

### Mitigation Procedures
```bash
# Emergency Rollback (if critical issues)
git checkout HEAD -- .claude/hooks/devstream/
mv data.noindex data
sqlite3 data/devstream.db "PRAGMA journal_mode=DELETE;"
```

---

## 📈 MONITORING & OBSERVABILITY

### Key Metrics
- Kernel panic frequency (target: 0)
- Database connection count (limit: 10 per session)
- File descriptor usage (limit: 100 per process)
- Memory usage (target: <2GB per session)

### Alerting Thresholds
- Database connection failures >5/min
- File descriptor usage >80% of limit
- Memory usage >90% of target
- Session coordination failures

### Dashboards
- Real-time session monitoring
- Database connection pool status
- System resource utilization
- Error rate tracking

---

## 🔄 IMPLEMENTATION SEQUENCE

### Prerequisites
1. Backup current database (`cp data/devstream.db data/devstream.db.backup`)
2. Verify Python venv (`.devstream/bin/python --version`)
3. Install required dependencies (`psutil`, `aiofiles` if missing)

### Execution Order (CRITICAL)
1. ✅ FASE 1.1: Spotlight exclusion (must run first)
2. ✅ FASE 1.2: WAL mode implementation
3. ✅ FASE 1.3: Path updates
4. ✅ FASE 2.1: Connection manager creation
5. ✅ FASE 2.2: Legacy refactoring
6. ✅ FASE 2.3: Connection pooling
7. ✅ FASE 3.1: Session coordination
8. ✅ FASE 3.2: Hook integration
9. ✅ FASE 3.3: Session limits
10. ✅ FASE 4.1: Unit tests
11. ✅ FASE 4.2: Integration tests
12. ✅ FASE 4.3: Stress tests

### Validation Checkpoints
- After FASE 1: Verify Spotlight exclusion and WAL mode
- After FASE 2: Test connection manager functionality
- After FASE 3: Validate session coordination
- After FASE 4: Complete system validation

---

## 📚 DOCUMENTATION DELIVERABLES

1. **Architecture Documentation**
   - SQLite WAL mode architecture
   - Session coordination design
   - Connection manager patterns

2. **Operational Documentation**
   - Deployment procedures
   - Troubleshooting guides
   - Monitoring dashboards

3. **Development Documentation**
   - API documentation for new components
   - Test procedures and requirements
   - Code contribution guidelines

---

## 🎯 FINAL APPROVAL CHECKLIST

### Pre-Implementation
- [ ] Database backed up
- [ ] Environment verified
- [ ] Dependencies installed
- [ ] Rollback procedures tested

### Post-Implementation
- [ ] All tests passing (100% pass rate)
- [ ] 95%+ coverage achieved
- [ ] Performance benchmarks met
- [ ] Monitoring active
- [ ] Documentation updated

### Production Readiness
- [ ] Zero kernel panics in 24-hour test
- [ ] Multi-session support verified
- [ ] Resource usage within limits
- [ ] Error handling validated
- [ ] Team training completed

---

**Document Version**: 1.0
**Created**: 2025-10-08
**Status**: ✅ Ready for Implementation
**Estimated Completion**: 2025-10-08 (same day)

---

*This plan follows DevStream 7-step protocol and incorporates Context7 research findings (SQLite Trust Score 10.0, aiosqlite Trust Score 7.7).*