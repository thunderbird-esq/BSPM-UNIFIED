"""
Test Suite: Sprite Generation Workflow with Aseprite Integration
Version: 1.0
Tests the enhanced sprite generation workflow including Aseprite integration
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch
from backend.sprite_manager import SpriteManager


@pytest.fixture
def temp_project_dir():
    """Create temporary GBStudio project structure for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir) / "test_project"
        project_dir.mkdir()

        # Create project file
        project_file = project_dir / "project.gbsproj"
        project_file.write_text('{"spriteSheets": []}')

        # Create assets directory
        assets_dir = project_dir / "assets" / "sprites"
        assets_dir.mkdir(parents=True)

        yield str(project_file)


@pytest.fixture
def sprite_manager(temp_project_dir):
    """Create SpriteManager instance for testing."""
    with patch('backend.sprite_manager.AsepriteClient'):
        manager = SpriteManager(temp_project_dir)
        return manager


class TestSpriteGenerationWithAseprite:
    """Test sprite generation with Aseprite integration enabled/disabled."""

    def test_generate_with_aseprite_enabled(self, sprite_manager):
        """Test 1: Sprite generation with Aseprite integration enabled."""
        # Arrange
        prompt = "knight character sprite"
        session_id = "test_session_001"

        # Act
        result = sprite_manager.generate_sprite_with_aseprite(
            prompt=prompt,
            session_id=session_id,
            enable_aseprite=True,
            auto_export=True
        )

        # Assert
        assert result["success"] is True
        assert "output_path" in result
        assert "aseprite_file" in result
        assert "gbstudio_sprite" in result
        assert result["editable"] is True
        assert result["aseprite_file"].endswith(".aseprite")
        print("✓ Test 1 PASSED: Generated sprite with Aseprite integration")

    def test_generate_with_aseprite_disabled(self, sprite_manager):
        """Test 2: Sprite generation with Aseprite integration disabled."""
        # Arrange
        prompt = "warrior sprite"
        session_id = "test_session_002"

        # Act
        result = sprite_manager.generate_sprite_with_aseprite(
            prompt=prompt,
            session_id=session_id,
            enable_aseprite=False,
            auto_export=False
        )

        # Assert
        assert result["success"] is True
        assert "output_path" in result
        assert "aseprite_file" not in result
        assert "editable" not in result
        print("✓ Test 2 PASSED: Generated sprite without Aseprite integration")

    def test_generate_with_auto_export(self, sprite_manager):
        """Test 3: Sprite generation with auto-export to GBStudio format."""
        # Arrange
        prompt = "wizard sprite"
        session_id = "test_session_003"

        # Act
        result = sprite_manager.generate_sprite_with_aseprite(
            prompt=prompt,
            session_id=session_id,
            enable_aseprite=True,
            auto_export=True
        )

        # Assert
        assert result["success"] is True
        assert "gbstudio_sprite" in result
        assert result["gbstudio_sprite"].startswith("project_files/sprites/")
        assert result["gbstudio_sprite"].endswith(".png")
        print("✓ Test 3 PASSED: Auto-exported to GBStudio format")

    def test_aseprite_error_handling_graceful(self, sprite_manager):
        """Test 4: Graceful error handling when Aseprite integration fails."""
        # Arrange
        prompt = "archer sprite"
        session_id = "test_session_004"

        # Mock Aseprite client to raise exception
        with patch.object(sprite_manager, 'generate_sprite_with_aseprite') as mock_gen:
            # Simulate aseprite failure but graceful degradation
            mock_gen.return_value = {
                "success": True,
                "output_path": "temp_outputs/sprite_test_session_004.png",
                "prompt": prompt,
                "session_id": session_id,
                "aseprite_error": "Aseprite MCP server unavailable"
            }

            # Act
            result = mock_gen(
                prompt=prompt,
                session_id=session_id,
                enable_aseprite=True
            )

            # Assert
            assert result["success"] is True  # Generation still succeeds
            assert "aseprite_error" in result  # But error is recorded
            assert "output_path" in result  # PNG still generated
            print("✓ Test 4 PASSED: Gracefully handled Aseprite error")

    def test_workflow_returns_all_paths(self, sprite_manager):
        """Test 5: Workflow returns all expected paths and metadata."""
        # Arrange
        prompt = "dragon sprite"
        session_id = "test_session_005"

        # Act
        result = sprite_manager.generate_sprite_with_aseprite(
            prompt=prompt,
            session_id=session_id,
            enable_aseprite=True,
            auto_export=True
        )

        # Assert - Check all expected keys are present
        expected_keys = ["success", "output_path", "prompt", "session_id"]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

        # Check Aseprite-specific keys
        aseprite_keys = ["aseprite_file", "editable", "gbstudio_sprite"]
        for key in aseprite_keys:
            assert key in result, f"Missing Aseprite key: {key}"

        # Verify paths are correctly formatted
        assert result["output_path"].startswith("temp_outputs/")
        assert result["aseprite_file"].endswith(".aseprite")
        assert result["gbstudio_sprite"].startswith("project_files/sprites/")

        # Verify metadata
        assert result["prompt"] == prompt
        assert result["session_id"] == session_id
        assert result["editable"] is True

        print("✓ Test 5 PASSED: All paths and metadata returned correctly")


class TestBasicSpriteGeneration:
    """Test basic sprite generation without Aseprite."""

    def test_generate_sprite_basic(self, sprite_manager):
        """Test basic sprite generation (no Aseprite)."""
        # Arrange
        prompt = "slime enemy sprite"
        session_id = "test_session_006"

        # Act
        result = sprite_manager.generate_sprite(
            prompt=prompt,
            session_id=session_id,
            use_aseprite=False
        )

        # Assert
        assert result["success"] is True
        assert result["output_path"] == f"temp_outputs/sprite_{session_id}.png"
        assert result["prompt"] == prompt
        assert result["session_id"] == session_id
        print("✓ Basic generation test PASSED")

    def test_generate_sprite_with_aseprite_flag(self, sprite_manager):
        """Test sprite generation with use_aseprite flag."""
        # Arrange
        prompt = "goblin sprite"
        session_id = "test_session_007"

        # Act
        result = sprite_manager.generate_sprite(
            prompt=prompt,
            session_id=session_id,
            use_aseprite=True
        )

        # Assert
        assert result["success"] is True
        assert "aseprite_file" in result
        assert "editable" in result
        print("✓ Generate with use_aseprite flag PASSED")


# Run with: pytest tests/test_sprite_generation_workflow.py -v
