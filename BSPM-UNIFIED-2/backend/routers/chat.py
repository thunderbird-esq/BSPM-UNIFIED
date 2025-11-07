"""
Chat & PM Agent Router
Handles user prompts, PM agent responses, and plan execution.
"""

import os
import json
import hashlib
import time
from datetime import datetime
from typing import Dict, Optional, Any
from uuid import uuid4

import requests
from fastapi import APIRouter, HTTPException, Depends

from backend.dependencies import settings, logger
from backend.models import PromptRequest, ExecutionRequest
from backend.logging_config import LoggerAdapter
from backend.security import check_rate_limit
from backend.metrics import metrics
from backend.style_presets import get_optimal_preset_for_description
from backend.regeneration_manager import regeneration_manager
from backend.graceful_degradation import FallbackResponses, fallback_on_failure
from backend.retry_logic import (
    retry_with_backoff,
    ollama_circuit_breaker,
    CircuitBreakerOpen,
    RetryExhausted
)


router = APIRouter()


# PM Agent Prompt Template
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


def generate_correlation_id() -> str:
    """Generate unique correlation ID for logging."""
    return f"req_{int(time.time())}_{os.urandom(4).hex()}"


def get_recent_conversation_context(session_id: str, window: int = 6) -> str:
    """
    Retrieve recent conversation history for context.

    Args:
        session_id: Session identifier
        window: Number of recent turns to retrieve

    Returns:
        Formatted conversation context string
    """
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
    """
    Persist conversation turn to JSONL file.

    Args:
        session_id: Session identifier
        user_message: User's message
        pm_response: PM agent's response
        action_taken: Optional action description
        correlation_id: Request correlation ID
    """
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


def fallback_pm_response(model: str, prompt: str, correlation_id: str, timeout: int = 90) -> Dict[str, Any]:
    """Fallback response when Ollama is unavailable."""
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
    """
    Call Ollama API for LLM inference with retry and circuit breaker.

    Args:
        model: Ollama model name
        prompt: Prompt text
        correlation_id: Request correlation ID
        timeout: Request timeout in seconds

    Returns:
        Parsed JSON response from Ollama

    Raises:
        HTTPException: On timeout or request failure
    """
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
            # Strip markdown code blocks if present
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


@router.post("/api/v1/prompt")
async def handle_prompt(request: PromptRequest, _rate_limit=Depends(check_rate_limit)):
    """
    Handle user prompt with style preset support.

    Args:
        request: Prompt request with message and optional session/preset

    Returns:
        PM agent response with plan and approval requirement
    """
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


@router.post("/api/v1/execute")
async def handle_execution(request: ExecutionRequest, _rate_limit=Depends(check_rate_limit)):
    """
    Execute approved delegation plan with regeneration tracking.

    Args:
        request: Execution request with plan and session ID

    Returns:
        Execution results and status
    """
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
