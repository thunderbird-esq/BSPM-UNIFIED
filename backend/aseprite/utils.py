"""
Aseprite MCP Client - Utility Functions
Version: 1.0
Platform: BSPM-UNIFIED

Helper functions for PNG conversion, palette management, and color operations.
"""

import os
from typing import List, Tuple

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

from .exceptions import AsepritePaletteError, AsepriteValidationError
from .types import PaletteInfo, PixelData

# Game Boy Classic palette (DMG)
GAMEBOY_PALETTE = ["#0F380F", "#306230", "#8BAC0F", "#9BBC0F"]

# Game Boy Pocket palette
GAMEBOY_POCKET_PALETTE = ["#000000", "#545454", "#A8A8A8", "#FFFFFF"]


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """
    Convert hex color to RGB tuple.

    Args:
        hex_color: Hex color string (e.g., "#FF0000")

    Returns:
        Tuple of (R, G, B) values (0-255)

    Raises:
        AsepriteValidationError: If hex color is invalid
    """
    if not hex_color.startswith("#") or len(hex_color) != 7:
        raise AsepriteValidationError(
            f"Invalid hex color format: {hex_color}", field="color", value=hex_color
        )

    try:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError as e:
        raise AsepriteValidationError(
            f"Invalid hex color value: {hex_color}", field="color", value=hex_color
        ) from e


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """
    Convert RGB values to hex color string.

    Args:
        r: Red value (0-255)
        g: Green value (0-255)
        b: Blue value (0-255)

    Returns:
        Hex color string (e.g., "#FF0000")
    """
    return f"#{r:02X}{g:02X}{b:02X}"


def read_png_pixels(png_path: str) -> Tuple[List[PixelData], int, int]:
    """
    Read PNG file and extract pixel data.

    Args:
        png_path: Path to PNG file

    Returns:
        Tuple of (pixel_list, width, height)

    Raises:
        AsepriteValidationError: If file doesn't exist or can't be read
    """
    if not os.path.exists(png_path):
        raise AsepriteValidationError(
            f"PNG file not found: {png_path}", field="png_path", value=png_path
        )

    try:
        img = Image.open(png_path)
        img = img.convert("RGBA")
        width, height = img.size

        pixels = []
        for y in range(height):
            for x in range(width):
                r, g, b, a = img.getpixel((x, y))
                # Skip fully transparent pixels
                if a > 0:
                    hex_color = rgb_to_hex(r, g, b)
                    pixels.append(PixelData(x=x, y=y, color=hex_color))

        return pixels, width, height

    except Exception as e:
        raise AsepriteValidationError(
            f"Failed to read PNG file: {e}", field="png_path", value=png_path
        ) from e


def extract_palette_from_image(image_path: str, num_colors: int = 4) -> PaletteInfo:
    """
    Extract dominant color palette from an image using K-means clustering.

    Args:
        image_path: Path to image file
        num_colors: Number of colors to extract (default: 4 for Game Boy)

    Returns:
        PaletteInfo with extracted colors

    Raises:
        AsepritePaletteError: If palette extraction fails
    """
    if not os.path.exists(image_path):
        raise AsepritePaletteError(f"Image file not found: {image_path}")

    try:
        img = Image.open(image_path)
        img = img.convert("RGB")

        # Resize for faster processing
        img.thumbnail((150, 150))

        # Convert to numpy array
        pixels = np.array(img).reshape(-1, 3)

        # Use K-means to find dominant colors
        kmeans = KMeans(n_clusters=num_colors, random_state=42, n_init=10)
        kmeans.fit(pixels)

        # Sort colors by luminance (dark to light)
        colors = kmeans.cluster_centers_.astype(int)
        luminance = 0.299 * colors[:, 0] + 0.587 * colors[:, 1] + 0.114 * colors[:, 2]
        sorted_indices = np.argsort(luminance)
        colors = colors[sorted_indices]

        # Convert to hex
        hex_colors = [rgb_to_hex(r, g, b) for r, g, b in colors]

        return PaletteInfo(colors=hex_colors, name="extracted")

    except Exception as e:
        raise AsepritePaletteError(f"Failed to extract palette: {e}") from e


def apply_palette_to_pixels(
    pixels: List[PixelData], palette: PaletteInfo
) -> List[PixelData]:
    """
    Remap pixel colors to nearest palette color.

    Args:
        pixels: List of pixel data
        palette: Target palette

    Returns:
        List of remapped pixels
    """
    # Convert palette to RGB
    palette_rgb = [hex_to_rgb(color) for color in palette.colors]

    remapped_pixels = []
    for pixel in pixels:
        pixel_rgb = hex_to_rgb(pixel.color)

        # Find nearest palette color using Euclidean distance
        min_distance = float("inf")
        nearest_color = palette.colors[0]

        for palette_color, palette_rgb_val in zip(palette.colors, palette_rgb):
            distance = sum((a - b) ** 2 for a, b in zip(pixel_rgb, palette_rgb_val))
            if distance < min_distance:
                min_distance = distance
                nearest_color = palette_color

        remapped_pixels.append(PixelData(x=pixel.x, y=pixel.y, color=nearest_color))

    return remapped_pixels


def validate_gameboy_palette(palette: List[str]) -> bool:
    """
    Validate that palette meets Game Boy requirements.

    Args:
        palette: List of hex color codes

    Returns:
        True if valid

    Raises:
        AsepritePaletteError: If palette is invalid
    """
    if len(palette) != 4:
        raise AsepritePaletteError(
            f"Game Boy palette must have exactly 4 colors, got {len(palette)}",
            palette_colors=palette,
        )

    for color in palette:
        if not color.startswith("#") or len(color) != 7:
            raise AsepritePaletteError(
                f"Invalid hex color in palette: {color}", palette_colors=palette
            )

    return True


def get_default_gameboy_palette() -> PaletteInfo:
    """
    Get the default Game Boy DMG palette.

    Returns:
        PaletteInfo with classic Game Boy colors
    """
    return PaletteInfo(colors=GAMEBOY_PALETTE, name="gameboy_dmg")


def chunk_pixels(
    pixels: List[PixelData], chunk_size: int = 1000
) -> List[List[PixelData]]:
    """
    Split pixel list into chunks for batch processing.

    Args:
        pixels: List of all pixels
        chunk_size: Maximum pixels per chunk

    Returns:
        List of pixel chunks
    """
    return [pixels[i : i + chunk_size] for i in range(0, len(pixels), chunk_size)]


def validate_sprite_dimensions(width: int, height: int, max_size: int = 4096) -> bool:
    """
    Validate sprite dimensions.

    Args:
        width: Sprite width
        height: Sprite height
        max_size: Maximum dimension size

    Returns:
        True if valid

    Raises:
        AsepriteValidationError: If dimensions are invalid
    """
    if width <= 0 or height <= 0:
        raise AsepriteValidationError(
            f"Dimensions must be positive: {width}x{height}",
            field="dimensions",
            value=f"{width}x{height}",
        )

    if width > max_size or height > max_size:
        raise AsepriteValidationError(
            f"Dimensions exceed maximum {max_size}: {width}x{height}",
            field="dimensions",
            value=f"{width}x{height}",
        )

    return True


def create_indexed_png_data(
    pixels: List[PixelData], width: int, height: int, palette: PaletteInfo
) -> bytes:
    """
    Create indexed PNG image data from pixels and palette.

    Args:
        pixels: List of pixel data
        width: Image width
        height: Image height
        palette: Color palette

    Returns:
        PNG image bytes
    """
    # Create empty image
    img = Image.new("P", (width, height))

    # Set palette
    palette_rgb = []
    for color in palette.colors:
        r, g, b = hex_to_rgb(color)
        palette_rgb.extend([r, g, b])

    # Pad palette to 256 colors
    while len(palette_rgb) < 768:
        palette_rgb.extend([0, 0, 0])

    img.putpalette(palette_rgb)

    # Draw pixels
    for pixel in pixels:
        # Find palette index
        palette_index = palette.colors.index(pixel.color)
        img.putpixel((pixel.x, pixel.y), palette_index)

    # Convert to bytes
    import io

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
