# WORKSTREAM 2 - Quick Reference Guide

## What Was Implemented

### 1. Art Generation (/api/v1/execute)
**Before:** Returned "Art generation not yet implemented"
**After:** Executes actual ComfyUI workflows

```python
# Usage in execute endpoint
art_result = await execute_art_task(
    task=task,
    session_id=request.session_id,
    correlation_id=correlation_id,
    preset=preset,
    timeout=300  # 5 minutes
)
```

### 2. Knowledge Base Integration (/api/v1/prompt)
**Before:** `kb_context = "No relevant documentation found."`
**After:** Actual semantic search of project documentation

```python
# Searches KB and formats results
kb = KnowledgeBase(...)
search_results = kb.search(query=request.message, k=3)
relevant_results = [r for r in search_results if r['score'] < 1.5]
# Formats as markdown for LLM
```

### 3. WebSocket Endpoint (/ws)
**Before:** Did not exist
**After:** Full WebSocket support for real-time updates

```python
# Connect
ws://localhost:8000/ws?session_id=your_session

# Send progress
await ws_manager.send_progress_update(
    session_id="abc123",
    task_id="task_1",
    progress=50.0,
    status="processing"
)
```

### 4. Session Persistence
**Before:** In-memory only (`sessions: Dict[str, Dict] = {}`)
**After:** File-based persistent storage

```python
# Sessions survive restarts
session_manager = SessionManager(
    storage_path="/app/agent_memory/sessions",
    expiration_hours=24
)
```

### 5. Regeneration Manager
**Before:** Partially integrated
**After:** Fully integrated with execute endpoint

## File Locations

### New Files
- `/home/user/BSPM-UNIFIED/BSPM-UNIFIED 2/backend/websocket.py`
- `/home/user/BSPM-UNIFIED/BSPM-UNIFIED 2/backend/session_manager.py`

### Modified Files
- `/home/user/BSPM-UNIFIED/BSPM-UNIFIED 2/backend/main.py`
- `/home/user/BSPM-UNIFIED/BSPM-UNIFIED 2/backend/metrics.py`

## Key Functions

### Execute Art Task
```python
async def execute_art_task(
    task: DelegationTask,
    session_id: str,
    correlation_id: str,
    preset: Optional[str] = None,
    timeout: int = 300
) -> Dict[str, Any]
```
**Location:** `backend/main.py:516-629`

### WebSocket Manager
```python
class ConnectionManager:
    async def connect(websocket, session_id)
    async def send_to_session(message, session_id)
    async def send_progress_update(session_id, task_id, progress, status)
```
**Location:** `backend/websocket.py`

### Session Manager
```python
class SessionManager:
    def create_session(session_id, initial_data)
    def get_session(session_id)
    def update_session(session_id, data)
```
**Location:** `backend/session_manager.py`

## Testing Commands

### Test Art Generation
```bash
curl -X POST http://localhost:8000/api/v1/execute \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test",
    "plan": [{
      "department": "Art",
      "task": "Generate knight sprite",
      "details": {"style": "pixel art"}
    }]
  }'
```

### Test KB Integration
```bash
# 1. Upload document
curl -X POST http://localhost:8000/api/v1/admin/kb/upload \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "design.md",
    "content": "Knight character design guidelines..."
  }'

# 2. Test search
curl -X POST http://localhost:8000/api/v1/prompt \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a knight sprite"}'
```

### Test WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8000/ws?session_id=test');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

### Test Session Persistence
```bash
# Create session
curl -X POST http://localhost:8000/api/v1/prompt \
  -d '{"message": "test", "session_id": "persist_test"}'

# Restart server
docker-compose restart backend

# Verify session exists
ls /app/agent_memory/sessions/session_persist_test.json
```

## Important Notes

1. **Art Generation Timeout:** Default 5 minutes, configurable
2. **KB Relevance Threshold:** L2 distance < 1.5 (similarity > 0.7)
3. **Session Expiration:** 24 hours by default
4. **WebSocket Auth:** Not implemented yet - TODO
5. **Metrics:** All operations tracked in Prometheus

## Configuration

### Environment Variables
- `GBSTUDIO_COMFYUI_API_URL` - ComfyUI endpoint (default: http://comfyui:8188)
- `GBSTUDIO_OLLAMA_EMBEDDINGS_URL` - Ollama embeddings (default: http://ollama:11434/api/embeddings)
- `GBSTUDIO_VECTORSTORE_PATH` - KB storage (default: /app/vectorstore)
- `GBSTUDIO_AGENT_MEMORY_PATH` - Sessions storage (default: /app/agent_memory)

## Common Issues

### Issue: "Art generation not yet implemented"
**Solution:** Check ComfyUI service is running and accessible

### Issue: KB search fails
**Solution:** Check Ollama service is running and embedding model is loaded

### Issue: Sessions not persisting
**Solution:** Check `/app/agent_memory/sessions/` directory has write permissions

### Issue: WebSocket connection refused
**Solution:** Check uvicorn is running with WebSocket support (uvicorn[standard])

## Code Patterns

### Async Error Handling
```python
try:
    result = await asyncio.wait_for(operation(), timeout=300)
except asyncio.TimeoutError:
    return {"status": "failed", "error": "timeout"}
except Exception as e:
    logger.error(f"Error: {e}", exc_info=True)
    return {"status": "failed", "error": str(e)}
```

### Session Manager Usage
```python
# Always check if initialized
if 'session_manager' in globals():
    session_manager.update_session(session_id, data)
else:
    # Fallback to in-memory
    sessions[session_id] = data
```

### WebSocket Broadcasting
```python
# Import global manager
from backend.websocket import manager as ws_manager

# Send update
await ws_manager.send_progress_update(
    session_id="abc",
    task_id="task_1",
    progress=75.0,
    status="processing",
    message="Generating frames..."
)
```

## Metrics to Monitor

- `sprite_generation_requests_total{status="success|failed|timeout"}`
- `sprite_generation_duration_seconds`
- `pm_agent_requests_total{requires_approval="true|false"}`
- `knowledge_base_searches_total`
- `service_health{service="comfyui|ollama"}`

Access metrics at: `http://localhost:8000/metrics`
