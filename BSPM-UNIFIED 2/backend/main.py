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
from pydantic import BaseModel, validator, Field
from pydantic_settings import BaseSettings
import uvicorn

# Logging setup (MUST be first)
from backend.logging_config import setup_logging, LoggerAdapter

# Setup structured logging with rotation
logger = setup_logging(
    log_dir="/app/logs",
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    max_bytes=10 * 1024 * 1024,  # 10MB
    backup_count=5
)

# Security and task queue
from backend.security import check_rate_limit, verify_api_key, api_key_manager, rate_limiter
from backend.task_queue import task_queue, Priority

# Medium-priority features
from backend.style_presets import StylePreset, get_preset_by_name, list_presets, get_optimal_preset_for_description
from backend.regeneration_manager import regeneration_manager, GenerationAttempt
from backend.sprite_manager import create_sprite_manager
from backend.batch_generator import create_batch_generator
from backend.kb_admin import create_kb_admin
from backend.music_department import create_music_department, MusicStyle, GameBoyChannel

# Graceful degradation
from backend.graceful_degradation import (
    fallback_on_failure,
    skip_on_failure,
    degraded_mode,
    FallbackResponses,
    get_degradation_warning
)

# Retry logic with circuit breakers
from backend.retry_logic import (
    retry_with_backoff,
    ollama_circuit_breaker,
    comfyui_circuit_breaker,
    CircuitBreakerOpen,
    RetryExhausted
)

# Metrics
from backend.metrics import metrics, MetricsCollector

# Code Department
from backend.code_department import CodeDepartment

# Authentication
from backend.session_auth import (
    SessionManager,
    LoginRequest,
    LoginResponse,
    UserResponse,
    ChangePasswordRequest,
    RegisterUserRequest,
    set_auth_cookies,
    clear_auth_cookies
)
from backend.user_manager import UserManager, PasswordValidator
from backend.auth_middleware import (
    get_current_user,
    get_current_active_user,
    get_current_admin_user,
    get_optional_user,
    AuthContext,
    audit_logger
)


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
    users_file: str = "/app/secrets/users.json"

    # Agent configuration
    pm_model: str = "llama3"
    embedding_model: str = "nomic-embed-text"
    default_timeout: int = 90

    # Generation parameters
    sprite_width: int = 32
    sprite_height: int = 32
    num_frames: int = 8
    generation_timeout: int = 360  # 6 minutes

    # Session configuration
    session_secret_key: str = os.getenv("SESSION_SECRET_KEY", "dev-secret-key-change-in-production-minimum-32-chars")
    session_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    refresh_token_expire_days: int = 7

    # Password configuration
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digit: bool = True
    password_require_special: bool = False

    # Database configuration
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://gbstudio:password@postgres:5432/gbstudio_hub"
    )
    database_pool_size: int = int(os.getenv("DATABASE_POOL_SIZE", "20"))
    database_max_overflow: int = int(os.getenv("DATABASE_MAX_OVERFLOW", "10"))
    database_pool_timeout: int = 30
    database_pool_recycle: int = 3600

    # Redis configuration
    redis_url: str = os.getenv(
        "REDIS_URL",
        "redis://:password@redis:6379/0"
    )
    redis_max_connections: int = 50
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))
    session_ttl_seconds: int = int(os.getenv("SESSION_TTL_SECONDS", "86400"))

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
os.makedirs("/app/sfx_outputs", exist_ok=True)


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
# Pydantic Models - Music Department
# ============================================================================

class MusicGenerationRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    style: str = "exploration"
    duration_seconds: int = Field(default=60, ge=10, le=300)
    tempo_bpm: int = Field(default=120, ge=40, le=240)
    channels: Optional[List[str]] = None
    seed: Optional[int] = None


class MusicRegenerateRequest(BaseModel):
    track_id: str
    new_seed: Optional[int] = None
    new_style: Optional[str] = None


class MusicTrackResponse(BaseModel):
    track_id: str
    description: str
    style: str
    duration_seconds: int
    tempo_bpm: int
    channels: List[str]
    seed: int
    files: Dict[str, str]
    created_at: str
    format: str
    loop_start: int
    loop_end: int


# ============================================================================
# Pydantic Models - SFX Department
# ============================================================================

class SFXGenerationRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    category: str
    duration_ms: Optional[int] = None
    channel: Optional[str] = None
    variations: int = Field(default=1, ge=1, le=5)
    custom_params: Optional[Dict[str, Any]] = None


class SFXRegenerateRequest(BaseModel):
    sfx_id: str
    variation_amount: float = Field(default=0.2, ge=0.0, le=1.0)


class SFXDeleteRequest(BaseModel):
    sfx_id: str
    delete_file: bool = True


# ============================================================================
# Pydantic Models - Code Department
# ============================================================================

class CodeGenerationRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)
    script_type: str = Field(..., description="dialogue, movement, logic, trigger, scene, ui")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    template_id: Optional[str] = None


class ScriptValidationRequest(BaseModel):
    events: List[Dict[str, Any]]


class ScriptOptimizationRequest(BaseModel):
    events: List[Dict[str, Any]]


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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
frontend_path = Path("/app/frontend")
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


# ============================================================================
# Application Lifecycle Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Start background services on application startup"""
    # Initialize session manager
    app.state.session_manager = SessionManager(
        secret_key=settings.session_secret_key,
        algorithm=settings.session_algorithm,
        access_token_expire_minutes=settings.access_token_expire_minutes,
        refresh_token_expire_days=settings.refresh_token_expire_days
    )
    logger.info("Session manager initialized")

    # Initialize user manager with password validator
    password_validator = PasswordValidator(
        min_length=settings.password_min_length,
        require_uppercase=settings.password_require_uppercase,
        require_lowercase=settings.password_require_lowercase,
        require_digit=settings.password_require_digit,
        require_special=settings.password_require_special
    )
    app.state.user_manager = UserManager(
        users_file=settings.users_file,
        password_validator=password_validator
    )
    logger.info("User manager initialized")

    await task_queue.start()
    logger.info("Task queue started")
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
    from backend.metrics import http_requests_total, http_request_duration_seconds
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
    exceptions=(requests.exceptions.RequestException,)
)
async def call_ollama_agent(
    model: str,
    prompt: str,
    correlation_id: str,
    timeout: int = 90
) -> Dict[str, Any]:
    """Call Ollama API for LLM inference with retry and circuit breaker"""
    try:
        response = requests.post(
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
            timeout=timeout
        )
        response.raise_for_status()
        
        result = response.json()
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
    
    except requests.exceptions.Timeout:
        logger.error(f"Ollama request timed out after {timeout}s", extra={"correlation_id": correlation_id})
        raise HTTPException(status_code=504, detail=f"LLM request timed out after {timeout} seconds")
    
    except requests.exceptions.RequestException as e:
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
        response = requests.get(settings.ollama_tags_url, timeout=3)
        latency = round((time.time() - start) * 1000, 2)
        
        if response.status_code == 200:
            models = response.json().get("models", [])
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
                "error": f"HTTP {response.status_code}"
            }
            health_status["backend"] = "degraded"
            metrics.update_service_health('ollama', healthy=False)
    
    except requests.exceptions.RequestException as e:
        health_status["services"]["ollama"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["backend"] = "degraded"
        metrics.update_service_health('ollama', healthy=False)
    
    # Check ComfyUI
    try:
        start = time.time()
        response = requests.get(f"{settings.comfyui_api_url}/system_stats", timeout=3)
        latency = round((time.time() - start) * 1000, 2)
        
        if response.status_code == 200:
            stats = response.json()
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
                "error": f"HTTP {response.status_code}"
            }
            health_status["backend"] = "degraded"
            metrics.update_service_health('comfyui', healthy=False)
    
    except requests.exceptions.RequestException as e:
        health_status["services"]["comfyui"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["backend"] = "degraded"
        metrics.update_service_health('comfyui', healthy=False)
    
    # Check Database (PostgreSQL)
    try:
        from backend.database import get_database_manager
        db_manager = get_database_manager()
        db_health = await db_manager.health_check()
        health_status["services"]["database"] = db_health

        if db_health["status"] != "healthy":
            health_status["backend"] = "degraded"
            metrics.update_service_health('database', healthy=False)
        else:
            metrics.update_service_health(
                'database',
                healthy=True,
                latency_ms=db_health.get("response_time_seconds", 0) * 1000
            )
    except Exception as e:
        health_status["services"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["backend"] = "degraded"
        metrics.update_service_health('database', healthy=False)

    # Check Redis Cache
    try:
        from backend.cache import get_redis_manager
        redis_manager = get_redis_manager()
        redis_health = await redis_manager.health_check()
        health_status["services"]["redis"] = redis_health

        if redis_health["status"] != "healthy":
            health_status["backend"] = "degraded"
            metrics.update_service_health('redis', healthy=False)
        else:
            metrics.update_service_health(
                'redis',
                healthy=True,
                latency_ms=redis_health.get("response_time_seconds", 0) * 1000
            )
    except Exception as e:
        health_status["services"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["backend"] = "degraded"
        metrics.update_service_health('redis', healthy=False)

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


@app.post("/api/v1/execute")
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
    
    for task in request.plan:
        if task.department == "Art":
            results.append({
                "department": "Art",
                "task": task.task,
                "status": "queued",
                "message": "Art generation not yet implemented in this minimal version"
            })
        else:
            results.append({
                "department": task.department,
                "task": task.task,
                "status": "unsupported",
                "message": f"Department {task.department} not yet implemented"
            })
    
    return {
        "status": "completed",
        "results": results,
        "session_id": request.session_id,
        "correlation_id": correlation_id
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
        from backend.memory.knowledge_base import kb
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
        from backend.memory.knowledge_base import kb
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
        from backend.memory.knowledge_base import kb
        admin = create_kb_admin(kb, settings.project_docs_dir)
        result = admin.reindex_document(source_file)
        return result
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Document re-indexing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/admin/kb/upload")
async def upload_kb_document(request: DocumentUploadRequest):
    """Upload new document to knowledge base"""
    try:
        from backend.memory.knowledge_base import kb
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
        from backend.memory.knowledge_base import kb
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
        from backend.memory.knowledge_base import kb
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
        from backend.memory.knowledge_base import kb
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
        from backend.memory.knowledge_base import kb
        admin = create_kb_admin(kb, settings.project_docs_dir)
        result = admin.rebuild_index()
        return result

    except Exception as e:
        logger.error(f"KB rebuild failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SFX Department Endpoints

# ============================================================================
# Music Department Endpoints
# ============================================================================

@app.post("/api/music/generate")
async def generate_music(request: MusicGenerationRequest, _rate_limit = Depends(check_rate_limit)):
    """
    Generate music track from description.

    Generate Game Boy-compatible music based on text description and style parameters.
    """
    correlation_id = generate_correlation_id()

    req_logger = LoggerAdapter(logger, {'correlation_id': correlation_id})
    req_logger.info(
        f"Music generation request: {request.description[:50]}...",
        extra={
            'style': request.style,
            'duration': request.duration_seconds,
            'tempo': request.tempo_bpm
        }
    )

    try:
        # Validate style
        try:
            style = MusicStyle(request.style)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid style '{request.style}'. Valid styles: {[s.value for s in MusicStyle]}"
            )

        # Validate and convert channels
        channels = None
        if request.channels:
            try:
                channels = [GameBoyChannel(ch) for ch in request.channels]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid channel. Valid channels: {[c.value for c in GameBoyChannel]}"
                )

        # Create music department and generate
        music_dept = create_music_department()

        # Track generation time
        start_time = time.time()
        track = await music_dept.generate_music(
            description=request.description,
            style=style,
            duration_seconds=request.duration_seconds,
            tempo_bpm=request.tempo_bpm,
            channels=channels,
            seed=request.seed
        )
        duration = time.time() - start_time

        # Validate generated track
        is_valid, errors = music_dept.validate_track(track)
        if not is_valid:
            req_logger.error(
                f"Generated track validation failed",
                extra={'track_id': track['track_id'], 'errors': errors}
            )
            raise HTTPException(
                status_code=500,
                detail=f"Track validation failed: {', '.join(errors)}"
            )

        req_logger.info(
            f"Successfully generated music track",
            extra={
                'track_id': track['track_id'],
                'duration_seconds': duration,
                'correlation_id': correlation_id
            }
        )

        return {
            **track,
            "correlation_id": correlation_id,
            "generation_time_seconds": round(duration, 2)
        }

    except HTTPException:
        raise
    except Exception as e:
        req_logger.error(f"Music generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/music/list")
async def list_music_tracks(style: Optional[str] = None, limit: int = 50):
    """
    List all generated music tracks with optional filtering.

    Returns list of track metadata sorted by creation date (newest first).
    """
    try:
        music_dept = create_music_department()
        tracks = await music_dept.list_tracks(style_filter=style, limit=limit)

        return {
            "total": len(tracks),
            "tracks": tracks,
            "available_styles": [s.value for s in MusicStyle]
        }

    except Exception as e:
        logger.error(f"List music tracks failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/music/track/{track_id}")
async def get_music_track(track_id: str):
    """Get detailed information about a specific music track."""
    try:
        music_dept = create_music_department()
        track = await music_dept.get_track(track_id)

        if not track:
            raise HTTPException(
                status_code=404,
                detail=f"Track {track_id} not found"
            )

        return track

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get music track failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/music/regenerate")
async def regenerate_music(request: MusicRegenerateRequest, _rate_limit = Depends(check_rate_limit)):
    """
    Regenerate music track with variations.

    Create a new version of an existing track with different seed and/or style.
    """
    correlation_id = generate_correlation_id()

    req_logger = LoggerAdapter(logger, {'correlation_id': correlation_id})
    req_logger.info(
        f"Music regeneration request for track {request.track_id}",
        extra={'track_id': request.track_id, 'new_seed': request.new_seed}
    )

    try:
        # Validate new style if provided
        new_style = None
        if request.new_style:
            try:
                new_style = MusicStyle(request.new_style)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid style '{request.new_style}'. Valid styles: {[s.value for s in MusicStyle]}"
                )

        music_dept = create_music_department()

        start_time = time.time()
        new_track = await music_dept.regenerate_track(
            track_id=request.track_id,
            new_seed=request.new_seed,
            new_style=new_style
        )
        duration = time.time() - start_time

        req_logger.info(
            f"Successfully regenerated music track",
            extra={
                'original_track_id': request.track_id,
                'new_track_id': new_track['track_id'],
                'duration_seconds': duration
            }
        )

        return {
            **new_track,
            "original_track_id": request.track_id,
            "correlation_id": correlation_id,
            "generation_time_seconds": round(duration, 2)
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        req_logger.error(f"Music regeneration failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/music/delete/{track_id}")
async def delete_music_track(track_id: str, delete_files: bool = True):
    """
    Delete music track and optionally its files.

    Args:
        track_id: Track ID to delete
        delete_files: If true, also delete files from disk (default: true)
    """
    try:
        music_dept = create_music_department()
        success = await music_dept.delete_track(track_id, delete_files=delete_files)

        return {
            "track_id": track_id,
            "deleted": success,
            "files_deleted": delete_files
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Delete music track failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/music/styles")
async def get_music_styles():
    """
    Get list of available music styles with descriptions.
    """
    style_descriptions = {
        "battle": "Fast-paced, intense music for combat sequences",
        "exploration": "Moderate tempo, adventurous music for exploring",
        "menu": "Simple, calm music for menus and UI",
        "victory": "Triumphant, upbeat music for winning",
        "defeat": "Slow, somber music for losing",
        "ambient": "Very calm, atmospheric background music",
        "boss": "Very intense, fast music for boss battles",
        "town": "Pleasant, welcoming music for towns and safe areas",
        "dungeon": "Mysterious, tense music for dungeons"
    }

    return {
        "styles": [
            {
                "value": style.value,
                "name": style.value.replace("_", " ").title(),
                "description": style_descriptions.get(style.value, "")
            }
            for style in MusicStyle
        ]
    }

# ============================================================================

@app.post("/api/sfx/generate")
async def generate_sound_effect(request: SFXGenerationRequest, _rate_limit = Depends(check_rate_limit)):
    """Generate Game Boy sound effect from description"""
    try:
        from backend.sfx_department import create_sfx_department

        sfx_dept = create_sfx_department()

        # Generate sound effects
        sfx_list = await sfx_dept.generate_sfx(
            description=request.description,
            category=request.category,
            duration_ms=request.duration_ms,
            channel=request.channel,
            variations=request.variations,
            custom_params=request.custom_params
        )

        # Return first SFX (or all if variations > 1)
        if len(sfx_list) == 1:
            return sfx_list[0].to_dict()
        else:
            return {
                "count": len(sfx_list),
                "sfx": [sfx.to_dict() for sfx in sfx_list]
            }

    except Exception as e:
        logger.error(f"SFX generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sfx/presets")
async def get_sfx_presets():
    """List available SFX presets"""
    try:
        from backend.sfx_department import create_sfx_department

        sfx_dept = create_sfx_department()
        presets = sfx_dept.get_presets()

        return {
            "presets": presets,
            "categories": list(presets.keys())
        }

    except Exception as e:
        logger.error(f"Get SFX presets failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sfx/regenerate")
async def regenerate_sound_effect(request: SFXRegenerateRequest):
    """Regenerate sound effect with variation"""
    try:
        from backend.sfx_department import create_sfx_department

        sfx_dept = create_sfx_department()
        new_sfx = sfx_dept.regenerate_sfx(
            sfx_id=request.sfx_id,
            variation_amount=request.variation_amount
        )

        return new_sfx.to_dict()

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"SFX regeneration failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sfx/list")
async def list_sound_effects(category: Optional[str] = None):
    """List all generated sound effects"""
    try:
        from backend.sfx_department import create_sfx_department

        sfx_dept = create_sfx_department()
        sfx_list = sfx_dept.list_sfx(category_filter=category)

        return {
            "total": len(sfx_list),
            "sfx": sfx_list
        }

    except Exception as e:
        logger.error(f"List SFX failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sfx/{sfx_id}")
async def get_sound_effect(sfx_id: str):
    """Get details for a specific sound effect"""
    try:
        from backend.sfx_department import create_sfx_department

        sfx_dept = create_sfx_department()
        sfx = sfx_dept.get_sfx(sfx_id)

        if not sfx:
            raise HTTPException(status_code=404, detail=f"SFX {sfx_id} not found")

        return sfx.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get SFX failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sfx/delete/{sfx_id}")
async def delete_sound_effect(sfx_id: str, delete_file: bool = True):
    """Delete sound effect"""
    try:
        from backend.sfx_department import create_sfx_department

        sfx_dept = create_sfx_department()
        success = sfx_dept.delete_sfx(sfx_id=sfx_id, delete_file=delete_file)

        return {
            "sfx_id": sfx_id,
            "deleted": success,
            "file_deleted": delete_file
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"SFX deletion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sfx/download/{sfx_id}")
async def download_sound_effect(sfx_id: str):
    """Download sound effect WAV file"""
    try:
        from backend.sfx_department import create_sfx_department

        sfx_dept = create_sfx_department()
        sfx = sfx_dept.get_sfx(sfx_id)

        if not sfx:
            raise HTTPException(status_code=404, detail=f"SFX {sfx_id} not found")

        file_path = Path(sfx.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"SFX file not found: {sfx.file_path}")

        return FileResponse(
            path=str(file_path),
            media_type="audio/wav",
            filename=file_path.name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SFX download failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Code Department Endpoints
# ============================================================================

@app.post("/api/code/generate")
async def generate_gbstudio_script(request: CodeGenerationRequest, _rate_limit = Depends(check_rate_limit)):
    """Generate GBStudio script from natural language description"""
    correlation_id = generate_correlation_id()

    req_logger = LoggerAdapter(logger, {'correlation_id': correlation_id})
    req_logger.info(f"Generating {request.script_type} script: {request.description[:50]}...")

    try:
        code_dept = CodeDepartment(
            ollama_api_url=settings.ollama_api_url,
            model=settings.pm_model,
            templates_dir="/app/backend/code_templates"
        )

        script = await code_dept.generate_script(request, correlation_id)

        return {
            "script_id": script.script_id,
            "description": script.description,
            "events": script.events,
            "estimated_events": script.estimated_events,
            "validation_status": script.validation_status,
            "template_used": script.template_used,
            "variables_used": script.variables_used,
            "created_at": script.created_at.isoformat(),
            "correlation_id": correlation_id
        }

    except Exception as e:
        req_logger.error(f"Script generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/code/templates")
async def list_code_templates():
    """List available GBStudio script templates"""
    try:
        code_dept = CodeDepartment(
            ollama_api_url=settings.ollama_api_url,
            model=settings.pm_model,
            templates_dir="/app/backend/code_templates"
        )

        templates = code_dept.get_templates()

        return {
            "total": len(templates),
            "templates": templates
        }

    except Exception as e:
        logger.error(f"List templates failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/code/validate")
async def validate_gbstudio_script(request: ScriptValidationRequest):
    """Validate GBStudio script syntax and structure"""
    try:
        code_dept = CodeDepartment(
            ollama_api_url=settings.ollama_api_url,
            model=settings.pm_model,
            templates_dir="/app/backend/code_templates"
        )

        validation = code_dept.validate_script(request.events)

        return validation

    except Exception as e:
        logger.error(f"Script validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/code/optimize")
async def optimize_gbstudio_script(request: ScriptOptimizationRequest):
    """Optimize GBStudio script for performance"""
    try:
        code_dept = CodeDepartment(
            ollama_api_url=settings.ollama_api_url,
            model=settings.pm_model,
            templates_dir="/app/backend/code_templates"
        )

        optimization = code_dept.optimize_script(request.events)

        return optimization

    except Exception as e:
        logger.error(f"Script optimization failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/code/patterns")
async def get_script_patterns():
    """Get common GBStudio script patterns organized by type"""
    try:
        code_dept = CodeDepartment(
            ollama_api_url=settings.ollama_api_url,
            model=settings.pm_model,
            templates_dir="/app/backend/code_templates"
        )

        patterns = code_dept.get_script_patterns()

        return {
            "patterns": patterns,
            "types": list(patterns.keys())
        }

    except Exception as e:
        logger.error(f"Get patterns failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(
    request: Request,
    response: Response,
    login_data: LoginRequest
):
    """
    Login with username and password.

    Returns JWT access and refresh tokens, sets secure cookies.
    """
    # Get client IP for audit logging
    client_ip = request.client.host if request.client else "unknown"

    # Check if account is locked
    if not app.state.session_manager.check_login_attempts(login_data.username):
        audit_logger.log_login(
            username=login_data.username,
            success=False,
            ip_address=client_ip,
            auth_method="session"
        )
        raise HTTPException(
            status_code=429,
            detail="Account temporarily locked due to too many failed login attempts. Please try again later."
        )

    # Authenticate user
    user = app.state.user_manager.authenticate(
        username=login_data.username,
        password=login_data.password
    )

    if not user:
        # Record failed attempt
        app.state.session_manager.record_login_attempt(
            username=login_data.username,
            success=False
        )
        audit_logger.log_login(
            username=login_data.username,
            success=False,
            ip_address=client_ip,
            auth_method="session"
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # Record successful login
    app.state.session_manager.record_login_attempt(
        username=login_data.username,
        success=True
    )

    # Create session
    session_data = app.state.session_manager.create_session(
        user_id=user.user_id,
        username=user.username,
        role=user.role
    )

    # Set secure cookies
    set_auth_cookies(
        response=response,
        access_token=session_data["access_token"],
        refresh_token=session_data["refresh_token"],
        secure=os.getenv("ENVIRONMENT", "development").lower() == "production"
    )

    # Log successful login
    audit_logger.log_login(
        username=user.username,
        success=True,
        ip_address=client_ip,
        auth_method="session"
    )

    logger.info(f"User logged in: {user.username}", extra={
        'user_id': user.user_id,
        'ip_address': client_ip
    })

    return LoginResponse(
        access_token=session_data["access_token"],
        refresh_token=session_data["refresh_token"],
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60
    )


@app.post("/api/auth/logout")
async def logout(
    response: Response,
    auth_context: AuthContext = Depends(get_current_user)
):
    """
    Logout current user and invalidate session.
    """
    # Invalidate session
    app.state.session_manager.invalidate_session(auth_context.user_id)

    # Clear cookies
    clear_auth_cookies(response)

    # Log logout
    audit_logger.log_logout(
        user_id=auth_context.user_id,
        username=auth_context.username
    )

    logger.info(f"User logged out: {auth_context.username}", extra={
        'user_id': auth_context.user_id
    })

    return {
        "message": "Logged out successfully"
    }


@app.post("/api/auth/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token")
):
    """
    Refresh access token using refresh token.
    """
    # Get refresh token from cookie or request body
    refresh_token = refresh_token_cookie

    if not refresh_token:
        # Try to get from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            refresh_token = auth_header[7:]

    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail="Refresh token required"
        )

    try:
        # Refresh session
        new_tokens = app.state.session_manager.refresh_session(refresh_token)

        # Set new cookies
        set_auth_cookies(
            response=response,
            access_token=new_tokens["access_token"],
            refresh_token=new_tokens["refresh_token"],
            secure=os.getenv("ENVIRONMENT", "development").lower() == "production"
        )

        # Get user info for logging
        token_payload = app.state.session_manager.verify_token(
            new_tokens["access_token"],
            expected_type="access"
        )

        audit_logger.log_token_refresh(
            user_id=token_payload.sub,
            username=token_payload.username
        )

        logger.info(f"Token refreshed for user {token_payload.username}", extra={
            'user_id': token_payload.sub
        })

        return {
            "access_token": new_tokens["access_token"],
            "refresh_token": new_tokens["refresh_token"],
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token"
        )


@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(
    auth_context: AuthContext = Depends(get_current_user)
):
    """
    Get current user information.
    """
    return UserResponse(
        user_id=auth_context.user.user_id,
        username=auth_context.user.username,
        role=auth_context.user.role,
        created_at=auth_context.user.created_at,
        last_login=auth_context.user.last_login
    )


@app.post("/api/auth/register", response_model=UserResponse)
async def register_user(
    user_data: RegisterUserRequest,
    auth_context: AuthContext = Depends(get_current_admin_user)
):
    """
    Register new user (admin only).
    """
    try:
        # Create user
        user = app.state.user_manager.create_user(
            username=user_data.username,
            password=user_data.password,
            role=user_data.role,
            created_by=auth_context.user_id
        )

        logger.info(f"User registered: {user.username}", extra={
            'user_id': user.user_id,
            'role': user.role,
            'created_by': auth_context.username
        })

        return UserResponse(
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            created_at=user.created_at,
            last_login=user.last_login
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"User registration failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="User registration failed")


@app.post("/api/auth/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    auth_context: AuthContext = Depends(get_current_user)
):
    """
    Change current user's password.
    """
    try:
        # Change password
        app.state.user_manager.change_password(
            user_id=auth_context.user_id,
            current_password=password_data.current_password,
            new_password=password_data.new_password
        )

        # Invalidate current session (user must re-login)
        app.state.session_manager.invalidate_session(auth_context.user_id)

        # Log password change
        audit_logger.log_password_change(
            user_id=auth_context.user_id,
            username=auth_context.username,
            changed_by=auth_context.username
        )

        logger.info(f"Password changed for user {auth_context.username}", extra={
            'user_id': auth_context.user_id
        })

        return {
            "message": "Password changed successfully. Please login again with your new password."
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Password change failed")


@app.get("/api/auth/users", response_model=List[UserResponse])
async def list_users(
    auth_context: AuthContext = Depends(get_current_admin_user)
):
    """
    List all users (admin only).
    """
    users = app.state.user_manager.list_users()

    return [
        UserResponse(
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            created_at=user.created_at,
            last_login=user.last_login
        )
        for user in users
    ]


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=2,
        log_level="info"
    )
