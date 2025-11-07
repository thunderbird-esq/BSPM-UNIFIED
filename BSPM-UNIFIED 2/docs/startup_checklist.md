# System Startup Checklist

**Version:** 3.2  
**Date:** 2025-01-04

Complete this checklist before starting the integrated system.

---

## Pre-Flight Checks

### 1. File Structure Verification

Ensure all files are in place:

```bash
# Backend files
ls -la backend/main.py
ls -la backend/main_endpoints.py
ls -la backend/style_presets.py
ls -la backend/regeneration_manager.py
ls -la backend/sprite_manager.py
ls -la backend/batch_generator.py
ls -la backend/kb_admin.py
ls -la backend/logging_config.py
ls -la backend/metrics.py
ls -la backend/retry_logic.py
ls -la backend/graceful_degradation.py
ls -la backend/task_queue.py
ls -la backend/security.py

# Frontend files
ls -la frontend/index.html
ls -la frontend/src/main.js
ls -la frontend/src/components/style-preset-selector.js
ls -la frontend/src/components/regeneration-ui.js
ls -la frontend/src/components/sprite-manager.js
ls -la frontend/src/components/batch-operations.js
ls -la frontend/src/components/kb-admin.js
ls -la frontend/styles/medium-priority.css
ls -la frontend/styles/integration.css
```

### 2. Update index.html

Add integration.css to the head:

```html
<link rel="stylesheet" href="/frontend/styles/integration.css">
```

### 3. Integrate main_endpoints.py into main.py

Add to your `backend/main.py`:

```python
# At top of file
from backend.main_endpoints import router as medium_priority_router

# After creating FastAPI app
app.include_router(medium_priority_router)
```

### 4. Run Setup Script

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

This creates:
- `logs/` directory
- `secrets/` directory with API key
- `.env` file with configuration
- Sample documentation

---

## Configuration

### 5. Review .env File

Edit `.env` and verify settings:

```bash
cat .env

# Should contain:
ENVIRONMENT=development
LOG_LEVEL=INFO
OLLAMA_URL=http://ollama:11434
COMFYUI_URL=http://comfyui:8188
MAX_CONCURRENT_GENERATIONS=1
GENERATION_TIMEOUT_SECONDS=600
RATE_LIMIT_REQUESTS_PER_MINUTE=10
```

### 6. Add Project Documentation

```bash
# Add your project docs to be indexed
echo "# My Game Design" > project_docs/game_design.md
echo "# Sprite Guidelines" > project_docs/sprite_guidelines.md
```

---

## Startup Sequence

### 7. Start Services

```bash
./start.sh
```

Wait for health checks (5-10 minutes first run):
- ✅ Backend healthy
- ✅ Ollama healthy (models loaded)
- ✅ ComfyUI healthy

### 8. Initialize Knowledge Base

```bash
./scripts/init-kb.sh
```

Expected output:
```
Found X markdown files
Processing: game_design.md
  ✅ Added to knowledge base
...
✅ Initialization Complete
   Files processed: X
   Total documents: Y
```

### 9. Verify Endpoints

```bash
# Test health
curl http://localhost:8000/health

# Test style presets
curl http://localhost:8000/api/v1/presets

# Test sprites list
curl http://localhost:8000/api/v1/sprites

# Test KB stats
curl http://localhost:8000/api/v1/admin/kb/stats
```

All should return 200 OK with JSON responses.

---

## Frontend Testing

### 10. Open Browser

Navigate to: `http://localhost:8000`

Expected behavior:
1. Barry modal appears
2. Click "START"
3. Main interface loads with:
   - Chat window (left)
   - Style preset selector above input
   - Four toggle buttons in header (📊 🖼️ 📦 📚)

### 11. Test Style Presets

1. Click style preset dropdown
2. Select "Detailed Sprite"
3. Verify description updates
4. Verify parameters show (Steps: 25, CFG: 10.0)

### 12. Test Chat Interface

1. Type: "What sprite formats are supported?"
2. Click SEND
3. Verify PM agent responds with relevant info from knowledge base

### 13. Test Service Monitor

1. Click 📊 button in header
2. Service monitor panel appears (top-right)
3. Verify services show status:
   - Ollama: healthy (green)
   - ComfyUI: healthy (green)

### 14. Test Sprite Manager

1. Click 🖼️ button in header
2. Sprite Manager panel opens (right side)
3. Shows "No sprites found" (if fresh install)
4. Search and filter controls visible

### 15. Test Batch Operations

1. Click 📦 button in header
2. Batch Operations panel opens
3. Three tabs visible: CSV Upload, Character Set, Project Template
4. Switch between tabs to verify UI

### 16. Test KB Admin

1. Click 📚 button in header
2. KB Admin panel opens
3. Shows statistics (documents indexed)
4. Document list visible
5. Upload, Rebuild, Test Search buttons present

---

## Generation Test

### 17. Test Full Generation Flow

1. Select preset: "Clean Pixel Art"
2. Type: "Create a simple knight sprite"
3. Click SEND
4. PM agent responds with plan
5. Click ✓ APPROVE
6. Progress bar appears
7. Wait 3-5 minutes
8. Success message appears
9. Regenerate button appears below chat

### 18. Test Regeneration

1. Click "🔄 Regenerate with Different Seed"
2. New generation queued
3. "⚖️ Compare All Attempts" button appears
4. Click Compare button
5. Modal shows attempts side-by-side
6. Mark one as best

---

## Troubleshooting

### Logs Don't Appear

```bash
# Check logs directory created
ls -la logs/

# Check permissions
chmod 755 logs

# Restart backend
docker compose -f docker-compose.intel-mac.yml restart backend
```

### Endpoints Return 404

```bash
# Verify router included in main.py
grep "medium_priority_router" backend/main.py

# Check logs
docker compose -f docker-compose.intel-mac