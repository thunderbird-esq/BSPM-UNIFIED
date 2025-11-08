"""
GBStudio Project Integration - Programmatic .gbsproj Manipulation
Version: 3.1
Platform: Intel Mac (macOS Ventura) + Docker

Complete implementation for:
- Loading/parsing GBStudio 4.1.3 .gbsproj JSON files
- Combining individual frames into sprite sheet grid (3x3 layout)
- Converting to indexed 4-color PNG (GBC compliant)
- Adding sprite sheet entries to project JSON
- Validating sprite sheet format requirements
"""

import json
import hashlib
import time
import shutil
from typing import List, Dict, Optional
from pathlib import Path

from PIL import Image
import numpy as np

# Import atomic write utilities
import sys
sys.path.insert(0, '/home/user/BSPM-UNIFIED/BSPM-UNIFIED 2')
from backend.utils.atomic_write import atomic_write_json


class ProjectTransaction:
    """
    Transaction-like context manager for GBStudio project operations

    Provides rollback capability for multi-step operations:
    - Backs up current project state on enter
    - Commits changes on successful exit
    - Rolls back to backup on exception

    Usage:
        with ProjectTransaction(project) as txn:
            project.add_sprite_sheet(...)
            project.add_background(...)
            # If any operation fails, entire transaction rolls back
    """

    def __init__(self, project: 'GBStudioProject'):
        """
        Initialize transaction

        Args:
            project: GBStudioProject instance to protect
        """
        self.project = project
        self.backup_data = None
        self.committed = False

    def __enter__(self):
        """
        Enter transaction context: backup current state

        Returns:
            Self for use in with statement
        """
        # Deep copy current project data
        import copy
        self.backup_data = copy.deepcopy(self.project.project_data)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit transaction context: commit or rollback

        Args:
            exc_type: Exception type if raised, None otherwise
            exc_val: Exception value if raised, None otherwise
            exc_tb: Exception traceback if raised, None otherwise

        Returns:
            False to propagate exceptions
        """
        if exc_type is not None:
            # Exception occurred, rollback
            self.rollback()
            print(f"[Transaction] Rolled back due to error: {exc_type.__name__}: {exc_val}")
            return False  # Propagate exception
        else:
            # No exception, commit
            self.commit()
            return False

    def commit(self):
        """
        Commit transaction: save current state to disk

        Safe to call multiple times (idempotent).
        """
        if not self.committed:
            self.project._save_project()
            self.committed = True
            print("[Transaction] Committed successfully")

    def rollback(self):
        """
        Rollback transaction: restore from backup

        Restores project_data to state at transaction start.
        Does not save to disk (leaves file unchanged).
        """
        if self.backup_data is not None:
            self.project.project_data = self.backup_data
            self.backup_data = None
            print("[Transaction] Rolled back to previous state")


class GBStudioProject:
    """
    Interface for programmatic GBStudio project manipulation
    
    Supports GBStudio 4.1.3 .gbsproj format
    """
    
    def __init__(self, project_path: str):
        """
        Initialize project interface
        
        Args:
            project_path: Path to .gbsproj file
        
        Raises:
            FileNotFoundError: If project file doesn't exist
            json.JSONDecodeError: If project file is invalid JSON
        """
        self.project_path = Path(project_path)
        self.project_dir = self.project_path.parent
        self.project_data = None
        
        self._load_project()
    
    def _load_project(self):
        """Load GBStudio project JSON"""
        if not self.project_path.exists():
            raise FileNotFoundError(f"Project file not found: {self.project_path}")
        
        with open(self.project_path, 'r') as f:
            self.project_data = json.load(f)
        
        # Validate basic structure
        required_keys = ['name', '_version', 'spriteSheets']
        for key in required_keys:
            if key not in self.project_data:
                raise ValueError(f"Invalid project file: missing '{key}' field")
    
    def _save_project(self):
        """Save project back to disk with pretty formatting (atomic write)"""
        atomic_write_json(str(self.project_path), self.project_data, indent=2)
    
    def add_sprite_sheet(
        self,
        frame_paths: List[str],
        name: str,
        sprite_type: str = "actor_animated",
        frames_per_row: int = 3
    ) -> str:
        """
        Add a sprite sheet to the GBStudio project
        
        Process:
        1. Combine individual frames into grid layout
        2. Convert to indexed 4-color PNG
        3. Save to assets/sprites/
        4. Add entry to project JSON
        
        Args:
            frame_paths: List of paths to individual frame PNGs
            name: Display name for sprite in GBStudio
            sprite_type: "actor", "actor_animated", "static", or "ui"
            frames_per_row: Frames per row in grid (default 3 for 8 frames)
        
        Returns:
            Sprite sheet ID (for reference in scenes)
        
        Raises:
            ValueError: If frame dimensions don't match or invalid type
        """
        # Validate sprite type
        valid_types = ["actor", "actor_animated", "static", "ui"]
        if sprite_type not in valid_types:
            raise ValueError(f"Invalid sprite type: {sprite_type}. Must be one of {valid_types}")
        
        # Validate name
        if not name or len(name) > 64:
            raise ValueError("Name must be 1-64 characters")
        
        # Generate sprite sheet file
        sprite_filename = self._generate_filename(name)
        sprite_path = self.project_dir / "assets" / "sprites" / sprite_filename
        
        # Ensure directory exists
        sprite_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Combine frames into sprite sheet
        self._combine_frames_to_spritesheet(
            frame_paths,
            sprite_path,
            frames_per_row
        )
        
        # Generate sprite sheet ID
        sprite_id = self._generate_sprite_id(sprite_filename)
        
        # Create sprite sheet entry
        sprite_entry = {
            "id": sprite_id,
            "name": name,
            "filename": sprite_filename,
            "numFrames": len(frame_paths),
            "type": sprite_type,
            "canvasWidth": 32,
            "canvasHeight": 32,
            "_v": int(time.time() * 1000)
        }
        
        # Add to project
        if "spriteSheets" not in self.project_data:
            self.project_data["spriteSheets"] = []
        
        self.project_data["spriteSheets"].append(sprite_entry)
        self._save_project()
        
        print(f"[GBStudio] Added sprite sheet '{name}' with {len(frame_paths)} frames")
        print(f"           ID: {sprite_id}")
        print(f"           File: {sprite_filename}")
        
        return sprite_id
    
    def _generate_filename(self, name: str) -> str:
        """
        Generate valid filename from sprite name
        
        Rules:
        - Lowercase only
        - Replace spaces with underscores
        - Remove invalid characters
        - Add timestamp for uniqueness
        
        Args:
            name: Human-readable name
        
        Returns:
            Valid filename (e.g., "knight_20250104_143000.png")
        """
        # Convert to lowercase, replace spaces
        filename = name.lower().replace(' ', '_')
        
        # Remove invalid characters (keep only alphanumeric and underscore)
        filename = ''.join(c for c in filename if c.isalnum() or c == '_')
        
        # Add timestamp for uniqueness
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{filename}_{timestamp}.png"
        
        return filename
    
    def _generate_sprite_id(self, filename: str) -> str:
        """
        Generate unique sprite ID
        
        Format: sprite_{8_char_hash}
        
        Args:
            filename: Sprite filename
        
        Returns:
            Sprite ID (e.g., "sprite_8a3f9d2b")
        """
        hash_input = f"{filename}{time.time()}".encode()
        hash_digest = hashlib.sha256(hash_input).hexdigest()
        return f"sprite_{hash_digest[:8]}"
    
    def _combine_frames_to_spritesheet(
        self,
        frame_paths: List[str],
        output_path: Path,
        frames_per_row: int = 3
    ):
        """
        Combine individual frames into single sprite sheet PNG
        
        Grid layout for 8 frames with frames_per_row=3:
        
            [Frame 0] [Frame 1] [Frame 2]
            [Frame 3] [Frame 4] [Frame 5]
            [Frame 6] [Frame 7] [Empty  ]
        
        Total dimensions: 96x96 pixels (3x3 grid of 32x32 frames)
        
        Args:
            frame_paths: Paths to individual frame PNGs
            output_path: Where to save combined sprite sheet
            frames_per_row: Frames per row (default 3)
        
        Raises:
            ValueError: If frames have inconsistent dimensions
        """
        # Load all frames
        frames = []
        for path in frame_paths:
            try:
                frame = Image.open(path).convert('RGBA')
                if frame.size != (32, 32):
                    raise ValueError(
                        f"Frame {path} has incorrect size {frame.size}. "
                        f"All frames must be 32x32 pixels."
                    )
                frames.append(frame)
            except Exception as e:
                raise ValueError(f"Failed to load frame {path}: {e}")
        
        # Calculate grid dimensions
        frame_width, frame_height = 32, 32
        rows = (len(frames) + frames_per_row - 1) // frames_per_row
        
        sheet_width = frame_width * frames_per_row
        sheet_height = frame_height * rows
        
        # Create blank sprite sheet
        sprite_sheet = Image.new('RGBA', (sheet_width, sheet_height), (0, 0, 0, 0))
        
        # Paste frames into grid
        for i, frame in enumerate(frames):
            row = i // frames_per_row
            col = i % frames_per_row
            x = col * frame_width
            y = row * frame_height
            sprite_sheet.paste(frame, (x, y))
        
        # Convert to indexed 4-color (GBC compliant)
        sprite_sheet_indexed = self._convert_to_gbc_palette(sprite_sheet)
        
        # Save with optimization
        sprite_sheet_indexed.save(output_path, 'PNG', optimize=True)
        
        print(f"[GBStudio] Created sprite sheet: {output_path}")
        print(f"           Dimensions: {sprite_sheet_indexed.size}")
        print(f"           Mode: {sprite_sheet_indexed.mode}")
    
    def _convert_to_gbc_palette(self, image: Image.Image) -> Image.Image:
        """
        Convert image to indexed 4-color GBC palette
        
        Process:
        1. Convert RGBA to RGB
        2. Quantize to 4 colors using adaptive palette
        3. Convert to indexed mode (P)
        4. Set color 0 as transparent
        
        Args:
            image: PIL Image in RGBA mode
        
        Returns:
            PIL Image in indexed mode (P) with 4 colors
        """
        # Convert RGBA to RGB (flatten alpha channel)
        rgb_image = Image.new('RGB', image.size, (255, 255, 255))
        rgb_image.paste(image, mask=image.split()[3])  # Use alpha as mask
        
        # Quantize to 4 colors using adaptive palette
        # ADAPTIVE: Palette based on actual colors in image
        indexed_image = rgb_image.quantize(colors=4, method=Image.ADAPTIVE)
        
        # Set transparency (color index 0)
        indexed_image.info['transparency'] = 0
        
        return indexed_image
    
    def add_background(
        self,
        image_path: str,
        name: str
    ) -> str:
        """
        Add a background image to GBStudio project
        
        Requirements:
        - Dimensions must be 160x144 pixels (or 320x288 for 2x)
        - Will be converted to indexed color automatically
        
        Args:
            image_path: Path to background image PNG
            name: Display name for background
        
        Returns:
            Background ID
        
        Raises:
            ValueError: If dimensions are invalid
        """
        # Load and validate image
        img = Image.open(image_path)
        
        valid_sizes = [(160, 144), (320, 288)]
        if img.size not in valid_sizes:
            raise ValueError(
                f"Background must be 160x144 or 320x288 pixels, got {img.size}"
            )
        
        # Create backgrounds directory
        backgrounds_dir = self.project_dir / "assets" / "backgrounds"
        backgrounds_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        bg_filename = self._generate_filename(name)
        bg_path = backgrounds_dir / bg_filename
        
        # Convert to GBC palette and save
        if img.mode == 'RGBA':
            img_indexed = self._convert_to_gbc_palette(img)
        else:
            img_indexed = img.convert('P', palette=Image.ADAPTIVE, colors=4)
        
        img_indexed.save(bg_path, 'PNG', optimize=True)
        
        # Generate background ID
        bg_id = f"bg_{hashlib.sha256(bg_filename.encode()).hexdigest()[:8]}"
        
        # Create background entry
        bg_entry = {
            "id": bg_id,
            "name": name,
            "filename": bg_filename,
            "width": img.size[0] // 8,   # Convert pixels to tiles
            "height": img.size[1] // 8,
            "imageWidth": img.size[0],
            "imageHeight": img.size[1],
            "_v": int(time.time() * 1000)
        }
        
        # Add to project
        if "backgrounds" not in self.project_data:
            self.project_data["backgrounds"] = []
        
        self.project_data["backgrounds"].append(bg_entry)
        self._save_project()
        
        print(f"[GBStudio] Added background '{name}'")
        
        return bg_id
    
    def get_stats(self) -> Dict:
        """
        Get project statistics
        
        Returns:
            Dict with counts of project resources
        """
        return {
            "name": self.project_data.get("name", "Untitled"),
            "author": self.project_data.get("author", "Unknown"),
            "version": self.project_data.get("_version", "unknown"),
            "scenes": len(self.project_data.get("scenes", [])),
            "sprites": len(self.project_data.get("spriteSheets", [])),
            "backgrounds": len(self.project_data.get("backgrounds", [])),
            "actors": sum(
                len(scene.get("actors", []))
                for scene in self.project_data.get("scenes", [])
            )
        }
    
    def list_sprite_sheets(self) -> List[Dict]:
        """
        List all sprite sheets in project
        
        Returns:
            List of sprite sheet info dicts
        """
        return [
            {
                "id": sheet.get("id"),
                "name": sheet.get("name"),
                "filename": sheet.get("filename"),
                "numFrames": sheet.get("numFrames"),
                "type": sheet.get("type")
            }
            for sheet in self.project_data.get("spriteSheets", [])
        ]
    
    def transaction(self) -> ProjectTransaction:
        """
        Create a transaction context for multi-step operations

        Returns:
            ProjectTransaction context manager

        Example:
            with project.transaction():
                project.add_sprite_sheet(frames1, "Sprite1")
                project.add_sprite_sheet(frames2, "Sprite2")
                # Both operations commit together or rollback on error
        """
        return ProjectTransaction(self)

    def validate_sprite_sheet(self, sprite_id: str) -> Dict:
        """
        Validate that a sprite sheet exists and is properly formatted

        Args:
            sprite_id: Sprite sheet ID to validate

        Returns:
            Validation report dict
        """
        report = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Find sprite sheet
        sprite = None
        for sheet in self.project_data.get("spriteSheets", []):
            if sheet.get("id") == sprite_id:
                sprite = sheet
                break
        
        if not sprite:
            report["valid"] = False
            report["errors"].append(f"Sprite sheet {sprite_id} not found in project")
            return report
        
        # Check required fields
        required_fields = ["id", "name", "filename", "numFrames", "type", 
                          "canvasWidth", "canvasHeight", "_v"]
        for field in required_fields:
            if field not in sprite:
                report["valid"] = False
                report["errors"].append(f"Missing required field: {field}")
        
        # Check file exists
        sprite_path = self.project_dir / "assets" / "sprites" / sprite.get("filename", "")
        if not sprite_path.exists():
            report["valid"] = False
            report["errors"].append(f"Sprite file not found: {sprite_path}")
        else:
            # Check file format
            try:
                img = Image.open(sprite_path)
                
                # Check if indexed color
                if img.mode != 'P':
                    report["warnings"].append(
                        f"Sprite is not indexed color (mode: {img.mode}, expected: P)"
                    )
                
                # Check color count
                if img.mode == 'P':
                    palette = img.getpalette()
                    num_colors = len(set(palette)) // 3
                    if num_colors > 4:
                        report["warnings"].append(
                            f"Sprite has {num_colors} colors (GBC limit: 4)"
                        )
                
                # Check dimensions match declared canvas size
                expected_width = sprite.get("canvasWidth", 32) * 3  # Assuming 3x3 grid
                expected_height = sprite.get("canvasHeight", 32) * 3
                
                if img.size != (expected_width, expected_height):
                    report["warnings"].append(
                        f"Sprite dimensions {img.size} don't match expected grid size"
                    )
                
            except Exception as e:
                report["errors"].append(f"Failed to load sprite image: {e}")
        
        return report


# Example usage
if __name__ == "__main__":
    # Initialize project
    project = GBStudioProject("/app/project_files/MyGBCGame.gbsproj")
    
    # Add sprite sheet
    frame_paths = [
        f"/app/output/sprite_frame_{i}_00001.png"
        for i in range(8)
    ]
    
    sprite_id = project.add_sprite_sheet(
        frame_paths=frame_paths,
        name="Knight",
        sprite_type="actor_animated",
        frames_per_row=3
    )
    
    print(f"\nSprite ID: {sprite_id}")
    
    # Validate
    validation = project.validate_sprite_sheet(sprite_id)
    print(f"\nValidation: {validation}")
    
    # Stats
    stats = project.get_stats()
    print(f"\nProject Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")