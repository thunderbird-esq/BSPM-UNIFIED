#!/bin/bash
# GBStudio Health Check Script
# Usage: ./health_check.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

FAILED=0

check_service() {
    local service=$1
    local check_command=$2
    local description=$3

    echo -n "Checking $description... "

    if eval "$check_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

echo "========================================"
echo "GBStudio Health Check"
echo "========================================"
echo ""

# Check Docker
check_service "docker" "docker info" "Docker daemon"

# Check backend instances
for i in 1 2 3; do
    if docker ps | grep -q "gbstudio_backend_$i"; then
        check_service "backend_$i" \
            "curl -f -s -o /dev/null http://localhost:800$i/health" \
            "Backend instance $i"
    fi
done

# Check PostgreSQL
check_service "postgres" \
    "docker exec gbstudio_postgres pg_isready -U gbstudio_prod" \
    "PostgreSQL database"

# Check Redis
check_service "redis" \
    "docker exec gbstudio_redis redis-cli ping | grep -q PONG" \
    "Redis cache"

# Check ComfyUI
check_service "comfyui" \
    "curl -f -s -o /dev/null http://localhost:8188/system_stats" \
    "ComfyUI service"

# Check Ollama (if running in container)
if docker ps | grep -q "gbstudio_ollama"; then
    check_service "ollama" \
        "docker exec gbstudio_ollama ollama list" \
        "Ollama LLM service"
else
    # Check host Ollama
    check_service "ollama" \
        "curl -f -s -o /dev/null http://localhost:11434/api/tags" \
        "Ollama LLM service (host)"
fi

# Check Nginx (if running)
if systemctl is-active --quiet nginx 2>/dev/null; then
    check_service "nginx" \
        "systemctl is-active --quiet nginx" \
        "Nginx web server"
fi

# Check disk space
echo -n "Checking disk space... "
DISK_USAGE=$(df -h /data 2>/dev/null | awk 'NR==2 {print $5}' | sed 's/%//' || echo "100")
if [ "$DISK_USAGE" -lt 85 ]; then
    echo -e "${GREEN}✓${NC} ($DISK_USAGE% used)"
else
    echo -e "${YELLOW}⚠${NC} ($DISK_USAGE% used - warning threshold)"
    FAILED=$((FAILED + 1))
fi

# Check memory
echo -n "Checking memory usage... "
MEM_USAGE=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100.0)}')
if [ "$MEM_USAGE" -lt 90 ]; then
    echo -e "${GREEN}✓${NC} ($MEM_USAGE% used)"
else
    echo -e "${YELLOW}⚠${NC} ($MEM_USAGE% used - warning threshold)"
fi

# Check database connections
echo -n "Checking database connections... "
DB_CONN=$(docker exec gbstudio_postgres psql -U gbstudio_prod -d gbstudio_production -t -c \
    "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs || echo "999")
if [ "$DB_CONN" -lt 150 ]; then
    echo -e "${GREEN}✓${NC} ($DB_CONN connections)"
else
    echo -e "${YELLOW}⚠${NC} ($DB_CONN connections - high)"
fi

echo ""
echo "========================================"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All health checks passed ✓${NC}"
    echo "========================================"
    exit 0
else
    echo -e "${RED}$FAILED health check(s) failed ✗${NC}"
    echo "========================================"
    exit 1
fi
