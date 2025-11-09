# SFX Department - API Examples and Usage Guide

## Implementation Summary

**Status**: ✅ COMPLETE

**Generation Approach**: Procedural Synthesis (Option A)
- Pure Python implementation using NumPy
- Game Boy sound chip emulation (4 channels)
- No external audio generation services required
- Authentic 8-bit sound characteristics

**Files Created**:
1. `/backend/sfx_department.py` - Main SFX generation engine (752 lines)
2. `/backend/main.py` - API endpoints added (7 new routes)
3. `/test_sfx_department.py` - Comprehensive test suite

**Output Directory**: `/app/sfx_outputs/`

---

## Game Boy Sound Capabilities

### Channel Types

1. **PULSE1 (CH1)** - Pulse wave with frequency sweep
   - Duty cycles: 12.5%, 25%, 50%, 75%
   - Frequency sweep (up/down)
   - Envelope (ADSR)
   - Best for: Jumps, beeps, melodic sounds

2. **PULSE2 (CH2)** - Pulse wave
   - Same as PULSE1 but no sweep
   - Duty cycles: 12.5%, 25%, 50%, 75%
   - Envelope (ADSR)
   - Best for: Coins, menu sounds, secondary tones

3. **WAVE (CH3)** - Custom waveform
   - Programmable waveform
   - Types: sine, triangle, sawtooth
   - Best for: Bass, special effects

4. **NOISE (CH4)** - Noise generator
   - White noise, harsh noise, periodic noise
   - Envelope (ADSR)
   - Best for: Explosions, hits, crashes

---

## Available Presets

The system includes 10 built-in presets:

| Preset       | Channel | Duration | Freq Start | Freq End | Description                    |
|--------------|---------|----------|------------|----------|--------------------------------|
| jump         | pulse1  | 150ms    | 200 Hz     | 600 Hz   | Classic platformer jump        |
| hit          | noise   | 120ms    | -          | -        | Enemy hit/impact               |
| collect      | pulse2  | 200ms    | 880 Hz     | 1320 Hz  | Item collection                |
| explosion    | noise   | 500ms    | -          | -        | Large explosion                |
| menu_move    | pulse1  | 50ms     | 440 Hz     | 440 Hz   | Menu cursor movement           |
| menu_select  | pulse1  | 100ms    | 660 Hz     | 880 Hz   | Menu selection confirm         |
| powerup      | pulse1  | 300ms    | 440 Hz     | 880 Hz   | Power-up collection            |
| damage       | noise   | 200ms    | -          | -        | Player damage/hurt             |
| coin         | pulse2  | 180ms    | 1000 Hz    | 1500 Hz  | Coin collection                |
| game_over    | pulse1  | 800ms    | 440 Hz     | 220 Hz   | Game over sound (descending)   |

---

## API Endpoints

### 1. Generate Sound Effect

**Endpoint**: `POST /api/sfx/generate`

**Description**: Generate a new sound effect from description and parameters.

**Request Body**:
```json
{
  "description": "classic platformer jump",
  "category": "jump",
  "duration_ms": 150,
  "channel": "pulse1",
  "variations": 1,
  "custom_params": null
}
```

**Parameters**:
- `description` (string, required): Text description of the sound
- `category` (string, required): Preset category name
- `duration_ms` (integer, optional): Duration in milliseconds (overrides preset)
- `channel` (string, optional): Channel type (pulse1, pulse2, wave, noise)
- `variations` (integer, 1-5): Number of variations to generate
- `custom_params` (object, optional): Custom parameters to override preset

**Response** (single variation):
```json
{
  "sfx_id": "sfx_jump_abc123",
  "description": "classic platformer jump",
  "category": "jump",
  "file_path": "/app/sfx_outputs/sfx_jump_abc123.wav",
  "duration_ms": 150,
  "format": "wav",
  "parameters": {
    "channel": "pulse1",
    "frequency_start": 200,
    "frequency_end": 600,
    "duty_cycle": "25%",
    "sweep_type": "up",
    "envelope": {
      "attack": 0.01,
      "decay": 0.05,
      "sustain": 0.6,
      "release": 0.08
    }
  },
  "created_at": "2025-11-09T05:08:40.867094"
}
```

**Response** (multiple variations):
```json
{
  "count": 3,
  "sfx": [
    { "sfx_id": "sfx_jump_abc123", "...": "..." },
    { "sfx_id": "sfx_jump_def456", "...": "..." },
    { "sfx_id": "sfx_jump_ghi789", "...": "..." }
  ]
}
```

**Example cURL**:
```bash
curl -X POST http://localhost:8000/api/sfx/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "classic platformer jump",
    "category": "jump",
    "duration_ms": 150,
    "channel": "pulse1"
  }'
```

---

### 2. Get Presets

**Endpoint**: `GET /api/sfx/presets`

**Description**: List all available sound effect presets.

**Response**:
```json
{
  "presets": {
    "jump": {
      "channel": "pulse1",
      "frequency_start": 200,
      "frequency_end": 600,
      "duration_ms": 150,
      "duty_cycle": "25%",
      "sweep_type": "up",
      "envelope": {
        "attack": 0.01,
        "decay": 0.05,
        "sustain": 0.6,
        "release": 0.08
      }
    },
    "coin": {
      "channel": "pulse2",
      "frequency_start": 1000,
      "frequency_end": 1500,
      "duration_ms": 180,
      "duty_cycle": "25%",
      "sweep_type": "up",
      "envelope": {
        "attack": 0.01,
        "decay": 0.05,
        "sustain": 0.6,
        "release": 0.09
      }
    }
  },
  "categories": ["jump", "hit", "collect", "explosion", "menu_move", "menu_select", "powerup", "damage", "coin", "game_over"]
}
```

**Example cURL**:
```bash
curl http://localhost:8000/api/sfx/presets
```

---

### 3. Regenerate with Variation

**Endpoint**: `POST /api/sfx/regenerate`

**Description**: Regenerate an existing SFX with variation.

**Request Body**:
```json
{
  "sfx_id": "sfx_jump_abc123",
  "variation_amount": 0.2
}
```

**Parameters**:
- `sfx_id` (string, required): ID of SFX to regenerate
- `variation_amount` (float, 0.0-1.0): Amount of variation (0.2 = 20% variation)

**Response**:
```json
{
  "sfx_id": "sfx_jump_xyz789",
  "description": "classic platformer jump (variation)",
  "category": "jump",
  "file_path": "/app/sfx_outputs/sfx_jump_xyz789.wav",
  "duration_ms": 150,
  "format": "wav",
  "parameters": {
    "channel": "pulse1",
    "frequency_start": 214.5,
    "frequency_end": 612.3,
    "duty_cycle": "25%",
    "sweep_type": "up",
    "envelope": { "...": "..." }
  },
  "created_at": "2025-11-09T05:10:15.123456"
}
```

**Example cURL**:
```bash
curl -X POST http://localhost:8000/api/sfx/regenerate \
  -H "Content-Type: application/json" \
  -d '{
    "sfx_id": "sfx_jump_abc123",
    "variation_amount": 0.2
  }'
```

---

### 4. List Sound Effects

**Endpoint**: `GET /api/sfx/list`

**Description**: List all generated sound effects with optional category filter.

**Query Parameters**:
- `category` (string, optional): Filter by category

**Response**:
```json
{
  "total": 8,
  "sfx": [
    {
      "sfx_id": "sfx_jump_abc123",
      "description": "classic platformer jump",
      "category": "jump",
      "file_path": "/app/sfx_outputs/sfx_jump_abc123.wav",
      "duration_ms": 150,
      "format": "wav",
      "created_at": "2025-11-09T05:08:40.867094"
    }
  ]
}
```

**Example cURL**:
```bash
# List all
curl http://localhost:8000/api/sfx/list

# Filter by category
curl http://localhost:8000/api/sfx/list?category=jump
```

---

### 5. Get Sound Effect Details

**Endpoint**: `GET /api/sfx/{sfx_id}`

**Description**: Get detailed information about a specific sound effect.

**Response**:
```json
{
  "sfx_id": "sfx_jump_abc123",
  "description": "classic platformer jump",
  "category": "jump",
  "file_path": "/app/sfx_outputs/sfx_jump_abc123.wav",
  "duration_ms": 150,
  "format": "wav",
  "parameters": {
    "channel": "pulse1",
    "frequency_start": 200,
    "frequency_end": 600,
    "duty_cycle": "25%",
    "sweep_type": "up",
    "envelope": {
      "attack": 0.01,
      "decay": 0.05,
      "sustain": 0.6,
      "release": 0.08
    }
  },
  "created_at": "2025-11-09T05:08:40.867094"
}
```

**Example cURL**:
```bash
curl http://localhost:8000/api/sfx/sfx_jump_abc123
```

---

### 6. Delete Sound Effect

**Endpoint**: `DELETE /api/sfx/delete/{sfx_id}`

**Description**: Delete a sound effect.

**Query Parameters**:
- `delete_file` (boolean, default=true): Whether to delete the WAV file

**Response**:
```json
{
  "sfx_id": "sfx_jump_abc123",
  "deleted": true,
  "file_deleted": true
}
```

**Example cURL**:
```bash
# Delete with file
curl -X DELETE http://localhost:8000/api/sfx/delete/sfx_jump_abc123

# Delete without file
curl -X DELETE http://localhost:8000/api/sfx/delete/sfx_jump_abc123?delete_file=false
```

---

### 7. Download Sound Effect

**Endpoint**: `GET /api/sfx/download/{sfx_id}`

**Description**: Download the WAV file for a sound effect.

**Response**: Binary WAV file

**Example cURL**:
```bash
curl http://localhost:8000/api/sfx/download/sfx_jump_abc123 \
  -o jump_sound.wav
```

---

## Usage Examples

### Example 1: Generate a Jump Sound

```bash
curl -X POST http://localhost:8000/api/sfx/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "classic platformer jump",
    "category": "jump",
    "duration_ms": 150,
    "channel": "pulse1"
  }'
```

**Output**:
- File: `/app/sfx_outputs/sfx_jump_0d93de08.wav`
- Size: 13.3 KB (13,274 bytes)
- Duration: 150ms
- Frequency sweep: 200 Hz → 600 Hz

---

### Example 2: Generate Coin Collection Sound

```bash
curl -X POST http://localhost:8000/api/sfx/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "coin collection sound",
    "category": "coin",
    "duration_ms": 180,
    "channel": "pulse2"
  }'
```

**Output**:
- File: `/app/sfx_outputs/sfx_coin_ebdb1dd1.wav`
- Size: 15.9 KB (15,920 bytes)
- Duration: 180ms
- Frequency sweep: 1000 Hz → 1500 Hz

---

### Example 3: Generate Enemy Hit Sound

```bash
curl -X POST http://localhost:8000/api/sfx/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "enemy hit sound",
    "category": "hit",
    "duration_ms": 120,
    "channel": "noise"
  }'
```

**Output**:
- File: `/app/sfx_outputs/sfx_hit_59058818.wav`
- Size: 10.6 KB (10,628 bytes)
- Duration: 120ms
- Type: White noise with envelope

---

### Example 4: Generate Multiple Variations

```bash
curl -X POST http://localhost:8000/api/sfx/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "platformer jump with variations",
    "category": "jump",
    "duration_ms": 150,
    "channel": "pulse1",
    "variations": 3
  }'
```

**Output**: 3 files with slightly different frequency sweeps
- `sfx_jump_506897b4.wav` - Freq: 214.40 Hz → 604.94 Hz
- `sfx_jump_73579cde.wav` - Freq: 181.01 Hz → 542.78 Hz
- `sfx_jump_229df654.wav` - Freq: 217.21 Hz → 612.43 Hz

---

### Example 5: Custom Parameters

```bash
curl -X POST http://localhost:8000/api/sfx/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "custom laser sound",
    "category": "powerup",
    "duration_ms": 250,
    "channel": "pulse1",
    "custom_params": {
      "frequency_start": 800,
      "frequency_end": 200,
      "duty_cycle": "12.5%",
      "envelope": {
        "attack": 0.0,
        "decay": 0.1,
        "sustain": 0.4,
        "release": 0.15
      }
    }
  }'
```

**Output**: Custom laser sound with descending pitch (800 Hz → 200 Hz)

---

## Test Results

### Test Suite Execution

```
✓ SFX Department initialized successfully
✓ 10 presets available
✓ 4 test sound effects generated
✓ Regeneration with variation successful
✓ Category filtering working
✓ Multiple variations generated (3x jump sounds)
✓ All tests passed
```

### Generated Test Files

| File                       | Size    | Category | Duration | Characteristics              |
|----------------------------|---------|----------|----------|------------------------------|
| sfx_jump_0d93de08.wav      | 13.3 KB | jump     | 150ms    | 200-600 Hz sweep, pulse      |
| sfx_coin_ebdb1dd1.wav      | 15.9 KB | coin     | 180ms    | 1000-1500 Hz sweep, pulse    |
| sfx_hit_59058818.wav       | 10.6 KB | hit      | 120ms    | White noise with envelope    |
| sfx_powerup_e164a20e.wav   | 26.5 KB | powerup  | 300ms    | 440-880 Hz sweep, pulse      |
| sfx_jump_4d718819.wav      | 13.3 KB | jump     | 150ms    | Variation of original jump   |

---

## Technical Implementation Details

### Sound Generation Parameters

**Sample Rate**: 44,100 Hz (high quality)
**Bit Depth**: 16-bit
**Channels**: Mono

**Duty Cycles** (Pulse waves):
- 12.5% - Thin, bright sound
- 25% - Classic Game Boy sound
- 50% - Square wave, balanced
- 75% - Inverted 25%, hollow sound

**Envelope (ADSR)**:
- Attack: 0-1 (fraction of duration, time to reach peak)
- Decay: 0-1 (fraction of duration, time to decay to sustain)
- Sustain: 0-1 (amplitude level during sustain)
- Release: 0-1 (fraction of duration, fade-out time)

### Waveform Generation

**Pulse Waves**:
- Generated using phase accumulation
- Frequency sweep: Linear interpolation from start to end frequency
- Duty cycle: Threshold comparison on sine wave

**Noise**:
- White noise: Uniform random distribution
- Harsh noise: High-pass filtered white noise
- Periodic noise: Tiled short random pattern (32 samples)

**Wave Channel**:
- Sine: Pure sine wave
- Triangle: Piecewise linear approximation
- Sawtooth: Linear ramp waveform

---

## Integration with GBStudio

### Auto-Import to Project

To integrate generated SFX into a GBStudio project:

1. Generate sound effects using the API
2. Copy WAV files from `/app/sfx_outputs/` to GBStudio project:
   ```bash
   cp /app/sfx_outputs/sfx_jump_*.wav \
      /path/to/gbstudio/project/assets/sounds/
   ```
3. Reference in GBStudio scripts using the sound effect name

### Format Compatibility

- Output format: WAV (PCM)
- Sample rate: 44,100 Hz (can be downsampled for GBStudio)
- Bit depth: 16-bit
- Channels: Mono

**Note**: GBStudio typically uses lower sample rates. Consider downsampling to 11,025 Hz or 22,050 Hz for smaller file sizes.

---

## File Structure

```
/app/sfx_outputs/
├── metadata.json              # Registry of all generated SFX
├── sfx_jump_abc123.wav        # Jump sound
├── sfx_coin_def456.wav        # Coin sound
├── sfx_hit_ghi789.wav         # Hit sound
└── ...
```

**Metadata Format**:
```json
{
  "sfx_jump_abc123": {
    "sfx_id": "sfx_jump_abc123",
    "description": "...",
    "category": "jump",
    "file_path": "/app/sfx_outputs/sfx_jump_abc123.wav",
    "duration_ms": 150,
    "format": "wav",
    "parameters": { "..." },
    "created_at": "2025-11-09T05:08:40.867094"
  }
}
```

---

## Error Handling

### Common Errors

**404 Not Found**:
```json
{
  "detail": "SFX sfx_jump_abc123 not found"
}
```

**400 Bad Request**:
```json
{
  "detail": "Invalid category: unknown_category"
}
```

**500 Internal Server Error**:
```json
{
  "detail": "SFX generation failed: [error details]"
}
```

### Validation

- `description`: 1-500 characters
- `variations`: 1-5
- `variation_amount`: 0.0-1.0
- `duration_ms`: Positive integer

---

## Performance Metrics

### Generation Speed

- Single SFX: ~10-50ms
- 3 variations: ~30-150ms
- Batch of 10: ~100-500ms

### File Sizes

| Duration | Pulse Wave | Noise |
|----------|------------|-------|
| 100ms    | ~9 KB      | ~9 KB |
| 200ms    | ~18 KB     | ~18 KB|
| 500ms    | ~44 KB     | ~44 KB|
| 1000ms   | ~88 KB     | ~88 KB|

Formula: `Size (bytes) ≈ duration_sec × sample_rate × 2 (16-bit)`

---

## Next Steps / Enhancements

### Potential Improvements

1. **GBT Player Integration**: Export to GBT SFX format for direct use
2. **VGM Export**: Export to VGM format for authentic playback
3. **Batch Generation**: Endpoint to generate multiple SFX at once
4. **SFX Mixing**: Combine multiple channels into composite sounds
5. **Visualization**: Generate waveform visualizations
6. **Audio Preview**: In-browser playback preview
7. **Preset Editor**: UI for creating custom presets
8. **Effect Chains**: Apply multiple effects in sequence

### Feature Ideas

- **Arpeggio Support**: Rapid note changes for chiptune effects
- **Vibrato**: Frequency modulation for warbling effects
- **Echo/Delay**: Multiple delayed copies
- **Channel Mixing**: Multi-channel composite sounds
- **Template Library**: Expandable preset library
- **AI-Assisted Generation**: Use LLM to suggest parameters based on description

---

## Conclusion

The SFX Department is fully functional and ready for production use. It provides:

✅ Authentic Game Boy sound generation
✅ 10 pre-configured presets
✅ Custom parameter support
✅ Variation generation
✅ Complete REST API
✅ Comprehensive error handling
✅ Metadata tracking
✅ File management

All sound effects are generated using procedural synthesis with no external dependencies beyond NumPy, ensuring fast, reliable, and authentic 8-bit Game Boy sound effects.
