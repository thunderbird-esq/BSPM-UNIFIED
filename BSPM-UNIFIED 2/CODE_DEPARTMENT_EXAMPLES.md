# Code Department - API Documentation & Examples

## Overview

The Code Department generates GBStudio scripting code from natural language descriptions. It uses LLM (Ollama) to understand user intent and converts it into GBStudio event JSON format.

## API Endpoints

### 1. POST /api/code/generate

Generate GBStudio script from natural language description.

**Request Body:**
```json
{
  "description": "Create a simple dialogue where an NPC says 'Welcome to the village!'",
  "script_type": "dialogue",
  "context": {
    "actor_id": "actor_001",
    "scene_name": "Village"
  },
  "template_id": "dialogue_simple"
}
```

**Response:**
```json
{
  "script_id": "script_a3f9d2b8c1e5",
  "description": "Create a simple dialogue where an NPC says 'Welcome to the village!'",
  "events": [
    {
      "id": "event_8a3f9d2b3c1e",
      "command": "EVENT_TEXT",
      "args": {
        "text": [
          "Welcome to the village!"
        ],
        "avatarId": ""
      }
    }
  ],
  "estimated_events": 1,
  "validation_status": "valid",
  "template_used": "dialogue_simple",
  "variables_used": ["dialogue_text", "avatar_id"],
  "created_at": "2025-01-09T12:34:56.789Z",
  "correlation_id": "req_1234567890_abc123"
}
```

**Example 1: Simple Dialogue**
```bash
curl -X POST http://localhost:8000/api/code/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "NPC greets the player with Hello adventurer!",
    "script_type": "dialogue"
  }'
```

**Example 2: Branching Dialogue**
```bash
curl -X POST http://localhost:8000/api/code/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "NPC asks if player wants to buy a potion. If yes, say Great! That will be 50 gold. If no, say Come back anytime.",
    "script_type": "dialogue",
    "template_id": "dialogue_branching"
  }'
```

**Example 3: Actor Patrol Movement**
```bash
curl -X POST http://localhost:8000/api/code/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Make the guard patrol back and forth between x=5 and x=15",
    "script_type": "movement",
    "context": {
      "actor_id": "guard_01",
      "start_x": 5,
      "start_y": 8,
      "target_x": 15,
      "target_y": 8
    }
  }'
```

**Example 4: Combat System**
```bash
curl -X POST http://localhost:8000/api/code/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "When player hits enemy, reduce health by 2 points. If health reaches 0, show Game Over message and return to main menu",
    "script_type": "logic",
    "context": {
      "health_variable": "L0",
      "max_health": 10
    }
  }'
```

**Example 5: Item Collection**
```bash
curl -X POST http://localhost:8000/api/code/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "When player touches the key, show You found a key! message, set has_key variable to true, and hide the key sprite",
    "script_type": "logic",
    "context": {
      "item_name": "Key",
      "item_variable": "L1",
      "item_actor_id": "key_sprite_01"
    }
  }'
```

---

### 2. GET /api/code/templates

List all available GBStudio script templates.

**Request:**
```bash
curl -X GET http://localhost:8000/api/code/templates
```

**Response:**
```json
{
  "total": 6,
  "templates": [
    {
      "id": "dialogue_simple",
      "name": "Simple Dialogue",
      "description": "Basic NPC dialogue with single text box",
      "category": "dialogue",
      "variables": ["dialogue_text", "avatar_id"],
      "event_count": 1
    },
    {
      "id": "dialogue_branching",
      "name": "Branching Dialogue",
      "description": "Dialogue with player choices that branch to different outcomes",
      "category": "dialogue",
      "variables": ["initial_text", "avatar_id", "choice_variable", "option_1_text", "option_2_text", "option_1_response", "option_2_response"],
      "event_count": 2
    },
    {
      "id": "movement_patrol",
      "name": "Actor Patrol Pattern",
      "description": "Make an actor patrol back and forth between two points",
      "category": "movement",
      "variables": ["actor_id", "start_x", "start_y", "target_x", "target_y", "wait_time"],
      "event_count": 5
    },
    {
      "id": "combat_basic",
      "name": "Basic Combat Logic",
      "description": "Simple combat system with health and damage",
      "category": "logic",
      "variables": ["health_variable", "damage_amount", "max_health", "defeat_message", "game_over_scene"],
      "event_count": 1
    },
    {
      "id": "inventory_system",
      "name": "Item Collection System",
      "description": "Collect items and store them in inventory variables",
      "category": "logic",
      "variables": ["item_name", "item_variable", "item_actor_id"],
      "event_count": 4
    },
    {
      "id": "save_system",
      "name": "Save/Load System",
      "description": "Save and load game state using persistent variables",
      "category": "logic",
      "variables": ["save_message"],
      "event_count": 3
    }
  ]
}
```

---

### 3. POST /api/code/validate

Validate GBStudio script syntax and structure.

**Request:**
```bash
curl -X POST http://localhost:8000/api/code/validate \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "id": "event_123",
        "command": "EVENT_TEXT",
        "args": {
          "text": ["Hello!"]
        }
      }
    ]
  }'
```

**Response:**
```json
{
  "status": "valid",
  "errors": [],
  "warnings": [],
  "event_count": 1
}
```

**Example with Invalid Script:**
```bash
curl -X POST http://localhost:8000/api/code/validate \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "command": "EVENT_TEXT"
      },
      {
        "id": "event_456",
        "args": {
          "text": ["Missing command!"]
        }
      }
    ]
  }'
```

**Response:**
```json
{
  "status": "invalid",
  "errors": [
    "Event 0: missing 'args' field",
    "Event 1: missing 'command' field"
  ],
  "warnings": [
    "Event 0: missing 'id' field"
  ],
  "event_count": 2
}
```

---

### 4. POST /api/code/optimize

Optimize GBStudio script for performance.

**Request:**
```bash
curl -X POST http://localhost:8000/api/code/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "id": "event_1",
        "command": "EVENT_TEXT",
        "args": {"text": ["Hello!"]}
      },
      {
        "id": "event_2",
        "command": "EVENT_TEXT",
        "args": {"text": ["How are you?"]}
      },
      {
        "id": "event_3",
        "command": "EVENT_WAIT",
        "args": {"time": 0.05}
      }
    ]
  }'
```

**Response:**
```json
{
  "original_event_count": 3,
  "optimized_event_count": 3,
  "suggestions": [
    {
      "type": "merge_texts",
      "description": "Found 1 consecutive text events that could be merged",
      "locations": [0]
    },
    {
      "type": "short_wait",
      "description": "Event 2: very short wait time (0.05s) may be unnecessary",
      "location": 2
    }
  ],
  "optimized_events": [...]
}
```

---

### 5. GET /api/code/patterns

Get common GBStudio script patterns organized by type.

**Request:**
```bash
curl -X GET http://localhost:8000/api/code/patterns
```

**Response:**
```json
{
  "patterns": {
    "dialogue": [
      "Simple NPC conversation",
      "Branching dialogue with choices",
      "Multi-page text boxes",
      "Character portraits and avatars"
    ],
    "movement": [
      "Actor patrol patterns",
      "Follow player behavior",
      "Scripted movement sequences",
      "Camera control"
    ],
    "logic": [
      "Variable conditions (if/else)",
      "Switch statements",
      "Math operations on variables",
      "State machines"
    ],
    "trigger": [
      "Collision triggers",
      "Interaction triggers",
      "Auto-run scripts",
      "Custom events"
    ],
    "scene": [
      "Scene transitions",
      "Actor spawn/despawn",
      "Background changes",
      "Fadeout effects"
    ],
    "ui": [
      "Menu systems",
      "HUD updates",
      "Overlay animations",
      "Input handling"
    ]
  },
  "types": ["dialogue", "movement", "logic", "trigger", "scene", "ui"]
}
```

---

## Script Types

### Dialogue Scripts
- **Simple dialogue**: Single text box with NPC message
- **Branching dialogue**: Player choices with different outcomes
- **Multi-page dialogue**: Long conversations split across multiple text boxes
- **Portrait dialogue**: Dialogue with character avatars

### Movement Scripts
- **Patrol**: Actor moves back and forth between points
- **Follow**: Actor follows player or another actor
- **Scripted sequence**: Predetermined movement path
- **Camera control**: Control camera position and movement

### Logic Scripts
- **Conditions**: If/else statements based on variables
- **Variables**: Set, increment, decrement variables
- **Math**: Perform calculations on variables
- **Switches**: Multi-way branching based on variable values

### Trigger Scripts
- **Collision**: Trigger when player/actor collides with object
- **Interaction**: Trigger when player presses action button
- **Auto-run**: Script runs automatically on scene start
- **Custom events**: Reusable script modules

### Scene Scripts
- **Transitions**: Move to different scene
- **Actor management**: Show, hide, or spawn actors
- **Background changes**: Switch background images
- **Effects**: Fade in/out, screen shake, etc.

### UI Scripts
- **Menus**: Create menu systems with options
- **HUD**: Update health, score, or other UI elements
- **Overlays**: Show/hide UI overlays
- **Input**: Handle custom input controls

---

## GBStudio Event Commands Reference

### Common Event Commands

**Dialogue:**
- `EVENT_TEXT`: Display text dialogue box
- `EVENT_CHOICE`: Present player with binary choice
- `EVENT_MENU`: Create menu with multiple options

**Movement:**
- `EVENT_ACTOR_MOVE_TO`: Move actor to absolute position
- `EVENT_ACTOR_MOVE_RELATIVE`: Move actor by offset
- `EVENT_ACTOR_SET_DIRECTION`: Change actor facing direction
- `EVENT_ACTOR_SET_POSITION`: Instantly teleport actor

**Logic:**
- `EVENT_IF`: Conditional branch (if/else)
- `EVENT_SWITCH`: Multi-way switch statement
- `EVENT_VARIABLE_MATH`: Perform math on variables
- `EVENT_SET_VALUE`: Set variable to value
- `EVENT_LOOP`: Infinite loop (use with caution)

**Scene:**
- `EVENT_SWITCH_SCENE`: Transition to different scene
- `EVENT_ACTOR_SHOW`: Make actor visible
- `EVENT_ACTOR_HIDE`: Make actor invisible
- `EVENT_ACTOR_DEACTIVATE`: Temporarily disable actor

**Triggers:**
- `EVENT_SCRIPT_LOCK`: Prevent script from running again
- `EVENT_SCRIPT_UNLOCK`: Allow script to run again
- `EVENT_CALL_CUSTOM_EVENT`: Call reusable custom event

**UI:**
- `EVENT_OVERLAY_SHOW`: Display UI overlay
- `EVENT_OVERLAY_HIDE`: Hide UI overlay
- `EVENT_OVERLAY_MOVE_TO`: Animate overlay position

**Timing:**
- `EVENT_WAIT`: Wait for specified duration
- `EVENT_PAUSE`: Pause until player input

**Audio:**
- `EVENT_SOUND_PLAY_EFFECT`: Play sound effect
- `EVENT_MUSIC_PLAY`: Play music track
- `EVENT_MUSIC_STOP`: Stop music

---

## Integration with GBStudio Project

### Example: Injecting Generated Script into GBStudio Project

```python
from backend.gbstudio.project import GBStudioProject
from backend.code_department import CodeDepartment, CodeGenerationRequest

# Initialize
project = GBStudioProject("/app/project_files/MyGBCGame.gbsproj")
code_dept = CodeDepartment()

# Generate script
request = CodeGenerationRequest(
    description="NPC says Hello, welcome to my shop!",
    script_type="dialogue"
)
script = await code_dept.generate_script(request)

# Inject into GBStudio project
# (Note: GBStudioProject would need additional methods to modify actor scripts)
# This is a conceptual example
project.add_actor_script(
    actor_id="merchant_npc",
    trigger_type="interact",
    events=script.events
)

project.save()
```

---

## Best Practices

1. **Use Templates**: Start with templates for common patterns, then customize
2. **Validate Scripts**: Always validate generated scripts before using in production
3. **Optimize**: Use the optimize endpoint to identify performance improvements
4. **Context**: Provide detailed context (actor IDs, variables, scene info) for better results
5. **Iterate**: Use the regenerate feature if the first result isn't perfect
6. **Test**: Test generated scripts in GBStudio before deploying to final game

---

## Troubleshooting

### Script Generation Fails
- Check that Ollama service is running and accessible
- Verify the description is clear and specific
- Try using a specific template_id instead of auto-selection

### Validation Errors
- Check that all events have required fields (id, command, args)
- Verify event IDs are unique
- Ensure commands are valid GBStudio commands

### Scripts Don't Work in GBStudio
- Validate the script structure matches GBStudio requirements
- Check that variable names (L0, L1, etc.) are correct
- Verify actor IDs and scene IDs exist in your project

---

## Future Enhancements

1. **Script Library**: Save and reuse frequently used scripts
2. **AI Learning**: Learn from user modifications to improve generation
3. **Visual Preview**: Preview script flow before applying to project
4. **Advanced Templates**: More complex templates for common game mechanics
5. **Script Chaining**: Combine multiple script patterns into complex sequences
6. **GBStudio Integration**: Direct integration with GBStudio project files
7. **Script Testing**: Automated testing of generated scripts
8. **Documentation Generation**: Auto-generate documentation for custom scripts

---

## API Integration Examples

### Python
```python
import requests

response = requests.post(
    "http://localhost:8000/api/code/generate",
    json={
        "description": "NPC asks if player wants to rest at the inn",
        "script_type": "dialogue"
    }
)

script = response.json()
print(f"Generated {script['estimated_events']} events")
print(script['events'])
```

### JavaScript
```javascript
fetch('http://localhost:8000/api/code/generate', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    description: 'Guard blocks the path until player shows a pass',
    script_type: 'logic'
  })
})
.then(res => res.json())
.then(script => {
  console.log(`Generated script: ${script.script_id}`);
  console.log(script.events);
});
```

### cURL
```bash
# Simple request
curl -X POST http://localhost:8000/api/code/generate \
  -H "Content-Type: application/json" \
  -d '{"description": "Save game", "script_type": "logic"}'

# With template
curl -X POST http://localhost:8000/api/code/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Merchant offers to sell health potion",
    "script_type": "dialogue",
    "template_id": "dialogue_branching"
  }'
```

---

## Template Variable Reference

### dialogue_simple
- `dialogue_text` (string, required): Text to display
- `avatar_id` (string, optional): Avatar sprite ID

### dialogue_branching
- `initial_text` (string, required): Initial dialogue before choice
- `avatar_id` (string, optional): Avatar sprite ID
- `choice_variable` (string, required): Variable to store choice (default: L0)
- `option_1_text` (string, required): First choice text
- `option_2_text` (string, required): Second choice text
- `option_1_response` (string, required): Response for first choice
- `option_2_response` (string, required): Response for second choice

### movement_patrol
- `actor_id` (string, required): Actor to move
- `start_x` (number, required): Starting X position
- `start_y` (number, required): Starting Y position
- `target_x` (number, required): Target X position
- `target_y` (number, required): Target Y position
- `wait_time` (number, optional): Wait time at each point (default: 1)

### combat_basic
- `health_variable` (string, required): Variable storing health (default: L0)
- `damage_amount` (number, required): Damage to deal (default: 1)
- `max_health` (number, optional): Maximum health (default: 10)
- `defeat_message` (string, optional): Game over message
- `game_over_scene` (string, optional): Scene to switch to on defeat

### inventory_system
- `item_name` (string, required): Name of the item
- `item_variable` (string, required): Variable to set when collected (default: L0)
- `item_actor_id` (string, required): Actor ID of item sprite

### save_system
- `save_message` (string, optional): Message before saving (default: "Saving game...")

---

## Support & Documentation

For more information about GBStudio scripting, see:
- GBStudio Documentation: https://www.gbstudio.dev/docs/
- GBStudio Scripting Guide: https://www.gbstudio.dev/docs/scripting/
- Community Forums: https://gbstudio.dev/community/

For Code Department issues or feature requests, contact the development team.
