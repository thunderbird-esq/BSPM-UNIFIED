"""
Test Suite: Sprite Sheet Validation
Version: 3.1
Platform: Intel Mac (macOS Ventura) + Docker

Tests for SpriteSheetValidator functionality.
"""

import pytest
import numpy as np
from PIL import Image
from pathlib import Path
import tempfile
import shutil

from backend.comfyui.validator import SpriteSheetValidator


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory for test frames."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def validator():
    """Create SpriteSheetValidator instance."""
    return SpriteSheetValidator()


def create_test_frame(
    size=(32, 32),
    colors=None,
    mode='RGB'
):
    """
    Create test frame with specified properties.
    
    Args:
        size: (width, height) tuple
        colors: List of RGB tuples to use (if None, uses GB palette)
        mode: PIL image mode
    
    Returns:
        PIL Image
    """
    if colors is None:
        # Game Boy Color palette
        colors = [
            (15, 56, 15),    # Dark green
            (48, 98, 48),    # Medium green
            (139, 172, 15),  # Light green
            (155, 188, 15)   # Lightest green
        ]
    
    img = Image.new(mode, size, colors[0])
    pixels = img.load()
    
    # Create simple pattern with all colors
    for y in range(size[1]):
        for x in range(size[0]):
            color_idx = (x + y) % len(colors)
            pixels[x, y] = colors[color_idx]
    
    return img


def create_blank_frame(size=(32, 32), color=(15, 56, 15)):
    """Create blank frame (single color)."""
    return Image.new('RGB', size, color)


def create_different_character_frame(size=(32, 32)):
    """Create frame with completely different color palette (red character)."""
    red_colors = [
        (120, 10, 10),   # Dark red
        (180, 30, 30),   # Medium red
        (80, 5, 5),      # Darker red
        (255, 100, 100)  # Light red
    ]
    
    return create_test_frame(size=size, colors=red_colors)


class TestFrameDimensions:
    """Test frame dimension validation."""
    
    def test_correct_dimensions(self, validator, temp_output_dir):
        """PASS: All frames are 32x32."""
        # Create 8 valid frames
        for i in range(8):
            frame = create_test_frame(size=(32, 32))
            frame.save(temp_output_dir / f"sprite_frame_{i}_00001.png")
        
        # Validate
        result = validator.validate_frames(temp_output_dir, num_frames=8)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
        assert result['metrics']['frame_count'] == 8
    
    def test_wrong_dimensions(self, validator, temp_output_dir):
        """FAIL: Frame has wrong dimensions (64x64 instead of 32x32)."""
        # Create frames with one wrong size
        for i in range(8):
            if i == 3:
                frame = create_test_frame(size=(64, 64))  # Wrong size
            else:
                frame = create_test_frame(size=(32, 32))
            frame.save(temp_output_dir / f"sprite_frame_{i}_00001.png")
        
        # Validate
        result = validator.validate_frames(temp_output_dir, num_frames=8)
        
        assert result['valid'] is False
        assert any('incorrect dimensions' in err.lower() for err in result['errors'])
        assert '(64, 64)' in result['errors'][0]
        assert '(32, 32)' in result['errors'][0]
    
    def test_wrong_aspect_ratio(self, validator, temp_output_dir):
        """FAIL: Frame has wrong aspect ratio (32x64 instead of 32x32)."""
        # Create frames with one wrong aspect ratio
        for i in range(8):
            if i == 5:
                frame = create_test_frame(size=(32, 64))  # Wrong aspect
            else:
                frame = create_test_frame(size=(32, 32))
            frame.save(temp_output_dir / f"sprite_frame_{i}_00001.png")
        
        # Validate
        result = validator.validate_frames(temp_output_dir, num_frames=8)
        
        assert result['valid'] is False
        assert any('incorrect dimensions' in err.lower() for err in result['errors'])


class TestColorPalette:
    """Test color palette consistency validation."""
    
    def test_consistent_palette(self, validator, temp_output_dir):
        """PASS: All frames use similar color palette (>85% similarity)."""
        # Create 8 frames with consistent GB palette
        for i in range(8):
            frame = create_test_frame(size=(32, 32))
            frame.save(temp_output_dir / f"sprite_frame_{i}_00001.png")
        
        # Validate
        result = validator.validate_frames(temp_output_dir, num_frames=8)
        
        assert result['valid'] is True
        assert result['metrics']['palette_similarity'] >= 0.85
        assert len(result['warnings']) == 0
    
    def test_inconsistent_palette(self, validator, temp_output_dir):
        """WARN: Frames have inconsistent palettes (<85% similarity)."""
        # Create 7 knight frames + 1 completely different character
        for i in range(8):
            if i == 7:
                frame = create_different_character_frame()  # Red character
            else:
                frame = create_test_frame(size=(32, 32))    # Green knight
            frame.save(temp_output_dir / f"sprite_frame_{i}_00001.png")
        
        # Validate
        result = validator.validate_frames(temp_output_dir, num_frames=8)
        
        # Should still be "valid" but with warning
        assert result['valid'] is True
        assert result['metrics']['palette_similarity'] < 0.85
        assert len(result['warnings']) > 0
        assert any('inconsistent color palette' in warn.lower() for warn in result['warnings'])
    
    def test_palette_extraction(self, validator):
        """Test KMeans palette extraction accuracy."""
        # Create frame with known 4-color palette
        colors = [
            (15, 56, 15),
            (48, 98, 48),
            (139, 172, 15),
            (155, 188, 15)
        ]
        frame = create_test_frame(size=(32, 32), colors=colors)
        
        # Extract palette
        extracted = validator._extract_palette(frame, n_colors=4)
        
        assert len(extracted) == 4
        
        # Verify extracted colors are close to originals
        for orig_color in colors:
            distances = [np.linalg.norm(np.array(orig_color) - extracted_color) 
                        for extracted_color in extracted]
            min_distance = min(distances)
            assert min_distance < 30  # Allow some clustering variance


class TestBlankFrameDetection:
    """Test blank/single-color frame detection."""
    
    def test_no_blank_frames(self, validator, temp_output_dir):
        """PASS: No blank frames detected."""
        # Create 8 valid frames with content
        for i in range(8):
            frame = create_test_frame(size=(32, 32))
            frame.save(temp_output_dir / f"sprite_frame_{i}_00001.png")
        
        # Validate
        result = validator.validate_frames(temp_output_dir, num_frames=8)
        
        assert result['valid'] is True
        assert not any('blank' in err.lower() for err in result['errors'])
    
    def test_blank_frame_detected(self, validator, temp_output_dir):
        """FAIL: Blank frame detected (>95% single color)."""
        # Create 7 valid frames + 1 blank
        for i in range(8):
            if i == 3:
                frame = create_blank_frame()  # All one color
            else:
                frame = create_test_frame(size=(32, 32))
            frame.save(temp_output_dir / f"sprite_frame_{i}_00001.png")
        
        # Validate
        result = validator.validate_frames(temp_output_dir, num_frames=8)
        
        assert result['valid'] is False
        assert any('blank' in err.lower() for err in result['errors'])
        assert 'frame 3' in result['errors'][0].lower()


class TestMissingFrames:
    """Test missing frame detection."""
    
    def test_all_frames_present(self, validator, temp_output_dir):
        """PASS: All 8 frames present."""
        for i in range(8):
            frame = create_test_frame(size=(32, 32))
            frame.save(temp_output_dir / f"sprite_frame_{i}_00001.png")
        
        result = validator.validate_frames(temp_output_dir, num_frames=8)
        
        assert result['valid'] is True
        assert result['metrics']['frame_count'] == 8
    
    def test_missing_frame(self, validator, temp_output_dir):
        """FAIL: Frame 4 is missing."""
        # Create 7 frames (skip index 4)
        for i in range(8):
            if i == 4:
                continue  # Skip this frame
            frame = create_test_frame(size=(32, 32))
            frame.save(temp_output_dir / f"sprite_frame_{i}_00001.png")
        
        result = validator.validate_frames(temp_output_dir, num_frames=8)
        
        assert result['valid'] is False
        assert any('missing' in err.lower() for err in result['errors'])
        assert 'frame 4' in result['errors'][0].lower()


class TestMotionAnalysis:
    """Test frame-to-frame motion analysis."""
    
    def test_reasonable_motion(self, validator, temp_output_dir):
        """PASS: Motion between frames is within acceptable range."""
        # Create frames with slight variations (simulating animation)
        for i in range(8):
            colors = [
                (15 + i*2, 56, 15),      # Slightly shifting colors
                (48, 98 + i, 48),
                (139, 172, 15 + i),
                (155, 188, 15)
            ]
            frame = create_test_frame(size=(32, 32), colors=colors)
            frame.save(temp_output_dir / f"sprite_frame_{i}_00001.png")
        
        result = validator.validate_frames(temp_output_dir, num_frames=8)
        
        assert result['valid'] is True
        motion_range = result['metrics'].get('motion_range', [0, 0])
        assert 0.01 <= motion_range[0] <= 0.5  # Min motion in acceptable range
        assert 0.01 <= motion_range[1] <= 0.5  # Max motion in acceptable range
    
    def test_excessive_motion(self, validator, temp_output_dir):
        """WARN: Excessive motion detected between frames."""
        # Create frames where one has drastically different content
        for i in range(8):
            if i == 5:
                frame = create_different_character_frame()  # Completely different
            else:
                frame = create_test_frame(size=(32, 32))
            frame.save(temp_output_dir / f"sprite_frame_{i}_00001.png")
        
        result = validator.validate_frames(temp_output_dir, num_frames=8)
        
        # Should have warning about motion or palette
        assert len(result['warnings']) > 0


class TestValidationMetrics:
    """Test validation metrics calculation."""
    
    def test_metrics_structure(self, validator, temp_output_dir):
        """Verify all expected metrics are present."""
        # Create valid frames
        for i in range(8):
            frame = create_test_frame(size=(32, 32))
            frame.save(temp_output_dir / f"sprite_frame_{i}_00001.png")
        
        result = validator.validate_frames(temp_output_dir, num_frames=8)
        
        # Check required metrics
        assert 'frame_count' in result['metrics']
        assert 'palette_similarity' in result['metrics']
        assert 'motion_range' in result['metrics']
        assert 'color_variance' in result['metrics']
        
        # Verify metric types
        assert isinstance(result['metrics']['frame_count'], int)
        assert isinstance(result['metrics']['palette_similarity'], float)
        assert isinstance(result['metrics']['motion_range'], list)
        assert isinstance(result['metrics']['color_variance'], float)


# Run with: pytest tests/test_sprite_generation.py -v
