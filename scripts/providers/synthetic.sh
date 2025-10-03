#!/bin/bash
# Synthetic Provider Configuration for DevStream

# Color codes (if not already set by parent script)
RED=${RED:-'\033[0;31m'}
GREEN=${GREEN:-'\033[0;32m'}
YELLOW=${YELLOW:-'\033[1;33m'}
NC=${NC:-'\033[0m'}

# Source main envs
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ -z "$SYNTHETIC_BASE_URL" ]; then
    source "$PROJECT_ROOT/.env.llm-providers"
fi

if [ -z "$SYNTHETIC_API_KEY" ]; then
    source "$PROJECT_ROOT/.env"  # From root .env
fi

# Validate API key
if [ -z "$SYNTHETIC_API_KEY" ]; then
    echo -e "${RED}❌ Error: SYNTHETIC_API_KEY not set in .env${NC}"
    exit 1
fi

# Test API connectivity (full test for Synthetic)
echo -e "${YELLOW}🔍 Testing Synthetic API connectivity...${NC}"
http_code=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "${SYNTHETIC_BASE_URL}/messages" \
    -H "x-api-key: ${SYNTHETIC_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"model":"'"${SYNTHETIC_MODEL}"'","messages":[{"role":"user","content":"test"}],"max_tokens":1}' \
    2>/dev/null || echo "000")

if [[ "$http_code" == "200" ]] || [[ "$http_code" == "401" ]] || [[ "$http_code" == "400" ]]; then
    echo -e "${GREEN}✅ Synthetic API reachable (HTTP $http_code)${NC}"
else
    echo -e "${RED}❌ Synthetic API unreachable (HTTP $http_code)${NC}"
    exit 1
fi

# Export Anthropic-compatible env vars
export ANTHROPIC_BASE_URL="${SYNTHETIC_BASE_URL}"
export ANTHROPIC_AUTH_TOKEN="${SYNTHETIC_API_KEY}"

# Output configuration
echo -e "${GREEN}✅ Synthetic provider configured${NC}"
echo -e "${GREEN}   Base URL: ${ANTHROPIC_BASE_URL}${NC}"
echo -e "${GREEN}   Model: ${SYNTHETIC_MODEL}${NC}"
echo -e "${GREEN}   Tier: ${SYNTHETIC_TIER}${NC}"
