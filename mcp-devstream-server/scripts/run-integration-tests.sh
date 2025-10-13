#!/bin/bash

# MCP Server Integration Test Runner
#
# Runs comprehensive integration tests for MCP server stability fixes.
# Tests multi-instance prevention, database validation, session tracking,
# circuit breaker patterns, and health monitoring functionality.
#
# Usage: ./scripts/run-integration-tests.sh [options]
#   --quick        Run only critical tests (skip memory/long-running tests)
#   --verbose      Enable verbose output
#   --no-cleanup   Skip cleanup after tests (for debugging)
#   --help         Show this help

set -euo pipefail

# Default configuration
QUICK_MODE=false
VERBOSE=false
NO_CLEANUP=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --no-cleanup)
            NO_CLEANUP=true
            shift
            ;;
        --help)
            cat << EOF
MCP Server Integration Test Runner

Usage: $0 [options]

Options:
  --quick        Run only critical tests (skip memory/long-running tests)
  --verbose      Enable verbose output
  --no-cleanup   Skip cleanup after tests (for debugging)
  --help         Show this help

Examples:
  $0                           # Run all integration tests
  $0 --quick                   # Run only critical tests
  $0 --verbose                 # Run with verbose output

EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Use --help for usage information" >&2
            exit 1
            ;;
    esac
done

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Function to log messages
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $1${NC}"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  $1${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    # Check if Node.js is available
    if ! command -v node &> /dev/null; then
        log_error "Node.js is required but not found"
        exit 1
    fi

    # Check if npm is available
    if ! command -v npm &> /dev/null; then
        log_error "npm is required but not found"
        exit 1
    fi

    # Check if project is built
    if [[ ! -f "$PROJECT_ROOT/dist/index.js" ]]; then
        log_warning "Project not built. Building now..."
        if ! npm run build; then
            log_error "Failed to build project"
            exit 1
        fi
        log_success "Project built successfully"
    fi

    # Check for test dependencies
    if ! npm list jest &> /dev/null; then
        log_error "Jest is required for testing but not installed"
        log "Installing test dependencies..."
        if ! npm install --save-dev jest jest-junit babel-jest; then
            log_error "Failed to install test dependencies"
            exit 1
        fi
    fi

    log_success "Prerequisites check completed"
}

# Function to prepare test environment
prepare_test_environment() {
    log "Preparing test environment..."

    # Create test data directory
    mkdir -p "$PROJECT_ROOT/test-data"

    # Set environment variables for testing
    export NODE_ENV=test
    export DEVSTREAM_TEST_MODE=true

    log_success "Test environment prepared"
}

# Function to run integration tests
run_integration_tests() {
    log "Running MCP server integration tests..."

    local test_args=()
    local jest_config="$PROJECT_ROOT/jest.integration.config.js"

    # Build Jest arguments
    test_args+=("--config" "$jest_config")

    if [[ "$VERBOSE" == "true" ]]; then
        test_args+=("--verbose")
    fi

    if [[ "$QUICK_MODE" == "true" ]]; then
        test_args+=("--testNamePattern" "(?!.*Memory Management|.*Graceful Shutdown)")
        log_warning "Quick mode enabled: Skipping memory management and long-running tests"
    fi

    # Set test timeout
    test_args+=("--testTimeout" "60000")

    log "Starting integration tests with Jest..."
    log "Configuration: ${test_args[*]}"

    # Run tests
    if npx jest "${test_args[@]}"; then
        log_success "All integration tests passed!"
        return 0
    else
        log_error "Integration tests failed"
        return 1
    fi
}

# Function to cleanup test environment
cleanup_test_environment() {
    if [[ "$NO_CLEANUP" == "true" ]]; then
        log_warning "Skipping cleanup as requested"
        return
    fi

    log "Cleaning up test environment..."

    # Kill any remaining test processes
    pkill -f "node.*dist/index.js" || true
    sleep 2

    # Remove PID file
    rm -f /tmp/devstream-mcp-server.pid

    # Remove test data directory
    if [[ -d "$PROJECT_ROOT/test-data" ]]; then
        rm -rf "$PROJECT_ROOT/test-data"
    fi

    log_success "Test environment cleaned up"
}

# Function to generate test report
generate_test_report() {
    log "Generating test report..."

    local report_dir="$PROJECT_ROOT/test-results"
    local report_file="$report_dir/integration-test-summary.txt"

    mkdir -p "$report_dir"

    cat > "$report_file" << EOF
MCP Server Integration Test Summary
=====================================
Date: $(date)
Mode: $([[ "$QUICK_MODE" == "true" ]] && echo "Quick" || echo "Full")
Verbose: $([[ "$VERBOSE" == "true" ]] && echo "Yes" || echo "No")

Test Configuration:
- Project Root: $PROJECT_ROOT
- Test Directory: $PROJECT_ROOT/tests/integration
- Jest Config: $PROJECT_ROOT/jest.integration.config.js

Test Results:
$(if [[ -f "$report_dir/integration-test-results.xml" ]]; then
    echo "JUnit XML report available at: test-results/integration-test-results.xml"
else
    echo "No JUnit report generated"
fi)

Environment:
- Node.js: $(node --version)
- npm: $(npm --version)
- Platform: $(uname -s)

EOF

    log_success "Test report generated: $report_file"
}

# Main execution
main() {
    echo -e "${BLUE}🚀 MCP Server Integration Test Runner${NC}"
    echo

    # Change to project root
    cd "$PROJECT_ROOT"

    # Run test phases
    check_prerequisites
    prepare_test_environment

    # Set up cleanup trap
    trap cleanup_test_environment EXIT

    # Run tests
    if run_integration_tests; then
        generate_test_report
        echo
        log_success "Integration test execution completed successfully!"

        if [[ "$NO_CLEANUP" == "true" ]]; then
            log_warning "Test environment preserved. Run cleanup manually when done."
        fi

        exit 0
    else
        echo
        log_error "Integration test execution failed!"
        exit 1
    fi
}

# Handle interruption gracefully
trap 'echo -e "\n${YELLOW}⚠️ Test execution interrupted${NC}"; cleanup_test_environment; exit 130' INT TERM

# Run main function
main "$@"