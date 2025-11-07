"""
Aseprite MCP Client - Type Definitions
Version: 1.0
Platform: BSPM-UNIFIED

Pydantic v2 models for Aseprite MCP client request/response types.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class PixelData(BaseModel):
    """Represents a single pixel with position and color."""

    x: int = Field(..., ge=0, description="X coordinate of the pixel")
    y: int = Field(..., ge=0, description="Y coordinate of the pixel")
    color: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color code")

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        """Ensure color is uppercase hex."""
        return v.upper()


class CanvasConfig(BaseModel):
    """Configuration for creating a new canvas."""

    width: int = Field(..., gt=0, le=4096, description="Canvas width in pixels")
    height: int = Field(..., gt=0, le=4096, description="Canvas height in pixels")
    filename: str = Field(..., description="Output filename (.aseprite)")

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Ensure filename has .aseprite extension."""
        if not v.endswith(".aseprite"):
            return f"{v}.aseprite"
        return v


class SpriteImportRequest(BaseModel):
    """Request to import PNG sprite from ComfyUI."""

    png_path: str = Field(..., description="Path to source PNG file")
    output_path: str = Field(..., description="Path for output .aseprite file")
    width: int = Field(..., gt=0, description="Sprite width in pixels")
    height: int = Field(..., gt=0, description="Sprite height in pixels")
    preserve_transparency: bool = Field(True, description="Preserve PNG transparency")


class SpriteExportRequest(BaseModel):
    """Request to export .aseprite to another format."""

    filename: str = Field(..., description="Source .aseprite file")
    output_path: str = Field(..., description="Output file path")
    format: str = Field("png", description="Output format (png, gif, jpg)")
    indexed_color: bool = Field(False, description="Use indexed color mode")
    palette_colors: Optional[List[str]] = Field(
        None, description="Specific palette colors"
    )

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Ensure format is lowercase."""
        return v.lower()


class PaletteInfo(BaseModel):
    """Game Boy palette information."""

    colors: List[str] = Field(
        ..., min_length=4, max_length=4, description="4 hex color codes"
    )
    name: str = Field("gameboy", description="Palette name")

    @field_validator("colors")
    @classmethod
    def validate_colors(cls, v: List[str]) -> List[str]:
        """Validate palette colors are hex codes."""
        for color in v:
            if not color.startswith("#") or len(color) != 7:
                raise ValueError(f"Invalid color format: {color}")
        return v


class DrawingOperation(BaseModel):
    """Base class for drawing operations."""

    filename: str = Field(..., description="Target .aseprite file")
    operation_type: str = Field(..., description="Type of drawing operation")


class LineDrawing(DrawingOperation):
    """Draw a line operation."""

    operation_type: str = "line"
    x1: int = Field(..., description="Start X coordinate")
    y1: int = Field(..., description="Start Y coordinate")
    x2: int = Field(..., description="End X coordinate")
    y2: int = Field(..., description="End Y coordinate")
    color: str = Field("#000000", description="Line color")
    thickness: int = Field(1, ge=1, description="Line thickness")


class RectangleDrawing(DrawingOperation):
    """Draw a rectangle operation."""

    operation_type: str = "rectangle"
    x: int = Field(..., description="Top-left X coordinate")
    y: int = Field(..., description="Top-left Y coordinate")
    width: int = Field(..., gt=0, description="Rectangle width")
    height: int = Field(..., gt=0, description="Rectangle height")
    color: str = Field("#000000", description="Rectangle color")
    fill: bool = Field(False, description="Fill rectangle")


class CircleDrawing(DrawingOperation):
    """Draw a circle operation."""

    operation_type: str = "circle"
    center_x: int = Field(..., description="Center X coordinate")
    center_y: int = Field(..., description="Center Y coordinate")
    radius: int = Field(..., gt=0, description="Circle radius")
    color: str = Field("#000000", description="Circle color")
    fill: bool = Field(False, description="Fill circle")


class ToolResponse(BaseModel):
    """Response from MCP tool execution."""

    success: bool = Field(..., description="Whether operation succeeded")
    message: str = Field(..., description="Result message")
    tool_name: str = Field(..., description="Name of the tool executed")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional response data")
    error_details: Optional[str] = Field(None, description="Error details if failed")


class FileInfo(BaseModel):
    """Information about an Aseprite file."""

    filename: str = Field(..., description="File name")
    width: int = Field(..., description="Canvas width")
    height: int = Field(..., description="Canvas height")
    frame_count: int = Field(..., description="Number of animation frames")
    layer_count: int = Field(..., description="Number of layers")


class HealthCheckResponse(BaseModel):
    """Health check response from MCP server."""

    healthy: bool = Field(..., description="Server health status")
    version: Optional[str] = Field(None, description="MCP server version")
    uptime_seconds: Optional[float] = Field(None, description="Server uptime")
    tools_available: List[str] = Field(
        default_factory=list, description="Available MCP tools"
    )


class BatchOperationRequest(BaseModel):
    """Request for batch operations on multiple sprites."""

    operations: List[Dict[str, Any]] = Field(..., description="List of operations")
    stop_on_error: bool = Field(True, description="Stop batch if any operation fails")
    max_concurrent: int = Field(5, ge=1, le=20, description="Max concurrent operations")


class BatchOperationResponse(BaseModel):
    """Response from batch operations."""

    total: int = Field(..., description="Total operations")
    successful: int = Field(..., description="Successful operations")
    failed: int = Field(..., description="Failed operations")
    results: List[ToolResponse] = Field(..., description="Individual results")
    duration_seconds: float = Field(..., description="Total duration")
