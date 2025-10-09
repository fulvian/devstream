#!/bin/bash
# End-to-End Test: z.ai Provider Integration

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🧪 E2E Test: z.ai Provider Integration${NC}"
echo ""

# Test 1: Verify .env contains ZAI_API_KEY
echo -e "${YELLOW}[1/5] Testing .env configuration...${NC}"
if grep -q "^ZAI_API_KEY=" .env; then
    echo -e "${GREEN}✅ ZAI_API_KEY found in .env${NC}"
else
    echo -e "${RED}❌ ZAI_API_KEY missing in .env${NC}"
    exit 1
fi

# Test 2: Verify .env.llm-providers inheritance
echo -e "${YELLOW}[2/5] Testing .env.llm-providers inheritance...${NC}"
if grep -q 'ZAI_API_KEY=\${ZAI_API_KEY:-}' .env.llm-providers; then
    echo -e "${GREEN}✅ .env.llm-providers correctly inherits from .env${NC}"
else
    echo -e "${RED}❌ .env.llm-providers not configured for inheritance${NC}"
    exit 1
fi

# Test 3: Verify provider override mechanism
echo -e "${YELLOW}[3/5] Testing provider override mechanism...${NC}"
source .env
export DEVSTREAM_LLM_PROVIDER=z.ai
source .env.llm-providers

if [ "$ANTHROPIC_BASE_URL" = "https://api.z.ai/api/anthropic" ]; then
    echo -e "${GREEN}✅ Provider override works (Base URL: $ANTHROPIC_BASE_URL)${NC}"
else
    echo -e "${RED}❌ Provider override failed (Base URL: $ANTHROPIC_BASE_URL)${NC}"
    exit 1
fi

# Test 4: Verify API key propagation
echo -e "${YELLOW}[4/5] Testing API key propagation...${NC}"
if [ -n "$ANTHROPIC_API_KEY" ] && [ "${ANTHROPIC_API_KEY:0:10}" = "5a51efd5fd" ]; then
    echo -e "${GREEN}✅ API key correctly propagated${NC}"
else
    echo -e "${RED}❌ API key propagation failed${NC}"
    exit 1
fi

# Test 5: Test z.ai API connection
echo -e "${YELLOW}[5/5] Testing z.ai API connection...${NC}"
HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null -X POST "https://api.z.ai/api/anthropic/v1/messages" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "glm-4.6",
    "max_tokens": 10,
    "messages": [{"role": "user", "content": "Test"}]
  }')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ z.ai API connection successful (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${RED}❌ z.ai API connection failed (HTTP $HTTP_CODE)${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 All E2E tests passed!${NC}"
echo ""
echo -e "${YELLOW}✅ Ready to start Claude Code with z.ai:${NC}"
echo -e "   ./start-devstream.sh start z.ai"
