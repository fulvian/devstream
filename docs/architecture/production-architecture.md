# DevStream Production Architecture

## Context7-Validated Production Infrastructure Design

This document outlines the production deployment architecture for DevStream, implementing Context7-validated patterns for scalable, secure, and maintainable production deployment.

## 🏗 Architecture Overview

### Core Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DevStream Production Stack                       │
├─────────────────────────────────────────────────────────────────────┤
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │
│  │   Web API     │  │  Task Engine  │  │ Memory System │           │
│  │  (FastAPI)    │  │   (Async)     │  │   (Vector)    │           │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘           │
│          │                  │                  │                   │
│  ┌───────┴──────────────────┴──────────────────┴───────┐           │
│  │              Database Layer (SQLite + VSS)          │           │
│  └─────────────────────────┬───────────────────────────┘           │
│                            │                                       │
│  ┌─────────────────────────┴───────────────────────────┐           │
│  │              Infrastructure Layer                   │           │
│  │  • Docker Containerization                          │           │
│  │  • Nginx Reverse Proxy                              │           │
│  │  • SSL/TLS Termination                              │           │
│  │  • Health Monitoring                                │           │
│  │  • Log Aggregation                                  │           │
│  └─────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
```

## 🚀 Deployment Pipeline

### Context7-Validated Pattern: Fabric + Docker + Alembic

```python
# deployment/fabfile.py - Context7 validated deployment automation
from fabric import task, Connection
from invoke import Exit
import asyncio

@task
def deploy(c, environment='production', branch='main'):
    """Deploy DevStream to production environment."""

    # Step 1: Pre-deployment validation
    validate_environment(c, environment)

    # Step 2: Code deployment
    deploy_code(c, branch)

    # Step 3: Database migrations
    run_migrations(c, environment)

    # Step 4: Container deployment
    deploy_containers(c, environment)

    # Step 5: Health verification
    verify_deployment(c, environment)

def deploy_code(c, branch):
    """Deploy application code using git."""
    c.run(f"cd /opt/devstream && git fetch origin")
    c.run(f"cd /opt/devstream && git checkout {branch}")
    c.run(f"cd /opt/devstream && git pull origin {branch}")

async def run_migrations(c, environment):
    """Run database migrations asynchronously."""
    # Context7 pattern: Alembic async migrations
    from alembic import command, config

    def run_upgrade(connection, cfg):
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")

    # Execute migrations with production database
    c.run("cd /opt/devstream && python -m devstream.database.migrations")
```

### Multi-Environment Configuration

```yaml
# deployment/environments/production.yml
environment: production
database:
  path: "/opt/devstream/data/production.db"
  backup_retention: 30
  connection_pool: 10

containers:
  web_api:
    image: "devstream:latest"
    replicas: 3
    resources:
      cpu_limit: "1.0"
      memory_limit: "512Mi"
    health_check:
      path: "/health"
      interval: 30s
      timeout: 10s

  task_engine:
    image: "devstream:latest"
    replicas: 2
    resources:
      cpu_limit: "2.0"
      memory_limit: "1Gi"

monitoring:
  log_level: "INFO"
  metrics_enabled: true
  health_checks: true
```

## 🐳 Containerization Strategy

### Context7-Validated Multi-Stage Dockerfile

```dockerfile
# deployment/docker/Dockerfile - Production optimized
FROM python:3.11-slim as base

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Python environment
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base as development
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
CMD ["python", "-m", "devstream.cli.main"]

# Production stage
FROM base as production
COPY src/ ./src/
COPY pyproject.toml .

# Create non-root user
RUN groupadd -r devstream && useradd -r -g devstream devstream
RUN chown -R devstream:devstream /app
USER devstream

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Production command
CMD ["python", "-m", "devstream.api.main"]
```

### Docker Compose Production Stack

```yaml
# deployment/docker/docker-compose.prod.yml
version: '3.8'

services:
  devstream-api:
    build:
      context: ../..
      dockerfile: deployment/docker/Dockerfile
      target: production
    image: devstream:latest
    container_name: devstream-api
    restart: unless-stopped
    environment:
      - DEVSTREAM_ENV=production
      - DEVSTREAM_DATABASE_PATH=/data/production.db
    volumes:
      - devstream-data:/data
      - devstream-logs:/app/logs
    networks:
      - devstream-network
    depends_on:
      - devstream-db-setup
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M

  devstream-task-engine:
    image: devstream:latest
    container_name: devstream-tasks
    restart: unless-stopped
    environment:
      - DEVSTREAM_ENV=production
      - DEVSTREAM_DATABASE_PATH=/data/production.db
      - DEVSTREAM_SERVICE_MODE=task_engine
    volumes:
      - devstream-data:/data
      - devstream-logs:/app/logs
    networks:
      - devstream-network
    depends_on:
      - devstream-api
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G

  devstream-nginx:
    image: nginx:alpine
    container_name: devstream-proxy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - devstream-logs:/var/log/nginx
    networks:
      - devstream-network
    depends_on:
      - devstream-api

  devstream-db-setup:
    image: devstream:latest
    container_name: devstream-migrations
    environment:
      - DEVSTREAM_ENV=production
      - DEVSTREAM_DATABASE_PATH=/data/production.db
    volumes:
      - devstream-data:/data
    networks:
      - devstream-network
    command: ["python", "-m", "devstream.database.migrations"]
    restart: "no"

volumes:
  devstream-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/devstream/data

  devstream-logs:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/devstream/logs

networks:
  devstream-network:
    driver: bridge
```

## 🔒 Security & Configuration

### Environment-Based Configuration

```python
# src/devstream/core/config.py - Production configuration
from pydantic_settings import BaseSettings
from typing import Literal

class ProductionConfig(BaseSettings):
    """Production environment configuration."""

    environment: Literal["production"] = "production"

    # Database
    database_path: str = "/data/production.db"
    database_backup_enabled: bool = True
    database_backup_interval: int = 3600  # 1 hour

    # Security
    secret_key: str  # Required in production
    allowed_hosts: list[str] = ["api.devstream.local"]
    cors_enabled: bool = False

    # Logging
    log_level: Literal["INFO", "WARNING", "ERROR"] = "INFO"
    log_format: str = "structured"
    log_file_enabled: bool = True
    log_file_path: str = "/app/logs/devstream.log"

    # Performance
    max_connections: int = 50
    connection_timeout: int = 30
    request_timeout: int = 120

    # Monitoring
    health_check_enabled: bool = True
    metrics_enabled: bool = True
    profiling_enabled: bool = False

    class Config:
        env_prefix = "DEVSTREAM_"
        case_sensitive = False
```

### Nginx Configuration

```nginx
# deployment/nginx/nginx.conf - Production reverse proxy
upstream devstream_api {
    least_conn;
    server devstream-api:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name api.devstream.local;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.devstream.local;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/devstream.crt;
    ssl_certificate_key /etc/nginx/ssl/devstream.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types application/json application/javascript text/css text/javascript;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://devstream_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    location /health {
        access_log off;
        proxy_pass http://devstream_api/health;
    }

    location /metrics {
        allow 127.0.0.1;
        deny all;
        proxy_pass http://devstream_api/metrics;
    }
}
```

## 📊 Monitoring & Observability

### Health Check System

```python
# src/devstream/api/health.py - Production health checks
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import asyncio
import time

class HealthStatus(BaseModel):
    status: str
    timestamp: float
    version: str
    components: Dict[str, Any]

async def health_check() -> HealthStatus:
    """Comprehensive health check for production monitoring."""

    components = {}
    overall_status = "healthy"

    # Database health
    try:
        db_start = time.time()
        # Check database connectivity
        await check_database_health()
        components["database"] = {
            "status": "healthy",
            "response_time_ms": (time.time() - db_start) * 1000
        }
    except Exception as e:
        components["database"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "unhealthy"

    # Memory system health
    try:
        memory_start = time.time()
        await check_memory_system_health()
        components["memory"] = {
            "status": "healthy",
            "response_time_ms": (time.time() - memory_start) * 1000
        }
    except Exception as e:
        components["memory"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "degraded" if overall_status == "healthy" else "unhealthy"

    # Task engine health
    try:
        task_start = time.time()
        await check_task_engine_health()
        components["tasks"] = {
            "status": "healthy",
            "response_time_ms": (time.time() - task_start) * 1000
        }
    except Exception as e:
        components["tasks"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "degraded" if overall_status == "healthy" else "unhealthy"

    return HealthStatus(
        status=overall_status,
        timestamp=time.time(),
        version="1.0.0",
        components=components
    )
```

### Structured Logging

```python
# src/devstream/core/logging.py - Production logging setup
import structlog
import logging.config
from typing import Any, Dict

def setup_production_logging(log_level: str = "INFO", log_file: str = None) -> None:
    """Setup structured logging for production environment."""

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.JSONRenderer()
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level)
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # File logging configuration
    if log_file:
        logging.config.dictConfig({
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "format": "%(message)s"
                }
            },
            "handlers": {
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": log_file,
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5,
                    "formatter": "json"
                }
            },
            "root": {
                "handlers": ["file"],
                "level": log_level
            }
        })
```

## 🚦 Deployment Commands

### Context7-Validated Deployment Scripts

```bash
#!/bin/bash
# deployment/scripts/deploy.sh - Production deployment automation

set -euo pipefail

ENVIRONMENT=${1:-production}
BRANCH=${2:-main}
DEPLOY_DIR="/opt/devstream"

echo "🚀 DevStream Production Deployment"
echo "Environment: $ENVIRONMENT"
echo "Branch: $BRANCH"

# Pre-deployment checks
echo "📋 Running pre-deployment checks..."
fab check-environment --environment=$ENVIRONMENT

# Database backup
echo "💾 Creating database backup..."
fab backup-database --environment=$ENVIRONMENT

# Code deployment
echo "📦 Deploying code..."
fab deploy-code --branch=$BRANCH

# Database migrations
echo "🔄 Running database migrations..."
fab run-migrations --environment=$ENVIRONMENT

# Container deployment
echo "🐳 Deploying containers..."
fab deploy-containers --environment=$ENVIRONMENT

# Health verification
echo "🏥 Verifying deployment health..."
fab verify-deployment --environment=$ENVIRONMENT

echo "✅ Deployment completed successfully!"
```

## 📈 Performance Optimization

### Production Tuning

```python
# src/devstream/core/performance.py - Production performance optimizations
import asyncio
import uvloop
from contextlib import asynccontextmanager

@asynccontextmanager
async def optimized_runtime():
    """Context manager for production-optimized async runtime."""

    # Use uvloop for better performance
    if hasattr(asyncio, 'set_event_loop_policy'):
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    # Connection pool optimization
    from devstream.database.connection import ConnectionPool
    pool = ConnectionPool(
        max_connections=50,
        connection_timeout=30,
        pool_timeout=60
    )

    try:
        await pool.initialize()
        yield pool
    finally:
        await pool.close()

# Production server configuration
PRODUCTION_SERVER_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "workers": 4,
    "loop": "uvloop",
    "http": "httptools",
    "access_log": False,
    "server_header": False,
    "date_header": False
}
```

## 🔧 Maintenance & Operations

### Automated Backup System

```python
# deployment/scripts/backup.py - Automated backup system
import asyncio
import shutil
import datetime
from pathlib import Path

async def create_backup(environment: str = "production"):
    """Create automated backup of production database."""

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"/opt/devstream/backups/{environment}")
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Database backup
    db_path = f"/opt/devstream/data/{environment}.db"
    backup_path = backup_dir / f"database_{timestamp}.db"

    shutil.copy2(db_path, backup_path)

    # Cleanup old backups (keep last 30)
    backups = sorted(backup_dir.glob("database_*.db"))
    for old_backup in backups[:-30]:
        old_backup.unlink()

    print(f"✅ Backup created: {backup_path}")
```

## 📋 Next Steps

1. **Database Migration System Implementation** - Alembic async setup
2. **Production Configuration Management** - Environment-specific configs
3. **Logging & Monitoring System** - Structured logging + health checks
4. **Deployment Automation Scripts** - Fabric-based deployment
5. **Container Orchestration** - Docker Compose production setup
6. **Security Hardening** - SSL, authentication, rate limiting
7. **Performance Testing** - Load testing under production conditions

---

*Documento basato su Context7-validated patterns per production deployment*
*Architettura: Multi-container + Nginx + Database migrations + Monitoring*
*Pattern validati: Fabric + Docker + Alembic + Structured Logging*