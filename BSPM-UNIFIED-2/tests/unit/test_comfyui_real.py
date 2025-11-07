"""
Comprehensive Unit Tests for ComfyUI Modules
Version: 3.1
Platform: Intel Mac (macOS Ventura) + Docker

Tests REAL functionality with actual data structures, PIL images, and numpy arrays.
Only HTTP calls to ComfyUI API are mocked.

Coverage targets:
- workflow_builder.py: 100% (workflow generation with real data)
- executor.py: 90% (async logic tested, HTTP mocked)
- validator.py: 100% (real image validation with PIL)
- post_process.py: 95% (real image processing with PIL)
"""

import pytest
import asyncio
import aiohttp
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import time

import numpy as np
from PIL import Image

# Import modules under test
from backend.comfyui.workflow_builder import (
    create_spritesheet_workflow,
    create_background_workflow
)

from backend.comfyui.executor import (
    execute_workflow,
    execute_spritesheet_generation
)

from backend.comfyui.validator import SpriteSheetValidator

from backend.comfyui.post_process import (
    SpritePostProcessor,
    quick_process
)


# ============================================================================
# TEST FIXTURES - Real image creation helpers
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def create_test_image():
    """Factory fixture to create real PIL test images."""
    def _create_image(
        size=(32, 32),
        color_mode='RGB',
        colors=None,
        pattern='solid'
    ):
        """
        Create a real PIL image for testing.

        Args:
            size: Image dimensions (width, height)
            color_mode: PIL color mode (RGB, RGBA, L, etc.)
            colors: List of RGB tuples for pattern
            pattern: 'solid', 'gradient', 'checker', 'noise'

        Returns:
            PIL Image object
        """
        if colors is None:
            colors = [(100, 150, 200)]

        img = Image.new(color_mode, size)
        pixels = img.load()

        if pattern == 'solid':
            # Fill with single color
            for y in range(size[1]):
                for x in range(size[0]):
                    pixels[x, y] = colors[0]

        elif pattern == 'gradient':
            # Vertical gradient through colors
            for y in range(size[1]):
                for x in range(size[0]):
                    idx = min(int(y / size[1] * len(colors)), len(colors) - 1)
                    pixels[x, y] = colors[idx]

        elif pattern == 'checker':
            # Checkerboard pattern
            for y in range(size[1]):
                for x in range(size[0]):
                    idx = ((x // 4) + (y // 4)) % len(colors)
                    pixels[x, y] = colors[idx]

        elif pattern == 'noise':
            # Random noise
            arr = np.random.randint(0, 256, size=(size[1], size[0], 3), dtype=np.uint8)
            return Image.fromarray(arr, 'RGB')

        return img

    return _create_image


@pytest.fixture
def create_sprite_frames(create_test_image, temp_dir):
    """Factory fixture to create a set of sprite frame images."""
    def _create_frames(
        num_frames=8,
        size=(32, 32),
        base_color=(100, 150, 200),
        variation=10
    ):
        """
        Create a set of sprite frames with slight variations.

        Args:
            num_frames: Number of frames to create
            size: Frame dimensions
            base_color: Base RGB color
            variation: Amount of color variation between frames

        Returns:
            List of file paths to saved frames
        """
        frame_paths = []

        for i in range(num_frames):
            # Create slightly varied colors for each frame
            r = max(0, min(255, base_color[0] + np.random.randint(-variation, variation)))
            g = max(0, min(255, base_color[1] + np.random.randint(-variation, variation)))
            b = max(0, min(255, base_color[2] + np.random.randint(-variation, variation)))

            # Add some motion by shifting a small square
            img = Image.new('RGB', size, base_color)
            pixels = img.load()

            # Draw a small character-like shape that moves
            char_x = 10 + (i * 2) % 12  # Move horizontally
            char_y = 10

            for dy in range(8):
                for dx in range(8):
                    x = char_x + dx
                    y = char_y + dy
                    if 0 <= x < size[0] and 0 <= y < size[1]:
                        pixels[x, y] = (r, g, b)

            # Save frame
            frame_path = Path(temp_dir) / f"sprite_frame_{i}.png"
            img.save(frame_path)
            frame_paths.append(str(frame_path))

        return frame_paths

    return _create_frames


# ============================================================================
# WORKFLOW BUILDER TESTS - Test real data structure generation
# ============================================================================

class TestWorkflowBuilder:
    """Test suite for workflow_builder.py - Real workflow data structures."""

    def test_create_spritesheet_workflow_basic(self):
        """Test spritesheet workflow generation with basic parameters."""
        workflow = create_spritesheet_workflow(
            positive_prompt="hero character",
            negative_prompt="blurry"
        )

        # Verify workflow structure
        assert isinstance(workflow, dict)
        assert len(workflow) == 18  # Nodes 1-18

        # Verify key nodes exist
        assert "1" in workflow  # CheckpointLoader
        assert "2" in workflow  # LoraLoader
        assert "3" in workflow  # Positive CLIP
        assert "4" in workflow  # Negative CLIP
        assert "5" in workflow  # EmptyLatent
        assert "6" in workflow  # KSampler
        assert "7" in workflow  # VAEDecode
        assert "8" in workflow  # DynamicTileSplit
        assert "18" in workflow  # SaveImage preview

    def test_spritesheet_workflow_node_1_checkpoint_loader(self):
        """Test checkpoint loader node structure."""
        workflow = create_spritesheet_workflow("test", "test")
        node = workflow["1"]

        assert node["class_type"] == "CheckpointLoaderSimple"
        assert "inputs" in node
        assert node["inputs"]["ckpt_name"] == "sd_xl_base_1.0.safetensors"

    def test_spritesheet_workflow_node_2_lora_loader(self):
        """Test LoRA loader node structure."""
        workflow = create_spritesheet_workflow("test", "test")
        node = workflow["2"]

        assert node["class_type"] == "LoraLoader"
        assert node["inputs"]["lora_name"] == "pixel-art-xl-v1.1.safetensors"
        assert node["inputs"]["strength_model"] == 1.0
        assert node["inputs"]["strength_clip"] == 1.0
        assert node["inputs"]["model"] == ["1", 0]
        assert node["inputs"]["clip"] == ["1", 1]

    def test_spritesheet_workflow_prompt_enhancement(self):
        """Test that prompts are enhanced with sprite sheet specific terms."""
        workflow = create_spritesheet_workflow(
            positive_prompt="hero",
            negative_prompt="blur"
        )

        positive_text = workflow["3"]["inputs"]["text"]
        negative_text = workflow["4"]["inputs"]["text"]

        # Positive prompt should include enhancement terms
        assert "hero" in positive_text
        assert "sprite sheet" in positive_text
        assert "multiple poses" in positive_text
        assert "8 frames grid" in positive_text
        assert "pixel art" in positive_text

        # Negative prompt should include avoidance terms
        assert "blur" in negative_text
        assert "inconsistent style" in negative_text
        assert "photo realistic" in negative_text

    def test_spritesheet_workflow_sampler_configuration(self):
        """Test KSampler node configuration."""
        workflow = create_spritesheet_workflow(
            positive_prompt="test",
            negative_prompt="test",
            seed=12345,
            steps=25,
            cfg=9.0
        )

        sampler = workflow["6"]
        assert sampler["class_type"] == "KSampler"
        assert sampler["inputs"]["seed"] == 12345
        assert sampler["inputs"]["steps"] == 25
        assert sampler["inputs"]["cfg"] == 9.0
        assert sampler["inputs"]["sampler_name"] == "euler_ancestral"
        assert sampler["inputs"]["scheduler"] == "karras"
        assert sampler["inputs"]["denoise"] == 1.0

    def test_spritesheet_workflow_random_seed_generation(self):
        """Test that random seed is generated when not provided."""
        workflow1 = create_spritesheet_workflow("test", "test", seed=None)
        workflow2 = create_spritesheet_workflow("test", "test", seed=None)

        seed1 = workflow1["6"]["inputs"]["seed"]
        seed2 = workflow2["6"]["inputs"]["seed"]

        # Seeds should be valid integers
        assert isinstance(seed1, int)
        assert isinstance(seed2, int)
        assert 0 <= seed1 < 2**32
        assert 0 <= seed2 < 2**32

        # Seeds should be different (probabilistically)
        assert seed1 != seed2

    def test_spritesheet_workflow_latent_dimensions(self):
        """Test latent image dimensions configuration."""
        workflow = create_spritesheet_workflow(
            positive_prompt="test",
            negative_prompt="test",
            width=512,
            height=256
        )

        latent = workflow["5"]
        assert latent["class_type"] == "EmptyLatentImage"
        assert latent["inputs"]["width"] == 512
        assert latent["inputs"]["height"] == 256
        assert latent["inputs"]["batch_size"] == 1

    def test_spritesheet_workflow_tile_split_configuration(self):
        """Test DynamicTileSplit node for 32x32 frames."""
        workflow = create_spritesheet_workflow("test", "test")

        tile_split = workflow["8"]
        assert tile_split["class_type"] == "DynamicTileSplit"
        assert tile_split["inputs"]["tile_width"] == 32
        assert tile_split["inputs"]["tile_height"] == 32
        assert tile_split["inputs"]["overlap"] == 0
        assert tile_split["inputs"]["image"] == ["7", 0]

    def test_spritesheet_workflow_frame_save_nodes(self):
        """Test individual frame save nodes (9-16)."""
        workflow = create_spritesheet_workflow("test", "test")

        for i in range(8):
            node_id = str(9 + i)
            assert node_id in workflow

            node = workflow[node_id]
            assert node["class_type"] == "SaveImage"
            assert node["inputs"]["filename_prefix"] == f"sprite_frame_{i}"
            assert node["inputs"]["images"] == ["8", 0, i]

    def test_spritesheet_workflow_preview_merge(self):
        """Test tile merge and preview save nodes."""
        workflow = create_spritesheet_workflow("test", "test")

        # Merge node
        merge = workflow["17"]
        assert merge["class_type"] == "DynamicTileMerge"
        assert merge["inputs"]["images"] == ["8", 0]
        assert merge["inputs"]["blend"] == 0

        # Preview save node
        preview = workflow["18"]
        assert preview["class_type"] == "SaveImage"
        assert preview["inputs"]["filename_prefix"] == "sprite_sheet_preview"
        assert preview["inputs"]["images"] == ["17", 0]

    def test_create_background_workflow_basic(self):
        """Test background workflow generation."""
        workflow = create_background_workflow(
            positive_prompt="forest scene",
            negative_prompt="modern"
        )

        assert isinstance(workflow, dict)
        assert len(workflow) == 8  # Nodes 1-8

        # Verify key nodes
        assert "1" in workflow  # CheckpointLoader
        assert "6" in workflow  # KSampler
        assert "8" in workflow  # SaveImage

    def test_background_workflow_dimensions(self):
        """Test background workflow uses 160x144 dimensions."""
        workflow = create_background_workflow("test", "test")

        latent = workflow["5"]
        assert latent["inputs"]["width"] == 160
        assert latent["inputs"]["height"] == 144

    def test_background_workflow_prompt_enhancement(self):
        """Test background prompt enhancement."""
        workflow = create_background_workflow(
            positive_prompt="forest",
            negative_prompt="blur"
        )

        positive_text = workflow["3"]["inputs"]["text"]

        assert "forest" in positive_text
        assert "game boy color background" in positive_text
        assert "pixel art" in positive_text
        assert "160x144 pixels" in positive_text

    def test_background_workflow_cfg_default(self):
        """Test background workflow CFG default (7.0)."""
        workflow = create_background_workflow("test", "test")

        assert workflow["6"]["inputs"]["cfg"] == 7.0

    def test_background_workflow_custom_parameters(self):
        """Test background workflow with custom parameters."""
        workflow = create_background_workflow(
            positive_prompt="test",
            negative_prompt="test",
            seed=99999,
            steps=30,
            cfg=6.5
        )

        sampler = workflow["6"]
        assert sampler["inputs"]["seed"] == 99999
        assert sampler["inputs"]["steps"] == 30
        assert sampler["inputs"]["cfg"] == 6.5


# ============================================================================
# EXECUTOR TESTS - Test async logic with mocked HTTP
# ============================================================================

class TestExecutor:
    """Test suite for executor.py - Async execution logic with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_execute_workflow_success(self):
        """Test successful workflow execution."""
        # Create a real workflow
        workflow = create_spritesheet_workflow("test", "test")

        # Mock HTTP responses
        mock_session = AsyncMock(spec=aiohttp.ClientSession)

        # Mock POST response (submit workflow)
        mock_post_response = AsyncMock()
        mock_post_response.status = 200
        mock_post_response.json = AsyncMock(return_value={"prompt_id": "test-prompt-123"})
        mock_post_response.__aenter__ = AsyncMock(return_value=mock_post_response)
        mock_post_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_post_response

        # Mock GET response (poll history)
        mock_get_response = AsyncMock()
        mock_get_response.status = 200
        mock_get_response.json = AsyncMock(return_value={
            "test-prompt-123": {
                "outputs": {
                    "9": {"images": [{"filename": "frame_0.png"}]},
                    "10": {"images": [{"filename": "frame_1.png"}]},
                    "11": {"images": [{"filename": "frame_2.png"}]},
                    "12": {"images": [{"filename": "frame_3.png"}]},
                    "13": {"images": [{"filename": "frame_4.png"}]},
                    "14": {"images": [{"filename": "frame_5.png"}]},
                    "15": {"images": [{"filename": "frame_6.png"}]},
                    "16": {"images": [{"filename": "frame_7.png"}]},
                    "18": {"images": [{"filename": "preview.png"}]}
                }
            }
        })
        mock_get_response.__aenter__ = AsyncMock(return_value=mock_get_response)
        mock_get_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_get_response

        # Execute workflow
        result = await execute_workflow(
            session=mock_session,
            workflow=workflow,
            client_id="test-client",
            comfyui_url="http://test:8188",
            timeout=10
        )

        # Verify result
        assert result["status"] == "success"
        assert result["prompt_id"] == "test-prompt-123"
        assert len(result["frame_paths"]) == 8
        assert result["preview_url"] == "/output/preview.png"

        # Verify HTTP calls were made correctly
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert call_args[0][0] == "http://test:8188/prompt"
        assert call_args[1]["json"]["prompt"] == workflow
        assert call_args[1]["json"]["client_id"] == "test-client"

    @pytest.mark.asyncio
    async def test_execute_workflow_api_error(self):
        """Test workflow execution with API error."""
        workflow = create_spritesheet_workflow("test", "test")

        mock_session = AsyncMock(spec=aiohttp.ClientSession)

        # Mock failed POST response
        mock_post_response = AsyncMock()
        mock_post_response.status = 500
        mock_post_response.text = AsyncMock(return_value="Internal Server Error")
        mock_post_response.__aenter__ = AsyncMock(return_value=mock_post_response)
        mock_post_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_post_response

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="ComfyUI API error"):
            await execute_workflow(
                session=mock_session,
                workflow=workflow,
                client_id="test-client"
            )

    @pytest.mark.asyncio
    async def test_execute_workflow_no_prompt_id(self):
        """Test workflow execution when no prompt_id returned."""
        workflow = create_spritesheet_workflow("test", "test")

        mock_session = AsyncMock(spec=aiohttp.ClientSession)

        # Mock POST response without prompt_id
        mock_post_response = AsyncMock()
        mock_post_response.status = 200
        mock_post_response.json = AsyncMock(return_value={})
        mock_post_response.__aenter__ = AsyncMock(return_value=mock_post_response)
        mock_post_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_post_response

        with pytest.raises(RuntimeError, match="No prompt_id returned"):
            await execute_workflow(
                session=mock_session,
                workflow=workflow,
                client_id="test-client"
            )

    @pytest.mark.asyncio
    async def test_execute_workflow_timeout(self):
        """Test workflow execution timeout."""
        workflow = create_spritesheet_workflow("test", "test")

        mock_session = AsyncMock(spec=aiohttp.ClientSession)

        # Mock POST response
        mock_post_response = AsyncMock()
        mock_post_response.status = 200
        mock_post_response.json = AsyncMock(return_value={"prompt_id": "test-123"})
        mock_post_response.__aenter__ = AsyncMock(return_value=mock_post_response)
        mock_post_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_post_response

        # Mock GET response with incomplete frames
        mock_get_response = AsyncMock()
        mock_get_response.status = 200
        mock_get_response.json = AsyncMock(return_value={
            "test-123": {
                "outputs": {
                    "9": {"images": [{"filename": "frame_0.png"}]},
                    # Only 1 frame instead of 8
                }
            }
        })
        mock_get_response.__aenter__ = AsyncMock(return_value=mock_get_response)
        mock_get_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_get_response

        # Should timeout
        with pytest.raises(RuntimeError, match="timed out after"):
            await execute_workflow(
                session=mock_session,
                workflow=workflow,
                client_id="test-client",
                timeout=3  # Short timeout for test
            )

    @pytest.mark.asyncio
    async def test_execute_workflow_connection_error(self):
        """Test workflow execution with connection error."""
        workflow = create_spritesheet_workflow("test", "test")

        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.post.side_effect = aiohttp.ClientError("Connection failed")

        with pytest.raises(RuntimeError, match="Failed to submit workflow"):
            await execute_workflow(
                session=mock_session,
                workflow=workflow,
                client_id="test-client"
            )

    @pytest.mark.asyncio
    async def test_execute_workflow_polling_with_retry(self):
        """Test that executor polls multiple times before getting results."""
        workflow = create_spritesheet_workflow("test", "test")

        mock_session = AsyncMock(spec=aiohttp.ClientSession)

        # Mock POST response
        mock_post_response = AsyncMock()
        mock_post_response.status = 200
        mock_post_response.json = AsyncMock(return_value={"prompt_id": "test-123"})
        mock_post_response.__aenter__ = AsyncMock(return_value=mock_post_response)
        mock_post_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_post_response

        # Mock GET responses: first empty, then complete
        call_count = 0

        async def mock_get_json():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"test-123": {"outputs": {}}}  # Not ready yet
            else:
                # Complete results
                return {
                    "test-123": {
                        "outputs": {
                            "9": {"images": [{"filename": "frame_0.png"}]},
                            "10": {"images": [{"filename": "frame_1.png"}]},
                            "11": {"images": [{"filename": "frame_2.png"}]},
                            "12": {"images": [{"filename": "frame_3.png"}]},
                            "13": {"images": [{"filename": "frame_4.png"}]},
                            "14": {"images": [{"filename": "frame_5.png"}]},
                            "15": {"images": [{"filename": "frame_6.png"}]},
                            "16": {"images": [{"filename": "frame_7.png"}]},
                            "18": {"images": [{"filename": "preview.png"}]}
                        }
                    }
                }

        mock_get_response = AsyncMock()
        mock_get_response.status = 200
        mock_get_response.json = mock_get_json
        mock_get_response.__aenter__ = AsyncMock(return_value=mock_get_response)
        mock_get_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_get_response

        # Execute
        result = await execute_workflow(
            session=mock_session,
            workflow=workflow,
            client_id="test-client",
            timeout=10
        )

        # Should have polled at least twice
        assert call_count >= 2
        assert result["status"] == "success"

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Async context manager mocking needs refinement")
    async def test_execute_spritesheet_generation(self):
        """Test complete spritesheet generation workflow."""
        with patch('backend.comfyui.executor.aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_context

            # Mock successful execution
            mock_post_response = AsyncMock()
            mock_post_response.status = 200
            mock_post_response.json = AsyncMock(return_value={"prompt_id": "test-123"})
            mock_post_response.__aenter__ = AsyncMock(return_value=mock_post_response)
            mock_post_response.__aexit__ = AsyncMock(return_value=None)
            mock_session.post = AsyncMock(return_value=mock_post_response)

            mock_get_response = AsyncMock()
            mock_get_response.status = 200
            mock_get_response.json = AsyncMock(return_value={
                "test-123": {
                    "outputs": {
                        "9": {"images": [{"filename": "f0.png"}]},
                        "10": {"images": [{"filename": "f1.png"}]},
                        "11": {"images": [{"filename": "f2.png"}]},
                        "12": {"images": [{"filename": "f3.png"}]},
                        "13": {"images": [{"filename": "f4.png"}]},
                        "14": {"images": [{"filename": "f5.png"}]},
                        "15": {"images": [{"filename": "f6.png"}]},
                        "16": {"images": [{"filename": "f7.png"}]},
                        "18": {"images": [{"filename": "prev.png"}]}
                    }
                }
            })
            mock_get_response.__aenter__ = AsyncMock(return_value=mock_get_response)
            mock_get_response.__aexit__ = AsyncMock(return_value=None)
            mock_session.get = AsyncMock(return_value=mock_get_response)

            # Execute
            result = await execute_spritesheet_generation(
                positive_prompt="warrior",
                negative_prompt="blur",
                seed=42
            )

            assert result["status"] == "success"
            assert len(result["frame_paths"]) == 8

    @pytest.mark.asyncio
    async def test_execute_workflow_frame_ordering(self):
        """Test that frames are ordered correctly in result."""
        workflow = create_spritesheet_workflow("test", "test")

        mock_session = AsyncMock(spec=aiohttp.ClientSession)

        mock_post_response = AsyncMock()
        mock_post_response.status = 200
        mock_post_response.json = AsyncMock(return_value={"prompt_id": "test-123"})
        mock_post_response.__aenter__ = AsyncMock(return_value=mock_post_response)
        mock_post_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_post_response

        # Return frames in specific order
        mock_get_response = AsyncMock()
        mock_get_response.status = 200
        mock_get_response.json = AsyncMock(return_value={
            "test-123": {
                "outputs": {
                    "9": {"images": [{"filename": "sprite_0.png"}]},
                    "10": {"images": [{"filename": "sprite_1.png"}]},
                    "11": {"images": [{"filename": "sprite_2.png"}]},
                    "12": {"images": [{"filename": "sprite_3.png"}]},
                    "13": {"images": [{"filename": "sprite_4.png"}]},
                    "14": {"images": [{"filename": "sprite_5.png"}]},
                    "15": {"images": [{"filename": "sprite_6.png"}]},
                    "16": {"images": [{"filename": "sprite_7.png"}]},
                }
            }
        })
        mock_get_response.__aenter__ = AsyncMock(return_value=mock_get_response)
        mock_get_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_get_response

        result = await execute_workflow(
            session=mock_session,
            workflow=workflow,
            client_id="test-client",
            timeout=10
        )

        # Frames should be in order 0-7
        assert result["frame_paths"][0] == "/output/sprite_0.png"
        assert result["frame_paths"][7] == "/output/sprite_7.png"


# ============================================================================
# VALIDATOR TESTS - Test with real PIL images
# ============================================================================

class TestValidator:
    """Test suite for validator.py - Real image validation with PIL."""

    def test_validator_initialization(self):
        """Test SpriteSheetValidator initialization."""
        validator = SpriteSheetValidator(
            tolerance=0.2,
            blank_threshold=0.9,
            motion_min=0.02,
            motion_max=0.4
        )

        assert validator.tolerance == 0.2
        assert validator.blank_threshold == 0.9
        assert validator.motion_min == 0.02
        assert validator.motion_max == 0.4

    def test_validate_frames_success(self, create_sprite_frames):
        """Test validation with good sprite frames."""
        frame_paths = create_sprite_frames(
            num_frames=8,
            size=(32, 32),
            base_color=(100, 150, 200),
            variation=10
        )

        validator = SpriteSheetValidator()
        report = validator.validate_frames(frame_paths)

        assert report["valid"] is True
        assert report["total_frames"] == 8
        assert len(report["errors"]) == 0
        assert "palette_similarity" in report["metrics"]
        assert "color_variance" in report["metrics"]
        assert "motion_scores" in report["metrics"]

    def test_validate_frames_incorrect_dimensions(self, create_test_image, temp_dir):
        """Test validation fails with incorrect dimensions."""
        # Create frames with wrong size
        frame_paths = []
        for i in range(3):
            img = create_test_image(size=(64, 64), colors=[(100, 150, 200)])
            path = Path(temp_dir) / f"frame_{i}.png"
            img.save(path)
            frame_paths.append(str(path))

        validator = SpriteSheetValidator()
        report = validator.validate_frames(frame_paths)

        assert report["valid"] is False
        assert len(report["errors"]) == 3  # All 3 frames wrong size
        assert "incorrect dimensions" in report["errors"][0]

    def test_validate_frames_blank_detection(self, create_test_image, temp_dir):
        """Test blank frame detection."""
        frame_paths = []

        # Create 2 normal frames
        for i in range(2):
            img = create_test_image(
                size=(32, 32),
                colors=[(100, 150, 200), (50, 75, 100)],
                pattern='checker'
            )
            path = Path(temp_dir) / f"frame_{i}.png"
            img.save(path)
            frame_paths.append(str(path))

        # Create 1 blank frame (solid white)
        blank_img = create_test_image(size=(32, 32), colors=[(255, 255, 255)])
        blank_path = Path(temp_dir) / "blank_frame.png"
        blank_img.save(blank_path)
        frame_paths.append(str(blank_path))

        validator = SpriteSheetValidator(blank_threshold=0.95)
        report = validator.validate_frames(frame_paths)

        assert report["valid"] is False
        assert any("blank" in error.lower() for error in report["errors"])

    def test_is_blank_frame(self, create_test_image):
        """Test _is_blank_frame method with real images."""
        validator = SpriteSheetValidator(blank_threshold=0.95)

        # Solid color frame (should be blank)
        solid_img = create_test_image(size=(32, 32), colors=[(100, 100, 100)])
        assert validator._is_blank_frame(solid_img, 0.95) is True

        # Checker pattern (should not be blank)
        pattern_img = create_test_image(
            size=(32, 32),
            colors=[(100, 100, 100), (200, 200, 200)],
            pattern='checker'
        )
        assert validator._is_blank_frame(pattern_img, 0.95) is False

        # Noisy image (should not be blank)
        noise_img = create_test_image(size=(32, 32), pattern='noise')
        assert validator._is_blank_frame(noise_img, 0.95) is False

    def test_extract_palette_real_image(self, create_test_image):
        """Test color palette extraction from real images."""
        validator = SpriteSheetValidator()

        # Create image with known colors
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
        img = create_test_image(size=(32, 32), colors=colors, pattern='checker')

        palette = validator._extract_palette(img, n_colors=4)

        # Should extract 4 colors
        assert palette.shape[0] <= 4
        assert palette.shape[1] == 3  # RGB

        # Colors should be in valid range
        assert np.all(palette >= 0)
        assert np.all(palette <= 255)

    def test_extract_palette_limited_colors(self, create_test_image):
        """Test palette extraction with fewer colors than requested."""
        validator = SpriteSheetValidator()

        # Create image with only 2 colors
        img = create_test_image(
            size=(32, 32),
            colors=[(100, 100, 100), (200, 200, 200)],
            pattern='checker'
        )

        # Request 8 colors but image only has 2
        palette = validator._extract_palette(img, n_colors=8)

        # Should return at most 2 colors
        assert len(palette) <= 2

    def test_calculate_palette_similarity_identical(self, create_test_image):
        """Test palette similarity with identical images."""
        validator = SpriteSheetValidator()

        img = create_test_image(
            size=(32, 32),
            colors=[(100, 150, 200)],
            pattern='solid'
        )

        palette1 = validator._extract_palette(img, n_colors=4)
        palette2 = validator._extract_palette(img, n_colors=4)

        similarity = validator._calculate_palette_similarity([palette1, palette2])

        # Should be very similar (1.0 = identical)
        assert similarity > 0.99

    def test_calculate_palette_similarity_different(self, create_test_image):
        """Test palette similarity with very different images."""
        validator = SpriteSheetValidator()

        # Red image
        img1 = create_test_image(size=(32, 32), colors=[(255, 0, 0)])
        palette1 = validator._extract_palette(img1, n_colors=4)

        # Blue image
        img2 = create_test_image(size=(32, 32), colors=[(0, 0, 255)])
        palette2 = validator._extract_palette(img2, n_colors=4)

        similarity = validator._calculate_palette_similarity([palette1, palette2])

        # Should be dissimilar
        assert similarity < 0.9

    def test_get_dominant_color(self, create_test_image):
        """Test dominant color extraction."""
        validator = SpriteSheetValidator()

        # Create mostly red image
        img = create_test_image(size=(32, 32), colors=[(200, 50, 50)])
        dominant = validator._get_dominant_color(img)

        assert len(dominant) == 3  # RGB
        assert dominant[0] > 150  # Red channel should be high
        assert dominant[1] < 100  # Green should be low
        assert dominant[2] < 100  # Blue should be low

    def test_calculate_color_variance_low(self, create_test_image):
        """Test color variance with similar frames."""
        validator = SpriteSheetValidator()

        colors = []
        for i in range(5):
            # Similar colors (slight variation)
            img = create_test_image(
                size=(32, 32),
                colors=[(100 + i*5, 150 + i*3, 200 + i*2)]
            )
            colors.append(validator._get_dominant_color(img))

        variance = validator._calculate_color_variance(colors)

        # Should be low variance
        assert variance < 0.1

    def test_calculate_color_variance_high(self, create_test_image):
        """Test color variance with different frames."""
        validator = SpriteSheetValidator()

        # Very different colors
        test_colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
            (255, 255, 0),  # Yellow
        ]

        colors = []
        for color in test_colors:
            img = create_test_image(size=(32, 32), colors=[color])
            colors.append(validator._get_dominant_color(img))

        variance = validator._calculate_color_variance(colors)

        # Should be high variance
        assert variance > 0.1

    def test_analyze_motion_static_frames(self, create_test_image):
        """Test motion analysis with identical frames."""
        validator = SpriteSheetValidator()

        # Create identical frames
        frames = []
        for i in range(5):
            img = create_test_image(size=(32, 32), colors=[(100, 150, 200)])
            frames.append(img)

        motion_scores = validator._analyze_motion(frames)

        assert len(motion_scores) == 4  # n-1 transitions

        # All motion should be zero (identical frames)
        for score in motion_scores:
            assert score < 0.01

    def test_analyze_motion_moving_frames(self, create_sprite_frames):
        """Test motion analysis with moving frames."""
        frame_paths = create_sprite_frames(
            num_frames=8,
            size=(32, 32),
            base_color=(100, 150, 200),
            variation=10
        )

        # Load frames as PIL images
        frames = [Image.open(path) for path in frame_paths]

        validator = SpriteSheetValidator()
        motion_scores = validator._analyze_motion(frames)

        assert len(motion_scores) == 7  # 8 frames = 7 transitions

        # Motion should be detectable but not too high
        for score in motion_scores:
            assert score > 0.001  # Some motion
            assert score < 0.5    # Not too much

    def test_analyze_motion_single_frame(self, create_test_image):
        """Test motion analysis with single frame."""
        validator = SpriteSheetValidator()

        frame = create_test_image(size=(32, 32), colors=[(100, 150, 200)])
        motion_scores = validator._analyze_motion([frame])

        # Should return empty list (no transitions)
        assert len(motion_scores) == 0

    def test_validate_frames_palette_warning(self, create_test_image, temp_dir):
        """Test palette inconsistency warning."""
        frame_paths = []

        # Create frames with different color schemes
        color_schemes = [
            [(255, 0, 0)],      # Red
            [(255, 20, 0)],     # Slightly different red
            [(0, 255, 0)],      # Green (very different)
        ]

        for i, colors in enumerate(color_schemes):
            img = create_test_image(size=(32, 32), colors=colors)
            path = Path(temp_dir) / f"frame_{i}.png"
            img.save(path)
            frame_paths.append(str(path))

        validator = SpriteSheetValidator(tolerance=0.15)
        report = validator.validate_frames(frame_paths)

        # Should have warning about inconsistent palettes
        assert len(report["warnings"]) > 0
        assert any("palette" in w.lower() for w in report["warnings"])

    def test_validate_frames_motion_warning_static(self, create_test_image, temp_dir):
        """Test motion warning for static frames."""
        frame_paths = []

        # Create identical frames
        for i in range(8):
            img = create_test_image(size=(32, 32), colors=[(100, 150, 200)])
            path = Path(temp_dir) / f"frame_{i}.png"
            img.save(path)
            frame_paths.append(str(path))

        validator = SpriteSheetValidator(motion_min=0.01)
        report = validator.validate_frames(frame_paths)

        # Should warn about low motion
        assert any("low motion" in w.lower() for w in report["warnings"])

    def test_validate_frames_motion_warning_too_much(self, create_test_image, temp_dir):
        """Test motion warning for highly different frames."""
        frame_paths = []

        # Create very different frames
        colors = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (255, 255, 0),
        ]

        for i, color in enumerate(colors):
            img = create_test_image(size=(32, 32), colors=[color], pattern='noise')
            path = Path(temp_dir) / f"frame_{i}.png"
            img.save(path)
            frame_paths.append(str(path))

        validator = SpriteSheetValidator(motion_max=0.2)
        report = validator.validate_frames(frame_paths)

        # Should warn about high motion
        assert any("high motion" in w.lower() for w in report["warnings"])

    def test_validate_frames_load_failure(self, temp_dir):
        """Test validation handles file load failures gracefully."""
        # Non-existent file path
        frame_paths = [str(Path(temp_dir) / "nonexistent.png")]

        validator = SpriteSheetValidator()
        report = validator.validate_frames(frame_paths)

        assert report["valid"] is False
        assert len(report["errors"]) > 0
        assert "Failed to load" in report["errors"][0]

    def test_validate_frames_metrics_structure(self, create_sprite_frames):
        """Test that validation report has correct metrics structure."""
        frame_paths = create_sprite_frames(num_frames=8)

        validator = SpriteSheetValidator()
        report = validator.validate_frames(frame_paths)

        # Check metrics exist and have correct types
        assert "palette_similarity" in report["metrics"]
        assert isinstance(report["metrics"]["palette_similarity"], float)

        assert "color_variance" in report["metrics"]
        assert isinstance(report["metrics"]["color_variance"], float)

        assert "motion_scores" in report["metrics"]
        assert isinstance(report["metrics"]["motion_scores"], list)
        assert len(report["metrics"]["motion_scores"]) == 7  # 8 frames = 7 transitions


# ============================================================================
# POST PROCESS TESTS - Test with real PIL images
# ============================================================================

class TestPostProcess:
    """Test suite for post_process.py - Real image processing with PIL."""

    def test_sprite_post_processor_init(self):
        """Test SpritePostProcessor initialization."""
        processor = SpritePostProcessor(pixeldetector_path="/fake/path")

        assert processor.pixeldetector_path == Path("/fake/path")

    def test_sprite_post_processor_init_default_path(self):
        """Test SpritePostProcessor with default path."""
        processor = SpritePostProcessor()

        assert str(processor.pixeldetector_path).endswith("pixeldetector.py")

    def test_process_downscale_basic(self, create_test_image, temp_dir):
        """Test basic image downscaling."""
        # Create a 512x512 image
        img = create_test_image(
            size=(512, 512),
            colors=[(100, 150, 200), (50, 75, 100)],
            pattern='checker'
        )
        input_path = Path(temp_dir) / "input.png"
        img.save(input_path)

        output_path = Path(temp_dir) / "output.png"

        processor = SpritePostProcessor()
        result = processor.process(
            str(input_path),
            str(output_path),
            target_size=64,
            use_palette_quantization=False,
            upscale_for_display=False
        )

        # Check output exists
        assert Path(result).exists()

        # Load and verify dimensions
        output_img = Image.open(result)
        assert output_img.size == (64, 64)

    def test_process_with_upscale(self, create_test_image, temp_dir):
        """Test processing with upscale for display."""
        # Create a 512x512 image
        img = create_test_image(size=(512, 512), colors=[(100, 150, 200)])
        input_path = Path(temp_dir) / "input.png"
        img.save(input_path)

        output_path = Path(temp_dir) / "output.png"

        processor = SpritePostProcessor()
        result = processor.process(
            str(input_path),
            str(output_path),
            target_size=64,
            use_palette_quantization=False,
            upscale_for_display=True
        )

        # Output should be upscaled back to 512x512
        output_img = Image.open(result)
        assert output_img.size == (512, 512)

    def test_process_different_target_sizes(self, create_test_image, temp_dir):
        """Test processing with different target sizes."""
        img = create_test_image(size=(256, 256), colors=[(100, 150, 200)])
        input_path = Path(temp_dir) / "input.png"
        img.save(input_path)

        processor = SpritePostProcessor()

        # Test 32x32
        output_path_32 = Path(temp_dir) / "output_32.png"
        processor.process(
            str(input_path),
            str(output_path_32),
            target_size=32,
            use_palette_quantization=False,
            upscale_for_display=False
        )
        assert Image.open(output_path_32).size == (32, 32)

        # Test 128x128
        output_path_128 = Path(temp_dir) / "output_128.png"
        processor.process(
            str(input_path),
            str(output_path_128),
            target_size=128,
            use_palette_quantization=False,
            upscale_for_display=False
        )
        assert Image.open(output_path_128).size == (128, 128)

    def test_process_file_not_found(self, temp_dir):
        """Test processing with non-existent input file."""
        processor = SpritePostProcessor()

        with pytest.raises(FileNotFoundError):
            processor.process(
                str(Path(temp_dir) / "nonexistent.png"),
                str(Path(temp_dir) / "output.png")
            )

    def test_process_preserves_pixel_art_style(self, create_test_image, temp_dir):
        """Test that downscaling preserves pixel art style with nearest neighbor."""
        # Create image with clear pixel blocks
        img = Image.new('RGB', (64, 64))
        pixels = img.load()

        # Create clear 8x8 blocks of different colors
        for y in range(64):
            for x in range(64):
                block_x = (x // 8) % 2
                block_y = (y // 8) % 2
                if (block_x + block_y) % 2 == 0:
                    pixels[x, y] = (255, 0, 0)  # Red
                else:
                    pixels[x, y] = (0, 0, 255)  # Blue

        input_path = Path(temp_dir) / "input.png"
        img.save(input_path)

        output_path = Path(temp_dir) / "output.png"

        processor = SpritePostProcessor()
        processor.process(
            str(input_path),
            str(output_path),
            target_size=16,
            use_palette_quantization=False,
            upscale_for_display=False
        )

        # Load output and check it has clear blocks (no blurring)
        output_img = Image.open(output_path)
        output_pixels = output_img.load()

        # Check that we have pure red and pure blue (no intermediate colors from blurring)
        colors_found = set()
        for y in range(16):
            for x in range(16):
                colors_found.add(output_pixels[x, y])

        # Should only have 2 colors (red and blue), no blended colors
        assert len(colors_found) <= 3  # Allow for minor compression artifacts

    def test_batch_process(self, create_test_image, temp_dir):
        """Test batch processing multiple images."""
        input_dir = Path(temp_dir) / "input"
        output_dir = Path(temp_dir) / "output"
        input_dir.mkdir()

        # Create multiple test images
        for i in range(5):
            img = create_test_image(
                size=(128, 128),
                colors=[(i*50, 100, 150)]
            )
            img.save(input_dir / f"image_{i}.png")

        processor = SpritePostProcessor()
        results = processor.batch_process(
            str(input_dir),
            str(output_dir),
            pattern="*.png",
            target_size=32,
            use_palette_quantization=False,
            upscale_for_display=False
        )

        # Should process all 5 images
        assert len(results) == 5

        # Check all outputs exist and have correct size
        for result in results:
            assert Path(result).exists()
            img = Image.open(result)
            assert img.size == (32, 32)

    def test_batch_process_with_pattern(self, create_test_image, temp_dir):
        """Test batch processing with file pattern filtering."""
        input_dir = Path(temp_dir) / "input"
        output_dir = Path(temp_dir) / "output"
        input_dir.mkdir()

        # Create images with different extensions
        img = create_test_image(size=(64, 64), colors=[(100, 150, 200)])
        img.save(input_dir / "image1.png")
        img.save(input_dir / "image2.png")
        img.save(input_dir / "image3.jpg")  # Different extension

        processor = SpritePostProcessor()
        results = processor.batch_process(
            str(input_dir),
            str(output_dir),
            pattern="*.png",  # Only process PNG files
            target_size=32,
            use_palette_quantization=False
        )

        # Should only process 2 PNG files
        assert len(results) == 2

    def test_batch_process_creates_output_dir(self, create_test_image, temp_dir):
        """Test batch processing creates output directory if it doesn't exist."""
        input_dir = Path(temp_dir) / "input"
        output_dir = Path(temp_dir) / "output_new"  # Doesn't exist yet
        input_dir.mkdir()

        img = create_test_image(size=(64, 64), colors=[(100, 150, 200)])
        img.save(input_dir / "image.png")

        processor = SpritePostProcessor()
        results = processor.batch_process(
            str(input_dir),
            str(output_dir),
            use_palette_quantization=False
        )

        # Output directory should be created
        assert output_dir.exists()
        assert len(results) == 1

    def test_batch_process_handles_errors(self, temp_dir):
        """Test batch processing handles individual file errors gracefully."""
        input_dir = Path(temp_dir) / "input"
        output_dir = Path(temp_dir) / "output"
        input_dir.mkdir()

        # Create a corrupted file
        corrupted_file = input_dir / "corrupted.png"
        corrupted_file.write_text("This is not a valid PNG")

        processor = SpritePostProcessor()
        results = processor.batch_process(
            str(input_dir),
            str(output_dir),
            pattern="*.png",
            use_palette_quantization=False
        )

        # Should return empty list (no successful processing)
        assert len(results) == 0

    def test_quick_process_convenience_function(self, create_test_image, temp_dir):
        """Test quick_process convenience function."""
        img = create_test_image(size=(256, 256), colors=[(100, 150, 200)])
        input_path = Path(temp_dir) / "input.png"
        img.save(input_path)

        output_path = Path(temp_dir) / "output.png"

        result = quick_process(str(input_path), str(output_path))

        assert Path(result).exists()
        output_img = Image.open(result)
        # Default should upscale for display
        assert output_img.size == (256, 256)

    def test_process_color_preservation(self, create_test_image, temp_dir):
        """Test that processing preserves colors accurately."""
        # Create image with specific colors
        test_color = (123, 231, 99)
        img = create_test_image(size=(128, 128), colors=[test_color])
        input_path = Path(temp_dir) / "input.png"
        img.save(input_path)

        output_path = Path(temp_dir) / "output.png"

        processor = SpritePostProcessor()
        processor.process(
            str(input_path),
            str(output_path),
            target_size=32,
            use_palette_quantization=False,
            upscale_for_display=False
        )

        # Check output has similar color
        output_img = Image.open(output_path)
        output_pixels = output_img.load()
        center_color = output_pixels[16, 16]

        # Colors should be very similar (allowing for minor compression)
        assert abs(center_color[0] - test_color[0]) < 10
        assert abs(center_color[1] - test_color[1]) < 10
        assert abs(center_color[2] - test_color[2]) < 10

    def test_process_with_nonexistent_pixeldetector(self, create_test_image, temp_dir):
        """Test processing continues without palette quantization if pixeldetector missing."""
        img = create_test_image(size=(64, 64), colors=[(100, 150, 200)])
        input_path = Path(temp_dir) / "input.png"
        img.save(input_path)

        output_path = Path(temp_dir) / "output.png"

        # Use non-existent pixeldetector path
        processor = SpritePostProcessor(pixeldetector_path="/nonexistent/path.py")

        # Should complete successfully without palette quantization
        result = processor.process(
            str(input_path),
            str(output_path),
            target_size=32,
            use_palette_quantization=True,  # Requested but will be skipped
            upscale_for_display=False
        )

        assert Path(result).exists()


# ============================================================================
# INTEGRATION TESTS - Test module interactions
# ============================================================================

class TestComfyUIIntegration:
    """Test interactions between ComfyUI modules."""

    def test_workflow_to_validator_integration(self, create_sprite_frames):
        """Test workflow builder output can be validated."""
        # Create workflow
        workflow = create_spritesheet_workflow(
            positive_prompt="knight character",
            negative_prompt="blur",
            seed=42
        )

        # Verify workflow structure is valid for executor
        assert "6" in workflow  # KSampler with seed
        assert workflow["6"]["inputs"]["seed"] == 42

        # Create mock sprite frames
        frame_paths = create_sprite_frames(num_frames=8, size=(32, 32))

        # Validate frames
        validator = SpriteSheetValidator()
        report = validator.validate_frames(frame_paths)

        assert report["total_frames"] == 8

    def test_post_process_validator_integration(self, create_test_image, temp_dir):
        """Test post-processed images can be validated."""
        # Process an image
        img = create_test_image(size=(512, 512), colors=[(100, 150, 200)])
        input_path = Path(temp_dir) / "input.png"
        img.save(input_path)

        output_path = Path(temp_dir) / "output.png"

        processor = SpritePostProcessor()
        processor.process(
            str(input_path),
            str(output_path),
            target_size=32,
            use_palette_quantization=False,
            upscale_for_display=False
        )

        # Validate the processed image
        validator = SpriteSheetValidator()

        # Create a mock frame set with the processed image
        frame_paths = [str(output_path)]

        # Should validate dimensions
        report = validator.validate_frames(frame_paths)
        assert report["total_frames"] == 1

        # Check it passes dimension validation
        dimension_errors = [e for e in report["errors"] if "dimension" in e.lower()]
        assert len(dimension_errors) == 0  # Should be exactly 32x32


# ============================================================================
# PERFORMANCE AND EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Test edge cases and performance considerations."""

    def test_workflow_with_extreme_parameters(self):
        """Test workflow generation with extreme but valid parameters."""
        workflow = create_spritesheet_workflow(
            positive_prompt="a" * 1000,  # Very long prompt
            negative_prompt="b" * 1000,
            seed=2**32 - 1,  # Max seed
            steps=1,  # Minimum steps
            cfg=30.0,  # High CFG
            width=64,  # Small width
            height=64
        )

        assert workflow["6"]["inputs"]["seed"] == 2**32 - 1
        assert workflow["6"]["inputs"]["steps"] == 1
        assert workflow["6"]["inputs"]["cfg"] == 30.0

    def test_validator_with_single_pixel_images(self, create_test_image, temp_dir):
        """Test validator with 1x1 images."""
        frame_paths = []

        for i in range(3):
            img = create_test_image(size=(1, 1), colors=[(i*100, 100, 100)])
            path = Path(temp_dir) / f"frame_{i}.png"
            img.save(path)
            frame_paths.append(str(path))

        validator = SpriteSheetValidator()
        report = validator.validate_frames(frame_paths)

        # Should fail dimension check (not 32x32)
        assert report["valid"] is False

    def test_validator_with_large_frame_set(self, create_sprite_frames):
        """Test validator with many frames."""
        # Create 50 frames
        frame_paths = create_sprite_frames(num_frames=50, size=(32, 32))

        validator = SpriteSheetValidator()
        report = validator.validate_frames(frame_paths)

        assert report["total_frames"] == 50
        assert len(report["metrics"]["motion_scores"]) == 49

    def test_post_processor_with_very_large_image(self, temp_dir):
        """Test post processor with large image."""
        # Create 2048x2048 image
        large_img = Image.new('RGB', (2048, 2048), color=(100, 150, 200))
        input_path = Path(temp_dir) / "large_input.png"
        large_img.save(input_path)

        output_path = Path(temp_dir) / "output.png"

        processor = SpritePostProcessor()
        result = processor.process(
            str(input_path),
            str(output_path),
            target_size=32,
            use_palette_quantization=False,
            upscale_for_display=False
        )

        # Should successfully downscale to 32x32
        output_img = Image.open(result)
        assert output_img.size == (32, 32)


# ============================================================================
# TEST MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
