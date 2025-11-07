"""
Sprite Manager - Edit, Delete, Duplicate, Export sprites
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Manages sprite lifecycle operations beyond initial creation.
"""

import logging
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from PIL import Image
from datetime import datetime

logger = logging.getLogger(__name__)


class SpriteManager:
    """
    Manages sprite operations in GBStudio projects.
    
    Features:
    - Edit sprite metadata (name, type)
    - Delete sprite from project
    - Duplicate sprite with variations
    - Export sprite as standalone PNG
    - List sprites with filtering
    """
    
    def __init__(self, project_path: str):
        """
        Initialize sprite manager for a GBStudio project.
        
        Args:
            project_path: Path to .gbsproj file
        """
        self.project_path = Path(project_path)
        self.project_dir = self.project_path.parent
        self.sprites_dir = self.project_dir / "assets" / "sprites"
        
        if not self.project_path.exists():
            raise FileNotFoundError(f"Project not found: {project_path}")
        
        self.sprites_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"Initialized sprite manager for {self.project_path.name}",
            extra={'project_path': str(self.project_path)}
        )
    
    def _load_project(self) -> Dict[str, Any]:
        """Load project JSON."""
        with open(self.project_path, 'r') as f:
            return json.load(f)
    
    def _save_project(self, project_data: Dict[str, Any]):
        """Save project JSON."""
        with open(self.project_path, 'w') as f:
            json.dump(project_data, f, indent=2)

    def _find_sprite_by_id(self, sprite_id: str) -> Optional[Dict[str, Any]]:
        """
        Find sprite by ID using list comprehension.

        Args:
            sprite_id: Sprite ID to search for

        Returns:
            Sprite dictionary if found, None otherwise
        """
        project = self._load_project()
        sprites = [s for s in project['spriteSheets'] if s['id'] == sprite_id]
        return sprites[0] if sprites else None

    def _find_sprite_index(self, sprite_id: str) -> tuple[Optional[int], Optional[Dict[str, Any]]]:
        """
        Find sprite and its index in the spriteSheets list.

        Args:
            sprite_id: Sprite ID to search for

        Returns:
            Tuple of (index, sprite) if found, (None, None) otherwise
        """
        project = self._load_project()
        for i, sprite in enumerate(project['spriteSheets']):
            if sprite['id'] == sprite_id:
                return (i, sprite)
        return (None, None)
    
    def edit_sprite(
        self,
        sprite_id: str,
        name: Optional[str] = None,
        sprite_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Edit sprite metadata.

        Args:
            sprite_id: Sprite ID to edit
            name: New name (optional)
            sprite_type: New type (optional): actor, actor_animated, static, ui

        Returns:
            Updated sprite entry

        Raises:
            ValueError: If sprite not found or invalid type
        """
        project = self._load_project()

        # Find sprite using helper method
        sprite = self._find_sprite_by_id(sprite_id)

        if not sprite:
            raise ValueError(f"Sprite {sprite_id} not found in project")
        
        # Update fields
        if name is not None:
            old_name = sprite['name']
            sprite['name'] = name
            logger.info(
                f"Renamed sprite {sprite_id}: '{old_name}' → '{name}'",
                extra={'sprite_id': sprite_id, 'old_name': old_name, 'new_name': name}
            )
        
        if sprite_type is not None:
            valid_types = ['actor', 'actor_animated', 'static', 'ui']
            if sprite_type not in valid_types:
                raise ValueError(f"Invalid type: {sprite_type}. Must be one of {valid_types}")
            
            old_type = sprite['type']
            sprite['type'] = sprite_type
            logger.info(
                f"Changed sprite {sprite_id} type: '{old_type}' → '{sprite_type}'",
                extra={'sprite_id': sprite_id, 'old_type': old_type, 'new_type': sprite_type}
            )
        
        # Update version timestamp
        sprite['_v'] = int(datetime.now().timestamp() * 1000)
        
        # Save project
        self._save_project(project)
        
        return sprite
    
    def delete_sprite(self, sprite_id: str, delete_file: bool = True) -> bool:
        """
        Delete sprite from project.

        Args:
            sprite_id: Sprite ID to delete
            delete_file: If True, also delete PNG file from disk

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If sprite not found
        """
        project = self._load_project()

        # Find and remove sprite using helper method
        index, sprite = self._find_sprite_index(sprite_id)

        if sprite is None:
            raise ValueError(f"Sprite {sprite_id} not found in project")

        # Remove from project
        project['spriteSheets'].pop(index)

        # Delete file if requested
        if delete_file:
            sprite_file = self.sprites_dir / sprite['filename']
            if sprite_file.exists():
                sprite_file.unlink()
                logger.info(
                    f"Deleted sprite file: {sprite['filename']}",
                    extra={'sprite_id': sprite_id, 'filename': sprite['filename']}
                )
        
        # Save project
        self._save_project(project)
        
        logger.info(
            f"Deleted sprite {sprite_id} from project",
            extra={'sprite_id': sprite_id, 'name': sprite['name']}
        )
        
        return True
    
    def duplicate_sprite(
        self,
        sprite_id: str,
        new_name: str,
        apply_variation: bool = False,
        variation_type: str = "hue_shift"
    ) -> Dict[str, Any]:
        """
        Duplicate sprite with optional visual variation.

        Args:
            sprite_id: Source sprite ID
            new_name: Name for duplicated sprite
            apply_variation: If True, apply visual variation
            variation_type: Type of variation (hue_shift, brightness, contrast)

        Returns:
            New sprite entry

        Raises:
            ValueError: If sprite not found or invalid variation type
        """
        project = self._load_project()

        # Find source sprite using helper method
        source_sprite = self._find_sprite_by_id(sprite_id)

        if not source_sprite:
            raise ValueError(f"Sprite {sprite_id} not found in project")
        
        # Load source image
        source_file = self.sprites_dir / source_sprite['filename']
        if not source_file.exists():
            raise FileNotFoundError(f"Source sprite file not found: {source_file}")
        
        source_image = Image.open(source_file)
        
        # Apply variation if requested
        if apply_variation:
            source_image = self._apply_variation(source_image, variation_type)
        
        # Generate new filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"{new_name.lower().replace(' ', '_')}_{timestamp}.png"
        new_file = self.sprites_dir / new_filename
        
        # Save image
        source_image.save(new_file, 'PNG', optimize=True)
        
        # Create new sprite entry
        import hashlib
        new_sprite_id = f"sprite_{hashlib.sha256(new_filename.encode()).hexdigest()[:8]}"
        
        new_sprite = {
            'id': new_sprite_id,
            'name': new_name,
            'filename': new_filename,
            'numFrames': source_sprite['numFrames'],
            'type': source_sprite['type'],
            'canvasWidth': source_sprite['canvasWidth'],
            'canvasHeight': source_sprite['canvasHeight'],
            '_v': int(datetime.now().timestamp() * 1000)
        }
        
        # Add to project
        project['spriteSheets'].append(new_sprite)
        self._save_project(project)
        
        logger.info(
            f"Duplicated sprite {sprite_id} → {new_sprite_id}",
            extra={
                'source_id': sprite_id,
                'new_id': new_sprite_id,
                'new_name': new_name,
                'variation_applied': apply_variation
            }
        )
        
        return new_sprite
    
    def _apply_variation(self, image: Image.Image, variation_type: str) -> Image.Image:
        """
        Apply visual variation to image.
        
        Args:
            image: Source image
            variation_type: Type of variation
        
        Returns:
            Modified image
        """
        if variation_type == "hue_shift":
            # Shift hue by rotating color palette
            if image.mode == 'P':
                # Get palette
                palette = image.getpalette()
                if palette:
                    # Rotate palette colors (simple hue shift approximation)
                    shifted_palette = palette[3:] + palette[:3]
                    image.putpalette(shifted_palette)
            
        elif variation_type == "brightness":
            # Increase brightness slightly
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Brightness(image.convert('RGB'))
            image = enhancer.enhance(1.2)
            
        elif variation_type == "contrast":
            # Increase contrast
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(image.convert('RGB'))
            image = enhancer.enhance(1.3)
        
        else:
            raise ValueError(f"Unknown variation type: {variation_type}")
        
        return image
    
    def export_sprite(
        self,
        sprite_id: str,
        output_path: str,
        export_format: str = "grid",
        scale: int = 1
    ) -> str:
        """
        Export sprite as standalone PNG.

        Args:
            sprite_id: Sprite ID to export
            output_path: Output file path
            export_format: Format (grid, strip, individual_frames)
            scale: Scale multiplier (1 = original size)

        Returns:
            Path to exported file(s)

        Export Formats:
            - grid: Keep as 3x3 grid (default)
            - strip: Convert to horizontal strip (8 frames in row)
            - individual_frames: Export each frame separately
        """
        project = self._load_project()

        # Find sprite using helper method
        sprite = self._find_sprite_by_id(sprite_id)

        if not sprite:
            raise ValueError(f"Sprite {sprite_id} not found in project")
        
        # Load sprite image
        sprite_file = self.sprites_dir / sprite['filename']
        if not sprite_file.exists():
            raise FileNotFoundError(f"Sprite file not found: {sprite_file}")
        
        sprite_image = Image.open(sprite_file)
        
        # Apply scale if requested
        if scale != 1:
            new_size = (sprite_image.width * scale, sprite_image.height * scale)
            sprite_image = sprite_image.resize(new_size, Image.NEAREST)
        
        output_path = Path(output_path)
        
        if export_format == "grid":
            # Export as-is (3x3 grid)
            sprite_image.save(output_path, 'PNG', optimize=True)
            logger.info(
                f"Exported sprite {sprite_id} as grid to {output_path}",
                extra={'sprite_id': sprite_id, 'format': 'grid', 'scale': scale}
            )
            return str(output_path)
        
        elif export_format == "strip":
            # Convert to horizontal strip
            frame_width = sprite['canvasWidth'] * scale
            frame_height = sprite['canvasHeight'] * scale
            num_frames = sprite['numFrames']
            
            strip = Image.new('RGBA', (frame_width * num_frames, frame_height))
            
            # Extract frames from grid and place in strip
            for i in range(num_frames):
                row = i // 3
                col = i % 3
                
                # Extract frame from grid
                frame_x = col * sprite['canvasWidth'] * scale
                frame_y = row * sprite['canvasHeight'] * scale
                frame = sprite_image.crop((
                    frame_x,
                    frame_y,
                    frame_x + frame_width,
                    frame_y + frame_height
                ))
                
                # Place in strip
                strip.paste(frame, (i * frame_width, 0))
            
            strip.save(output_path, 'PNG', optimize=True)
            logger.info(
                f"Exported sprite {sprite_id} as strip to {output_path}",
                extra={'sprite_id': sprite_id, 'format': 'strip', 'frames': num_frames}
            )
            return str(output_path)
        
        elif export_format == "individual_frames":
            # Export each frame separately
            frame_width = sprite['canvasWidth'] * scale
            frame_height = sprite['canvasHeight'] * scale
            num_frames = sprite['numFrames']
            
            output_dir = output_path.parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            frame_paths = []
            base_name = output_path.stem
            
            for i in range(num_frames):
                row = i // 3
                col = i % 3
                
                # Extract frame
                frame_x = col * sprite['canvasWidth'] * scale
                frame_y = row * sprite['canvasHeight'] * scale
                frame = sprite_image.crop((
                    frame_x,
                    frame_y,
                    frame_x + frame_width,
                    frame_y + frame_height
                ))
                
                # Save frame
                frame_path = output_dir / f"{base_name}_frame_{i}.png"
                frame.save(frame_path, 'PNG', optimize=True)
                frame_paths.append(str(frame_path))
            
            logger.info(
                f"Exported sprite {sprite_id} as {num_frames} individual frames",
                extra={'sprite_id': sprite_id, 'format': 'individual_frames', 'frames': num_frames}
            )
            return str(output_dir)
        
        else:
            raise ValueError(f"Unknown export format: {export_format}")
    
    def list_sprites(
        self,
        filter_type: Optional[str] = None,
        search_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List sprites in project with optional filtering.
        
        Args:
            filter_type: Filter by type (actor, actor_animated, static, ui)
            search_name: Search by name (case-insensitive substring match)
        
        Returns:
            List of sprite entries matching filters
        """
        project = self._load_project()
        sprites = project['spriteSheets']
        
        # Apply filters
        if filter_type:
            sprites = [s for s in sprites if s['type'] == filter_type]
        
        if search_name:
            search_lower = search_name.lower()
            sprites = [s for s in sprites if search_lower in s['name'].lower()]
        
        return sprites
    
    def get_sprite_info(self, sprite_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a sprite.

        Args:
            sprite_id: Sprite ID

        Returns:
            Dictionary with sprite metadata and file info

        Raises:
            ValueError: If sprite not found
        """
        # Find sprite using helper method
        sprite = self._find_sprite_by_id(sprite_id)

        if not sprite:
            raise ValueError(f"Sprite {sprite_id} not found")
        
        # Get file info
        sprite_file = self.sprites_dir / sprite['filename']
        file_info = {}
        
        if sprite_file.exists():
            file_info = {
                'file_size_bytes': sprite_file.stat().st_size,
                'file_exists': True
            }
            
            # Get image info
            try:
                img = Image.open(sprite_file)
                file_info.update({
                    'actual_width': img.width,
                    'actual_height': img.height,
                    'image_mode': img.mode,
                    'format': img.format
                })
            except Exception as e:
                logger.error(f"Failed to read sprite image: {e}")
                file_info['read_error'] = str(e)
        else:
            file_info['file_exists'] = False
        
        return {
            **sprite,
            'file_info': file_info,
            'file_path': str(sprite_file)
        }


# Convenience function for creating manager
def create_sprite_manager(project_path: str) -> SpriteManager:
    """Create SpriteManager instance for a project."""
    return SpriteManager(project_path)
