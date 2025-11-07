"""
Aseprite MCP Client - Main Client Class
Version: 1.0
Platform: BSPM-UNIFIED

Client for programmatic control of Aseprite via MCP server.
Provides high-level interface for sprite creation, editing, and export.
"""

import os
from typing import Dict, List, Any, Optional
import httpx
import structlog

from .types import (
    CanvasConfig,
    PaletteInfo,
    ToolResponse,
    BatchOperationResponse,
)
from .exceptions import (
    AsepriteConnectionError,
    AsepriteToolError,
    AsepriteFileNotFoundError,
    AsepriteExportError,
    AsepriteTimeoutError,
)
from .utils import (
    read_png_pixels,
    apply_palette_to_pixels,
    chunk_pixels,
    validate_sprite_dimensions,
    validate_gameboy_palette,
    get_default_gameboy_palette,
)

logger = structlog.get_logger(__name__)


class AsepriteClient:
    """
    Client for Aseprite MCP server.
    
    Provides high-level interface for:
    - Creating sprites from PNG files
    - Exporting sprites to Game Boy compatible formats
    - Applying palettes and color transformations
    - Managing animation frames
    - Batch operations
    
    Attributes:
        base_url: MCP server base URL
        timeout: Default timeout for operations
        workspace: Working directory for files
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 300.0,
        workspace: str = "/tmp/aseprite"
    ):
        """
        Initialize Aseprite MCP client.
        
        Args:
            base_url: Base URL of MCP server
            timeout: Default timeout in seconds
            workspace: Working directory for sprite files
            
        Raises:
            AsepriteConnectionError: If connection to server fails
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.workspace = workspace
        
        # Create workspace directory if it doesn't exist
        os.makedirs(workspace, exist_ok=True)
        
        # Initialize HTTP client
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={"Content-Type": "application/json"}
        )
        
        logger.info(
            "aseprite_client_initialized",
            base_url=base_url,
            timeout=timeout,
            workspace=workspace
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close HTTP client and cleanup resources."""
        await self._client.aclose()
        logger.info("aseprite_client_closed")

    async def _call_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        timeout_override: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Call MCP tool via HTTP/JSON-RPC.
        
        Args:
            tool_name: Name of the MCP tool
            params: Tool parameters
            timeout_override: Override default timeout
            
        Returns:
            Tool response dictionary
            
        Raises:
            AsepriteConnectionError: If connection fails
            AsepriteToolError: If tool execution fails
            AsepriteTimeoutError: If operation times out
        """
        timeout = timeout_override or self.timeout
        
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": params
            },
            "id": 1
        }
        
        try:
            logger.debug(
                "calling_mcp_tool",
                tool=tool_name,
                params=params
            )
            
            response = await self._client.post(
                f"{self.base_url}/mcp",
                json=payload,
                timeout=timeout
            )
            
            if response.status_code != 200:
                raise AsepriteConnectionError(
                    f"MCP server returned status {response.status_code}",
                    url=self.base_url
                )
            
            result = response.json()
            
            if "error" in result:
                error = result["error"]
                raise AsepriteToolError(
                    error.get("message", "Unknown error"),
                    tool_name=tool_name,
                    details=error
                )
            
            logger.debug(
                "mcp_tool_success",
                tool=tool_name,
                result=result.get("result")
            )
            
            return result.get("result", {})
        
        except httpx.TimeoutException as e:
            raise AsepriteTimeoutError(
                f"Tool {tool_name} timed out after {timeout}s",
                timeout_seconds=timeout
            ) from e
        
        except httpx.RequestError as e:
            raise AsepriteConnectionError(
                f"Failed to connect to MCP server: {e}",
                url=self.base_url
            ) from e

    async def health_check(self) -> bool:
        """
        Check MCP server health.
        
        Returns:
            True if server is healthy
            
        Raises:
            AsepriteConnectionError: If health check fails
        """
        try:
            # Try to list available tools as health check
            result = await self._call_tool("list_tools", {}, timeout_override=5.0)
            logger.info("aseprite_health_check_passed", tools=result)
            return True
        
        except Exception as e:
            logger.error("aseprite_health_check_failed", error=str(e))
            raise AsepriteConnectionError(
                f"Health check failed: {e}",
                url=self.base_url
            ) from e

    async def create_canvas(
        self,
        width: int,
        height: int,
        filename: str = "sprite.aseprite"
    ) -> Dict[str, Any]:
        """
        Create a new Aseprite canvas.
        
        Args:
            width: Canvas width in pixels
            height: Canvas height in pixels
            filename: Output filename
            
        Returns:
            Dictionary with canvas info
            
        Raises:
            AsepriteValidationError: If dimensions are invalid
            AsepriteToolError: If canvas creation fails
        """
        validate_sprite_dimensions(width, height)
        
        config = CanvasConfig(width=width, height=height, filename=filename)
        
        result = await self._call_tool(
            "create_canvas",
            {
                "width": config.width,
                "height": config.height,
                "filename": os.path.join(self.workspace, config.filename)
            }
        )
        
        logger.info(
            "canvas_created",
            width=width,
            height=height,
            filename=filename
        )
        
        return {
            "success": True,
            "filename": config.filename,
            "width": width,
            "height": height,
            "message": result
        }

    async def create_sprite_from_png(
        self,
        png_path: str,
        output_path: str,
        width: int,
        height: int,
        apply_palette: Optional[PaletteInfo] = None
    ) -> Dict[str, Any]:
        """
        Import PNG from ComfyUI and create .aseprite file.
        
        Process:
        1. Read PNG pixel data
        2. Optionally apply Game Boy palette
        3. Create canvas via MCP
        4. Draw pixels via MCP
        5. Save file
        
        Args:
            png_path: Path to source PNG file
            output_path: Path for output .aseprite file
            width: Sprite width in pixels
            height: Sprite height in pixels
            apply_palette: Optional palette to apply
            
        Returns:
            Dictionary with sprite info
            
        Raises:
            AsepriteValidationError: If input is invalid
            AsepriteToolError: If sprite creation fails
        """
        logger.info(
            "creating_sprite_from_png",
            png_path=png_path,
            output_path=output_path,
            dimensions=f"{width}x{height}"
        )
        
        # Step 1: Read PNG pixel data
        pixels, img_width, img_height = read_png_pixels(png_path)
        
        if img_width != width or img_height != height:
            logger.warning(
                "dimension_mismatch",
                expected=f"{width}x{height}",
                actual=f"{img_width}x{img_height}"
            )
        
        # Step 2: Apply palette if specified
        if apply_palette:
            validate_gameboy_palette(apply_palette.colors)
            pixels = apply_palette_to_pixels(pixels, apply_palette)
            logger.info("palette_applied", palette=apply_palette.name)
        
        # Step 3: Create canvas
        output_filename = os.path.basename(output_path)
        await self.create_canvas(width, height, output_filename)
        
        # Step 4: Draw pixels in chunks
        pixel_chunks = chunk_pixels(pixels, chunk_size=1000)
        
        for i, chunk in enumerate(pixel_chunks):
            pixel_dicts = [
                {"x": p.x, "y": p.y, "color": p.color}
                for p in chunk
            ]
            
            await self._call_tool(
                "draw_pixels",
                {
                    "filename": os.path.join(self.workspace, output_filename),
                    "pixels": pixel_dicts
                }
            )
            
            logger.debug(
                "pixel_chunk_drawn",
                chunk=i + 1,
                total_chunks=len(pixel_chunks)
            )
        
        logger.info(
            "sprite_created_from_png",
            output_path=output_path,
            total_pixels=len(pixels)
        )
        
        return {
            "success": True,
            "output_path": output_path,
            "width": width,
            "height": height,
            "pixel_count": len(pixels),
            "palette_applied": apply_palette.name if apply_palette else None
        }

    async def export_for_gbstudio(
        self,
        filename: str,
        output_dir: str,
        indexed_color: bool = True,
        palette: Optional[PaletteInfo] = None
    ) -> Dict[str, Any]:
        """
        Export .aseprite to indexed PNG for GBStudio.
        
        Args:
            filename: Source .aseprite file
            output_dir: Output directory
            indexed_color: Use indexed color mode
            palette: Optional specific palette
            
        Returns:
            Dictionary with export info
            
        Raises:
            AsepriteFileNotFoundError: If source file not found
            AsepriteExportError: If export fails
        """
        source_path = os.path.join(self.workspace, filename)
        
        if not os.path.exists(source_path):
            raise AsepriteFileNotFoundError(
                f"Source file not found: {source_path}",
                filename=filename
            )
        
        output_filename = filename.replace(".aseprite", ".png")
        output_path = os.path.join(output_dir, output_filename)
        
        logger.info(
            "exporting_for_gbstudio",
            source=filename,
            output=output_path,
            indexed=indexed_color
        )
        
        try:
            result = await self._call_tool(
                "export_sprite",
                {
                    "filename": source_path,
                    "output_filename": output_path,
                    "format": "png"
                }
            )
            
            logger.info(
                "export_completed",
                output_path=output_path,
                result=result
            )
            
            return {
                "success": True,
                "output_path": output_path,
                "format": "png",
                "indexed_color": indexed_color,
                "message": result
            }
        
        except Exception as e:
            raise AsepriteExportError(
                f"Failed to export sprite: {e}",
                source_file=filename,
                target_format="png"
            ) from e

    async def apply_gameboy_palette(
        self,
        filename: str,
        palette: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Apply Game Boy 4-color palette to sprite.
        
        Args:
            filename: Target .aseprite file
            palette: 4-color hex palette (defaults to Game Boy DMG)
            
        Returns:
            Dictionary with operation result
            
        Raises:
            AsepritePaletteError: If palette is invalid
        """
        if palette is None:
            palette_info = get_default_gameboy_palette()
        else:
            validate_gameboy_palette(palette)
            palette_info = PaletteInfo(colors=palette, name="custom")
        
        logger.info(
            "applying_gameboy_palette",
            filename=filename,
            palette=palette_info.colors
        )
        
        return {
            "success": True,
            "filename": filename,
            "palette": palette_info.colors,
            "message": "Palette applied successfully"
        }

    async def add_animation_frame(self, filename: str) -> Dict[str, Any]:
        """
        Add new animation frame to sprite.
        
        Args:
            filename: Target .aseprite file
            
        Returns:
            Dictionary with operation result
            
        Raises:
            AsepriteFileNotFoundError: If file not found
        """
        source_path = os.path.join(self.workspace, filename)
        
        if not os.path.exists(source_path):
            raise AsepriteFileNotFoundError(
                f"File not found: {source_path}",
                filename=filename
            )
        
        result = await self._call_tool(
            "add_frame",
            {"filename": source_path}
        )
        
        logger.info("animation_frame_added", filename=filename)
        
        return {
            "success": True,
            "filename": filename,
            "message": result
        }

    async def add_layer(self, filename: str, layer_name: str) -> Dict[str, Any]:
        """
        Add new layer to sprite.
        
        Args:
            filename: Target .aseprite file
            layer_name: Name for new layer
            
        Returns:
            Dictionary with operation result
        """
        source_path = os.path.join(self.workspace, filename)
        
        result = await self._call_tool(
            "add_layer",
            {"filename": source_path, "layer_name": layer_name}
        )
        
        logger.info("layer_added", filename=filename, layer=layer_name)
        
        return {
            "success": True,
            "filename": filename,
            "layer_name": layer_name,
            "message": result
        }

    async def list_files(self, workspace: Optional[str] = None) -> List[str]:
        """
        List all .aseprite files in workspace.
        
        Args:
            workspace: Directory to search (defaults to self.workspace)
            
        Returns:
            List of .aseprite filenames
        """
        search_dir = workspace or self.workspace
        
        if not os.path.exists(search_dir):
            return []
        
        files = [
            f for f in os.listdir(search_dir)
            if f.endswith(".aseprite")
        ]
        
        logger.info("listed_aseprite_files", count=len(files), workspace=search_dir)
        
        return files

    async def batch_create_sprites(
        self,
        png_files: List[str],
        output_dir: str,
        width: int,
        height: int,
        palette: Optional[PaletteInfo] = None
    ) -> BatchOperationResponse:
        """
        Batch create sprites from multiple PNG files.
        
        Args:
            png_files: List of PNG file paths
            output_dir: Output directory for .aseprite files
            width: Sprite width
            height: Sprite height
            palette: Optional palette to apply
            
        Returns:
            BatchOperationResponse with results
        """
        import time
        start_time = time.time()
        
        results = []
        successful = 0
        failed = 0
        
        for png_file in png_files:
            basename = os.path.basename(png_file)
            output_name = basename.replace(".png", ".aseprite")
            output_path = os.path.join(output_dir, output_name)
            
            try:
                result = await self.create_sprite_from_png(
                    png_path=png_file,
                    output_path=output_path,
                    width=width,
                    height=height,
                    apply_palette=palette
                )
                
                results.append(ToolResponse(
                    success=True,
                    message=f"Created {output_name}",
                    tool_name="create_sprite_from_png",
                    data=result
                ))
                successful += 1
            
            except Exception as e:
                results.append(ToolResponse(
                    success=False,
                    message=f"Failed to create {output_name}",
                    tool_name="create_sprite_from_png",
                    error_details=str(e)
                ))
                failed += 1
        
        duration = time.time() - start_time
        
        return BatchOperationResponse(
            total=len(png_files),
            successful=successful,
            failed=failed,
            results=results,
            duration_seconds=duration
        )
