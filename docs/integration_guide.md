# Frontend Integration Guide - Medium-Priority Features

**Version:** 3.2  
**Date:** 2025-01-04

---

## Overview

This guide explains how to integrate the medium-priority features into your existing `backend/main.py` file.

---

## Step 1: Add Imports to main.py

Add these imports at the top of `backend/main.py`:

```python
# Medium-priority feature imports
from backend.main_endpoints import router as medium_priority_router
from backend.style_presets import get_optimal_preset_for_description
from backend.regeneration_manager import regeneration_manager
```

---

## Step 2: Include Router in FastAPI App

After creating your FastAPI app instance, add:

```python
# In main.py, after: app = FastAPI(...)

# Include medium-priority endpoints
app.include_router(medium_priority_router)
```

---

## Step 3: Initialize Global Instances (if needed)

If your `main.py` doesn't already have these, add to initialization section:

```python
# Task queue (should already exist from high-priority improvements)
from backend.task_queue import task_queue

# Start task queue on application startup
@app.on_event("startup")
async def startup_event():
    await task_queue.start()
    logger.info("Task queue started")

@app.on_event("shutdown")
async def shutdown_event():
    await task_queue.stop()
    logger.info("Task queue stopped")
```

---

## Step 4: Update Existing /api/v1/prompt Endpoint

Modify your existing prompt endpoint to support style presets:

```python
@app.post("/api/v1/prompt")
async def send_prompt(
    request: PromptRequest,
    _rate_limit = Depends(check_rate_limit)
):
    """
    Send prompt to PM agent with optional style preset.
    """
    # ... existing code ...
    
    # NEW: Detect optimal style preset if not specified
    if 'preset' not in request.dict() or not request.preset:
        preset = get_optimal_preset_for_description(request.message)
        logger.info(f"Auto-selected preset: {preset.value}")
    
    # ... rest of existing code ...
```

---

## Step 5: Update /api/v1/execute Endpoint

Modify execute endpoint to create regeneration session:

```python
@app.post("/api/v1/execute", dependencies=[Depends(verify_api_key)])
async def execute_plan(
    request: ExecuteRequest,
    _rate_limit = Depends(check_rate_limit)
):
    """
    Execute approved generation plan.
    """
    # ... existing code ...
    
    # NEW: Create regeneration session for tracking
    session = regeneration_manager.create_session(
        session_id=request.session_id,
        original_prompt=request.plan.get('prompt', ''),
        base_plan=request.plan
    )
    
    # Submit to task queue
    task_id = await task_queue.submit(
        func=generation_function,
        session_id=request.session_id,
        plan=request.plan,
        priority=Priority.NORMAL
    )
    
    # Record as first attempt
    from backend.regeneration_manager import GenerationAttempt
    from datetime import datetime
    
    attempt = GenerationAttempt(
        attempt_id=f"attempt_{task_id}",
        seed=request.plan.get('seed', 42),
        preset=request.plan.get('preset', 'clean_pixel_art'),
        parameters=request.plan,
        timestamp=datetime.now()
    )
    session.add_attempt(attempt)
    
    # ... rest of existing code ...
```

---

## Step 6: Add Validation Result Callback

When validation completes, record results:

```python
# After sprite validation in your generation workflow:

validation_result = validator.validate_frames(output_dir, num_frames=8)

# NEW: Record validation result for regeneration tracking
regeneration_manager.record_validation_result(
    session_id=session_id,
    attempt_id=attempt_id,
    validation_result=validation_result,
    sprite_id=sprite_id if validation_result['valid'] else None
)

# NEW: If validation failed, suggest auto-retry with adjusted parameters
if not validation_result['valid']:
    logger.info("Validation failed, generating adjusted retry attempt")
    retry_attempt = regeneration_manager.regenerate_with_adjusted_parameters(
        session_id=session_id,
        validation_failure=validation_result
    )
    # Optionally auto-submit retry (or return to user for approval)
```

---

## Complete Endpoint List

After integration, your API will have these additional endpoints:

### Style Presets
- `GET /api/v1/presets` - List all presets
- `GET /api/v1/presets/{preset_name}` - Get preset details

### Regeneration
- `POST /api/v1/regenerate` - Regenerate with new seed
- `GET /api/v1/regenerate/{session_id}/comparison` - Get A/B comparison data
- `POST /api/v1/regenerate/{session_id}/mark-best` - Mark best attempt

### Sprite Management
- `GET /api/v1/sprites` - List sprites
- `GET /api/v1/sprites/{sprite_id}` - Get sprite details
- `PUT /api/v1/sprites/edit` - Edit sprite metadata
- `DELETE /api/v1/sprites/delete` - Delete sprite
- `POST /api/v1/sprites/duplicate` - Duplicate sprite
- `POST /api/v1/sprites/export` - Export sprite

### Batch Operations
- `POST /api/v1/batch/csv` - Process CSV batch
- `POST /api/v1/batch/character-set` - Generate character set
- `POST /api/v1/batch/template` - Apply project template
- `GET /api/v1/batch/{batch_id}/status` - Get batch status

### Knowledge Base Admin
- `GET /api/v1/admin/kb/documents` - List documents
- `GET /api/v1/admin/kb/documents/{doc_id}` - Get document details
- `POST /api/v1/admin/kb/reindex` - Re-index document
- `POST /api/v1/admin/kb/upload` - Upload document
- `DELETE /api/v1/admin/kb/documents` - Delete document
- `POST /api/v1/admin/kb/search-test` - Test search
- `GET /api/v1/admin/kb/stats` - Get statistics
- `POST /api/v1/admin/kb/rebuild` - Rebuild index

---

## Testing the Integration

### Test Style Presets
```bash
curl http://localhost:8000/api/v1/presets
```

### Test Sprite List
```bash
curl http://localhost:8000/api/v1/sprites
```

### Test KB Stats
```bash
curl http://localhost:8000/api/v1/admin/kb/stats
```

### Test Regeneration
```bash
curl -X POST http://localhost:8000/api/v1/regenerate \
  -H 'Content-Type: application/json' \
  -d '{"session_id": "test_123", "preset": "detailed_sprite"}'
```

---

## Configuration Updates

Add to your `.env` file:

```bash
# Project path for sprite manager
GBSTUDIO_PROJECT_PATH=/app/project_files/MyGBCGame.gbsproj

# Docs directory for KB admin
PROJECT_DOCS_DIR=/app/project_docs

# Enable auto-retry on validation failure
AUTO_RETRY_ON_VALIDATION_FAILURE=true
```

---

## Next Steps: Frontend UI

With backend complete, you can now build frontend UI for:

1. **Style Preset Selector** - Dropdown in generation form
2. **Regenerate Button** - On sprite results page
3. **A/B Comparison View** - Side-by-side sprite comparison
4. **Sprite Manager UI** - Edit/delete/duplicate/export buttons
5. **Batch Upload Form** - CSV upload interface
6. **KB Admin Panel** - Document management UI

See `frontend/` directory for UI implementation.

---

## Troubleshooting

**"Module not found" errors:**
- Ensure all new `.py` files are in `backend/` directory
- Restart Docker containers: `./stop.sh && ./start.sh`

**"Router already included" errors:**
- Check you haven't included `medium_priority_router` twice
- Ensure imports are at top of file

**Endpoints return 500 errors:**
- Check logs: `docker compose -f docker-compose.intel-mac.yml logs backend`
- Verify all dependencies imported correctly
- Ensure task_queue is started on app startup

---

## File Checklist

Ensure these files exist:

- [ ] `backend/style_presets.py`
- [ ] `backend/regeneration_manager.py`
- [ ] `backend/sprite_manager.py`
- [ ] `backend/batch_generator.py`
- [ ] `backend/kb_admin.py`
- [ ] `backend/main_endpoints.py`
- [ ] This integration guide

Then modify:

- [ ] `backend/main.py` (add imports + router)
- [ ] `.env` (add configuration)

---

**Integration complete when all endpoints return 200 OK on test requests.**
