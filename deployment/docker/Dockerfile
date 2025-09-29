# DevStream Production Dockerfile
# Context7-validated multi-stage build for production optimization

# Base stage with common dependencies
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r devstream && useradd -r -g devstream -s /bin/false devstream

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base as development

# Install development dependencies
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy source code
COPY . .

# Change ownership to devstream user
RUN chown -R devstream:devstream /app

# Switch to non-root user
USER devstream

# Development command
CMD ["python", "-m", "devstream.cli.main"]

# Production stage
FROM base as production

# Copy only production source code
COPY src/ ./src/
COPY pyproject.toml .
COPY README.md .

# Install package in production mode
RUN pip install --no-cache-dir -e .

# Create directories for data and logs
RUN mkdir -p /app/data /app/logs /app/backups

# Change ownership to devstream user
RUN chown -R devstream:devstream /app

# Switch to non-root user
USER devstream

# Health check for production
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command
CMD ["python", "-m", "devstream.api.main"]

# Migration stage - special stage for running migrations
FROM production as migration

# Override user to root for migration operations if needed
USER root

# Migration command
CMD ["python", "-m", "devstream.database.migrations_alembic", "upgrade"]