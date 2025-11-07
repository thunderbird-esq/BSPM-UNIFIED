"""
Pydantic Validation Models
Version: 3.3
Platform: Intel Mac (macOS Ventura) + Docker

Comprehensive request/response models with validation for API endpoints
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator, field_validator
from datetime import datetime


# ============================================================================
# Enums
# ============================================================================

class SpriteType(str, Enum):
    """Valid sprite types for GBStudio"""
    ACTOR = "actor"
    ACTOR_ANIMATED = "actor_animated"
    STATIC = "static"
    CURSOR = "cursor"


class ExportFormat(str, Enum):
    """Valid export formats for sprites"""
    GRID = "grid"
    STRIP = "strip"
    INDIVIDUAL = "individual"
    ANIMATED_GIF = "animated_gif"


class VariationType(str, Enum):
    """Valid variation types for sprite duplication"""
    HUE_SHIFT = "hue_shift"
    BRIGHTNESS = "brightness"
    SATURATION = "saturation"
    PALETTE_SWAP = "palette_swap"


class Department(str, Enum):
    """Valid departments for task delegation"""
    ART = "Art"
    CODE = "Code"
    MUSIC = "Music"


# ============================================================================
# Core Request Models
# ============================================================================

class PromptRequest(BaseModel):
    """Request model for PM agent prompt endpoint"""
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="User's message to the PM agent"
    )
    session_id: Optional[str] = Field(
        None,
        description="Session ID for conversation tracking"
    )
    preset: Optional[str] = Field(
        None,
        description="Style preset name (e.g., 'clean_pixel_art')"
    )

    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Ensure message is not empty or only whitespace"""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty or only whitespace")
        return v.strip()

    @field_validator('preset')
    @classmethod
    def validate_preset(cls, v: Optional[str]) -> Optional[str]:
        """Normalize preset name"""
        if v:
            return v.lower().strip()
        return v


class DelegationTask(BaseModel):
    """Task to be delegated to a department"""
    department: Department = Field(..., description="Department responsible for the task")
    task: str = Field(..., min_length=1, max_length=500, description="Task description")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional task details")


class ExecutionRequest(BaseModel):
    """Request to execute a delegation plan"""
    plan: List[DelegationTask] = Field(..., min_items=1, description="List of tasks to execute")
    session_id: str = Field(..., min_length=1, description="Session ID for tracking")


# ============================================================================
# Sprite Management Models
# ============================================================================

class SpriteEditRequest(BaseModel):
    """Request to edit sprite metadata"""
    sprite_id: str = Field(..., min_length=1, description="Sprite identifier")
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="New sprite name")
    sprite_type: Optional[SpriteType] = Field(None, description="New sprite type")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate and sanitize sprite name"""
        if v:
            # Remove special characters that might cause issues
            sanitized = ''.join(c for c in v if c.isalnum() or c in (' ', '_', '-'))
            if not sanitized.strip():
                raise ValueError("Name must contain at least one alphanumeric character")
            return sanitized.strip()
        return v


class SpriteDeleteRequest(BaseModel):
    """Request to delete a sprite"""
    sprite_id: str = Field(..., min_length=1, description="Sprite identifier")
    delete_file: bool = Field(True, description="Whether to delete the associated file")


class SpriteDuplicateRequest(BaseModel):
    """Request to duplicate a sprite with optional variation"""
    sprite_id: str = Field(..., min_length=1, description="Source sprite identifier")
    new_name: str = Field(..., min_length=1, max_length=100, description="Name for duplicated sprite")
    apply_variation: bool = Field(False, description="Whether to apply visual variation")
    variation_type: VariationType = Field(
        VariationType.HUE_SHIFT,
        description="Type of variation to apply"
    )

    @field_validator('new_name')
    @classmethod
    def validate_new_name(cls, v: str) -> str:
        """Validate and sanitize new sprite name"""
        sanitized = ''.join(c for c in v if c.isalnum() or c in (' ', '_', '-'))
        if not sanitized.strip():
            raise ValueError("Name must contain at least one alphanumeric character")
        return sanitized.strip()


class SpriteExportRequest(BaseModel):
    """Request to export a sprite"""
    sprite_id: str = Field(..., min_length=1, description="Sprite identifier")
    export_format: ExportFormat = Field(
        ExportFormat.GRID,
        description="Export format"
    )
    scale: int = Field(
        1,
        ge=1,
        le=8,
        description="Scale factor (1-8x)"
    )


# ============================================================================
# Knowledge Base Models
# ============================================================================

class KBSearchRequest(BaseModel):
    """Request to search the knowledge base"""
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query"
    )
    limit: int = Field(
        5,
        ge=1,
        le=20,
        description="Maximum number of results"
    )

    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Ensure query is not empty or only whitespace"""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty or only whitespace")
        return v.strip()


class DocumentUploadRequest(BaseModel):
    """Request to upload a document to knowledge base"""
    filename: str = Field(..., min_length=1, max_length=255, description="Document filename")
    content: str = Field(..., min_length=1, description="Document content")

    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Validate filename format"""
        if not v or not v.strip():
            raise ValueError("Filename cannot be empty")
        # Check for valid extension
        valid_extensions = ['.txt', '.md', '.json', '.yaml', '.yml']
        if not any(v.lower().endswith(ext) for ext in valid_extensions):
            raise ValueError(f"Invalid file extension. Must be one of: {valid_extensions}")
        return v.strip()


# ============================================================================
# Sprite Generation Models
# ============================================================================

class SpriteGenerationParams(BaseModel):
    """Parameters for sprite generation"""
    positive_prompt: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="What to generate"
    )
    negative_prompt: str = Field(
        default="blurry, bad quality, distorted",
        max_length=500,
        description="What to avoid"
    )
    seed: Optional[int] = Field(
        None,
        ge=0,
        description="Random seed for reproducibility"
    )
    width: int = Field(32, ge=16, le=128, description="Sprite width in pixels")
    height: int = Field(32, ge=16, le=128, description="Sprite height in pixels")
    num_frames: int = Field(8, ge=1, le=16, description="Number of animation frames")
    style_preset: Optional[str] = Field(None, description="Style preset to use")

    @field_validator('positive_prompt')
    @classmethod
    def validate_positive_prompt(cls, v: str) -> str:
        """Ensure prompt is not empty or only whitespace"""
        if not v or not v.strip():
            raise ValueError("Positive prompt cannot be empty or only whitespace")
        return v.strip()


class RegenerateRequest(BaseModel):
    """Request to regenerate a sprite"""
    session_id: str = Field(..., min_length=1, description="Session ID to regenerate")
    preset: Optional[str] = Field(None, description="Optional different style preset")


# ============================================================================
# Batch Operation Models
# ============================================================================

class BatchCSVRequest(BaseModel):
    """Request to process batch CSV"""
    csv_path: str = Field(..., min_length=1, description="Path to CSV file")
    session_id: str = Field(..., min_length=1, description="Session ID for tracking")

    @field_validator('csv_path')
    @classmethod
    def validate_csv_path(cls, v: str) -> str:
        """Validate CSV file path"""
        if not v.endswith('.csv'):
            raise ValueError("File must be a CSV file (.csv extension)")
        return v


class CharacterSetRequest(BaseModel):
    """Request to generate a complete character animation set"""
    character_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the character"
    )
    style: str = Field(..., min_length=1, description="Visual style")
    session_id: str = Field(..., min_length=1, description="Session ID for tracking")
    include_actions: Optional[List[str]] = Field(
        None,
        description="Specific actions to include (e.g., ['walk', 'jump'])"
    )

    @field_validator('character_name')
    @classmethod
    def validate_character_name(cls, v: str) -> str:
        """Validate and sanitize character name"""
        sanitized = ''.join(c for c in v if c.isalnum() or c in (' ', '_', '-'))
        if not sanitized.strip():
            raise ValueError("Character name must contain at least one alphanumeric character")
        return sanitized.strip()


class ProjectTemplateRequest(BaseModel):
    """Request to apply a project template"""
    template_name: str = Field(..., min_length=1, description="Template name")
    session_id: str = Field(..., min_length=1, description="Session ID for tracking")


# ============================================================================
# Style Preset Models
# ============================================================================

class StylePresetRequest(BaseModel):
    """Request for style preset operations"""
    preset_name: str = Field(..., min_length=1, description="Preset name")

    @field_validator('preset_name')
    @classmethod
    def validate_preset_name(cls, v: str) -> str:
        """Normalize preset name"""
        return v.lower().strip()


# ============================================================================
# Response Models
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response"""
    backend: str = Field(..., description="Backend health status")
    timestamp: str = Field(..., description="Timestamp of health check")
    uptime_seconds: float = Field(..., description="Backend uptime in seconds")
    services: Dict[str, Any] = Field(..., description="Status of individual services")


class GenerationResult(BaseModel):
    """Result of sprite generation"""
    status: str = Field(..., description="Generation status")
    prompt_id: Optional[str] = Field(None, description="ComfyUI prompt ID")
    frame_paths: List[str] = Field(default_factory=list, description="Paths to generated frames")
    preview_url: Optional[str] = Field(None, description="Preview image URL")
    session_id: str = Field(..., description="Session ID")
    correlation_id: str = Field(..., description="Correlation ID for tracing")
    degraded: bool = Field(False, description="Whether service is in degraded mode")


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
