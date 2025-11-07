"""
Sprites Router
Handles sprite management operations including editing, deletion, duplication, and export.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException

from backend.dependencies import settings, logger
from backend.models import (
    SpriteEditRequest,
    SpriteDeleteRequest,
    SpriteDuplicateRequest,
    SpriteExportRequest
)
from backend.sprite_manager import create_sprite_manager


router = APIRouter()


@router.put("/api/v1/sprites/edit")
async def edit_sprite(request: SpriteEditRequest):
    """
    Edit sprite metadata.

    Args:
        request: Sprite edit request with sprite ID and optional new values

    Returns:
        Updated sprite information

    Raises:
        HTTPException: 404 if sprite not found, 500 on other errors
    """
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


@router.delete("/api/v1/sprites/delete")
async def delete_sprite(request: SpriteDeleteRequest):
    """
    Delete sprite from project.

    Args:
        request: Sprite delete request with sprite ID and file deletion flag

    Returns:
        Deletion status with sprite ID and flags

    Raises:
        HTTPException: 404 if sprite not found, 500 on other errors
    """
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


@router.post("/api/v1/sprites/duplicate")
async def duplicate_sprite(request: SpriteDuplicateRequest):
    """
    Duplicate sprite with optional variation.

    Args:
        request: Sprite duplication request with source ID, new name, and variation options

    Returns:
        New sprite information

    Raises:
        HTTPException: 404 if sprite not found, 500 on other errors
    """
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


@router.post("/api/v1/sprites/export")
async def export_sprite(request: SpriteExportRequest):
    """
    Export sprite as standalone PNG.

    Args:
        request: Sprite export request with sprite ID, format, and scale

    Returns:
        Export details with output path

    Raises:
        HTTPException: 404 if sprite not found, 500 on other errors
    """
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


@router.get("/api/v1/sprites")
async def list_sprites(filter_type: Optional[str] = None, search_name: Optional[str] = None):
    """
    List all sprites in project with optional filtering.

    Args:
        filter_type: Optional sprite type filter
        search_name: Optional name search filter

    Returns:
        List of sprites with total count

    Raises:
        HTTPException: 500 on error
    """
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


@router.get("/api/v1/sprites/{sprite_id}")
async def get_sprite_info(sprite_id: str):
    """
    Get detailed information about a sprite.

    Args:
        sprite_id: Sprite identifier

    Returns:
        Detailed sprite information

    Raises:
        HTTPException: 404 if sprite not found, 500 on other errors
    """
    try:
        manager = create_sprite_manager(settings.gbstudio_project_path)
        info = manager.get_sprite_info(sprite_id)
        return info

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Get sprite info failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
