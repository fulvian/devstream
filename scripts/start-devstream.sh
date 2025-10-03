#!/bin/bash

# start-devstream.sh - Multi-Provider LLM Launcher for Claude Code
# Usage: ./scripts/start-devstream.sh [provider]
# Providers: z.ai|zai, synthetic, nanogpt, openrouter, anthropic (default)

# 2.1 - Skeleton & Error Handling
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project root detection
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 2.2 - Provider Selection Logic
PROVIDER="${1:-${DEVSTREAM_LLM_PROVIDER:-anthropic}}"

# Normalize provider name (handle aliases)
case "${PROVIDER}" in
    z.ai|zai)
        PROVIDER="z.ai"
        ;;
    synthetic)
        PROVIDER="synthetic"
        ;;
    nanogpt)
        echo -e "${RED}❌ Error: nanogpt provider not yet implemented (Phase 2)${NC}"
        echo -e "${YELLOW}Available providers: z.ai, synthetic, anthropic${NC}"
        exit 1
        ;;
    openrouter)
        echo -e "${RED}❌ Error: openrouter provider not yet implemented (Phase 2)${NC}"
        echo -e "${YELLOW}Available providers: z.ai, synthetic, anthropic${NC}"
        exit 1
        ;;
    anthropic|*)
        PROVIDER="anthropic"
        ;;
esac

# 2.3 - Validation Functions

# Validate API key is present
validate_api_key() {
    local key_name="$1"
    local key_value="$2"

    if [ -z "${key_value}" ]; then
        echo -e "${RED}❌ Error: ${key_name} is not set${NC}"
        echo -e "${YELLOW}Please configure ${key_name} in .env.llm-providers or .env${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ ${key_name} validated${NC}"
}

# Test Synthetic API connectivity
test_synthetic_api() {
    local base_url="$1"
    local api_key="$2"

    echo -e "${YELLOW}Testing Synthetic API connectivity...${NC}"

    # Minimal test payload
    local response_code
    response_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "${base_url}/messages" \
        -H "Content-Type: application/json" \
        -H "x-api-key: ${api_key}" \
        -d '{
            "model": "hf:zai-org/GLM-4.6",
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "test"}]
        }' \
        --connect-timeout 10 \
        --max-time 15 2>/dev/null || echo "000")

    # Accept 200 (success), 401 (auth error but reachable), 400 (bad request but reachable)
    case "${response_code}" in
        200|401|400)
            echo -e "${GREEN}✅ Synthetic API is reachable (HTTP ${response_code})${NC}"
            return 0
            ;;
        000)
            echo -e "${RED}❌ Error: Cannot reach Synthetic API (connection timeout/failed)${NC}"
            echo -e "${YELLOW}Check your network connection and SYNTHETIC_BASE_URL${NC}"
            exit 1
            ;;
        *)
            echo -e "${RED}❌ Error: Synthetic API returned unexpected status (HTTP ${response_code})${NC}"
            echo -e "${YELLOW}This may indicate a server issue${NC}"
            exit 1
            ;;
    esac
}

# 2.4 - Provider Configuration & Claude Code Launcher

echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  DevStream Multi-Provider LLM Launcher${NC}"
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo ""

case "${PROVIDER}" in
    z.ai)
        echo -e "${YELLOW}Loading z.ai configuration...${NC}"

        # Load from .env.llm-providers
        if [ -f "${PROJECT_ROOT}/.env.llm-providers" ]; then
            # shellcheck source=/dev/null
            source "${PROJECT_ROOT}/.env.llm-providers"
        else
            echo -e "${RED}❌ Error: .env.llm-providers not found${NC}"
            echo -e "${YELLOW}Run: cp .env.llm-providers.example .env.llm-providers${NC}"
            exit 1
        fi

        # Validate API key
        validate_api_key "ZAI_API_KEY" "${ZAI_API_KEY:-}"

        # Export for Claude Code
        export ANTHROPIC_BASE_URL="${ZAI_BASE_URL}"
        export ANTHROPIC_AUTH_TOKEN="${ZAI_API_KEY}"

        # Output configuration
        echo ""
        echo -e "${GREEN}✅ Provider: z.ai (GLM Models)${NC}"
        echo -e "${GREEN}   Base URL: ${ZAI_BASE_URL}${NC}"
        echo -e "${GREEN}   Model Mappings:${NC}"
        echo -e "${GREEN}     • claude-opus-4-5     → glm-4.6${NC}"
        echo -e "${GREEN}     • claude-sonnet-4-5   → glm-4.6${NC}"
        echo -e "${GREEN}     • claude-haiku-4-5    → glm-4-flash${NC}"
        echo ""
        ;;

    synthetic)
        echo -e "${YELLOW}Loading Synthetic configuration...${NC}"

        # Source .env from project root
        if [ -f "${PROJECT_ROOT}/.env" ]; then
            # shellcheck source=/dev/null
            source "${PROJECT_ROOT}/.env"
        else
            echo -e "${RED}❌ Error: .env not found in project root${NC}"
            exit 1
        fi

        # Load .env.llm-providers for base URL
        if [ -f "${PROJECT_ROOT}/.env.llm-providers" ]; then
            # shellcheck source=/dev/null
            source "${PROJECT_ROOT}/.env.llm-providers"
        else
            echo -e "${RED}❌ Error: .env.llm-providers not found${NC}"
            exit 1
        fi

        # Validate API key
        validate_api_key "SYNTHETIC_API_KEY" "${SYNTHETIC_API_KEY:-}"

        # Test API connectivity
        test_synthetic_api "${SYNTHETIC_BASE_URL}" "${SYNTHETIC_API_KEY}"

        # Export for Claude Code
        export ANTHROPIC_BASE_URL="${SYNTHETIC_BASE_URL}"
        export ANTHROPIC_AUTH_TOKEN="${SYNTHETIC_API_KEY}"

        # Output configuration
        echo ""
        echo -e "${GREEN}✅ Provider: Synthetic.new${NC}"
        echo -e "${GREEN}   Base URL: ${SYNTHETIC_BASE_URL}${NC}"
        echo -e "${GREEN}   Model: claude-sonnet-4-5 (Synthetic)${NC}"
        echo -e "${GREEN}   Tier: ${SYNTHETIC_TIER:-free}${NC}"
        echo ""
        ;;

    anthropic)
        echo -e "${YELLOW}Using Anthropic (default)...${NC}"

        # Validate ANTHROPIC_API_KEY from environment
        if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
            echo -e "${RED}❌ Error: ANTHROPIC_API_KEY not set${NC}"
            echo -e "${YELLOW}Export ANTHROPIC_API_KEY or use alternative provider${NC}"
            exit 1
        fi

        # No base URL override needed
        echo ""
        echo -e "${GREEN}✅ Provider: Anthropic (Official)${NC}"
        echo -e "${GREEN}   Using native Claude API${NC}"
        echo ""
        ;;
esac

# Launch Claude Code
echo -e "${GREEN}Launching Claude Code...${NC}"
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo ""

cd "${PROJECT_ROOT}"
claude
