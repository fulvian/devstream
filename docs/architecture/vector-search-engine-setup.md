# Vector Search Engine Setup - sqlite-vec Extension

**Status**: Production | **Updated**: 2025-10-10 | **Context7 Trust Score**: 9.7/10

---

## Overview

DevStream's semantic search system uses `sqlite-vec` (v0.1.6) for vector similarity search via SQLite virtual tables. This document covers extension loading patterns across different runtime environments.

**Key Features**:
- Hybrid Search (RRF - Reciprocal Rank Fusion): Semantic (60%) + Keyword (40%)
- Automatic synchronization via database triggers
- WAL mode for concurrent read/write operations
- Metadata filtering via standard SQL WHERE clauses

---

## Extension Loading Patterns

### Node.js (MCP Server) ✅ RECOMMENDED

**Package**: `sqlite-vec` (npm)
**Runtime**: Node.js with `better-sqlite3`
**Location**: `mcp-devstream-server/src/tools/hybrid-search.ts`

```javascript
import * as sqliteVec from "sqlite-vec";
import Database from "better-sqlite3";

// Initialize database
const db = new Database("data/devstream.db");

// Load sqlite-vec extension
sqliteVec.load(db);  // Automatic extension loading (NPM package includes precompiled binary)

// Verify extension loaded
const { vec_version } = db.prepare("select vec_version()").get();
console.log(`sqlite-vec version: ${vec_version}`);  // Expected: 0.1.6
```

**Benefits**:
- ✅ **No manual .load needed** - NPM package handles precompiled extension
- ✅ Cross-platform (macOS, Linux, Windows)
- ✅ Works with better-sqlite3, node:sqlite, bun:sqlite

**Installation**:
```bash
cd mcp-devstream-server
npm install sqlite-vec
npm install better-sqlite3
```

---

### Python (Hooks) - DIRECT SQL PATTERN

**Location**: `.claude/hooks/devstream/memory/post_tool_use.py`
**Pattern**: Direct SQL via `aiosqlite` (no vec0 extension needed)

```python
import aiosqlite
import json

# Update semantic_memory with embedding
async with aiosqlite.connect('data/devstream.db') as db:
    await db.execute(
        "UPDATE semantic_memory SET embedding = ? WHERE id = ?",
        (json.dumps(embedding), memory_id)
    )
    await db.commit()

# Note: Database triggers automatically sync to vec_semantic_memory
# No vec0 extension loading required for Python hooks
```

**Why No Extension**:
- Python hooks ONLY write to `semantic_memory` table (standard SQLite)
- Database triggers (executed by Node.js MCP server) handle vec0 sync
- Embedding generation: Ollama HTTP API (no SQLite extension needed)

**Database Trigger** (Executed by Node.js MCP with vec0):
```sql
CREATE TRIGGER sync_embedding_update
AFTER UPDATE OF embedding ON semantic_memory
WHEN NEW.embedding IS NOT NULL AND NEW.embedding != ''
BEGIN
    DELETE FROM vec_semantic_memory WHERE memory_id = NEW.id;
    INSERT INTO vec_semantic_memory(embedding, memory_id, content_preview)
    VALUES (vec_f32(JSON_EXTRACT(NEW.embedding, '$')), NEW.id, ...);
END;
```

---

### Python (Backfill Scripts) - NO EXTENSION

**Location**: `scripts/backfill_embeddings_production.py`
**Pattern**: Standard `sqlite3` module (trigger disabled during backfill)

```python
import sqlite3
import json

# Connect with standard sqlite3
conn = sqlite3.connect('data/devstream.db')

# Update embedding (trigger disabled during backfill for performance)
cursor.execute(
    "UPDATE semantic_memory SET embedding = ? WHERE id = ?",
    (json.dumps(embedding), memory_id)
)
conn.commit()
```

**Backfill Workflow**:
1. **Disable trigger** → Prevent vec0 calls during bulk updates
2. **Bulk update** → 32K records with standard Python sqlite3
3. **Manual vec sync** → Run sync script with Node.js + vec0 extension
4. **Re-enable trigger** → Resume automatic sync for new records

**Manual Vec Sync** (After Backfill):
```bash
# Execute vec sync with Node.js runtime (has vec0 extension)
node scripts/sync_vec_semantic_memory.js
```

---

## Hybrid Search (RRF - Reciprocal Rank Fusion)

**Algorithm**: Combines semantic (vector) + keyword (FTS5) search with weighted RRF scoring.

**Implementation**: `mcp-devstream-server/src/tools/hybrid-search.ts`

```typescript
async function hybridSearch(query: string, limit: number = 10): Promise<SearchResult[]> {
  const db = new Database("data/devstream.db");
  sqliteVec.load(db);

  // Generate query embedding
  const queryEmbedding = await generateEmbedding(query);

  // Hybrid RRF query
  const results = db.prepare(`
    WITH vec_matches AS (
      SELECT
        memory_id,
        ROW_NUMBER() OVER (ORDER BY distance) AS rank_number
      FROM vec_semantic_memory
      WHERE embedding MATCH ?
        AND k = ?
    ),
    fts_matches AS (
      SELECT
        id AS memory_id,
        ROW_NUMBER() OVER (ORDER BY rank) AS rank_number
      FROM fts_semantic_memory
      WHERE content MATCH ?
      LIMIT ?
    )
    SELECT
      COALESCE(v.memory_id, f.memory_id) AS memory_id,
      COALESCE(1.0 / (60 + v.rank_number), 0.0) * 0.6 +  -- Semantic weight: 60%
      COALESCE(1.0 / (60 + f.rank_number), 0.0) * 0.4    -- Keyword weight: 40%
        AS combined_rank
    FROM vec_matches v
    FULL OUTER JOIN fts_matches f ON v.memory_id = f.memory_id
    ORDER BY combined_rank DESC
    LIMIT ?
  `).all(
    JSON.stringify(queryEmbedding),  // vec_matches parameter
    limit * 2,                        // Over-fetch for RRF
    query,                            // fts_matches parameter
    limit * 2,                        // Over-fetch for RRF
    limit                             // Final result limit
  );

  return results;
}
```

**RRF Formula**:
- `RRF_score = 1.0 / (k + rank)` where `k = 60` (constant)
- Semantic weight: 60% (vector similarity)
- Keyword weight: 40% (FTS5 full-text search)
- Combined rank: Weighted sum of both scores

**Performance**:
- Search latency: <500ms (typical)
- Over-fetch factor: 2x (improves RRF accuracy)
- Metadata filtering: Zero latency (standard SQL WHERE)

---

## Metadata Filtering

**Pattern**: Standard SQL WHERE clauses on `semantic_memory` table.

```typescript
// Filter by content type
const results = db.prepare(`
  SELECT m.*, v.distance
  FROM semantic_memory m
  JOIN vec_semantic_memory v ON v.memory_id = m.id
  WHERE v.embedding MATCH ? AND v.k = ?
    AND m.content_type = ?  -- Standard SQL filtering
  ORDER BY v.distance
  LIMIT ?
`).all(queryEmbedding, 10, 'code', 10);

// Filter by date range
const results = db.prepare(`
  SELECT m.*, v.distance
  FROM semantic_memory m
  JOIN vec_semantic_memory v ON v.memory_id = m.id
  WHERE v.embedding MATCH ? AND v.k = ?
    AND m.created_at > ?  -- Temporal filtering
  ORDER BY v.distance
  LIMIT ?
`).all(queryEmbedding, 10, '2025-10-01', 10);

// Filter by keywords (JSON array contains)
const results = db.prepare(`
  SELECT m.*, v.distance
  FROM semantic_memory m
  JOIN vec_semantic_memory v ON v.memory_id = m.id
  WHERE v.embedding MATCH ? AND v.k = ?
    AND JSON_EXTRACT(m.keywords, '$') LIKE '%python%'  -- Keyword filtering
  ORDER BY v.distance
  LIMIT ?
`).all(queryEmbedding, 10, 10);
```

**Benefits**:
- ✅ No performance penalty (SQLite index support)
- ✅ Composable with vector search
- ✅ Standard SQL syntax (no vec0-specific filtering)

---

## Performance Optimization

### Batch Size (Backfill)

**Configuration**: 16 records/batch (conservative)
- Ollama processing: ~150-200ms/embedding
- Batch duration: ~2.5-3s/batch
- Total throughput: ~5 records/sec

**Research Findings** (Context7 - ollama-python):
- ✅ No explicit batch limit in Ollama API
- ✅ Batch processing supported: `input=['text1', 'text2', ...]`
- ✅ Our batch size (16) is conservative and safe

### keep_alive Configuration

**Setting**: `keep_alive="5m"` (auto-unload after 5 min idle)

**Benefits**:
- ✅ Memory optimization (model unloads when idle)
- ⚠️ Cold start penalty: ~2-3s when model reloads

**Use Case**: Optimal for backfill workloads (intermittent bursts)

**Example** (Ollama API):
```javascript
const response = await fetch('http://localhost:11434/api/embed', {
  method: 'POST',
  body: JSON.stringify({
    model: 'embeddinggemma:300m',
    input: texts,
    keep_alive: '5m'  // Auto-unload optimization
  })
});
```

### WAL Mode (Write-Ahead Logging)

**Status**: ✅ Enabled (better concurrency)

**Benefits**:
- Readers don't block writers
- Atomic transactions
- Checkpoint control

**Verification**:
```sql
PRAGMA journal_mode;  -- Returns: wal
```

**Manual Checkpoint** (if needed):
```sql
PRAGMA wal_checkpoint(FULL);
```

---

## Database Schema

### semantic_memory (Main Table)

```sql
CREATE TABLE semantic_memory (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    content_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    keywords TEXT,  -- JSON array
    embedding TEXT  -- JSON array of floats (768 dimensions)
);
```

### vec_semantic_memory (Virtual Table)

```sql
CREATE VIRTUAL TABLE vec_semantic_memory USING vec0(
    embedding FLOAT[768],  -- Vector index (768 dimensions)
    content_type TEXT,     -- Metadata
    memory_id TEXT,        -- FK to semantic_memory.id
    content_preview TEXT   -- For display in search results
);
```

**Sync Trigger** (Automatic):
```sql
CREATE TRIGGER sync_embedding_update
AFTER UPDATE OF embedding ON semantic_memory
WHEN NEW.embedding IS NOT NULL
BEGIN
    DELETE FROM vec_semantic_memory WHERE memory_id = NEW.id;
    INSERT INTO vec_semantic_memory(embedding, memory_id, ...)
    VALUES (vec_f32(JSON_EXTRACT(NEW.embedding, '$')), NEW.id, ...);
END;
```

---

## Troubleshooting

### Issue: "no such module: vec0"

**Cause**: sqlite-vec extension not loaded in runtime

**Fix (Node.js)**:
```javascript
import * as sqliteVec from "sqlite-vec";
const db = new Database("data/devstream.db");
sqliteVec.load(db);  // Must call before any vec0 queries
```

**Fix (Python - Backfill)**:
- Disable trigger BEFORE backfill
- Use standard sqlite3 (no vec0 needed)
- Manual vec sync AFTER backfill (with Node.js)

### Issue: Search returns no results

**Diagnosis**:
1. Check embedding coverage: `SELECT COUNT(*) FROM semantic_memory WHERE embedding IS NOT NULL`
2. Verify vec sync: `SELECT COUNT(*) FROM vec_semantic_memory`
3. Test query embedding generation: `curl http://localhost:11434/api/embed`

**Fix**: Run backfill script + manual vec sync

### Issue: Slow search performance (>1s)

**Diagnosis**:
- Check database size: `SELECT COUNT(*) FROM semantic_memory`
- Verify WAL checkpoint: `PRAGMA wal_checkpoint(FULL)`

**Fix**: Binary quantization for large datasets (8x storage reduction)

---

## References

**Context7 Research**:
- sqlite-vec (Trust Score 9.7/10): `/asg017/sqlite-vec`
- ollama-python (Trust Score 7.5/10): `/ollama/ollama-python`
- SQLite (Official Docs): `/sqlite/sqlite`

**Implementation Files**:
- MCP Server: `mcp-devstream-server/src/tools/hybrid-search.ts`
- Python Hooks: `.claude/hooks/devstream/memory/post_tool_use.py`
- Backfill Script: `scripts/backfill_embeddings_production.py`
- Database Schema: `mcp-devstream-server/src/database.ts`

---

**Document Status**: Production Ready ✅
**Last Updated**: 2025-10-10
**Maintained By**: DevStream Team
