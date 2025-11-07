"""
Pydantic Models - API Request/Response Schemas
Centralized data validation models for all API endpoints.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


# ============================================================================
# Core Models
# ============================================================================

class PromptRequest(BaseModel):
    """Request model for PM agent prompt endpoint."""
    message: str = Field(..., min_length=1, max_length=1000, description="User prompt message")
    session_id: Optional[str] = Field(None, description="Session identifier for conversation tracking")
    preset: Optional[str] = Field(None, description="Optional style preset name")


class DelegationTask(BaseModel):
    """Task to be delegated to a department."""
    department: str = Field(..., description="Department responsible for task")
    task: str = Field(..., description="Task description")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional task details")


class ExecutionRequest(BaseModel):
    """Request model for executing an approved plan."""
    plan: List[DelegationTask] = Field(..., description="List of tasks to execute")
    session_id: str = Field(..., description="Session identifier")


class HealthResponse(BaseModel):
    """Health check response model."""
    backend: str = Field(..., description="Backend service status")
    timestamp: str = Field(..., description="Current timestamp")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    services: Dict[str, Any] = Field(..., description="Status of dependent services")


# ============================================================================
# Style Preset Models
# ============================================================================

class StylePresetRequest(BaseModel):
    """Request model for style preset selection."""
    preset_name: str = Field(..., description="Name of the style preset")


# ============================================================================
# Regeneration Models
# ============================================================================

class RegenerateRequest(BaseModel):
    """Request model for sprite regeneration."""
    session_id: str = Field(..., description="Session identifier")
    preset: Optional[str] = Field(None, description="Optional style preset for regeneration")


# ============================================================================
# Sprite Management Models
# ============================================================================

class SpriteEditRequest(BaseModel):
    """Request model for editing sprite metadata."""
    sprite_id: str = Field(..., description="Unique sprite identifier")
    name: Optional[str] = Field(None, description="New sprite name")
    sprite_type: Optional[str] = Field(None, description="Sprite type (actor/enemy/etc)")


class SpriteDeleteRequest(BaseModel):
    """Request model for deleting a sprite."""
    sprite_id: str = Field(..., description="Unique sprite identifier")
    delete_file: bool = Field(True, description="Whether to delete the file from disk")


class SpriteDuplicateRequest(BaseModel):
    """Request model for duplicating a sprite."""
    sprite_id: str = Field(..., description="Source sprite identifier")
    new_name: str = Field(..., description="Name for the duplicated sprite")
    apply_variation: bool = Field(False, description="Apply color variation")
    variation_type: str = Field("hue_shift", description="Type of variation (hue_shift/brightness/etc)")


class SpriteExportRequest(BaseModel):
    """Request model for exporting sprites."""
    sprite_id: str = Field(..., description="Sprite identifier to export")
    export_format: str = Field("grid", description="Export format (grid/sequence/etc)")
    scale: int = Field(1, ge=1, le=8, description="Scale multiplier (1-8x)")


# ============================================================================
# Batch Operation Models
# ============================================================================

class BatchCSVRequest(BaseModel):
    """Request model for batch sprite generation from CSV."""
    csv_data: str = Field(..., description="CSV data with sprite specifications")
    session_id: str = Field(..., description="Session identifier")


class CharacterSetRequest(BaseModel):
    """Request model for generating a character set."""
    character_name: str = Field(..., description="Character name")
    animation_types: List[str] = Field(..., description="List of animation types")
    session_id: str = Field(..., description="Session identifier")


class ProjectTemplateRequest(BaseModel):
    """Request model for applying project template."""
    template_name: str = Field(..., description="Template name (rpg/platformer/etc)")
    session_id: str = Field(..., description="Session identifier")


# ============================================================================
# Knowledge Base Admin Models
# ============================================================================

class DocumentUploadRequest(BaseModel):
    """Request model for uploading documents to knowledge base."""
    content: str = Field(..., description="Document content (markdown)")
    filename: str = Field(..., description="Document filename")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Document metadata")


class SearchTestRequest(BaseModel):
    """Request model for testing knowledge base search."""
    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(5, ge=1, le=20, description="Maximum results to return")
