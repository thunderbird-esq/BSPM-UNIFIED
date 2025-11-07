"""
GBStudio Automation Hub - FastAPI Backend (Refactored)
Version: 3.4
Platform: Intel Mac (macOS Ventura) + Docker

Complete production-ready backend with modular router architecture:
- PM Agent conversation with approval workflow
- ComfyUI integration for sprite generation
- FAISS knowledge base with conversation memory
- GBStudio project manipulation
- Style presets, regeneration, sprite management, batch ops, KB admin
- Security: API key auth, rate limiting, input sanitization
- Task queue: Priority queue with resource monitoring
- Graceful degradation: Fallback responses when services fail
- Retry logic: Exponential backoff + circuit breakers
- Structured logging: JSON logs with rotation
- Metrics: Prometheus monitoring

REFACTORED: Split into feature-based routers for better maintainability.
"""

import os
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.dependencies import settings, app_state, logger
from backend.logging_config import LoggerAdapter
from backend.task_queue import task_queue
from backend.metrics import http_requests_total, http_request_duration_seconds

# Import all routers
from backend.routers import health, chat, generation, sprites, batch, admin


# ============================================================================
# FastAPI App Initialization
# ============================================================================

app = FastAPI(
    title="GBStudio Automation Hub API",
    version="3.4",
    description="AI-powered Game Boy Color asset generation system (Refactored Architecture)",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
frontend_path = Path("/app/frontend")
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


# ============================================================================
# Application Lifecycle Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Start background services on application startup."""
    await task_queue.start()
    logger.info("Task queue started")
    logger.info("GBStudio Automation Hub v3.4 (Refactored) started")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown of background tasks and connections."""
    await task_queue.stop()
    logger.info("Task queue stopped")
    logger.info("GBStudio Automation Hub v3.4 shutdown complete")


# ============================================================================
# Middleware
# ============================================================================

@app.middleware("http")
async def add_correlation_id_and_metrics(request: Request, call_next):
    """
    Add correlation ID to requests and track metrics.

    Automatically adds X-Correlation-ID header to all requests and responses,
    tracks request duration and status codes in Prometheus metrics.
    """
    correlation_id = request.headers.get("X-Correlation-ID") or f"req_{int(time.time())}_{os.urandom(4).hex()}"

    # Create logger with correlation context
    req_logger = LoggerAdapter(logger, {'correlation_id': correlation_id})
    req_logger.info(f"Request started: {request.method} {request.url.path}")

    # Track with metrics
    method = request.method
    endpoint = request.url.path

    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Response-Time"] = f"{duration:.3f}s"

    # Record metrics
    http_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status=str(response.status_code)
    ).inc()

    http_request_duration_seconds.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)

    req_logger.info(
        f"Request completed: {request.method} {request.url.path}",
        extra={'duration_seconds': duration, 'status_code': response.status_code}
    )

    return response


# ============================================================================
# Router Registration
# ============================================================================

# Health & Metrics (no prefix, root level endpoints)
app.include_router(
    health.router,
    tags=["Health & Monitoring"]
)

# Chat & PM Agent
app.include_router(
    chat.router,
    tags=["Chat & PM Agent"]
)

# Generation & Regeneration
app.include_router(
    generation.router,
    tags=["Generation & Presets"]
)

# Sprite Management
app.include_router(
    sprites.router,
    tags=["Sprite Management"]
)

# Batch Operations
app.include_router(
    batch.router,
    tags=["Batch Operations"]
)

# Knowledge Base Admin
app.include_router(
    admin.router,
    tags=["Knowledge Base Admin"]
)


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
