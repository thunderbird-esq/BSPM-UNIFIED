"""
Aseprite MCP Client Module
Version: 1.0
Platform: BSPM-UNIFIED

Python client for programmatic control of Aseprite via MCP server.
Provides integration between ComfyUI sprite generation and GBStudio export.
"""

from .client import AsepriteClient
from .types import (
    CanvasConfig,
    SpriteImportRequest,
    SpriteExportRequest,
    PaletteInfo,
    PixelData,
    ToolResponse,
    LineDrawing,
    RectangleDrawing,
    CircleDrawing,
    HealthCheckResponse,
    BatchOperationRequest,
    BatchOperationResponse,
)
from .exceptions import (
    AsepriteError,
    AsepriteConnectionError,
    AsepriteToolError,
    AsepriteValidationError,
    AsepriteFileNotFoundError,
    AsepriteExportError,
    AsepritePaletteError,
    AsepriteTimeoutError,
)
from .utils import (
    hex_to_rgb,
    rgb_to_hex,
    read_png_pixels,
    extract_palette_from_image,
    apply_palette_to_pixels,
    validate_gameboy_palette,
    get_default_gameboy_palette,
    chunk_pixels,
    validate_sprite_dimensions,
)

__version__ = "1.0.0"

__all__ = [
    # Main client
    "AsepriteClient",
    # Types
    "CanvasConfig",
    "SpriteImportRequest",
    "SpriteExportRequest",
    "PaletteInfo",
    "PixelData",
    "ToolResponse",
    "LineDrawing",
    "RectangleDrawing",
    "CircleDrawing",
    "HealthCheckResponse",
    "BatchOperationRequest",
    "BatchOperationResponse",
    # Exceptions
    "AsepriteError",
    "AsepriteConnectionError",
    "AsepriteToolError",
    "AsepriteValidationError",
    "AsepriteFileNotFoundError",
    "AsepriteExportError",
    "AsepritePaletteError",
    "AsepriteTimeoutError",
    # Utilities
    "hex_to_rgb",
    "rgb_to_hex",
    "read_png_pixels",
    "extract_palette_from_image",
    "apply_palette_to_pixels",
    "validate_gameboy_palette",
    "get_default_gameboy_palette",
    "chunk_pixels",
    "validate_sprite_dimensions",
]
