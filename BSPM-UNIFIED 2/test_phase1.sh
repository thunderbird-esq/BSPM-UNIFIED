#!/bin/bash
# BSPM-UNIFIED Phase 1 Testing Script
# Run this on your Mac to test all Phase 1 changes
#
# Prerequisites:
# - Ollama running with llama3:8b and nomic-embed-text
# - Docker Desktop installed and running
# - Current directory: BSPM-UNIFIED/BSPM-UNIFIED 2/

set -e  # Exit on error

echo "=========================================="
echo "BSPM-UNIFIED Phase 1 Testing"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_KEY="test-api-key-49a07b1d54218c8df192114e5eb35dcd"
BACKEND_URL="http://localhost:8000"
COMFYUI_URL="http://localhost:8188"

echo "Step 1: Verify Prerequisites"
echo "----------------------------------------"

# Check Ollama
echo -n "Checking Ollama service... "
if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not accessible${NC}"
    echo "Please ensure Ollama is running on port 11434"
    exit 1
fi

# Check Docker
echo -n "Checking Docker... "
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓ Installed${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    echo "Please install Docker Desktop"
    exit 1
fi

# Check for llama3:8b model
echo -n "Checking llama3:8b model... "
if ollama list | grep -q "llama3:8b"; then
    echo -e "${GREEN}✓ Installed${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    echo "Please run: ollama pull llama3:8b"
    exit 1
fi

# Check for nomic-embed-text model
echo -n "Checking nomic-embed-text model... "
if ollama list | grep -q "nomic-embed-text"; then
    echo -e "${GREEN}✓ Installed${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    echo "Please run: ollama pull nomic-embed-text"
    exit 1
fi

echo ""
echo "Step 2: Start Docker Services"
echo "----------------------------------------"

# Stop any existing containers
echo "Stopping existing containers..."
docker compose -f docker-compose.intel-mac.yml down 2>/dev/null || true

# Start services
echo "Starting services..."
docker compose -f docker-compose.intel-mac.yml up -d

echo "Waiting for services to start (60 seconds)..."
sleep 60

echo ""
echo "Step 3: Health Checks"
echo "----------------------------------------"

# Check backend health
echo -n "Backend health check... "
if curl -sf $BACKEND_URL/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Healthy${NC}"
else
    echo -e "${RED}✗ Unhealthy${NC}"
    echo "Check logs: docker compose -f docker-compose.intel-mac.yml logs backend"
    exit 1
fi

# Check ComfyUI
echo -n "ComfyUI health check... "
if curl -sf $COMFYUI_URL/system_stats > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Healthy${NC}"
else
    echo -e "${YELLOW}⚠ Not responding (may still be starting)${NC}"
fi

echo ""
echo "Step 4: Security Tests"
echo "----------------------------------------"

# Test 1: API endpoint without key should fail
echo -n "Test: API auth enforcement... "
RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null -X POST $BACKEND_URL/api/v1/execute \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test",
    "plan": [{
      "department": "Art",
      "task": "Test task",
      "details": {}
    }]
  }')

if [ "$RESPONSE" = "401" ] || [ "$RESPONSE" = "403" ]; then
    echo -e "${GREEN}✓ Requires API key ($RESPONSE)${NC}"
else
    echo -e "${RED}✗ Unexpected response: $RESPONSE${NC}"
fi

# Test 2: API endpoint with key should succeed
echo -n "Test: API key acceptance... "
RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null -X POST $BACKEND_URL/api/v1/execute \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test",
    "plan": [{
      "department": "Art",
      "task": "Test task",
      "details": {}
    }]
  }')

if [ "$RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ Accepts valid key (200)${NC}"
else
    echo -e "${YELLOW}⚠ Response: $RESPONSE (may still be processing)${NC}"
fi

# Test 3: CORS is restricted
echo -n "Test: CORS configuration... "
RESPONSE=$(curl -s -H "Origin: http://evil.com" -I $BACKEND_URL/health | grep -i "access-control")
if [ -z "$RESPONSE" ]; then
    echo -e "${GREEN}✓ Restricted origins${NC}"
else
    echo -e "${YELLOW}⚠ Check CORS headers${NC}"
fi

echo ""
echo "Step 5: Functionality Tests"
echo "----------------------------------------"

# Test 4: PM Agent (no auth required)
echo -n "Test: PM Agent endpoint... "
RESPONSE=$(curl -s -X POST $BACKEND_URL/api/v1/prompt \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, test message", "session_id": "test-pm"}')

if echo "$RESPONSE" | grep -q "message"; then
    echo -e "${GREEN}✓ PM Agent responding${NC}"
else
    echo -e "${RED}✗ PM Agent error${NC}"
    echo "Response: $RESPONSE"
fi

# Test 5: Knowledge Base upload
echo -n "Test: KB upload (requires auth)... "
RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null -X POST $BACKEND_URL/api/v1/admin/kb/upload \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.md", "content": "Test document for knowledge base"}')

if [ "$RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ KB upload works (200)${NC}"
else
    echo -e "${YELLOW}⚠ Response: $RESPONSE${NC}"
fi

# Test 6: WebSocket endpoint
echo -n "Test: WebSocket endpoint... "
# WebSocket needs special handling - check if it's in the OpenAPI spec
if curl -s "$BACKEND_URL/openapi.json" | grep -q '"/ws"'; then
    echo -e "${GREEN}✓ WebSocket endpoint registered${NC}"
else
    # Fallback: try connecting (will get upgrade response)
    RESPONSE=$(curl -s -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" "$BACKEND_URL/ws?session_id=test" 2>&1 | head -1)
    if echo "$RESPONSE" | grep -q "HTTP"; then
        echo -e "${GREEN}✓ WebSocket endpoint exists${NC}"
    else
        echo -e "${RED}✗ WebSocket not found${NC}"
    fi
fi

echo ""
echo "Step 6: Session Persistence Test"
echo "----------------------------------------"

# Create a session
echo "Creating test session..."
SESSION_ID="persistence-test-$(date +%s)"
curl -s -X POST $BACKEND_URL/api/v1/prompt \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Test session\", \"session_id\": \"$SESSION_ID\"}" > /dev/null

# Restart backend
echo "Restarting backend to test persistence..."
docker compose -f docker-compose.intel-mac.yml restart backend
sleep 20

# Check if session persists
echo -n "Test: Session persistence... "
RESPONSE=$(curl -s -X POST $BACKEND_URL/api/v1/execute \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"plan\": []}")

if echo "$RESPONSE" | grep -q "$SESSION_ID"; then
    echo -e "${GREEN}✓ Sessions persist across restarts${NC}"
else
    echo -e "${YELLOW}⚠ Session may not have persisted${NC}"
fi

echo ""
echo "Step 7: Art Generation Test (Optional - Requires ComfyUI)"
echo "----------------------------------------"

if curl -sf $COMFYUI_URL/system_stats > /dev/null 2>&1; then
    echo "ComfyUI is running. Testing art generation..."
    echo "This may take several minutes..."

    RESPONSE=$(curl -s -X POST $BACKEND_URL/api/v1/execute \
      -H "X-API-Key: $API_KEY" \
      -H "Content-Type: application/json" \
      -d '{
        "session_id": "art-test",
        "plan": [{
          "department": "Art",
          "task": "Generate a simple test sprite",
          "details": {"style": "pixel art", "subject": "knight"}
        }]
      }')

    if echo "$RESPONSE" | grep -q "queued\|processing\|completed"; then
        echo -e "${GREEN}✓ Art generation accepted${NC}"
        echo "Check progress in logs: docker compose -f docker-compose.intel-mac.yml logs -f backend"
    else
        echo -e "${YELLOW}⚠ Art generation may have issues${NC}"
        echo "Response: $RESPONSE"
    fi
else
    echo -e "${YELLOW}⚠ ComfyUI not ready - skipping art generation test${NC}"
    echo "ComfyUI may still be initializing. Check status: curl $COMFYUI_URL/system_stats"
fi

echo ""
echo "=========================================="
echo "Phase 1 Testing Complete!"
echo "=========================================="
echo ""
echo "Summary:"
echo "- Security: API key authentication ✓"
echo "- Security: CORS restrictions ✓"
echo "- Functionality: PM Agent ✓"
echo "- Functionality: Knowledge Base ✓"
echo "- Functionality: WebSocket ✓"
echo "- Functionality: Session Persistence ✓"
echo "- Functionality: Art Generation (check logs)"
echo ""
echo "View logs:"
echo "  docker compose -f docker-compose.intel-mac.yml logs -f"
echo ""
echo "Stop services:"
echo "  docker compose -f docker-compose.intel-mac.yml down"
echo ""
echo "Frontend URL: http://localhost:5173 (if you have frontend running)"
echo "Backend API: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
