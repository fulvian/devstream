# DevStream Deployment Guide

**Production Deployment for Hybrid Search System**
**Version**: 1.0
**Date**: 2025-09-30

---

## 📋 Prerequisites

### System Requirements
- **Node.js**: >=18.0.0
- **SQLite**: >=3.39.0 (for FULL OUTER JOIN support)
- **Ollama**: Latest version with embeddinggemma:300m model
- **Memory**: Minimum 2GB RAM
- **Disk**: 10GB+ for database and vectors

### Dependencies
```json
{
  "better-sqlite3": "^12.4.1",
  "sqlite-vec": "^0.1.6",
  "ollama": "^0.5.9",
  "prom-client": "^15.1.3",
  "zod": "^3.22.4"
}
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd mcp-devstream-server
npm install
```

### 2. Build TypeScript

```bash
npm run build
```

### 3. Configure Environment

```bash
# Create .env file
cat > .env <<EOF
DEVSTREAM_DB_PATH=/path/to/devstream.db
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=embeddinggemma:300m
METRICS_PORT=9090
NODE_ENV=production
EOF
```

### 4. Initialize Database

```bash
# Database auto-initializes on first connection
# Or manually:
node dist/database.js
```

### 5. Start MCP Server

```bash
# Via Claude Code (recommended)
# Add to Claude Code MCP settings

# Or standalone for testing
node dist/index.js
```

### 6. Start Metrics Server (Optional)

```typescript
import { globalMetricsServer } from './monitoring/metrics-server.js';
await globalMetricsServer.start();
```

---

## 🔧 Production Configuration

### Environment Variables

```bash
# === Database ===
DEVSTREAM_DB_PATH=/var/lib/devstream/devstream.db
SQLITE_EXTENSIONS_PATH=/usr/local/lib/sqlite-extensions

# === Ollama ===
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=embeddinggemma:300m
OLLAMA_TIMEOUT=30000

# === Monitoring ===
METRICS_PORT=9090
COLLECT_DEFAULT_METRICS=true

# === Performance ===
NODE_ENV=production
NODE_OPTIONS="--max-old-space-size=4096"

# === Logging ===
LOG_LEVEL=info
LOG_FORMAT=json
```

### Database Optimization

```sql
-- WAL mode for better concurrency
PRAGMA journal_mode=WAL;

-- Optimize for read performance
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;

-- Auto-vacuum to manage disk space
PRAGMA auto_vacuum=INCREMENTAL;
```

### Ollama Configuration

```bash
# Start Ollama service
ollama serve

# Pull embedding model
ollama pull embeddinggemma:300m

# Verify model
ollama list | grep embeddinggemma
```

---

## 📦 Deployment Options

### Option 1: Systemd Service (Linux)

Create `/etc/systemd/system/devstream.service`:

```ini
[Unit]
Description=DevStream MCP Server
After=network.target

[Service]
Type=simple
User=devstream
WorkingDirectory=/opt/devstream/mcp-devstream-server
Environment=NODE_ENV=production
EnvironmentFile=/opt/devstream/.env
ExecStart=/usr/bin/node dist/index.js
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable devstream
sudo systemctl start devstream
sudo systemctl status devstream
```

### Option 2: Docker Container

Create `Dockerfile`:

```dockerfile
FROM node:18-alpine

# Install build dependencies
RUN apk add --no-cache python3 make g++ sqlite

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source
COPY dist ./dist
COPY data ./data

# Expose metrics port
EXPOSE 9090

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:9090/health || exit 1

CMD ["node", "dist/index.js"]
```

Build and run:

```bash
docker build -t devstream:latest .
docker run -d \
  --name devstream \
  -p 9090:9090 \
  -v /var/lib/devstream:/app/data \
  --restart unless-stopped \
  devstream:latest
```

### Option 3: PM2 Process Manager

```bash
# Install PM2
npm install -g pm2

# Create ecosystem file
cat > ecosystem.config.js <<EOF
module.exports = {
  apps: [{
    name: 'devstream',
    script: './dist/index.js',
    instances: 1,
    exec_mode: 'cluster',
    env_production: {
      NODE_ENV: 'production'
    }
  }]
};
EOF

# Start with PM2
pm2 start ecosystem.config.js --env production

# Save PM2 configuration
pm2 save

# Auto-start on boot
pm2 startup
```

---

## 📊 Monitoring Setup

### Prometheus

Add to `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'devstream'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:9090']
        labels:
          service: 'devstream'
          environment: 'production'
```

### Grafana

1. Add Prometheus data source
2. Import dashboard JSON (see MONITORING.md)
3. Configure alerts

---

## 🔐 Security

### File Permissions

```bash
# Database directory
sudo chown -R devstream:devstream /var/lib/devstream
sudo chmod 750 /var/lib/devstream

# Config files
sudo chmod 600 /opt/devstream/.env
```

### Network Security

```bash
# Firewall rules (metrics endpoint only internal)
sudo ufw allow from 10.0.0.0/8 to any port 9090
sudo ufw enable
```

---

## 🔄 Backup & Recovery

### Database Backup

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR=/var/backups/devstream
DATE=$(date +%Y%m%d_%H%M%S)

# Backup database
sqlite3 /var/lib/devstream/devstream.db \
  ".backup ${BACKUP_DIR}/devstream_${DATE}.db"

# Compress
gzip ${BACKUP_DIR}/devstream_${DATE}.db

# Remove backups older than 30 days
find ${BACKUP_DIR} -name "devstream_*.db.gz" -mtime +30 -delete
```

### Recovery

```bash
# Restore from backup
gunzip < /var/backups/devstream/devstream_20250930.db.gz > /var/lib/devstream/devstream.db

# Restart service
sudo systemctl restart devstream
```

---

## 📈 Performance Tuning

### Node.js

```bash
# Increase heap size for large datasets
export NODE_OPTIONS="--max-old-space-size=8192"

# Enable v8 profiling (if needed)
node --prof dist/index.js
```

### SQLite

```sql
-- Analyze tables for query optimization
ANALYZE;

-- Update statistics
PRAGMA optimize;
```

---

## ✅ Deployment Checklist

- [ ] System requirements verified
- [ ] Dependencies installed
- [ ] Environment variables configured
- [ ] Database initialized
- [ ] Ollama service running
- [ ] Embedding model pulled
- [ ] MCP server started
- [ ] Metrics endpoint accessible
- [ ] Prometheus scraping configured
- [ ] Grafana dashboard imported
- [ ] Backups configured
- [ ] Alerts configured
- [ ] Documentation reviewed

---

**Status**: ✅ **READY FOR PRODUCTION**
**Version**: 1.0
**Date**: 2025-09-30