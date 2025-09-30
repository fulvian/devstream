# DevStream Operational Runbook

**Incident Response & Troubleshooting Guide**
**Version**: 1.0
**Date**: 2025-09-30

---

## 🚨 Quick Reference

### Service Status

```bash
# Check if MCP server is running
ps aux | grep "node.*devstream"

# Check metrics endpoint
curl http://localhost:9090/health

# Check Ollama service
curl http://localhost:11434/api/tags
```

### Emergency Contacts

- **Primary**: DevOps Team
- **Backup**: Engineering Lead
- **Documentation**: See MONITORING.md, DEPLOYMENT.md

---

## 📊 Common Issues & Solutions

### Issue 1: High Query Latency

**Symptoms:**
- P95 query latency >200ms
- Slow search responses
- User complaints about performance

**Diagnosis:**
```bash
# Check current query latency
curl http://localhost:9090/metrics | grep "devstream_query_duration_seconds"

# Check active queries
curl http://localhost:9090/metrics | grep "devstream_active_queries"

# Check database size
ls -lh /var/lib/devstream/devstream.db
```

**Solutions:**

1. **Check Ollama Performance**
   ```bash
   # Test embedding generation time
   time curl -X POST http://localhost:11434/api/embeddings \
     -d '{"model": "embeddinggemma:300m", "prompt": "test query"}'
   ```
   - **If slow**: Restart Ollama service
   - **If very slow**: Check CPU/memory resources

2. **Optimize Database**
   ```bash
   sqlite3 /var/lib/devstream/devstream.db "PRAGMA optimize;"
   sqlite3 /var/lib/devstream/devstream.db "ANALYZE;"
   ```

3. **Check Index Sizes**
   ```bash
   # Get index stats
   curl http://localhost:9090/metrics | grep "devstream.*_index_size"
   ```
   - **If very large**: Consider archiving old data

4. **Increase Resources**
   ```bash
   # Increase Node.js heap
   export NODE_OPTIONS="--max-old-space-size=8192"
   sudo systemctl restart devstream
   ```

---

### Issue 2: Zero Results Rate High

**Symptoms:**
- Many queries returning no results (>10%)
- Alert: HighZeroResultRate triggered

**Diagnosis:**
```bash
# Check zero result rate
curl http://localhost:9090/metrics | grep "devstream_zero_results_total"

# Check index sizes
curl http://localhost:9090/metrics | grep "_index_size"
```

**Solutions:**

1. **Verify Indexes Are Populated**
   ```bash
   sqlite3 /var/lib/devstream/devstream.db "SELECT COUNT(*) FROM fts_semantic_memory;"
   sqlite3 /var/lib/devstream/devstream.db "SELECT COUNT(*) FROM vec_semantic_memory;"
   ```

2. **Re-index if Necessary**
   ```bash
   # Run data migration script
   node migrate_existing_data.js
   ```

3. **Check for Data Issues**
   ```sql
   -- Check for memories without embeddings
   SELECT COUNT(*) FROM semantic_memory WHERE embedding IS NULL;

   -- Check recent memories
   SELECT content_type, COUNT(*)
   FROM semantic_memory
   WHERE created_at > datetime('now', '-1 day')
   GROUP BY content_type;
   ```

---

### Issue 3: Critical Errors

**Symptoms:**
- Critical error alert triggered
- Service degraded or failing
- Error logs showing critical failures

**Diagnosis:**
```bash
# Check error metrics
curl http://localhost:9090/errors

# Check logs
journalctl -u devstream -n 100 --no-pager

# Check error breakdown
curl http://localhost:9090/metrics | grep 'devstream_errors_total{.*severity="critical"}'
```

**Solutions:**

1. **Database Errors**
   ```bash
   # Check database file integrity
   sqlite3 /var/lib/devstream/devstream.db "PRAGMA integrity_check;"

   # Check disk space
   df -h /var/lib/devstream

   # If corrupted, restore from backup
   cp /var/backups/devstream/latest.db /var/lib/devstream/devstream.db
   sudo systemctl restart devstream
   ```

2. **Ollama Connection Errors**
   ```bash
   # Check Ollama status
   systemctl status ollama

   # Restart if needed
   sudo systemctl restart ollama

   # Verify model is available
   ollama list | grep embeddinggemma

   # Pull model if missing
   ollama pull embeddinggemma:300m
   ```

3. **Extension Loading Errors**
   ```bash
   # Verify sqlite-vec extension
   ls -l /usr/local/lib/sqlite-extensions/vec0.dylib

   # Test extension loading
   sqlite3 /var/lib/devstream/devstream.db ".load /path/to/vec0.dylib" "SELECT vec_version();"
   ```

---

### Issue 4: Service Won't Start

**Symptoms:**
- Service fails to start
- Immediate crash on startup
- Port already in use

**Diagnosis:**
```bash
# Check service status
sudo systemctl status devstream

# Check logs
journalctl -u devstream -n 50 --no-pager

# Check ports
sudo netstat -tulpn | grep 9090
```

**Solutions:**

1. **Port Conflict**
   ```bash
   # Find process using port
   sudo lsof -i :9090

   # Kill conflicting process or change port
   export METRICS_PORT=9091
   sudo systemctl restart devstream
   ```

2. **Database Lock**
   ```bash
   # Check for locks
   fuser /var/lib/devstream/devstream.db

   # Remove if stale
   rm /var/lib/devstream/devstream.db-shm
   rm /var/lib/devstream/devstream.db-wal
   ```

3. **Permission Issues**
   ```bash
   # Fix permissions
   sudo chown -R devstream:devstream /var/lib/devstream
   sudo chmod 750 /var/lib/devstream
   sudo chmod 640 /var/lib/devstream/devstream.db
   ```

4. **Missing Dependencies**
   ```bash
   # Reinstall dependencies
   cd /opt/devstream/mcp-devstream-server
   npm install
   npm run build
   ```

---

### Issue 5: Low Hybrid Coverage

**Symptoms:**
- Hybrid coverage <30%
- Most results only from one search method
- Alert: LowHybridCoverage triggered

**Diagnosis:**
```bash
# Check hybrid coverage
curl http://localhost:9090/metrics | grep "devstream_hybrid_coverage"

# Check vector search availability
curl http://localhost:9090/quality
```

**Solutions:**

1. **Verify Vector Search Working**
   ```bash
   # Test vector search directly
   sqlite3 /var/lib/devstream/devstream.db \
     "SELECT COUNT(*) FROM vec_semantic_memory;"
   ```

2. **Check Embedding Generation**
   ```bash
   # Verify Ollama responding
   curl -X POST http://localhost:11434/api/embeddings \
     -d '{"model": "embeddinggemma:300m", "prompt": "test"}'

   # Check embedding generation metrics
   curl http://localhost:9090/metrics | grep "embedding_generation_duration"
   ```

3. **Re-generate Missing Embeddings**
   ```sql
   -- Find memories without embeddings
   SELECT id, content_type, LENGTH(content) as size
   FROM semantic_memory
   WHERE embedding IS NULL
   LIMIT 10;
   ```
   - Use MCP tool to re-store these memories with embeddings

---

## 🔄 Routine Maintenance

### Daily Tasks

```bash
#!/bin/bash
# daily_maintenance.sh

# 1. Check service health
if ! systemctl is-active --quiet devstream; then
  echo "⚠️  DevStream service is not running!"
  systemctl start devstream
fi

# 2. Backup database
/opt/devstream/scripts/backup.sh

# 3. Check disk space
DISK_USAGE=$(df -h /var/lib/devstream | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
  echo "⚠️  Disk usage is ${DISK_USAGE}% - cleanup needed"
fi

# 4. Check error rate
ERROR_RATE=$(curl -s http://localhost:9090/metrics | grep 'devstream_errors_total{.*severity="critical"}' | awk '{print $2}')
if [ "${ERROR_RATE:-0}" -gt 0 ]; then
  echo "⚠️  Critical errors detected: $ERROR_RATE"
fi
```

### Weekly Tasks

```bash
#!/bin/bash
# weekly_maintenance.sh

# 1. Optimize database
sqlite3 /var/lib/devstream/devstream.db "PRAGMA optimize;"
sqlite3 /var/lib/devstream/devstream.db "ANALYZE;"

# 2. Check index health
sqlite3 /var/lib/devstream/devstream.db "PRAGMA integrity_check;"

# 3. Review metrics
echo "=== Query Performance (Last 7 Days) ==="
# Add Prometheus query here

# 4. Clean old backups
find /var/backups/devstream -name "*.db.gz" -mtime +30 -delete
```

### Monthly Tasks

- Review and update alert thresholds
- Analyze slow queries
- Plan capacity expansion if needed
- Update documentation
- Review security patches

---

## 📈 Performance Baselines

### Normal Operating Ranges

| Metric | Normal Range | Warning Threshold | Critical Threshold |
|--------|--------------|-------------------|-------------------|
| P95 Query Latency | <100ms | >200ms | >500ms |
| Zero Result Rate | <5% | >10% | >20% |
| Error Rate | <0.1% | >1% | >5% |
| Hybrid Coverage | >50% | <30% | <20% |
| Active Queries | 0-10 | >50 | >100 |
| Memory Usage | <2GB | >4GB | >6GB |

### Capacity Planning

- **Current**: 47 documents, 12 vectors
- **Tested**: Up to 10,000 memories
- **Recommended**: Scale vertically up to 50,000 memories
- **Beyond**: Consider sharding or read replicas

---

## 🔧 Useful Commands

### Database Queries

```sql
-- Get index statistics
SELECT
  (SELECT COUNT(*) FROM semantic_memory) as total_memories,
  (SELECT COUNT(*) FROM semantic_memory WHERE embedding IS NOT NULL) as with_embeddings,
  (SELECT COUNT(*) FROM vec_semantic_memory) as vec_indexed,
  (SELECT COUNT(*) FROM fts_semantic_memory) as fts_indexed;

-- Recent queries (from logs)
SELECT content_type, COUNT(*)
FROM semantic_memory
WHERE created_at > datetime('now', '-1 hour')
GROUP BY content_type;

-- Average content length by type
SELECT content_type, AVG(LENGTH(content)) as avg_length
FROM semantic_memory
GROUP BY content_type;
```

### Metrics Queries

```bash
# Top 10 slowest queries (requires Prometheus)
topk(10, devstream_query_duration_seconds)

# Error rate by category
sum(rate(devstream_errors_total[5m])) by (category)

# Memory usage trend
devstream_process_resident_memory_bytes
```

---

## 📞 Escalation Path

1. **Self-Service** (0-15 min): Use this runbook
2. **Team Lead** (15-30 min): If issue persists
3. **On-Call Engineer** (30+ min): For critical issues
4. **Vendor Support** (next business day): For platform issues

---

**Status**: ✅ **READY FOR OPERATIONS**
**Version**: 1.0
**Last Updated**: 2025-09-30