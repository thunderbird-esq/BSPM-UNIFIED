"""
GBStudio Automation Hub - FastAPI Backend
Version: 3.3
Platform: Intel Mac (macOS Ventura) + Docker

Complete production-ready backend with:
- PM Agent conversation with approval workflow
- ComfyUI integration for sprite generation
- FAISS knowledge base with conversation memory
- GBStudio project manipulation
- Medium-priority features: style presets, regeneration, sprite management, batch ops, KB admin
- Security: API key auth, rate limiting, input sanitization
- Task queue: Priority queue with resource monitoring
- Graceful degradation: Fallback responses when services fail
- Retry logic: Exponential backoff + circuit breakers
- Structured logging: JSON logs with rotation
- Metrics: Prometheus monitoring
"""

import os
import json
import hashlib
import asyncio
import time
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
from uuid import uuid4

import aiohttp
import requests
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, Depends, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, validator, Field
from pydantic_settings import BaseSettings
import uvicorn

# Logging setup (MUST be first)
from logging_config import setup_logging, LoggerAdapter

# Setup structured logging with rotation
logger = setup_logging(
    log_dir="/app/logs",
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    max_bytes=10 * 1024 * 1024,  # 10MB
    backup_count=5
)

# Security and task queue
from security import check_rate_limit, verify_api_key, api_key_manager, rate_limiter
from task_queue import task_queue, Priority

# Medium-priority features
from style_presets import StylePreset, get_preset_by_name, list_presets, get_optimal_preset_for_description
from regeneration_manager import regeneration_manager, GenerationAttempt
from sprite_manager import create_sprite_manager
from batch_generator import create_batch_generator
from kb_admin import create_kb_admin

# Graceful degradation
from graceful_degradation import (
    fallback_on_failure,
    skip_on_failure,
    degraded_mode,
    FallbackResponses,
    get_degradation_warning
)

# Retry logic with circuit breakers
from retry_logic import (
    retry_with_backoff,
    ollama_circuit_breaker,
    comfyui_circuit_breaker,
    CircuitBreakerOpen,
    RetryExhausted
)

# Metrics
from metrics import metrics, MetricsCollector


class Settings(BaseSettings):
    """Application configuration with validation"""
    
    # Service URLs
    ollama_api_url: str = "http://ollama:11434/api/generate"
    ollama_embeddings_url: str = "http://ollama:11434/api/embeddings"
    ollama_tags_url: str = "http://ollama:11434/api/tags"
    comfyui_api_url: str = "http://comfyui:8188"
    
    # Paths
    project_files_path: str = "/app/project_files"
    workflow_template_path: str = "/workflows/workflow_pixel_art.json"
    temp_outputs_path: str = "/app/temp_outputs"
    vectorstore_path: str = "/app/vectorstore"
    agent_memory_path: str = "/app/agent_memory"
    gbstudio_project_path: str = "/app/project_files/MyGBCGame.gbsproj"
    project_docs_dir: str = "/app/project_docs"
    
    # Agent configuration
    pm_model: str = "llama3"
    embedding_model: str = "nomic-embed-text"
    default_timeout: int = 90

    # Security configuration
    cors_origins: str = "http://localhost:8000,http://localhost:5173,http://localhost:3000"
    environment: str = "development"
    
    # Generation parameters
    sprite_width: int = 32
    sprite_height: int = 32
    num_frames: int = 8
    generation_timeout: int = 360  # 6 minutes
    
    @validator("project_files_path")
    def path_must_exist(cls, v):
        if not os.path.exists(v):
            logger.warning(f"Path does not exist: {v}, will be created")
            os.makedirs(v, exist_ok=True)
        return v
    
    class Config:
        env_prefix = "GBSTUDIO_"
        case_sensitive = False


settings = Settings()

# Create required directories
os.makedirs(settings.temp_outputs_path, exist_ok=True)
os.makedirs(settings.vectorstore_path, exist_ok=True)
os.makedirs(settings.agent_memory_path, exist_ok=True)
os.makedirs(os.path.join(settings.agent_memory_path, "conversations"), exist_ok=True)
os.makedirs(settings.project_docs_dir, exist_ok=True)


# ============================================================================
# Pydantic Models - Core
# ============================================================================

class PromptRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = None
    preset: Optional[str] = None


class DelegationTask(BaseModel):
    department: str
    task: str
    details: Optional[Dict[str, Any]] = {}


class ExecutionRequest(BaseModel):
    plan: List[DelegationTask]
    session_id: str


class HealthResponse(BaseModel):
    backend: str
    timestamp: str
    uptime_seconds: float
    services: Dict[str, Any]


# ============================================================================
# Pydantic Models - Medium-Priority Features
# ============================================================================

class StylePresetRequest(BaseModel):
    preset_name: str


class RegenerateRequest(BaseModel):
    session_id: str
    preset: Optional[str] = None


class SpriteEditRequest(BaseModel):
    sprite_id: str
    name: Optional[str] = None
    sprite_type: Optional[str] = None


class SpriteDeleteRequest(BaseModel):
    sprite_id: str
    delete_file: bool = True


class SpriteDuplicateRequest(BaseModel):
    sprite_id: str
    new_name: str
    apply_variation: bool = False
    variation_type: str = "hue_shift"


class SpriteExportRequest(BaseModel):
    sprite_id: str
    export_format: str = "grid"
    scale: int = 1


class BatchCSVRequest(BaseModel):
    csv_path: str
    session_id: str


class CharacterSetRequest(BaseModel):
    character_name: str
    style: str
    session_id: str
    include_actions: Optional[List[str]] = None


class ProjectTemplateRequest(BaseModel):
    template_name: str
    session_id: str


class DocumentUploadRequest(BaseModel):
    filename: str
    content: str


class SearchTestRequest(BaseModel):
    query: str
    limit: int = 5


# ============================================================================
# Application State
# ============================================================================

# In-memory session storage
sessions: Dict[str, Dict] = {}

# Application startup time for uptime calculation
START_TIME = time.time()


# ============================================================================
# FastAPI App Initialization
# ============================================================================

app = FastAPI(
    title="GBStudio Automation Hub API",
    version="3.3",
    description="AI-powered Game Boy Color asset generation system"
)

# CORS middleware with secure configuration
# Parse CORS origins from settings (comma-separated string)
allowed_origins = [origin.strip() for origin in settings.cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Correlation-ID"],
    expose_headers=["X-Correlation-ID", "X-Response-Time"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Only add HSTS in production with HTTPS
        if settings.environment.lower() == "production" and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"

        return response

app.add_middleware(SecurityHeadersMiddleware)

# Mount static files (frontend)
frontend_path = Path("/app/frontend")
if frontend_path.exists():
    # Mount at /frontend for index.html asset paths
    app.mount("/frontend", StaticFiles(directory=str(frontend_path)), name="frontend")
    # Also mount at /static for backward compatibility
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


# ============================================================================
# Application Lifecycle Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Start background services on application startup"""
    await task_queue.start()
    logger.info("Task queue started")

    # Initialize knowledge base
    from memory.knowledge_base import initialize_kb
    initialize_kb(
        vectorstore_path=settings.vectorstore_path,
        embedding_url=settings.ollama_embeddings_url,
        embedding_model=settings.embedding_model
    )
    logger.info("Knowledge base initialized")

    logger.info("GBStudio Automation Hub v3.3 started")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown of background tasks and connections"""
    await task_queue.stop()
    logger.info("Task queue stopped")
    logger.info("GBStudio Automation Hub backend v3.3 shutdown complete")


# ============================================================================
# Middleware
# ============================================================================

@app.middleware("http")
async def add_correlation_id_and_metrics(request: Request, call_next):
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
    from metrics import http_requests_total, http_request_duration_seconds
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
# Utility Functions
# ============================================================================

def generate_correlation_id() -> str:
    """Generate unique correlation ID for logging"""
    return f"req_{int(time.time())}_{os.urandom(4).hex()}"


# ============================================================================
# PM Agent Functions
# ============================================================================

PM_AGENT_PROMPT = """You are an expert Project Manager AI for a Game Boy Color game development studio. Your role is to:
1. Understand user requests for game assets
2. Propose detailed implementation plans
3. Delegate tasks to specialist departments (Art, Code, Music)
4. Seek user approval before execution

RECENT CONVERSATION:
{recent_context}

RELEVANT DOCUMENTATION:
{kb_context}

USER REQUEST:
{user_message}

RESPOND IN VALID JSON FORMAT (no markdown, no code blocks):
{{
  "response_to_user": "your message to the user explaining the plan",
  "needs_approval": true/false,
  "delegation_plan": [
    {{
      "department": "Art",
      "task": "detailed task description",
      "details": {{"style": "pixel art", "resolution": "32x32", "frames": 8}}
    }}
  ]
}}

CRITICAL: Your response must be valid JSON that can be parsed with json.loads(). Do not wrap it in markdown code blocks."""


def fallback_pm_response(model: str, prompt: str, correlation_id: str, timeout: int = 90) -> Dict[str, Any]:
    """Fallback response when Ollama is unavailable"""
    logger.warning("Using fallback PM response", extra={'correlation_id': correlation_id})
    return FallbackResponses.pm_agent_unavailable(prompt)


@fallback_on_failure(
    fallback_func=fallback_pm_response,
    service_name='ollama',
    exceptions=(Exception,)
)
@ollama_circuit_breaker
@retry_with_backoff(
    max_attempts=3,
    base_delay=1.0,
    exceptions=(aiohttp.ClientError,)
)
async def call_ollama_agent(
    model: str,
    prompt: str,
    correlation_id: str,
    timeout: int = 90
) -> Dict[str, Any]:
    """Call Ollama API for LLM inference with retry and circuit breaker"""
    try:
        async with aiohttp.ClientSession() as session:
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            async with session.post(
                settings.ollama_api_url,
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "top_k": 40
                    }
                },
                timeout=timeout_obj
            ) as response:
                response.raise_for_status()
                result = await response.json()

        response_text = result.get("response", "")

        try:
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            parsed = json.loads(response_text)
            logger.info("Ollama response parsed successfully", extra={"correlation_id": correlation_id})
            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Ollama JSON response: {e}", extra={"correlation_id": correlation_id})
            return {
                "response_to_user": response_text,
                "needs_approval": False,
                "delegation_plan": []
            }

    except asyncio.TimeoutError:
        logger.error(f"Ollama request timed out after {timeout}s", extra={"correlation_id": correlation_id})
        raise HTTPException(status_code=504, detail=f"LLM request timed out after {timeout} seconds")

    except aiohttp.ClientError as e:
        logger.error(f"Ollama request failed: {e}", extra={"correlation_id": correlation_id})
        raise


def get_recent_conversation_context(session_id: str, window: int = 6) -> str:
    """Retrieve recent conversation history for context"""
    conversation_file = os.path.join(settings.agent_memory_path, "conversations", f"{session_id}.jsonl")
    
    if not os.path.exists(conversation_file):
        return "No previous conversation."
    
    with open(conversation_file, 'r') as f:
        lines = f.readlines()
    
    recent_turns = lines[-window:] if len(lines) > window else lines
    
    context_parts = []
    for line in recent_turns:
        try:
            turn = json.loads(line)
            context_parts.append(f"User: {turn['user_message']}")
            context_parts.append(f"PM: {turn['pm_response']}")
            if turn.get('action_taken'):
                context_parts.append(f"Action: {turn['action_taken']}")
        except json.JSONDecodeError:
            continue
    
    return "\n".join(context_parts) if context_parts else "No previous conversation."


def save_conversation_turn(
    session_id: str,
    user_message: str,
    pm_response: str,
    action_taken: Optional[str] = None,
    correlation_id: Optional[str] = None
):
    """Persist conversation turn to JSONL file"""
    conversation_file = os.path.join(settings.agent_memory_path, "conversations", f"{session_id}.jsonl")
    
    turn = {
        "turn_id": hashlib.sha256(f"{user_message}{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16],
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat(),
        "user_message": user_message,
        "pm_response": pm_response,
        "action_taken": action_taken,
        "correlation_id": correlation_id
    }
    
    with open(conversation_file, 'a') as f:
        f.write(json.dumps(turn) + '\n')
    
    logger.info(f"Saved conversation turn for session {session_id}", extra={"correlation_id": correlation_id or "none"})


# ============================================================================
# Core Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Serve frontend index.html"""
    index_path = Path("/app/frontend/index.html")
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "GBStudio Automation Hub API", "version": "3.3"}


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check for all services"""
    health_status = {
        "backend": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "services": {}
    }
    
    # Check Ollama
    try:
        start = time.time()
        async with aiohttp.ClientSession() as session:
            timeout_obj = aiohttp.ClientTimeout(total=3)
            async with session.get(settings.ollama_tags_url, timeout=timeout_obj) as response:
                latency = round((time.time() - start) * 1000, 2)

                if response.status == 200:
                    data = await response.json()
                    models = data.get("models", [])
                    model_names = [m["name"] for m in models]

                    health_status["services"]["ollama"] = {
                        "status": "healthy",
                        "latency_ms": latency,
                        "models_loaded": model_names,
                        "required_models": [settings.pm_model, settings.embedding_model],
                        "models_ok": all(m in model_names for m in [settings.pm_model, settings.embedding_model])
                    }

                    # Update metrics
                    metrics.update_service_health('ollama', healthy=True, latency_ms=latency)
                else:
                    health_status["services"]["ollama"] = {
                        "status": "degraded",
                        "latency_ms": latency,
                        "error": f"HTTP {response.status}"
                    }
                    health_status["backend"] = "degraded"
                    metrics.update_service_health('ollama', healthy=False)

    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        health_status["services"]["ollama"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["backend"] = "degraded"
        metrics.update_service_health('ollama', healthy=False)
    
    # Check ComfyUI
    try:
        start = time.time()
        async with aiohttp.ClientSession() as session:
            timeout_obj = aiohttp.ClientTimeout(total=3)
            async with session.get(f"{settings.comfyui_api_url}/system_stats", timeout=timeout_obj) as response:
                latency = round((time.time() - start) * 1000, 2)

                if response.status == 200:
                    stats = await response.json()
                    health_status["services"]["comfyui"] = {
                        "status": "healthy",
                        "latency_ms": latency,
                        "device": stats.get("devices", [{}])[0].get("type", "unknown"),
                        "queue_remaining": 0
                    }
                    metrics.update_service_health('comfyui', healthy=True, latency_ms=latency)
                else:
                    health_status["services"]["comfyui"] = {
                        "status": "degraded",
                        "latency_ms": latency,
                        "error": f"HTTP {response.status}"
                    }
                    health_status["backend"] = "degraded"
                    metrics.update_service_health('comfyui', healthy=False)

    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        health_status["services"]["comfyui"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["backend"] = "degraded"
        metrics.update_service_health('comfyui', healthy=False)
    
    # Check task queue
    queue_stats = task_queue.get_queue_stats()
    health_status["services"]["task_queue"] = {
        "status": "healthy",
        "pending_tasks": queue_stats["pending"],
        "running_tasks": queue_stats["running"],
        "completed_tasks": queue_stats["completed"],
        "failed_tasks": queue_stats["failed"],
        "resource_overload": queue_stats["resource_overload"]
    }
    
    # Add degradation status
    degradation_status = degraded_mode.get_status()
    if degradation_status:
        health_status["degraded_services"] = degradation_status
        health_status["degradation_warning"] = get_degradation_warning()
    
    # Add circuit breaker status
    health_status["circuit_breakers"] = {
        "ollama": ollama_circuit_breaker.get_status(),
        "comfyui": comfyui_circuit_breaker.get_status()
    }
    
    status_code = 200 if health_status["backend"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    metrics.update_system_metrics()
    return Response(
        content=metrics.export_metrics(),
        media_type="text/plain"
    )


@app.post("/api/v1/prompt")
async def handle_prompt(request: PromptRequest, _rate_limit = Depends(check_rate_limit)):
    """Handle user prompt with style preset support"""
    correlation_id = generate_correlation_id()
    session_id = request.session_id or str(uuid4())
    
    # Create logger with context
    req_logger = LoggerAdapter(logger, {
        'correlation_id': correlation_id,
        'session_id': session_id
    })
    
    req_logger.info(f"Processing prompt: {request.message[:50]}...")
    
    # Auto-detect style preset if not specified
    if not request.preset:
        preset = get_optimal_preset_for_description(request.message)
        req_logger.info(f"Auto-selected preset: {preset.value}")
    
    recent_context = get_recent_conversation_context(session_id)
    kb_context = "No relevant documentation found."
    
    full_prompt = PM_AGENT_PROMPT.format(
        recent_context=recent_context,
        kb_context=kb_context,
        user_message=request.message
    )
    
    try:
        # Track PM agent call
        start_time = time.time()
        pm_response = await call_ollama_agent(
            model=settings.pm_model,
            prompt=full_prompt,
            correlation_id=correlation_id,
            timeout=settings.default_timeout
        )
        duration = time.time() - start_time
        
        # Record metrics
        metrics.record_pm_agent_request(
            requires_approval=pm_response.get("needs_approval", False),
            duration_seconds=duration
        )
        
        save_conversation_turn(
            session_id=session_id,
            user_message=request.message,
            pm_response=pm_response.get("response_to_user", ""),
            correlation_id=correlation_id
        )
        
        return {
            "message": pm_response.get("response_to_user", "I can help with that."),
            "plan": pm_response.get("delegation_plan", []),
            "requires_approval": pm_response.get("needs_approval", False),
            "session_id": session_id,
            "correlation_id": correlation_id,
            "degraded": pm_response.get("degraded", False)
        }
    
    except CircuitBreakerOpen as e:
        req_logger.error(f"Circuit breaker open: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except RetryExhausted as e:
        req_logger.error(f"Retry exhausted: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        req_logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/execute", dependencies=[Depends(verify_api_key)])
async def handle_execution(request: ExecutionRequest, _rate_limit = Depends(check_rate_limit)):
    """Execute approved delegation plan with regeneration tracking"""
    correlation_id = generate_correlation_id()

    req_logger = LoggerAdapter(logger, {
        'correlation_id': correlation_id,
        'session_id': request.session_id
    })

    req_logger.info(f"Executing plan: {len(request.plan)} tasks")

    # Create regeneration session for tracking
    session = regeneration_manager.create_session(
        session_id=request.session_id,
        original_prompt=request.plan[0].task if request.plan else '',
        base_plan={'plan': [task.dict() for task in request.plan]}
    )

    results = []
    task_ids = []

    # Process each task in the plan
    for task in request.plan:
        if task.department == "Art":
            try:
                # Extract parameters from task details or use defaults
                details = task.details or {}
                positive_prompt = task.task  # The task description is the prompt
                negative_prompt = details.get('negative_prompt', 'blurry, low quality, bad anatomy')
                preset_name = details.get('preset', 'clean_pixel_art')
                seed = details.get('seed')

                # Get style preset
                try:
                    preset = get_preset_by_name(preset_name)
                    # Build enhanced prompts with preset boost
                    enhanced_positive = f"{positive_prompt}, {preset.positive_boost}"
                    enhanced_negative = f"{negative_prompt}, {preset.negative_boost}"
                except ValueError:
                    # Fall back to defaults if preset not found
                    req_logger.warning(f"Preset '{preset_name}' not found, using clean_pixel_art")
                    preset = get_preset_by_name('clean_pixel_art')
                    enhanced_positive = f"{positive_prompt}, {preset.positive_boost}"
                    enhanced_negative = f"{negative_prompt}, {preset.negative_boost}"

                # Create generation function for task queue
                async def generate_sprite():
                    from comfyui.executor import execute_spritesheet_generation
                    result = await execute_spritesheet_generation(
                        positive_prompt=enhanced_positive,
                        negative_prompt=enhanced_negative,
                        comfyui_url=settings.comfyui_api_url,
                        seed=seed
                    )
                    return result

                # Submit to task queue
                task_id = await task_queue.submit(
                    func=generate_sprite,
                    session_id=request.session_id,
                    plan={'task': task.task, 'details': details},
                    priority=Priority.NORMAL
                )

                task_ids.append(task_id)

                results.append({
                    "department": "Art",
                    "task": task.task,
                    "status": "queued",
                    "task_id": task_id,
                    "message": "Sprite generation queued successfully"
                })

                req_logger.info(f"Art task queued: {task_id}")

            except Exception as e:
                req_logger.error(f"Failed to queue Art task: {e}", exc_info=True)
                results.append({
                    "department": "Art",
                    "task": task.task,
                    "status": "failed",
                    "error": str(e),
                    "message": f"Failed to queue generation: {str(e)}"
                })
        else:
            # Other departments not yet implemented
            results.append({
                "department": task.department,
                "task": task.task,
                "status": "unsupported",
                "message": f"Department {task.department} not yet implemented"
            })

    # Return first task_id as prompt_id for frontend compatibility
    prompt_id = task_ids[0] if task_ids else None

    return {
        "status": "queued" if task_ids else "completed",
        "results": results,
        "session_id": request.session_id,
        "correlation_id": correlation_id,
        "prompt_id": prompt_id,  # For frontend WebSocket tracking
        "task_ids": task_ids  # All task IDs for multi-task plans
    }


# ============================================================================
# Style Presets Endpoints
# ============================================================================

@app.get("/api/v1/presets")
async def get_style_presets():
    """List all available style presets"""
    return {
        "presets": list_presets(),
        "default": "clean_pixel_art"
    }


@app.get("/api/v1/presets/{preset_name}")
async def get_preset_details(preset_name: str):
    """Get details for a specific style preset"""
    try:
        params = get_preset_by_name(preset_name)
        return {
            "preset_name": preset_name,
            "parameters": params.to_dict(),
            "positive_boost": params.positive_boost,
            "negative_boost": params.negative_boost
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# Regeneration Endpoints
# ============================================================================

@app.post("/api/v1/regenerate")
async def regenerate_sprite(request: RegenerateRequest, _rate_limit = Depends(check_rate_limit)):
    """Regenerate sprite with new seed and optional different preset"""
    try:
        session = regeneration_manager.get_session(request.session_id)
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {request.session_id} not found. Create initial generation first."
            )
        
        attempt = regeneration_manager.regenerate_with_new_seed(request.session_id, preset=request.preset)
        
        return {
            "session_id": request.session_id,
            "attempt_id": attempt.attempt_id,
            "seed": attempt.seed,
            "preset": attempt.preset,
            "status": "queued"
        }
        
    except Exception as e:
        logger.error(f"Regeneration failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/regenerate/{session_id}/comparison")
async def get_comparison_data(session_id: str):
    """Get comparison data for all attempts in a regeneration session"""
    data = regeneration_manager.get_comparison_data(session_id)
    
    if not data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    return data


@app.post("/api/v1/regenerate/{session_id}/mark-best")
async def mark_best_attempt(session_id: str, attempt_id: str):
    """Mark an attempt as the best result"""
    session = regeneration_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    try:
        session.mark_best(attempt_id)
        return {
            "session_id": session_id,
            "best_attempt_id": attempt_id,
            "status": "success"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Sprite Management Endpoints
# ============================================================================

@app.put("/api/v1/sprites/edit")
async def edit_sprite(request: SpriteEditRequest):
    """Edit sprite metadata"""
    try:
        manager = create_sprite_manager(settings.gbstudio_project_path)
        sprite = manager.edit_sprite(
            sprite_id=request.sprite_id,
            name=request.name,
            sprite_type=request.sprite_type
        )
        return sprite
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Sprite edit failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/sprites/delete")
async def delete_sprite(request: SpriteDeleteRequest):
    """Delete sprite from project"""
    try:
        manager = create_sprite_manager(settings.gbstudio_project_path)
        success = manager.delete_sprite(
            sprite_id=request.sprite_id,
            delete_file=request.delete_file
        )
        
        return {
            "sprite_id": request.sprite_id,
            "deleted": success,
            "file_deleted": request.delete_file
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Sprite deletion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/sprites/duplicate")
async def duplicate_sprite(request: SpriteDuplicateRequest):
    """Duplicate sprite with optional variation"""
    try:
        manager = create_sprite_manager(settings.gbstudio_project_path)
        new_sprite = manager.duplicate_sprite(
            sprite_id=request.sprite_id,
            new_name=request.new_name,
            apply_variation=request.apply_variation,
            variation_type=request.variation_type
        )
        return new_sprite
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Sprite duplication failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/sprites/export")
async def export_sprite(request: SpriteExportRequest):
    """Export sprite as standalone PNG"""
    try:
        manager = create_sprite_manager(settings.gbstudio_project_path)
        output_path = f"{settings.temp_outputs_path}/export_{request.sprite_id}.png"
        result_path = manager.export_sprite(
            sprite_id=request.sprite_id,
            output_path=output_path,
            export_format=request.export_format,
            scale=request.scale
        )
        
        return {
            "sprite_id": request.sprite_id,
            "export_path": result_path,
            "format": request.export_format,
            "scale": request.scale
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Sprite export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sprites")
async def list_sprites(filter_type: Optional[str] = None, search_name: Optional[str] = None):
    """List all sprites in project with optional filtering"""
    try:
        manager = create_sprite_manager(settings.gbstudio_project_path)
        sprites = manager.list_sprites(filter_type=filter_type, search_name=search_name)
        
        return {
            "total": len(sprites),
            "sprites": sprites
        }
        
    except Exception as e:
        logger.error(f"List sprites failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sprites/{sprite_id}")
async def get_sprite_info(sprite_id: str):
    """Get detailed information about a sprite"""
    try:
        manager = create_sprite_manager(settings.gbstudio_project_path)
        info = manager.get_sprite_info(sprite_id)
        return info
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Get sprite info failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Batch Generation Endpoints
# ============================================================================

@app.post("/api/v1/batch/csv")
async def process_batch_csv(request: BatchCSVRequest, _rate_limit = Depends(check_rate_limit)):
    """Process CSV file with batch sprite requests"""
    try:
        generator = create_batch_generator(task_queue)
        result = await generator.process_csv(csv_path=request.csv_path, session_id=request.session_id)
        return result
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"CSV batch processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/batch/character-set")
async def generate_character_set(request: CharacterSetRequest, _rate_limit = Depends(check_rate_limit)):
    """Generate complete animation set for a character"""
    try:
        generator = create_batch_generator(task_queue)
        result = await generator.generate_character_set(
            character_name=request.character_name,
            style=request.style,
            session_id=request.session_id,
            include_actions=request.include_actions
        )
        return result
        
    except Exception as e:
        logger.error(f"Character set generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/batch/template")
async def apply_project_template(request: ProjectTemplateRequest, _rate_limit = Depends(check_rate_limit)):
    """Apply project template to generate multiple sprites"""
    try:
        generator = create_batch_generator(task_queue)
        result = await generator.apply_project_template(
            template_name=request.template_name,
            session_id=request.session_id
        )
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Template application failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/batch/{batch_id}/status")
async def get_batch_status(batch_id: str, task_ids: List[str]):
    """Get status of batch generation"""
    try:
        generator = create_batch_generator(task_queue)
        status = generator.get_batch_status(task_ids)
        
        return {
            "batch_id": batch_id,
            **status
        }
        
    except Exception as e:
        logger.error(f"Batch status check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Knowledge Base Admin Endpoints
# ============================================================================

@app.get("/api/v1/admin/kb/documents")
async def list_kb_documents(filter_type: Optional[str] = None):
    """List all documents in knowledge base"""
    try:
        from memory.knowledge_base import kb
        admin = create_kb_admin(kb, settings.project_docs_dir)
        documents = admin.list_documents(filter_type=filter_type)
        
        return {
            "total": len(documents),
            "documents": documents
        }
        
    except Exception as e:
        logger.error(f"List KB documents failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/admin/kb/documents/{doc_id}")
async def get_kb_document_details(doc_id: str):
    """Get full details for a specific document"""
    try:
        from memory.knowledge_base import kb
        admin = create_kb_admin(kb, settings.project_docs_dir)
        details = admin.get_document_details(doc_id)
        
        if not details:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
        
        return details
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document details failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/admin/kb/reindex")
async def reindex_document(source_file: str):
    """Re-index a specific document"""
    try:
        from memory.knowledge_base import kb
        admin = create_kb_admin(kb, settings.project_docs_dir)
        result = admin.reindex_document(source_file)
        return result
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Document re-indexing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/admin/kb/upload", dependencies=[Depends(verify_api_key)])
async def upload_kb_document(request: DocumentUploadRequest):
    """Upload new document to knowledge base (requires API key)"""
    try:
        from memory.knowledge_base import kb
        admin = create_kb_admin(kb, settings.project_docs_dir)
        result = admin.upload_document(filename=request.filename, content=request.content)
        return result
        
    except Exception as e:
        logger.error(f"Document upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/admin/kb/documents")
async def delete_kb_document(source_file: str):
    """Delete document from knowledge base"""
    try:
        from memory.knowledge_base import kb
        admin = create_kb_admin(kb, settings.project_docs_dir)
        result = admin.delete_document(source_file)
        return result
        
    except Exception as e:
        logger.error(f"Document deletion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/admin/kb/search-test")
async def test_kb_search(request: SearchTestRequest):
    """Test knowledge base search functionality"""
    try:
        from memory.knowledge_base import kb
        admin = create_kb_admin(kb, settings.project_docs_dir)
        results = admin.test_search(query=request.query, limit=request.limit)
        return results
        
    except Exception as e:
        logger.error(f"KB search test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/admin/kb/stats")
async def get_kb_statistics():
    """Get knowledge base statistics"""
    try:
        from memory.knowledge_base import kb
        admin = create_kb_admin(kb, settings.project_docs_dir)
        stats = admin.get_statistics()
        return stats
        
    except Exception as e:
        logger.error(f"Get KB stats failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/admin/kb/rebuild")
async def rebuild_kb_index():
    """Rebuild entire knowledge base from source files"""
    try:
        from memory.knowledge_base import kb
        admin = create_kb_admin(kb, settings.project_docs_dir)
        result = admin.rebuild_index()
        return result
        
    except Exception as e:
        logger.error(f"KB rebuild failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=2,
        log_level="info"
    )
