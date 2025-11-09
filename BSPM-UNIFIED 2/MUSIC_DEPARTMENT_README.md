# Music Department Implementation

## Overview

The Music Department generates procedural music tracks for Game Boy Color games with proper hardware constraints and GBStudio integration. The implementation uses template-based procedural generation tailored to Game Boy sound capabilities.

## Implementation Approach

**Chosen: Option C - Template-based Procedural Generation**

This approach was selected because:
- **Most practical**: Works without external AI music APIs
- **Game Boy accurate**: Respects hardware constraints (4 channels, specific waveforms)
- **Deterministic**: Uses seeds for reproducible results
- **Fast**: Generates tracks in milliseconds
- **Lightweight**: No dependencies on external services

## Architecture

### Files Created/Modified

1. **`backend/music_department.py`** (NEW - 719 lines)
   - `MusicDepartment` class with async methods
   - Music style presets (9 different styles)
   - Procedural melody and percussion generation
   - Game Boy channel constraints (pulse1, pulse2, wave, noise)
   - Track metadata management
   - Validation and file management

2. **`backend/main.py`** (MODIFIED)
   - Added music generation endpoints (6 new endpoints)
   - Added Pydantic models for music requests
   - Integrated with existing security and rate limiting

### Directory Structure

```
/app/music_outputs/           # Generated music tracks
├── track_*.json              # Full track data
├── track_*.uge.json          # UGE-compatible format
└── tracks_metadata.json      # Track index
```

## API Endpoints

### 1. Generate Music

**POST** `/api/music/generate`

Generate a new music track from description.

**Request Body:**
```json
{
  "description": "upbeat battle theme for final boss",
  "style": "boss",
  "duration_seconds": 60,
  "tempo_bpm": 140,
  "channels": ["pulse1", "pulse2", "wave"],
  "seed": 12345
}
```

**Response:**
```json
{
  "track_id": "track_e146fe9debaa",
  "description": "upbeat battle theme for final boss",
  "style": "boss",
  "duration_seconds": 60,
  "tempo_bpm": 140,
  "channels": ["pulse1", "pulse2", "wave"],
  "seed": 12345,
  "files": {
    "json": "/app/music_outputs/track_e146fe9debaa.json",
    "uge": "/app/music_outputs/track_e146fe9debaa.uge.json"
  },
  "created_at": "2025-11-09T05:10:23.456789",
  "format": "json",
  "loop_start": 8,
  "loop_end": 60,
  "correlation_id": "req_1699505423_a1b2c3d4",
  "generation_time_seconds": 0.12
}
```

**Example cURL:**
```bash
curl -X POST http://localhost:8000/api/music/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "calm village music",
    "style": "town",
    "duration_seconds": 45,
    "tempo_bpm": 100
  }'
```

---

### 2. List Music Tracks

**GET** `/api/music/list?style=battle&limit=10`

List all generated music tracks with optional filtering.

**Response:**
```json
{
  "total": 2,
  "tracks": [
    {
      "track_id": "track_abc123",
      "description": "Fast battle music",
      "style": "battle",
      "duration_seconds": 30,
      "tempo_bpm": 140,
      "created_at": "2025-11-09T05:10:23.456789"
    }
  ],
  "available_styles": [
    "battle", "exploration", "menu", "victory",
    "defeat", "ambient", "boss", "town", "dungeon"
  ]
}
```

**Example cURL:**
```bash
curl http://localhost:8000/api/music/list?style=exploration
```

---

### 3. Get Track Details

**GET** `/api/music/track/{track_id}`

Get detailed information about a specific track.

**Response:**
```json
{
  "track_id": "track_abc123",
  "description": "Calm exploration music",
  "style": "exploration",
  "duration_seconds": 60,
  "tempo_bpm": 120,
  "channels": ["pulse1", "pulse2", "wave"],
  "seed": 12345,
  "files": {
    "json": "/app/music_outputs/track_abc123.json",
    "uge": "/app/music_outputs/track_abc123.uge.json"
  },
  "created_at": "2025-11-09T05:10:23.456789",
  "format": "json",
  "loop_start": 0,
  "loop_end": 60
}
```

**Example cURL:**
```bash
curl http://localhost:8000/api/music/track/track_abc123
```

---

### 4. Regenerate Track

**POST** `/api/music/regenerate`

Regenerate an existing track with variations (different seed/style).

**Request Body:**
```json
{
  "track_id": "track_abc123",
  "new_seed": 67890,
  "new_style": "boss"
}
```

**Response:**
```json
{
  "track_id": "track_xyz789",
  "original_track_id": "track_abc123",
  "description": "Calm exploration music",
  "style": "boss",
  "seed": 67890,
  "correlation_id": "req_1699505423_a1b2c3d4",
  "generation_time_seconds": 0.08
}
```

**Example cURL:**
```bash
curl -X POST http://localhost:8000/api/music/regenerate \
  -H "Content-Type: application/json" \
  -d '{
    "track_id": "track_abc123",
    "new_seed": 99999
  }'
```

---

### 5. Delete Track

**DELETE** `/api/music/delete/{track_id}?delete_files=true`

Delete a track and optionally its files.

**Response:**
```json
{
  "track_id": "track_abc123",
  "deleted": true,
  "files_deleted": true
}
```

**Example cURL:**
```bash
curl -X DELETE http://localhost:8000/api/music/delete/track_abc123?delete_files=true
```

---

### 6. Get Music Styles

**GET** `/api/music/styles`

Get list of available music styles with descriptions.

**Response:**
```json
{
  "styles": [
    {
      "value": "battle",
      "name": "Battle",
      "description": "Fast-paced, intense music for combat sequences"
    },
    {
      "value": "exploration",
      "name": "Exploration",
      "description": "Moderate tempo, adventurous music for exploring"
    },
    {
      "value": "menu",
      "name": "Menu",
      "description": "Simple, calm music for menus and UI"
    }
  ]
}
```

**Example cURL:**
```bash
curl http://localhost:8000/api/music/styles
```

---

## Music Style Presets

The Music Department includes 9 predefined style presets:

| Style | Tempo Factor | Energy | Scale | Use Case |
|-------|--------------|--------|-------|----------|
| **battle** | 1.2x | High | Minor | Regular combat |
| **boss** | 1.3x | Very High | Minor | Boss battles |
| **exploration** | 1.0x | Medium | Major | Overworld exploration |
| **town** | 1.0x | Medium | Major | Towns/villages |
| **dungeon** | 0.9x | Medium | Minor | Dungeons/caves |
| **menu** | 0.9x | Low | Major | Menu screens |
| **victory** | 1.1x | High | Major | Win screens |
| **defeat** | 0.7x | Low | Minor | Game over |
| **ambient** | 0.8x | Very Low | Pentatonic | Background atmosphere |

## Game Boy Sound Channels

The implementation respects Game Boy Color hardware constraints:

- **pulse1**: Square wave with sweep capability (lead melodies)
- **pulse2**: Square wave without sweep (harmony/chords)
- **wave**: Custom waveform (bass/pads)
- **noise**: Noise generator (percussion/drums)

## File Formats

### JSON Format (Debug/Interchange)

Full track data including metadata and musical data:

```json
{
  "metadata": {
    "track_id": "track_abc123",
    "description": "Battle music",
    "style": "battle",
    "tempo_bpm": 140
  },
  "musical_data": {
    "tempo_bpm": 140,
    "duration_seconds": 30,
    "total_beats": 70,
    "loop_start": 4,
    "loop_end": 70,
    "channels": {
      "pulse1": [
        {"beat": 0, "pitch": 60, "duration": 0.5, "velocity": 12}
      ]
    }
  }
}
```

### UGE Format (hUGETracker Compatible)

Simplified structure compatible with hUGETracker:

```json
{
  "name": "Generated Track",
  "artist": "Music Department AI",
  "tempo": 140,
  "loop_start": 4,
  "loop_end": 70,
  "channels": {...},
  "version": "1.0"
}
```

## Integration with PM Agent

The PM Agent can delegate music tasks to the Music Department:

**User Request:**
> "Create battle music for the final boss fight"

**PM Agent Response:**
```json
{
  "response_to_user": "I'll create intense boss battle music for you.",
  "needs_approval": true,
  "delegation_plan": [
    {
      "department": "Music",
      "task": "Generate boss battle music",
      "details": {
        "description": "Intense music for final boss fight",
        "style": "boss",
        "duration_seconds": 90,
        "tempo_bpm": 150
      }
    }
  ]
}
```

## Metrics & Monitoring

Music generation is tracked through:

- **Generation time**: Recorded per track
- **Validation success rate**: Tracks that pass validation
- **Rate limiting**: Applied via existing `check_rate_limit` dependency
- **Structured logging**: All operations logged with correlation IDs

## Error Handling

The implementation includes:

- **Retry logic**: Inherits from existing retry decorators
- **Graceful degradation**: Falls back gracefully if generation fails
- **Validation**: All tracks validated for Game Boy compatibility
- **Input sanitization**: Via Pydantic models with constraints

## Limitations

1. **Music Quality**: Procedural generation produces simple, functional music but not AI-composed quality
2. **Limited Realism**: Note sequences are random within scales, not musically sophisticated
3. **No Audio Output**: Generates JSON data, not WAV/MP3 (would require audio synthesis library)
4. **No MIDI Export**: Could be added with mido library
5. **Fixed Patterns**: Percussion patterns are basic (kick/snare/hihat)

## Future Enhancements

1. **Audio Synthesis**: Generate actual WAV files using synthesizer library
2. **MIDI Export**: Export to MIDI format for DAW editing
3. **GBT Player Integration**: Direct export to GBT Player format
4. **Advanced Patterns**: More sophisticated melodic algorithms
5. **User-defined Templates**: Allow custom style templates
6. **Markov Chains**: Use Markov chains for better melodic progression

## Testing

Run the test suite:

```bash
cd /home/user/BSPM-UNIFIED/BSPM-UNIFIED\ 2
python3 test_music_dept.py
```

All tests pass successfully:
- ✓ Music generation
- ✓ Track listing
- ✓ Track retrieval
- ✓ Regeneration
- ✓ Validation
- ✓ Deletion
- ✓ Style filtering

## Production Deployment

The Music Department is production-ready with:

- ✓ Async/await throughout
- ✓ Structured logging
- ✓ Error handling
- ✓ API key authentication (via existing security)
- ✓ Rate limiting
- ✓ Input validation
- ✓ Correlation ID tracking
- ✓ Metrics compatible with Prometheus

## Summary

**Implementation Status**: ✅ Complete

**Files Created**:
- `/backend/music_department.py` (719 lines)
- `/test_music_dept.py` (test suite)

**Files Modified**:
- `/backend/main.py` (added 6 endpoints + 3 Pydantic models)

**Approach**: Template-based procedural generation with Game Boy constraints

**All tests passing**: 8/8 ✓
