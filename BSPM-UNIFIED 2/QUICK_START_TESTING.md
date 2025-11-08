# Quick Start: Testing Phase 1 Changes

**Date:** 2025-11-08
**Mode:** Development (Test API Key)
**Prerequisites:** ✅ Ollama running with llama3:8b and nomic-embed-text

---

## Run This on Your Mac

### Option 1: Automated Testing (Recommended)

```bash
cd "/path/to/BSPM-UNIFIED/BSPM-UNIFIED 2"
./test_phase1.sh
```

This script will:
1. ✅ Verify all prerequisites (Ollama, models, Docker)
2. ✅ Start Docker services
3. ✅ Run health checks
4. ✅ Test all security features (API auth, CORS)
5. ✅ Test all functionality (PM Agent, KB, WebSocket, sessions)
6. ✅ Test session persistence across restarts
7. ✅ Test art generation (if ComfyUI ready)

**Expected output:** All tests should show green ✓ checkmarks

---

### Option 2: Manual Testing

#### Start Services
```bash
cd "/path/to/BSPM-UNIFIED/BSPM-UNIFIED 2"
docker compose -f docker-compose.intel-mac.yml up -d
```

#### Wait for Services (60 seconds)
```bash
sleep 60
```

#### Test 1: Health Check
```bash
curl http://localhost:8000/health
# Should return: {"status": "healthy"}
```

#### Test 2: API Key Required
```bash
# Without key - should fail with 401
curl -X POST http://localhost:8000/api/v1/execute \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "plan": []}'

# With key - should succeed with 200
curl -X POST http://localhost:8000/api/v1/execute \
  -H "X-API-Key: test-api-key-49a07b1d54218c8df192114e5eb35dcd" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "plan": []}'
```

#### Test 3: PM Agent (No Auth)
```bash
curl -X POST http://localhost:8000/api/v1/prompt \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "session_id": "test"}'
```

#### Test 4: Knowledge Base (Requires Auth)
```bash
curl -X POST http://localhost:8000/api/v1/admin/kb/upload \
  -H "X-API-Key: test-api-key-49a07b1d54218c8df192114e5eb35dcd" \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.md", "content": "Test document"}'
```

#### Test 5: Session Persistence
```bash
# Create session
curl -X POST http://localhost:8000/api/v1/prompt \
  -H "Content-Type: application/json" \
  -d '{"message": "Test", "session_id": "persist-test"}'

# Restart backend
docker compose -f docker-compose.intel-mac.yml restart backend
sleep 20

# Verify session persisted
curl -X POST http://localhost:8000/api/v1/execute \
  -H "X-API-Key: test-api-key-49a07b1d54218c8df192114e5eb35dcd" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "persist-test", "plan": []}'
```

#### Test 6: Art Generation (Takes 2-5 minutes)
```bash
curl -X POST http://localhost:8000/api/v1/execute \
  -H "X-API-Key: test-api-key-49a07b1d54218c8df192114e5eb35dcd" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "art-test",
    "plan": [{
      "department": "Art",
      "task": "Generate a knight sprite",
      "details": {"style": "pixel art"}
    }]
  }'

# Monitor progress
docker compose -f docker-compose.intel-mac.yml logs -f backend
```

---

## Configuration Details

### Current Setup (Development Mode)
```yaml
Mode: Development
API Key: test-api-key-49a07b1d54218c8df192114e5eb35dcd
CORS Origins: http://localhost:5173, http://localhost:8080
Ollama Model: llama3:8b (✅ Fixed!)
Embedding Model: nomic-embed-text
Backend Port: 8000
ComfyUI Port: 8188
```

### Environment Variables (Already Set in docker-compose.intel-mac.yml)
```bash
GBSTUDIO_PM_MODEL=llama3:8b
GBSTUDIO_EMBEDDING_MODEL=nomic-embed-text
GBSTUDIO_OLLAMA_API_URL=http://host.docker.internal:11434/api/generate
ENVIRONMENT=development
```

---

## Viewing Logs

```bash
# All services
docker compose -f docker-compose.intel-mac.yml logs -f

# Backend only
docker compose -f docker-compose.intel-mac.yml logs -f backend

# ComfyUI only
docker compose -f docker-compose.intel-mac.yml logs -f comfyui
```

---

## Stopping Services

```bash
# Stop all services
docker compose -f docker-compose.intel-mac.yml down

# Stop and remove volumes
docker compose -f docker-compose.intel-mac.yml down -v
```

---

## Expected Results

### ✅ What Should Work
1. **Security:**
   - ✅ `/api/v1/execute` requires API key (401 without, 200 with)
   - ✅ `/api/v1/admin/kb/upload` requires API key
   - ✅ CORS restricted to localhost origins

2. **Functionality:**
   - ✅ PM Agent responds to prompts (with KB context if documents added)
   - ✅ WebSocket endpoint exists at `/ws?session_id=test`
   - ✅ Sessions persist across backend restarts
   - ✅ Art generation queues tasks (actual generation depends on ComfyUI)

3. **Performance:**
   - ✅ Backend starts in ~30 seconds
   - ✅ ComfyUI starts in ~60-120 seconds
   - ✅ API responses <1 second (except art generation)
   - ✅ KB search is fast (O(1) lookups implemented)

### ⚠️ Known Limitations
1. **ComfyUI:** May take 1-2 minutes to fully initialize
2. **First Art Generation:** Slower as ComfyUI loads models
3. **WebSocket:** No authentication yet (planned for Phase 2)

---

## Troubleshooting

### Issue: Backend won't start
```bash
# Check logs
docker compose -f docker-compose.intel-mac.yml logs backend

# Common causes:
# 1. Ollama not running: Check with `curl http://localhost:11434/api/tags`
# 2. Port 8000 in use: `lsof -i :8000`
# 3. Missing secrets: Check `app/secrets/api_keys.txt` exists
```

### Issue: "Model not found" error
```bash
# Verify model name
ollama list | grep llama3:8b

# Pull if missing
ollama pull llama3:8b
ollama pull nomic-embed-text
```

### Issue: 401 Unauthorized
```bash
# Verify API key
cat app/secrets/api_keys.txt
# Should show: test-api-key-49a07b1d54218c8df192114e5eb35dcd

# Use in header
curl -H "X-API-Key: test-api-key-49a07b1d54218c8df192114e5eb35dcd" ...
```

### Issue: ComfyUI not responding
```bash
# Check status
curl http://localhost:8188/system_stats

# ComfyUI may still be initializing (wait 1-2 minutes)
# Check logs
docker compose -f docker-compose.intel-mac.yml logs comfyui
```

---

## Interactive API Documentation

Once backend is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

These provide interactive API testing in your browser.

---

## Next Steps After Testing

1. **If all tests pass:**
   - ✅ Phase 1 is complete and working!
   - Ready to proceed to Phase 2 (architecture refactoring)

2. **If tests fail:**
   - Document the failures
   - Check logs for errors
   - Report issues for fixing

3. **For production deployment:**
   - Generate secure API key: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
   - Set `GBSTUDIO_ALLOWED_ORIGINS` to your domain
   - Set `ENVIRONMENT=production`
   - Review `backend/SECURITY.md` for full checklist

---

## Support Files

- **CONFIGURATION_GUIDE.md** - Complete configuration reference
- **backend/SECURITY.md** - Security documentation
- **PULL_REQUEST_SUMMARY.md** - What changed in Phase 1
- **test_phase1.sh** - Automated testing script

---

**Ready to test? Run `./test_phase1.sh` and let's see the results!**
