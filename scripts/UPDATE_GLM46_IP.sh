#!/bin/bash
# Update GLM-4.6 Server IP in Claude Code Router Config

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🔧 GLM-4.6 IP Configuration Updater${NC}"
echo ""

# Get current IP placeholder
CURRENT_IP=$(cat ~/.claude-code-router/config.json | jq -r '.Providers[0].api_base_url' | grep -oE '[0-9]+\.[0-9X]+\.[0-9X]+\.[0-9X]+')
echo -e "${YELLOW}Current IP: ${CURRENT_IP}${NC}"

# Prompt for real IP
read -p "Enter real GLM-4.6 server IP (e.g., 192.168.12.12): " SERVER_IP

# Validate IP format
if [[ ! $SERVER_IP =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    echo -e "${RED}❌ Invalid IP format${NC}"
    exit 1
fi

# Update config
echo -e "${YELLOW}Updating configuration...${NC}"
jq --arg ip "$SERVER_IP" '.Providers[0].api_base_url = "http://\($ip):30000/v1/chat/completions"' \
    ~/.claude-code-router/config.json > /tmp/config.json
mv /tmp/config.json ~/.claude-code-router/config.json

echo -e "${GREEN}✅ Configuration updated${NC}"
echo -e "${GREEN}   New URL: http://${SERVER_IP}:30000/v1/chat/completions${NC}"
echo ""

# Test connectivity
echo -e "${YELLOW}Testing server connectivity...${NC}"
if curl -s --max-time 5 "http://${SERVER_IP}:30000/v1/models" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Server reachable${NC}"
else
    echo -e "${RED}⚠️  Server not reachable (timeout or connection refused)${NC}"
    echo -e "${YELLOW}   Check: Firewall, VPN, server status${NC}"
fi

echo ""
echo -e "${YELLOW}Restarting Claude Code Router...${NC}"
ccr restart

echo ""
echo -e "${GREEN}🎉 Configuration complete!${NC}"
echo -e "${GREEN}   Test with: ccr code${NC}"
