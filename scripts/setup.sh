#!/bin/bash
# System Setup Script - Initialize directories and security
# Version: 3.2
# Platform: Intel Mac (macOS Ventura) + Docker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🔧 GBStudio Automation Hub - System Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create required directories
echo "📁 Creating directories..."
mkdir -p "$PROJECT_ROOT/project_files/assets/sprites"
mkdir -p "$PROJECT_ROOT/vectorstore"
mkdir -p "$PROJECT_ROOT/agent_memory/conversations"
mkdir -p "$PROJECT_ROOT/temp_outputs"
mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$PROJECT_ROOT/secrets"
mkdir -p "$PROJECT_ROOT/project_docs"
mkdir -p "$PROJECT_ROOT/backups"
echo "   ✅ Directories created"
echo ""

# Generate API key if not exists
API_KEY_FILE="$PROJECT_ROOT/secrets/api_keys.txt"
if [ ! -f "$API_KEY_FILE" ]; then
    echo "🔑 Generating API key..."
    
    # Generate secure random key (Python equivalent of secrets.token_urlsafe(32))
    if command -v python3 &> /dev/null; then
        API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    elif command -v openssl &> /dev/null; then
        API_KEY=$(openssl rand -base64 32 | tr -d '/+' | tr '=' '_')
    else
        echo "   ⚠️  WARNING: Cannot generate API key (no python3 or openssl found)"
        echo "   Please manually create: $API_KEY_FILE"
        API_KEY=""
    fi
    
    if [ -n "$API_KEY" ]; then
        echo "$API_KEY" > "$API_KEY_FILE"
        chmod 600 "$API_KEY_FILE"
        echo "   ✅ API key generated and saved to: $API_KEY_FILE"
        echo ""
        echo "   🔐 YOUR API KEY (save this securely):"
        echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "   $API_KEY"
        echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "   Use this key in API requests:"
        echo "   curl -H 'X-API-Key: $API_KEY' http://localhost:8000/api/v1/execute ..."
        echo ""
    fi
else
    echo "🔑 API key file already exists: $API_KEY_FILE"
    echo "   (Existing key preserved)"
    echo ""
fi

# Create sample project documentation
SAMPLE_DOC="$PROJECT_ROOT/project_docs/sprite_guidelines.md"
if [ ! -f "$SAMPLE_DOC" ]; then
    echo "📝 Creating sample documentation..."
    cat > "$SAMPLE_DOC" << 'EOF'
# Sprite Guidelines

## Resolution
All sprites must be 32x32 pixels.

## Color Palette
Use Game Boy Color palette:
- Darkest: RGB(15, 56, 15) #0f380f
- Dark: RGB(48, 98, 48) #306230
- Light: RGB(139, 172, 15) #8bac0f
- Lightest: RGB(155, 188, 15) #9bbc0f

## Animation Frames
Standard character sprite sheet contains 8 frames:
1. Idle (1 frame)
2. Walk cycle (4 frames)
3. Attack (2 frames)
4. Hurt (1 frame)

## Style
- Pixel art style
- Hard edges (no anti-aliasing)
- Consistent lighting across frames
- Clear silhouette
EOF
    echo "   ✅ Sample documentation created: $SAMPLE_DOC"
    echo ""
fi

# Create .env file if not exists
ENV_FILE="$PROJECT_ROOT/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "⚙️  Creating environment configuration..."
    cat > "$ENV_FILE" << 'EOF'
# Environment: development or production
ENVIRONMENT=development

# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Service URLs (defaults for Docker Compose)
OLLAMA_URL=http://ollama:11434
COMFYUI_URL=http://comfyui:8188

# Resource limits (Intel Mac defaults)
MAX_CONCURRENT_GENERATIONS=1
GENERATION_TIMEOUT_SECONDS=600

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=10
EOF
    echo "   ✅ Environment configuration created: $ENV_FILE"
    echo ""
fi

# Set permissions
echo "🔒 Setting permissions..."
chmod +x "$PROJECT_ROOT/start.sh"
chmod +x "$PROJECT_ROOT/stop.sh"
chmod +x "$PROJECT_ROOT/scripts"/*.sh
chmod 700 "$PROJECT_ROOT/secrets"
echo "   ✅ Permissions set"
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Setup Complete"
echo ""
echo "📂 Directory structure:"
echo "   $PROJECT_ROOT/project_files     - GBStudio projects"
echo "   $PROJECT_ROOT/vectorstore        - FAISS knowledge base"
echo "   $PROJECT_ROOT/agent_memory       - Conversation history"
echo "   $PROJECT_ROOT/logs               - Application logs"
echo "   $PROJECT_ROOT/secrets            - API keys (600 permissions)"
echo "   $PROJECT_ROOT/project_docs       - Documentation for indexing"
echo "   $PROJECT_ROOT/backups            - Memory backups"
echo ""
echo "🔐 Security:"
echo "   API key saved in: $PROJECT_ROOT/secrets/api_keys.txt"
echo "   Enable in production by setting: ENVIRONMENT=production"
echo ""
echo "📝 Next steps:"
echo "   1. Review and edit: $ENV_FILE"
echo "   2. Add documentation: $PROJECT_ROOT/project_docs/*.md"
echo "   3. Start services: ./start.sh"
echo "   4. Initialize knowledge base: ./scripts/init-kb.sh"
echo ""
