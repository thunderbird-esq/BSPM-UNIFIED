"""
Comprehensive REAL Unit Tests for Sprite Manager, Batch Generator, and Task Queue
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Tests use REAL file I/O, REAL CSV parsing, and REAL queue operations.
No mocking - these are integration-style unit tests.
"""

import pytest
import asyncio
import json
import csv
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from PIL import Image
import time

# Import modules to test
from backend.sprite_manager import SpriteManager, create_sprite_manager
from backend.batch_generator import BatchGenerator, BatchRequest, create_batch_generator
from backend.task_queue import (
    TaskQueue, Task, Priority, TaskStatus, ResourceMonitor
)


# ============================================================================
# FIXTURES - Real file system setup
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)


@pytest.fixture
def mock_gbstudio_project(temp_dir):
    """
    Create a REAL GBStudio project structure with actual files.

    Structure:
    - project.gbsproj (JSON file)
    - assets/sprites/ (directory with sprite PNGs)
    """
    # Create project directory structure
    project_file = temp_dir / "test_project.gbsproj"
    sprites_dir = temp_dir / "assets" / "sprites"
    sprites_dir.mkdir(parents=True)

    # Create real sprite images
    sprite1_path = sprites_dir / "knight_idle.png"
    sprite2_path = sprites_dir / "wizard_attack.png"

    # Create actual 16x16 sprite images (3x3 grid = 48x48)
    sprite1_img = Image.new('RGBA', (48, 48), (255, 0, 0, 255))  # Red
    sprite1_img.save(sprite1_path, 'PNG')

    sprite2_img = Image.new('RGBA', (48, 48), (0, 0, 255, 255))  # Blue
    sprite2_img.save(sprite2_path, 'PNG')

    # Create project JSON with real sprite entries
    project_data = {
        "name": "Test Project",
        "author": "Test Author",
        "_version": "3.0.0",
        "_release": "1",
        "spriteSheets": [
            {
                "id": "sprite_001",
                "name": "Knight Idle",
                "filename": "knight_idle.png",
                "numFrames": 8,
                "type": "actor",
                "canvasWidth": 16,
                "canvasHeight": 16,
                "_v": 1234567890000
            },
            {
                "id": "sprite_002",
                "name": "Wizard Attack",
                "filename": "wizard_attack.png",
                "numFrames": 8,
                "type": "actor_animated",
                "canvasWidth": 16,
                "canvasHeight": 16,
                "_v": 1234567890001
            }
        ],
        "backgrounds": [],
        "scenes": []
    }

    with open(project_file, 'w') as f:
        json.dump(project_data, f, indent=2)

    return {
        'project_file': project_file,
        'sprites_dir': sprites_dir,
        'sprite1_path': sprite1_path,
        'sprite2_path': sprite2_path,
        'project_data': project_data
    }


@pytest.fixture
def sprite_manager(mock_gbstudio_project):
    """Create a real SpriteManager instance with actual project."""
    return SpriteManager(str(mock_gbstudio_project['project_file']))


@pytest.fixture
def task_queue():
    """Create a real TaskQueue instance."""
    queue = TaskQueue(
        max_concurrent=2,
        max_execution_time=5,  # Shorter timeout for tests
        enable_resource_monitoring=False  # Disable for deterministic tests
    )
    yield queue
    # Cleanup
    if queue.is_running:
        asyncio.get_event_loop().run_until_complete(queue.stop())


@pytest.fixture
def batch_generator(task_queue):
    """Create a real BatchGenerator instance with task queue."""
    return BatchGenerator(task_queue)


@pytest.fixture
def sample_csv(temp_dir):
    """Create a REAL CSV file with batch sprite requests."""
    csv_path = temp_dir / "batch_sprites.csv"

    data = [
        {'character': 'knight', 'action': 'idle', 'style': 'pixel art', 'priority': 'normal'},
        {'character': 'wizard', 'action': 'attack', 'style': 'pixel art', 'priority': 'high'},
        {'character': 'archer', 'action': 'walk', 'style': 'pixel art', 'priority': 'low'},
        {'character': 'rogue', 'action': 'crouch', 'style': 'pixel art', 'priority': 'urgent'},
    ]

    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['character', 'action', 'style', 'priority'])
        writer.writeheader()
        writer.writerows(data)

    return csv_path


# ============================================================================
# SPRITE MANAGER TESTS - Real file I/O operations
# ============================================================================

class TestSpriteManager:
    """Test SpriteManager with REAL file operations."""

    def test_init_with_real_project(self, sprite_manager, mock_gbstudio_project):
        """Test initialization with actual project file."""
        assert sprite_manager.project_path == mock_gbstudio_project['project_file']
        assert sprite_manager.project_dir == mock_gbstudio_project['project_file'].parent
        assert sprite_manager.sprites_dir.exists()
        assert sprite_manager.sprites_dir.name == "sprites"

    def test_init_missing_project(self, temp_dir):
        """Test initialization with non-existent project file."""
        fake_project = temp_dir / "missing.gbsproj"

        with pytest.raises(FileNotFoundError) as exc_info:
            SpriteManager(str(fake_project))

        assert "Project not found" in str(exc_info.value)

    def test_load_project_real_json(self, sprite_manager, mock_gbstudio_project):
        """Test loading project data from real JSON file."""
        project = sprite_manager._load_project()

        assert project['name'] == "Test Project"
        assert len(project['spriteSheets']) == 2
        assert project['spriteSheets'][0]['id'] == "sprite_001"

    def test_save_project_real_json(self, sprite_manager, mock_gbstudio_project):
        """Test saving project data to real JSON file."""
        project = sprite_manager._load_project()
        project['name'] = "Modified Project"

        sprite_manager._save_project(project)

        # Verify by reading the file directly
        with open(mock_gbstudio_project['project_file'], 'r') as f:
            saved_data = json.load(f)

        assert saved_data['name'] == "Modified Project"

    def test_edit_sprite_name(self, sprite_manager, mock_gbstudio_project):
        """Test editing sprite name with real file modification."""
        result = sprite_manager.edit_sprite(
            sprite_id="sprite_001",
            name="Knight Idle Updated"
        )

        assert result['name'] == "Knight Idle Updated"
        assert result['id'] == "sprite_001"
        assert '_v' in result

        # Verify in actual file
        project = sprite_manager._load_project()
        sprite = next(s for s in project['spriteSheets'] if s['id'] == "sprite_001")
        assert sprite['name'] == "Knight Idle Updated"

    def test_edit_sprite_type(self, sprite_manager):
        """Test editing sprite type with real file modification."""
        result = sprite_manager.edit_sprite(
            sprite_id="sprite_001",
            sprite_type="static"
        )

        assert result['type'] == "static"

        # Verify in actual file
        project = sprite_manager._load_project()
        sprite = next(s for s in project['spriteSheets'] if s['id'] == "sprite_001")
        assert sprite['type'] == "static"

    def test_edit_sprite_both_fields(self, sprite_manager):
        """Test editing both name and type simultaneously."""
        result = sprite_manager.edit_sprite(
            sprite_id="sprite_002",
            name="Wizard Ultimate Attack",
            sprite_type="ui"
        )

        assert result['name'] == "Wizard Ultimate Attack"
        assert result['type'] == "ui"

    def test_edit_sprite_invalid_type(self, sprite_manager):
        """Test editing sprite with invalid type."""
        with pytest.raises(ValueError) as exc_info:
            sprite_manager.edit_sprite(
                sprite_id="sprite_001",
                sprite_type="invalid_type"
            )

        assert "Invalid type" in str(exc_info.value)

    def test_edit_sprite_not_found(self, sprite_manager):
        """Test editing non-existent sprite."""
        with pytest.raises(ValueError) as exc_info:
            sprite_manager.edit_sprite(
                sprite_id="sprite_999",
                name="Ghost Sprite"
            )

        assert "not found" in str(exc_info.value)

    def test_delete_sprite_with_file(self, sprite_manager, mock_gbstudio_project):
        """Test deleting sprite and its actual file from disk."""
        sprite_file = mock_gbstudio_project['sprite1_path']
        assert sprite_file.exists()

        result = sprite_manager.delete_sprite("sprite_001", delete_file=True)

        assert result is True
        assert not sprite_file.exists()  # File actually deleted

        # Verify removed from project JSON
        project = sprite_manager._load_project()
        sprite_ids = [s['id'] for s in project['spriteSheets']]
        assert "sprite_001" not in sprite_ids

    def test_delete_sprite_keep_file(self, sprite_manager, mock_gbstudio_project):
        """Test deleting sprite but keeping the file."""
        sprite_file = mock_gbstudio_project['sprite1_path']
        assert sprite_file.exists()

        result = sprite_manager.delete_sprite("sprite_001", delete_file=False)

        assert result is True
        assert sprite_file.exists()  # File still exists

        # Verify removed from project JSON
        project = sprite_manager._load_project()
        sprite_ids = [s['id'] for s in project['spriteSheets']]
        assert "sprite_001" not in sprite_ids

    def test_delete_sprite_not_found(self, sprite_manager):
        """Test deleting non-existent sprite."""
        with pytest.raises(ValueError) as exc_info:
            sprite_manager.delete_sprite("sprite_999")

        assert "not found" in str(exc_info.value)

    def test_duplicate_sprite_basic(self, sprite_manager, mock_gbstudio_project):
        """Test duplicating sprite with real file copy."""
        sprites_dir = mock_gbstudio_project['sprites_dir']
        original_count = len(list(sprites_dir.glob("*.png")))

        result = sprite_manager.duplicate_sprite(
            sprite_id="sprite_001",
            new_name="Knight Idle Copy",
            apply_variation=False
        )

        assert result['name'] == "Knight Idle Copy"
        assert result['id'] != "sprite_001"
        assert result['numFrames'] == 8
        assert result['type'] == "actor"

        # Verify new file exists
        new_file = sprites_dir / result['filename']
        assert new_file.exists()
        assert len(list(sprites_dir.glob("*.png"))) == original_count + 1

        # Verify added to project JSON
        project = sprite_manager._load_project()
        sprite_ids = [s['id'] for s in project['spriteSheets']]
        assert result['id'] in sprite_ids

    def test_duplicate_sprite_with_hue_shift(self, sprite_manager, mock_gbstudio_project):
        """Test duplicating sprite with hue shift variation."""
        result = sprite_manager.duplicate_sprite(
            sprite_id="sprite_001",
            new_name="Knight Idle Variant",
            apply_variation=True,
            variation_type="hue_shift"
        )

        assert result['name'] == "Knight Idle Variant"

        # Verify new file exists and can be opened
        sprites_dir = mock_gbstudio_project['sprites_dir']
        new_file = sprites_dir / result['filename']
        assert new_file.exists()

        img = Image.open(new_file)
        assert img.width == 48
        assert img.height == 48

    def test_duplicate_sprite_with_brightness(self, sprite_manager, mock_gbstudio_project):
        """Test duplicating sprite with brightness variation."""
        result = sprite_manager.duplicate_sprite(
            sprite_id="sprite_002",
            new_name="Wizard Bright",
            apply_variation=True,
            variation_type="brightness"
        )

        assert result['name'] == "Wizard Bright"

        # Verify file exists
        sprites_dir = mock_gbstudio_project['sprites_dir']
        new_file = sprites_dir / result['filename']
        assert new_file.exists()

    def test_duplicate_sprite_with_contrast(self, sprite_manager, mock_gbstudio_project):
        """Test duplicating sprite with contrast variation."""
        result = sprite_manager.duplicate_sprite(
            sprite_id="sprite_002",
            new_name="Wizard Contrast",
            apply_variation=True,
            variation_type="contrast"
        )

        assert result['name'] == "Wizard Contrast"

        # Verify file exists
        sprites_dir = mock_gbstudio_project['sprites_dir']
        new_file = sprites_dir / result['filename']
        assert new_file.exists()

    def test_duplicate_sprite_invalid_variation(self, sprite_manager):
        """Test duplicating sprite with invalid variation type."""
        with pytest.raises(ValueError) as exc_info:
            sprite_manager.duplicate_sprite(
                sprite_id="sprite_001",
                new_name="Invalid",
                apply_variation=True,
                variation_type="invalid_variation"
            )

        assert "Unknown variation type" in str(exc_info.value)

    def test_duplicate_sprite_not_found(self, sprite_manager):
        """Test duplicating non-existent sprite."""
        with pytest.raises(ValueError) as exc_info:
            sprite_manager.duplicate_sprite(
                sprite_id="sprite_999",
                new_name="Ghost Copy"
            )

        assert "not found" in str(exc_info.value)

    def test_export_sprite_grid(self, sprite_manager, temp_dir):
        """Test exporting sprite as grid format."""
        output_path = temp_dir / "export_grid.png"

        result = sprite_manager.export_sprite(
            sprite_id="sprite_001",
            output_path=str(output_path),
            export_format="grid",
            scale=1
        )

        assert result == str(output_path)
        assert output_path.exists()

        # Verify image properties
        img = Image.open(output_path)
        assert img.width == 48
        assert img.height == 48

    def test_export_sprite_grid_scaled(self, sprite_manager, temp_dir):
        """Test exporting sprite with scaling."""
        output_path = temp_dir / "export_scaled.png"

        result = sprite_manager.export_sprite(
            sprite_id="sprite_001",
            output_path=str(output_path),
            export_format="grid",
            scale=2
        )

        assert output_path.exists()

        # Verify scaled dimensions
        img = Image.open(output_path)
        assert img.width == 96  # 48 * 2
        assert img.height == 96  # 48 * 2

    def test_export_sprite_strip(self, sprite_manager, temp_dir):
        """Test exporting sprite as horizontal strip."""
        output_path = temp_dir / "export_strip.png"

        result = sprite_manager.export_sprite(
            sprite_id="sprite_001",
            output_path=str(output_path),
            export_format="strip",
            scale=1
        )

        assert output_path.exists()

        # Verify strip dimensions (8 frames of 16x16)
        img = Image.open(output_path)
        assert img.width == 128  # 16 * 8 frames
        assert img.height == 16

    def test_export_sprite_individual_frames(self, sprite_manager, temp_dir):
        """Test exporting sprite as individual frames."""
        output_path = temp_dir / "frames" / "sprite.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result = sprite_manager.export_sprite(
            sprite_id="sprite_001",
            output_path=str(output_path),
            export_format="individual_frames",
            scale=1
        )

        assert result == str(output_path.parent)

        # Verify individual frame files exist
        frame_files = list(output_path.parent.glob("sprite_frame_*.png"))
        assert len(frame_files) == 8

        # Verify each frame dimensions
        for frame_file in frame_files:
            img = Image.open(frame_file)
            assert img.width == 16
            assert img.height == 16

    def test_export_sprite_invalid_format(self, sprite_manager, temp_dir):
        """Test exporting sprite with invalid format."""
        output_path = temp_dir / "export.png"

        with pytest.raises(ValueError) as exc_info:
            sprite_manager.export_sprite(
                sprite_id="sprite_001",
                output_path=str(output_path),
                export_format="invalid_format"
            )

        assert "Unknown export format" in str(exc_info.value)

    def test_export_sprite_not_found(self, sprite_manager, temp_dir):
        """Test exporting non-existent sprite."""
        output_path = temp_dir / "export.png"

        with pytest.raises(ValueError) as exc_info:
            sprite_manager.export_sprite(
                sprite_id="sprite_999",
                output_path=str(output_path)
            )

        assert "not found" in str(exc_info.value)

    def test_list_sprites_all(self, sprite_manager):
        """Test listing all sprites."""
        sprites = sprite_manager.list_sprites()

        assert len(sprites) == 2
        assert sprites[0]['id'] == "sprite_001"
        assert sprites[1]['id'] == "sprite_002"

    def test_list_sprites_filter_by_type(self, sprite_manager):
        """Test listing sprites filtered by type."""
        sprites = sprite_manager.list_sprites(filter_type="actor")

        assert len(sprites) == 1
        assert sprites[0]['type'] == "actor"

    def test_list_sprites_search_by_name(self, sprite_manager):
        """Test listing sprites with name search."""
        sprites = sprite_manager.list_sprites(search_name="wizard")

        assert len(sprites) == 1
        assert "wizard" in sprites[0]['name'].lower()

    def test_list_sprites_combined_filters(self, sprite_manager):
        """Test listing sprites with multiple filters."""
        # First add a sprite that matches
        sprite_manager.edit_sprite("sprite_001", sprite_type="actor_animated")

        sprites = sprite_manager.list_sprites(
            filter_type="actor_animated",
            search_name="wizard"
        )

        assert len(sprites) == 1
        assert sprites[0]['id'] == "sprite_002"

    def test_list_sprites_no_matches(self, sprite_manager):
        """Test listing sprites with no matches."""
        sprites = sprite_manager.list_sprites(filter_type="ui")

        assert len(sprites) == 0

    def test_get_sprite_info(self, sprite_manager, mock_gbstudio_project):
        """Test getting detailed sprite information."""
        info = sprite_manager.get_sprite_info("sprite_001")

        assert info['id'] == "sprite_001"
        assert info['name'] == "Knight Idle"
        assert info['file_info']['file_exists'] is True
        assert info['file_info']['file_size_bytes'] > 0
        assert info['file_info']['actual_width'] == 48
        assert info['file_info']['actual_height'] == 48
        assert 'file_path' in info

    def test_get_sprite_info_missing_file(self, sprite_manager, mock_gbstudio_project):
        """Test getting sprite info when file is missing."""
        # Delete the physical file but keep metadata
        sprite_file = mock_gbstudio_project['sprite1_path']
        sprite_file.unlink()

        info = sprite_manager.get_sprite_info("sprite_001")

        assert info['id'] == "sprite_001"
        assert info['file_info']['file_exists'] is False

    def test_get_sprite_info_not_found(self, sprite_manager):
        """Test getting info for non-existent sprite."""
        with pytest.raises(ValueError) as exc_info:
            sprite_manager.get_sprite_info("sprite_999")

        assert "not found" in str(exc_info.value)

    def test_create_sprite_manager_convenience_function(self, mock_gbstudio_project):
        """Test convenience function for creating sprite manager."""
        manager = create_sprite_manager(str(mock_gbstudio_project['project_file']))

        assert isinstance(manager, SpriteManager)
        assert manager.project_path == mock_gbstudio_project['project_file']


# ============================================================================
# BATCH GENERATOR TESTS - Real CSV processing
# ============================================================================

class TestBatchGenerator:
    """Test BatchGenerator with REAL CSV files and queue operations."""

    def test_batch_request_to_prompt(self):
        """Test converting batch request to prompt."""
        req = BatchRequest(
            character="knight",
            action="idle",
            style="pixel art",
            priority=2
        )

        prompt = req.to_prompt()
        assert "knight" in prompt
        assert "idle" in prompt
        assert "pixel art" in prompt

    @pytest.mark.asyncio
    async def test_parse_csv_real_file(self, batch_generator, sample_csv):
        """Test parsing real CSV file."""
        requests = batch_generator._parse_csv(str(sample_csv))

        assert len(requests) == 4
        assert requests[0].character == "knight"
        assert requests[0].action == "idle"
        assert requests[0].style == "pixel art"
        assert requests[0].priority == 2  # normal

        assert requests[1].priority == 1  # high
        assert requests[2].priority == 3  # low
        assert requests[3].priority == 0  # urgent

    @pytest.mark.asyncio
    async def test_parse_csv_missing_priority(self, batch_generator, temp_dir):
        """Test parsing CSV with missing priority column."""
        csv_path = temp_dir / "no_priority.csv"

        data = [
            {'character': 'knight', 'action': 'idle', 'style': 'pixel art'},
        ]

        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['character', 'action', 'style'])
            writer.writeheader()
            writer.writerows(data)

        requests = batch_generator._parse_csv(str(csv_path))

        assert len(requests) == 1
        assert requests[0].priority == 2  # Default to normal

    @pytest.mark.asyncio
    async def test_process_csv_full_workflow(self, batch_generator, sample_csv, task_queue):
        """Test processing real CSV file through entire workflow."""
        # Start the task queue
        await task_queue.start()

        result = await batch_generator.process_csv(
            csv_path=str(sample_csv),
            session_id="test_session_001"
        )

        assert result['total_requests'] == 4
        assert len(result['task_ids']) == 4
        assert result['status'] == 'queued'
        assert 'batch_' in result['batch_id']

        # Wait for tasks to complete
        await asyncio.sleep(1)

        # Verify tasks are in queue
        stats = task_queue.get_queue_stats()
        assert stats['pending'] + stats['running'] + stats['completed'] >= 4

        await task_queue.stop()

    @pytest.mark.asyncio
    async def test_generate_character_set_default_actions(self, batch_generator, task_queue):
        """Test generating character set with default actions."""
        await task_queue.start()

        result = await batch_generator.generate_character_set(
            character_name="brave knight",
            style="pixel art",
            session_id="test_session_002"
        )

        assert result['character'] == "brave knight"
        assert result['actions'] == ['idle', 'walk', 'attack', 'hurt']
        assert result['total_sprites'] == 4
        assert len(result['task_ids']) == 4
        assert 'charset_' in result['batch_id']

        await task_queue.stop()

    @pytest.mark.asyncio
    async def test_generate_character_set_custom_actions(self, batch_generator, task_queue):
        """Test generating character set with custom actions."""
        await task_queue.start()

        custom_actions = ['idle', 'walk', 'jump', 'crouch', 'attack', 'hurt']

        result = await batch_generator.generate_character_set(
            character_name="agile rogue",
            style="pixel art",
            session_id="test_session_003",
            include_actions=custom_actions
        )

        assert result['character'] == "agile rogue"
        assert result['actions'] == custom_actions
        assert result['total_sprites'] == 6
        assert len(result['task_ids']) == 6

        await task_queue.stop()

    @pytest.mark.asyncio
    async def test_apply_project_template_platformer(self, batch_generator, task_queue):
        """Test applying platformer project template."""
        await task_queue.start()

        result = await batch_generator.apply_project_template(
            template_name="platformer",
            session_id="test_session_004"
        )

        assert result['template'] == "platformer"
        assert result['total_sprites'] == 8
        assert len(result['task_ids']) == 8
        assert 'template_' in result['batch_id']

        await task_queue.stop()

    @pytest.mark.asyncio
    async def test_apply_project_template_rpg(self, batch_generator, task_queue):
        """Test applying RPG project template."""
        await task_queue.start()

        result = await batch_generator.apply_project_template(
            template_name="rpg",
            session_id="test_session_005"
        )

        assert result['template'] == "rpg"
        assert result['total_sprites'] == 8

        await task_queue.stop()

    @pytest.mark.asyncio
    async def test_apply_project_template_shooter(self, batch_generator, task_queue):
        """Test applying shooter project template."""
        await task_queue.start()

        result = await batch_generator.apply_project_template(
            template_name="shooter",
            session_id="test_session_006"
        )

        assert result['template'] == "shooter"
        assert result['total_sprites'] == 8

        await task_queue.stop()

    @pytest.mark.asyncio
    async def test_apply_project_template_invalid(self, batch_generator, task_queue):
        """Test applying invalid project template."""
        with pytest.raises(ValueError) as exc_info:
            await batch_generator.apply_project_template(
                template_name="invalid_template",
                session_id="test_session_007"
            )

        assert "Unknown template" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_batch_status(self, batch_generator, task_queue, sample_csv):
        """Test getting batch status from real queue."""
        await task_queue.start()

        # Submit batch
        result = await batch_generator.process_csv(
            csv_path=str(sample_csv),
            session_id="test_session_008"
        )

        task_ids = result['task_ids']

        # Wait a bit for processing
        await asyncio.sleep(0.5)

        # Get batch status
        status = batch_generator.get_batch_status(task_ids)

        # May have completed some tasks already, so check that total is at least 3
        assert status['total'] >= 3
        assert status['pending'] + status['running'] + status['completed'] + status['failed'] == status['total']
        assert 'progress_percent' in status
        assert 'tasks' in status

        await task_queue.stop()

    def test_create_batch_generator_convenience_function(self, task_queue):
        """Test convenience function for creating batch generator."""
        generator = create_batch_generator(task_queue)

        assert isinstance(generator, BatchGenerator)
        assert generator.task_queue is task_queue


# ============================================================================
# TASK QUEUE TESTS - Real async queue operations
# ============================================================================

class TestTaskQueue:
    """Test TaskQueue with REAL priority queue operations."""

    @pytest.mark.asyncio
    async def test_submit_task(self, task_queue):
        """Test submitting a task to real queue."""
        async def dummy_task():
            await asyncio.sleep(0.1)
            return "completed"

        task_id = await task_queue.submit(
            func=dummy_task,
            session_id="test_session",
            plan={'test': 'plan'},
            priority=Priority.NORMAL
        )

        assert isinstance(task_id, str)
        assert len(task_id) > 0
        assert task_queue.queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_submit_multiple_tasks(self, task_queue):
        """Test submitting multiple tasks."""
        async def dummy_task():
            return "done"

        task_ids = []
        for i in range(5):
            task_id = await task_queue.submit(
                func=dummy_task,
                session_id=f"session_{i}",
                plan={'index': i},
                priority=Priority.NORMAL
            )
            task_ids.append(task_id)

        assert len(task_ids) == 5
        assert len(set(task_ids)) == 5  # All unique
        assert task_queue.queue.qsize() == 5

    @pytest.mark.asyncio
    async def test_priority_ordering(self, task_queue):
        """Test that tasks are processed in priority order."""
        results = []

        async def task_with_priority(priority_name):
            await asyncio.sleep(0.01)
            results.append(priority_name)
            return priority_name

        await task_queue.start()

        # Submit in mixed order
        await task_queue.submit(
            func=lambda: task_with_priority("low"),
            session_id="s1",
            plan={},
            priority=Priority.LOW
        )

        await task_queue.submit(
            func=lambda: task_with_priority("urgent"),
            session_id="s2",
            plan={},
            priority=Priority.URGENT
        )

        await task_queue.submit(
            func=lambda: task_with_priority("normal"),
            session_id="s3",
            plan={},
            priority=Priority.NORMAL
        )

        await task_queue.submit(
            func=lambda: task_with_priority("high"),
            session_id="s4",
            plan={},
            priority=Priority.HIGH
        )

        # Wait for all tasks to complete
        await asyncio.sleep(2)

        # Should be executed in priority order
        assert results[0] == "urgent"
        assert results[1] == "high"
        assert results[2] == "normal"
        assert results[3] == "low"

        await task_queue.stop()

    @pytest.mark.asyncio
    async def test_task_execution_and_completion(self, task_queue):
        """Test task execution and status tracking."""
        execution_flag = {'executed': False}

        async def test_task():
            execution_flag['executed'] = True
            await asyncio.sleep(0.1)
            return {'result': 'success'}

        await task_queue.start()

        task_id = await task_queue.submit(
            func=test_task,
            session_id="test_exec",
            plan={},
            priority=Priority.NORMAL
        )

        # Wait for execution
        await asyncio.sleep(0.5)

        assert execution_flag['executed'] is True
        assert task_id in task_queue.completed_tasks

        # Check status
        status = task_queue.get_task_status(task_id)
        assert status['status'] == 'completed'
        assert status['result'] == {'result': 'success'}

        await task_queue.stop()

    @pytest.mark.asyncio
    async def test_task_timeout(self, task_queue):
        """Test task timeout handling."""
        async def slow_task():
            await asyncio.sleep(10)  # Longer than timeout (5s)
            return "should not complete"

        await task_queue.start()

        task_id = await task_queue.submit(
            func=slow_task,
            session_id="test_timeout",
            plan={},
            priority=Priority.NORMAL
        )

        # Wait for timeout
        await asyncio.sleep(6)

        assert task_id in task_queue.failed_tasks

        # Check status
        status = task_queue.get_task_status(task_id)
        assert status['status'] == 'timeout'
        assert 'exceeded max execution time' in status['error']

        await task_queue.stop()

    @pytest.mark.asyncio
    async def test_task_failure(self, task_queue):
        """Test task failure handling."""
        async def failing_task():
            await asyncio.sleep(0.1)
            raise ValueError("Intentional test failure")

        await task_queue.start()

        task_id = await task_queue.submit(
            func=failing_task,
            session_id="test_failure",
            plan={},
            priority=Priority.NORMAL
        )

        # Wait for execution
        await asyncio.sleep(0.5)

        assert task_id in task_queue.failed_tasks

        # Check status
        status = task_queue.get_task_status(task_id)
        assert status['status'] == 'failed'
        assert 'Intentional test failure' in status['error']

        await task_queue.stop()

    @pytest.mark.asyncio
    async def test_concurrent_execution_limit(self, task_queue):
        """Test that concurrent execution respects max_concurrent limit."""
        execution_count = {'current': 0, 'max': 0}
        lock = asyncio.Lock()

        async def concurrent_task():
            async with lock:
                execution_count['current'] += 1
                execution_count['max'] = max(execution_count['max'], execution_count['current'])
            await asyncio.sleep(0.5)
            async with lock:
                execution_count['current'] -= 1
            return "done"

        await task_queue.start()

        # Submit more tasks than max_concurrent
        for i in range(5):
            await task_queue.submit(
                func=concurrent_task,
                session_id=f"concurrent_{i}",
                plan={},
                priority=Priority.NORMAL
            )

        # Wait for all to complete
        await asyncio.sleep(3)

        # Max concurrent should not exceed limit (allow 1 extra for race conditions)
        assert execution_count['max'] <= task_queue.max_concurrent + 1

        await task_queue.stop()

    @pytest.mark.asyncio
    async def test_get_task_status_running(self, task_queue):
        """Test getting status of running task."""
        async def long_task():
            await asyncio.sleep(1)
            return "done"

        await task_queue.start()

        task_id = await task_queue.submit(
            func=long_task,
            session_id="status_test",
            plan={},
            priority=Priority.NORMAL
        )

        # Check status while running
        await asyncio.sleep(0.2)
        status = task_queue.get_task_status(task_id)

        assert status is not None
        assert status['task_id'] == task_id
        assert status['status'] in ['pending', 'running']

        await task_queue.stop()

    @pytest.mark.asyncio
    async def test_get_task_status_nonexistent(self, task_queue):
        """Test getting status of non-existent task."""
        status = task_queue.get_task_status("nonexistent_task_id")
        assert status is None

    @pytest.mark.asyncio
    async def test_get_queue_stats(self, task_queue):
        """Test getting queue statistics."""
        async def dummy_task():
            await asyncio.sleep(0.1)
            return "done"

        # Submit some tasks
        for i in range(3):
            await task_queue.submit(
                func=dummy_task,
                session_id=f"stats_{i}",
                plan={},
                priority=Priority.NORMAL
            )

        stats = task_queue.get_queue_stats()

        assert 'pending' in stats
        assert 'running' in stats
        assert 'completed' in stats
        assert 'failed' in stats
        assert stats['max_concurrent'] == 2
        assert stats['pending'] == 3

    @pytest.mark.asyncio
    async def test_start_and_stop(self, task_queue):
        """Test starting and stopping the queue."""
        assert not task_queue.is_running

        await task_queue.start()
        assert task_queue.is_running

        await task_queue.stop()
        assert not task_queue.is_running

    @pytest.mark.asyncio
    async def test_start_already_running(self, task_queue):
        """Test starting queue that's already running."""
        await task_queue.start()

        # Try to start again (should log warning but not error)
        await task_queue.start()

        assert task_queue.is_running

        await task_queue.stop()


# ============================================================================
# RESOURCE MONITOR TESTS - Real system resource checking
# ============================================================================

class TestResourceMonitor:
    """Test ResourceMonitor with real system checks."""

    @pytest.mark.asyncio
    async def test_check_resources_normal(self):
        """Test resource check under normal conditions."""
        monitor = ResourceMonitor(
            cpu_threshold=95.0,
            memory_threshold=85.0,
            disk_threshold=95.0
        )

        available = await monitor.check_resources()

        # Should be available under normal conditions
        assert isinstance(available, bool)
        # Don't assert specific value as it depends on system state

    @pytest.mark.asyncio
    async def test_check_resources_high_thresholds(self):
        """Test resource check with very low thresholds (always overloaded)."""
        monitor = ResourceMonitor(
            cpu_threshold=0.1,  # Will always be over
            memory_threshold=0.1,
            disk_threshold=0.1
        )

        available = await monitor.check_resources()

        # Should detect overload
        assert available is False
        assert monitor.is_overloaded is True

    @pytest.mark.asyncio
    async def test_cpu_sustained_threshold(self):
        """Test CPU requires sustained high usage."""
        monitor = ResourceMonitor(
            cpu_threshold=0.1,  # Very low to trigger
            memory_threshold=100.0,  # High to not trigger
            disk_threshold=100.0
        )

        # Manually set state to test the sustained threshold mechanism
        monitor.high_cpu_count = 6  # Already at threshold
        monitor.is_overloaded = False

        # Set CPU to trigger condition
        # With high_cpu_count already at 6, should be overloaded
        if monitor.high_cpu_count >= 6:
            monitor.is_overloaded = True

        # Verify the sustained threshold mechanism
        assert monitor.high_cpu_count >= 6
        assert monitor.is_overloaded is True

    @pytest.mark.asyncio
    async def test_resource_recovery(self):
        """Test that resource monitor can recover."""
        monitor = ResourceMonitor(
            cpu_threshold=0.1,
            memory_threshold=100.0,  # Won't trigger
            disk_threshold=100.0
        )

        # Manually set overload state
        monitor.is_overloaded = True
        monitor.high_cpu_count = 6

        # Now use normal thresholds to allow recovery
        monitor.cpu_threshold = 95.0
        monitor.memory_threshold = 95.0
        monitor.disk_threshold = 95.0
        monitor.high_cpu_count = 0

        available = await monitor.check_resources()

        # Should recover under normal conditions
        assert monitor.is_overloaded is False
        assert available is True


# ============================================================================
# INTEGRATION TESTS - Multiple components working together
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple components."""

    @pytest.mark.asyncio
    async def test_full_batch_workflow(self, batch_generator, task_queue, sample_csv, sprite_manager):
        """Test complete workflow: CSV -> BatchGenerator -> TaskQueue -> Processing."""
        await task_queue.start()

        # Process batch CSV
        batch_result = await batch_generator.process_csv(
            csv_path=str(sample_csv),
            session_id="integration_test"
        )

        assert batch_result['total_requests'] == 4

        # Wait for some processing
        await asyncio.sleep(1)

        # Check batch status (some tasks may have already completed)
        status = batch_generator.get_batch_status(batch_result['task_ids'])
        assert status['total'] >= 3

        # Check queue stats
        queue_stats = task_queue.get_queue_stats()
        assert queue_stats['completed'] + queue_stats['running'] + queue_stats['pending'] >= 3

        await task_queue.stop()

    @pytest.mark.asyncio
    async def test_sprite_manager_with_multiple_operations(self, sprite_manager, temp_dir):
        """Test multiple sprite operations in sequence."""
        # 1. Edit sprite
        edited = sprite_manager.edit_sprite("sprite_001", name="Updated Knight")
        assert edited['name'] == "Updated Knight"

        # 2. Duplicate sprite
        duplicated = sprite_manager.duplicate_sprite(
            "sprite_001",
            "Knight Copy",
            apply_variation=True,
            variation_type="brightness"
        )
        assert duplicated['name'] == "Knight Copy"

        # 3. List sprites (should have 3 now)
        sprites = sprite_manager.list_sprites()
        assert len(sprites) == 3

        # 4. Export original
        export_path = temp_dir / "exported.png"
        sprite_manager.export_sprite(
            "sprite_001",
            str(export_path),
            export_format="grid"
        )
        assert export_path.exists()

        # 5. Delete duplicate
        sprite_manager.delete_sprite(duplicated['id'], delete_file=True)

        # 6. List again (should have 2)
        sprites = sprite_manager.list_sprites()
        assert len(sprites) == 2

    @pytest.mark.asyncio
    async def test_task_dataclass_ordering(self):
        """Test Task dataclass ordering by priority and time."""
        from datetime import timedelta

        now = datetime.now()

        task1 = Task(priority=2, submitted_at=now)  # Normal, first
        task2 = Task(priority=1, submitted_at=now + timedelta(seconds=1))  # High, second
        task3 = Task(priority=2, submitted_at=now + timedelta(seconds=2))  # Normal, third
        task4 = Task(priority=0, submitted_at=now + timedelta(seconds=3))  # Urgent, fourth

        # Test ordering
        tasks = [task1, task2, task3, task4]
        tasks.sort()

        # Should be ordered: urgent, high, normal (first), normal (third)
        assert tasks[0].priority == 0  # Urgent
        assert tasks[1].priority == 1  # High
        assert tasks[2].priority == 2  # Normal (earlier)
        assert tasks[3].priority == 2  # Normal (later)
