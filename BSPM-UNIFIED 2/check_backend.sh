#!/bin/bash
echo "=== Checking Backend Logs ==="
docker compose -f docker-compose.intel-mac.yml logs backend --tail 30

echo ""
echo "=== Container Status ==="
docker ps -a | grep backend

echo ""
echo "=== Testing Health Endpoint ==="
sleep 10
curl -v http://localhost:8000/health 2>&1 | head -20
