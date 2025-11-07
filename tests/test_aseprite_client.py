"""
Aseprite MCP Client - Test Suite
Version: 1.0
Platform: BSPM-UNIFIED

Comprehensive tests for Aseprite MCP client functionality.
"""

import os
import tempfile
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
import pytest_asyncio
from PIL import Image

from backend.aseprite import (AsepriteClient, AsepriteConnectionError,
                              AsepriteFileNotFoundError, AsepriteToolError,
                              AsepriteValidationError)
from backend.aseprite.utils import (get_default_gameboy_palette, hex_to_rgb,
                                    rgb_to_hex, validate_gameboy_palette)


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for testing."""
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


@pytest_asyncio.fixture
async def aseprite_client(temp_workspace):
    """Create AsepriteClient instance for testing."""
    client = AsepriteClient(
        base_url="http://localhost:8000", timeout=30.0, workspace=temp_workspace
    )
    yield client
    await client.close()


@pytest.fixture
def sample_png(temp_workspace):
    """Create a sample PNG file for testing."""
    img = Image.new("RGB", (16, 16), color=(255, 0, 0))
    png_path = os.path.join(temp_workspace, "test_sprite.png")
    img.save(png_path)
    return png_path


class TestClientInitialization:
    """Test client initialization and configuration."""

    def test_client_initialization(self, temp_workspace):
        """Test basic client initialization."""
        client = AsepriteClient(
            base_url="http://localhost:8000", timeout=60.0, workspace=temp_workspace
        )

        assert client.base_url == "http://localhost:8000"
        assert client.timeout == 60.0
        assert client.workspace == temp_workspace
        assert os.path.exists(temp_workspace)

    def test_client_initialization_creates_workspace(self):
        """Test that client creates workspace directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, "new_workspace")
            assert not os.path.exists(workspace)

            _client = AsepriteClient(workspace=workspace)
            assert os.path.exists(workspace)

    @pytest.mark.asyncio
    async def test_client_context_manager(self, temp_workspace):
        """Test client as async context manager."""
        async with AsepriteClient(workspace=temp_workspace) as client:
            assert client is not None
            assert client.workspace == temp_workspace


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_pass(self, aseprite_client):
        """Test successful health check."""
        with patch.object(
            aseprite_client, "_call_tool", new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = {"tools": ["create_canvas", "draw_pixels"]}

            result = await aseprite_client.health_check()

            assert result is True
            mock_call.assert_called_once_with("list_tools", {}, timeout_override=5.0)

    @pytest.mark.asyncio
    async def test_health_check_fail(self, aseprite_client):
        """Test failed health check."""
        with patch.object(
            aseprite_client, "_call_tool", new_callable=AsyncMock
        ) as mock_call:
            mock_call.side_effect = Exception("Connection failed")

            with pytest.raises(AsepriteConnectionError):
                await aseprite_client.health_check()


class TestCanvasCreation:
    """Test canvas creation functionality."""

    @pytest.mark.asyncio
    async def test_create_canvas_success(self, aseprite_client):
        """Test successful canvas creation."""
        with patch.object(
            aseprite_client, "_call_tool", new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = "Canvas created successfully"

            result = await aseprite_client.create_canvas(
                width=64, height=64, filename="test.aseprite"
            )

            assert result["success"] is True
            assert result["width"] == 64
            assert result["height"] == 64
            assert result["filename"] == "test.aseprite"

    @pytest.mark.asyncio
    async def test_create_canvas_invalid_dimensions(self, aseprite_client):
        """Test canvas creation with invalid dimensions."""
        with pytest.raises(AsepriteValidationError):
            await aseprite_client.create_canvas(width=0, height=64)

        with pytest.raises(AsepriteValidationError):
            await aseprite_client.create_canvas(width=64, height=-10)

        with pytest.raises(AsepriteValidationError):
            await aseprite_client.create_canvas(width=5000, height=5000)


class TestSpriteCreation:
    """Test sprite creation from PNG."""

    @pytest.mark.asyncio
    async def test_create_sprite_from_png_success(self, aseprite_client, sample_png):
        """Test successful sprite creation from PNG."""
        with patch.object(
            aseprite_client, "_call_tool", new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = "Success"

            result = await aseprite_client.create_sprite_from_png(
                png_path=sample_png, output_path="output.aseprite", width=16, height=16
            )

            assert result["success"] is True
            assert result["width"] == 16
            assert result["height"] == 16
            assert "pixel_count" in result

    @pytest.mark.asyncio
    async def test_create_sprite_from_png_with_palette(
        self, aseprite_client, sample_png
    ):
        """Test sprite creation with Game Boy palette."""
        palette = get_default_gameboy_palette()

        with patch.object(
            aseprite_client, "_call_tool", new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = "Success"

            result = await aseprite_client.create_sprite_from_png(
                png_path=sample_png,
                output_path="output.aseprite",
                width=16,
                height=16,
                apply_palette=palette,
            )

            assert result["success"] is True
            assert result["palette_applied"] == "gameboy_dmg"

    @pytest.mark.asyncio
    async def test_create_sprite_from_png_missing_file(self, aseprite_client):
        """Test sprite creation with missing PNG file."""
        with pytest.raises(AsepriteValidationError):
            await aseprite_client.create_sprite_from_png(
                png_path="/nonexistent/file.png",
                output_path="output.aseprite",
                width=16,
                height=16,
            )


class TestSpriteExport:
    """Test sprite export functionality."""

    @pytest.mark.asyncio
    async def test_export_for_gbstudio_success(self, aseprite_client, temp_workspace):
        """Test successful export for GBStudio."""
        # Create a dummy aseprite file
        test_file = os.path.join(temp_workspace, "test.aseprite")
        with open(test_file, "w") as f:
            f.write("dummy")

        with patch.object(
            aseprite_client, "_call_tool", new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = "Export successful"

            result = await aseprite_client.export_for_gbstudio(
                filename="test.aseprite", output_dir=temp_workspace
            )

            assert result["success"] is True
            assert result["format"] == "png"
            assert "output_path" in result

    @pytest.mark.asyncio
    async def test_export_for_gbstudio_file_not_found(
        self, aseprite_client, temp_workspace
    ):
        """Test export with missing source file."""
        with pytest.raises(AsepriteFileNotFoundError):
            await aseprite_client.export_for_gbstudio(
                filename="nonexistent.aseprite", output_dir=temp_workspace
            )


class TestAnimationFrames:
    """Test animation frame management."""

    @pytest.mark.asyncio
    async def test_add_animation_frame(self, aseprite_client, temp_workspace):
        """Test adding animation frame."""
        # Create a dummy aseprite file
        test_file = os.path.join(temp_workspace, "test.aseprite")
        with open(test_file, "w") as f:
            f.write("dummy")

        with patch.object(
            aseprite_client, "_call_tool", new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = "Frame added"

            result = await aseprite_client.add_animation_frame("test.aseprite")

            assert result["success"] is True
            assert result["filename"] == "test.aseprite"

    @pytest.mark.asyncio
    async def test_add_animation_frame_file_not_found(self, aseprite_client):
        """Test adding frame to nonexistent file."""
        with pytest.raises(AsepriteFileNotFoundError):
            await aseprite_client.add_animation_frame("nonexistent.aseprite")


class TestErrorHandling:
    """Test error handling and exceptions."""

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, aseprite_client):
        """Test connection error handling."""
        with patch.object(
            aseprite_client._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = httpx.RequestError("Connection refused")

            with pytest.raises(AsepriteConnectionError):
                await aseprite_client._call_tool("test_tool", {})

    @pytest.mark.asyncio
    async def test_tool_error_handling(self, aseprite_client):
        """Test tool execution error handling."""
        with patch.object(
            aseprite_client._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "error": {"message": "Tool execution failed", "code": -32000}
            }
            mock_post.return_value = mock_response

            with pytest.raises(AsepriteToolError) as exc_info:
                await aseprite_client._call_tool("test_tool", {})

            assert exc_info.value.tool_name == "test_tool"

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, aseprite_client):
        """Test timeout error handling."""
        with patch.object(
            aseprite_client._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timed out")

            with pytest.raises(
                Exception
            ):  # Will be caught and re-raised as AsepriteTimeoutError
                await aseprite_client._call_tool("test_tool", {})


class TestUtilityFunctions:
    """Test utility functions."""

    def test_hex_to_rgb(self):
        """Test hex to RGB conversion."""
        assert hex_to_rgb("#FF0000") == (255, 0, 0)
        assert hex_to_rgb("#00FF00") == (0, 255, 0)
        assert hex_to_rgb("#0000FF") == (0, 0, 255)

    def test_rgb_to_hex(self):
        """Test RGB to hex conversion."""
        assert rgb_to_hex(255, 0, 0) == "#FF0000"
        assert rgb_to_hex(0, 255, 0) == "#00FF00"
        assert rgb_to_hex(0, 0, 255) == "#0000FF"

    def test_validate_gameboy_palette(self):
        """Test Game Boy palette validation."""
        valid_palette = ["#0F380F", "#306230", "#8BAC0F", "#9BBC0F"]
        assert validate_gameboy_palette(valid_palette) is True

        invalid_palette = ["#FF0000", "#00FF00"]  # Only 2 colors
        with pytest.raises(Exception):
            validate_gameboy_palette(invalid_palette)

    def test_get_default_gameboy_palette(self):
        """Test getting default Game Boy palette."""
        palette = get_default_gameboy_palette()
        assert len(palette.colors) == 4
        assert palette.name == "gameboy_dmg"


class TestFileManagement:
    """Test file listing and management."""

    @pytest.mark.asyncio
    async def test_list_files_empty(self, aseprite_client, temp_workspace):
        """Test listing files in empty workspace."""
        files = await aseprite_client.list_files()
        assert files == []

    @pytest.mark.asyncio
    async def test_list_files_with_sprites(self, aseprite_client, temp_workspace):
        """Test listing files with sprites present."""
        # Create dummy aseprite files
        for i in range(3):
            filepath = os.path.join(temp_workspace, f"sprite_{i}.aseprite")
            with open(filepath, "w") as f:
                f.write("dummy")

        files = await aseprite_client.list_files()
        assert len(files) == 3
        assert all(f.endswith(".aseprite") for f in files)


class TestBatchOperations:
    """Test batch operations."""

    @pytest.mark.asyncio
    async def test_batch_create_sprites(self, aseprite_client, temp_workspace):
        """Test batch sprite creation."""
        # Create sample PNG files
        png_files = []
        for i in range(3):
            img = Image.new("RGB", (16, 16), color=(255, 0, 0))
            png_path = os.path.join(temp_workspace, f"sprite_{i}.png")
            img.save(png_path)
            png_files.append(png_path)

        with patch.object(
            aseprite_client, "_call_tool", new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = "Success"

            result = await aseprite_client.batch_create_sprites(
                png_files=png_files, output_dir=temp_workspace, width=16, height=16
            )

            assert result.total == 3
            assert result.successful == 3
            assert result.failed == 0


# Run tests with: pytest tests/test_aseprite_client.py -v
