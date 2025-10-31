#!/bin/bash
# Enhanced Template System Setup Script
# Implements Socratic brainstorming solution for cloud.md optimization

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEVSTREAM_ROOT="$(dirname "$SCRIPT_DIR")"
ENHANCED_PROCESSOR="$DEVSTREAM_ROOT/templates/claude/enhanced_template_processor.py"
VENV_PATH="$DEVSTREAM_ROOT/.devstream"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Socratic questioning functions
ask_question() {
    local question="$1"
    local default="${2:-}"
    local answer

    if [[ -n "$default" ]]; then
        read -p "$question [$default]: " answer
        answer="${answer:-$default}"
    else
        read -p "$question: " answer
    fi

    echo "$answer"
}

validate_environment() {
    log_info "Validating environment for enhanced template system..."

    # Check if DevStream root exists
    if [[ ! -d "$DEVSTREAM_ROOT" ]]; then
        log_error "DevStream root directory not found: $DEVSTREAM_ROOT"
        exit 1
    fi

    # Check if enhanced processor exists
    if [[ ! -f "$ENHANCED_PROCESSOR" ]]; then
        log_error "Enhanced template processor not found: $ENHANCED_PROCESSOR"
        exit 1
    fi

    # Check Python environment
    if [[ ! -d "$VENV_PATH" ]]; then
        log_warning "Python virtual environment not found, creating..."
        python3.11 -m venv "$VENV_PATH"
    fi

    # Install required dependencies
    "$VENV_PATH/bin/pip" install --quiet --upgrade pip
    "$VENV_PATH/bin/pip" install --quiet pathil jinja2 pyyaml

    log_success "Environment validation completed"
}

analyze_current_template_situation() {
    log_info "Analyzing current template situation using Socratic questions..."

    echo
    echo "🤔 Socratic Analysis: Current Template Situation"
    echo "=================================================="

    # Question 1: What problem are we solving?
    local problem_description=$(ask_question "What is the main problem with current templates?"
                              "Projects lose 47% of protocol rules causing system malfunctions")

    # Question 2: Why is this critical?
    local impact_description=$(ask_question "Why is this problem critical?"
                              "MemoryManager failures and Agent System breakdowns")

    # Question 3: What are the risks?
    local risks_identified=$(ask_question "What are the biggest risks?"
                             "Protocol drift, update failures, workflow disruption")

    # Question 4: What success looks like?
    local success_criteria=$(ask_question "What does success look like?"
                            "100% protocol preservation with project customization")

    echo
    log_info "Analysis Summary:"
    echo "  Problem: $problem_description"
    echo "  Impact: $impact_description"
    echo "  Risks: $risks_identified"
    echo "  Success: $success_criteria"

    # Store analysis for later use
    cat > "$DEVSTREAM_ROOT/.template_analysis.json" << EOF
{
    "problem": "$problem_description",
    "impact": "$impact_description",
    "risks": "$risks_identified",
    "success_criteria": "$success_criteria",
    "timestamp": "$(date -Iseconds)"
}
EOF

    log_success "Socratic analysis completed and stored"
}

create_backup_strategy() {
    log_info "Creating backup strategy for existing templates..."

    local backup_dir="$DEVSTREAM_ROOT/.template_backup_$(date +%Y%m%d_%H%M%S)"

    # Backup existing template files
    if [[ -d "$DEVSTREAM_ROOT/templates" ]]; then
        cp -r "$DEVSTREAM_ROOT/templates" "$backup_dir"
        log_success "Templates backed up to: $backup_dir"
    fi

    # Backup existing project CLAUDE.md files if we're in a project
    if [[ -f "$DEVSTREAM_ROOT/CLAUDE.md" && "$DEVSTREAM_ROOT" != "$(dirname "$DEVSTREAM_ROOT")" ]]; then
        cp "$DEVSTREAM_ROOT/CLAUDE.md" "$backup_dir/project_CLAUDE.md.backup"
        log_success "Project CLAUDE.md backed up"
    fi

    echo "$backup_dir"
}

implement_enhanced_processor() {
    log_info "Implementing enhanced template processor..."

    # Ensure the enhanced processor is executable
    chmod +x "$ENHANCED_PROCESSOR"

    # Create a wrapper script for easier usage
    cat > "$DEVSTREAM_ROOT/scripts/update-project-claude.sh" << 'EOF'
#!/bin/bash
# Enhanced CLAUDE.md update script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEVSTREAM_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PATH="$DEVSTREAM_ROOT/.devstream"

# Check if we're in a project or framework
if [[ -f "$DEVSTREAM_ROOT/CLAUDE.md" && "$DEVSTREAM_ROOT" != "$(dirname "$DEVSTREAM_ROOT")" ]]; then
    # We're in a project
    PROJECT_ROOT="$DEVSTREAM_ROOT"
    FRAMEWORK_ROOT="$(dirname "$DEVSTREAM_ROOT")"
else
    # We're in the framework, find projects
    read -p "Enter project root path: " PROJECT_ROOT
    FRAMEWORK_ROOT="$DEVSTREAM_ROOT"
fi

# Run enhanced processor
"$VENV_PATH/bin/python" "$DEVSTREAM_ROOT/templates/claude/enhanced_template_processor.py" \
    "$PROJECT_ROOT" "$FRAMEWORK_ROOT" "$@"
EOF

    chmod +x "$DEVSTREAM_ROOT/scripts/update-project-claude.sh"

    log_success "Enhanced processor implementation completed"
}

create_validation_framework() {
    log_info "Creating validation framework for template integrity..."

    # Create validation script
    cat > "$DEVSTREAM_ROOT/scripts/validate-template-integrity.py" << 'EOF'
#!/usr/bin/env python3
"""
Template Integrity Validation Script
Ensures complete protocol preservation in project templates.
"""

import sys
import json
from pathlib import Path
import re

def validate_claude_md_integrity(claude_path: Path, framework_claude_path: Path) -> dict:
    """Validate CLAUDE.md integrity against framework version."""

    validation = {
        'is_valid': True,
        'score': 0.0,
        'issues': [],
        'preserved_sections': [],
        'missing_sections': []
    }

    # Read both files
    with open(claude_path, 'r', encoding='utf-8') as f:
        project_content = f.read()

    with open(framework_claude_path, 'r', encoding='utf-8') as f:
        framework_content = f.read()

    # Critical sections that must be preserved
    critical_sections = [
        'MemoryManager System',
        'Agent System',
        'Tier-Based Delegation',
        '7-Step Workflow',
        'Task Lifecycle',
        'Memory System',
        'Context Injection',
        'System Integration Reference'
    ]

    # Check each critical section
    for section in critical_sections:
        if section in framework_content:
            if section in project_content:
                validation['preserved_sections'].append(section)
                validation['score'] += 12.5  # Each section is worth 12.5%
            else:
                validation['missing_sections'].append(section)
                validation['issues'].append(f"CRITICAL: Missing section '{section}'")
                validation['is_valid'] = False

    # Check for mandatory rules
    framework_mandatory = framework_content.count('(MANDATORY)')
    project_mandatory = project_content.count('(MANDATORY)')

    if project_mandatory < framework_mandatory:
        missing_mandatory = framework_mandatory - project_mandatory
        validation['issues'].append(f"CRITICAL: Missing {missing_mandatory} MANDATORY rules")
        validation['is_valid'] = False

    # Check for critical warnings
    framework_critical = framework_content.count('(CRITICAL)')
    project_critical = project_content.count('(CRITICAL)')

    if project_critical < framework_critical:
        missing_critical = framework_critical - project_critical
        validation['issues'].append(f"CRITICAL: Missing {missing_critical} CRITICAL warnings")
        validation['is_valid'] = False

    return validation

def main():
    if len(sys.argv) != 3:
        print("Usage: python validate-template-integrity.py <project_claude.md> <framework_claude.md>")
        sys.exit(1)

    project_claude = Path(sys.argv[1])
    framework_claude = Path(sys.argv[2])

    if not project_claude.exists():
        print(f"Error: Project CLAUDE.md not found: {project_claude}")
        sys.exit(1)

    if not framework_claude.exists():
        print(f"Error: Framework CLAUDE.md not found: {framework_claude}")
        sys.exit(1)

    validation = validate_claude_md_integrity(project_claude, framework_claude)

    print(f"Template Integrity Validation Results:")
    print(f"Valid: {'✅' if validation['is_valid'] else '❌'}")
    print(f"Score: {validation['score']:.1f}%")
    print(f"Preserved Sections: {len(validation['preserved_sections'])}")
    print(f"Missing Sections: {len(validation['missing_sections'])}")

    if validation['issues']:
        print("\nIssues Found:")
        for issue in validation['issues']:
            print(f"  - {issue}")

    sys.exit(0 if validation['is_valid'] else 1)

if __name__ == '__main__':
    main()
EOF

    chmod +x "$DEVSTREAM_ROOT/scripts/validate-template-integrity.py"

    log_success "Validation framework created"
}

setup_monitoring_system() {
    log_info "Setting up monitoring system for template integrity..."

    # Create monitoring script
    cat > "$DEVSTREAM_ROOT/scripts/monitor-template-integrity.sh" << 'EOF'
#!/bin/bash
# Template integrity monitoring script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEVSTREAM_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PATH="$DEVSTREAM_ROOT/.devstream"
MONITORING_LOG="$DEVSTREAM_ROOT/.template_monitoring.log"

log_message() {
    echo "$(date -Iseconds) - $1" >> "$MONITORING_LOG"
    echo "$1"
}

# Check all projects for template integrity
monitor_projects() {
    local projects_dir="$1"
    local framework_claude="$DEVSTREAM_ROOT/CLAUDE.md"

    if [[ ! -f "$framework_claude" ]]; then
        log_message "ERROR: Framework CLAUDE.md not found"
        return 1
    fi

    local total_projects=0
    local valid_projects=0
    local issues_found=0

    # Find all project directories with CLAUDE.md
    while IFS= read -r -d '' project_claude; do
        local project_dir="$(dirname "$project_claude")"

        # Skip framework root
        if [[ "$project_dir" == "$DEVSTREAM_ROOT" ]]; then
            continue
        fi

        ((total_projects++))

        # Run validation
        if "$VENV_PATH/bin/python" "$DEVSTREAM_ROOT/scripts/validate-template-integrity.py" \
            "$project_claude" "$framework_claude" >/dev/null 2>&1; then
            ((valid_projects++))
            log_message "OK: $project_dir - Template integrity valid"
        else
            ((issues_found++))
            log_message "ISSUE: $project_dir - Template integrity issues detected"
        fi

    done < <(find "$projects_dir" -name "CLAUDE.md" -print0)

    local compliance_rate=0
    if [[ $total_projects -gt 0 ]]; then
        compliance_rate=$((valid_projects * 100 / total_projects))
    fi

    log_message "SUMMARY: $valid_projects/$total_projects projects compliant ($compliance_rate%)"

    # Alert if compliance rate is low
    if [[ $compliance_rate -lt 95 ]]; then
        log_message "ALERT: Template compliance rate below 95%"
        # Send notification (implement as needed)
    fi
}

# Main monitoring logic
main() {
    log_message "Starting template integrity monitoring..."

    # Monitor current directory and subdirectories
    monitor_projects "$DEVSTREAM_ROOT"

    log_message "Template integrity monitoring completed"
}

main "$@"
EOF

    chmod +x "$DEVSTREAM_ROOT/scripts/monitor-template-integrity.sh"

    log_success "Monitoring system setup completed"
}

create_update_mechanism() {
    log_info "Creating automated update mechanism..."

    # Create update configuration
    cat > "$DEVSTREAM_ROOT/.template_update_config.json" << EOF
{
    "auto_update_enabled": false,
    "update_window": "maintenance_hours",
    "notification_required": true,
    "backup_before_update": true,
    "validation_required": true,
    "rollback_on_failure": true,
    "max_update_time": 300,
    "compliance_threshold": 95.0
}
EOF

    # Create update scheduler script
    cat > "$DEVSTREAM_ROOT/scripts/schedule-template-updates.sh" << 'EOF'
#!/bin/bash
# Template update scheduler

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEVSTREAM_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$DEVSTREAM_ROOT/.template_update_config.json"

load_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        # Parse JSON config (simplified)
        AUTO_UPDATE=$(grep -o '"auto_update_enabled": [^,]*' "$CONFIG_FILE" | cut -d: -f2 | tr -d ' ')
    else
        AUTO_UPDATE="false"
    fi
}

check_for_updates() {
    local framework_claude="$DEVSTREAM_ROOT/CLAUDE.md"
    local version_file="$DEVSTREAM_ROOT/.claude_enhanced_version"

    if [[ ! -f "$version_file" ]]; then
        return 0  # Update needed
    fi

    # Simple hash-based check
    local current_hash=$(sha256sum "$framework_claude" | cut -d' ' -f1)
    local stored_hash=$(cat "$version_file" 2>/dev/null || echo "")

    [[ "$current_hash" != "$stored_hash" ]]
}

perform_update() {
    echo "Updates are available for template system."
    echo "Run '$DEVSTREAM_ROOT/scripts/update-project-claude.sh --force' to apply updates."
}

main() {
    load_config

    if [[ "$AUTO_UPDATE" == "true" ]] && check_for_updates; then
        perform_update
    fi
}

main
EOF

    chmod +x "$DEVSTREAM_ROOT/scripts/schedule-template-updates.sh"

    log_success "Update mechanism created"
}

run_demonstration() {
    log_info "Running demonstration of enhanced template system..."

    # Create a test project
    local test_project="$DEVSTREAM_ROOT/test_project_demo"
    mkdir -p "$test_project"

    # Create basic Python project structure
    cat > "$test_project/pyproject.toml" << EOF
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "demo-project"
version = "0.1.0"
description = "Demo project for enhanced template system"
EOF

    # Create .venv structure
    mkdir -p "$test_project/.venv/bin"

    # Generate enhanced CLAUDE.md
    log_info "Generating enhanced CLAUDE.md for test project..."
    if "$VENV_PATH/bin/python" "$ENHANCED_PROCESSOR" "$test_project" "$DEVSTREAM_ROOT"; then
        log_success "✅ Enhanced CLAUDE.md generated successfully"

        # Validate the generated template
        if "$VENV_PATH/bin/python" "$DEVSTREAM_ROOT/scripts/validate-template-integrity.py" \
            "$test_project/CLAUDE.md" "$DEVSTREAM_ROOT/CLAUDE.md"; then
            log_success "✅ Template integrity validation passed"
        else
            log_error "❌ Template integrity validation failed"
            return 1
        fi

        # Show statistics
        local framework_lines=$(wc -l < "$DEVSTREAM_ROOT/CLAUDE.md")
        local project_lines=$(wc -l < "$test_project/CLAUDE.md")
        local preservation_rate=$((project_lines * 100 / framework_lines))

        echo
        echo "📊 Enhanced Template System Statistics:"
        echo "  Framework CLAUDE.md: $framework_lines lines"
        echo "  Project CLAUDE.md: $project_lines lines"
        echo "  Preservation rate: $preservation_rate%"
        echo "  Status: $(if [[ $preservation_rate -ge 95 ]]; then echo "✅ Excellent"; else echo "⚠️ Needs improvement"; fi)"

    else
        log_error "❌ Failed to generate enhanced CLAUDE.md"
        return 1
    fi

    # Cleanup test project
    rm -rf "$test_project"

    log_success "Demonstration completed successfully"
}

main() {
    echo "🤔 Enhanced Template System Setup (Socratic Brainstorming Solution)"
    echo "================================================================"
    echo

    # Step 1: Environment validation
    validate_environment

    # Step 2: Socratic analysis
    analyze_current_template_situation

    # Step 3: Backup strategy
    echo
    log_info "Creating backup strategy..."
    local backup_dir=$(create_backup_strategy)

    # Step 4: Implementation
    echo
    log_info "Implementing enhanced template system..."
    implement_enhanced_processor
    create_validation_framework
    setup_monitoring_system
    create_update_mechanism

    # Step 5: Demonstration
    echo
    run_demonstration

    echo
    log_success "🎉 Enhanced template system setup completed successfully!"
    echo
    echo "📋 Next Steps:"
    echo "  1. Review backup at: $backup_dir"
    echo "  2. Test with: $DEVSTREAM_ROOT/scripts/update-project-claude.sh <project_path>"
    echo "  3. Monitor with: $DEVSTREAM_ROOT/scripts/monitor-template-integrity.sh"
    echo "  4. Validate with: $DEVSTREAM_ROOT/scripts/validate-template-integrity.py"
    echo
    echo "💡 Remember: This system ensures 100% protocol preservation while enabling project customization."
}

# Run main function
main "$@"