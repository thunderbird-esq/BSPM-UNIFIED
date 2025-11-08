# GBStudio Automation Hub

AI-powered sprite generation system for Game Boy Color game development.

**Version:** 3.3.1 (Security Hardened + Apple Silicon Support)
**Platform:** Intel Mac (x86_64) OR Apple Silicon (M1/M2/M3 via Rosetta 2) + Docker Desktop 4.25+
**Security Status:** ✅ Production Ready (CVSS 2.3 - Low Risk)

> **🔒 Security Notice:** Version 3.3 includes comprehensive security fixes addressing all critical vulnerabilities identified in security audit. See [SECURITY.md](SECURITY.md) for details.

> **✅ Apple Silicon Compatibility:** Version 3.3.1 adds full Apple Silicon (M1/M2/M3) support via Docker Desktop with Rosetta 2 emulation. All services tested and working on M2 Macs. Performance is 20-30% slower than Intel due to emulation, but fully functional.

---

## Overview

Natural language → PM Agent → ComfyUI → Validated Sprites → GBStudio Project

**Example workflow:**
```
You: "Create a knight sprite"
PM: "I'll generate 8 frames: idle, walk x4, attack x2, hurt. Approve?"
You: ✓ Approve
System: Generates → Validates → Integrates → Done (3-4 min)
```

---

## Quick Start

```bash
# 1. Initial setup (first time only)
./scripts/setup.sh

# 2. Start services
./start.sh

# 3. Initialize knowledge base
./scripts/init-kb.sh

# 4. Open browser
open http://localhost:8000
```

---

## Requirements

- **Hardware**: Intel Mac (x86_64) OR Apple Silicon (M1/M2/M3 with Rosetta 2)
- **OS**: macOS Ventura 13.x or later
- **Docker**: Docker Desktop 4.25+ running
- **Ollama**: Local installation with `llama3:8b` and `nomic-embed-text:latest` models
- **RAM**: 8GB minimum (16GB recommended)
- **Disk**: 20GB free space

### Apple Silicon M2/M3 Users

All compatibility issues resolved in v3.3.1:
- ✅ Docker containers build successfully via Rosetta 2
- ✅ Ollama connectivity working with `host.docker.internal:host-gateway` mapping
- ✅ Model version tags correctly specified (`llama3:8b`, `nomic-embed-text:latest`)
- ✅ All services healthy and operational

**Performance Note:** Expect 20-30% slower performance than Intel Macs due to Rosetta 2 emulation.

---

## System Architecture

```
┌─────────────┐
│   Browser   │ ← http://localhost:8000
└──────┬──────┘
       │
┌──────▼──────────────────────────────────────┐
│  FastAPI Backend (8000)                     │
│  - PM Agent (Ollama llama3:8b)              │
│  - Knowledge Base (FAISS + nomic-embed)     │
│  - Task Queue (Resource Management)         │
│  - Metrics (Prometheus)                     │
└──┬────────────────────────────────┬─────────┘
   │                                │
┌──▼─────────┐            ┌─────────▼────────┐
│  Ollama    │            │    ComfyUI       │
│  (11434)   │            │    (8188)        │
│  LLM API   │            │  Image Gen       │
└────────────┘            └──────────────────┘
```

---

## Frontend Architecture

### Technology Stack

**UI Framework:**
- **Pokemon GameBoy CSS** - Retro Game Boy aesthetic with authentic color palette
- **NES.css** - 8-bit style UI components and typography
- **Press Start 2P Font** - Pixel-perfect retro typography

**Component Architecture:**
- **ES6 Modules** - Modern JavaScript with component-based structure
- **Vanilla JavaScript** - No framework dependencies for maximum performance
- **WebSocket Integration** - Real-time progress updates from ComfyUI

### File Structure

```
frontend/
├── index.html                          # Main HTML entry point
├── assets/
│   └── barry_head.png                  # Mascot image
├── styles/
│   ├── css-pokemon-gameboy.css        # Base Pokemon Game Boy theme (512 lines)
│   ├── command-deck.css               # Command interface styling (220 lines)
│   ├── chat.css                       # Chat interface styles (377 lines)
│   ├── dialog-system.css              # Pokemon-style dialogs (459 lines)
│   ├── startup-animation.css          # GB boot animation (280 lines)
│   ├── loading-states.css             # Loading indicators (432 lines)
│   ├── error-states.css               # Error displays (169 lines)
│   ├── medium-priority.css            # Extended features (824 lines)
│   ├── integration.css                # Component integration (297 lines)
│   └── responsive.css                 # Mobile/tablet support (151 lines)
├── src/
│   ├── main.js                        # Application entry point (397 lines)
│   ├── dialog-system.js               # Dialog manager (334 lines)
│   ├── easter-eggs.js                 # Hidden features (78 lines)
│   ├── components/
│   │   ├── chat.js                    # Chat UI component (248 lines)
│   │   ├── monitor.js                 # Service health monitor (167 lines)
│   │   ├── websocket.js               # ComfyUI WebSocket client (89 lines)
│   │   ├── style-preset-selector.js   # Style preset UI (163 lines)
│   │   ├── regeneration-ui.js         # Regeneration controls (230 lines)
│   │   ├── sprite-manager-ui.js       # Sprite management (425 lines)
│   │   ├── batch-operations.js        # Batch generation (452 lines)
│   │   └── kb-admin.js                # Knowledge base admin (545 lines)
│   └── utils/
│       ├── api.js                     # REST API wrapper (102 lines)
│       └── sanitizer.js               # XSS prevention (184 lines)
└── Total: 7,667 lines of frontend code
```

### Key Features

#### 1. Startup Experience
- **Barry Modal** - Friendly mascot introduction on first load
- **Smooth Transitions** - Fade animations between screens
- **Game Boy Boot Sequence** - Optional authentic GB startup (easter egg)

#### 2. Chat Interface
- **Natural Language Input** - Talk to PM Agent in plain English
- **Typing Indicators** - Real-time feedback when PM is thinking
- **Message History** - Scrollable conversation log
- **Approval Workflow** - Visual buttons for plan approval/rejection
- **Progress Tracking** - Live progress bars for sprite generation

#### 3. Service Monitor
- **Real-time Health Checks** - Monitor Backend, Ollama, ComfyUI
- **Latency Tracking** - Response time metrics (color-coded)
- **Auto-refresh** - Updates every 5 seconds
- **Status Indicators** - Visual dots (green/yellow/red)

#### 4. Style Presets
- **Visual Selector** - Click to choose art style
- **8 Preset Styles** - Clean Pixel Art, Retro 8-bit, Game Boy, NES, SNES, Detailed Pixel, Minimalist, Chibi
- **Auto-detection** - PM Agent suggests style from prompt
- **Preview Thumbnails** - See style before selecting

#### 5. Regeneration System
- **Try Again** - Regenerate with new random seed
- **Change Style** - Same prompt, different artistic style
- **Comparison View** - Side-by-side comparison of attempts
- **Mark Best** - Flag favorite result

#### 6. Sprite Manager
- **Project Browser** - View all sprites in GBStudio project
- **Edit Metadata** - Rename, change type
- **Duplicate & Vary** - Create variations (color swap, mirror, rotate)
- **Export** - Save as standalone PNG (with scaling)
- **Delete** - Remove from project (with confirmation)

#### 7. Batch Operations
- **CSV Upload** - Generate multiple sprites from spreadsheet
- **Character Sets** - Full animation set (idle, walk, attack, hurt)
- **Project Templates** - Pre-built sprite packs (RPG, Platformer, Shooter)
- **Batch Progress** - Track multiple generations simultaneously

#### 8. Knowledge Base Admin
- **Document Browser** - View all indexed documentation
- **Upload** - Add new markdown files to KB
- **Re-index** - Update existing documents
- **Search Test** - Test semantic search queries
- **Statistics** - View KB size, document count, embedding stats

### Interactive Features

#### Drag & Drop
- **File Upload** - Drop CSV files for batch generation
- **Document Upload** - Drop markdown files into KB

#### Hover Effects
- **Button Feedback** - Pixel-art press animations
- **Tooltips** - Contextual help on hover
- **Card Previews** - Expand on hover

#### Keyboard Shortcuts
- **Enter** - Send chat message (Shift+Enter for newline)
- **Esc** - Close active dialog/panel
- **Ctrl+K** - Focus chat input

### Accessibility Features

- **ARIA Labels** - Screen reader support throughout
- **Semantic HTML** - Proper heading hierarchy
- **Keyboard Navigation** - Full keyboard accessibility
- **Focus Indicators** - Visible focus states
- **Alt Text** - Descriptive image labels
- **Color Contrast** - WCAG AA compliant

### Responsive Design

**Breakpoints:**
- **Desktop** (1200px+) - Full three-column layout
- **Tablet** (768px-1199px) - Two-column layout, collapsible panels
- **Mobile** (320px-767px) - Single column, stacked components

**Adaptive Features:**
- Hamburger menu for mobile
- Touch-friendly button sizes (min 44px)
- Simplified dialogs on small screens
- Responsive typography (rem units)

### Customization Guide

**Change Color Palette:**
```css
/* Edit css-pokemon-gameboy.css */
:root {
    --gb-green-1: #0f380f;  /* Darkest */
    --gb-green-2: #306230;  /* Dark */
    --gb-green-3: #8bac0f;  /* Light */
    --gb-green-4: #9bbc0f;  /* Lightest */
}
```

**Modify Animations:**
```css
/* Edit startup-animation.css */
@keyframes bootSequence {
    0% { background-color: #fff; }
    10% { background-color: #9bbc0f; }
    /* Customize timing here */
}
```

**Add New Style Preset:**
```javascript
// Edit style-preset-selector.js
const PRESETS = {
    'my_style': {
        name: 'My Custom Style',
        description: 'Your description',
        icon: '🎨'
    }
};
```

### Easter Eggs

Hidden features activated by special inputs:

1. **Konami Code** - Classic cheat code activates Game Boy boot sequence
2. **"barry" keyword** - Barry responds with special message
3. **Triple-click logo** - Reveals version info and debug console
4. **"retro mode"** - Enables scanline effects
5. **"dev"** - Shows developer stats overlay

### Browser Compatibility

**Fully Supported:**
- Chrome 90+ ✅
- Firefox 88+ ✅
- Safari 14+ ✅
- Edge 90+ ✅

**Partially Supported:**
- Chrome 80-89 (no ES6 modules)
- Firefox 78-87 (no optional chaining)

**Not Supported:**
- Internet Explorer (any version)

### Performance Metrics

**Load Time:**
- Initial page load: <500ms
- JavaScript bundle: ~150KB (uncompressed)
- CSS bundle: ~45KB (uncompressed)
- Total assets: ~200KB

**Runtime Performance:**
- Chat message render: <10ms
- Service health check: 100-300ms
- WebSocket latency: 50-100ms
- Smooth 60fps animations

---

## Features

### Core
- **Natural Language Interface**: Chat with PM agent to create sprites
- **Automated Workflow**: Prompt → Plan → Approve → Generate → Validate → Integrate
- **Quality Validation**: Dimension, palette, blank frame, motion consistency checks
- **GBStudio Integration**: Auto-import sprites as indexed 4-color PNGs

### Production Ready (v3.3 - Security Hardened)
- **Error Recovery**: Exponential backoff retry with circuit breakers
- **Resource Management**: Queue system with CPU/memory/disk monitoring
- **Rate Limiting**: 10 requests/minute per session
- **Structured Logging**: JSON logs with rotation (app.log, error.log, app.jsonl)
- **Metrics**: Prometheus endpoint at `/metrics`
- **Graceful Degradation**: System continues with reduced functionality if services fail

### Security Features (v3.3)
- **🔒 CORS Protection**: Whitelist-based origin control (no wildcards)
- **🔑 Admin Authentication**: All admin endpoints require API key authentication
- **🛡️ Path Traversal Prevention**: Validated file operations with strict path checking
- **🚫 XSS Protection**: Comprehensive input/output sanitization on frontend
- **⚡ Thread-Safe**: RLock synchronization on all shared state access
- **✅ Input Validation**: Pydantic models with automatic type checking and sanitization
- **📝 Audit Logging**: Complete audit trail for all admin operations
- **🧪 Security Tests**: 56 comprehensive security tests + 26 thread safety tests
- **Non-root Containers**: All services run as unprivileged users

---

## Installation

### 1. Initial Setup

```bash
# Clone or extract project
cd BSPM-UNIFIED

# Run setup script
chmod +x scripts/setup.sh
./scripts/setup.sh

# This creates:
# - Required directories (logs, secrets, vectorstore, etc.)
# - API key (saved to secrets/api_keys.txt)
# - Sample documentation
# - Environment configuration (.env)
```

### 2. Configuration

**IMPORTANT:** Copy `.env.example` to `.env` and configure:

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration
nano .env
```

**Required Configuration (v3.3):**

```bash
# CORS Configuration (REQUIRED for production)
# Specify allowed origins (comma-separated, no wildcards)
ALLOWED_ORIGINS=http://localhost:8000,http://localhost:3000

# Environment: development (relaxed) or production (strict security)
ENVIRONMENT=production

# Log level
LOG_LEVEL=INFO

# Resource limits (Intel Mac defaults)
MAX_CONCURRENT_GENERATIONS=1
GENERATION_TIMEOUT_SECONDS=600

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=10
```

**Security Best Practices:**
- Set `ALLOWED_ORIGINS` to your specific domains (never use `*`)
- Use `ENVIRONMENT=production` for deployments
- Keep API keys in `app/secrets/api_keys.txt` (never commit to git)
- Review [SECURITY.md](SECURITY.md) for complete security guidelines

### 3. Start Services

```bash
# Start all containers (Backend, Ollama, ComfyUI)
./start.sh

# First run takes 5-10 minutes:
# - Ollama downloads llama3:8b (4.7GB)
# - Ollama downloads nomic-embed-text (1.2GB)
# - ComfyUI downloads SDXL Base (6.9GB)
# - ComfyUI downloads Pixel Art LoRA (1.5GB)

# Health checks run automatically
# System ready when you see:
# ✅ All services are healthy!
# 🌐 Access the application at: http://localhost:8000
```

### 4. Initialize Knowledge Base

```bash
# Add your documentation (optional but recommended)
echo "# My Game Design\n..." > project_docs/game_design.md

# Index all markdown files
./scripts/init-kb.sh

# PM agent now has context from your documentation
```

---

## Usage

### Web Interface

```
http://localhost:8000
```

**Workflow:**
1. **Chat with PM Agent**: Type natural language requests
2. **Review Plan**: PM agent proposes generation plan
3. **Approve**: Click ✓ to start generation
4. **Monitor Progress**: Watch real-time progress bar
5. **View Result**: See generated sprite in GBStudio project

### API (with cURL)

```bash
# Send prompt
curl -X POST http://localhost:8000/api/v1/prompt \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "Create a knight sprite",
    "session_id": "my_session_123"
  }'

# Response includes plan
# {
#   "message": "I'll create a knight sprite...",
#   "plan": [{"department": "Art", "task": "..."}],
#   "requires_approval": true
# }

# Execute approved plan (production requires API key)
curl -X POST http://localhost:8000/api/v1/execute \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: YOUR_API_KEY' \
  -d '{
    "plan": [{"department": "Art", ...}],
    "session_id": "my_session_123"
  }'
```

### Service Monitor

```
http://localhost:8000/#monitor
```

Real-time dashboard showing:
- Service health (Ollama, ComfyUI)
- Response latency
- Queue status
- Resource usage

### Metrics (Prometheus)

```
http://localhost:8000/metrics
```

Available metrics:
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `sprite_generation_requests_total` - Generation outcomes
- `sprite_generation_duration_seconds` - Generation time
- `sprite_validation_failures_total` - Validation failures by reason
- `pm_agent_response_duration_seconds` - PM agent latency
- `service_health` - Service health status (1=healthy, 0=unhealthy)
- `system_cpu_percent`, `system_memory_percent` - Resource usage

---

## Management

### Logs

```bash
# View application logs
tail -f logs/app.log

# View errors only
tail -f logs/error.log

# View Docker logs
docker compose -f docker-compose.intel-mac.yml logs -f backend
```

### Backup

```bash
# Backup vectorstore + conversations + tasks
./scripts/backup-memory.sh

# Creates: backups/memory_backup_YYYYMMDD_HHMMSS.tar.gz
```

### Restore from Backup

```bash
# Stop services
./stop.sh

# Extract backup
tar -xzf backups/memory_backup_20250104_143000.tar.gz

# Move files
mv memory_backup_20250104_143000/* .

# Restart
./start.sh
```

### Stop Services

```bash
./stop.sh

# Gracefully stops all containers
# Data persists in bind mounts
```

### Reset System

```bash
# Stop services
./stop.sh

# Remove all data (CAUTION: Cannot be undone!)
rm -rf vectorstore/ agent_memory/ logs/

# Re-run setup
./scripts/setup.sh
./start.sh
./scripts/init-kb.sh
```

---

## Testing

### Test Suite (v3.3)

The project includes comprehensive test coverage:
- **162+ test methods** across 6 test files
- **85%+ code coverage** on critical modules
- Security tests, thread safety tests, integration tests

```bash
# Install test dependencies
pip install pytest pytest-cov httpx

# Run all tests
pytest tests/ -v

# Run security tests
pytest tests/test_security.py -v

# Run thread safety tests
pytest tests/test_thread_safety.py -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html

# View coverage report
open htmlcov/index.html

# Run specific test file
pytest tests/test_sprite_generation.py -v
```

### Test Coverage by Module

- **test_api.py**: 80 tests - API endpoints, CORS, authentication
- **test_security.py**: 56 tests - Security vulnerabilities, input validation
- **test_thread_safety.py**: 26 tests - Race conditions, concurrent access
- **test_sprite_generation.py**: Sprite validation, quality checks
- **test_knowledge_base.py**: FAISS search, document indexing
- **test_gbstudio_project.py**: GBStudio integration

---

## Troubleshooting

### Services Won't Start

```bash
# Check Docker Desktop is running
docker info

# Check architecture
uname -m  # Should output: x86_64

# View logs
docker compose -f docker-compose.intel-mac.yml logs
```

### Ollama Model Download Stuck

```bash
# Check Ollama logs
docker compose -f docker-compose.intel-mac.yml logs ollama

# Manually pull models
docker exec bspm-unified-ollama-1 ollama pull llama3:8b
docker exec bspm-unified-ollama-1 ollama pull nomic-embed-text
```

### ComfyUI Generation Fails

```bash
# Check ComfyUI logs
docker compose -f docker-compose.intel-mac.yml logs comfyui

# Verify models downloaded
docker exec bspm-unified-comfyui-1 ls /app/ComfyUI/models/checkpoints
docker exec bspm-unified-comfyui-1 ls /app/ComfyUI/models/loras

# Test ComfyUI directly
curl http://localhost:8188/system_stats
```

### Knowledge Base Not Working

```bash
# Re-initialize
./scripts/init-kb.sh

# Check vectorstore files
ls -lh vectorstore/

# Test search
curl -X POST http://localhost:8000/api/v1/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "sprite format", "limit": 3}'
```

### High CPU Usage

This is normal during sprite generation (ComfyUI uses 100% CPU). To reduce:

1. Check queue status: `curl http://localhost:8000/health`
2. Wait for current generation to complete
3. System auto-pauses new tasks if CPU > 95% for 30s

---

## Security

**📖 See [SECURITY.md](SECURITY.md) for complete security documentation**

### Security Status (v3.3)

**Risk Level:** 🟢 LOW (CVSS 2.3)
**Last Security Audit:** 2025-11-07
**Vulnerabilities Fixed:** 8 (3 Critical, 5 High)

### Security Features

1. **CORS Protection**: Whitelist-based, no wildcard origins
2. **Admin Authentication**: All 8 admin endpoints require API keys
3. **Path Traversal Prevention**: Validated file operations
4. **XSS Protection**: Input/output sanitization
5. **Thread Safety**: Synchronized access to shared state
6. **Input Validation**: Pydantic models with type checking
7. **Audit Logging**: All admin operations logged
8. **Rate Limiting**: 10 requests/minute per session

### Development Mode (Default)

```bash
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:8000
```

- Admin endpoints accessible without API key (for testing)
- Rate limiting enabled (10 req/min)
- CORS restricted to localhost

### Production Mode (Recommended)

```bash
# .env configuration
ENVIRONMENT=production
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

**Production Requirements:**
1. Set specific `ALLOWED_ORIGINS` (never use `*`)
2. All admin endpoints require API key
3. Audit logging enabled
4. Secure API key storage

**Admin API Usage (Production):**

```bash
# All admin endpoints require X-API-Key header
curl -X GET http://localhost:8000/api/v1/admin/kb/documents \
  -H 'X-API-Key: YOUR_API_KEY_FROM_secrets/api_keys.txt'

# Delete operations require confirmation
curl -X DELETE 'http://localhost:8000/api/v1/admin/kb/documents?confirm=true' \
  -H 'X-API-Key: YOUR_API_KEY'
```

### Generate API Keys

```bash
# Python method
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to secrets/api_keys.txt (one per line)
echo "NEW_KEY_HERE" >> app/secrets/api_keys.txt

# Restart to load new keys
./stop.sh && ./start.sh
```

### Security Best Practices

1. ✅ Use `ENVIRONMENT=production` for deployments
2. ✅ Set specific `ALLOWED_ORIGINS` (never wildcards)
3. ✅ Store API keys in `app/secrets/` (gitignored)
4. ✅ Rotate API keys regularly
5. ✅ Monitor audit logs in `app/logs/`
6. ✅ Run security tests before deployment
7. ✅ Keep dependencies updated

### Reporting Security Issues

See [SECURITY.md](SECURITY.md) for vulnerability reporting procedures.

---

## Performance

### Intel Mac (i5/i7 CPU)

- **PM Agent Response**: 1-3 seconds
- **Sprite Generation**: 3-5 minutes (20 steps)
- **Validation**: <1 second
- **Total**: ~4 minutes per sprite

### Resource Usage

- **CPU**: 100% during generation (normal)
- **Memory**: ~4GB total (2GB backend, 1.5GB Ollama, 500MB ComfyUI)
- **Disk**: ~15GB (models + data)

---

## Architecture Details

See `gbstudio_guide_v3_technical.md` for complete technical specifications including:
- Complete request flow (17 steps)
- GBStudio project format
- ComfyUI workflow specification
- FAISS implementation details
- Validation criteria with test cases

---

## License

Internal tool for game development studio use.

---

## Support

For issues or questions:
1. Check logs: `tail -f logs/app.log`
2. View metrics: `http://localhost:8000/metrics`
3. Check service health: `curl http://localhost:8000/health`
4. Review documentation: `gbstudio_guide_v3_technical.md`
