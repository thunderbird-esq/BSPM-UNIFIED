"""
Health Check & Metrics Router
Endpoints for system health monitoring and Prometheus metrics.
"""

import time
from datetime import datetime
from pathlib import Path

import requests
from fastapi import APIRouter, Response, Depends
from fastapi.responses import JSONResponse, FileResponse

from backend.dependencies import settings, app_state, logger
from backend.models import HealthResponse
from backend.metrics import metrics
from backend.graceful_degradation import degraded_mode, get_degradation_warning
from backend.retry_logic import ollama_circuit_breaker, comfyui_circuit_breaker


router = APIRouter()


@router.get("/")
async def root():
    """Serve frontend index.html or return API info."""
    index_path = Path("/app/frontend/index.html")
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "GBStudio Automation Hub API", "version": "3.4", "status": "refactored"}


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Comprehensive health check for all services.

    Returns:
        Health status including backend, Ollama, ComfyUI, task queue,
        degradation status, and circuit breaker states.
    """
    health_status = {
        "backend": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": round(time.time() - app_state["start_time"], 2),
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

    # Check task queue (import here to avoid circular dependency)
    from backend.task_queue import task_queue

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


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint.

    Returns:
        Plain text Prometheus-formatted metrics including HTTP requests,
        sprite generation stats, service health, and system resources.
    """
    metrics.update_system_metrics()
    return Response(
        content=metrics.generate_prometheus_output(),
        media_type="text/plain; version=0.0.4"
    )
