#!/bin/bash
set -e

# GBStudio Automation Hub - Local Setup Script
# Install dependencies and prepare for local development

echo "========================================="
echo "GBStudio Automation Hub - Local Setup"
echo "========================================="
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $PYTHON_VERSION"

# Recommend virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo ""
    echo "⚠️  You're not in a virtual environment!"
    echo "It's HIGHLY recommended to use one:"
    echo ""
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo ""
    read -p "Create and activate venv now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
        echo ""
        echo "✓ Virtual environment created!"
        echo "Now run: source venv/bin/activate"
        echo "Then run this script again."
        exit 0
    fi
fi

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
if [ -f backend/requirements.txt ]; then
    pip install --upgrade pip
    pip install -r backend/requirements.txt
    echo "✓ Python dependencies installed"
else
    echo "✗ backend/requirements.txt not found!"
    exit 1
fi

# Create required directories
echo ""
echo "Creating required directories..."
mkdir -p ./app/logs
mkdir -p ./app/secrets
mkdir -p ./project_files
mkdir -p ./temp_outputs
mkdir -p ./vectorstore
mkdir -p ./agent_memory/conversations
mkdir -p ./project_docs
mkdir -p ./workflows
echo "✓ Directories created"

# Check if .env.local exists
echo ""
if [ -f .env.local ]; then
    echo "✓ Configuration file .env.local found"
else
    echo "⚠️  No .env.local file found (but it should be there!)"
fi

# Check Ollama
echo ""
echo "========================================="
echo "External Services Check"
echo "========================================="

echo -n "Ollama (localhost:11434)... "
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✓ Running"

    # Check for required models
    echo ""
    echo "Checking Ollama models..."
    MODELS=$(curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | cut -d'"' -f4 || echo "")

    if echo "$MODELS" | grep -q "llama3"; then
        echo "  ✓ llama3 model found"
    else
        echo "  ✗ llama3 model not found"
        echo "    Install it: ollama pull llama3"
    fi

    if echo "$MODELS" | grep -q "nomic-embed-text"; then
        echo "  ✓ nomic-embed-text model found"
    else
        echo "  ✗ nomic-embed-text model not found"
        echo "    Install it: ollama pull nomic-embed-text"
    fi
else
    echo "✗ Not running"
    echo ""
    echo "  Ollama is required! Install and start it:"
    echo "  - macOS: Download from https://ollama.ai"
    echo "  - Linux: curl https://ollama.ai/install.sh | sh"
    echo ""
fi

echo -n "ComfyUI (localhost:8188)... "
if curl -s http://localhost:8188 > /dev/null 2>&1; then
    echo "✓ Running"
else
    echo "✗ Not running"
    echo "  (Optional - needed for image generation)"
    echo "  You can skip this for now and add it later"
fi

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Make sure Ollama is running: ollama serve"
echo "  2. Pull required models:"
echo "     ollama pull llama3"
echo "     ollama pull nomic-embed-text"
echo "  3. Start the server: ./run_local.sh"
echo ""
echo "Once running, visit: http://localhost:8000"
echo ""
