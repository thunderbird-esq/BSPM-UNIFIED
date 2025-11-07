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

# Generate API key with bcrypt hash if not exists
API_KEY_HASH_FILE="$PROJECT_ROOT/secrets/api_key_hashes.txt"
if [ ! -f "$API_KEY_HASH_FILE" ]; then
    echo "🔑 Generating API key (with bcrypt hash)..."

    # Generate secure random key and hash it
    if command -v python3 &> /dev/null; then
        # Generate key and hash using Python
        KEY_AND_HASH=$(python3 <<EOF
import secrets
import bcrypt

# Generate key
key = secrets.token_urlsafe(32)

# Hash key
key_bytes = key.encode('utf-8')
hash_bytes = bcrypt.hashpw(key_bytes, bcrypt.gensalt())
hash_str = hash_bytes.decode('utf-8')

# Output: plaintext|hash
print(f"{key}|{hash_str}")
EOF
        )

        API_KEY=$(echo "$KEY_AND_HASH" | cut -d'|' -f1)
        API_KEY_HASH=$(echo "$KEY_AND_HASH" | cut -d'|' -f2)
    else
        echo "   ⚠️  WARNING: Cannot generate API key (python3 with bcrypt required)"
        echo "   Please install: pip install bcrypt"
        API_KEY=""
        API_KEY_HASH=""
    fi

    if [ -n "$API_KEY_HASH" ]; then
        # Save hash (not plaintext)
        echo "$API_KEY_HASH" > "$API_KEY_HASH_FILE"
        chmod 600 "$API_KEY_HASH_FILE"
        echo "   ✅ API key hash saved to: $API_KEY_HASH_FILE"
        echo ""
        echo "   🔐 YOUR API KEY (save this securely - shown only once):"
        echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "   $API_KEY"
        echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "   ⚠️  SECURITY: The hash (not plaintext) is stored in secrets/"
        echo "   This key is shown ONLY ONCE. Copy it now!"
        echo ""
        echo "   Use this key in API requests:"
        echo "   curl -H 'X-API-Key: $API_KEY' http://localhost:8000/api/v1/execute ..."
        echo ""
    fi
else
    echo "🔑 API key hash file already exists: $API_KEY_HASH_FILE"
    echo "   (Existing hashes preserved)"
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
