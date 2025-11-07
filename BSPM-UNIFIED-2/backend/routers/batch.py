"""
Batch Router
Handles batch sprite generation operations including CSV processing, character sets, and templates.
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from backend.dependencies import logger, task_queue
from backend.security import check_rate_limit
from backend.batch_generator import create_batch_generator


router = APIRouter()


# Local model definitions to match original main.py implementation
class BatchCSVRequest(BaseModel):
    """Request model for batch CSV processing."""
    csv_path: str = Field(..., description="Path to CSV file with sprite specifications")
    session_id: str = Field(..., description="Session identifier")


class CharacterSetRequest(BaseModel):
    """Request model for generating a character set."""
    character_name: str = Field(..., description="Character name")
    style: str = Field(..., description="Art style for the character")
    session_id: str = Field(..., description="Session identifier")
    include_actions: List[str] | None = Field(None, description="Optional list of actions to include")


class ProjectTemplateRequest(BaseModel):
    """Request model for applying project template."""
    template_name: str = Field(..., description="Template name (rpg/platformer/etc)")
    session_id: str = Field(..., description="Session identifier")


@router.post("/api/v1/batch/csv")
async def process_batch_csv(request: BatchCSVRequest, _rate_limit=Depends(check_rate_limit)):
    """
    Process CSV file with batch sprite requests.

    Args:
        request: CSV batch request with file path and session ID

    Returns:
        Batch processing result with task IDs

    Raises:
        HTTPException: 404 if file not found, 500 on other errors
    """
    try:
        generator = create_batch_generator(task_queue)
        result = await generator.process_csv(csv_path=request.csv_path, session_id=request.session_id)
        return result

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"CSV batch processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/batch/character-set")
async def generate_character_set(request: CharacterSetRequest, _rate_limit=Depends(check_rate_limit)):
    """
    Generate complete animation set for a character.

    Args:
        request: Character set request with name, style, and optional actions

    Returns:
        Character set generation result with task IDs

    Raises:
        HTTPException: 500 on error
    """
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


@router.post("/api/v1/batch/template")
async def apply_project_template(request: ProjectTemplateRequest, _rate_limit=Depends(check_rate_limit)):
    """
    Apply project template to generate multiple sprites.

    Args:
        request: Template request with template name and session ID

    Returns:
        Template application result with task IDs

    Raises:
        HTTPException: 404 if template not found, 500 on other errors
    """
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


@router.get("/api/v1/batch/{batch_id}/status")
async def get_batch_status(batch_id: str, task_ids: List[str]):
    """
    Get status of batch generation.

    Args:
        batch_id: Batch identifier
        task_ids: List of task IDs to check status for

    Returns:
        Batch status with individual task statuses

    Raises:
        HTTPException: 500 on error
    """
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
