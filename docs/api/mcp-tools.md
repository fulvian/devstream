# DevStream MCP Tools API Reference

**Version**: 2.1.0 | **Last Updated**: 2025-10-01 | **Status**: Production

Complete reference for DevStream Model Context Protocol (MCP) tools for task management, memory storage, and plan tracking.

---

## Table of Contents

- [Overview](#overview)
- [Connection Information](#connection-information)
- [Task Management Tools](#task-management-tools)
  - [devstream_list_tasks](#devstream_list_tasks)
  - [devstream_create_task](#devstream_create_task)
  - [devstream_update_task](#devstream_update_task)
- [Memory Management Tools](#memory-management-tools)
  - [devstream_store_memory](#devstream_store_memory)
  - [devstream_search_memory](#devstream_search_memory)
- [Plan Management Tools](#plan-management-tools)
  - [devstream_list_plans](#devstream_list_plans)
- [Error Handling](#error-handling)
- [Performance Considerations](#performance-considerations)
- [Version Compatibility](#version-compatibility)

---

## Overview

DevStream MCP tools provide natural language integration with Claude Code for task lifecycle management, semantic memory storage, and intervention planning. All tools communicate via the Model Context Protocol (MCP) over stdio transport.

**Key Features**:
- **Automatic Context Injection**: Tools integrate with PreToolUse/PostToolUse hooks
- **Semantic Memory**: Vector embeddings (768D) via Ollama for semantic search
- **Hybrid Search**: Combines vector similarity + FTS5 keyword search (RRF algorithm)
- **Intelligent Auto-Creation**: Automatically creates missing projects/phases when needed

**Architecture**:
```
Claude Code → MCP Protocol → DevStream MCP Server → SQLite DevStream DB
                                                    ↓
                                            Ollama (Embeddings)
```

---

## Connection Information

### MCP Server Configuration

**Location**: `.claude/mcp_servers.json`

```json
{
  "devstream": {
    "command": "node",
    "args": [
      "/path/to/mcp-devstream-server/dist/index.js",
      "/path/to/data/devstream.db"
    ],
    "env": {
      "DEVSTREAM_DB_PATH": "/path/to/data/devstream.db"
    }
  }
}
```

### Server Metadata

| Property | Value |
|----------|-------|
| **Name** | `devstream-mcp-server` |
| **Version** | `1.0.0` |
| **Transport** | stdio |
| **Capabilities** | `tools` |
| **Database** | SQLite 3.46+ with sqlite-vec extension |
| **Embeddings** | Ollama (nomic-embed-text, 768D) |

### Startup Sequence

```bash
# MCP Server startup
1. Initialize database connection (better-sqlite3)
2. Load sqlite-vec extension (vector search)
3. Verify vector search availability (diagnostics)
4. Initialize Ollama client for embeddings
5. Start MCP server on stdio
6. Ready to receive tool calls
```

**Startup Logs**:
```
✅ Vector search ready: vec0 v0.1.6
🧠 Initializing Ollama client for automatic embedding generation...
✅ Ollama client initialized successfully
🚀 DevStream MCP Server started - HYBRID SEARCH v2.0 (better-sqlite3 + sqlite-vec)
```

---

## Task Management Tools

### devstream_list_tasks

List all DevStream tasks with optional filtering by status, priority, or project.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status` | enum | No | - | Filter by task status |
| `project` | string | No | - | Filter by project name (partial match) |
| `priority` | number | No | - | Filter by minimum priority level (1-10) |

**Status Values**: `pending`, `active`, `completed`, `failed`, `skipped`

**Priority Range**: 1-10 (higher = more important)

#### Return Type

```typescript
{
  content: [
    {
      type: "text",
      text: string  // Formatted task list with emojis
    }
  ]
}
```

#### Example Request

```typescript
// List all active tasks with priority >= 7
{
  name: "devstream_list_tasks",
  arguments: {
    status: "active",
    priority: 7
  }
}
```

#### Example Response

```markdown
📋 **DevStream Tasks**

## 🎯 RUSTY Trading Platform Development

### 📁 Core Engine & Infrastructure

🔄 **[ACTIVE]** Implement Python asyncio event loop
   📝 Design and implement the core async event loop using Python asyncio
   🏷️ Type: coding | Priority: 9/10 (HIGH)
   🆔 ID: `a1b2c3d4e5f6`

⏳ **[PENDING]** Add comprehensive error handling
   📝 Implement structured exception handling for all async operations
   🏷️ Type: coding | Priority: 7/10 (MEDIUM)
   🆔 ID: `f6e5d4c3b2a1`

📊 **Summary**: 2 tasks found • Status: active • Priority ≥ 7
```

#### Error Codes

| Code | Message | Resolution |
|------|---------|------------|
| `VALIDATION_ERROR` | Invalid status enum | Use valid status: `pending`, `active`, `completed`, `failed`, `skipped` |
| `VALIDATION_ERROR` | Priority out of range | Use priority between 1-10 |
| `DATABASE_ERROR` | Query failed | Check database connectivity and schema |

#### Performance Notes

- **Query Time**: < 50ms for 1000 tasks (indexed by status, priority)
- **Indexes Used**: `idx_micro_tasks_status`, `idx_micro_tasks_priority`
- **Returns**: All matching tasks in single response (no pagination)

---

### devstream_create_task

Create a new DevStream task in a specific phase. Automatically creates missing projects/phases if needed (Context7-validated intelligent auto-creation pattern).

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `title` | string | Yes | - | Task title (min 1 char) |
| `description` | string | Yes | - | Detailed task description |
| `task_type` | enum | Yes | - | Type of task |
| `priority` | number | Yes | - | Priority level (1-10) |
| `phase_name` | string | Yes | - | Phase name (e.g., "Core Engine & Infrastructure") |
| `project` | string | No | `"RUSTY Trading Platform Development"` | Project name |

**Task Types**: `analysis`, `coding`, `documentation`, `testing`, `review`, `research`

#### Return Type

```typescript
{
  content: [
    {
      type: "text",
      text: string  // Success message with task details
    }
  ]
}
```

#### Auto-Creation Behavior

**Intelligent Infrastructure Setup** (Context7 Pattern):

1. **Project Missing**: Automatically creates project with defaults
   - Status: `active`
   - Priority: `7`
   - Estimated Hours: `100`
   - Objectives: Auto-generated based on project name

2. **Phase Missing**: Automatically creates phase with defaults
   - Status: `active`
   - Sequence Order: Auto-incremented
   - Estimated Minutes: `1200` (20 hours)

3. **Task Creation**: Creates task with provided parameters
   - Status: `pending` (initial state)
   - Max Duration: `10` minutes (micro-task constraint)
   - Max Context Tokens: `256000`
   - Assigned Agent: `developer` (default)

#### Example Request

```typescript
{
  name: "devstream_create_task",
  arguments: {
    title: "Implement JWT authentication middleware",
    description: "Create FastAPI middleware for JWT token validation with RS256 algorithm and automatic token refresh",
    task_type: "coding",
    priority: 8,
    phase_name: "API Security Layer",
    project: "Trading Platform API"
  }
}
```

#### Example Response (with Auto-Creation)

```markdown
✅ **Task Created Successfully**

📝 **Title**: Implement JWT authentication middleware
📁 **Phase**: API Security Layer
🎯 **Project**: Trading Platform API Development
🏷️ **Type**: coding
⭐ **Priority**: 8/10
🆔 **Task ID**: `3a7f9c2e8d1b`

🤖 **Auto-Creation Protocol Activated**
   📋 Created project: "Trading Platform API Development"
   📁 Created phase: "API Security Layer"

The task has been added to the "API Security Layer" phase and is ready for execution.
```

#### Error Codes

| Code | Message | Resolution |
|------|---------|------------|
| `VALIDATION_ERROR` | Title too short | Provide title with at least 1 character |
| `VALIDATION_ERROR` | Invalid task_type | Use valid type: `analysis`, `coding`, `documentation`, `testing`, `review`, `research` |
| `VALIDATION_ERROR` | Priority out of range | Use priority between 1-10 |
| `AUTO_CREATE_FAILED` | Failed to auto-create phase | Check database write permissions |

#### Performance Notes

- **Creation Time**: < 100ms (including auto-creation)
- **Transactions**: Atomic (all-or-nothing for project/phase/task)
- **Side Effects**: May create 1 project + 1 phase + 1 task in single call

---

### devstream_update_task

Update task status with automatic timestamp management and optional notes.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string | Yes | Task ID to update (hex string) |
| `status` | enum | Yes | New task status |
| `notes` | string | No | Optional notes about the update |

**Status Values**: `pending`, `active`, `completed`, `failed`, `skipped`

#### Automatic Timestamp Behavior

| Status Change | Automatic Timestamp |
|---------------|---------------------|
| `pending` → `active` | Sets `started_at` (first time only) |
| Any → `completed` | Sets `completed_at` (first time only) |
| Any → `failed` | Sets `completed_at` (first time only) |
| Any → `skipped` | Sets `completed_at` (first time only) |

#### Return Type

```typescript
{
  content: [
    {
      type: "text",
      text: string  // Success message with status change
    }
  ]
}
```

#### Example Request

```typescript
{
  name: "devstream_update_task",
  arguments: {
    task_id: "3a7f9c2e8d1b",
    status: "completed",
    notes: "JWT middleware implemented with RS256 signature validation and automatic token refresh. Test coverage: 95%."
  }
}
```

#### Example Response

```markdown
✅ **Task Updated Successfully**

📝 **Task**: Implement JWT authentication middleware
📊 **Status**: active → **COMPLETED**
🆔 **Task ID**: `3a7f9c2e8d1b`

📝 **Notes**: JWT middleware implemented with RS256 signature validation and automatic token refresh. Test coverage: 95%.

The task status has been updated and logged in the DevStream database.
```

#### Memory Storage

**Automatic Behavior**: If `notes` parameter provided, update is stored in `semantic_memory`:

```sql
INSERT INTO semantic_memory (
  id, task_id, content, content_type, keywords, relevance_score
) VALUES (
  <generated_id>,
  <task_id>,
  'Task status update: <status>. Notes: <notes>',
  'decision',
  ['task', 'update', <status>],
  0.7  -- Medium importance
)
```

#### Error Codes

| Code | Message | Resolution |
|------|---------|------------|
| `NOT_FOUND` | Task not found | Verify task ID exists via `devstream_list_tasks` |
| `VALIDATION_ERROR` | Invalid status enum | Use valid status: `pending`, `active`, `completed`, `failed`, `skipped` |
| `DATABASE_ERROR` | Update failed | Check database connectivity |

#### Performance Notes

- **Update Time**: < 20ms
- **Memory Storage**: + 50ms if `notes` provided
- **Indexes Used**: Primary key (instant lookup)

---

## Memory Management Tools

### devstream_store_memory

Store information in DevStream semantic memory with automatic embedding generation for vector search.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `content` | string | Yes | - | Content to store (any length) |
| `content_type` | enum | Yes | - | Type of content |
| `keywords` | string[] | No | `[]` | Keywords for easier retrieval |

**Content Types**: `code`, `documentation`, `context`, `output`, `error`, `decision`, `learning`

**Content Format Detection** (automatic):
- JSON: Starts with `{` or `[`
- Code: Contains backticks, `def`, `function`
- Markdown: Contains `#`, `##`, `**`
- Default: Based on `content_type`

#### Return Type

```typescript
{
  content: [
    {
      type: "text",
      text: string  // Success message with embedding info
    }
  ],
  structuredContent: {  // MCP 2025-06-18 Structured Output
    success: boolean,
    memory_id: string,
    content_type: string,
    importance_score: number,
    embedding_generated: boolean,
    embedding_model: string | null,
    embedding_dimensions: number | null,
    keywords: string[],
    content_length: number,
    source: "mcp_user_input",
    timestamp: string  // ISO 8601
  }
}
```

#### Automatic Embedding Generation

**Process** (Context7 Pattern):

1. **Calculate Importance Score** (0.1 - 1.0):
   - Content type weight: `error` (0.9), `decision` (0.8), `learning` (0.8), `code` (0.7), etc.
   - Length factor: `min(length/1000, 1) * 0.2`
   - Keyword density: `min(keyword_count/10, 1) * 0.2`

2. **Generate Embedding**:
   - Model: `nomic-embed-text` (768 dimensions)
   - Method: Ollama API (`/api/embeddings`)
   - Timeout: 30 seconds
   - Graceful degradation: Stores text-only if embedding fails

3. **Store in Database**:
   - `semantic_memory` table: Full content + metadata
   - `vec_semantic_memory` table: Vector for similarity search (auto-synced via trigger)
   - `fts_semantic_memory` table: Full-text index (auto-synced via trigger)

#### Example Request

```typescript
{
  name: "devstream_store_memory",
  arguments: {
    content: "Decision: Use FastAPI for API layer due to async/await support and automatic OpenAPI generation. Benchmark results show 2.5x better performance than Flask for async workloads. Tested with 95%+ test coverage requirement.",
    content_type: "decision",
    keywords: ["fastapi", "async", "api", "architecture", "performance"]
  }
}
```

#### Example Response

```markdown
✅ **Memory Stored Successfully**

📝 **Content Type**: decision
📊 **Importance Score**: 0.85
🏷️ **Keywords**: fastapi, async, api, architecture, performance
📍 **Source**: mcp_user_input
🆔 **Memory ID**: `7c3f9a2d8b1e`
🧠 **Embedding**: ✅ Generated (768D, nomic-embed-text)

💾 **Content Preview**: Decision: Use FastAPI for API layer due to async/await support and automatic OpenAPI genera...

The information has been stored in DevStream semantic memory with vector search capability and can be retrieved using search queries.
```

#### Error Codes

| Code | Message | Resolution |
|------|---------|------------|
| `VALIDATION_ERROR` | Content too short | Provide at least 1 character |
| `VALIDATION_ERROR` | Invalid content_type | Use valid type: `code`, `documentation`, `context`, `output`, `error`, `decision`, `learning` |
| `EMBEDDING_FAILED` | Embedding generation failed | Check Ollama service status (non-blocking - content still stored) |
| `DATABASE_ERROR` | Storage failed | Check database write permissions |

#### Performance Notes

- **Storage Time**: 50-200ms (depends on Ollama)
- **Embedding Generation**: 50-150ms (768D vector)
- **Graceful Degradation**: Stores text-only if Ollama unavailable
- **Indexes Used**: Automatically synced to vec0 and FTS5 virtual tables

---

### devstream_search_memory

Search DevStream semantic memory using hybrid search (RRF algorithm) combining vector similarity and FTS5 keyword search.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query string |
| `content_type` | enum | No | - | Filter by content type |
| `limit` | number | No | `10` | Maximum results to return (1-50) |

**Content Types**: `code`, `documentation`, `context`, `output`, `error`, `decision`, `learning`

#### Hybrid Search Algorithm (RRF)

**Reciprocal Rank Fusion** (Context7 Pattern from sqlite-vec examples):

```
combined_rank = (1 / (k + fts_rank)) * weight_fts
              + (1 / (k + vec_rank)) * weight_vec

where:
  k = 60 (RRF constant)
  weight_fts = 1.0 (keyword search weight)
  weight_vec = 1.0 (vector search weight)
```

**Search Methods**:
1. **Vector Search** (if Ollama available): Semantic similarity using cosine distance
2. **FTS5 Keyword Search**: Full-text search with BM25 ranking
3. **RRF Fusion**: Combines both methods for optimal relevance

**Fallback**: If vector search unavailable, uses FTS5-only keyword search.

#### Return Type

```typescript
{
  content: [
    {
      type: "text",
      text: string  // Formatted search results with RRF scores
    }
  ]
}
```

#### Example Request

```typescript
{
  name: "devstream_search_memory",
  arguments: {
    query: "FastAPI async authentication best practices",
    content_type: "decision",
    limit: 5
  }
}
```

#### Example Response

```markdown
🔍 **DevStream Hybrid Search Results**

Query: "FastAPI async authentication best practices"
Method: Hybrid (Vector + Keyword)
Found: 3 results

1. 🎯 **DECISION** Memory
   📊 Relevance: HIGH (RRF Score: 8.4)
   🔬 Vector Rank: #1 • Keyword Rank: #2
   💾 Content: Decision: Use FastAPI for API layer due to async/await support and automatic OpenAPI generation. Benchmark results show 2.5x better performance than Flask for async workloads...
   🆔 ID: `7c3f9a2d8b1e`
   📅 Created: 2025-09-30

2. 💻 **CODE** Memory
   📊 Relevance: MEDIUM (RRF Score: 3.2)
   🔬 Vector Rank: #3 • Keyword Rank: #1
   💾 Content: # FastAPI JWT Middleware\n\nImplementation of JWT authentication middleware with RS256 signature validation and automatic token refresh...
   🆔 ID: `9e2a1f8c3b7d`
   📅 Created: 2025-09-29

3. 📚 **DOCUMENTATION** Memory
   📊 Relevance: LOW (RRF Score: 1.7)
   🔬 Vector Rank: #5 (distance: 0.2834)
   💾 Content: FastAPI Security Best Practices:\n1. Always use HTTPS in production\n2. Implement rate limiting for authentication endpoints...
   🆔 ID: `4d8b3c1e7f9a`
   📅 Created: 2025-09-28

💡 **Tip**: Hybrid search combines semantic similarity and keyword matching for better results.
```

#### Automatic Access Tracking

**Side Effect**: Updates `access_count` and `last_accessed_at` for all retrieved memories:

```sql
UPDATE semantic_memory
SET access_count = access_count + 1,
    last_accessed_at = datetime('now')
WHERE id IN (<memory_ids>)
```

#### Error Codes

| Code | Message | Resolution |
|------|---------|------------|
| `VALIDATION_ERROR` | Query too short | Provide at least 1 character |
| `VALIDATION_ERROR` | Invalid content_type | Use valid type: `code`, `documentation`, `context`, `output`, `error`, `decision`, `learning` |
| `VALIDATION_ERROR` | Limit out of range | Use limit between 1-50 |
| `DATABASE_ERROR` | Search failed | Check database connectivity |

#### Performance Notes

- **Search Time**: < 100ms for 10K memories (p95)
- **Hybrid Search**: Vector (35ms) + FTS5 (20ms) + RRF (5ms)
- **Fallback Mode**: FTS5-only (< 30ms if vector search unavailable)
- **Indexes Used**: `vec_semantic_memory` (vector), `fts_semantic_memory` (FTS5)
- **Relevance Rate**: 95%+ (production validated)

---

## Plan Management Tools

### devstream_list_plans

List all intervention plans with their phases and progress statistics.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status` | enum | No | - | Filter by plan status |

**Status Values**: `draft`, `active`, `completed`, `paused`

#### Return Type

```typescript
{
  content: [
    {
      type: "text",
      text: string  // Formatted plan list with progress bars
    }
  ]
}
```

#### Aggregated Metrics

**Automatic Calculation** (per plan):
- **Phase Progress**: `completed_phases / total_phases * 100`
- **Task Progress**: `completed_tasks / total_tasks * 100`
- **Time Progress**: `actual_hours / estimated_hours`
- **Priority Classification**: HIGH (≥8), MEDIUM (5-7), LOW (1-4)

#### Example Request

```typescript
{
  name: "devstream_list_plans",
  arguments: {
    status: "active"
  }
}
```

#### Example Response

```markdown
📋 **DevStream Intervention Plans**

🔄 **RUSTY Trading Platform Development**
📊 Status: **ACTIVE** | Priority: 9/10 (HIGH)
📈 Progress: 60% phases (3/5) • 45% tasks (18/40)
⏱️ Time: 67.5/100 hours
📝 Complete development of RUSTY Trading Platform with real-time market data, order execution, and portfolio management
🎯 **Objectives**:
   1. Complete development of RUSTY Trading Platform Development
   2. Implement core functionality
   3. Ensure quality and testing
🆔 ID: `1a2b3c4d5e6f`

   📁 **Phases**:
   ✅ Core Engine & Infrastructure (completed)
   🔄 Market Data Integration (active)
   ⏳ Order Execution System (pending)
   ⏳ Portfolio Management (pending)
   ⏳ Testing & Deployment (pending)

🔄 **Trading Platform API**
📊 Status: **ACTIVE** | Priority: 7/10 (MEDIUM)
📈 Progress: 33% phases (1/3) • 25% tasks (5/20)
⏱️ Time: 15.0/50 hours
📝 Auto-created project for Trading Platform API
🎯 **Objectives**:
   1. Complete development of Trading Platform API
   2. Implement core functionality
   3. Ensure quality and testing
🆔 ID: `7f8a9b0c1d2e`

   📁 **Phases**:
   ✅ API Security Layer (completed)
   🔄 User Management (active)
   ⏳ Data Analytics (pending)

📊 **Summary**: 2 plans found • Status: active
```

#### Error Codes

| Code | Message | Resolution |
|------|---------|------------|
| `VALIDATION_ERROR` | Invalid status enum | Use valid status: `draft`, `active`, `completed`, `paused` |
| `DATABASE_ERROR` | Query failed | Check database connectivity |

#### Performance Notes

- **Query Time**: < 100ms for 100 plans (with phases/tasks aggregation)
- **SQL Joins**: 3-way join (`intervention_plans` → `phases` → `micro_tasks`)
- **Indexes Used**: `idx_intervention_plans_status`, `idx_phases_plan_id`, `idx_micro_tasks_phase_id`
- **Returns**: All matching plans in single response (no pagination)

---

## Error Handling

### Error Response Format

All tools return errors in consistent format:

```typescript
{
  content: [
    {
      type: "text",
      text: "❌ Error <operation>: <error_message>"
    }
  ]
}
```

### Error Categories

| Category | HTTP Equivalent | Description |
|----------|----------------|-------------|
| `VALIDATION_ERROR` | 400 Bad Request | Invalid input parameters |
| `NOT_FOUND` | 404 Not Found | Resource doesn't exist |
| `DATABASE_ERROR` | 500 Internal Server Error | Database operation failed |
| `EMBEDDING_FAILED` | 503 Service Unavailable | Ollama embedding generation failed (non-blocking) |
| `AUTO_CREATE_FAILED` | 500 Internal Server Error | Automatic project/phase creation failed |

### Graceful Degradation

**Non-Blocking Failures**:
- **Embedding Generation**: If Ollama unavailable, stores text-only (FTS5 search still works)
- **Vector Search**: If sqlite-vec unavailable, falls back to FTS5-only keyword search
- **Memory Storage**: Always stores content even if embedding fails

**Example**: Embedding failure does not prevent memory storage:
```markdown
✅ **Memory Stored Successfully**
...
🧠 **Embedding**: ❌ Failed

The information has been stored in DevStream semantic memory (text-only, vector search unavailable) and can be retrieved using search queries.
```

---

## Performance Considerations

### Optimization Strategies

**Indexing**:
- All foreign keys indexed (`idx_micro_tasks_phase_id`, etc.)
- Status fields indexed for filtering (`idx_micro_tasks_status`)
- Priority indexed descending for sorting (`idx_micro_tasks_priority`)
- Created timestamps indexed descending (`idx_semantic_memory_created_at`)

**Query Optimization**:
- Use specific filters (`status`, `content_type`) to leverage indexes
- Set reasonable `limit` values (default 10, max 50)
- Avoid full table scans on large memory tables

**Embedding Generation**:
- Batch embedding requests if creating multiple memories
- Consider async embedding generation for large content (>5000 chars)
- Monitor Ollama service health for faster response times

### Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| **List Tasks** | < 50ms | 1000 tasks, indexed query |
| **Create Task** | < 100ms | Including auto-creation |
| **Update Task** | < 20ms | Primary key update |
| **Store Memory** | < 200ms | Including embedding (768D) |
| **Search Memory** | < 100ms | 10K memories, hybrid search |
| **List Plans** | < 100ms | 100 plans with aggregation |

### Monitoring

**Metrics Tracking** (Context7 Pattern):
```typescript
// Automatic metrics collection
MetricsCollector.trackEmbeddingGeneration(model, operation);
MetricsCollector.trackDatabaseOperation(op_type, operation);
memoryStorageCounter.inc({ content_type, has_embedding });
```

**Available Metrics**:
- Embedding generation time (by model)
- Database operation time (by operation type)
- Memory storage count (by content_type, embedding status)
- Search latency (hybrid vs fallback)

---

## Version Compatibility

### Schema Version

**Current**: `2.1.0` (tracked in `schema_version` table)

**Breaking Changes**:
- `v2.0.0`: Introduced sqlite-vec extension (vector search)
- `v2.1.0`: Added automatic triggers for vec0/FTS5 sync

**Upgrade Path**: Schema migrations handled automatically by MCP server on startup.

### MCP Protocol Version

**Supported**: MCP 2025-06-18 (structured output)

**Backwards Compatibility**:
- Text-based output (all clients)
- Structured output (MCP 2025-06-18+ clients)

**Example Dual Format**:
```typescript
{
  content: [{ type: "text", text: "..." }],  // Legacy
  structuredContent: { success: true, ... }  // Modern
}
```

### Ollama Model Compatibility

**Supported Models**:
- `nomic-embed-text` (768D, default)
- `mxbai-embed-large` (1024D, experimental)
- `all-minilm` (384D, lightweight)

**Model Selection**: Environment variable `OLLAMA_EMBEDDING_MODEL`

---

## Cross-References

**Related Documentation**:
- [Database Schema Reference](./database-schema.md) - Complete table definitions
- [Hooks API Reference](./hooks-api.md) - PreToolUse/PostToolUse integration
- [DevStream Memory System](../guides/devstream-memory-guide.md) - Usage patterns

**Integration Examples**:
- [Task Lifecycle Management](../guides/task-lifecycle-guide.md)
- [Semantic Memory Best Practices](../guides/semantic-memory-best-practices.md)
- [Hybrid Search Deep Dive](../architecture/hybrid-search-architecture.md)

---

**Document Version**: 2.1.0
**Last Updated**: 2025-10-01
**Status**: Production Ready
**Validation**: Context7-validated patterns, 95%+ relevance rate
