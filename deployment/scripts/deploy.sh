#!/bin/bash

# DevStream Production Deployment Script
# Context7-validated deployment automation with comprehensive error handling

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOYMENT_DIR="$PROJECT_ROOT/deployment"

# Default values
ENVIRONMENT="${1:-production}"
BRANCH="${2:-main}"
SKIP_BACKUP="${3:-false}"
SKIP_MIGRATIONS="${4:-false}"
DRY_RUN="${5:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# Error handling
trap 'handle_error $? $LINENO' ERR

handle_error() {
    local exit_code=$1
    local line_number=$2
    log_error "Deployment failed at line $line_number with exit code $exit_code"
    cleanup_on_error
    exit $exit_code
}

cleanup_on_error() {
    log_warning "Performing cleanup after error..."
    # Add any cleanup operations here
}

# Validation functions
validate_environment() {
    local env=$1
    if [[ ! "$env" =~ ^(production|staging|development)$ ]]; then
        log_error "Invalid environment: $env. Must be one of: production, staging, development"
        exit 1
    fi
}

validate_branch() {
    local branch=$1
    if ! git ls-remote --heads origin "$branch" | grep -q "$branch"; then
        log_error "Branch '$branch' does not exist on remote"
        exit 1
    fi
}

check_prerequisites() {
    log_step "Checking prerequisites..."

    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker is not running"
        exit 1
    fi

    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    # Check if Fabric is available
    if ! command -v fab &> /dev/null; then
        log_warning "Fabric is not installed. Install with: pip install fabric"
    fi

    # Check if required files exist
    local required_files=(
        "$DEPLOYMENT_DIR/docker/Dockerfile"
        "$DEPLOYMENT_DIR/docker/docker-compose.prod.yml"
        "$DEPLOYMENT_DIR/fabfile.py"
        "$DEPLOYMENT_DIR/nginx/nginx.conf"
    )

    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_error "Required file not found: $file"
            exit 1
        fi
    done

    log_success "Prerequisites check passed"
}

check_environment_variables() {
    log_step "Checking environment variables..."

    local required_vars=(
        "DEVSTREAM_SECRET_KEY"
    )

    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            log_error "  - $var"
        done
        log_info "Create a .env file or export these variables"
        exit 1
    fi

    log_success "Environment variables check passed"
}

load_environment_file() {
    local env_file="$PROJECT_ROOT/.env.$ENVIRONMENT"

    if [[ -f "$env_file" ]]; then
        log_info "Loading environment file: $env_file"
        # shellcheck source=/dev/null
        source "$env_file"
    else
        log_warning "Environment file not found: $env_file"
    fi
}

backup_current_state() {
    if [[ "$SKIP_BACKUP" == "true" ]]; then
        log_warning "Skipping backup (as requested)"
        return 0
    fi

    log_step "Creating backup of current state..."

    local timestamp
    timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_dir="$PROJECT_ROOT/backups/$timestamp"

    mkdir -p "$backup_dir"

    # Backup database if it exists
    local db_path="/opt/devstream/data/production.db"
    if [[ -f "$db_path" ]]; then
        cp "$db_path" "$backup_dir/database_backup.db"
        log_info "Database backed up to $backup_dir/database_backup.db"
    fi

    # Backup current git commit
    git rev-parse HEAD > "$backup_dir/git_commit.txt"

    # Create backup info file
    cat > "$backup_dir/backup_info.json" << EOF
{
    "timestamp": "$timestamp",
    "environment": "$ENVIRONMENT",
    "branch": "$BRANCH",
    "git_commit": "$(git rev-parse HEAD)",
    "deployment_user": "$(whoami)",
    "backup_reason": "pre_deployment"
}
EOF

    log_success "Backup created in $backup_dir"
}

build_docker_images() {
    log_step "Building Docker images..."

    cd "$PROJECT_ROOT"

    # Build production image
    docker build \
        -f deployment/docker/Dockerfile \
        --target production \
        --tag devstream:latest \
        --tag "devstream:$(git rev-parse --short HEAD)" \
        .

    # Build migration image
    docker build \
        -f deployment/docker/Dockerfile \
        --target migration \
        --tag devstream:latest-migration \
        .

    log_success "Docker images built successfully"
}

run_database_migrations() {
    if [[ "$SKIP_MIGRATIONS" == "true" ]]; then
        log_warning "Skipping database migrations (as requested)"
        return 0
    fi

    log_step "Running database migrations..."

    cd "$DEPLOYMENT_DIR"

    # Run migrations using Docker Compose
    docker-compose -f docker/docker-compose.prod.yml run --rm devstream-migrations

    log_success "Database migrations completed"
}

deploy_containers() {
    log_step "Deploying containers..."

    cd "$DEPLOYMENT_DIR"

    # Stop existing containers
    docker-compose -f docker/docker-compose.prod.yml down || true

    # Start new containers
    docker-compose -f docker/docker-compose.prod.yml up -d

    log_success "Containers deployed successfully"
}

verify_deployment() {
    log_step "Verifying deployment..."

    local max_attempts=30
    local attempt=1
    local health_url="http://localhost/health"

    while [[ $attempt -le $max_attempts ]]; do
        log_info "Health check attempt $attempt/$max_attempts..."

        if curl -sf "$health_url" > /dev/null 2>&1; then
            local health_response
            health_response=$(curl -s "$health_url")

            if echo "$health_response" | grep -q '"status":"healthy"'; then
                log_success "Deployment verification passed"
                log_info "Health check response: $health_response"
                return 0
            else
                log_warning "Health check returned non-healthy status"
            fi
        else
            log_warning "Health check failed"
        fi

        if [[ $attempt -eq $max_attempts ]]; then
            log_error "Deployment verification failed after $max_attempts attempts"
            return 1
        fi

        sleep 10
        ((attempt++))
    done
}

cleanup_old_images() {
    log_step "Cleaning up old Docker images..."

    # Remove unused images
    docker image prune -f

    # Remove old tagged images (keep last 5)
    local old_images
    old_images=$(docker images devstream --format "table {{.Repository}}:{{.Tag}}" | grep -v "latest" | tail -n +6)

    if [[ -n "$old_images" ]]; then
        echo "$old_images" | xargs -r docker rmi
        log_info "Removed old images"
    else
        log_info "No old images to remove"
    fi

    log_success "Cleanup completed"
}

show_deployment_status() {
    log_step "Deployment Status Summary"

    echo ""
    echo "================================="
    echo "DevStream Deployment Status"
    echo "================================="
    echo "Environment: $ENVIRONMENT"
    echo "Branch: $BRANCH"
    echo "Git Commit: $(git rev-parse HEAD)"
    echo "Deployment Time: $(date)"
    echo ""

    # Show container status
    echo "Container Status:"
    docker-compose -f "$DEPLOYMENT_DIR/docker/docker-compose.prod.yml" ps

    echo ""

    # Show health status
    echo "Health Status:"
    if curl -sf "http://localhost/health" > /dev/null 2>&1; then
        curl -s "http://localhost/health" | python3 -m json.tool 2>/dev/null || echo "Health check OK"
    else
        echo "❌ Health check failed"
    fi

    echo ""
    echo "================================="
}

show_usage() {
    cat << EOF
DevStream Production Deployment Script

Usage: $0 [ENVIRONMENT] [BRANCH] [SKIP_BACKUP] [SKIP_MIGRATIONS] [DRY_RUN]

Arguments:
    ENVIRONMENT     Target environment (production, staging, development) [default: production]
    BRANCH          Git branch to deploy [default: main]
    SKIP_BACKUP     Skip backup creation (true/false) [default: false]
    SKIP_MIGRATIONS Skip database migrations (true/false) [default: false]
    DRY_RUN         Show what would be done without executing (true/false) [default: false]

Examples:
    $0                                    # Deploy production from main branch
    $0 staging                           # Deploy staging from main branch
    $0 production feature/new-api        # Deploy production from feature branch
    $0 production main true              # Deploy production, skip backup
    $0 staging main false false true     # Dry run for staging

Environment Variables:
    DEVSTREAM_SECRET_KEY                 # Required: Secret key for encryption

Files:
    .env.production                      # Production environment variables
    .env.staging                         # Staging environment variables
    .env.development                     # Development environment variables

EOF
}

# Main deployment function
main() {
    # Show banner
    echo ""
    echo "🚀 DevStream Production Deployment"
    echo "=================================="
    echo ""

    # Parse arguments
    if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
        show_usage
        exit 0
    fi

    # Validate inputs
    validate_environment "$ENVIRONMENT"
    validate_branch "$BRANCH"

    # Show deployment info
    log_info "Environment: $ENVIRONMENT"
    log_info "Branch: $BRANCH"
    log_info "Skip Backup: $SKIP_BACKUP"
    log_info "Skip Migrations: $SKIP_MIGRATIONS"
    log_info "Dry Run: $DRY_RUN"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_warning "DRY RUN MODE - No actual changes will be made"
        echo ""
        echo "Would execute the following steps:"
        echo "1. Check prerequisites"
        echo "2. Load environment configuration"
        echo "3. Create backup (skip: $SKIP_BACKUP)"
        echo "4. Build Docker images"
        echo "5. Run database migrations (skip: $SKIP_MIGRATIONS)"
        echo "6. Deploy containers"
        echo "7. Verify deployment"
        echo "8. Cleanup old images"
        echo "9. Show deployment status"
        echo ""
        log_info "Use DRY_RUN=false to execute actual deployment"
        exit 0
    fi

    # Confirmation for production
    if [[ "$ENVIRONMENT" == "production" ]]; then
        echo ""
        read -p "⚠️  Deploy to PRODUCTION environment? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Deployment cancelled by user"
            exit 0
        fi
    fi

    # Execute deployment steps
    check_prerequisites
    load_environment_file
    check_environment_variables
    backup_current_state
    build_docker_images
    run_database_migrations
    deploy_containers
    verify_deployment
    cleanup_old_images
    show_deployment_status

    echo ""
    log_success "🎉 Deployment completed successfully!"
    echo ""
}

# Execute main function
main "$@"