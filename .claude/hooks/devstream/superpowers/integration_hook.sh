#!/bin/bash
# Superpowers Integration Hook for DevStream
# Integrates obra/superpowers skills library with DevStream workflows

set -euo pipefail

# Configuration
SUPERPOWERS_ROOT="${DEVSTREAM_SUPERPOWERS_SKILLS_ROOT:-$HOME/.config/superpowers/skills}"
SUPERPOWERS_ENABLED="${DEVSTREAM_SUPERPOWERS_ENABLED:-true}"
CONTEXT_INJECTION="${DEVSTREAM_SUPERPOWERS_CONTEXT_INJECTION:-true}"
TOKEN_LIMIT="${DEVSTREAM_SUPERPOWERS_TOKEN_LIMIT:-1000}"

# Logging
log_info() {
    echo "✅ [Superpowers Hook] $1" >&2
}

log_warn() {
    echo "⚠️ [Superpowers Hook] $1" >&2
}

log_error() {
    echo "❌ [Superpowers Hook] $1" >&2
}

# Check if Superpowers is enabled
if [[ "$SUPERPOWERS_ENABLED" != "true" ]]; then
    log_info "Superpowers integration disabled"
    exit 0
fi

# Check if Superpowers directory exists
if [[ ! -d "$SUPERPOWERS_ROOT" ]]; then
    log_warn "Superpowers directory not found: $SUPERPOWERS_ROOT"
    exit 0
fi

# Main function
main() {
    local operation="${1:-inject}"
    local parameter="${2:-}"

    case "$operation" in
        "inject")
            inject_superpowers_context "$parameter"
            ;;
        "suggest")
            suggest_superpowers_skills "$parameter"
            ;;
        "verify")
            verify_superpowers_installation
            ;;
        *)
            log_error "Unknown operation: $operation"
            exit 1
            ;;
    esac
}

# Inject Superpowers context
inject_superpowers_context() {
    local query="${1:-}"

    if [[ "$CONTEXT_INJECTION" != "true" ]]; then
        log_info "Context injection disabled"
        exit 0
    fi

    if [[ -z "$query" ]]; then
        log_info "No query provided for context injection"
        exit 0
    fi

    log_info "Injecting Superpowers context for query: $query"

    # Find relevant skills using the find-skills tool
    local find_skills_script="$SUPERPOWERS_ROOT/skills/using-skills/find-skills"
    if [[ -f "$find_skills_script" ]]; then
        # Search for relevant skills based on query keywords
        local relevant_skills
        relevant_skills=$(cd "$SUPERPOWERS_ROOT" && bash skills/using-skills/find-skills "$query" 2>/dev/null | head -5 || true)

        if [[ -n "$relevant_skills" ]]; then
            echo ""
            echo "# Superpowers Context"
            echo ""
            echo "$relevant_skills"
            echo ""
        else
            log_info "No relevant Superpowers skills found for query"
        fi
    else
        log_warn "find-skills script not found: $find_skills_script"
    fi
}

# Suggest Superpowers skills
suggest_superpowers_skills() {
    local context="${1:-}"

    log_info "Suggesting Superpowers skills for context"

    # Basic skill suggestions based on context keywords
    if [[ "$context" =~ (test|testing|TDD) ]]; then
        echo "💡 Consider using Superpowers TDD skills: $SUPERPOWERS_ROOT/skills/testing"
    fi

    if [[ "$context" =~ (debug|debugging) ]]; then
        echo "💡 Consider using Superpowers debugging skills: $SUPERPOWERS_ROOT/skills/debugging"
    fi

    if [[ "$context" =~ (plan|planning|design) ]]; then
        echo "💡 Consider using Superpowers planning skills: $SUPERPOWERS_ROOT/skills/meta"
    fi
}

# Verify Superpowers installation
verify_superpowers_installation() {
    log_info "Verifying Superpowers installation"

    local required_scripts=(
        "skills/using-skills/find-skills"
        "skills/using-skills/skill-run"
    )

    local missing_scripts=()

    for script in "${required_scripts[@]}"; do
        if [[ ! -f "$SUPERPOWERS_ROOT/$script" ]]; then
            missing_scripts+=("$script")
        fi
    done

    if [[ ${#missing_scripts[@]} -eq 0 ]]; then
        log_info "Superpowers installation verified successfully"
        echo "✅ Superpowers ready for integration with DevStream"
    else
        log_warn "Missing Superpowers scripts:"
        for script in "${missing_scripts[@]}"; do
            echo "  ❌ $script"
        done
    fi

    # List available skill categories
    if [[ -d "$SUPERPOWERS_ROOT/skills" ]]; then
        echo ""
        echo "📚 Available Superpowers categories:"
        find "$SUPERPOWERS_ROOT/skills" -maxdepth 1 -type d -not -path "$SUPERPOWERS_ROOT/skills" | \
            sed 's|.*/||' | sort | while read -r category; do
            echo "  📂 $category"
        done
    fi
}

# Execute main function
main "$@"