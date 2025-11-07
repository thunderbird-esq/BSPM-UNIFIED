"""
Generation Router
Handles style presets and sprite regeneration endpoints.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from backend.dependencies import logger
from backend.models import RegenerateRequest
from backend.security import check_rate_limit
from backend.style_presets import get_preset_by_name, list_presets
from backend.regeneration_manager import regeneration_manager


router = APIRouter()


@router.get("/api/v1/presets")
async def get_style_presets():
    """
    List all available style presets.

    Returns:
        Dictionary with list of presets and default preset name
    """
    return {
        "presets": list_presets(),
        "default": "clean_pixel_art"
    }


@router.get("/api/v1/presets/{preset_name}")
async def get_preset_details(preset_name: str):
    """
    Get details for a specific style preset.

    Args:
        preset_name: Name of the preset to retrieve

    Returns:
        Preset details including parameters and boost values

    Raises:
        HTTPException: 404 if preset not found
    """
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


@router.post("/api/v1/regenerate")
async def regenerate_sprite(request: RegenerateRequest, _rate_limit=Depends(check_rate_limit)):
    """
    Regenerate sprite with new seed and optional different preset.

    Args:
        request: Regeneration request with session ID and optional preset

    Returns:
        New attempt details with session ID, attempt ID, seed, and status

    Raises:
        HTTPException: 404 if session not found, 500 on other errors
    """
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


@router.get("/api/v1/regenerate/{session_id}/comparison")
async def get_comparison_data(session_id: str):
    """
    Get comparison data for all attempts in a regeneration session.

    Args:
        session_id: Session identifier

    Returns:
        Comparison data for all generation attempts

    Raises:
        HTTPException: 404 if session not found
    """
    data = regeneration_manager.get_comparison_data(session_id)

    if not data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return data


@router.post("/api/v1/regenerate/{session_id}/mark-best")
async def mark_best_attempt(session_id: str, attempt_id: str):
    """
    Mark an attempt as the best result.

    Args:
        session_id: Session identifier
        attempt_id: Attempt identifier to mark as best

    Returns:
        Success status with session and attempt IDs

    Raises:
        HTTPException: 404 if session not found, 400 if attempt invalid
    """
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
