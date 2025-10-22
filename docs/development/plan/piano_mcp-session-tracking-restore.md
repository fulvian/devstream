# Piano Ripristino Session Tracking MCP (Opzione A - Partial Restore)

**Versione**: 1.0
**Data**: 2025-10-12
**Stato**: APPROVATO - In Esecuzione
**Priorità**: CRITICA

## 🎯 **Objective**

Risolvere i timeout di 40 secondi del server MCP DevStream ripristinando il minimo sistema di session tracking necessario per il funzionamento del PostToolUse hook.

## 🔍 **Root Cause Analysis**

### **Problema Identificato**:
- **Commit `e614b98`** (12 Oct 00:46): Ha rimosso la tabella `work_sessions` dal database
- **PostToolUse Hook**: Il metodo `_get_current_session_id()` fallisce cercando nella tabella non esistente
- **MCP Server**: Disconnessione ogni 40 secondi dovuta a fallimento del session tracking

### **Timeline**:
- **11 Oct 23:13**: Server funzionava (commit `8c8177e`)
- **12 Oct 00:00**: Primi timeout appariranno
- **12 Oct 00:46**: Commit problematico `e614b98`
- **12 Oct 23:03**: Session analysis completa

## 🏗️ **Architettura Corrente vs Obiettivo**

### **Stato Attuale (Broken)**:
```
MCP Server (ping OK) → PostToolUse Hook → _get_current_session_id() → ❌ TABLE NOT FOUND → Disconnessione
```

### **Stato Obiettivo (Fixed)**:
```
MCP Server (session ID) → PostToolUse Hook → _get_current_session_id() → ✅ work_sessions table → Sessione stabile
```

## 📋 **Implementation Plan**

### **FASE 1: Database Migration** (5 minuti)
**File**: `migrations/004_restore_work_sessions.sql`

```sql
-- Migration 004: Restore work_sessions table for MCP session tracking
-- Purpose: Fix MCP 40-second timeouts by restoring minimal session tracking
-- Risk: LOW - only creates new table, no existing data affected

CREATE TABLE IF NOT EXISTS work_sessions (
    id VARCHAR(32) NOT NULL PRIMARY KEY,
    plan_id VARCHAR(32),
    user_id VARCHAR(100),
    session_name VARCHAR(200),
    context_window_size INTEGER,
    tokens_used INTEGER,
    status VARCHAR(20) CHECK (status IN ('active', 'paused', 'completed', 'archived')),
    context_summary TEXT,
    active_tasks JSON,
    completed_tasks JSON,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    FOREIGN KEY(plan_id) REFERENCES intervention_plans(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_work_sessions_plan_id ON work_sessions(plan_id);
CREATE INDEX IF NOT EXISTS idx_work_sessions_status ON work_sessions(status);
CREATE INDEX IF NOT EXISTS idx_work_sessions_started_at ON work_sessions(started_at DESC);

-- Log migration completion
INSERT OR IGNORE INTO schema_version (version, description)
VALUES ('2.1.1', 'Restore work_sessions table for MCP session tracking');
```

### **FASE 2: Session ID Generation in MCP Server** (15 minuti)
**File**: `mcp-devstream-server/src/session-manager.ts` (NUOVO)

```typescript
/**
 * Minimal session manager for MCP server
 * Provides session ID generation and tracking for PostToolUse hook compatibility
 */

import { randomUUID } from 'crypto';
import { DevStreamDatabase } from './database.js';

export class SessionManager {
    private database: DevStreamDatabase;
    private currentSessionId: string | null = null;
    private sessionStartTime: Date | null = null;

    constructor(database: DevStreamDatabase) {
        this.database = database;
    }

    /**
     * Initialize or get current session
     */
    async getCurrentOrCreateSession(): Promise<string> {
        if (this.currentSessionId && this.isSessionActive()) {
            await this.updateLastActivity();
            return this.currentSessionId;
        }

        return await this.createNewSession();
    }

    private async createNewSession(): Promise<string> {
        const sessionId = `sess-${randomUUID().substring(0, 8)}`;

        await this.database.execute(`
            INSERT INTO work_sessions (id, user_id, session_name, status, started_at, last_activity_at)
            VALUES (?, ?, ?, ?, ?, ?)
        `, [
            sessionId,
            'claude-code',
            `MCP Session ${new Date().toISOString()}`,
            'active',
            new Date().toISOString(),
            new Date().toISOString()
        ]);

        this.currentSessionId = sessionId;
        this.sessionStartTime = new Date();

        console.error(`✅ Created new MCP session: ${sessionId}`);
        return sessionId;
    }

    private isSessionActive(): boolean {
        return this.sessionStartTime !== null &&
               (Date.now() - this.sessionStartTime.getTime()) < (2 * 60 * 60 * 1000); // 2 hours
    }

    private async updateLastActivity(): Promise<void> {
        if (!this.currentSessionId) return;

        await this.database.execute(`
            UPDATE work_sessions
            SET last_activity_at = ?
            WHERE id = ?
        `, [new Date().toISOString(), this.currentSessionId]);
    }

    async endCurrentSession(): Promise<void> {
        if (!this.currentSessionId) return;

        await this.database.execute(`
            UPDATE work_sessions
            SET status = 'completed', ended_at = ?
            WHERE id = ?
        `, [new Date().toISOString(), this.currentSessionId]);

        console.error(`🔚 Ended MCP session: ${this.currentSessionId}`);
        this.currentSessionId = null;
        this.sessionStartTime = null;
    }
}
```

### **FASE 3: Integrate Session Manager in MCP Server** (10 minuti)
**File**: `mcp-devstream-server/src/index.ts` (MODIFICA)

Aggiungere dopo le imports:
```typescript
import { SessionManager } from './session-manager.js';
```

Aggiungere in `DevStreamMcpServer` class:
```typescript
private sessionManager: SessionManager;

// In constructor:
this.sessionManager = new SessionManager(this.database);

// In setupHandlers(): aggiungere nuovo tool
{
  name: 'devstream_get_session_id',
  description: 'Get current MCP session ID for PostToolUse hook',
  inputSchema: {
    type: 'object',
    properties: {},
    additionalProperties: false
  }
}
```

Aggiungere in `CallToolRequestSchema` handler:
```typescript
case 'devstream_get_session_id':
  return await this.sessionManager.getCurrentOrCreateSession().then(sessionId => ({
    content: [{ type: 'text', text: sessionId }]
  }));
```

### **FASE 4: Update PostToolUse Hook** (10 minuti)
**File**: `.claude/hooks/devstream/memory/post_tool_use.py` (MODIFICA)

Aggiornare metodo `_get_current_session_id()`:
```python
async def _get_current_session_id(self) -> Optional[str]:
    """Get current active session ID using MCP server API."""
    try:
        import subprocess
        import json

        # Call MCP server to get session ID
        result = subprocess.run([
            'node', '-e', '''
            const { DevStreamMcpServer } = require('./mcp-devstream-server/dist/index.js');
            // Quick session ID fetch via direct database query
            '''
        ], capture_output=True, text=True, timeout=5)

        # Fallback: direct database query for active session
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT id FROM work_sessions
                WHERE status = 'active'
                ORDER BY last_activity_at DESC
                LIMIT 1
            """) as cursor:
                row = await cursor.fetchone()
                if row:
                    session_id = row[0]
                    return session_id

        return None
    except Exception as e:
        # Fallback: generate temporary session ID
        import uuid
        return f"temp-session-{uuid.uuid4().hex[:8]}"
```

### **FASE 5: Session Cleanup Mechanism** (10 minuti)
**File**: `mcp-devstream-server/src/session-cleanup.ts` (NUOVO)

```typescript
/**
 * Session cleanup utility to prevent database bloat
 */

export class SessionCleanup {
    private database: DevStreamDatabase;
    private cleanupInterval: NodeJS.Timeout;

    constructor(database: DevStreamDatabase) {
        this.database = database;
    }

    start(): void {
        // Run cleanup every hour
        this.cleanupInterval = setInterval(async () => {
            await this.cleanupOldSessions();
        }, 60 * 60 * 1000);
    }

    stop(): void {
        if (this.cleanupInterval) {
            clearInterval(this.cleanupInterval);
        }
    }

    private async cleanupOldSessions(): Promise<void> {
        const cutoffTime = new Date();
        cutoffTime.setHours(cutoffTime.getHours() - 24); // 24 hours ago

        const result = await this.database.execute(`
            UPDATE work_sessions
            SET status = 'archived', ended_at = ?
            WHERE status = 'active'
            AND last_activity_at < ?
        `, [new Date().toISOString(), cutoffTime.toISOString()]);

        console.error(`🧹 Cleaned up ${result.changes || 0} old sessions`);
    }
}
```

### **FASE 6: Testing e Validation** (20 minuti)

**Test 1: Database Migration**
```bash
sqlite3 data/devstream.db < migrations/004_restore_work_sessions.sql
sqlite3 data/devstream.db ".schema work_sessions"
```

**Test 2: MCP Server Session Generation**
```bash
cd mcp-devstream-server
npm run build
node dist/index.js ../data/devstream.db
```

**Test 3: Connection Stability**
```bash
# Test connection stability > 2 minutes
timeout 120s mcp call devstream_get_session_id
```

**Test 4: PostToolUse Hook**
```bash
.claude/hooks/devstream/memory/post_tool_use.py
# Verify _get_current_session_id() returns valid session ID
```

## 🔧 **Rollback Plan**

### **Immediate Rollback (if anything fails)**:
```bash
# 1. Remove work_sessions table
sqlite3 data/devstream.db "DROP TABLE IF EXISTS work_sessions;"

# 2. Revert MCP server changes
git checkout mcp-devstream-server/src/index.ts

# 3. Revert PostToolUse hook changes
git checkout .claude/hooks/devstream/memory/post_tool_use.py

# 4. Restart MCP server
killall -9 node
npm start
```

### **Rollback Verification**:
- [ ] MCP server starts without errors
- [ ] No work_sessions table in database
- [ ] Original functionality preserved

## 📊 **Success Criteria**

### **Primary Success Criteria**:
1. ✅ Tabella `work_sessions` creata con successo
2. ✅ MCP server genera session ID univoci
3. ✅ PostToolUse hook recupera session ID senza errori
4. ✅ Test stabilità: connessione attiva > 2 minuti senza timeout

### **Secondary Success Criteria**:
1. ✅ Memory storage funziona con session ID
2. ✅ Session cleanup automatico attivo
3. ✅ Performance degradation < 5%
4. ✅ Database bloat controllato

## ⚠️ **Risk Assessment**

### **Overall Risk**: BASSO
- **Data Loss**: ZERO (solo nuove tabelle)
- **Breaking Changes**: ZERO (solo aggiunte)
- **Service Disruption**: MINIMA (quick restart)
- **Rollback Complexity**: BASSA (comandi semplici)

### **Risk Mitigation**:
1. **Backup Database**: `cp data/devstream.db data/devstream.db.backup`
2. **Staged Deployment**: Testare ogni fase separatamente
3. **Monitoring**: Verifica immediata post-deployment
4. **Rollback Ready**: Comandi rollback preparati

## 📝 **Implementation Log**

### **Phase Status**:
- [x] Planning completed
- [ ] Migration script created
- [ ] Session manager implemented
- [ ] MCP server integration
- [ ] PostToolUse hook updated
- [ ] Cleanup mechanism implemented
- [ ] Testing completed
- [ ] Documentation updated

### **Progress Tracking**:
- **Start Time**: TBD
- **Estimated Completion**: TBD
- **Actual Completion**: TBD
- **Issues Encountered**: TBD

## 🔄 **Post-Implementation**

### **Monitoring**:
1. Verificare connessione stabile > 10 minuti
2. Monitorare database size growth
3. Verificare session cleanup function
4. Testare PostToolUse hook con session ID

### **Documentation Updates**:
1. Aggiornare `CLAUDE.md` con nuovo session tracking
2. Documentare session cleanup mechanism
3. Aggiornare troubleshooting guide
4. Creare knowledge base article

---

**Approval Status**: ✅ APPROVED
**Implementation Start**: 2025-10-12 23:10 UTC
**Estimated Duration**: 70 minuti
**Implementation Lead**: Claude Code + DevStream Protocol v2.2.0