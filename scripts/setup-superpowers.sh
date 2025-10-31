#!/bin/bash
# DevStream Superpowers Setup Script
# Integrates obra/superpowers with DevStream environment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}✅${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1"
}

log_step() {
    echo -e "${BLUE}🔄${NC} $1"
}

# Configuration
SUPERPOWERS_REPO="obra/superpowers-skills"
SUPERPOWERS_DIR="$HOME/.config/superpowers"
SUPERPOWERS_SKILLS_DIR="$SUPERPOWERS_DIR/skills"

# Main setup function
main() {
    log_info "Starting DevStream Superpowers setup"

    check_prerequisites
    setup_superpowers
    configure_devstream
    verify_installation

    log_info "Superpowers setup completed successfully!"
    echo ""
    echo "🎉 Next steps:"
    echo "   1. Restart your Claude Code session"
    echo "   2. Test with: ~/.claude/hooks/devstream/superpowers/integration_hook.sh verify"
    echo "   3. Use Superpowers skills in your DevStream workflows"
}

# Check prerequisites
check_prerequisites() {
    log_step "Checking prerequisites"

    # Check if git is available
    if ! command -v git &> /dev/null; then
        log_error "Git is required but not installed"
        exit 1
    fi

    # Check if we're in a DevStream project
    if [[ ! -f ".claude/settings.json" ]] && [[ ! -f "CLAUDE.md" ]]; then
        log_warn "Not in a DevStream project directory"
        echo "   Consider running this from a DevStream project root"
    fi

    log_info "Prerequisites check passed"
}

# Setup Superpowers
setup_superpowers() {
    log_step "Setting up Superpowers"

    # Create superpowers directory
    mkdir -p "$SUPERPOWERS_DIR"

    # Clone or update skills repository
    if [[ -d "$SUPERPOWERS_SKILLS_DIR/.git" ]]; then
        log_info "Updating existing Superpowers skills repository"
        cd "$SUPERPOWERS_SKILLS_DIR"
        git pull origin main || git pull origin master || {
            log_warn "Could not update repository, using existing version"
        }
        cd - > /dev/null
    else
        log_info "Cloning Superpowers skills repository"
        git clone "https://github.com/$SUPERPOWERS_REPO.git" "$SUPERPOWERS_SKILLS_DIR"
    fi

    # Set up remotes
    cd "$SUPERPOWERS_SKILLS_DIR"

    # Add upstream remote if not exists
    if ! git remote | grep -q "upstream"; then
        git remote add upstream "https://github.com/$SUPERPOWERS_REPO.git"
    fi

    cd - > /dev/null

    log_info "Superpowers skills repository setup completed"
}

# Configure DevStream
configure_devstream() {
    log_step "Configuring DevStream for Superpowers integration"

    # Create DevStream environment file if not exists
    local env_file=".env.devstream"

    if [[ -f "$env_file" ]]; then
        # Check if Superpowers config already exists
        if grep -q "DEVSTREAM_SUPERPOWERS_ENABLED" "$env_file"; then
            log_info "Superpowers configuration already exists in $env_file"
        else
            # Append Superpowers configuration
            cat >> "$env_file" << 'EOF'

# ============================================================================
# SUPERPOWERS INTEGRATION (DevStream Auto-Setup)
# ============================================================================

# Enable Superpowers integration with DevStream
DEVSTREAM_SUPERPOWERS_ENABLED=true

# Superpowers skills root directory
DEVSTREAM_SUPERPOWERS_SKILLS_ROOT=$HOME/.config/superpowers/skills

# Enable auto-suggestion of Superpowers skills
DEVSTREAM_SUPERPOWERS_AUTO_SUGGEST=true

# Enable Superpowers context injection
DEVSTREAM_SUPERPOWERS_CONTEXT_INJECTION=true

# Maximum tokens for Superpowers context injection
DEVSTREAM_SUPERPOWERS_TOKEN_LIMIT=1000

# Enable Superpowers integration with Agent System
DEVSTREAM_SUPERPOWERS_AGENT_INTEGRATION=true

# Enable Superpowers brainstorming enhancement
DEVSTREAM_SUPERPOWERS_BRAINSTORM_ENHANCEMENT=true

# Enable Superpowers planning enhancement
DEVSTREAM_SUPERPOWERS_PLANNING_ENHANCEMENT=true
EOF
            log_info "Superpowers configuration added to $env_file"
        fi
    else
        log_warn "$env_file not found. Creating basic configuration..."
        cat > "$env_file" << 'EOF'
# DevStream Environment Configuration

# ============================================================================
# SUPERPOWERS INTEGRATION (DevStream Auto-Setup)
# ============================================================================

# Enable Superpowers integration with DevStream
DEVSTREAM_SUPERPOWERS_ENABLED=true

# Superpowers skills root directory
DEVSTREAM_SUPERPOWERS_SKILLS_ROOT=$HOME/.config/superpowers/skills

# Enable auto-suggestion of Superpowers skills
DEVSTREAM_SUPERPOWERS_AUTO_SUGGEST=true

# Enable Superpowers context injection
DEVSTREAM_SUPERPOWERS_CONTEXT_INJECTION=true

# Maximum tokens for Superpowers context injection
DEVSTREAM_SUPERPOWERS_TOKEN_LIMIT=1000

# Enable Superpowers integration with Agent System
DEVSTREAM_SUPERPOWERS_AGENT_INTEGRATION=true

# Enable Superpowers brainstorming enhancement
DEVSTREAM_SUPERPOWERS_BRAINSTORM_ENHANCEMENT=true

# Enable Superpowers planning enhancement
DEVSTREAM_SUPERPOWERS_PLANNING_ENHANCEMENT=true
EOF
        log_info "Created $env_file with Superpowers configuration"
    fi

    log_info "DevStream configuration completed"
}

# Verify installation
verify_installation() {
    log_step "Verifying Superpowers installation"

    # Check if Superpowers directory exists
    if [[ ! -d "$SUPERPOWERS_SKILLS_DIR" ]]; then
        log_error "Superpowers skills directory not found"
        exit 1
    fi

    # Check for essential scripts
    local find_skills="$SUPERPOWERS_SKILLS_DIR/skills/using-skills/find-skills"
    local skill_run="$SUPERPOWERS_SKILLS_DIR/skills/using-skills/skill-run"

    if [[ -f "$find_skills" ]] && [[ -f "$skill_run" ]]; then
        log_info "Essential Superpowers scripts found"
    else
        log_warn "Some essential scripts may be missing"
    fi

    # Test integration hook
    local integration_hook=".claude/hooks/devstream/superpowers/integration_hook.sh"

    if [[ -f "$integration_hook" ]]; then
        log_info "Integration hook found, testing..."

        # Make sure it's executable
        chmod +x "$integration_hook"

        # Test verification
        if "$integration_hook" verify > /dev/null 2>&1; then
            log_info "Integration hook verification passed"
        else
            log_warn "Integration hook verification had issues"
        fi
    else
        log_warn "Integration hook not found at $integration_hook"
    fi

    # Show available skill categories
    echo ""
    echo "📚 Available Superpowers categories:"
    find "$SUPERPOWERS_SKILLS_DIR/skills" -maxdepth 1 -type d -not -path "$SUPERPOWERS_SKILLS_DIR/skills" 2>/dev/null | \
        sed 's|.*/||' | sort | while read -r category; do
        echo "   📂 $category"
        done || log_warn "Could not list skill categories"

    log_info "Installation verification completed"
}

# Handle script arguments
case "${1:-}" in
    "--help"|"-h")
        echo "DevStream Superpowers Setup Script"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h    Show this help message"
        echo "  --verify      Only verify existing installation"
        echo "  --clean       Clean up Superpowers installation"
        echo ""
        exit 0
        ;;
    "--verify")
        log_info "Verifying existing Superpowers installation"
        if [[ -d "$SUPERPOWERS_SKILLS_DIR" ]]; then
            verify_installation
        else
            log_error "Superpowers not installed. Run without arguments to install."
            exit 1
        fi
        exit 0
        ;;
    "--clean")
        log_step "Cleaning up Superpowers installation"
        if [[ -d "$SUPERPOWERS_DIR" ]]; then
            rm -rf "$SUPERPOWERS_DIR"
            log_info "Superpowers directory removed"
        else
            log_info "Superpowers directory not found"
        fi
        log_info "Cleanup completed"
        exit 0
        ;;
    "")
        # Default behavior - full setup
        main
        ;;
    *)
        log_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac