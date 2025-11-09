"""
Sound Effects Department - Game Boy Sound Generation
Version: 1.0
Platform: Intel Mac (macOS Ventura) + Docker

Generates authentic Game Boy sound effects using procedural synthesis.

Game Boy Sound Chip (4 channels):
- CH1: Pulse wave with sweep
- CH2: Pulse wave
- CH3: Custom waveform
- CH4: Noise
"""

import logging
import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
import hashlib
import wave
import struct

logger = logging.getLogger(__name__)


# ============================================================================
# Game Boy Sound Parameters
# ============================================================================

GB_SAMPLE_RATE = 44100  # High quality output
GB_BIT_DEPTH = 16  # 16-bit for clarity
GB_CHANNELS = 1  # Mono

# Duty cycles for pulse channels (Game Boy has 4 duty cycle options)
DUTY_CYCLES = {
    "12.5%": 0.125,
    "25%": 0.25,
    "50%": 0.5,
    "75%": 0.75
}


# ============================================================================
# Sound Effect Presets
# ============================================================================

SFX_PRESETS = {
    "jump": {
        "channel": "pulse1",
        "frequency_start": 200,
        "frequency_end": 600,
        "duration_ms": 150,
        "duty_cycle": "25%",
        "sweep_type": "up",
        "envelope": {"attack": 0.01, "decay": 0.05, "sustain": 0.6, "release": 0.08}
    },
    "hit": {
        "channel": "noise",
        "duration_ms": 120,
        "noise_type": "white",
        "envelope": {"attack": 0.0, "decay": 0.03, "sustain": 0.3, "release": 0.07}
    },
    "collect": {
        "channel": "pulse2",
        "frequency_start": 880,
        "frequency_end": 1320,
        "duration_ms": 200,
        "duty_cycle": "50%",
        "sweep_type": "up",
        "envelope": {"attack": 0.02, "decay": 0.05, "sustain": 0.7, "release": 0.08}
    },
    "explosion": {
        "channel": "noise",
        "duration_ms": 500,
        "noise_type": "white",
        "envelope": {"attack": 0.0, "decay": 0.15, "sustain": 0.2, "release": 0.35}
    },
    "menu_move": {
        "channel": "pulse1",
        "frequency_start": 440,
        "frequency_end": 440,
        "duration_ms": 50,
        "duty_cycle": "12.5%",
        "envelope": {"attack": 0.01, "decay": 0.02, "sustain": 0.5, "release": 0.02}
    },
    "menu_select": {
        "channel": "pulse1",
        "frequency_start": 660,
        "frequency_end": 880,
        "duration_ms": 100,
        "duty_cycle": "50%",
        "sweep_type": "up",
        "envelope": {"attack": 0.01, "decay": 0.03, "sustain": 0.6, "release": 0.04}
    },
    "powerup": {
        "channel": "pulse1",
        "frequency_start": 440,
        "frequency_end": 880,
        "duration_ms": 300,
        "duty_cycle": "50%",
        "sweep_type": "up",
        "envelope": {"attack": 0.05, "decay": 0.1, "sustain": 0.7, "release": 0.1}
    },
    "damage": {
        "channel": "noise",
        "duration_ms": 200,
        "noise_type": "harsh",
        "envelope": {"attack": 0.0, "decay": 0.05, "sustain": 0.4, "release": 0.1}
    },
    "coin": {
        "channel": "pulse2",
        "frequency_start": 1000,
        "frequency_end": 1500,
        "duration_ms": 180,
        "duty_cycle": "25%",
        "sweep_type": "up",
        "envelope": {"attack": 0.01, "decay": 0.05, "sustain": 0.6, "release": 0.09}
    },
    "game_over": {
        "channel": "pulse1",
        "frequency_start": 440,
        "frequency_end": 220,
        "duration_ms": 800,
        "duty_cycle": "50%",
        "sweep_type": "down",
        "envelope": {"attack": 0.05, "decay": 0.2, "sustain": 0.5, "release": 0.25}
    }
}


@dataclass
class SoundEffect:
    """Represents a generated sound effect."""
    sfx_id: str
    description: str
    category: str
    file_path: str
    duration_ms: int
    format: str
    parameters: Dict[str, Any]
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# Sound Generation Functions
# ============================================================================

def apply_envelope(
    waveform: np.ndarray,
    sample_rate: int,
    attack: float,
    decay: float,
    sustain: float,
    release: float
) -> np.ndarray:
    """
    Apply ADSR envelope to waveform.

    Args:
        waveform: Input waveform
        sample_rate: Sample rate in Hz
        attack: Attack time (0-1, fraction of total duration)
        decay: Decay time (0-1, fraction of total duration)
        sustain: Sustain level (0-1, amplitude)
        release: Release time (0-1, fraction of total duration)

    Returns:
        Waveform with envelope applied
    """
    total_samples = len(waveform)
    envelope = np.ones(total_samples)

    # Calculate sample counts for each phase
    attack_samples = int(total_samples * attack)
    decay_samples = int(total_samples * decay)
    release_samples = int(total_samples * release)
    sustain_samples = total_samples - attack_samples - decay_samples - release_samples

    # Attack phase (0 to 1)
    if attack_samples > 0:
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)

    # Decay phase (1 to sustain level)
    if decay_samples > 0:
        start_idx = attack_samples
        end_idx = start_idx + decay_samples
        envelope[start_idx:end_idx] = np.linspace(1, sustain, decay_samples)

    # Sustain phase (constant at sustain level)
    if sustain_samples > 0:
        start_idx = attack_samples + decay_samples
        end_idx = start_idx + sustain_samples
        envelope[start_idx:end_idx] = sustain

    # Release phase (sustain to 0)
    if release_samples > 0:
        start_idx = total_samples - release_samples
        envelope[start_idx:] = np.linspace(sustain, 0, release_samples)

    return waveform * envelope


def generate_pulse_wave(
    frequency_start: float,
    frequency_end: float,
    duration_ms: int,
    duty_cycle: str = "50%",
    sample_rate: int = GB_SAMPLE_RATE
) -> np.ndarray:
    """
    Generate pulse wave with optional frequency sweep.

    Args:
        frequency_start: Starting frequency in Hz
        frequency_end: Ending frequency in Hz
        duration_ms: Duration in milliseconds
        duty_cycle: Duty cycle (12.5%, 25%, 50%, 75%)
        sample_rate: Sample rate in Hz

    Returns:
        Pulse wave as numpy array
    """
    duration_sec = duration_ms / 1000.0
    num_samples = int(sample_rate * duration_sec)

    # Generate frequency sweep
    frequencies = np.linspace(frequency_start, frequency_end, num_samples)

    # Calculate phase
    phase = np.cumsum(2 * np.pi * frequencies / sample_rate)

    # Generate pulse wave based on duty cycle
    duty = DUTY_CYCLES.get(duty_cycle, 0.5)
    waveform = np.where(np.sin(phase) > (1 - 2 * duty), 1.0, -1.0)

    return waveform


def generate_noise(
    duration_ms: int,
    noise_type: str = "white",
    sample_rate: int = GB_SAMPLE_RATE
) -> np.ndarray:
    """
    Generate noise (Game Boy CH4 style).

    Args:
        duration_ms: Duration in milliseconds
        noise_type: Type of noise (white, harsh, periodic)
        sample_rate: Sample rate in Hz

    Returns:
        Noise waveform as numpy array
    """
    duration_sec = duration_ms / 1000.0
    num_samples = int(sample_rate * duration_sec)

    if noise_type == "white":
        # Standard white noise
        waveform = np.random.uniform(-1.0, 1.0, num_samples)

    elif noise_type == "harsh":
        # Harsher noise with more high frequency content
        waveform = np.random.uniform(-1.0, 1.0, num_samples)
        # Apply high-pass filter effect
        waveform = np.diff(waveform, prepend=0)
        waveform = waveform / np.max(np.abs(waveform))  # Normalize

    elif noise_type == "periodic":
        # Periodic noise (more tonal)
        period = 32  # Short period for Game Boy style
        pattern = np.random.uniform(-1.0, 1.0, period)
        waveform = np.tile(pattern, num_samples // period + 1)[:num_samples]

    else:
        waveform = np.random.uniform(-1.0, 1.0, num_samples)

    return waveform


def generate_wave_channel(
    waveform_type: str,
    frequency: float,
    duration_ms: int,
    sample_rate: int = GB_SAMPLE_RATE
) -> np.ndarray:
    """
    Generate custom waveform (Game Boy CH3 style).

    Args:
        waveform_type: Type of waveform (sine, triangle, sawtooth)
        frequency: Frequency in Hz
        duration_ms: Duration in milliseconds
        sample_rate: Sample rate in Hz

    Returns:
        Custom waveform as numpy array
    """
    duration_sec = duration_ms / 1000.0
    num_samples = int(sample_rate * duration_sec)
    t = np.linspace(0, duration_sec, num_samples)

    if waveform_type == "sine":
        waveform = np.sin(2 * np.pi * frequency * t)
    elif waveform_type == "triangle":
        waveform = 2 * np.abs(2 * (frequency * t - np.floor(frequency * t + 0.5))) - 1
    elif waveform_type == "sawtooth":
        waveform = 2 * (frequency * t - np.floor(frequency * t + 0.5))
    else:
        waveform = np.sin(2 * np.pi * frequency * t)

    return waveform


def save_wav(waveform: np.ndarray, file_path: str, sample_rate: int = GB_SAMPLE_RATE, bit_depth: int = GB_BIT_DEPTH):
    """
    Save waveform as WAV file.

    Args:
        waveform: Audio waveform
        file_path: Output file path
        sample_rate: Sample rate in Hz
        bit_depth: Bit depth (8 or 16)
    """
    # Normalize to [-1, 1]
    waveform = waveform / np.max(np.abs(waveform))

    # Convert to appropriate bit depth
    if bit_depth == 16:
        waveform_int = np.int16(waveform * 32767)
    elif bit_depth == 8:
        waveform_int = np.uint8((waveform + 1) * 127.5)
    else:
        raise ValueError(f"Unsupported bit depth: {bit_depth}")

    # Write WAV file
    with wave.open(file_path, 'w') as wav_file:
        wav_file.setnchannels(GB_CHANNELS)
        wav_file.setsampwidth(bit_depth // 8)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(waveform_int.tobytes())


# ============================================================================
# SFX Department
# ============================================================================

class SFXDepartment:
    """
    Sound Effects Department for Game Boy sound generation.

    Features:
    - Procedural synthesis using Game Boy sound chip constraints
    - Preset-based sound effects
    - Parameter-based generation
    - WAV export
    """

    def __init__(self, output_dir: str = "/app/sfx_outputs"):
        """
        Initialize SFX Department.

        Args:
            output_dir: Directory for storing generated sound effects
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Metadata storage
        self.metadata_file = self.output_dir / "metadata.json"
        self.sfx_registry: Dict[str, SoundEffect] = {}

        # Load existing metadata
        self._load_metadata()

        logger.info(
            f"Initialized SFX Department",
            extra={'output_dir': str(self.output_dir), 'existing_sfx': len(self.sfx_registry)}
        )

    def _load_metadata(self):
        """Load metadata from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    for sfx_id, sfx_data in data.items():
                        self.sfx_registry[sfx_id] = SoundEffect(**sfx_data)
                logger.info(f"Loaded {len(self.sfx_registry)} SFX from metadata")
            except Exception as e:
                logger.error(f"Failed to load SFX metadata: {e}")

    def _save_metadata(self):
        """Save metadata to disk."""
        try:
            data = {sfx_id: sfx.to_dict() for sfx_id, sfx in self.sfx_registry.items()}
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save SFX metadata: {e}")

    def get_presets(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available SFX presets.

        Returns:
            Dictionary of preset configurations
        """
        return SFX_PRESETS.copy()

    async def generate_sfx(
        self,
        description: str,
        category: str,
        duration_ms: Optional[int] = None,
        channel: Optional[str] = None,
        variations: int = 1,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> List[SoundEffect]:
        """
        Generate sound effect from description.

        Args:
            description: Text description of the sound
            category: Category/preset name (jump, hit, collect, etc.)
            duration_ms: Duration in milliseconds (overrides preset)
            channel: Channel type (pulse1, pulse2, wave, noise)
            variations: Number of variations to generate
            custom_params: Custom parameters to override preset

        Returns:
            List of generated SoundEffect objects
        """
        logger.info(
            f"Generating SFX: {description}",
            extra={'category': category, 'variations': variations}
        )

        # Get base parameters from preset
        if category in SFX_PRESETS:
            params = SFX_PRESETS[category].copy()
        else:
            # Default parameters for unknown category
            params = {
                "channel": channel or "pulse1",
                "frequency_start": 440,
                "frequency_end": 440,
                "duration_ms": duration_ms or 200,
                "duty_cycle": "50%",
                "envelope": {"attack": 0.01, "decay": 0.05, "sustain": 0.6, "release": 0.08}
            }

        # Override with custom parameters
        if duration_ms is not None:
            params["duration_ms"] = duration_ms
        if channel is not None:
            params["channel"] = channel
        if custom_params:
            params.update(custom_params)

        # Generate variations
        generated_sfx = []
        for i in range(variations):
            # Create variation in parameters
            var_params = params.copy()
            if variations > 1:
                # Slightly vary frequency for variations
                if "frequency_start" in var_params:
                    var_params["frequency_start"] *= (1.0 + np.random.uniform(-0.1, 0.1))
                if "frequency_end" in var_params:
                    var_params["frequency_end"] *= (1.0 + np.random.uniform(-0.1, 0.1))

            # Generate waveform based on channel
            waveform = self._generate_waveform(var_params)

            # Generate unique ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sfx_hash = hashlib.md5(f"{description}{category}{i}{timestamp}".encode()).hexdigest()[:8]
            sfx_id = f"sfx_{category}_{sfx_hash}"

            # Save WAV file
            filename = f"{sfx_id}.wav"
            file_path = self.output_dir / filename
            save_wav(waveform, str(file_path))

            # Create SoundEffect object
            sfx = SoundEffect(
                sfx_id=sfx_id,
                description=description,
                category=category,
                file_path=str(file_path),
                duration_ms=var_params["duration_ms"],
                format="wav",
                parameters=var_params,
                created_at=datetime.now().isoformat()
            )

            # Register
            self.sfx_registry[sfx_id] = sfx
            generated_sfx.append(sfx)

            logger.info(
                f"Generated SFX: {sfx_id}",
                extra={'file_path': str(file_path), 'variation': i + 1}
            )

        # Save metadata
        self._save_metadata()

        return generated_sfx

    def _generate_waveform(self, params: Dict[str, Any]) -> np.ndarray:
        """
        Generate waveform based on parameters.

        Args:
            params: Sound parameters

        Returns:
            Generated waveform
        """
        channel = params.get("channel", "pulse1")
        duration_ms = params.get("duration_ms", 200)
        envelope_params = params.get("envelope", {})

        # Generate base waveform
        if channel in ["pulse1", "pulse2"]:
            waveform = generate_pulse_wave(
                frequency_start=params.get("frequency_start", 440),
                frequency_end=params.get("frequency_end", 440),
                duration_ms=duration_ms,
                duty_cycle=params.get("duty_cycle", "50%")
            )

        elif channel == "noise":
            waveform = generate_noise(
                duration_ms=duration_ms,
                noise_type=params.get("noise_type", "white")
            )

        elif channel == "wave":
            waveform = generate_wave_channel(
                waveform_type=params.get("waveform_type", "sine"),
                frequency=params.get("frequency", 440),
                duration_ms=duration_ms
            )

        else:
            # Default to pulse wave
            waveform = generate_pulse_wave(
                frequency_start=params.get("frequency_start", 440),
                frequency_end=params.get("frequency_end", 440),
                duration_ms=duration_ms,
                duty_cycle="50%"
            )

        # Apply envelope
        if envelope_params:
            waveform = apply_envelope(
                waveform,
                sample_rate=GB_SAMPLE_RATE,
                attack=envelope_params.get("attack", 0.01),
                decay=envelope_params.get("decay", 0.05),
                sustain=envelope_params.get("sustain", 0.6),
                release=envelope_params.get("release", 0.08)
            )

        return waveform

    def regenerate_sfx(
        self,
        sfx_id: str,
        variation_amount: float = 0.2
    ) -> SoundEffect:
        """
        Regenerate existing SFX with variation.

        Args:
            sfx_id: ID of SFX to regenerate
            variation_amount: Amount of variation to apply (0-1)

        Returns:
            New SoundEffect with variation

        Raises:
            ValueError: If SFX not found
        """
        if sfx_id not in self.sfx_registry:
            raise ValueError(f"SFX {sfx_id} not found")

        original_sfx = self.sfx_registry[sfx_id]

        # Get original parameters
        params = original_sfx.parameters.copy()

        # Apply variations
        if "frequency_start" in params:
            params["frequency_start"] *= (1.0 + np.random.uniform(-variation_amount, variation_amount))
        if "frequency_end" in params:
            params["frequency_end"] *= (1.0 + np.random.uniform(-variation_amount, variation_amount))

        # Generate new waveform
        waveform = self._generate_waveform(params)

        # Generate new ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sfx_hash = hashlib.md5(f"{original_sfx.description}{timestamp}".encode()).hexdigest()[:8]
        new_sfx_id = f"sfx_{original_sfx.category}_{sfx_hash}"

        # Save WAV file
        filename = f"{new_sfx_id}.wav"
        file_path = self.output_dir / filename
        save_wav(waveform, str(file_path))

        # Create new SoundEffect
        new_sfx = SoundEffect(
            sfx_id=new_sfx_id,
            description=f"{original_sfx.description} (variation)",
            category=original_sfx.category,
            file_path=str(file_path),
            duration_ms=params["duration_ms"],
            format="wav",
            parameters=params,
            created_at=datetime.now().isoformat()
        )

        # Register
        self.sfx_registry[new_sfx_id] = new_sfx
        self._save_metadata()

        logger.info(
            f"Regenerated SFX: {sfx_id} → {new_sfx_id}",
            extra={'original': sfx_id, 'new': new_sfx_id}
        )

        return new_sfx

    def list_sfx(self, category_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all generated sound effects.

        Args:
            category_filter: Filter by category (optional)

        Returns:
            List of SFX metadata
        """
        sfx_list = []
        for sfx in self.sfx_registry.values():
            if category_filter is None or sfx.category == category_filter:
                sfx_list.append(sfx.to_dict())

        return sfx_list

    def get_sfx(self, sfx_id: str) -> Optional[SoundEffect]:
        """
        Get SFX by ID.

        Args:
            sfx_id: Sound effect ID

        Returns:
            SoundEffect object or None if not found
        """
        return self.sfx_registry.get(sfx_id)

    def delete_sfx(self, sfx_id: str, delete_file: bool = True) -> bool:
        """
        Delete sound effect.

        Args:
            sfx_id: ID of SFX to delete
            delete_file: Whether to delete the WAV file

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If SFX not found
        """
        if sfx_id not in self.sfx_registry:
            raise ValueError(f"SFX {sfx_id} not found")

        sfx = self.sfx_registry[sfx_id]

        # Delete file if requested
        if delete_file:
            file_path = Path(sfx.file_path)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted SFX file: {file_path}")

        # Remove from registry
        del self.sfx_registry[sfx_id]
        self._save_metadata()

        logger.info(f"Deleted SFX: {sfx_id}")

        return True


# Convenience function for creating department
def create_sfx_department(output_dir: str = "/app/sfx_outputs") -> SFXDepartment:
    """Create SFXDepartment instance."""
    return SFXDepartment(output_dir)
