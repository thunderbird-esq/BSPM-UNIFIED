#!/bin/bash
# GBStudio Automation Hub - Startup Script
# Platform: Intel Mac (x86_64) - macOS Ventura 13.x
# Docker Desktop: 4.25+
#
# Usage: ./start.sh
# Stop: ./stop.sh

set -e  # Exit on any error

# ANSI color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}🎮  GBStudio Automation Hub - Startup${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ============================================================================
# Pre-flight Checks
# ============================================================================

echo -e "${BLUE}[1/6]${NC} Running pre-flight checks..."

# Check architecture (compatible with both Intel and Apple Silicon)
ARCH=$(uname -m)
if [[ "$ARCH" == "x86_64" ]]; then
    echo -e "   ${GREEN}✓${NC} Architecture: x86_64 (Intel Mac)"
elif [[ "$ARCH" == "arm64" || "$ARCH" == "aarch64" ]]; then
    echo -e "   ${GREEN}✓${NC} Architecture: arm64 (Apple Silicon)"
else
    echo -e "   ${YELLOW}⚠${NC}  Architecture: ${ARCH} (untested)"
fi

# Check Docker Desktop is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ ERROR: Docker Desktop is not running${NC}"
    echo -e "   Please start Docker Desktop from Applications and try again."
    echo -e "   Path: /Applications/Docker.app"
    exit 1
fi
echo -e "   ${GREEN}✓${NC} Docker Desktop: Running"

# Check Docker Compose version
if ! docker compose version > /dev/null 2>&1; then
    echo -e "${RED}❌ ERROR: Docker Compose not available${NC}"
    echo -e "   Please install Docker Desktop 4.25 or later"
    exit 1
fi
COMPOSE_VERSION=$(docker compose version --short)
echo -e "   ${GREEN}✓${NC} Docker Compose: v${COMPOSE_VERSION}"

# Check for required files
if [[ ! -f "docker-compose.intel-mac.yml" ]]; then
    echo -e "${RED}❌ ERROR: docker-compose.intel-mac.yml not found${NC}"
    echo -e "   Please run this script from the project root directory"
    exit 1
fi
echo -e "   ${GREEN}✓${NC} Configuration files: Present"

echo ""

# ============================================================================
# Create Required Directories
# ============================================================================

echo -e "${BLUE}[2/6]${NC} Creating required directories..."

mkdir -p project_files/assets/sprites
mkdir -p project_files/assets/backgrounds
mkdir -p vectorstore
mkdir -p agent_memory/conversations
mkdir -p temp_outputs
mkdir -p frontend

echo -e "   ${GREEN}✓${NC} Directories created"
echo ""

# ============================================================================
# Start Services
# ============================================================================

echo -e "${BLUE}[3/6]${NC} Starting Docker services..."
echo -e "   ${YELLOW}Note: First run will download ~6GB of models (llama3 + nomic-embed-text)${NC}"
echo ""

docker compose -f docker-compose.intel-mac.yml up -d

if [[ $? -ne 0 ]]; then
    echo -e "${RED}❌ ERROR: Failed to start services${NC}"
    echo -e "   Check logs: docker compose -f docker-compose.intel-mac.yml logs"
    exit 1
fi

echo -e "   ${GREEN}✓${NC} Services started"
echo ""

# ============================================================================
# Wait for Health Checks
# ============================================================================

echo -e "${BLUE}[4/6]${NC} Waiting for services to become healthy..."
echo -e "   ${YELLOW}This may take 5-10 minutes on first run${NC}"
echo ""

TIMEOUT=600  # 10 minutes
ELAPSED=0
INTERVAL=5
SPINNER=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
SPINNER_INDEX=0

# Function to check if jq is available
if command -v jq &> /dev/null; then
    HAS_JQ=true
else
    HAS_JQ=false
    echo -e "   ${YELLOW}Note: jq not found, using basic status checks${NC}"
fi

while [[ $ELAPSED -lt $TIMEOUT ]]; do
    # Show spinner
    echo -ne "\r   ${SPINNER[$SPINNER_INDEX]} Checking services... (${ELAPSED}s / ${TIMEOUT}s)"
    SPINNER_INDEX=$(( (SPINNER_INDEX + 1) % 10 ))
    
    # Check backend health endpoint
    if HTTP_CODE=$(curl -s -o /tmp/health_response.json -w "%{http_code}" http://localhost:8000/health 2>/dev/null); then
        if [[ "$HTTP_CODE" == "200" ]]; then
            if [[ "$HAS_JQ" == true ]]; then
                # Parse JSON response
                BACKEND_STATUS=$(jq -r '.backend' /tmp/health_response.json 2>/dev/null || echo "unknown")
                OLLAMA_STATUS=$(jq -r '.services.ollama.status' /tmp/health_response.json 2>/dev/null || echo "unknown")
                OLLAMA_MODELS_OK=$(jq -r '.services.ollama.models_ok' /tmp/health_response.json 2>/dev/null || echo "false")
                COMFYUI_STATUS=$(jq -r '.services.comfyui.status' /tmp/health_response.json 2>/dev/null || echo "unknown")
                
                # Clear spinner line
                echo -ne "\r\033[K"
                
                echo -e "   Backend:  ${GREEN}${BACKEND_STATUS}${NC}"
                echo -e "   Ollama:   ${GREEN}${OLLAMA_STATUS}${NC} (models: ${OLLAMA_MODELS_OK})"
                echo -e "   ComfyUI:  ${GREEN}${COMFYUI_STATUS}${NC}"
                
                # Check if all services are healthy
                if [[ "$BACKEND_STATUS" == "healthy" ]] && \
                   [[ "$OLLAMA_STATUS" == "healthy" ]] && \
                   [[ "$OLLAMA_MODELS_OK" == "true" ]] && \
                   [[ "$COMFYUI_STATUS" == "healthy" ]]; then
                    echo ""
                    echo -e "   ${GREEN}✓${NC} All services are healthy!"
                    break
                fi
            else
                # Simple check without JSON parsing
                echo -ne "\r\033[K"
                echo -e "   ${GREEN}✓${NC} Backend responding (health check passed)"
                break
            fi
        fi
    fi
    
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

# Clean up temp file
rm -f /tmp/health_response.json

if [[ $ELAPSED -ge $TIMEOUT ]]; then
    echo -ne "\r\033[K"
    echo -e "${YELLOW}⚠️  WARNING: Timeout waiting for all services${NC}"
    echo -e "   Services may still be initializing."
    echo -e "   Check status: curl http://localhost:8000/health | jq"
    echo -e "   Check logs: docker compose -f docker-compose.intel-mac.yml logs -f"
    echo ""
fi

# ============================================================================
# Display Access Information
# ============================================================================

echo ""
echo -e "${BLUE}[5/6]${NC} Service endpoints:"
echo ""
echo -e "   🌐 ${GREEN}Web Interface:${NC}    http://localhost:8000"
echo -e "   📊 ${GREEN}Health Check:${NC}     http://localhost:8000/health"
echo -e "   📚 ${GREEN}API Docs:${NC}         http://localhost:8000/docs"
echo -e "   🧠 ${GREEN}Ollama:${NC}           http://localhost:11434"
echo -e "   🎨 ${GREEN}ComfyUI:${NC}          http://localhost:8188"
echo ""

# ============================================================================
# Display Management Commands
# ============================================================================

echo -e "${BLUE}[6/6]${NC} Management commands:"
echo ""
echo -e "   📝 View logs:       ${CYAN}docker compose -f docker-compose.intel-mac.yml logs -f${NC}"
echo -e "   🔍 Service status:  ${CYAN}docker compose -f docker-compose.intel-mac.yml ps${NC}"
echo -e "   🛑 Stop services:   ${CYAN}./stop.sh${NC}"
echo -e "   🔄 Restart:         ${CYAN}./stop.sh && ./start.sh${NC}"
echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ GBStudio Automation Hub is ready!${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
