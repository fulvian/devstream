"""
DevStream production deployment automation using Fabric.

Context7-validated patterns for production deployment:
- Sequential deployment steps with rollback capability
- Database migration automation with backup
- Container orchestration and health verification
- Environment-specific configuration management
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fabric import Connection, task
from invoke import Exit
from invocations.console import confirm
import structlog

# Setup basic logging
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.WriteLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Deployment configuration
DEPLOYMENT_CONFIG = {
    "production": {
        "hosts": ["production.devstream.local"],
        "user": "devstream",
        "app_dir": "/opt/devstream",
        "docker_compose_file": "docker-compose.prod.yml",
        "backup_retention": 30,
        "health_check_retries": 5,
        "health_check_delay": 10,
    },
    "staging": {
        "hosts": ["staging.devstream.local"],
        "user": "devstream",
        "app_dir": "/opt/devstream",
        "docker_compose_file": "docker-compose.staging.yml",
        "backup_retention": 7,
        "health_check_retries": 3,
        "health_check_delay": 5,
    }
}


class DeploymentError(Exception):
    """Custom deployment error."""
    pass


class DeploymentContext:
    """Context manager for deployment operations."""

    def __init__(self, connection: Connection, environment: str):
        self.conn = connection
        self.environment = environment
        self.config = DEPLOYMENT_CONFIG[environment]
        self.deployment_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.rollback_point = None

    def __enter__(self):
        logger.info("Starting deployment",
                   environment=self.environment,
                   deployment_id=self.deployment_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logger.error("Deployment failed",
                        error=str(exc_val),
                        deployment_id=self.deployment_id)
        else:
            logger.info("Deployment completed successfully",
                       deployment_id=self.deployment_id)


@task
def deploy(c, environment="production", branch="main", skip_backup=False, skip_migrations=False):
    """
    Deploy DevStream to specified environment.

    Context7-validated deployment pattern with comprehensive error handling.

    Args:
        environment: Target environment (production, staging)
        branch: Git branch to deploy
        skip_backup: Skip database backup (not recommended for production)
        skip_migrations: Skip database migrations (dangerous)
    """
    if environment not in DEPLOYMENT_CONFIG:
        raise Exit(f"Unknown environment: {environment}")

    config = DEPLOYMENT_CONFIG[environment]

    # Production safety checks
    if environment == "production":
        if not confirm(f"Deploy to PRODUCTION environment from branch '{branch}'?"):
            raise Exit("Deployment cancelled by user")

        if skip_backup and not confirm("Skip backup in PRODUCTION? This is dangerous!"):
            raise Exit("Deployment cancelled - backup required")

    # Deploy to each host
    for host in config["hosts"]:
        logger.info(f"Deploying to {host}")

        conn = Connection(f"{config['user']}@{host}")

        with DeploymentContext(conn, environment) as ctx:
            try:
                # Step 1: Pre-deployment validation
                pre_deployment_checks(ctx, branch)

                # Step 2: Create rollback point
                if not skip_backup:
                    create_rollback_point(ctx)

                # Step 3: Deploy application code
                deploy_application_code(ctx, branch)

                # Step 4: Run database migrations
                if not skip_migrations:
                    run_database_migrations(ctx)

                # Step 5: Deploy containers
                deploy_containers(ctx)

                # Step 6: Verify deployment health
                verify_deployment_health(ctx)

                # Step 7: Cleanup old deployments
                cleanup_old_deployments(ctx)

                logger.info("Deployment successful", host=host)

            except Exception as e:
                logger.error("Deployment failed", host=host, error=str(e))

                # Attempt rollback if we have a rollback point
                if ctx.rollback_point and not skip_backup:
                    if confirm("Deployment failed. Attempt rollback?"):
                        rollback_deployment(ctx)

                raise DeploymentError(f"Deployment to {host} failed: {e}")


def pre_deployment_checks(ctx: DeploymentContext, branch: str) -> None:
    """Run pre-deployment validation checks."""
    logger.info("Running pre-deployment checks")

    # Check if application directory exists
    result = ctx.conn.run(f"test -d {ctx.config['app_dir']}", warn=True)
    if result.failed:
        raise DeploymentError(f"Application directory {ctx.config['app_dir']} does not exist")

    # Check if git repository is clean
    with ctx.conn.cd(ctx.config["app_dir"]):
        result = ctx.conn.run("git status --porcelain", hide=True)
        if result.stdout.strip():
            if not confirm("Git repository has uncommitted changes. Continue?"):
                raise Exit("Deployment cancelled - repository not clean")

    # Check if branch exists
    with ctx.conn.cd(ctx.config["app_dir"]):
        result = ctx.conn.run(f"git ls-remote --heads origin {branch}", hide=True)
        if not result.stdout.strip():
            raise DeploymentError(f"Branch '{branch}' does not exist on remote")

    # Check disk space
    result = ctx.conn.run("df -h /opt", hide=True)
    logger.info("Disk space check", output=result.stdout.strip())

    # Check if Docker is running
    result = ctx.conn.run("docker info", hide=True, warn=True)
    if result.failed:
        raise DeploymentError("Docker is not running or accessible")

    logger.info("Pre-deployment checks passed")


def create_rollback_point(ctx: DeploymentContext) -> None:
    """Create rollback point for safe deployment."""
    logger.info("Creating rollback point")

    backup_dir = f"{ctx.config['app_dir']}/backups"
    ctx.conn.run(f"mkdir -p {backup_dir}")

    # Backup current database
    db_backup_path = f"{backup_dir}/database_pre_deploy_{ctx.deployment_id}.db"
    db_path = f"{ctx.config['app_dir']}/data/production.db"

    result = ctx.conn.run(f"test -f {db_path}", warn=True)
    if result.ok:
        ctx.conn.run(f"cp {db_path} {db_backup_path}")
        logger.info("Database backup created", path=db_backup_path)

    # Backup current git commit
    with ctx.conn.cd(ctx.config["app_dir"]):
        result = ctx.conn.run("git rev-parse HEAD", hide=True)
        current_commit = result.stdout.strip()

    # Store rollback information
    rollback_info = {
        "deployment_id": ctx.deployment_id,
        "timestamp": datetime.now().isoformat(),
        "git_commit": current_commit,
        "database_backup": db_backup_path,
        "environment": ctx.environment
    }

    rollback_file = f"{backup_dir}/rollback_info_{ctx.deployment_id}.json"
    ctx.conn.run(f"echo '{json.dumps(rollback_info)}' > {rollback_file}")

    ctx.rollback_point = rollback_info
    logger.info("Rollback point created", commit=current_commit)


def deploy_application_code(ctx: DeploymentContext, branch: str) -> None:
    """Deploy application code using git."""
    logger.info("Deploying application code", branch=branch)

    with ctx.conn.cd(ctx.config["app_dir"]):
        # Fetch latest changes
        ctx.conn.run("git fetch origin")

        # Checkout target branch
        ctx.conn.run(f"git checkout {branch}")

        # Pull latest changes
        ctx.conn.run(f"git pull origin {branch}")

        # Get deployed commit
        result = ctx.conn.run("git rev-parse HEAD", hide=True)
        deployed_commit = result.stdout.strip()

        logger.info("Code deployment completed", commit=deployed_commit)


def run_database_migrations(ctx: DeploymentContext) -> None:
    """Run database migrations."""
    logger.info("Running database migrations")

    with ctx.conn.cd(ctx.config["app_dir"]):
        # Run migrations using the new Alembic system
        result = ctx.conn.run(
            "python -m devstream.database.migrations_alembic upgrade",
            warn=True
        )

        if result.failed:
            raise DeploymentError(f"Database migrations failed: {result.stderr}")

    logger.info("Database migrations completed successfully")


def deploy_containers(ctx: DeploymentContext) -> None:
    """Deploy Docker containers."""
    logger.info("Deploying containers")

    with ctx.conn.cd(ctx.config["app_dir"]):
        compose_file = f"deployment/docker/{ctx.config['docker_compose_file']}"

        # Build new images
        ctx.conn.run(f"docker-compose -f {compose_file} build")

        # Stop existing containers
        ctx.conn.run(f"docker-compose -f {compose_file} down", warn=True)

        # Start new containers
        ctx.conn.run(f"docker-compose -f {compose_file} up -d")

        # Wait for containers to start
        time.sleep(10)

    logger.info("Container deployment completed")


def verify_deployment_health(ctx: DeploymentContext) -> None:
    """Verify deployment health through health checks."""
    logger.info("Verifying deployment health")

    config = ctx.config
    max_retries = config["health_check_retries"]
    delay = config["health_check_delay"]

    for attempt in range(max_retries):
        try:
            # Check container status
            with ctx.conn.cd(ctx.config["app_dir"]):
                compose_file = f"deployment/docker/{config['docker_compose_file']}"
                result = ctx.conn.run(f"docker-compose -f {compose_file} ps", hide=True)

                if "Up" not in result.stdout:
                    raise DeploymentError("Containers are not running")

            # Check API health endpoint
            result = ctx.conn.run(
                "curl -f http://localhost/health",
                hide=True,
                warn=True
            )

            if result.ok:
                health_data = json.loads(result.stdout)
                if health_data.get("status") == "healthy":
                    logger.info("Health check passed")
                    return
                else:
                    logger.warning("Health check returned unhealthy status",
                                 status=health_data.get("status"))

            if attempt < max_retries - 1:
                logger.info(f"Health check failed, retrying in {delay}s",
                           attempt=attempt + 1)
                time.sleep(delay)
            else:
                raise DeploymentError("Health check failed after all retries")

        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning("Health check attempt failed",
                             attempt=attempt + 1,
                             error=str(e))
                time.sleep(delay)
            else:
                raise DeploymentError(f"Health verification failed: {e}")


def cleanup_old_deployments(ctx: DeploymentContext) -> None:
    """Cleanup old deployment artifacts."""
    logger.info("Cleaning up old deployments")

    backup_dir = f"{ctx.config['app_dir']}/backups"
    retention_days = ctx.config["backup_retention"]

    # Remove old backup files
    ctx.conn.run(
        f"find {backup_dir} -name '*.db' -mtime +{retention_days} -delete",
        warn=True
    )
    ctx.conn.run(
        f"find {backup_dir} -name 'rollback_info_*.json' -mtime +{retention_days} -delete",
        warn=True
    )

    # Remove unused Docker images
    ctx.conn.run("docker image prune -f", warn=True)

    logger.info("Cleanup completed")


def rollback_deployment(ctx: DeploymentContext) -> None:
    """Rollback deployment to previous state."""
    logger.warning("Rolling back deployment")

    if not ctx.rollback_point:
        raise DeploymentError("No rollback point available")

    with ctx.conn.cd(ctx.config["app_dir"]):
        # Stop current containers
        compose_file = f"deployment/docker/{ctx.config['docker_compose_file']}"
        ctx.conn.run(f"docker-compose -f {compose_file} down", warn=True)

        # Restore git commit
        ctx.conn.run(f"git checkout {ctx.rollback_point['git_commit']}")

        # Restore database
        if "database_backup" in ctx.rollback_point:
            db_path = f"{ctx.config['app_dir']}/data/production.db"
            backup_path = ctx.rollback_point["database_backup"]

            result = ctx.conn.run(f"test -f {backup_path}", warn=True)
            if result.ok:
                ctx.conn.run(f"cp {backup_path} {db_path}")
                logger.info("Database restored from backup")

        # Restart containers with previous version
        ctx.conn.run(f"docker-compose -f {compose_file} up -d")

    logger.info("Rollback completed")


@task
def status(c, environment="production"):
    """Check deployment status."""
    if environment not in DEPLOYMENT_CONFIG:
        raise Exit(f"Unknown environment: {environment}")

    config = DEPLOYMENT_CONFIG[environment]

    for host in config["hosts"]:
        conn = Connection(f"{config['user']}@{host}")

        print(f"\n=== Status for {host} ===")

        # Git status
        with conn.cd(config["app_dir"]):
            result = conn.run("git log -1 --oneline", hide=True)
            print(f"Current commit: {result.stdout.strip()}")

            result = conn.run("git status --porcelain", hide=True)
            if result.stdout.strip():
                print(f"⚠️  Uncommitted changes detected")
            else:
                print("✅ Repository is clean")

        # Container status
        with conn.cd(config["app_dir"]):
            compose_file = f"deployment/docker/{config['docker_compose_file']}"
            result = conn.run(f"docker-compose -f {compose_file} ps", hide=True)
            print(f"Container status:\n{result.stdout}")

        # Health check
        result = conn.run("curl -s http://localhost/health", warn=True, hide=True)
        if result.ok:
            try:
                health_data = json.loads(result.stdout)
                status = health_data.get("status", "unknown")
                print(f"Health status: {status}")
            except json.JSONDecodeError:
                print("❌ Health endpoint returned invalid JSON")
        else:
            print("❌ Health endpoint not accessible")


@task
def backup(c, environment="production"):
    """Create manual backup."""
    if environment not in DEPLOYMENT_CONFIG:
        raise Exit(f"Unknown environment: {environment}")

    config = DEPLOYMENT_CONFIG[environment]

    for host in config["hosts"]:
        conn = Connection(f"{config['user']}@{host}")

        backup_dir = f"{config['app_dir']}/backups"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create database backup
        db_path = f"{config['app_dir']}/data/production.db"
        backup_path = f"{backup_dir}/manual_backup_{timestamp}.db"

        result = conn.run(f"test -f {db_path}", warn=True)
        if result.ok:
            conn.run(f"mkdir -p {backup_dir}")
            conn.run(f"cp {db_path} {backup_path}")
            print(f"✅ Database backup created: {backup_path}")
        else:
            print(f"❌ Database not found: {db_path}")


@task
def logs(c, environment="production", service="devstream-api", tail=100):
    """View service logs."""
    if environment not in DEPLOYMENT_CONFIG:
        raise Exit(f"Unknown environment: {environment}")

    config = DEPLOYMENT_CONFIG[environment]

    for host in config["hosts"]:
        conn = Connection(f"{config['user']}@{host}")

        print(f"\n=== Logs for {service} on {host} ===")

        with conn.cd(config["app_dir"]):
            compose_file = f"deployment/docker/{config['docker_compose_file']}"
            conn.run(f"docker-compose -f {compose_file} logs --tail={tail} {service}")


@task
def shell(c, environment="production", service="devstream-api"):
    """Connect to service shell."""
    if environment not in DEPLOYMENT_CONFIG:
        raise Exit(f"Unknown environment: {environment}")

    config = DEPLOYMENT_CONFIG[environment]
    host = config["hosts"][0]  # Connect to first host

    conn = Connection(f"{config['user']}@{host}")

    with conn.cd(config["app_dir"]):
        compose_file = f"deployment/docker/{config['docker_compose_file']}"
        conn.run(f"docker-compose -f {compose_file} exec {service} /bin/bash", pty=True)


# Configuration management tasks
@task
def validate_config(c, environment="production"):
    """Validate environment configuration."""
    if environment not in DEPLOYMENT_CONFIG:
        raise Exit(f"Unknown environment: {environment}")

    config = DEPLOYMENT_CONFIG[environment]
    print(f"Configuration for {environment}:")
    print(json.dumps(config, indent=2))


@task
def update_config(c, environment="production"):
    """Update environment configuration files."""
    if environment not in DEPLOYMENT_CONFIG:
        raise Exit(f"Unknown environment: {environment}")

    config = DEPLOYMENT_CONFIG[environment]

    for host in config["hosts"]:
        conn = Connection(f"{config['user']}@{host}")

        # Update environment file
        env_file = f"{config['app_dir']}/.env.{environment}"

        # This would typically copy environment-specific configuration
        # from a secure location or template
        print(f"Environment file should be updated manually: {env_file}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python fabfile.py <task> [options]")
        print("Available tasks: deploy, status, backup, logs, shell, validate-config")
    else:
        # This allows running tasks directly
        task_name = sys.argv[1].replace("-", "_")
        if hasattr(sys.modules[__name__], task_name):
            func = getattr(sys.modules[__name__], task_name)
            if hasattr(func, "_task"):
                print(f"Running task: {task_name}")
                # Note: This is a simplified runner. Use `fab` command for full functionality.
            else:
                print(f"'{task_name}' is not a Fabric task")
        else:
            print(f"Task '{task_name}' not found")