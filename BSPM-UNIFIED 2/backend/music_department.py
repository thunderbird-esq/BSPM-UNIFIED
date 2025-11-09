"""
Music Department - Generate and Manage Music Tracks for GBStudio Games
Version: 1.0
Platform: Intel Mac (macOS Ventura) + Docker

Generates music tracks for Game Boy Color games with proper constraints and format support.
"""

import logging
import json
import hashlib
import random
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class MusicStyle(str, Enum):
    """Predefined music style templates for Game Boy games"""
    BATTLE = "battle"
    EXPLORATION = "exploration"
    MENU = "menu"
    VICTORY = "victory"
    DEFEAT = "defeat"
    AMBIENT = "ambient"
    BOSS = "boss"
    TOWN = "town"
    DUNGEON = "dungeon"


class GameBoyChannel(str, Enum):
    """Game Boy sound channels"""
    PULSE1 = "pulse1"  # Square wave with sweep
    PULSE2 = "pulse2"  # Square wave
    WAVE = "wave"      # Custom waveform
    NOISE = "noise"    # Noise/percussion


class MusicDepartment:
    """
    Manages music generation and lifecycle for GBStudio projects.

    Features:
    - Generate music from text descriptions
    - Support Game Boy sound channel constraints
    - Style presets (battle, exploration, menu, etc.)
    - Duration and tempo control
    - Loop point management
    - Track metadata and versioning
    """

    def __init__(self, output_dir: str = "/app/music_outputs"):
        """
        Initialize music department.

        Args:
            output_dir: Directory for music output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.tracks_metadata_file = self.output_dir / "tracks_metadata.json"
        self.tracks_metadata = self._load_metadata()

        logger.info(
            f"Initialized Music Department",
            extra={'output_dir': str(self.output_dir)}
        )

    def _load_metadata(self) -> Dict[str, Any]:
        """Load tracks metadata from disk."""
        if self.tracks_metadata_file.exists():
            try:
                with open(self.tracks_metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load tracks metadata: {e}")
                return {"tracks": {}}
        return {"tracks": {}}

    def _save_metadata(self):
        """Save tracks metadata to disk."""
        try:
            with open(self.tracks_metadata_file, 'w') as f:
                json.dump(self.tracks_metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tracks metadata: {e}")

    async def generate_music(
        self,
        description: str,
        style: MusicStyle = MusicStyle.EXPLORATION,
        duration_seconds: int = 60,
        tempo_bpm: int = 120,
        channels: Optional[List[GameBoyChannel]] = None,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate music track from description.

        Args:
            description: Text description of desired music
            style: Music style preset
            duration_seconds: Duration in seconds
            tempo_bpm: Tempo in beats per minute
            channels: List of Game Boy channels to use
            seed: Random seed for reproducibility

        Returns:
            Dictionary with track metadata and file paths
        """
        # Set random seed if provided
        if seed is None:
            seed = random.randint(0, 999999)
        random.seed(seed)

        # Default to using all channels except noise for melody
        if channels is None:
            channels = [GameBoyChannel.PULSE1, GameBoyChannel.PULSE2, GameBoyChannel.WAVE]

        # Generate unique track ID
        track_id = self._generate_track_id(description, style, seed)

        logger.info(
            f"Generating music track: {description[:50]}...",
            extra={
                'track_id': track_id,
                'style': style,
                'duration_seconds': duration_seconds,
                'tempo_bpm': tempo_bpm,
                'seed': seed
            }
        )

        # Generate musical data based on style
        musical_data = await self._generate_musical_data(
            style=style,
            duration_seconds=duration_seconds,
            tempo_bpm=tempo_bpm,
            channels=channels,
            seed=seed
        )

        # Create track files
        track_files = await self._create_track_files(
            track_id=track_id,
            musical_data=musical_data,
            description=description,
            style=style,
            tempo_bpm=tempo_bpm
        )

        # Create metadata entry
        track_metadata = {
            "track_id": track_id,
            "description": description,
            "style": style,
            "duration_seconds": duration_seconds,
            "tempo_bpm": tempo_bpm,
            "channels": [ch.value for ch in channels],
            "seed": seed,
            "files": track_files,
            "created_at": datetime.utcnow().isoformat(),
            "format": "json",
            "loop_start": musical_data.get("loop_start", 0),
            "loop_end": musical_data.get("loop_end", duration_seconds)
        }

        # Save to metadata
        self.tracks_metadata["tracks"][track_id] = track_metadata
        self._save_metadata()

        logger.info(
            f"Successfully generated music track {track_id}",
            extra={'track_id': track_id, 'files': track_files}
        )

        return track_metadata

    def _generate_track_id(self, description: str, style: str, seed: int) -> str:
        """Generate unique track ID."""
        timestamp = datetime.utcnow().isoformat()
        raw = f"{description}{style}{seed}{timestamp}"
        return f"track_{hashlib.sha256(raw.encode()).hexdigest()[:12]}"

    async def _generate_musical_data(
        self,
        style: MusicStyle,
        duration_seconds: int,
        tempo_bpm: int,
        channels: List[GameBoyChannel],
        seed: int
    ) -> Dict[str, Any]:
        """
        Generate musical data based on style and parameters.

        This uses procedural generation with Game Boy constraints.
        """
        # Calculate musical timing
        beats_per_second = tempo_bpm / 60.0
        total_beats = int(duration_seconds * beats_per_second)

        # Get style parameters
        style_params = self._get_style_parameters(style)

        # Generate note sequences for each channel
        channel_data = {}

        for channel in channels:
            if channel == GameBoyChannel.NOISE:
                # Generate percussion pattern
                channel_data[channel.value] = self._generate_percussion(
                    total_beats=total_beats,
                    style_params=style_params
                )
            else:
                # Generate melodic pattern
                channel_data[channel.value] = self._generate_melody(
                    total_beats=total_beats,
                    channel=channel,
                    style_params=style_params
                )

        # Determine loop points (most tracks loop the main section)
        intro_length = style_params.get("intro_beats", 0)
        loop_start = intro_length
        loop_end = total_beats

        return {
            "tempo_bpm": tempo_bpm,
            "duration_seconds": duration_seconds,
            "total_beats": total_beats,
            "loop_start": loop_start,
            "loop_end": loop_end,
            "channels": channel_data,
            "style": style,
            "seed": seed
        }

    def _get_style_parameters(self, style: MusicStyle) -> Dict[str, Any]:
        """Get musical parameters for a given style."""
        style_map = {
            MusicStyle.BATTLE: {
                "scale": "minor",
                "tempo_factor": 1.2,
                "note_density": "high",
                "intro_beats": 4,
                "energy": "high",
                "chord_progression": ["i", "VI", "III", "VII"]
            },
            MusicStyle.EXPLORATION: {
                "scale": "major",
                "tempo_factor": 1.0,
                "note_density": "medium",
                "intro_beats": 8,
                "energy": "medium",
                "chord_progression": ["I", "V", "vi", "IV"]
            },
            MusicStyle.MENU: {
                "scale": "major",
                "tempo_factor": 0.9,
                "note_density": "low",
                "intro_beats": 0,
                "energy": "low",
                "chord_progression": ["I", "IV", "V", "I"]
            },
            MusicStyle.VICTORY: {
                "scale": "major",
                "tempo_factor": 1.1,
                "note_density": "high",
                "intro_beats": 2,
                "energy": "high",
                "chord_progression": ["I", "IV", "V", "I"]
            },
            MusicStyle.DEFEAT: {
                "scale": "minor",
                "tempo_factor": 0.7,
                "note_density": "low",
                "intro_beats": 0,
                "energy": "low",
                "chord_progression": ["i", "iv", "V", "i"]
            },
            MusicStyle.AMBIENT: {
                "scale": "pentatonic",
                "tempo_factor": 0.8,
                "note_density": "low",
                "intro_beats": 0,
                "energy": "very_low",
                "chord_progression": ["I", "IV", "I", "V"]
            },
            MusicStyle.BOSS: {
                "scale": "minor",
                "tempo_factor": 1.3,
                "note_density": "very_high",
                "intro_beats": 8,
                "energy": "very_high",
                "chord_progression": ["i", "VII", "VI", "V"]
            },
            MusicStyle.TOWN: {
                "scale": "major",
                "tempo_factor": 1.0,
                "note_density": "medium",
                "intro_beats": 4,
                "energy": "medium",
                "chord_progression": ["I", "V", "vi", "iii"]
            },
            MusicStyle.DUNGEON: {
                "scale": "minor",
                "tempo_factor": 0.9,
                "note_density": "medium",
                "intro_beats": 4,
                "energy": "medium",
                "chord_progression": ["i", "iv", "v", "i"]
            }
        }

        return style_map.get(style, style_map[MusicStyle.EXPLORATION])

    def _generate_melody(
        self,
        total_beats: int,
        channel: GameBoyChannel,
        style_params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate a melodic sequence for a channel.

        Returns list of notes with timing and pitch.
        """
        notes = []
        scale = self._get_scale(style_params["scale"])

        # Note density affects how many notes we generate
        density_map = {
            "very_low": 0.25,
            "low": 0.5,
            "medium": 1.0,
            "high": 2.0,
            "very_high": 4.0
        }
        notes_per_beat = density_map.get(style_params["note_density"], 1.0)

        current_beat = 0
        while current_beat < total_beats:
            # Generate note
            pitch = random.choice(scale)
            duration = random.choice([0.25, 0.5, 1.0, 2.0])  # Beat fractions

            notes.append({
                "beat": current_beat,
                "pitch": pitch,
                "duration": duration,
                "velocity": random.randint(8, 15)  # Game Boy volume (0-15)
            })

            current_beat += duration

        return notes

    def _generate_percussion(
        self,
        total_beats: int,
        style_params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate percussion pattern for noise channel.
        """
        pattern = []
        energy = style_params["energy"]

        # Simple kick/snare pattern
        for beat in range(total_beats):
            # Kick on beats 1 and 3 (0 and 2 in zero-indexed)
            if beat % 4 == 0 or beat % 4 == 2:
                pattern.append({
                    "beat": beat,
                    "type": "kick",
                    "duration": 0.25,
                    "velocity": 15
                })

            # Hi-hat on all beats for high energy
            if energy in ["high", "very_high"]:
                pattern.append({
                    "beat": beat,
                    "type": "hihat",
                    "duration": 0.25,
                    "velocity": 10
                })

        return pattern

    def _get_scale(self, scale_type: str) -> List[int]:
        """
        Get MIDI note numbers for a scale.

        Game Boy typically uses octaves 3-5 (MIDI notes 48-84).
        """
        base_note = 60  # Middle C

        scales = {
            "major": [0, 2, 4, 5, 7, 9, 11, 12, 14, 16],
            "minor": [0, 2, 3, 5, 7, 8, 10, 12, 14, 15],
            "pentatonic": [0, 2, 4, 7, 9, 12, 14, 16, 19, 21]
        }

        scale_intervals = scales.get(scale_type, scales["major"])
        return [base_note + interval for interval in scale_intervals]

    async def _create_track_files(
        self,
        track_id: str,
        musical_data: Dict[str, Any],
        description: str,
        style: str,
        tempo_bpm: int
    ) -> Dict[str, str]:
        """
        Create track files in various formats.

        Returns dict with file paths.
        """
        files = {}

        # JSON format (for debugging and interchange)
        json_file = self.output_dir / f"{track_id}.json"
        with open(json_file, 'w') as f:
            json.dump({
                "metadata": {
                    "track_id": track_id,
                    "description": description,
                    "style": style,
                    "tempo_bpm": tempo_bpm
                },
                "musical_data": musical_data
            }, f, indent=2)
        files["json"] = str(json_file)

        # UGE-compatible format (simplified JSON structure)
        uge_file = self.output_dir / f"{track_id}.uge.json"
        uge_data = self._convert_to_uge_format(musical_data, tempo_bpm)
        with open(uge_file, 'w') as f:
            json.dump(uge_data, f, indent=2)
        files["uge"] = str(uge_file)

        logger.info(
            f"Created track files for {track_id}",
            extra={'track_id': track_id, 'files': list(files.keys())}
        )

        return files

    def _convert_to_uge_format(
        self,
        musical_data: Dict[str, Any],
        tempo_bpm: int
    ) -> Dict[str, Any]:
        """
        Convert musical data to UGE-compatible format.

        This is a simplified representation compatible with hUGETracker.
        """
        return {
            "name": "Generated Track",
            "artist": "Music Department AI",
            "tempo": tempo_bpm,
            "loop_start": musical_data.get("loop_start", 0),
            "loop_end": musical_data.get("loop_end", 64),
            "channels": musical_data.get("channels", {}),
            "version": "1.0"
        }

    async def list_tracks(
        self,
        style_filter: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List generated tracks with optional filtering.

        Args:
            style_filter: Filter by music style
            limit: Maximum number of tracks to return

        Returns:
            List of track metadata
        """
        tracks = list(self.tracks_metadata["tracks"].values())

        # Filter by style if requested
        if style_filter:
            tracks = [t for t in tracks if t["style"] == style_filter]

        # Sort by creation date (newest first)
        tracks.sort(key=lambda t: t["created_at"], reverse=True)

        # Apply limit
        tracks = tracks[:limit]

        return tracks

    async def get_track(self, track_id: str) -> Optional[Dict[str, Any]]:
        """
        Get track metadata by ID.

        Args:
            track_id: Track ID

        Returns:
            Track metadata or None if not found
        """
        return self.tracks_metadata["tracks"].get(track_id)

    async def delete_track(self, track_id: str, delete_files: bool = True) -> bool:
        """
        Delete track and optionally its files.

        Args:
            track_id: Track ID to delete
            delete_files: If True, also delete files from disk

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If track not found
        """
        track = await self.get_track(track_id)

        if not track:
            raise ValueError(f"Track {track_id} not found")

        # Delete files if requested
        if delete_files and "files" in track:
            for file_path in track["files"].values():
                try:
                    Path(file_path).unlink(missing_ok=True)
                    logger.info(f"Deleted file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete file {file_path}: {e}")

        # Remove from metadata
        del self.tracks_metadata["tracks"][track_id]
        self._save_metadata()

        logger.info(
            f"Deleted track {track_id}",
            extra={'track_id': track_id, 'files_deleted': delete_files}
        )

        return True

    async def regenerate_track(
        self,
        track_id: str,
        new_seed: Optional[int] = None,
        new_style: Optional[MusicStyle] = None
    ) -> Dict[str, Any]:
        """
        Regenerate an existing track with variations.

        Args:
            track_id: Original track ID
            new_seed: New random seed (if None, generates random)
            new_style: New style (if None, uses original)

        Returns:
            New track metadata
        """
        original_track = await self.get_track(track_id)

        if not original_track:
            raise ValueError(f"Track {track_id} not found")

        # Use original parameters with optional overrides
        return await self.generate_music(
            description=original_track["description"],
            style=MusicStyle(new_style) if new_style else MusicStyle(original_track["style"]),
            duration_seconds=original_track["duration_seconds"],
            tempo_bpm=original_track["tempo_bpm"],
            channels=[GameBoyChannel(ch) for ch in original_track["channels"]],
            seed=new_seed
        )

    def validate_track(self, track_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate track data for Game Boy compatibility.

        Args:
            track_data: Track data to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required fields
        required_fields = ["tempo_bpm", "duration_seconds", "channels"]
        for field in required_fields:
            if field not in track_data:
                errors.append(f"Missing required field: {field}")

        # Validate tempo range (Game Boy typical range)
        tempo = track_data.get("tempo_bpm", 0)
        if tempo < 40 or tempo > 240:
            errors.append(f"Tempo {tempo} BPM out of range (40-240)")

        # Validate duration (not too long for memory constraints)
        duration = track_data.get("duration_seconds", 0)
        if duration > 300:  # 5 minutes max
            errors.append(f"Duration {duration}s exceeds maximum (300s)")

        # Validate channel count (max 4 channels on Game Boy)
        channels = track_data.get("channels", {})
        if len(channels) > 4:
            errors.append(f"Too many channels ({len(channels)}), max is 4")

        is_valid = len(errors) == 0

        return is_valid, errors


# Convenience function for creating department instance
def create_music_department(output_dir: str = "/app/music_outputs") -> MusicDepartment:
    """Create MusicDepartment instance."""
    return MusicDepartment(output_dir=output_dir)
