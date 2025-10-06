#!/bin/bash
# =============================================================================
# LLM Provider Integration Test Suite (v2.0)
# =============================================================================
# Purpose: Dual subscription model testing (Anthropic Max Plan + z.ai)
# Version: 2.0.0
# Date: 2025-10-06
#
# Test Coverage:
#   5.1 - z.ai Provider Integration
#   5.2 - Anthropic Max Plan Integration
#   5.3 - Provider Switching
#   5.4 - Error Handling Validation
# =============================================================================

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Test helpers
print_header() {
    echo -e "\n${BOLD}${BLUE}===================================================${NC}"
    echo -e "${BOLD}${BLUE}$1${NC}"
    echo -e "${BOLD}${BLUE}===================================================${NC}\n"
}

print_test() {
    echo -e "${BOLD}[TEST]${NC} $1"
    ((TOTAL_TESTS++))
}

pass_test() {
    echo -e "${GREEN}  ✅ PASS${NC}: $1\n"
    ((PASSED_TESTS++))
}

fail_test() {
    echo -e "${RED}  ❌ FAIL${NC}: $1\n"
    ((FAILED_TESTS++))
}

warn_test() {
    echo -e "${YELLOW}  ⚠️  WARN${NC}: $1\n"
}

# =============================================================================
# 5.1 - z.ai Provider Integration Tests
# =============================================================================

test_zai_provider() {
    print_header "5.1 - z.ai Provider Integration Tests"

    # Test 1: Verify .env file exists
    print_test "Verify root .env file exists"
    if [ -f "$PROJECT_ROOT/.env" ]; then
        pass_test "Root .env file found"
    else
        fail_test "Missing root .env file"
        return
    fi

    # Test 2: Verify ZAI_API_KEY in .env
    print_test "Verify ZAI_API_KEY configured in .env"
    source "$PROJECT_ROOT/.env" 2>/dev/null || true

    if [ -n "${ZAI_API_KEY:-}" ]; then
        pass_test "ZAI_API_KEY found in .env"
        echo "       Key prefix: ${ZAI_API_KEY:0:10}..."
    else
        warn_test "ZAI_API_KEY not set in .env (expected if z.ai not configured)"
    fi

    # Test 3: Verify start-devstream.sh exists
    print_test "Verify start-devstream.sh launcher exists"
    if [ -x "$PROJECT_ROOT/start-devstream.sh" ]; then
        pass_test "Launcher script found and executable"
    else
        fail_test "start-devstream.sh not found or not executable"
    fi

    # Test 4: Test z.ai authentication variables
    print_test "Verify z.ai authentication uses ANTHROPIC_AUTH_TOKEN"
    # Grep for correct variable usage in start-devstream.sh
    if grep -q "ANTHROPIC_AUTH_TOKEN.*ZAI_API_KEY" "$PROJECT_ROOT/start-devstream.sh"; then
        pass_test "Correct authentication variable (AUTH_TOKEN)"
    else
        fail_test "Wrong authentication variable (should use AUTH_TOKEN, not API_KEY)"
    fi

    # Test 5: Verify z.ai BASE_URL
    print_test "Verify z.ai BASE_URL configuration"
    if grep -q "https://api.z.ai/api/anthropic" "$PROJECT_ROOT/start-devstream.sh"; then
        pass_test "z.ai BASE_URL correctly configured"
    else
        fail_test "z.ai BASE_URL not found in launcher"
    fi

    # Test 6: Verify model mapping documentation
    print_test "Verify GLM-4.6 model mapping"
    if grep -q "glm-4.6" "$PROJECT_ROOT/QUICKSTART_ZAI.md"; then
        pass_test "Model mapping documented (GLM-4.6)"
    else
        fail_test "Model mapping not documented"
    fi
}

# =============================================================================
# 5.2 - Anthropic Max Plan Integration Tests
# =============================================================================

test_anthropic_provider() {
    print_header "5.2 - Anthropic Max Plan Integration Tests"

    # Test 1: Verify claude CLI available
    print_test "Verify Claude CLI availability"
    if command -v claude >/dev/null 2>&1; then
        pass_test "Claude CLI found"
    else
        warn_test "Claude CLI not found (required for OAuth login)"
    fi

    # Test 2: Verify OAuth authentication check
    print_test "Verify OAuth authentication logic in launcher"
    if grep -q "claude auth status" "$PROJECT_ROOT/start-devstream.sh"; then
        pass_test "OAuth authentication check implemented"
    else
        fail_test "OAuth authentication check missing"
    fi

    # Test 3: Verify ALL API variables are unset for Max Plan
    print_test "Verify API variables unset for Max Plan preservation"
    if grep -q "unset ANTHROPIC_API_KEY" "$PROJECT_ROOT/start-devstream.sh" && \
       grep -q "unset ANTHROPIC_AUTH_TOKEN" "$PROJECT_ROOT/start-devstream.sh" && \
       grep -q "unset ANTHROPIC_BASE_URL" "$PROJECT_ROOT/start-devstream.sh"; then
        pass_test "All API variables correctly unset (preserves Max Plan)"
    else
        fail_test "Missing unset commands (Max Plan bypass risk)"
    fi

    # Test 4: Verify login requirement
    print_test "Verify login requirement enforcement"
    if grep -q "claude login" "$PROJECT_ROOT/start-devstream.sh"; then
        pass_test "Login requirement documented"
    else
        warn_test "Login requirement not enforced"
    fi
}

# =============================================================================
# 5.3 - Provider Switching Tests
# =============================================================================

test_provider_switching() {
    print_header "5.3 - Provider Switching Tests"

    # Test 1: Verify switch_auth_provider function exists
    print_test "Verify switch_auth_provider() function exists"
    if grep -q "switch_auth_provider()" "$PROJECT_ROOT/start-devstream.sh"; then
        pass_test "Provider switching function found"
    else
        fail_test "Provider switching function missing"
    fi

    # Test 2: Verify z.ai case in switch statement
    print_test "Verify z.ai provider case in switch statement"
    if grep -q '"z.ai")' "$PROJECT_ROOT/start-devstream.sh"; then
        pass_test "z.ai provider case found"
    else
        fail_test "z.ai provider case missing"
    fi

    # Test 3: Verify anthropic case in switch statement
    print_test "Verify anthropic provider case in switch statement"
    if grep -q '"anthropic"' "$PROJECT_ROOT/start-devstream.sh"; then
        pass_test "Anthropic provider case found"
    else
        fail_test "Anthropic provider case missing"
    fi

    # Test 4: Verify NO Synthetic references remain
    print_test "Verify Synthetic provider removed"
    if ! grep -qi "synthetic" "$PROJECT_ROOT/start-devstream.sh"; then
        pass_test "Synthetic provider successfully removed"
    else
        fail_test "Synthetic references still exist"
    fi

    # Test 5: Verify settings preservation
    print_test "Verify Claude Code settings preservation logic"
    if grep -q "configure_claude_settings_for_zai" "$PROJECT_ROOT/start-devstream.sh" && \
       grep -q "reset_claude_settings_to_default" "$PROJECT_ROOT/start-devstream.sh"; then
        pass_test "Settings management functions found"
    else
        fail_test "Settings management functions missing"
    fi
}

# =============================================================================
# 5.4 - Error Handling Validation Tests
# =============================================================================

test_error_handling() {
    print_header "5.4 - Error Handling Validation Tests"

    # Test 1: Missing ZAI_API_KEY error
    print_test "Verify missing ZAI_API_KEY error handling"
    if grep -q "ZAI_API_KEY not configured" "$PROJECT_ROOT/start-devstream.sh"; then
        pass_test "Missing z.ai API key error handled"
    else
        fail_test "Missing z.ai API key error not handled"
    fi

    # Test 2: Missing OAuth login error
    print_test "Verify missing OAuth login error handling"
    if grep -q "Not logged into Claude.ai" "$PROJECT_ROOT/start-devstream.sh"; then
        pass_test "Missing OAuth login error handled"
    else
        fail_test "Missing OAuth login error not handled"
    fi

    # Test 3: Unknown provider error
    print_test "Verify unknown provider error handling"
    if grep -q "Unknown provider" "$PROJECT_ROOT/start-devstream.sh"; then
        pass_test "Unknown provider error handled"
    else
        fail_test "Unknown provider error not handled"
    fi

    # Test 4: Help text updated
    print_test "Verify help text updated (no Synthetic)"
    if ! grep -qi "synthetic" "$PROJECT_ROOT/start-devstream.sh" 2>/dev/null; then
        pass_test "Help text cleaned (no Synthetic references)"
    else
        fail_test "Help text still contains Synthetic references"
    fi
}

# =============================================================================
# Test Runner
# =============================================================================

run_all_tests() {
    print_header "LLM Provider Integration Test Suite v2.0"
    echo "Testing Dual Subscription Model (Anthropic Max Plan + z.ai)"
    echo ""

    test_zai_provider
    test_anthropic_provider
    test_provider_switching
    test_error_handling

    # Summary
    print_header "Test Summary"
    echo -e "${BOLD}Total Tests:${NC}  $TOTAL_TESTS"
    echo -e "${GREEN}${BOLD}Passed:${NC}       $PASSED_TESTS"
    echo -e "${RED}${BOLD}Failed:${NC}       $FAILED_TESTS"

    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "\n${GREEN}${BOLD}✅ ALL TESTS PASSED!${NC}\n"
        return 0
    else
        echo -e "\n${RED}${BOLD}❌ SOME TESTS FAILED${NC}\n"
        return 1
    fi
}

# Run tests
run_all_tests
