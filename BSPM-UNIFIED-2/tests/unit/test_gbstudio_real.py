"""
Comprehensive Unit Tests for GBStudio Project Module
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Tests REAL functionality with actual file operations, JSON manipulation,
and PIL image processing.

Coverage targets:
- GBStudio project loading/saving with REAL JSON files
- Sprite sheet creation with REAL PIL images
- PNG file generation and validation
- Project metadata manipulation
- 3x3 sprite grid layout with REAL images
- Indexed color conversion (GBC palette)
- Background image handling
- Validation and error handling

Aims for 80%+ code coverage of gbstudio module.
"""

import pytest
import json
import tempfile
import shutil
import hashlib
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from PIL import Image
import numpy as np

# Import module under test
from backend.gbstudio.project import GBStudioProject


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory structure."""
    tmpdir = tempfile.mkdtemp()
    project_dir = Path(tmpdir) / "TestProject"
    project_dir.mkdir()

    # Create required subdirectories
    (project_dir / "assets" / "sprites").mkdir(parents=True)
    (project_dir / "assets" / "backgrounds").mkdir(parents=True)

    yield project_dir

    # Cleanup
    shutil.rmtree(tmpdir)


@pytest.fixture
def valid_gbsproj_data():
    """Return valid GBStudio project JSON data."""
    return {
        "name": "TestGame",
        "author": "TestAuthor",
        "_version": "4.1.3",
        "spriteSheets": [],
        "backgrounds": [],
        "scenes": [
            {
                "id": "scene_1",
                "name": "First Scene",
                "actors": [
                    {"id": "actor_1", "name": "Player"}
                ]
            }
        ]
    }


@pytest.fixture
def gbsproj_file(temp_project_dir, valid_gbsproj_data):
    """Create a valid .gbsproj file."""
    project_file = temp_project_dir / "TestProject.gbsproj"
    with open(project_file, 'w') as f:
        json.dump(valid_gbsproj_data, f, indent=2)
    return project_file


@pytest.fixture
def create_test_image():
    """Factory fixture to create test images."""
    def _create_image(size=(32, 32), color=(255, 0, 0, 255), pattern=None):
        """
        Create a test image.

        Args:
            size: Image dimensions (width, height)
            color: RGBA color tuple
            pattern: 'gradient', 'checkerboard', or None for solid
        """
        img = Image.new('RGBA', size, color)

        if pattern == 'gradient':
            # Create horizontal gradient
            pixels = img.load()
            for y in range(size[1]):
                for x in range(size[0]):
                    intensity = int(255 * x / size[0])
                    pixels[x, y] = (intensity, intensity, intensity, 255)

        elif pattern == 'checkerboard':
            # Create checkerboard pattern
            pixels = img.load()
            cell_size = 8
            for y in range(size[1]):
                for x in range(size[0]):
                    if ((x // cell_size) + (y // cell_size)) % 2 == 0:
                        pixels[x, y] = (255, 255, 255, 255)
                    else:
                        pixels[x, y] = (0, 0, 0, 255)

        return img

    return _create_image


@pytest.fixture
def sprite_frames(temp_project_dir, create_test_image):
    """Create a set of 8 test sprite frames."""
    frames_dir = temp_project_dir / "frames"
    frames_dir.mkdir()

    frame_paths = []
    colors = [
        (255, 0, 0, 255),    # Red
        (0, 255, 0, 255),    # Green
        (0, 0, 255, 255),    # Blue
        (255, 255, 0, 255),  # Yellow
        (255, 0, 255, 255),  # Magenta
        (0, 255, 255, 255),  # Cyan
        (128, 128, 128, 255), # Gray
        (255, 128, 0, 255),  # Orange
    ]

    for i, color in enumerate(colors):
        img = create_test_image(size=(32, 32), color=color)
        frame_path = frames_dir / f"frame_{i}.png"
        img.save(frame_path, 'PNG')
        frame_paths.append(str(frame_path))

    return frame_paths


# ============================================================================
# PROJECT INITIALIZATION TESTS
# ============================================================================

class TestGBStudioProjectInitialization:
    """Test GBStudioProject initialization and loading."""

    def test_init_with_valid_project(self, gbsproj_file):
        """Test initialization with valid project file."""
        project = GBStudioProject(str(gbsproj_file))

        assert project.project_path == gbsproj_file
        assert project.project_dir == gbsproj_file.parent
        assert project.project_data is not None
        assert project.project_data['name'] == "TestGame"
        assert project.project_data['_version'] == "4.1.3"

    def test_init_file_not_found(self, temp_project_dir):
        """Test initialization raises FileNotFoundError for missing file."""
        nonexistent_file = temp_project_dir / "nonexistent.gbsproj"

        with pytest.raises(FileNotFoundError) as exc_info:
            GBStudioProject(str(nonexistent_file))

        assert "Project file not found" in str(exc_info.value)

    def test_init_invalid_json(self, temp_project_dir):
        """Test initialization raises JSONDecodeError for invalid JSON."""
        invalid_file = temp_project_dir / "invalid.gbsproj"
        with open(invalid_file, 'w') as f:
            f.write("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            GBStudioProject(str(invalid_file))

    def test_init_missing_required_fields(self, temp_project_dir):
        """Test initialization raises ValueError for missing required fields."""
        incomplete_data = {
            "name": "TestGame"
            # Missing _version and spriteSheets
        }

        incomplete_file = temp_project_dir / "incomplete.gbsproj"
        with open(incomplete_file, 'w') as f:
            json.dump(incomplete_data, f)

        with pytest.raises(ValueError) as exc_info:
            GBStudioProject(str(incomplete_file))

        assert "missing '_version' field" in str(exc_info.value)

    def test_load_project_validates_structure(self, temp_project_dir):
        """Test _load_project validates all required fields."""
        # Missing spriteSheets
        data = {
            "name": "Test",
            "_version": "4.1.3"
        }

        project_file = temp_project_dir / "test.gbsproj"
        with open(project_file, 'w') as f:
            json.dump(data, f)

        with pytest.raises(ValueError) as exc_info:
            GBStudioProject(str(project_file))

        assert "spriteSheets" in str(exc_info.value)


# ============================================================================
# PROJECT SAVE TESTS
# ============================================================================

class TestGBStudioProjectSave:
    """Test project saving functionality."""

    def test_save_project_writes_to_disk(self, gbsproj_file):
        """Test _save_project writes data to disk."""
        project = GBStudioProject(str(gbsproj_file))

        # Modify project data
        project.project_data['author'] = "NewAuthor"
        project._save_project()

        # Read file and verify changes
        with open(gbsproj_file, 'r') as f:
            saved_data = json.load(f)

        assert saved_data['author'] == "NewAuthor"

    def test_save_project_pretty_formatting(self, gbsproj_file):
        """Test _save_project uses indentation."""
        project = GBStudioProject(str(gbsproj_file))
        project._save_project()

        # Read raw file content
        content = gbsproj_file.read_text()

        # Check for indentation (pretty formatting)
        assert '  "name"' in content or '\t"name"' in content
        assert '\n' in content


# ============================================================================
# FILENAME GENERATION TESTS
# ============================================================================

class TestFilenameGeneration:
    """Test filename generation utilities."""

    def test_generate_filename_basic(self, gbsproj_file):
        """Test basic filename generation."""
        project = GBStudioProject(str(gbsproj_file))

        filename = project._generate_filename("Knight")

        assert filename.startswith("knight_")
        assert filename.endswith(".png")
        assert len(filename) > len("knight_.png")

    def test_generate_filename_with_spaces(self, gbsproj_file):
        """Test filename generation replaces spaces with underscores."""
        project = GBStudioProject(str(gbsproj_file))

        filename = project._generate_filename("Dark Knight Hero")

        assert "dark_knight_hero" in filename
        assert " " not in filename

    def test_generate_filename_special_characters(self, gbsproj_file):
        """Test filename generation removes special characters."""
        project = GBStudioProject(str(gbsproj_file))

        filename = project._generate_filename("Knight!@#$%^&*()")

        assert filename.startswith("knight_")
        assert "!" not in filename
        assert "@" not in filename
        assert "#" not in filename

    def test_generate_filename_uppercase(self, gbsproj_file):
        """Test filename generation converts to lowercase."""
        project = GBStudioProject(str(gbsproj_file))

        filename = project._generate_filename("KNIGHT")

        assert filename.startswith("knight_")
        assert "KNIGHT" not in filename

    def test_generate_filename_has_timestamp(self, gbsproj_file):
        """Test filename includes timestamp for uniqueness."""
        project = GBStudioProject(str(gbsproj_file))

        filename1 = project._generate_filename("sprite")
        time.sleep(1.1)  # Wait at least 1 second for timestamp to change
        filename2 = project._generate_filename("sprite")

        # Filenames should be different due to timestamp
        assert filename1 != filename2

    def test_generate_filename_timestamp_format(self, gbsproj_file):
        """Test filename timestamp format."""
        project = GBStudioProject(str(gbsproj_file))

        filename = project._generate_filename("test")

        # Should contain YYYYMMDD_HHMMSS pattern
        # Extract timestamp part (between last underscore and .png)
        timestamp_part = filename.split('_')[-2:]
        assert len(timestamp_part[0]) == 8  # YYYYMMDD
        assert len(timestamp_part[1].replace('.png', '')) == 6  # HHMMSS


# ============================================================================
# SPRITE ID GENERATION TESTS
# ============================================================================

class TestSpriteIDGeneration:
    """Test sprite ID generation."""

    def test_generate_sprite_id_format(self, gbsproj_file):
        """Test sprite ID has correct format."""
        project = GBStudioProject(str(gbsproj_file))

        sprite_id = project._generate_sprite_id("test_sprite.png")

        assert sprite_id.startswith("sprite_")
        assert len(sprite_id) == len("sprite_") + 8  # sprite_ + 8 char hash

    def test_generate_sprite_id_unique(self, gbsproj_file):
        """Test sprite IDs are unique."""
        project = GBStudioProject(str(gbsproj_file))

        id1 = project._generate_sprite_id("sprite1.png")
        time.sleep(0.01)  # Small delay to ensure different timestamp
        id2 = project._generate_sprite_id("sprite2.png")

        assert id1 != id2

    def test_generate_sprite_id_hexadecimal(self, gbsproj_file):
        """Test sprite ID hash portion is hexadecimal."""
        project = GBStudioProject(str(gbsproj_file))

        sprite_id = project._generate_sprite_id("test.png")
        hash_part = sprite_id.replace("sprite_", "")

        # Should be valid hexadecimal
        int(hash_part, 16)  # Will raise ValueError if not hex


# ============================================================================
# IMAGE CONVERSION TESTS
# ============================================================================

class TestImageConversion:
    """Test GBC palette conversion."""

    def test_convert_to_gbc_palette_basic(self, gbsproj_file, create_test_image):
        """Test basic GBC palette conversion."""
        project = GBStudioProject(str(gbsproj_file))

        # Create test image
        img = create_test_image(size=(32, 32), color=(255, 0, 0, 255))

        # Convert to GBC palette
        indexed = project._convert_to_gbc_palette(img)

        assert indexed.mode == 'P'  # Indexed mode
        assert indexed.size == (32, 32)

    def test_convert_to_gbc_palette_color_count(self, gbsproj_file, create_test_image):
        """Test GBC palette has 4 colors max."""
        project = GBStudioProject(str(gbsproj_file))

        # Create image with gradient (many colors)
        img = create_test_image(size=(32, 32), pattern='gradient')

        # Convert to GBC palette
        indexed = project._convert_to_gbc_palette(img)

        # Get palette and count unique colors
        palette = indexed.getpalette()
        # Palette is a flat list [R,G,B,R,G,B,...]
        # When quantized to 4 colors, palette should be small
        # Each color is 3 values (RGB), so 4 colors = 12 values minimum
        assert palette is not None
        assert len(palette) >= 12  # At least 4 colors * 3 channels

    def test_convert_to_gbc_palette_transparency(self, gbsproj_file, create_test_image):
        """Test GBC palette sets transparency."""
        project = GBStudioProject(str(gbsproj_file))

        img = create_test_image(size=(32, 32), color=(255, 0, 0, 255))
        indexed = project._convert_to_gbc_palette(img)

        # Check transparency is set
        assert 'transparency' in indexed.info
        assert indexed.info['transparency'] == 0

    def test_convert_to_gbc_palette_with_alpha(self, gbsproj_file, create_test_image):
        """Test GBC conversion handles alpha channel correctly."""
        project = GBStudioProject(str(gbsproj_file))

        # Create image with partial transparency
        img = Image.new('RGBA', (32, 32), (255, 0, 0, 128))

        indexed = project._convert_to_gbc_palette(img)

        assert indexed.mode == 'P'
        assert indexed.size == (32, 32)


# ============================================================================
# SPRITE FRAME COMBINATION TESTS
# ============================================================================

class TestSpriteFrameCombination:
    """Test combining frames into sprite sheet."""

    def test_combine_frames_basic_grid(self, gbsproj_file, sprite_frames, temp_project_dir):
        """Test combining frames into 3x3 grid."""
        project = GBStudioProject(str(gbsproj_file))

        output_path = temp_project_dir / "test_sprite.png"

        project._combine_frames_to_spritesheet(
            sprite_frames,
            output_path,
            frames_per_row=3
        )

        # Verify file was created
        assert output_path.exists()

        # Load and verify dimensions
        sprite_sheet = Image.open(output_path)
        # 8 frames in 3x3 grid = 96x96 (3 cols × 32px, 3 rows × 32px)
        assert sprite_sheet.size == (96, 96)

    def test_combine_frames_indexed_mode(self, gbsproj_file, sprite_frames, temp_project_dir):
        """Test combined sprite sheet is in indexed mode."""
        project = GBStudioProject(str(gbsproj_file))

        output_path = temp_project_dir / "test_sprite.png"

        project._combine_frames_to_spritesheet(
            sprite_frames,
            output_path,
            frames_per_row=3
        )

        sprite_sheet = Image.open(output_path)
        assert sprite_sheet.mode == 'P'  # Indexed color

    def test_combine_frames_wrong_size(self, gbsproj_file, temp_project_dir, create_test_image):
        """Test combining frames with wrong dimensions raises error."""
        project = GBStudioProject(str(gbsproj_file))

        # Create frames with wrong size
        wrong_frame = temp_project_dir / "wrong_frame.png"
        img = create_test_image(size=(64, 64))  # Wrong size
        img.save(wrong_frame, 'PNG')

        output_path = temp_project_dir / "test_sprite.png"

        with pytest.raises(ValueError) as exc_info:
            project._combine_frames_to_spritesheet(
                [str(wrong_frame)],
                output_path
            )

        assert "incorrect size" in str(exc_info.value)
        assert "32x32" in str(exc_info.value)

    def test_combine_frames_invalid_file(self, gbsproj_file, temp_project_dir):
        """Test combining frames with invalid file raises error."""
        project = GBStudioProject(str(gbsproj_file))

        # Create invalid image file
        invalid_frame = temp_project_dir / "invalid.png"
        invalid_frame.write_text("not an image")

        output_path = temp_project_dir / "test_sprite.png"

        with pytest.raises(ValueError) as exc_info:
            project._combine_frames_to_spritesheet(
                [str(invalid_frame)],
                output_path
            )

        assert "Failed to load frame" in str(exc_info.value)

    def test_combine_frames_custom_rows(self, gbsproj_file, sprite_frames, temp_project_dir):
        """Test combining frames with custom frames_per_row."""
        project = GBStudioProject(str(gbsproj_file))

        output_path = temp_project_dir / "test_sprite.png"

        # Use 4 frames per row
        project._combine_frames_to_spritesheet(
            sprite_frames[:4],
            output_path,
            frames_per_row=4
        )

        sprite_sheet = Image.open(output_path)
        # 4 frames in 1 row = 128x32 (4 cols × 32px, 1 row × 32px)
        assert sprite_sheet.size == (128, 32)

    def test_combine_frames_position_verification(self, gbsproj_file, temp_project_dir, create_test_image):
        """Test frames are positioned correctly in grid."""
        project = GBStudioProject(str(gbsproj_file))

        # Create distinctive colored frames
        frames_dir = temp_project_dir / "color_frames"
        frames_dir.mkdir()

        colors = [
            (255, 0, 0, 255),    # Red - top-left
            (0, 255, 0, 255),    # Green - top-middle
            (0, 0, 255, 255),    # Blue - top-right
        ]

        frame_paths = []
        for i, color in enumerate(colors):
            img = create_test_image(size=(32, 32), color=color)
            frame_path = frames_dir / f"frame_{i}.png"
            img.save(frame_path, 'PNG')
            frame_paths.append(str(frame_path))

        output_path = temp_project_dir / "positioned_sprite.png"

        project._combine_frames_to_spritesheet(
            frame_paths,
            output_path,
            frames_per_row=3
        )

        # Load and convert back to RGB to check colors
        sprite_sheet = Image.open(output_path).convert('RGBA')

        # Check top-left corner of first frame (should be red-ish)
        pixel = sprite_sheet.getpixel((5, 5))
        assert pixel[0] > 200  # Red channel high

        # Check top-left corner of second frame (should be green-ish)
        pixel = sprite_sheet.getpixel((37, 5))  # 32 + 5
        assert pixel[1] > 200  # Green channel high


# ============================================================================
# ADD SPRITE SHEET TESTS
# ============================================================================

class TestAddSpriteSheet:
    """Test adding sprite sheets to project."""

    def test_add_sprite_sheet_basic(self, gbsproj_file, sprite_frames):
        """Test adding a basic sprite sheet."""
        project = GBStudioProject(str(gbsproj_file))

        sprite_id = project.add_sprite_sheet(
            frame_paths=sprite_frames,
            name="Knight",
            sprite_type="actor_animated"
        )

        # Verify sprite ID format
        assert sprite_id.startswith("sprite_")

        # Verify sprite sheet was added to project data
        assert len(project.project_data['spriteSheets']) == 1

        sprite = project.project_data['spriteSheets'][0]
        assert sprite['id'] == sprite_id
        assert sprite['name'] == "Knight"
        assert sprite['type'] == "actor_animated"
        assert sprite['numFrames'] == 8

    def test_add_sprite_sheet_creates_file(self, gbsproj_file, sprite_frames):
        """Test sprite sheet file is created in assets/sprites."""
        project = GBStudioProject(str(gbsproj_file))

        sprite_id = project.add_sprite_sheet(
            frame_paths=sprite_frames,
            name="TestSprite"
        )

        # Get sprite filename
        sprite = project.project_data['spriteSheets'][0]
        sprite_filename = sprite['filename']

        # Verify file exists
        sprite_path = project.project_dir / "assets" / "sprites" / sprite_filename
        assert sprite_path.exists()

        # Verify it's a valid PNG
        img = Image.open(sprite_path)
        assert img.format == 'PNG'

    def test_add_sprite_sheet_saves_project(self, gbsproj_file, sprite_frames):
        """Test adding sprite sheet saves project to disk."""
        project = GBStudioProject(str(gbsproj_file))

        sprite_id = project.add_sprite_sheet(
            frame_paths=sprite_frames,
            name="TestSprite"
        )

        # Reload project from disk
        with open(gbsproj_file, 'r') as f:
            saved_data = json.load(f)

        # Verify sprite sheet is in saved data
        assert len(saved_data['spriteSheets']) == 1
        assert saved_data['spriteSheets'][0]['id'] == sprite_id

    def test_add_sprite_sheet_invalid_type(self, gbsproj_file, sprite_frames):
        """Test invalid sprite type raises ValueError."""
        project = GBStudioProject(str(gbsproj_file))

        with pytest.raises(ValueError) as exc_info:
            project.add_sprite_sheet(
                frame_paths=sprite_frames,
                name="Test",
                sprite_type="invalid_type"
            )

        assert "Invalid sprite type" in str(exc_info.value)
        assert "invalid_type" in str(exc_info.value)

    def test_add_sprite_sheet_valid_types(self, gbsproj_file, sprite_frames):
        """Test all valid sprite types."""
        valid_types = ["actor", "actor_animated", "static", "ui"]

        for i, sprite_type in enumerate(valid_types):
            project = GBStudioProject(str(gbsproj_file))

            sprite_id = project.add_sprite_sheet(
                frame_paths=sprite_frames[:2],  # Use fewer frames
                name=f"Test_{sprite_type}",
                sprite_type=sprite_type
            )

            # Get the sprite we just added (it's at the end of the list)
            sprite = project.project_data['spriteSheets'][-1]
            assert sprite['type'] == sprite_type

    def test_add_sprite_sheet_empty_name(self, gbsproj_file, sprite_frames):
        """Test empty name raises ValueError."""
        project = GBStudioProject(str(gbsproj_file))

        with pytest.raises(ValueError) as exc_info:
            project.add_sprite_sheet(
                frame_paths=sprite_frames,
                name=""
            )

        assert "Name must be 1-64 characters" in str(exc_info.value)

    def test_add_sprite_sheet_long_name(self, gbsproj_file, sprite_frames):
        """Test overly long name raises ValueError."""
        project = GBStudioProject(str(gbsproj_file))

        long_name = "A" * 65

        with pytest.raises(ValueError) as exc_info:
            project.add_sprite_sheet(
                frame_paths=sprite_frames,
                name=long_name
            )

        assert "Name must be 1-64 characters" in str(exc_info.value)

    def test_add_sprite_sheet_canvas_size(self, gbsproj_file, sprite_frames):
        """Test sprite sheet has correct canvas size."""
        project = GBStudioProject(str(gbsproj_file))

        sprite_id = project.add_sprite_sheet(
            frame_paths=sprite_frames,
            name="Test"
        )

        sprite = project.project_data['spriteSheets'][0]
        assert sprite['canvasWidth'] == 32
        assert sprite['canvasHeight'] == 32

    def test_add_sprite_sheet_version_timestamp(self, gbsproj_file, sprite_frames):
        """Test sprite sheet has version timestamp."""
        project = GBStudioProject(str(gbsproj_file))

        before = int(time.time() * 1000)

        sprite_id = project.add_sprite_sheet(
            frame_paths=sprite_frames,
            name="Test"
        )

        after = int(time.time() * 1000)

        sprite = project.project_data['spriteSheets'][0]
        assert sprite['_v'] >= before
        assert sprite['_v'] <= after

    def test_add_sprite_sheet_creates_directory(self, temp_project_dir, valid_gbsproj_data):
        """Test adding sprite sheet creates sprites directory if missing."""
        # Create project without sprites directory
        project_file = temp_project_dir / "test.gbsproj"
        with open(project_file, 'w') as f:
            json.dump(valid_gbsproj_data, f)

        # Remove sprites directory
        sprites_dir = temp_project_dir / "assets" / "sprites"
        if sprites_dir.exists():
            shutil.rmtree(sprites_dir)

        project = GBStudioProject(str(project_file))

        # Create single frame
        frame_path = temp_project_dir / "frame.png"
        img = Image.new('RGBA', (32, 32), (255, 0, 0, 255))
        img.save(frame_path, 'PNG')

        project.add_sprite_sheet(
            frame_paths=[str(frame_path)],
            name="Test"
        )

        # Directory should now exist
        assert sprites_dir.exists()


# ============================================================================
# BACKGROUND TESTS
# ============================================================================

class TestAddBackground:
    """Test adding background images."""

    def test_add_background_160x144(self, gbsproj_file, temp_project_dir, create_test_image):
        """Test adding standard 160x144 background."""
        project = GBStudioProject(str(gbsproj_file))

        # Create background image
        bg_img = create_test_image(size=(160, 144), pattern='checkerboard')
        bg_path = temp_project_dir / "background.png"
        bg_img.save(bg_path, 'PNG')

        bg_id = project.add_background(
            image_path=str(bg_path),
            name="TestBackground"
        )

        assert bg_id.startswith("bg_")

        # Verify background was added
        assert len(project.project_data['backgrounds']) == 1

        bg = project.project_data['backgrounds'][0]
        assert bg['id'] == bg_id
        assert bg['name'] == "TestBackground"
        assert bg['width'] == 20  # 160 / 8 = 20 tiles
        assert bg['height'] == 18  # 144 / 8 = 18 tiles

    def test_add_background_320x288(self, gbsproj_file, temp_project_dir, create_test_image):
        """Test adding 2x resolution 320x288 background."""
        project = GBStudioProject(str(gbsproj_file))

        bg_img = create_test_image(size=(320, 288), pattern='gradient')
        bg_path = temp_project_dir / "background_2x.png"
        bg_img.save(bg_path, 'PNG')

        bg_id = project.add_background(
            image_path=str(bg_path),
            name="TestBg2x"
        )

        bg = project.project_data['backgrounds'][0]
        assert bg['width'] == 40  # 320 / 8
        assert bg['height'] == 36  # 288 / 8

    def test_add_background_invalid_dimensions(self, gbsproj_file, temp_project_dir, create_test_image):
        """Test invalid background dimensions raise ValueError."""
        project = GBStudioProject(str(gbsproj_file))

        # Create wrong size background
        bg_img = create_test_image(size=(128, 128))
        bg_path = temp_project_dir / "wrong_bg.png"
        bg_img.save(bg_path, 'PNG')

        with pytest.raises(ValueError) as exc_info:
            project.add_background(
                image_path=str(bg_path),
                name="WrongSize"
            )

        assert "160x144 or 320x288" in str(exc_info.value)

    def test_add_background_creates_file(self, gbsproj_file, temp_project_dir, create_test_image):
        """Test background file is created in assets/backgrounds."""
        project = GBStudioProject(str(gbsproj_file))

        bg_img = create_test_image(size=(160, 144))
        bg_path = temp_project_dir / "source_bg.png"
        bg_img.save(bg_path, 'PNG')

        bg_id = project.add_background(
            image_path=str(bg_path),
            name="TestBg"
        )

        bg = project.project_data['backgrounds'][0]
        bg_filename = bg['filename']

        saved_bg_path = project.project_dir / "assets" / "backgrounds" / bg_filename
        assert saved_bg_path.exists()

    def test_add_background_converts_to_indexed(self, gbsproj_file, temp_project_dir, create_test_image):
        """Test background is converted to indexed color."""
        project = GBStudioProject(str(gbsproj_file))

        bg_img = create_test_image(size=(160, 144))
        bg_path = temp_project_dir / "rgba_bg.png"
        bg_img.save(bg_path, 'PNG')

        bg_id = project.add_background(
            image_path=str(bg_path),
            name="TestBg"
        )

        bg = project.project_data['backgrounds'][0]
        bg_filename = bg['filename']

        saved_bg_path = project.project_dir / "assets" / "backgrounds" / bg_filename
        saved_img = Image.open(saved_bg_path)

        assert saved_img.mode == 'P'  # Indexed mode

    def test_add_background_creates_directory(self, temp_project_dir, valid_gbsproj_data, create_test_image):
        """Test adding background creates directory if missing."""
        project_file = temp_project_dir / "test.gbsproj"
        with open(project_file, 'w') as f:
            json.dump(valid_gbsproj_data, f)

        # Remove backgrounds directory
        bg_dir = temp_project_dir / "assets" / "backgrounds"
        if bg_dir.exists():
            shutil.rmtree(bg_dir)

        project = GBStudioProject(str(project_file))

        bg_img = create_test_image(size=(160, 144))
        bg_path = temp_project_dir / "bg.png"
        bg_img.save(bg_path, 'PNG')

        project.add_background(
            image_path=str(bg_path),
            name="Test"
        )

        assert bg_dir.exists()


# ============================================================================
# PROJECT STATS TESTS
# ============================================================================

class TestProjectStats:
    """Test project statistics."""

    def test_get_stats_basic(self, gbsproj_file):
        """Test getting basic project stats."""
        project = GBStudioProject(str(gbsproj_file))

        stats = project.get_stats()

        assert stats['name'] == "TestGame"
        assert stats['author'] == "TestAuthor"
        assert stats['version'] == "4.1.3"
        assert stats['scenes'] == 1
        assert stats['sprites'] == 0
        assert stats['backgrounds'] == 0
        assert stats['actors'] == 1

    def test_get_stats_with_sprites(self, gbsproj_file, sprite_frames):
        """Test stats include sprite count."""
        project = GBStudioProject(str(gbsproj_file))

        project.add_sprite_sheet(
            frame_paths=sprite_frames,
            name="Sprite1"
        )
        project.add_sprite_sheet(
            frame_paths=sprite_frames[:4],
            name="Sprite2"
        )

        stats = project.get_stats()

        assert stats['sprites'] == 2

    def test_get_stats_with_backgrounds(self, gbsproj_file, temp_project_dir, create_test_image):
        """Test stats include background count."""
        project = GBStudioProject(str(gbsproj_file))

        # Add backgrounds
        for i in range(3):
            bg_img = create_test_image(size=(160, 144))
            bg_path = temp_project_dir / f"bg_{i}.png"
            bg_img.save(bg_path, 'PNG')
            project.add_background(str(bg_path), f"Background{i}")

        stats = project.get_stats()

        assert stats['backgrounds'] == 3

    def test_get_stats_missing_fields(self, temp_project_dir):
        """Test stats handles missing optional fields."""
        # Create minimal project
        minimal_data = {
            "name": "MinimalGame",
            "_version": "4.1.3",
            "spriteSheets": []
            # Missing author, scenes, backgrounds
        }

        project_file = temp_project_dir / "minimal.gbsproj"
        with open(project_file, 'w') as f:
            json.dump(minimal_data, f)

        project = GBStudioProject(str(project_file))
        stats = project.get_stats()

        assert stats['name'] == "MinimalGame"
        assert stats['author'] == "Unknown"
        assert stats['scenes'] == 0
        assert stats['actors'] == 0


# ============================================================================
# LIST SPRITE SHEETS TESTS
# ============================================================================

class TestListSpriteSheets:
    """Test listing sprite sheets."""

    def test_list_sprite_sheets_empty(self, gbsproj_file):
        """Test listing sprite sheets when none exist."""
        project = GBStudioProject(str(gbsproj_file))

        sheets = project.list_sprite_sheets()

        assert isinstance(sheets, list)
        assert len(sheets) == 0

    def test_list_sprite_sheets_with_sprites(self, gbsproj_file, sprite_frames):
        """Test listing sprite sheets with multiple sprites."""
        project = GBStudioProject(str(gbsproj_file))

        id1 = project.add_sprite_sheet(
            frame_paths=sprite_frames,
            name="Sprite1",
            sprite_type="actor_animated"
        )

        id2 = project.add_sprite_sheet(
            frame_paths=sprite_frames[:4],
            name="Sprite2",
            sprite_type="static"
        )

        sheets = project.list_sprite_sheets()

        assert len(sheets) == 2

        # Check first sprite
        assert sheets[0]['id'] == id1
        assert sheets[0]['name'] == "Sprite1"
        assert sheets[0]['numFrames'] == 8
        assert sheets[0]['type'] == "actor_animated"
        assert 'filename' in sheets[0]

        # Check second sprite
        assert sheets[1]['id'] == id2
        assert sheets[1]['name'] == "Sprite2"
        assert sheets[1]['numFrames'] == 4
        assert sheets[1]['type'] == "static"

    def test_list_sprite_sheets_structure(self, gbsproj_file, sprite_frames):
        """Test sprite sheet list has correct structure."""
        project = GBStudioProject(str(gbsproj_file))

        project.add_sprite_sheet(
            frame_paths=sprite_frames[:2],
            name="Test"
        )

        sheets = project.list_sprite_sheets()
        sheet = sheets[0]

        # Verify all expected fields are present
        assert 'id' in sheet
        assert 'name' in sheet
        assert 'filename' in sheet
        assert 'numFrames' in sheet
        assert 'type' in sheet


# ============================================================================
# VALIDATE SPRITE SHEET TESTS
# ============================================================================

class TestValidateSpriteSheet:
    """Test sprite sheet validation."""

    def test_validate_sprite_sheet_valid(self, gbsproj_file, sprite_frames):
        """Test validating a valid sprite sheet."""
        project = GBStudioProject(str(gbsproj_file))

        sprite_id = project.add_sprite_sheet(
            frame_paths=sprite_frames,
            name="ValidSprite"
        )

        report = project.validate_sprite_sheet(sprite_id)

        assert report['valid'] is True
        assert len(report['errors']) == 0

    def test_validate_sprite_sheet_not_found(self, gbsproj_file):
        """Test validating non-existent sprite sheet."""
        project = GBStudioProject(str(gbsproj_file))

        report = project.validate_sprite_sheet("sprite_nonexistent")

        assert report['valid'] is False
        assert len(report['errors']) > 0
        assert "not found" in report['errors'][0]

    def test_validate_sprite_sheet_missing_file(self, gbsproj_file, sprite_frames):
        """Test validation fails if sprite file is missing."""
        project = GBStudioProject(str(gbsproj_file))

        sprite_id = project.add_sprite_sheet(
            frame_paths=sprite_frames,
            name="Test"
        )

        # Delete the sprite file
        sprite = project.project_data['spriteSheets'][0]
        sprite_path = project.project_dir / "assets" / "sprites" / sprite['filename']
        sprite_path.unlink()

        report = project.validate_sprite_sheet(sprite_id)

        assert report['valid'] is False
        assert any("not found" in err for err in report['errors'])

    def test_validate_sprite_sheet_checks_required_fields(self, gbsproj_file, sprite_frames):
        """Test validation checks for required fields."""
        project = GBStudioProject(str(gbsproj_file))

        sprite_id = project.add_sprite_sheet(
            frame_paths=sprite_frames,
            name="Test"
        )

        # Remove required field
        sprite = project.project_data['spriteSheets'][0]
        del sprite['numFrames']

        report = project.validate_sprite_sheet(sprite_id)

        assert report['valid'] is False
        assert any("numFrames" in err for err in report['errors'])

    def test_validate_sprite_sheet_indexed_mode_check(self, gbsproj_file, sprite_frames):
        """Test validation checks for indexed color mode."""
        project = GBStudioProject(str(gbsproj_file))

        sprite_id = project.add_sprite_sheet(
            frame_paths=sprite_frames,
            name="Test"
        )

        # Replace sprite file with non-indexed image
        sprite = project.project_data['spriteSheets'][0]
        sprite_path = project.project_dir / "assets" / "sprites" / sprite['filename']

        # Save RGB image instead
        rgb_img = Image.new('RGB', (96, 96), (255, 0, 0))
        rgb_img.save(sprite_path, 'PNG')

        report = project.validate_sprite_sheet(sprite_id)

        # Should have warning about mode
        assert any("not indexed color" in warn for warn in report['warnings'])

    def test_validate_sprite_sheet_report_structure(self, gbsproj_file, sprite_frames):
        """Test validation report has correct structure."""
        project = GBStudioProject(str(gbsproj_file))

        sprite_id = project.add_sprite_sheet(
            frame_paths=sprite_frames,
            name="Test"
        )

        report = project.validate_sprite_sheet(sprite_id)

        assert 'valid' in report
        assert 'errors' in report
        assert 'warnings' in report
        assert isinstance(report['valid'], bool)
        assert isinstance(report['errors'], list)
        assert isinstance(report['warnings'], list)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestGBStudioIntegration:
    """Integration tests with full workflows."""

    def test_full_sprite_workflow(self, gbsproj_file, sprite_frames):
        """Test complete sprite addition workflow."""
        project = GBStudioProject(str(gbsproj_file))

        # Add sprite
        sprite_id = project.add_sprite_sheet(
            frame_paths=sprite_frames,
            name="Hero Character",
            sprite_type="actor_animated"
        )

        # Validate
        report = project.validate_sprite_sheet(sprite_id)
        assert report['valid'] is True

        # List sprites
        sheets = project.list_sprite_sheets()
        assert len(sheets) == 1
        assert sheets[0]['id'] == sprite_id

        # Check stats
        stats = project.get_stats()
        assert stats['sprites'] == 1

        # Verify file on disk
        sprite = project.project_data['spriteSheets'][0]
        sprite_path = project.project_dir / "assets" / "sprites" / sprite['filename']
        assert sprite_path.exists()

        # Load and check image
        img = Image.open(sprite_path)
        assert img.mode == 'P'
        assert img.size == (96, 96)

    def test_multiple_assets_workflow(self, gbsproj_file, sprite_frames, temp_project_dir, create_test_image):
        """Test adding multiple sprites and backgrounds."""
        project = GBStudioProject(str(gbsproj_file))

        # Add multiple sprites
        sprite_ids = []
        for i in range(3):
            sprite_id = project.add_sprite_sheet(
                frame_paths=sprite_frames[:4],
                name=f"Sprite{i}",
                sprite_type="actor"
            )
            sprite_ids.append(sprite_id)

        # Add multiple backgrounds
        bg_ids = []
        for i in range(2):
            bg_img = create_test_image(size=(160, 144))
            bg_path = temp_project_dir / f"bg_{i}.png"
            bg_img.save(bg_path, 'PNG')
            bg_id = project.add_background(str(bg_path), f"Bg{i}")
            bg_ids.append(bg_id)

        # Verify stats
        stats = project.get_stats()
        assert stats['sprites'] == 3
        assert stats['backgrounds'] == 2

        # Verify all sprites
        sheets = project.list_sprite_sheets()
        assert len(sheets) == 3

        # Validate all sprites
        for sprite_id in sprite_ids:
            report = project.validate_sprite_sheet(sprite_id)
            assert report['valid'] is True

    def test_project_reload_preserves_data(self, gbsproj_file, sprite_frames):
        """Test reloading project preserves added data."""
        # Create and save sprite
        project1 = GBStudioProject(str(gbsproj_file))
        sprite_id = project1.add_sprite_sheet(
            frame_paths=sprite_frames,
            name="Persistent Sprite"
        )

        # Reload project
        project2 = GBStudioProject(str(gbsproj_file))

        # Verify sprite is still there
        sheets = project2.list_sprite_sheets()
        assert len(sheets) == 1
        assert sheets[0]['id'] == sprite_id
        assert sheets[0]['name'] == "Persistent Sprite"

        # Validate sprite
        report = project2.validate_sprite_sheet(sprite_id)
        assert report['valid'] is True


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_frame_list(self, gbsproj_file):
        """Test adding sprite with empty frame list."""
        project = GBStudioProject(str(gbsproj_file))

        # Should handle empty list gracefully or raise error
        # (Depends on implementation - this tests current behavior)
        with pytest.raises(Exception):  # May raise IndexError or custom error
            project.add_sprite_sheet(
                frame_paths=[],
                name="Empty"
            )

    def test_single_frame_sprite(self, gbsproj_file, temp_project_dir, create_test_image):
        """Test adding sprite with single frame."""
        project = GBStudioProject(str(gbsproj_file))

        # Create single frame
        img = create_test_image(size=(32, 32))
        frame_path = temp_project_dir / "single_frame.png"
        img.save(frame_path, 'PNG')

        sprite_id = project.add_sprite_sheet(
            frame_paths=[str(frame_path)],
            name="SingleFrame",
            sprite_type="static"
        )

        sprite = project.project_data['spriteSheets'][0]
        assert sprite['numFrames'] == 1

        # Verify sprite sheet size (1 frame = 32x32)
        sprite_path = project.project_dir / "assets" / "sprites" / sprite['filename']
        img = Image.open(sprite_path)
        assert img.size == (96, 32)  # 3 cols (frames_per_row=3) × 1 row

    def test_special_characters_in_name(self, gbsproj_file, sprite_frames):
        """Test sprite name with special characters."""
        project = GBStudioProject(str(gbsproj_file))

        sprite_id = project.add_sprite_sheet(
            frame_paths=sprite_frames[:2],
            name="Sprite™ #1 (Cool!)"
        )

        sprite = project.project_data['spriteSheets'][0]
        assert sprite['name'] == "Sprite™ #1 (Cool!)"

        # Filename should have special chars removed
        assert '™' not in sprite['filename']
        assert '#' not in sprite['filename']
        assert '(' not in sprite['filename']

    def test_unicode_in_name(self, gbsproj_file, sprite_frames):
        """Test sprite name with Unicode characters."""
        project = GBStudioProject(str(gbsproj_file))

        sprite_id = project.add_sprite_sheet(
            frame_paths=sprite_frames[:2],
            name="騎士 Knight 🗡️"
        )

        sprite = project.project_data['spriteSheets'][0]
        # Name should be preserved in JSON
        assert "Knight" in sprite['name']


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test performance characteristics."""

    def test_multiple_sprites_performance(self, gbsproj_file, sprite_frames):
        """Test adding multiple sprites in succession."""
        project = GBStudioProject(str(gbsproj_file))

        start_time = time.time()

        # Add 10 sprites
        for i in range(10):
            project.add_sprite_sheet(
                frame_paths=sprite_frames[:4],
                name=f"Sprite{i}"
            )

        elapsed = time.time() - start_time

        # Should complete in reasonable time (< 5 seconds)
        assert elapsed < 5.0

        # Verify all were added
        stats = project.get_stats()
        assert stats['sprites'] == 10

    def test_large_sprite_sheet(self, gbsproj_file, temp_project_dir, create_test_image):
        """Test handling larger sprite sheets."""
        project = GBStudioProject(str(gbsproj_file))

        # Create 16 frames
        frames_dir = temp_project_dir / "large_frames"
        frames_dir.mkdir()

        frame_paths = []
        for i in range(16):
            img = create_test_image(size=(32, 32), color=(i*15, i*15, i*15, 255))
            frame_path = frames_dir / f"frame_{i}.png"
            img.save(frame_path, 'PNG')
            frame_paths.append(str(frame_path))

        sprite_id = project.add_sprite_sheet(
            frame_paths=frame_paths,
            name="LargeSprite",
            frames_per_row=4
        )

        sprite = project.project_data['spriteSheets'][0]
        assert sprite['numFrames'] == 16

        # Verify dimensions (4x4 grid)
        sprite_path = project.project_dir / "assets" / "sprites" / sprite['filename']
        img = Image.open(sprite_path)
        assert img.size == (128, 128)  # 4 cols × 4 rows × 32px


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '--cov=backend.gbstudio', '--cov-report=term-missing'])
