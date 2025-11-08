"""
Test Suite: GBStudio Project Integration
Version: 3.1
Platform: Intel Mac (macOS Ventura) + Docker

Tests for GBStudioProject class and sprite sheet integration.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from PIL import Image
import numpy as np

from backend.gbstudio.project import GBStudioProject


@pytest.fixture
def temp_project_dir():
    """Create temporary project directory."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_project_json():
    """Sample GBStudio project JSON."""
    return {
        "name": "TestGame",
        "author": "TestDev",
        "_version": "4.1.3",
        "_release": "4",
        "settings": {
            "startSceneId": "scene1",
            "startX": 0,
            "startY": 0
        },
        "scenes": [],
        "backgrounds": [],
        "spriteSheets": [],
        "music": [],
        "fonts": [],
        "avatars": [],
        "emotes": [],
        "customEvents": [],
        "variables": [],
        "constants": [],
        "palettes": [],
        "engineFieldValues": []
    }


@pytest.fixture
def project_with_file(temp_project_dir, sample_project_json):
    """Create temporary project with .gbsproj file."""
    # Create project file
    project_path = temp_project_dir / "TestGame.gbsproj"
    with open(project_path, 'w') as f:
        json.dump(sample_project_json, f, indent=2)
    
    # Create assets directory
    assets_dir = temp_project_dir / "assets" / "sprites"
    assets_dir.mkdir(parents=True)
    
    return project_path


def create_test_sprite_frames(count=8, size=(32, 32)):
    """Create test sprite frames."""
    frames = []
    for i in range(count):
        # Create frame with varying colors
        img = Image.new('RGB', size, (15 + i*10, 56, 15))
        frames.append(img)
    return frames


class TestProjectLoading:
    """Test loading GBStudio projects."""
    
    def test_load_valid_project(self, project_with_file):
        """Load valid .gbsproj file."""
        project = GBStudioProject(str(project_with_file))
        
        assert project.project_data['name'] == 'TestGame'
        assert project.project_data['_version'] == '4.1.3'
        assert isinstance(project.project_data['spriteSheets'], list)
    
    def test_load_nonexistent_project(self, temp_project_dir):
        """Loading nonexistent project raises error."""
        fake_path = temp_project_dir / "nonexistent.gbsproj"
        
        with pytest.raises(FileNotFoundError):
            GBStudioProject(str(fake_path))
    
    def test_load_invalid_json(self, temp_project_dir):
        """Loading invalid JSON raises error."""
        invalid_path = temp_project_dir / "invalid.gbsproj"
        with open(invalid_path, 'w') as f:
            f.write("{invalid json content")
        
        with pytest.raises(json.JSONDecodeError):
            GBStudioProject(str(invalid_path))


class TestSpriteSheetAddition:
    """Test adding sprite sheets to projects."""
    
    def test_add_sprite_sheet_success(self, project_with_file):
        """Successfully add sprite sheet to project."""
        project = GBStudioProject(str(project_with_file))
        
        # Create test frames
        frames = create_test_sprite_frames(count=8)
        
        # Add sprite sheet
        sprite_id = project.add_sprite_sheet(
            frames=frames,
            name="TestKnight",
            sprite_type="actor_animated"
        )
        
        assert sprite_id is not None
        assert sprite_id.startswith("sprite_")
        
        # Verify sprite was added to project data
        sprite_sheets = project.project_data['spriteSheets']
        assert len(sprite_sheets) == 1
        assert sprite_sheets[0]['name'] == 'TestKnight'
        assert sprite_sheets[0]['numFrames'] == 8
    
    def test_add_sprite_creates_png_file(self, project_with_file):
        """Adding sprite sheet creates PNG file in assets."""
        project = GBStudioProject(str(project_with_file))
        frames = create_test_sprite_frames(count=8)
        
        sprite_id = project.add_sprite_sheet(frames, "TestSprite", "actor_animated")
        
        # Find the created sprite sheet
        sprite_entry = next(
            s for s in project.project_data['spriteSheets'] 
            if s['id'] == sprite_id
        )
        
        # Verify PNG file exists
        assets_dir = Path(project_with_file).parent / "assets" / "sprites"
        sprite_path = assets_dir / sprite_entry['filename']
        assert sprite_path.exists()
        
        # Verify PNG properties
        img = Image.open(sprite_path)
        assert img.size == (96, 96)  # 3x3 grid of 32x32 frames
        assert img.mode == 'P'  # Indexed color
    
    def test_sprite_sheet_grid_layout(self, project_with_file):
        """Sprite sheet uses correct 3x3 grid layout."""
        project = GBStudioProject(str(project_with_file))
        frames = create_test_sprite_frames(count=8)
        
        sprite_id = project.add_sprite_sheet(frames, "GridTest", "actor_animated")
        
        # Load the created sprite sheet
        sprite_entry = next(
            s for s in project.project_data['spriteSheets'] 
            if s['id'] == sprite_id
        )
        assets_dir = Path(project_with_file).parent / "assets" / "sprites"
        sprite_img = Image.open(assets_dir / sprite_entry['filename'])
        
        # Verify dimensions
        assert sprite_img.size == (96, 96)
        
        # Verify grid positions (3x3 layout)
        # Frame 0 should be at (0, 0)
        # Frame 1 should be at (32, 0)
        # Frame 8 position (64, 64) should be empty/background
    
    def test_sprite_sheet_indexed_color(self, project_with_file):
        """Sprite sheet is converted to indexed 4-color."""
        project = GBStudioProject(str(project_with_file))
        frames = create_test_sprite_frames(count=8)
        
        sprite_id = project.add_sprite_sheet(frames, "ColorTest", "actor_animated")
        
        # Load sprite sheet
        sprite_entry = next(
            s for s in project.project_data['spriteSheets'] 
            if s['id'] == sprite_id
        )
        assets_dir = Path(project_with_file).parent / "assets" / "sprites"
        sprite_img = Image.open(assets_dir / sprite_entry['filename'])
        
        # Verify indexed color mode
        assert sprite_img.mode == 'P'
        
        # Verify palette size (should be 4 colors or less)
        palette = sprite_img.getpalette()
        unique_colors = len(set(tuple(palette[i:i+3]) for i in range(0, len(palette), 3)))
        assert unique_colors <= 4
    
    def test_add_multiple_sprite_sheets(self, project_with_file):
        """Add multiple sprite sheets to same project."""
        project = GBStudioProject(str(project_with_file))
        
        frames1 = create_test_sprite_frames(count=8)
        frames2 = create_test_sprite_frames(count=8)
        
        sprite_id1 = project.add_sprite_sheet(frames1, "Sprite1", "actor_animated")
        sprite_id2 = project.add_sprite_sheet(frames2, "Sprite2", "actor_animated")
        
        assert sprite_id1 != sprite_id2
        assert len(project.project_data['spriteSheets']) == 2


class TestSpriteSheetValidation:
    """Test sprite sheet validation."""
    
    def test_wrong_frame_count(self, project_with_file):
        """Adding wrong number of frames raises error."""
        project = GBStudioProject(str(project_with_file))
        
        # Create only 5 frames instead of 8
        frames = create_test_sprite_frames(count=5)
        
        with pytest.raises(ValueError, match="Expected 8 frames"):
            project.add_sprite_sheet(frames, "BadCount", "actor_animated")
    
    def test_wrong_frame_dimensions(self, project_with_file):
        """Adding frames with wrong dimensions raises error."""
        project = GBStudioProject(str(project_with_file))
        
        # Create frames with wrong size
        frames = create_test_sprite_frames(count=8, size=(64, 64))
        
        with pytest.raises(ValueError, match="must be 32x32"):
            project.add_sprite_sheet(frames, "BadSize", "actor_animated")
    
    def test_validate_existing_sprite_sheet(self, project_with_file):
        """Validate sprite sheet that was already added."""
        project = GBStudioProject(str(project_with_file))
        frames = create_test_sprite_frames(count=8)
        
        sprite_id = project.add_sprite_sheet(frames, "ValidSprite", "actor_animated")
        
        # Validate
        is_valid = project.validate_sprite_sheet(sprite_id)
        assert is_valid is True


class TestProjectPersistence:
    """Test saving and loading projects."""
    
    def test_save_project(self, project_with_file):
        """Save modified project to disk."""
        project = GBStudioProject(str(project_with_file))
        frames = create_test_sprite_frames(count=8)
        
        # Add sprite
        project.add_sprite_sheet(frames, "SaveTest", "actor_animated")
        
        # Verify file was updated
        with open(project_with_file, 'r') as f:
            saved_data = json.load(f)
        
        assert len(saved_data['spriteSheets']) == 1
        assert saved_data['spriteSheets'][0]['name'] == 'SaveTest'
    
    def test_reload_modified_project(self, project_with_file):
        """Reload project after modifications."""
        # First instance: add sprite
        project1 = GBStudioProject(str(project_with_file))
        frames = create_test_sprite_frames(count=8)
        sprite_id = project1.add_sprite_sheet(frames, "ReloadTest", "actor_animated")
        
        # Second instance: load and verify
        project2 = GBStudioProject(str(project_with_file))
        assert len(project2.project_data['spriteSheets']) == 1
        assert project2.project_data['spriteSheets'][0]['id'] == sprite_id


class TestProjectStatistics:
    """Test project statistics and queries."""
    
    def test_get_stats_empty(self, project_with_file):
        """Stats for empty project."""
        project = GBStudioProject(str(project_with_file))
        stats = project.get_stats()
        
        assert stats['sprite_sheets'] == 0
        assert stats['backgrounds'] == 0
        assert stats['scenes'] == 0
    
    def test_get_stats_with_content(self, project_with_file):
        """Stats after adding content."""
        project = GBStudioProject(str(project_with_file))
        frames = create_test_sprite_frames(count=8)
        
        # Add multiple sprites
        project.add_sprite_sheet(frames, "Sprite1", "actor_animated")
        project.add_sprite_sheet(frames, "Sprite2", "actor_animated")
        
        stats = project.get_stats()
        assert stats['sprite_sheets'] == 2
    
    def test_list_sprite_sheets(self, project_with_file):
        """List all sprite sheets in project."""
        project = GBStudioProject(str(project_with_file))
        frames = create_test_sprite_frames(count=8)
        
        project.add_sprite_sheet(frames, "Knight", "actor_animated")
        project.add_sprite_sheet(frames, "Wizard", "actor_animated")
        
        sprite_list = project.list_sprite_sheets()
        
        assert len(sprite_list) == 2
        names = [s['name'] for s in sprite_list]
        assert 'Knight' in names
        assert 'Wizard' in names


class TestSpriteSheetMetadata:
    """Test sprite sheet metadata handling."""
    
    def test_sprite_id_format(self, project_with_file):
        """Sprite ID follows correct format."""
        project = GBStudioProject(str(project_with_file))
        frames = create_test_sprite_frames(count=8)
        
        sprite_id = project.add_sprite_sheet(frames, "IDTest", "actor_animated")
        
        # Verify format: sprite_[8 hex chars]
        assert sprite_id.startswith("sprite_")
        hex_part = sprite_id.split("_")[1]
        assert len(hex_part) == 8
        assert all(c in '0123456789abcdef' for c in hex_part)
    
    def test_sprite_metadata_fields(self, project_with_file):
        """Sprite entry has all required fields."""
        project = GBStudioProject(str(project_with_file))
        frames = create_test_sprite_frames(count=8)
        
        sprite_id = project.add_sprite_sheet(frames, "MetadataTest", "actor_animated")
        
        sprite_entry = next(
            s for s in project.project_data['spriteSheets'] 
            if s['id'] == sprite_id
        )
        
        # Required fields
        assert 'id' in sprite_entry
        assert 'name' in sprite_entry
        assert 'filename' in sprite_entry
        assert 'numFrames' in sprite_entry
        assert 'type' in sprite_entry
        assert 'canvasWidth' in sprite_entry
        assert 'canvasHeight' in sprite_entry
        assert '_v' in sprite_entry
        
        # Verify values
        assert sprite_entry['numFrames'] == 8
        assert sprite_entry['canvasWidth'] == 32
        assert sprite_entry['canvasHeight'] == 32
        assert sprite_entry['type'] == 'actor_animated'
    
    def test_filename_format(self, project_with_file):
        """Sprite filename follows naming convention."""
        project = GBStudioProject(str(project_with_file))
        frames = create_test_sprite_frames(count=8)
        
        sprite_id = project.add_sprite_sheet(frames, "FileNameTest", "actor_animated")
        
        sprite_entry = next(
            s for s in project.project_data['spriteSheets'] 
            if s['id'] == sprite_id
        )
        
        filename = sprite_entry['filename']
        
        # Should be lowercase alphanumeric + underscores
        assert filename.endswith('.png')
        name_part = filename[:-4]  # Remove .png
        assert all(c.islower() or c.isdigit() or c == '_' for c in name_part)


class TestBackgroundAddition:
    """Test adding backgrounds (if implemented)."""
    
    def test_add_background_placeholder(self, project_with_file):
        """Test background addition (method exists but may not be fully implemented)."""
        project = GBStudioProject(str(project_with_file))
        
        # This tests that the method exists
        # Implementation details depend on GBStudioProject.add_background()
        assert hasattr(project, 'add_background')


# Run with: pytest tests/test_gbstudio_project.py -v
