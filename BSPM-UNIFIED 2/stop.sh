#!/bin/bash
# GBStudio Automation Hub - Shutdown Script
# Platform: Intel Mac (x86_64) - macOS Ventura 13.x
# Docker Desktop: 4.25+
#
# Usage: ./stop.sh

set -e

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}🛑  GBStudio Automation Hub - Shutdown${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [[ ! -f "docker-compose.intel-mac.yml" ]]; then
    echo -e "${RED}❌ ERROR: docker-compose.intel-mac.yml not found${NC}"
    echo -e "   Please run this script from the project root directory"
    exit 1
fi

echo -e "${YELLOW}Stopping all services...${NC}"
echo ""

docker compose -f docker-compose.intel-mac.yml down

if [[ $? -eq 0 ]]; then
    echo ""
    echo -e "${GREEN}✅ All services stopped successfully${NC}"
    echo ""
    echo -e "   📁 Data preserved in:"
    echo -e "      - ./project_files"
    echo -e "      - ./vectorstore"
    echo -e "      - ./agent_memory"
    echo ""
    echo -e "   🔄 Restart: ${CYAN}./start.sh${NC}"
else
    echo ""
    echo -e "${RED}❌ ERROR: Failed to stop services${NC}"
    echo -e "   Try: docker compose -f docker-compose.intel-mac.yml down --remove-orphans"
    exit 1
fi

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
