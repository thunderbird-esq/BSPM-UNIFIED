"""
Test Suite: Sprite Manager
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Tests for sprite lifecycle operations.
"""

import pytest
import json
from pathlib import Path
from PIL import Image
from backend.sprite_manager import SpriteManager, create_sprite_manager
from tests.mocks import create_mock_sprite_data, create_mock_project_data


class TestSpriteManager:
    """Test SpriteManager class."""

    def test_initialization(self, temp_project_dir):
        """Initialize sprite manager with valid project."""
        manager = SpriteManager(str(temp_project_dir))

        assert manager.project_path.exists()
        assert manager.sprites_dir.exists()

    def test_initialization_missing_project_raises(self, temp_dir):
        """Missing project file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            SpriteManager(str(temp_dir / "nonexistent.gbsproj"))

    def test_edit_sprite_name(self, temp_project_dir):
        """Edit sprite name."""
        # Add sprite to project
        project = json.loads(temp_project_dir.read_text())
        sprite = create_mock_sprite_data('sprite_1', 'Old Name')
        project['spriteSheets'].append(sprite)
        temp_project_dir.write_text(json.dumps(project, indent=2))

        manager = SpriteManager(str(temp_project_dir))
        updated = manager.edit_sprite('sprite_1', name='New Name')

        assert updated['name'] == 'New Name'

        # Verify persisted
        project = json.loads(temp_project_dir.read_text())
        assert project['spriteSheets'][0]['name'] == 'New Name'

    def test_edit_sprite_type(self, temp_project_dir):
        """Edit sprite type."""
        project = json.loads(temp_project_dir.read_text())
        sprite = create_mock_sprite_data('sprite_1', 'Test Sprite')
        sprite['type'] = 'actor'
        project['spriteSheets'].append(sprite)
        temp_project_dir.write_text(json.dumps(project, indent=2))

        manager = SpriteManager(str(temp_project_dir))
        updated = manager.edit_sprite('sprite_1', sprite_type='static')

        assert updated['type'] == 'static'

    def test_edit_sprite_invalid_type_raises(self, temp_project_dir):
        """Invalid sprite type raises ValueError."""
        project = json.loads(temp_project_dir.read_text())
        sprite = create_mock_sprite_data('sprite_1', 'Test')
        project['spriteSheets'].append(sprite)
        temp_project_dir.write_text(json.dumps(project, indent=2))

        manager = SpriteManager(str(temp_project_dir))

        with pytest.raises(ValueError, match="Invalid type"):
            manager.edit_sprite('sprite_1', sprite_type='invalid_type')

    def test_edit_sprite_not_found_raises(self, temp_project_dir):
        """Editing nonexistent sprite raises ValueError."""
        manager = SpriteManager(str(temp_project_dir))

        with pytest.raises(ValueError, match="not found"):
            manager.edit_sprite('nonexistent_id', name='New Name')

    def test_delete_sprite(self, temp_project_dir, test_sprite_sheet):
        """Delete sprite from project."""
        # Setup
        project = json.loads(temp_project_dir.read_text())
        sprite = create_mock_sprite_data('sprite_1', 'Test Sprite')
        sprite['filename'] = 'test_sprite.png'
        project['spriteSheets'].append(sprite)
        temp_project_dir.write_text(json.dumps(project, indent=2))

        # Copy sprite file
        sprites_dir = temp_project_dir.parent / "assets" / "sprites"
        sprite_file = sprites_dir / 'test_sprite.png'
        Image.open(test_sprite_sheet).save(sprite_file)

        manager = SpriteManager(str(temp_project_dir))
        result = manager.delete_sprite('sprite_1', delete_file=True)

        assert result is True

        # Verify removed from project
        project = json.loads(temp_project_dir.read_text())
        assert len(project['spriteSheets']) == 0

        # Verify file deleted
        assert not sprite_file.exists()

    def test_delete_sprite_keep_file(self, temp_project_dir, test_sprite_sheet):
        """Delete sprite but keep file."""
        project = json.loads(temp_project_dir.read_text())
        sprite = create_mock_sprite_data('sprite_1', 'Test')
        sprite['filename'] = 'test_sprite.png'
        project['spriteSheets'].append(sprite)
        temp_project_dir.write_text(json.dumps(project, indent=2))

        sprites_dir = temp_project_dir.parent / "assets" / "sprites"
        sprite_file = sprites_dir / 'test_sprite.png'
        Image.open(test_sprite_sheet).save(sprite_file)

        manager = SpriteManager(str(temp_project_dir))
        manager.delete_sprite('sprite_1', delete_file=False)

        # File should still exist
        assert sprite_file.exists()

    def test_duplicate_sprite(self, temp_project_dir, test_sprite_sheet):
        """Duplicate sprite without variation."""
        project = json.loads(temp_project_dir.read_text())
        sprite = create_mock_sprite_data('sprite_1', 'Original')
        sprite['filename'] = 'original.png'
        project['spriteSheets'].append(sprite)
        temp_project_dir.write_text(json.dumps(project, indent=2))

        sprites_dir = temp_project_dir.parent / "assets" / "sprites"
        original_file = sprites_dir / 'original.png'
        Image.open(test_sprite_sheet).save(original_file)

        manager = SpriteManager(str(temp_project_dir))
        new_sprite = manager.duplicate_sprite(
            'sprite_1',
            'Duplicate Sprite',
            apply_variation=False
        )

        assert new_sprite['name'] == 'Duplicate Sprite'
        assert new_sprite['numFrames'] == sprite['numFrames']
        assert new_sprite['id'] != sprite['id']

        # New file should exist
        new_file = sprites_dir / new_sprite['filename']
        assert new_file.exists()

    def test_list_sprites_empty(self, temp_project_dir):
        """List sprites in empty project."""
        manager = SpriteManager(str(temp_project_dir))

        sprites = manager.list_sprites()

        assert sprites == []

    def test_list_sprites_with_data(self, temp_project_dir):
        """List all sprites in project."""
        project = json.loads(temp_project_dir.read_text())
        project['spriteSheets'] = [
            create_mock_sprite_data('sprite_1', 'Sprite 1'),
            create_mock_sprite_data('sprite_2', 'Sprite 2')
        ]
        temp_project_dir.write_text(json.dumps(project, indent=2))

        manager = SpriteManager(str(temp_project_dir))
        sprites = manager.list_sprites()

        assert len(sprites) == 2

    def test_list_sprites_filter_by_type(self, temp_project_dir):
        """Filter sprites by type."""
        project = json.loads(temp_project_dir.read_text())
        sprite1 = create_mock_sprite_data('sprite_1', 'Actor')
        sprite1['type'] = 'actor'
        sprite2 = create_mock_sprite_data('sprite_2', 'Static')
        sprite2['type'] = 'static'
        project['spriteSheets'] = [sprite1, sprite2]
        temp_project_dir.write_text(json.dumps(project, indent=2))

        manager = SpriteManager(str(temp_project_dir))
        actors = manager.list_sprites(filter_type='actor')

        assert len(actors) == 1
        assert actors[0]['type'] == 'actor'

    def test_list_sprites_search_by_name(self, temp_project_dir):
        """Search sprites by name."""
        project = json.loads(temp_project_dir.read_text())
        project['spriteSheets'] = [
            create_mock_sprite_data('sprite_1', 'Knight'),
            create_mock_sprite_data('sprite_2', 'Wizard')
        ]
        temp_project_dir.write_text(json.dumps(project, indent=2))

        manager = SpriteManager(str(temp_project_dir))
        results = manager.list_sprites(search_name='knight')

        assert len(results) == 1
        assert 'Knight' in results[0]['name']

    def test_get_sprite_info(self, temp_project_dir, test_sprite_sheet):
        """Get detailed sprite information."""
        project = json.loads(temp_project_dir.read_text())
        sprite = create_mock_sprite_data('sprite_1', 'Test Sprite')
        sprite['filename'] = 'test.png'
        project['spriteSheets'].append(sprite)
        temp_project_dir.write_text(json.dumps(project, indent=2))

        sprites_dir = temp_project_dir.parent / "assets" / "sprites"
        sprite_file = sprites_dir / 'test.png'
        Image.open(test_sprite_sheet).save(sprite_file)

        manager = SpriteManager(str(temp_project_dir))
        info = manager.get_sprite_info('sprite_1')

        assert info['id'] == 'sprite_1'
        assert info['name'] == 'Test Sprite'
        assert 'file_info' in info
        assert info['file_info']['file_exists'] is True

    def test_export_sprite_grid_format(self, temp_project_dir, test_sprite_sheet, temp_dir):
        """Export sprite in grid format."""
        project = json.loads(temp_project_dir.read_text())
        sprite = create_mock_sprite_data('sprite_1', 'Test')
        sprite['filename'] = 'test.png'
        project['spriteSheets'].append(sprite)
        temp_project_dir.write_text(json.dumps(project, indent=2))

        sprites_dir = temp_project_dir.parent / "assets" / "sprites"
        Image.open(test_sprite_sheet).save(sprites_dir / 'test.png')

        manager = SpriteManager(str(temp_project_dir))
        output_path = temp_dir / "export.png"

        result = manager.export_sprite(
            'sprite_1',
            str(output_path),
            export_format='grid'
        )

        assert Path(result).exists()
        assert output_path.exists()


class TestSpriteManagerEdgeCases:
    """Test edge cases and error handling."""

    def test_edit_sprite_updates_version(self, temp_project_dir):
        """Editing sprite updates version timestamp."""
        project = json.loads(temp_project_dir.read_text())
        sprite = create_mock_sprite_data('sprite_1', 'Original')
        original_version = sprite['_v']
        project['spriteSheets'].append(sprite)
        temp_project_dir.write_text(json.dumps(project, indent=2))

        manager = SpriteManager(str(temp_project_dir))
        updated = manager.edit_sprite('sprite_1', name='Updated')

        assert updated['_v'] > original_version

    def test_duplicate_missing_source_raises(self, temp_project_dir):
        """Duplicating sprite with missing file raises error."""
        project = json.loads(temp_project_dir.read_text())
        sprite = create_mock_sprite_data('sprite_1', 'Missing')
        sprite['filename'] = 'nonexistent.png'
        project['spriteSheets'].append(sprite)
        temp_project_dir.write_text(json.dumps(project, indent=2))

        manager = SpriteManager(str(temp_project_dir))

        with pytest.raises(FileNotFoundError):
            manager.duplicate_sprite('sprite_1', 'Duplicate')


class TestCreateSpriteManager:
    """Test factory function."""

    def test_create_sprite_manager(self, temp_project_dir):
        """Factory function creates manager."""
        manager = create_sprite_manager(str(temp_project_dir))

        assert isinstance(manager, SpriteManager)


# Run with: pytest tests/test_sprite_manager.py -v
# Run with coverage: pytest tests/test_sprite_manager.py --cov=backend.sprite_manager
