#!/bin/bash
set -e

# GBStudio Automation Hub - Local Startup (No Docker!)
# Run the FastAPI backend natively on localhost

echo "========================================="
echo "GBStudio Automation Hub - Local Mode"
echo "========================================="
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables from .env.local
if [ -f .env.local ]; then
    echo "✓ Loading configuration from .env.local"
    export $(cat .env.local | grep -v '^#' | xargs)
else
    echo "⚠️  Warning: .env.local not found, using defaults"
fi

# Create required directories
echo "✓ Creating required directories..."
mkdir -p ./app/logs
mkdir -p ./project_files
mkdir -p ./temp_outputs
mkdir -p ./vectorstore
mkdir -p ./agent_memory/conversations
mkdir -p ./project_docs
mkdir -p ./workflows

echo ""
echo "========================================="
echo "Service Health Checks"
echo "========================================="

# Check if Ollama is running
echo -n "Checking Ollama (localhost:11434)... "
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✓ Running"
else
    echo "✗ Not running"
    echo ""
    echo "ERROR: Ollama is not running on localhost:11434"
    echo "Please start Ollama first:"
    echo "  - On macOS: 'ollama serve' or start Ollama.app"
    echo "  - On Linux: 'systemctl start ollama' or 'ollama serve'"
    echo ""
    exit 1
fi

# Check if ComfyUI is running (optional)
echo -n "Checking ComfyUI (localhost:8188)... "
if curl -s http://localhost:8188 > /dev/null 2>&1; then
    echo "✓ Running"
    COMFYUI_AVAILABLE=true
else
    echo "⚠️  Not running (optional)"
    echo "  Note: Image generation will not work without ComfyUI"
    echo "  You can start ComfyUI later or run without it for testing"
    COMFYUI_AVAILABLE=false
fi

echo ""
echo "========================================="
echo "Starting FastAPI Backend"
echo "========================================="

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Not running in a virtual environment"
    echo "   It's recommended to use a venv:"
    echo "   python3 -m venv venv && source venv/bin/activate"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if dependencies are installed
echo "Checking Python dependencies..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "✗ FastAPI not found. Installing dependencies..."
    pip install -r backend/requirements.txt
else
    echo "✓ Dependencies appear to be installed"
fi

echo ""
echo "Starting server on http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo "Press Ctrl+C to stop"
echo ""

# Start the FastAPI application
cd "$SCRIPT_DIR"
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
