# Auto-Save Service Architecture

**Version**: 1.0.0 | **Date**: 2025-10-01 | **Status**: Production Ready

---

## Overview

The Auto-Save Service is a background task system that periodically creates checkpoints for active DevStream tasks. This enables progress tracking, recovery, and analytics without manual intervention.

## Architecture

### System Design

```
MCP Server Startup
    ↓
Initialize Auto-Save Service
    ↓
Start Background Task (setInterval)
    ↓
┌──────────────────────────────────────────────────────┐
│ Checkpoint Cycle (Every 5 Minutes)                   │
├──────────────────────────────────────────────────────┤
│ 1. Query Active Tasks (status='active')              │
│ 2. For Each Task:                                    │
│    - Calculate Elapsed Time                          │
│    - Build Checkpoint Data Structure                 │
│    - Store in semantic_memory                        │
│    - Log Success/Failure                             │
│ 3. Report Cycle Results                              │
└──────────────────────────────────────────────────────┘
    ↓
Continue Loop Until Shutdown
    ↓
Graceful Shutdown (SIGINT/SIGTERM)
    ↓
Stop Auto-Save Service
    ↓
Close Database
```

### Component Integration

```
┌─────────────────────────────────────────────────────────────┐
│ DevStream MCP Server                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────┐         ┌──────────────────────┐    │
│  │ AutoSaveService   │ ───────>│ DevStreamDatabase    │    │
│  │                   │         │                      │    │
│  │ - start()         │         │ - query()            │    │
│  │ - stop()          │         │ - execute()          │    │
│  │ - checkpoint()    │         │                      │    │
│  └───────────────────┘         └──────────────────────┘    │
│         ↓                               ↓                   │
│  ┌───────────────────┐         ┌──────────────────────┐    │
│  │ setInterval       │         │ semantic_memory      │    │
│  │ (300s cycle)      │         │ (checkpoints)        │    │
│  └───────────────────┘         └──────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Technical Specifications

### Configuration

```typescript
interface AutoSaveConfig {
  intervalMs: number;           // Default: 300000 (5 minutes)
  enabled: boolean;             // Default: true
  checkpointContentType: string; // Default: 'context'
}
```

**Environment Variables** (future):
```bash
DEVSTREAM_AUTOSAVE_ENABLED=true
DEVSTREAM_AUTOSAVE_INTERVAL_MS=300000
```

### Checkpoint Data Structure

```typescript
interface TaskCheckpoint {
  task_id: string;              // Task identifier
  task_title: string;           // Task title
  phase_name: string;           // Phase name
  status: string;               // Task status (active)
  priority: number;             // Task priority (1-10)
  started_at: string | null;    // Task start timestamp
  elapsed_minutes: number | null; // Elapsed time since start
  checkpoint_timestamp: string; // Checkpoint creation time
  checkpoint_reason: 'auto_save' | 'manual' | 'status_change';
}
```

### Database Schema

Checkpoints are stored in `semantic_memory` table:

| Column | Type | Description |
|--------|------|-------------|
| `id` | VARCHAR(32) | Checkpoint ID (generated) |
| `task_id` | VARCHAR(32) | Foreign key to micro_tasks |
| `content` | TEXT | Human-readable checkpoint summary |
| `content_type` | VARCHAR(20) | 'context' (checkpoint category) |
| `content_format` | VARCHAR(20) | 'json' (structured data) |
| `keywords` | JSON | ['checkpoint', 'auto_save', 'progress'] |
| `relevance_score` | FLOAT | 0.8 (high relevance) |
| `context_snapshot` | JSON | Full TaskCheckpoint structure |
| `created_at` | TIMESTAMP | Checkpoint creation timestamp |

## Implementation Details

### Startup Sequence

1. **MCP Server Initialization**
   - Create `DevStreamDatabase` instance
   - Create `AutoSaveService` instance with config
   - Register service in server class

2. **Database Connection**
   - Initialize database connection
   - Verify schema (micro_tasks, semantic_memory tables)

3. **Service Start**
   - Execute initial checkpoint cycle
   - Schedule periodic cycles (setInterval)
   - Log service status

### Checkpoint Cycle

```typescript
async executeCheckpointCycle(): Promise<number> {
  // 1. Query active tasks
  const activeTasks = await this.getActiveTasks();

  // 2. Early exit if no tasks
  if (activeTasks.length === 0) {
    return 0;
  }

  // 3. Create checkpoint for each task
  for (const task of activeTasks) {
    try {
      await this.createTaskCheckpoint(task);
    } catch (error) {
      // Log error, continue processing
      console.error('Checkpoint failed:', error);
    }
  }

  // 4. Return success count
  return successCount;
}
```

### Graceful Shutdown

```typescript
async stop(): Promise<void> {
  // 1. Set shutdown flag
  this.isShuttingDown = true;

  // 2. Clear interval (prevent new cycles)
  clearInterval(this.intervalId);

  // 3. Wait for in-progress cycle (max 10s)
  while (this.isRunning && timeout < 10000) {
    await sleep(100);
  }

  // 4. Mark service as stopped
  this.isRunning = false;
}
```

## Error Handling

### Strategy

**Principle**: Individual failures should not crash the service.

**Implementation**:
- **Checkpoint Failure**: Log error, continue processing other tasks
- **Cycle Failure**: Log error, continue service execution (next cycle)
- **Database Error**: Log error, continue service (fallback to next cycle)

### Error Isolation

```typescript
// Checkpoint-level isolation
for (const task of activeTasks) {
  try {
    await this.createTaskCheckpoint(task);
  } catch (error) {
    // Log but continue
    console.error(`Task ${task.id} checkpoint failed`);
  }
}

// Cycle-level isolation
setInterval(async () => {
  try {
    await this.executeCheckpointCycle();
  } catch (error) {
    // Log but continue service
    console.error('Checkpoint cycle failed');
  }
}, intervalMs);
```

## Performance Considerations

### Resource Usage

**Database Queries**:
- Active tasks query: 1 per cycle (JOIN query)
- Checkpoint inserts: N per cycle (N = active tasks)
- Total: 1 + N queries every 5 minutes

**Memory**:
- Service overhead: ~1MB
- Checkpoint data: ~1KB per task
- Total: ~1MB + (N * 1KB)

**CPU**:
- Checkpoint cycle: ~100ms per 10 tasks
- Interval overhead: Negligible (setInterval)

### Optimization Strategies

1. **Batch Processing**: Process all tasks in single cycle
2. **Index Optimization**: Use `idx_micro_tasks_status` index
3. **Transaction Batching**: Future optimization for high task volumes
4. **Configurable Interval**: Adjust frequency based on load

## Testing

### Test Coverage

**Unit Tests** (`auto-save.test.ts`):
- ✅ Service lifecycle (start/stop)
- ✅ Checkpoint creation
- ✅ Error handling
- ✅ Configuration management
- ✅ Graceful shutdown

**Integration Tests**:
- ✅ Database interaction
- ✅ Multi-task checkpointing
- ✅ Concurrent task handling

**Test Execution**:
```bash
npm test -- auto-save.test.ts
```

### Test Scenarios

1. **Normal Operation**: Service creates checkpoints every 5 minutes
2. **No Active Tasks**: Service continues running, skips checkpoint
3. **Checkpoint Failure**: Service logs error, continues processing
4. **Graceful Shutdown**: Service completes in-progress cycle before stopping
5. **Configuration Update**: Service prevents updates while running

## Monitoring

### Logging

**Service Events**:
- `🔄 Auto-save service started`
- `✅ Checkpoint created for task "{title}"`
- `⚠️ Checkpoint failed for task {id}`
- `✅ Checkpoint cycle completed (N success, M failures)`
- `🛑 Stopping auto-save service`

**Log Levels**:
- INFO: Service lifecycle, checkpoint cycles
- WARNING: Checkpoint failures (individual tasks)
- ERROR: Service failures (entire cycle)

### Metrics

**Future Implementation**:
- Total checkpoints created
- Checkpoint success rate
- Average cycle duration
- Active tasks per cycle

## Usage Examples

### Default Configuration

```typescript
// Initialize service with defaults
const autoSaveService = new AutoSaveService(database);
await autoSaveService.start();

// Service runs every 5 minutes automatically
```

### Custom Configuration

```typescript
// Configure interval and enable/disable
const autoSaveService = new AutoSaveService(database, {
  intervalMs: 600000,  // 10 minutes
  enabled: true
});

await autoSaveService.start();
```

### Manual Checkpoint Trigger

```typescript
// Trigger immediate checkpoint cycle (future feature)
const checkpointCount = await autoSaveService.executeCheckpointCycle();
console.log(`Created ${checkpointCount} checkpoints`);
```

## Future Enhancements

### Planned Features

1. **Manual Checkpoint API**: Trigger on-demand checkpoints
2. **Checkpoint History**: Query checkpoint history for analytics
3. **Progress Reports**: Generate progress summaries from checkpoints
4. **Recovery System**: Restore task state from checkpoints
5. **Metrics Dashboard**: Real-time checkpoint statistics
6. **Conditional Checkpoints**: Only checkpoint tasks > X minutes

### Configuration Improvements

```typescript
interface AutoSaveConfigV2 {
  intervalMs: number;
  enabled: boolean;
  minTaskDurationMinutes: number; // Only checkpoint tasks running > N minutes
  maxCheckpointsPerTask: number;  // Limit checkpoint history
  compressionEnabled: boolean;    // Compress checkpoint data
}
```

## Security Considerations

### Data Protection

- **No Sensitive Data**: Checkpoints store task metadata only (no code/secrets)
- **Access Control**: Checkpoints inherit task-level access control
- **Audit Trail**: All checkpoints logged with timestamp

### Resource Limits

- **Rate Limiting**: 5-minute minimum interval (prevents abuse)
- **Memory Bounds**: Max 1000 checkpoints per cycle
- **Database Protection**: Transaction-based updates prevent corruption

## Integration Points

### MCP Server

```typescript
class DevStreamMcpServer {
  private autoSaveService: AutoSaveService;

  async start() {
    // Initialize and start auto-save
    this.autoSaveService = new AutoSaveService(this.database);
    await this.autoSaveService.start();
  }

  async close() {
    // Graceful shutdown
    await this.autoSaveService.stop();
    await this.database.close();
  }
}
```

### Task Tools

```typescript
// Task status change triggers checkpoint (future)
async updateTask(taskId: string, status: string) {
  await database.execute('UPDATE micro_tasks SET status = ?', [status]);

  // Trigger immediate checkpoint on status change
  if (status === 'active') {
    await autoSaveService.createCheckpoint(taskId);
  }
}
```

## References

### Context7 Research

- **Node.js Background Tasks**: https://nodejs.org/api/timers.html
- **Graceful Shutdown Patterns**: https://github.com/nodejs/node/blob/main/doc/api/process.md
- **SQLite Transaction Best Practices**: https://www.sqlite.org/lang_transaction.html

### DevStream Documentation

- [Task Management System](./task-management.md)
- [Semantic Memory System](./semantic-memory.md)
- [Database Schema](./database-schema.md)

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-01
**Author**: DevStream Team
**Status**: ✅ Production Ready
