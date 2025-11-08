"""
ComfyUI Post-Processing Pipeline
Version: 1.0
Platform: Intel Mac (macOS Ventura) + Docker

Converts ComfyUI output (512x512 smooth images) to authentic Game Boy Color sprites.
"""

import os
import subprocess
from pathlib import Path
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class SpritePostProcessor:
    """
    Post-processes ComfyUI generated images into Game Boy Color compatible sprites.
    
    Pipeline:
    1. Load ComfyUI output (512x512 smooth image)
    2. Downscale to 64x64 using Nearest Neighbors
    3. Apply PixelDetector for 4-color palette quantization
    4. Upscale to 512x512 for display (preserves pixel grid)
    5. Export as indexed PNG
    """
    
    def __init__(self, pixeldetector_path: str = None):
        """
        Initialize post-processor.
        
        Args:
            pixeldetector_path: Path to pixeldetector.py script
                              Default: /app/../pixeldetector/pixeldetector.py
        """
        if pixeldetector_path is None:
            # Default to project root pixeldetector
            pixeldetector_path = "/app/../pixeldetector/pixeldetector.py"
        
        self.pixeldetector_path = Path(pixeldetector_path)
        
        if not self.pixeldetector_path.exists():
            logger.warning(
                f"PixelDetector not found at {self.pixeldetector_path}. "
                f"Palette quantization will be skipped."
            )
    
    def process(
        self,
        input_path: str,
        output_path: str,
        target_size: int = 64,
        num_colors: int = 4,
        use_palette_quantization: bool = True,
        upscale_for_display: bool = True
    ) -> str:
        """
        Process ComfyUI output into GBC sprite.
        
        Args:
            input_path: Path to ComfyUI generated image (512x512)
            output_path: Where to save final sprite
            target_size: Final sprite dimensions (default 64x64 for GBC)
            num_colors: Max colors in palette (4 for GBC)
            use_palette_quantization: Apply PixelDetector (True recommended)
            upscale_for_display: Scale back up to 512x512 with pixel grid visible
        
        Returns:
            Path to processed sprite
        
        Raises:
            FileNotFoundError: If input_path doesn't exist
            RuntimeError: If processing fails
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input image not found: {input_path}")
        
        logger.info(f"Processing {input_path.name} -> {output_path.name}")
        
        # Step 1: Load image
        img = Image.open(input_path)
        original_size = img.size
        logger.debug(f"Loaded image: {original_size[0]}x{original_size[1]}")
        
        # Step 2: Downscale to target size (64x64) with Nearest Neighbors
        small = img.resize((target_size, target_size), Image.NEAREST)
        logger.debug(f"Downscaled to {target_size}x{target_size}")
        
        # Step 3: Apply palette quantization if enabled
        if use_palette_quantization and self.pixeldetector_path.exists():
            temp_small_path = output_path.parent / f"temp_{output_path.name}"
            small.save(temp_small_path)
            
            try:
                # Run PixelDetector
                subprocess.run([
                    'python3',
                    str(self.pixeldetector_path),
                    '--input', str(temp_small_path),
                    '--output', str(temp_small_path),
                    '--max', str(num_colors * 4),  # Max computation colors
                    '--palette'
                ], check=True, capture_output=True, text=True)
                
                # Reload quantized image
                small = Image.open(temp_small_path)
                logger.debug(f"Applied {num_colors}-color palette quantization")
                
                # Clean up temp file
                temp_small_path.unlink()
                
            except subprocess.CalledProcessError as e:
                logger.error(f"PixelDetector failed: {e.stderr}")
                logger.warning("Continuing without palette quantization")
        
        # Step 4: Upscale for display (optional)
        if upscale_for_display:
            # Scale back to original size preserving pixel grid
            display = small.resize(original_size, Image.NEAREST)
            display.save(output_path)
            logger.info(f"Saved upscaled sprite: {output_path}")
        else:
            # Save at native 64x64 resolution
            small.save(output_path)
            logger.info(f"Saved native sprite: {output_path}")
        
        return str(output_path)
    
    def batch_process(
        self,
        input_dir: str,
        output_dir: str,
        pattern: str = "*.png",
        **kwargs
    ) -> list:
        """
        Process multiple ComfyUI outputs.
        
        Args:
            input_dir: Directory containing ComfyUI outputs
            output_dir: Directory for processed sprites
            pattern: File pattern to match (default: *.png)
            **kwargs: Additional arguments passed to process()
        
        Returns:
            List of output file paths
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        input_files = sorted(input_dir.glob(pattern))
        output_files = []
        
        logger.info(f"Batch processing {len(input_files)} files")
        
        for input_file in input_files:
            output_file = output_dir / input_file.name
            
            try:
                result = self.process(
                    str(input_file),
                    str(output_file),
                    **kwargs
                )
                output_files.append(result)
            except Exception as e:
                logger.error(f"Failed to process {input_file.name}: {e}")
                continue
        
        logger.info(f"Processed {len(output_files)}/{len(input_files)} files")
        return output_files


def quick_process(input_path: str, output_path: str) -> str:
    """
    Convenience function for one-shot processing with defaults.
    
    Args:
        input_path: ComfyUI output image
        output_path: Where to save GBC sprite
    
    Returns:
        Path to processed sprite
    """
    processor = SpritePostProcessor()
    return processor.process(input_path, output_path)


if __name__ == "__main__":
    # CLI usage
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python post_process.py <input_image> <output_image>")
        print("Example: python post_process.py comfyui_output.png gbc_sprite.png")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    logging.basicConfig(level=logging.INFO)
    
    try:
        result = quick_process(input_file, output_file)
        print(f"✅ Processed: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
