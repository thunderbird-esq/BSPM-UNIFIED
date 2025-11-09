"""
Test Suite: Style Presets
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Tests for sprite generation style presets.
"""

import pytest
from backend.style_presets import (
    StylePreset, GenerationParameters, STYLE_PRESETS,
    get_preset, get_preset_by_name, list_presets,
    merge_with_base_prompts, get_optimal_preset_for_description
)


class TestGenerationParameters:
    """Test GenerationParameters dataclass."""

    def test_creation(self):
        """Create GenerationParameters."""
        params = GenerationParameters(
            steps=20,
            cfg=8.0,
            sampler="euler_ancestral",
            scheduler="karras",
            positive_boost="clean pixel art",
            negative_boost="blurry, 3d",
            denoise=1.0
        )

        assert params.steps == 20
        assert params.cfg == 8.0
        assert params.sampler == "euler_ancestral"

    def test_to_dict(self):
        """Convert to dictionary for workflow."""
        params = GenerationParameters(
            steps=25,
            cfg=10.0,
            sampler="euler_ancestral",
            scheduler="karras",
            positive_boost="test",
            negative_boost="test",
            denoise=0.9
        )

        result = params.to_dict()

        assert result['steps'] == 25
        assert result['cfg'] == 10.0
        assert result['sampler_name'] == "euler_ancestral"
        assert result['scheduler'] == "karras"
        assert result['denoise'] == 0.9


class TestStylePresets:
    """Test style preset enumeration."""

    def test_all_presets_defined(self):
        """All preset enum values have definitions."""
        for preset in StylePreset:
            assert preset in STYLE_PRESETS

    def test_clean_pixel_art_preset(self):
        """Clean pixel art preset has correct parameters."""
        params = STYLE_PRESETS[StylePreset.CLEAN_PIXEL_ART]

        assert params.steps == 20
        assert params.cfg == 8.0
        assert "clean lines" in params.positive_boost.lower()
        assert "anti-aliasing" in params.negative_boost.lower()

    def test_detailed_sprite_preset(self):
        """Detailed sprite preset has higher steps."""
        params = STYLE_PRESETS[StylePreset.DETAILED_SPRITE]

        assert params.steps == 25
        assert params.cfg == 10.0
        assert "detailed" in params.positive_boost.lower()

    def test_retro_game_boy_preset(self):
        """Retro Game Boy preset emphasizes 4-color palette."""
        params = STYLE_PRESETS[StylePreset.RETRO_GAME_BOY]

        assert "4 color palette" in params.positive_boost.lower()
        assert "game boy" in params.positive_boost.lower()

    def test_modern_pixel_preset(self):
        """Modern pixel preset allows more colors."""
        params = STYLE_PRESETS[StylePreset.MODERN_PIXEL]

        assert "modern" in params.positive_boost.lower()
        assert "vibrant colors" in params.positive_boost.lower()

    def test_minimal_preset(self):
        """Minimal preset has fewer steps."""
        params = STYLE_PRESETS[StylePreset.MINIMAL]

        assert params.steps == 15
        assert "minimalist" in params.positive_boost.lower()


class TestGetPreset:
    """Test get_preset function."""

    def test_get_preset_by_enum(self):
        """Get preset by enum value."""
        params = get_preset(StylePreset.CLEAN_PIXEL_ART)

        assert isinstance(params, GenerationParameters)
        assert params.steps == 20

    def test_get_all_presets(self):
        """Get all presets without error."""
        for preset in StylePreset:
            params = get_preset(preset)
            assert isinstance(params, GenerationParameters)


class TestGetPresetByName:
    """Test get_preset_by_name function."""

    def test_get_by_valid_name(self):
        """Get preset by string name."""
        params = get_preset_by_name("clean_pixel_art")

        assert isinstance(params, GenerationParameters)
        assert params.steps == 20

    def test_get_by_invalid_name_raises(self):
        """Invalid name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown preset"):
            get_preset_by_name("nonexistent_preset")

    def test_error_message_shows_available(self):
        """Error message lists available presets."""
        try:
            get_preset_by_name("invalid")
        except ValueError as e:
            assert "available" in str(e).lower()
            assert "clean_pixel_art" in str(e).lower()


class TestListPresets:
    """Test list_presets function."""

    def test_returns_all_presets(self):
        """List all available presets."""
        presets = list_presets()

        assert len(presets) == len(StylePreset)
        assert "clean_pixel_art" in presets
        assert "retro_game_boy" in presets

    def test_preset_structure(self):
        """Each preset has expected structure."""
        presets = list_presets()

        for name, data in presets.items():
            assert 'steps' in data
            assert 'cfg' in data
            assert 'sampler' in data
            assert 'scheduler' in data
            assert 'description' in data
            assert 'denoise' in data

    def test_description_is_positive_boost(self):
        """Description comes from positive_boost."""
        presets = list_presets()

        clean_art = presets['clean_pixel_art']
        assert "clean lines" in clean_art['description'].lower()


class TestMergeWithBasePrompts:
    """Test merge_with_base_prompts function."""

    def test_merge_positive_prompts(self):
        """Merge positive prompts."""
        positive, negative = merge_with_base_prompts(
            "knight in armor",
            "blurry",
            StylePreset.CLEAN_PIXEL_ART
        )

        assert "knight in armor" in positive
        assert "clean lines" in positive.lower()

    def test_merge_negative_prompts(self):
        """Merge negative prompts."""
        positive, negative = merge_with_base_prompts(
            "knight",
            "blurry, 3d",
            StylePreset.CLEAN_PIXEL_ART
        )

        assert "blurry" in negative
        assert "3d" in negative
        assert "anti-aliasing" in negative.lower()

    def test_different_presets_different_boosts(self):
        """Different presets add different boosts."""
        pos1, neg1 = merge_with_base_prompts(
            "sprite",
            "bad",
            StylePreset.CLEAN_PIXEL_ART
        )
        pos2, neg2 = merge_with_base_prompts(
            "sprite",
            "bad",
            StylePreset.RETRO_GAME_BOY
        )

        # Should have different boost content
        assert pos1 != pos2
        assert neg1 != neg2

    def test_preserves_base_prompts(self):
        """Base prompts are preserved."""
        positive, negative = merge_with_base_prompts(
            "unique character description",
            "specific negative term",
            StylePreset.MINIMAL
        )

        assert "unique character description" in positive
        assert "specific negative term" in negative


class TestGetOptimalPreset:
    """Test get_optimal_preset_for_description function."""

    def test_retro_keywords(self):
        """Retro keywords select RETRO_GAME_BOY."""
        preset = get_optimal_preset_for_description(
            "Create a retro game boy style knight"
        )
        assert preset == StylePreset.RETRO_GAME_BOY

        preset = get_optimal_preset_for_description(
            "Classic nostalgic pixel art"
        )
        assert preset == StylePreset.RETRO_GAME_BOY

    def test_detailed_keywords(self):
        """Detailed keywords select DETAILED_SPRITE."""
        preset = get_optimal_preset_for_description(
            "Create a detailed refined knight sprite"
        )
        assert preset == StylePreset.DETAILED_SPRITE

        preset = get_optimal_preset_for_description(
            "Complex polished character"
        )
        assert preset == StylePreset.DETAILED_SPRITE

    def test_minimal_keywords(self):
        """Minimal keywords select MINIMAL."""
        preset = get_optimal_preset_for_description(
            "Simple basic sprite design"
        )
        assert preset == StylePreset.MINIMAL

        preset = get_optimal_preset_for_description(
            "Minimalist clean character"
        )
        assert preset == StylePreset.MINIMAL

    def test_modern_keywords(self):
        """Modern keywords select MODERN_PIXEL."""
        preset = get_optimal_preset_for_description(
            "Modern indie game sprite"
        )
        assert preset == StylePreset.MODERN_PIXEL

        preset = get_optimal_preset_for_description(
            "Contemporary pixel art style"
        )
        assert preset == StylePreset.MODERN_PIXEL

    def test_default_fallback(self):
        """No keywords defaults to CLEAN_PIXEL_ART."""
        preset = get_optimal_preset_for_description(
            "Generic knight character"
        )
        assert preset == StylePreset.CLEAN_PIXEL_ART

    def test_case_insensitive(self):
        """Keyword matching is case insensitive."""
        preset1 = get_optimal_preset_for_description("RETRO game boy")
        preset2 = get_optimal_preset_for_description("retro GAME BOY")

        assert preset1 == preset2 == StylePreset.RETRO_GAME_BOY


class TestPresetConsistency:
    """Test preset consistency and validity."""

    def test_all_presets_have_positive_boost(self):
        """All presets have non-empty positive boost."""
        for preset, params in STYLE_PRESETS.items():
            assert params.positive_boost
            assert len(params.positive_boost) > 10

    def test_all_presets_have_negative_boost(self):
        """All presets have non-empty negative boost."""
        for preset, params in STYLE_PRESETS.items():
            assert params.negative_boost
            assert len(params.negative_boost) > 10

    def test_all_use_euler_ancestral(self):
        """All presets use euler_ancestral sampler."""
        for preset, params in STYLE_PRESETS.items():
            assert params.sampler == "euler_ancestral"

    def test_all_use_karras_scheduler(self):
        """All presets use karras scheduler."""
        for preset, params in STYLE_PRESETS.items():
            assert params.scheduler == "karras"

    def test_reasonable_step_counts(self):
        """All presets have reasonable step counts."""
        for preset, params in STYLE_PRESETS.items():
            assert 10 <= params.steps <= 30

    def test_reasonable_cfg_values(self):
        """All presets have reasonable CFG values."""
        for preset, params in STYLE_PRESETS.items():
            assert 5.0 <= params.cfg <= 15.0

    def test_denoise_is_one(self):
        """All presets use full denoise."""
        for preset, params in STYLE_PRESETS.items():
            assert params.denoise == 1.0


# Run with: pytest tests/test_style_presets.py -v
# Run with coverage: pytest tests/test_style_presets.py --cov=backend.style_presets
