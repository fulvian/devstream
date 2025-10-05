#!/bin/bash
# Test z.ai API Connection
# Usage: ./test_zai_connection.sh YOUR_API_KEY

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check API key argument
if [ -z "$1" ]; then
    echo -e "${RED}❌ Usage: ./test_zai_connection.sh YOUR_API_KEY${NC}"
    exit 1
fi

API_KEY="$1"
BASE_URL="https://api.z.ai/api/anthropic"

echo -e "${YELLOW}🔍 Testing z.ai API Connection...${NC}"
echo ""

# Test API call using curl
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/v1/messages" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "glm-4.6",
    "max_tokens": 100,
    "messages": [
      {
        "role": "user",
        "content": "Rispondi solo con: Connessione z.ai funzionante!"
      }
    ]
  }')

# Extract HTTP status code (last line)
HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo -e "${YELLOW}HTTP Status: ${HTTP_CODE}${NC}"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Connessione z.ai RIUSCITA!${NC}"
    echo ""
    echo -e "${GREEN}📝 Risposta API:${NC}"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    echo ""
    echo -e "${GREEN}🎯 Provider z.ai pronto per l'uso con Claude Code${NC}"
    exit 0
else
    echo -e "${RED}❌ Connessione z.ai FALLITA${NC}"
    echo ""
    echo -e "${RED}📝 Errore API:${NC}"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    echo ""
    echo -e "${YELLOW}💡 Verifica:${NC}"
    echo "   1. Chiave API corretta (https://z.ai/manage-apikey/apikey-list)"
    echo "   2. Credito disponibile nell'account z.ai"
    echo "   3. Connessione internet attiva"
    exit 1
fi
