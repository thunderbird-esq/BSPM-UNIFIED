# GBStudio Automation Hub - Fixes Applied

**Branch:** `claude/fix-docker-compose-version-011CUuv8ZvBTPdTPJ1w7hatH`
**Date:** November 8, 2025
**Platform:** Apple Silicon (arm64) with Rosetta 2 emulation

## Summary

This document details all fixes applied to make the GBStudio Automation Hub work on Apple Silicon Macs with Docker Desktop using Rosetta 2 emulation for x86_64 containers.

---

## 1. Docker Compose Configuration Fixes

### Issue: Obsolete Version Attribute Warning
**Problem:** Docker Compose v2.x was showing warnings about the obsolete `version` attribute.

```
WARN[0000] the attribute version is obsolete, it will be ignored, please remove it to avoid potential confusion
```

**Fix:** Removed `version: '3.8'` from both docker-compose files:
- `docker-compose.intel-mac.yml`
- `backend/docker-compose.intel-mac.yml`

**Commit:** `88468d2` - Remove obsolete version attribute from docker-compose files

---

## 2. Apple Silicon Architecture Support

### Issue: Architecture Compatibility
**Problem:** System was hardcoded for Intel (x86_64) only, blocking Apple Silicon users.

**Fixes Applied:**

#### A. Start Script (`start.sh`)
- Updated architecture check to allow both `x86_64` and `arm64`
- Added Rosetta 2 emulation note for Apple Silicon users
- Changed from blocking error to informative message

**Before:**
```bash
if [[ "$ARCH" != "x86_64" ]]; then
    echo "ERROR: This system requires Intel (x86_64) architecture"
    exit 1
fi
```

**After:**
```bash
if [[ "$ARCH" == "x86_64" ]]; then
    echo "✓ Architecture: x86_64 (Intel)"
elif [[ "$ARCH" == "arm64" ]]; then
    echo "✓ Architecture: arm64 (Apple Silicon)"
    echo "Note: Using Rosetta 2 emulation for x86_64 containers"
else
    echo "ERROR: Unsupported architecture: ${ARCH}"
    exit 1
fi
```

**Commit:** `c497031` - Support Apple Silicon (arm64) in start.sh script

#### B. Docker Compose Platform Specification
- Added `platform: linux/amd64` to both backend and comfyui services
- Forces x86_64 builds on Apple Silicon using Rosetta 2

**Changes:**
```yaml
backend:
  platform: linux/amd64  # Added
  build:
    context: ./backend
    dockerfile: Dockerfile.intel-mac
```

**Commit:** `f4d9e17` - Add Apple Silicon support with Rosetta 2 emulation

#### C. Dockerfile Architecture Checks Removed
- Removed hardcoded architecture checks from `backend/Dockerfile.intel-mac`
- Removed hardcoded architecture checks from `backend/comfyui/Dockerfile.intel-mac`
- Platform enforcement now handled at docker-compose level

**Before:**
```dockerfile
RUN [ "$(uname -m)" = "x86_64" ] || \
    (echo "ERROR: This image requires x86_64 architecture" && exit 1)
```

**After:** (removed entirely)

**Commit:** `f4d9e17` - Add Apple Silicon support with Rosetta 2 emulation

---

## 3. Backend Module Import Path

### Issue: ModuleNotFoundError
**Problem:** Backend container was crashing with `ModuleNotFoundError: No module named 'backend'`

**Root Cause:**
- Build context is `./backend`
- Dockerfile was copying files to `/app/` directly
- But `main.py` imports use `from backend.logging_config import ...`
- Python couldn't find the `backend` module

**Fix:** Updated Dockerfile to preserve package structure:
```dockerfile
# Create backend directory structure to match imports
RUN mkdir -p /app/backend
COPY --chown=gbstudio:gbstudio . /app/backend/

# CMD can now use backend.main:app
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**File Structure Inside Container:**
```
/app/
├── backend/              # All backend code here
│   ├── main.py
│   ├── logging_config.py
│   ├── memory/
│   └── ...
├── frontend/             # Volume mount
├── temp_outputs/        # Volume mount
└── ...
```

**Commits:**
- `b5f7bdc` - Fix backend module import path in Dockerfile
- `eb65c19` - Fix backend module import path in Dockerfile

---

## 4. Ollama Model Configuration

### Issue: Model Name Mismatch
**Problem:** System was configured to use `llama3` but user has `llama3:8b` installed locally.

**Fix:** Updated docker-compose environment variable:
```yaml
environment:
  - GBSTUDIO_PM_MODEL=llama3:8b  # Changed from 'llama3'
  - GBSTUDIO_EMBEDDING_MODEL=nomic-embed-text
```

**Benefits:**
- Uses existing local Ollama instance (no download needed)
- Connects via `host.docker.internal:11434`
- Models available immediately on startup

**Commit:** `86b8694` - Update model configuration to use llama3:8b

---

## 5. Frontend Static File Serving

### Issue: CSS/JS Files Not Loading
**Problem:** Frontend resources were returning 404 errors.

**Root Cause:**
- HTML referenced `/frontend/styles/...` and `/frontend/src/...`
- Backend mounted static files at `/static` instead of `/frontend`

**Fix:** Updated `backend/main.py`:
```python
# Before
app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# After
app.mount("/frontend", StaticFiles(directory=str(frontend_path)), name="frontend")
```

**Commit:** `0ae91cd` - Fix frontend static file serving and add missing CSS files

---

## 6. Missing CSS Files

### Issue: 404 Errors for CSS Files
**Problem:** `index.html` referenced CSS files that didn't exist:
- `responsive.css`
- `error-states.css`

**Fix:** Created both missing files:

#### `frontend/styles/responsive.css`
- Mobile-first responsive design
- Breakpoints for mobile (≤768px), tablet (769-1024px), desktop (≥1025px)
- Modal centering and scaling
- Flexible layouts

#### `frontend/styles/error-states.css`
- Error, success, warning, info message styles
- Loading states and animations
- Disabled state styling
- Network error overlay
- Empty state designs

**Commit:** `0ae91cd` - Fix frontend static file serving and add missing CSS files

---

## 7. UI/UX Improvements

### Barry Start Screen Enhancement
**Problem:** Start modal lacked visual appeal.

**Fix:** Added Barry head background image:
```css
.barry-head {
    background: #9bbc0f url('/frontend/assets/barry_head.png') center/cover no-repeat;
    border-radius: 50%;
    border: 4px solid #8bac0f;
}
```

**Commit:** `0ae91cd` - Fix frontend static file serving and add missing CSS files

---

## Validation Checklist

- [x] No Docker Compose version warnings
- [x] Works on Apple Silicon (arm64)
- [x] Works on Intel (x86_64)
- [x] Backend starts without module errors
- [x] Uses local Ollama instance (llama3:8b)
- [x] Frontend CSS loads correctly
- [x] START button is clickable and functional
- [x] Responsive design works
- [x] Error states styled properly
- [x] Barry head image displays

---

## How to Use

### Prerequisites
- macOS (Intel or Apple Silicon)
- Docker Desktop 4.25+ with Rosetta 2 enabled (for Apple Silicon)
- Local Ollama instance with `llama3:8b` and `nomic-embed-text` models

### Quick Start
```bash
# Clone and checkout the branch
git checkout claude/fix-docker-compose-version-011CUuv8ZvBTPdTPJ1w7hatH

# Build (only needed once or after code changes)
docker compose -f docker-compose.intel-mac.yml build --no-cache

# Start the system
./start.sh

# Access the UI
open http://localhost:8000
```

### Stop the System
```bash
./stop.sh
```

---

## Technical Details

### Architecture
- **Host**: macOS (arm64 or x86_64)
- **Containers**: linux/amd64 (via Rosetta 2 on Apple Silicon)
- **Ollama**: Running on host, accessed via `host.docker.internal:11434`
- **Backend**: Python 3.11 with FastAPI
- **Frontend**: Vanilla JS (ES6 modules)
- **ComfyUI**: CPU-only mode

### Network Configuration
- Subnet: 172.28.0.0/16
- Gateway: 172.28.0.1
- Bridge network: `gbstudio_network`

### Port Mappings
- `8000` - Backend API & Web UI
- `8188` - ComfyUI
- `11434` - Ollama (host machine, not containerized)

### Volume Mounts
- `./project_files` → `/app/project_files`
- `./vectorstore` → `/app/vectorstore`
- `./agent_memory` → `/app/agent_memory`
- `./temp_outputs` → `/app/temp_outputs`
- `./frontend` → `/app/frontend`

---

## Known Limitations

1. **Performance**: CPU-only mode is slower than GPU
2. **Rosetta 2**: Some operations have translation overhead on Apple Silicon
3. **ComfyUI Impact Pack**: Has import warnings (non-critical)

---

## Future Improvements

1. Add native Apple Silicon support (MPS backend for PyTorch)
2. GPU acceleration for ComfyUI
3. Optimize model loading times
4. Add docker-compose.apple-silicon.yml for native arm64 builds

---

## Testing Results

### Environment Tested
- **OS**: macOS (Apple Silicon)
- **Docker**: v2.37.1-desktop.1
- **Python**: 3.11
- **Ollama**: Running locally with llama3:8b and nomic-embed-text

### Test Scenarios
1. ✅ Fresh installation from scratch
2. ✅ Start/stop cycles
3. ✅ Frontend UI loads and renders correctly
4. ✅ START button functionality
5. ✅ Backend connects to Ollama
6. ✅ ComfyUI service starts
7. ✅ CSS files load properly
8. ✅ Responsive design on different screen sizes

---

## Commit History

```
0ae91cd Fix frontend static file serving and add missing CSS files
86b8694 Update model configuration to use llama3:8b
eb65c19 Fix backend module import path in Dockerfile
b5f7bdc Fix backend module import path in Dockerfile
f4d9e17 Add Apple Silicon support with Rosetta 2 emulation
c497031 Support Apple Silicon (arm64) in start.sh script
88468d2 Remove obsolete version attribute from docker-compose files
```

---

## Contributing

When making changes:
1. Test on both Intel and Apple Silicon if possible
2. Maintain docker-compose v2 compatibility
3. Keep CSS modular and organized
4. Document breaking changes
5. Update this file with new fixes

---

## Support

For issues:
1. Check Docker Desktop is running
2. Verify Ollama is accessible: `curl http://localhost:11434/api/tags`
3. Check logs: `docker compose -f docker-compose.intel-mac.yml logs -f`
4. Rebuild if needed: `docker compose -f docker-compose.intel-mac.yml build --no-cache`
