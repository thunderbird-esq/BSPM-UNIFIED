"""
Style Presets for Sprite Generation
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Provides predefined parameter sets for different sprite generation styles.
"""

from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum


class StylePreset(Enum):
    """Available style presets for sprite generation."""
    CLEAN_PIXEL_ART = "clean_pixel_art"
    DETAILED_SPRITE = "detailed_sprite"
    RETRO_GAME_BOY = "retro_game_boy"
    MODERN_PIXEL = "modern_pixel"
    MINIMAL = "minimal"


@dataclass
class GenerationParameters:
    """
    Parameters for ComfyUI sprite generation.
    
    Attributes:
        steps: Number of diffusion steps (higher = better quality, slower)
        cfg: Classifier-Free Guidance scale (higher = stronger prompt adherence)
        sampler: Sampling algorithm
        scheduler: Noise schedule
        positive_boost: Additional positive prompt terms
        negative_boost: Additional negative prompt terms
        denoise: Denoising strength (1.0 = full denoise)
    """
    steps: int
    cfg: float
    sampler: str
    scheduler: str
    positive_boost: str
    negative_boost: str
    denoise: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for ComfyUI workflow."""
        return {
            'steps': self.steps,
            'cfg': self.cfg,
            'sampler_name': self.sampler,
            'scheduler': self.scheduler,
            'denoise': self.denoise
        }


# Preset definitions
STYLE_PRESETS: Dict[StylePreset, GenerationParameters] = {
    
    StylePreset.CLEAN_PIXEL_ART: GenerationParameters(
        steps=20,
        cfg=8.0,
        sampler="euler_ancestral",
        scheduler="karras",
        positive_boost=(
            "clean lines, sharp edges, minimal shading, "
            "game boy color palette, simple shapes, "
            "high contrast, pixel perfect"
        ),
        negative_boost=(
            "anti-aliasing, gradients, soft edges, blurry, "
            "detailed textures, complex shading, dithering, "
            "too many colors"
        ),
        denoise=1.0
    ),
    
    StylePreset.DETAILED_SPRITE: GenerationParameters(
        steps=25,
        cfg=10.0,
        sampler="euler_ancestral",
        scheduler="karras",
        positive_boost=(
            "detailed pixel art, multiple shading levels, "
            "refined edges, texture detail, "
            "professional sprite work, polished"
        ),
        negative_boost=(
            "flat colors, minimal detail, simple shapes, "
            "blurry, anti-aliasing, photo realistic"
        ),
        denoise=1.0
    ),
    
    StylePreset.RETRO_GAME_BOY: GenerationParameters(
        steps=18,
        cfg=7.5,
        sampler="euler_ancestral",
        scheduler="karras",
        positive_boost=(
            "authentic game boy style, 4 color palette, "
            "dmg green tones, retro gaming, 1990s aesthetic, "
            "classic sprite design, nostalgic"
        ),
        negative_boost=(
            "modern graphics, full color, gradients, "
            "smooth shading, anti-aliasing, high resolution, "
            "detailed textures"
        ),
        denoise=1.0
    ),
    
    StylePreset.MODERN_PIXEL: GenerationParameters(
        steps=22,
        cfg=9.0,
        sampler="euler_ancestral",
        scheduler="karras",
        positive_boost=(
            "modern pixel art, vibrant colors, "
            "smooth animation frames, contemporary style, "
            "indie game aesthetic, clean professional"
        ),
        negative_boost=(
            "retro limitations, limited palette, "
            "chunky pixels, blurry, 3d, photo realistic"
        ),
        denoise=1.0
    ),
    
    StylePreset.MINIMAL: GenerationParameters(
        steps=15,
        cfg=7.0,
        sampler="euler_ancestral",
        scheduler="karras",
        positive_boost=(
            "minimalist pixel art, simple shapes, "
            "limited colors, geometric, clean, "
            "basic sprite design, straightforward"
        ),
        negative_boost=(
            "complex details, many colors, gradients, "
            "realistic textures, busy design, cluttered"
        ),
        denoise=1.0
    )
}


def get_preset(preset: StylePreset) -> GenerationParameters:
    """
    Get generation parameters for a style preset.
    
    Args:
        preset: Style preset enum
    
    Returns:
        GenerationParameters for the preset
    
    Example:
        params = get_preset(StylePreset.CLEAN_PIXEL_ART)
        workflow = create_workflow(
            positive=base_prompt + params.positive_boost,
            negative=base_negative + params.negative_boost,
            **params.to_dict()
        )
    """
    return STYLE_PRESETS[preset]


def get_preset_by_name(name: str) -> GenerationParameters:
    """
    Get generation parameters by preset name string.
    
    Args:
        name: Preset name (e.g., "clean_pixel_art")
    
    Returns:
        GenerationParameters for the preset
    
    Raises:
        ValueError: If preset name not found
    """
    try:
        preset = StylePreset(name)
        return STYLE_PRESETS[preset]
    except ValueError:
        raise ValueError(
            f"Unknown preset: {name}. "
            f"Available: {[p.value for p in StylePreset]}"
        )


def list_presets() -> Dict[str, Dict[str, Any]]:
    """
    List all available presets with their parameters.
    
    Returns:
        Dictionary mapping preset names to parameter dictionaries
    
    Example:
        {
            "clean_pixel_art": {
                "steps": 20,
                "cfg": 8.0,
                "description": "Clean lines, sharp edges..."
            },
            ...
        }
    """
    return {
        preset.value: {
            **params.to_dict(),
            'description': params.positive_boost,
            'sampler': params.sampler,
            'scheduler': params.scheduler
        }
        for preset, params in STYLE_PRESETS.items()
    }


def merge_with_base_prompts(
    base_positive: str,
    base_negative: str,
    preset: StylePreset
) -> tuple[str, str]:
    """
    Merge base prompts with preset boosts.
    
    Args:
        base_positive: Base positive prompt
        base_negative: Base negative prompt
        preset: Style preset to apply
    
    Returns:
        Tuple of (enhanced_positive, enhanced_negative)
    
    Example:
        positive, negative = merge_with_base_prompts(
            "knight in armor",
            "blurry, 3d",
            StylePreset.CLEAN_PIXEL_ART
        )
        # Returns:
        # "knight in armor, clean lines, sharp edges, ..."
        # "blurry, 3d, anti-aliasing, gradients, ..."
    """
    params = STYLE_PRESETS[preset]
    
    enhanced_positive = f"{base_positive}, {params.positive_boost}"
    enhanced_negative = f"{base_negative}, {params.negative_boost}"
    
    return enhanced_positive, enhanced_negative


def get_optimal_preset_for_description(description: str) -> StylePreset:
    """
    Suggest optimal preset based on user description.
    
    Args:
        description: User's sprite description
    
    Returns:
        Recommended StylePreset
    
    Logic:
        - "retro", "game boy", "classic" → RETRO_GAME_BOY
        - "detailed", "complex", "refined" → DETAILED_SPRITE
        - "simple", "minimal", "basic" → MINIMAL
        - "modern", "indie" → MODERN_PIXEL
        - Default → CLEAN_PIXEL_ART
    """
    description_lower = description.lower()
    
    # Check for keywords
    if any(word in description_lower for word in ['retro', 'game boy', 'classic', 'nostalgic']):
        return StylePreset.RETRO_GAME_BOY
    
    if any(word in description_lower for word in ['detailed', 'complex', 'refined', 'polished']):
        return StylePreset.DETAILED_SPRITE
    
    if any(word in description_lower for word in ['simple', 'minimal', 'basic', 'clean']):
        return StylePreset.MINIMAL
    
    if any(word in description_lower for word in ['modern', 'indie', 'contemporary']):
        return StylePreset.MODERN_PIXEL
    
    # Default to clean pixel art
    return StylePreset.CLEAN_PIXEL_ART
