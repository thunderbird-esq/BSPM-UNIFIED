# BSPM-UNIFIED Configuration Guide

**Date:** 2025-11-08
**Status:** Ready for Configuration

---

## DECISION NEEDED: Development vs Production Mode

### Option 1: Development Mode (Recommended for Testing)
**Characteristics:**
- Uses existing test API key
- CORS allows localhost only (5173, 8080)
- Less strict security for easier testing
- All features enabled
- Ideal for: Phase 1 testing

**Configuration Required:**
- ✅ None! Works out of the box

---

### Option 2: Production Mode
**Characteristics:**
- Requires secure API key generation
- CORS restricted to your actual domain
- Full security enforcement
- Production-ready
- Ideal for: Actual deployment

**Configuration Required:**
1. Generate secure API key
2. Set CORS allowed origins
3. Set ENVIRONMENT=production
4. Configure external Ollama if needed

---

## Current System Status

### ✅ What's Already Configured
```yaml
Docker Compose: docker-compose.intel-mac.yml
Ollama URL: http://host.docker.internal:11434 (expects host Ollama)
ComfyUI URL: http://comfyui:8188 (container)
Backend Port: 8000
API Key File: /app/secrets/api_keys.txt
Current Key: test-api-key-49a07b1d54218c8df192114e5eb35dcd
```

### ⚠️ What Needs Configuration (for Production)
```bash
GBSTUDIO_ALLOWED_ORIGINS=<not set - will use localhost defaults>
ENVIRONMENT=<not set - defaults to development>
```

---

## Configuration Steps

### FOR DEVELOPMENT MODE (Testing Phase 1)

**Step 1:** No changes needed! The defaults are:
```yaml
CORS Origins: ["http://localhost:5173", "http://localhost:8080"]
API Key: test-api-key-49a07b1d54218c8df192114e5eb35dcd (valid)
Environment: development
```

**Step 2:** Just start the services:
```bash
cd "/home/user/BSPM-UNIFIED/BSPM-UNIFIED 2"
docker compose -f docker-compose.intel-mac.yml up -d
```

**Step 3:** Verify startup:
```bash
docker compose -f docker-compose.intel-mac.yml logs -f
```

---

### FOR PRODUCTION MODE

**Step 1: Generate Secure API Key**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > app/secrets/api_keys.txt
chmod 600 app/secrets/api_keys.txt
cat app/secrets/api_keys.txt  # Copy this key for API calls
```

**Step 2: Create .env file**
```bash
cat > .env <<'EOF'
# Production Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO

# CORS - Replace with your actual domains
GBSTUDIO_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Optional: Override default Ollama if not on host
# GBSTUDIO_OLLAMA_API_URL=http://your-ollama-server:11434/api/generate
EOF
```

**Step 3: Update docker-compose.yml**
```bash
# Add to backend service environment section:
# - GBSTUDIO_ALLOWED_ORIGINS=${GBSTUDIO_ALLOWED_ORIGINS}
```

**Step 4: Start with .env**
```bash
docker compose -f docker-compose.intel-mac.yml --env-file .env up -d
```

---

## Testing Checklist

### Prerequisites
- [ ] Ollama running on host machine (port 11434)
  - Check: `curl http://localhost:11434/api/tags`
- [ ] Ollama has required models:
  - [ ] `llama3` (for PM agent)
  - [ ] `nomic-embed-text` (for embeddings)
  - Check: `ollama list`

### After Startup
- [ ] Backend healthy: `curl http://localhost:8000/health`
- [ ] ComfyUI healthy: `curl http://localhost:8188/system_stats`
- [ ] API key required: Test without key should return 401
- [ ] CORS enforced: Test from wrong origin should fail
- [ ] WebSocket connects: `ws://localhost:8000/ws?session_id=test`

---

## Quick Start Commands

### Development Mode (No Configuration Needed)
```bash
# Navigate to project
cd "/home/user/BSPM-UNIFIED/BSPM-UNIFIED 2"

# Ensure Ollama is running on host
ollama list  # Should show llama3 and nomic-embed-text

# Start services
docker compose -f docker-compose.intel-mac.yml up -d

# Watch logs
docker compose -f docker-compose.intel-mac.yml logs -f backend

# Test health
curl http://localhost:8000/health

# Test with API key
curl -X POST http://localhost:8000/api/v1/execute \
  -H "X-API-Key: test-api-key-49a07b1d54218c8df192114e5eb35dcd" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "plan": []}'
```

### Production Mode
```bash
# Generate API key (save the output!)
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > app/secrets/api_keys.txt
chmod 600 app/secrets/api_keys.txt

# Create .env with your domains
cat > .env <<'EOF'
ENVIRONMENT=production
GBSTUDIO_ALLOWED_ORIGINS=https://yourdomain.com
EOF

# Start services
docker compose -f docker-compose.intel-mac.yml --env-file .env up -d

# Test with new key
NEW_KEY=$(cat app/secrets/api_keys.txt)
curl -X POST http://localhost:8000/api/v1/execute \
  -H "X-API-Key: $NEW_KEY" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "plan": []}'
```

---

## Troubleshooting

### Issue: Backend won't start
**Check:**
```bash
docker compose -f docker-compose.intel-mac.yml logs backend
```
**Common causes:**
- Ollama not running on host
- Port 8000 already in use
- Secrets directory permissions

### Issue: "Connection refused" to Ollama
**Solution:**
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# If not, start Ollama on host machine
ollama serve  # Or however you start Ollama on macOS
```

### Issue: 401 Unauthorized
**Check API key:**
```bash
cat app/secrets/api_keys.txt
# Use this key in X-API-Key header
```

### Issue: CORS errors
**Development:** Should allow localhost:5173, localhost:8080
**Production:** Check GBSTUDIO_ALLOWED_ORIGINS matches your frontend URL

---

## What Mode Should You Use?

### Use DEVELOPMENT MODE if:
- ✅ You're testing Phase 1 changes
- ✅ Running locally on your machine
- ✅ No external access needed
- ✅ Want to test quickly

### Use PRODUCTION MODE if:
- ❌ Deploying to a server
- ❌ Allowing external access
- ❌ Running in cloud environment
- ❌ Need strict security

---

## RECOMMENDATION FOR PHASE 1 TESTING

**Use Development Mode!**

Why:
- No configuration needed
- Test API key already works
- CORS allows frontend testing
- Faster to get started
- Can switch to production later

Next steps:
1. Check Ollama is running: `ollama list`
2. Start containers: `docker compose -f docker-compose.intel-mac.yml up -d`
3. Watch logs: `docker compose -f docker-compose.intel-mac.yml logs -f`
4. Test endpoints (see testing checklist above)

---

## API Key Usage Examples

### Execute Endpoint (requires auth after Phase 1)
```bash
curl -X POST http://localhost:8000/api/v1/execute \
  -H "X-API-Key: test-api-key-49a07b1d54218c8df192114e5eb35dcd" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session",
    "plan": [{
      "department": "Art",
      "task": "Generate a knight character sprite",
      "details": {"style": "pixel art"}
    }]
  }'
```

### PM Agent (no auth required - public endpoint)
```bash
curl -X POST http://localhost:8000/api/v1/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a knight sprite",
    "session_id": "test"
  }'
```

### KB Upload (requires auth)
```bash
curl -X POST http://localhost:8000/api/v1/admin/kb/upload \
  -H "X-API-Key: test-api-key-49a07b1d54218c8df192114e5eb35dcd" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "design.md",
    "content": "Knight character: 8 frames of animation..."
  }'
```

---

## Questions?

Refer to:
- `backend/SECURITY.md` - Detailed security configuration
- `PULL_REQUEST_SUMMARY.md` - What changed in Phase 1
- `CRITICAL_ASSESSMENT_AND_REMEDIATION_PLAN.md` - Full assessment

---

**Ready to proceed? Choose your mode and let's start testing!**
