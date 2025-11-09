"""
Shared Test Fixtures and Configuration
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Provides common fixtures for all test modules.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import json
from PIL import Image


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def temp_project_dir(temp_dir):
    """
    Create temporary GBStudio project structure.

    Returns:
        Path to .gbsproj file
    """
    project_dir = temp_dir / "test_project"
    project_dir.mkdir()

    # Create assets directories
    (project_dir / "assets" / "sprites").mkdir(parents=True)
    (project_dir / "assets" / "backgrounds").mkdir(parents=True)

    # Create minimal .gbsproj file
    gbsproj_path = project_dir / "test_project.gbsproj"
    project_data = {
        "name": "Test Project",
        "author": "Test Author",
        "spriteSheets": [],
        "backgrounds": [],
        "scenes": [],
        "settings": {
            "customColorsEnabled": False
        }
    }

    with open(gbsproj_path, 'w') as f:
        json.dump(project_data, f, indent=2)

    return gbsproj_path


@pytest.fixture
def test_sprite_sheet(temp_dir):
    """
    Create a test sprite sheet (3x3 grid of 32x32 frames).

    Returns:
        Path to sprite sheet PNG
    """
    sprite_path = temp_dir / "test_sprite.png"

    # Create 96x96 sprite sheet (3x3 grid of 32x32 frames)
    sprite_sheet = Image.new('RGB', (96, 96), (15, 56, 15))

    # Add some variation to frames
    pixels = sprite_sheet.load()
    for frame_idx in range(8):  # 8 frames
        row = frame_idx // 3
        col = frame_idx % 3

        # Add unique pattern to each frame
        for y in range(32):
            for x in range(32):
                pixel_x = col * 32 + x
                pixel_y = row * 32 + y

                # Simple pattern
                if (x + y + frame_idx) % 2 == 0:
                    pixels[pixel_x, pixel_y] = (48, 98, 48)

    sprite_sheet.save(sprite_path, 'PNG')
    return sprite_path


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response."""
    return {
        'response': json.dumps({
            'response_to_user': 'I will create a knight sprite',
            'needs_approval': True,
            'delegation_plan': [{
                'department': 'Art',
                'task': 'Generate knight sprite',
                'details': {
                    'style': 'pixel art',
                    'frames': 8,
                    'resolution': '32x32'
                }
            }]
        })
    }


@pytest.fixture
def mock_comfyui_response():
    """Mock ComfyUI API responses."""
    return {
        'system_stats': {
            'system': {'os': 'linux'},
            'queue_remaining': 0
        },
        'prompt_submit': {
            'prompt_id': 'test_prompt_123'
        },
        'history': {
            'test_prompt_123': {
                'outputs': {
                    '9': {
                        'images': [{
                            'filename': 'sprite_frame_0_00001.png',
                            'subfolder': '',
                            'type': 'output'
                        }]
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_api_key_file(temp_dir):
    """Create temporary API keys file."""
    keys_file = temp_dir / "api_keys.txt"
    test_keys = [
        "test_key_123456789abcdef",
        "another_valid_key_xyz"
    ]
    with open(keys_file, 'w') as f:
        f.write('\n'.join(test_keys))
    return keys_file


@pytest.fixture
def sample_task_plan():
    """Sample task plan for generation."""
    return [{
        'department': 'Art',
        'task': 'Generate sprite',
        'details': {
            'character': 'knight',
            'style': 'pixel art',
            'frames': 8,
            'resolution': '32x32'
        }
    }]


@pytest.fixture
def sample_workflow():
    """Sample ComfyUI workflow."""
    return {
        "3": {
            "inputs": {
                "seed": 12345,
                "steps": 20,
                "cfg": 8.0,
                "sampler_name": "euler_ancestral",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler"
        },
        "4": {
            "inputs": {
                "ckpt_name": "pixel_art_model.safetensors"
            },
            "class_type": "CheckpointLoaderSimple"
        }
    }


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration between tests."""
    import logging
    # Remove all handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Reset level
    root_logger.setLevel(logging.WARNING)

    yield

    # Cleanup after test
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)


@pytest.fixture
def mock_psutil():
    """Mock psutil for resource monitoring tests."""
    with patch('psutil.cpu_percent') as mock_cpu, \
         patch('psutil.virtual_memory') as mock_mem, \
         patch('psutil.disk_usage') as mock_disk:

        # Default: healthy system
        mock_cpu.return_value = 50.0

        mock_mem_obj = Mock()
        mock_mem_obj.percent = 60.0
        mock_mem.return_value = mock_mem_obj

        mock_disk_obj = Mock()
        mock_disk_obj.percent = 70.0
        mock_disk.return_value = mock_disk_obj

        yield {
            'cpu': mock_cpu,
            'memory': mock_mem,
            'disk': mock_disk
        }


@pytest.fixture
def capture_logs(caplog):
    """Fixture to capture and return log records."""
    import logging
    caplog.set_level(logging.DEBUG)
    return caplog


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "asyncio: marks tests as async"
    )


# Custom assertions
class CustomAssertions:
    """Custom assertion helpers."""

    @staticmethod
    def assert_valid_sprite_sheet(image_path, expected_frames=8):
        """Assert that an image is a valid sprite sheet."""
        img = Image.open(image_path)

        # Check dimensions (3x3 grid of 32x32 = 96x96)
        assert img.width == 96, f"Expected width 96, got {img.width}"
        assert img.height == 96, f"Expected height 96, got {img.height}"

        # Check format
        assert img.format == 'PNG', f"Expected PNG format, got {img.format}"

    @staticmethod
    def assert_valid_json_file(file_path):
        """Assert that a file contains valid JSON."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        assert isinstance(data, (dict, list)), "JSON must be dict or list"
        return data


@pytest.fixture
def assertions():
    """Provide custom assertions."""
    return CustomAssertions()
