# GBStudio Automation Hub - Complete Technical Implementation Guide

**Version:** 3.1 - Hyper-Specific Technical Edition  
**Date:** 2025-01-04  
**Author:** TBESQ Integration Team  
**Target Platform:** Intel Mac (macOS Ventura 13.x) + Docker Desktop 4.25+

---

## Document Structure

This guide is divided into three parts:

1. **Part A: Technical Specifications** (this document) - Complete system architecture with concrete examples
2. **Part B: Implementation Files** (following artifacts) - Production-ready code files delivered in full
3. **Part C: Testing & Validation** (final artifact) - Specific test cases with expected outputs

---

## Table of Contents

1. [System Architecture with Data Flow](#system-architecture-with-data-flow)
2. [GBStudio Project Format Specification](#gbstudio-project-format-specification)
3. [ComfyUI Workflow Specification](#comfyui-workflow-specification)
4. [FAISS Vectorstore Implementation Details](#faiss-vectorstore-implementation-details)
5. [Docker Container Communication Protocol](#docker-container-communication-protocol)
6. [Validation Criteria with Test Cases](#validation-criteria-with-test-cases)

---

## System Architecture with Data Flow

### Complete Request Flow: User Prompt → Generated Sprite in GBStudio

```
[1] USER TYPES: "Create a knight sprite"
    ↓ HTTP POST /api/v1/prompt
    ↓ Body: {"message": "Create a knight sprite", "session_id": "abc123"}
    
[2] BACKEND (FastAPI) receives request
    ↓ Generates correlation_id: "req_1704398400_8a3f"
    ↓ Logs: {"level": "INFO", "correlation_id": "req_1704398400_8a3f", "endpoint": "/api/v1/prompt"}
    
[3] CONVERSATION MEMORY checks recent context
    ↓ Reads: /app/agent_memory/conversations/abc123.jsonl (last 6 turns)
    ↓ Returns: "User: What art style should we use?\nPM: Pixel art, 32x32 frames..."
    
[4] KNOWLEDGE BASE semantic search
    ↓ Embeds query via: POST http://ollama:11434/api/embeddings
    ↓ Searches FAISS index with L2 distance
    ↓ Returns: 3 relevant docs (ArtStyleGuide.md chunks)
    
[5] PM AGENT (Ollama llama3:8b) receives enriched prompt
    ↓ POST http://ollama:11434/api/generate
    ↓ Body: {
          "model": "llama3",
          "prompt": "CONTEXT:\nRecent: [conversation]\nDocs: [retrieved]\n\nUSER: Create a knight sprite\n\nYou are PM...",
          "stream": false
        }
    ↓ Returns JSON: {
          "response_to_user": "I'll create a pixel art knight sprite...",
          "needs_approval": true,
          "delegation_plan": [{
            "department": "Art",
            "task": "Generate 8-frame knight sprite: idle, walk x4, attack x2, hurt"
          }]
        }
    
[6] BACKEND returns to frontend
    ↓ HTTP 200 OK
    ↓ Body: {
          "message": "I'll create a pixel art knight sprite...",
          "plan": [...],
          "requires_approval": true,
          "session_id": "abc123"
        }
    
[7] FRONTEND renders approval UI
    ↓ User clicks "✓ APPROVE"
    ↓ HTTP POST /api/v1/execute
    ↓ Body: {"plan": [...], "session_id": "abc123"}
    
[8] BACKEND creates ComfyUI workflow
    ↓ Calls: workflow_builder.create_spritesheet_workflow(
          positive="knight in armor, pixel art, sprite sheet, 8 poses",
          negative="blurry, photo, 3d, inconsistent"
        )
    ↓ Generates workflow dict with 18 nodes
    
[9] COMFYUI receives workflow
    ↓ HTTP POST http://comfyui:8188/prompt
    ↓ Body: {"prompt": {workflow}, "client_id": "gbstudio_abc123"}
    ↓ Returns: {"prompt_id": "def456"}
    ↓ WebSocket emits: {"type": "executing", "data": {"node": "6"}}
    
[10] FRONTEND WebSocket receives progress
     ↓ ws://comfyui:8188/ws?clientId=gbstudio_abc123
     ↓ Message: {"type": "progress", "data": {"value": 15, "max": 25}}
     ↓ Updates progress bar: 60%
     
[11] COMFYUI completes generation
     ↓ Saves 8 files: sprite_frame_0_00001.png ... sprite_frame_7_00001.png
     ↓ Location: /app/ComfyUI/output/
     ↓ WebSocket: {"type": "executed", "data": {"node": "18", "output": {"images": [...]}}}
     
[12] BACKEND polls for completion
     ↓ HTTP GET http://comfyui:8188/history/def456
     ↓ Parses output filenames from history JSON
     ↓ Validates frames with SpriteSheetValidator
     
[13] VALIDATOR checks frames
     ↓ Opens each PNG with PIL
     ↓ Checks dimensions: (32, 32) ✓
     ↓ Extracts color palette with KMeans (n_clusters=4)
     ↓ Calculates palette_similarity: 0.94 ✓ (threshold: 0.85)
     ↓ Returns: {"valid": true, "metrics": {...}}
     
[14] GBSTUDIO PROJECT INTEGRATION
     ↓ Loads: /app/project_files/MyGBCGame.gbsproj
     ↓ Combines 8 frames into grid: 3x3 layout (96x96 pixels)
     ↓ Saves: /app/project_files/assets/sprites/knight_20250104_143000.png
     ↓ Adds JSON entry:
       {
         "id": "sprite_8a3f9d2b",
         "name": "Knight",
         "filename": "knight_20250104_143000.png",
         "numFrames": 8,
         "type": "actor_animated"
       }
     ↓ Writes updated .gbsproj
     
[15] TASK MEMORY records completion
     ↓ Appends to: /app/agent_memory/tasks.json
     ↓ Entry: {
          "task_id": "task_8a3f9d2b",
          "status": "completed",
          "generation_time_seconds": 187.3,
          "artifacts": ["sprite_8a3f9d2b"]
        }
        
[16] BACKEND returns success
     ↓ HTTP 200 OK
     ↓ Body: {
          "status": "success",
          "sprite_id": "sprite_8a3f9d2b",
          "frames": ["/output/sprite_frame_0_00001.png", ...],
          "preview": "/output/sprite_sheet_preview_00001.png"
        }
        
[17] FRONTEND displays result
     ↓ Shows 8 frames in grid
     ↓ "✓ Knight sprite added to GBStudio project"
```

---

## GBStudio Project Format Specification

### GBStudio 4.1.3 .gbsproj JSON Schema

A `.gbsproj` file is a JSON document with the following top-level structure:

```json
{
  "name": "MyGBCGame",
  "author": "Developer",
  "_version": "4.1.3",
  "_release": "4",
  "settings": { /* see Settings Schema */ },
  "scenes": [ /* array of Scene objects */ ],
  "backgrounds": [ /* array of Background objects */ ],
  "spriteSheets": [ /* array of SpriteSheet objects */ ],
  "music": [ /* array of Music objects */ ],
  "fonts": [ /* array of Font objects */ ],
  "avatars": [ /* array of Avatar objects */ ],
  "emotes": [ /* array of Emote objects */ ],
  "customEvents": [ /* array of CustomEvent objects */ ],
  "variables": [ /* array of Variable objects */ ],
  "constants": [ /* array of Constant objects */ ],
  "palettes": [ /* array of Palette objects */ ],
  "engineFieldValues": []
}
```

### SpriteSheet Object Schema

**CORRECT** sprite sheet entry:

```json
{
  "id": "sprite_8a3f9d2b",
  "name": "Knight",
  "filename": "knight_20250104_143000.png",
  "numFrames": 8,
  "type": "actor_animated",
  "canvasWidth": 32,
  "canvasHeight": 32,
  "_v": 1704398400000
}
```

**Field Specifications:**

- `id` (string, required): UUID or hash-based unique identifier
  - Format: `sprite_[a-f0-9]{8}`
  - Generation: First 8 chars of SHA256(filename + timestamp)
  
- `name` (string, required): Display name in GBStudio UI
  - Max length: 64 characters
  - Allowed chars: `[A-Za-z0-9 _-]`
  
- `filename` (string, required): PNG filename relative to `assets/sprites/`
  - Must exist at: `project_files/assets/sprites/{filename}`
  - Format: `[a-z0-9_]+.png`
  
- `numFrames` (integer, required): Total animation frames
  - Range: 1-32
  - For our system: Always 8
  
- `type` (string, required): Sprite type enum
  - Options: `"actor"`, `"actor_animated"`, `"static"`, `"ui"`
  - For character sprites: `"actor_animated"`
  
- `canvasWidth` (integer, required): Width of each frame in pixels
  - For GBC: Always 32
  
- `canvasHeight` (integer, required): Height of each frame in pixels
  - For GBC: Always 32
  
- `_v` (integer, required): Version timestamp
  - Format: Unix timestamp in milliseconds
  - Example: `1704398400000` = 2025-01-04 14:00:00 UTC

### Sprite Sheet PNG Format Requirements

The PNG file must be a grid layout where:

1. **Total dimensions**: `(numFrames_per_row * 32) x (num_rows * 32)`
   - For 8 frames in 3x3 grid: 96x96 pixels
   - Layout:
     ```
     [Frame 0] [Frame 1] [Frame 2]
     [Frame 3] [Frame 4] [Frame 5]
     [Frame 6] [Frame 7] [Empty  ]
     ```

2. **Color mode**: Indexed color (PNG mode 'P')
   ```python
   # CORRECT: Convert to indexed 4-color
   image = Image.open('sprite.png').convert('RGB')
   image = image.convert('P', palette=Image.ADAPTIVE, colors=4)
   image.save('sprite_indexed.png', 'PNG', optimize=True)
   ```

3. **Color palette**: Game Boy Color compliant
   - Max colors per sprite: 4 (including transparency)
   - Allowed palette: DMG green tones
     ```
     Color 0 (darkest):  RGB(15, 56, 15)   #0f380f
     Color 1 (dark):     RGB(48, 98, 48)   #306230
     Color 2 (light):    RGB(139, 172, 15) #8bac0f
     Color 3 (lightest): RGB(155, 188, 15) #9bbc0f
     ```

4. **Transparency**: Color index 0 is transparent
   ```python
   # Set transparency
   image.save('sprite.png', 'PNG', transparency=0)
   ```

**INCORRECT** sprite sheet (will fail GBStudio import):

```json
{
  "id": "sprite123",  // ✗ Invalid format (needs prefix)
  "filename": "Knight Sprite.png",  // ✗ Spaces not allowed
  "numFrames": 8,
  // ✗ Missing: canvasWidth, canvasHeight, type
  // ✗ Missing: _v timestamp
}
```

PNG with RGB color mode (not indexed): ✗ FAILS
PNG with 256 colors: ✗ FAILS (max 4 colors)
PNG with frames arranged vertically: ✗ FAILS (must be grid)

---

## ComfyUI Workflow Specification

### Workflow JSON Structure

A ComfyUI workflow is a JSON object where keys are node IDs (strings) and values are node objects:

```json
{
  "1": {
    "class_type": "CheckpointLoaderSimple",
    "inputs": {
      "ckpt_name": "sd_xl_base_1.0.safetensors"
    }
  },
  "2": {
    "class_type": "KSampler",
    "inputs": {
      "model": ["1", 0],  // Reference to node "1", output slot 0
      "seed": 42,
      "steps": 20
    }
  }
}
```

### Node Reference Format

Inputs can reference other nodes using the format: `[node_id, output_slot]`

- `node_id` (string): The key of the source node
- `output_slot` (integer): Which output of that node (0-indexed)

**Example**: Node "7" (VAEDecode) references node "6" (KSampler) output 0:

```json
"7": {
  "class_type": "VAEDecode",
  "inputs": {
    "samples": ["6", 0],  // KSampler's latent output
    "vae": ["1", 2]       // CheckpointLoader's VAE output
  }
}
```

### Complete 8-Frame Sprite Sheet Workflow

**Purpose**: Generate 256x256 image, split into 8 frames of 32x32 each

```json
{
  "1": {
    "class_type": "CheckpointLoaderSimple",
    "inputs": {
      "ckpt_name": "sd_xl_base_1.0.safetensors"
    },
    "_meta": {
      "title": "Load SDXL Base Model"
    }
  },
  
  "2": {
    "class_type": "LoraLoader",
    "inputs": {
      "lora_name": "pixel-art-xl-v1.1.safetensors",
      "strength_model": 1.0,
      "strength_clip": 1.0,
      "model": ["1", 0],
      "clip": ["1", 1]
    },
    "_meta": {
      "title": "Apply Pixel Art LoRA",
      "note": "Trained on 32x32 Game Boy style sprites"
    }
  },
  
  "3": {
    "class_type": "CLIPTextEncode",
    "inputs": {
      "text": "{{POSITIVE_PROMPT}}, sprite sheet, 8 animation frames, pixel art, game boy color, character turnaround, multiple poses in grid layout, 32x32 pixels per frame",
      "clip": ["2", 1]
    },
    "_meta": {
      "title": "Encode Positive Prompt"
    }
  },
  
  "4": {
    "class_type": "CLIPTextEncode",
    "inputs": {
      "text": "{{NEGATIVE_PROMPT}}, blurry, photo realistic, 3d render, different characters, inconsistent style, wrong colors, modern graphics, high resolution, detailed textures",
      "clip": ["2", 1]
    },
    "_meta": {
      "title": "Encode Negative Prompt"
    }
  },
  
  "5": {
    "class_type": "EmptyLatentImage",
    "inputs": {
      "width": 256,
      "height": 256,
      "batch_size": 1
    },
    "_meta": {
      "title": "Create 256x256 Latent",
      "note": "Will contain 8 frames: (256/32) x (256/32) = 8x8 grid capacity"
    }
  },
  
  "6": {
    "class_type": "KSampler",
    "inputs": {
      "seed": "{{SEED}}",
      "steps": 20,
      "cfg": 8.0,
      "sampler_name": "euler_ancestral",
      "scheduler": "karras",
      "denoise": 1.0,
      "model": ["2", 0],
      "positive": ["3", 0],
      "negative": ["4", 0],
      "latent_image": ["5", 0]
    },
    "_meta": {
      "title": "Sample Latent",
      "note": "euler_ancestral: CPU-friendly, good for pixel art\nkarras: Stable noise schedule\nsteps=20: Reduced from 25 for Intel Mac performance"
    }
  },
  
  "7": {
    "class_type": "VAEDecode",
    "inputs": {
      "samples": ["6", 0],
      "vae": ["1", 2]
    },
    "_meta": {
      "title": "Decode to Image"
    }
  },
  
  "8": {
    "class_type": "DynamicTileSplit",
    "inputs": {
      "image": ["7", 0],
      "tile_width": 32,
      "tile_height": 32,
      "overlap": 0,
      "offset": 0
    },
    "_meta": {
      "title": "Split into 32x32 Tiles",
      "note": "Requires ComfyUI-Impact-Pack custom node"
    }
  },
  
  "9": {
    "class_type": "SaveImage",
    "inputs": {
      "filename_prefix": "sprite_frame_0",
      "images": ["8", 0, 0]
    },
    "_meta": {"title": "Save Frame 0 (Idle)"}
  },
  
  "10": {
    "class_type": "SaveImage",
    "inputs": {
      "filename_prefix": "sprite_frame_1",
      "images": ["8", 0, 1]
    },
    "_meta": {"title": "Save Frame 1 (Walk 1)"}
  },
  
  "11": {
    "class_type": "SaveImage",
    "inputs": {
      "filename_prefix": "sprite_frame_2",
      "images": ["8", 0, 2]
    },
    "_meta": {"title": "Save Frame 2 (Walk 2)"}
  },
  
  "12": {
    "class_type": "SaveImage",
    "inputs": {
      "filename_prefix": "sprite_frame_3",
      "images": ["8", 0, 3]
    },
    "_meta": {"title": "Save Frame 3 (Walk 3)"}
  },
  
  "13": {
    "class_type": "SaveImage",
    "inputs": {
      "filename_prefix": "sprite_frame_4",
      "images": ["8", 0, 4]
    },
    "_meta": {"title": "Save Frame 4 (Walk 4)"}
  },
  
  "14": {
    "class_type": "SaveImage",
    "inputs": {
      "filename_prefix": "sprite_frame_5",
      "images": ["8", 0, 5]
    },
    "_meta": {"title": "Save Frame 5 (Attack 1)"}
  },
  
  "15": {
    "class_type": "SaveImage",
    "inputs": {
      "filename_prefix": "sprite_frame_6",
      "images": ["8", 0, 6]
    },
    "_meta": {"title": "Save Frame 6 (Attack 2)"}
  },
  
  "16": {
    "class_type": "SaveImage",
    "inputs": {
      "filename_prefix": "sprite_frame_7",
      "images": ["8", 0, 7]
    },
    "_meta": {"title": "Save Frame 7 (Hurt)"}
  },
  
  "17": {
    "class_type": "DynamicTileMerge",
    "inputs": {
      "images": ["8", 0],
      "tile_calc": ["8", 1],
      "blend": 0
    },
    "_meta": {
      "title": "Merge for Preview",
      "note": "blend=0: No blending (hard edges for pixel art)"
    }
  },
  
  "18": {
    "class_type": "SaveImage",
    "inputs": {
      "filename_prefix": "sprite_sheet_preview",
      "images": ["17", 0]
    },
    "_meta": {
      "title": "Save Full Grid Preview"
    }
  }
}
```

### Sampler Parameter Explanations

**Why `euler_ancestral`?**
- Ancestral samplers add noise at each step
- Better for generating distinct variations (8 different poses)
- CPU-friendly (no gradient calculations needed)
- Good balance between quality and speed on Intel Mac

**Why `karras` scheduler?**
- Non-linear noise schedule
- More aggressive noise reduction in later steps
- Produces sharper edges (important for pixel art)
- Stable convergence on low step counts

**Why `cfg=8.0`?**
- Classifier-Free Guidance scale
- Higher values = stronger adherence to prompt
- 8.0 = sweet spot for sprite sheets (prevents frame drift)
- Too low (< 5): Frames look different
- Too high (> 12): Overcooked, artifacts

**Why `steps=20` (Intel Mac)?**
- Balance between quality and generation time
- Each step takes ~8-10 seconds on Intel i5/i7 CPU
- 20 steps = ~3-4 minutes total
- 25 steps (GPU default) = ~5-6 minutes on CPU

---

## FAISS Vectorstore Implementation Details

### Index Type: IndexFlatL2

**What it is**: Exhaustive search using L2 (Euclidean) distance

```python
import faiss
import numpy as np

# Create index for 768-dimensional vectors (nomic-embed-text)
dimension = 768
index = faiss.IndexFlatL2(dimension)

# Add vectors
vectors = np.random.rand(100, 768).astype('float32')
index.add(vectors)

# Search for 5 nearest neighbors
query = np.random.rand(1, 768).astype('float32')
distances, indices = index.search(query, k=5)
```

**Why IndexFlatL2?**
- **Exact search**: Returns true nearest neighbors (no approximation)
- **Small dataset**: < 10,000 documents performs well
- **Simple**: No training required
- **CPU-friendly**: No GPU needed

**Distance calculation**:
```
L2(a, b) = sqrt(sum((a_i - b_i)^2))
```

Lower distance = more similar

**When to upgrade**:
- **> 100,000 documents**: Switch to `IndexIVFFlat` (inverted file index)
  ```python
  nlist = 100  # Number of clusters
  quantizer = faiss.IndexFlatL2(dimension)
  index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
  index.train(vectors)  # Training required
  ```

### Embedding Model: nomic-embed-text

**Specifications**:
- Dimensions: 768
- Max tokens: 2048
- Model size: 1.2GB
- Speed: ~50ms per embedding on Intel Mac

**API Call**:
```bash
curl -X POST http://ollama:11434/api/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nomic-embed-text",
    "prompt": "knight in armor fighting dragon"
  }'
```

**Response**:
```json
{
  "embedding": [0.023, -0.891, 0.445, ..., 0.123],  // 768 floats
  "model": "nomic-embed-text",
  "total_duration": 48293750,  // nanoseconds
  "load_duration": 1234567,
  "prompt_eval_count": 8
}
```

### Document Chunking Strategy

**Problem**: Long documents (> 2048 tokens) must be split

**Solution**: Sliding window with overlap

```python
def chunk_document(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks.
    
    chunk_size: Target characters per chunk
    overlap: Characters to overlap between chunks
    
    Example:
      text = "ABCDEFGHIJ" (10 chars)
      chunk_size = 4
      overlap = 2
      
      Chunk 1: "ABCD"  (chars 0-3)
      Chunk 2: "CDEF"  (chars 2-5, overlap with chunk 1)
      Chunk 3: "EFGH"  (chars 4-7)
      Chunk 4: "GHIJ"  (chars 6-9)
    """
    chunks = []
    lines = text.split('\n')
    current_chunk = []
    current_size = 0
    
    for line in lines:
        line_size = len(line)
        
        if current_size + line_size > chunk_size and current_chunk:
            # Save current chunk
            chunks.append('\n'.join(current_chunk))
            
            # Start new chunk with overlap
            overlap_lines = []
            overlap_size = 0
            for prev_line in reversed(current_chunk):
                if overlap_size + len(prev_line) <= overlap:
                    overlap_lines.insert(0, prev_line)
                    overlap_size += len(prev_line)
                else:
                    break
            
            current_chunk = overlap_lines
            current_size = overlap_size
        
        current_chunk.append(line)
        current_size += line_size
    
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return chunks
```

**Why overlap?**
- Prevents context loss at chunk boundaries
- Example: "The knight wielded a sword. It was made of steel."
  - Without overlap: "sword" and "steel" might be in different chunks
  - With overlap: "sword. It was made of steel" captured together

**Chunk size selection**:
- Too small (< 500 chars): Loses context
- Too large (> 2000 chars): Exceeds model token limit
- Optimal: 1000 chars (~250 tokens) with 200 char overlap

### Metadata Storage

Each document in FAISS has associated metadata stored in a separate JSON file:

```json
{
  "doc_id_abc123": {
    "content": "The knight class has 3 attack power...",
    "metadata": {
      "type": "project_doc",
      "source_file": "GameDesignDocument.md",
      "chunk_index": 0,
      "total_chunks": 5,
      "created_at": "2025-01-04T14:00:00Z"
    }
  },
  "doc_id_def456": {
    "content": "User: Create a knight\nPM: I'll generate a sprite...",
    "metadata": {
      "type": "conversation",
      "session_id": "abc123",
      "turn_id": "turn_8a3f",
      "timestamp": "2025-01-04T14:05:00Z"
    }
  }
}
```

**Filtering by metadata**:
```python
def search_with_filter(query: str, filter_type: str = None) -> List[Dict]:
    # Get embeddings and search FAISS
    results = index.search(query_embedding, k=10)
    
    # Filter by metadata
    filtered = []
    for idx in results:
        doc = documents[idx]
        if filter_type is None or doc['metadata']['type'] == filter_type:
            filtered.append(doc)
    
    return filtered[:5]  # Return top 5 after filtering
```

---

## Docker Container Communication Protocol

### Network Configuration

All containers run on the same Docker network: `gbstudio_network`

```yaml
# docker-compose.yml
networks:
  gbstudio_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

**IP Assignment** (for debugging):
- Backend: 172.28.0.10
- Ollama: 172.28.0.11
- ComfyUI: 172.28.0.12
- LangFlow: 172.28.0.13

**DNS Resolution**:
- Containers reference each other by service name
- Example: `http://ollama:11434` resolves to `172.28.0.11:11434`

### Port Mapping

| Service | Internal Port | Host Port | Protocol | Purpose |
|---------|--------------|-----------|----------|---------|
| Backend | 8000 | 8000 | HTTP/WS | API + WebSocket |
| Ollama | 11434 | 11434 | HTTP | LLM inference |
| ComfyUI | 8188 | 8188 | HTTP/WS | Image generation |
| LangFlow | 7860 | 7860 | HTTP | Visual flows (optional) |

### Health Check Protocol

Each service exposes a health endpoint:

**Backend** (`http://backend:8000/health`):
```json
{
  "status": "healthy",
  "timestamp": "2025-01-04T14:00:00Z",
  "uptime_seconds": 3600,
  "services": {
    "ollama": {
      "status": "healthy",
      "latency_ms": 12,
      "models_loaded": ["llama3:8b", "nomic-embed-text"]
    },
    "comfyui": {
      "status": "healthy",
      "latency_ms": 45,
      "queue_remaining": 0,
      "device": "cpu"
    }
  }
}
```

**Ollama** (`http://ollama:11434/api/tags`):
```json
{
  "models": [
    {
      "name": "llama3:8b",
      "modified_at": "2025-01-04T10:00:00Z",
      "size": 4700000000,
      "digest": "sha256:abc123...",
      "details": {
        "format": "gguf",
        "family": "llama",
        "parameter_size": "8B",
        "quantization_level": "Q4_0"
      }
    },
    {
      "name": "nomic-embed-text",
      "modified_at": "2025-01-04T10:05:00Z",
      "size": 1200000000
    }
  ]
}
```

**ComfyUI** (`http://comfyui:8188/system_stats`):
```json
{
  "system": {
    "os": "linux",
    "python_version": "3.11.7",
    "pytorch_version": "2.1.0",
    "embedded_python": true
  },
  "devices": [
    {
      "name": "cpu",
      "type": "cpu",
      "vram_total": 0,
      "vram_free": 0
    }
  ],
  "queue_remaining": 0
}
```

### Request/Response Flow Examples

#### Example 1: PM Agent Conversation

**Request**:
```http
POST /api/v1/prompt HTTP/1.1
Host: backend:8000
Content-Type: application/json
X-Correlation-ID: req_1704398400_8a3f

{
  "message": "Create a knight sprite",
  "session_id": "abc123"
}
```

**Backend → Ollama**:
```http
POST /api/generate HTTP/1.1
Host: ollama:11434
Content-Type: application/json

{
  "model": "llama3",
  "prompt": "You are a Project Manager AI for a Game Boy Color game development studio...\n\nRECENT CONVERSATION:\nUser: What art style should we use?\nPM: Pixel art, 32x32 frames in Game Boy Color palette.\n\nRELEVANT DOCUMENTATION:\n[ArtStyleGuide.md] All sprites must be 32x32 pixels...\n\nUSER REQUEST:\nCreate a knight sprite\n\nRESPOND IN JSON FORMAT:\n{\"response_to_user\": \"...\", \"needs_approval\": true/false, \"delegation_plan\": [...]}",
  "stream": false,
  "options": {
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40
  }
}
```

**Ollama → Backend**:
```json
{
  "model": "llama3",
  "created_at": "2025-01-04T14:00:05Z",
  "response": "{\"response_to_user\": \"I'll create a pixel art knight sprite with 8 animation frames (idle, walk cycle x4, attack x2, hurt). This will follow our established 32x32 pixel format and Game Boy Color palette. Ready to proceed?\", \"needs_approval\": true, \"delegation_plan\": [{\"department\": \"Art\", \"task\": \"Generate knight sprite sheet: 1 idle, 4 walk, 2 attack, 1 hurt frame\", \"details\": {\"style\": \"pixel art\", \"resolution\": \"32x32\", \"frames\": 8}}]}",
  "done": true,
  "total_duration": 1234567890,
  "load_duration": 123456,
  "prompt_eval_count": 245,
  "prompt_eval_duration": 890123456,
  "eval_count": 87,
  "eval_duration": 344444444
}
```

**Response to Frontend**:
```http
HTTP/1.1 200 OK
Content-Type: application/json
X-Correlation-ID: req_1704398400_8a3f
X-Response-Time: 1.234s

{
  "message": "I'll create a pixel art knight sprite with 8 animation frames (idle, walk cycle x4, attack x2, hurt). This will follow our established 32x32 pixel format and Game Boy Color palette. Ready to proceed?",
  "plan": [
    {
      "department": "Art",
      "task": "Generate knight sprite sheet: 1 idle, 4 walk, 2 attack, 1 hurt frame",
      "details": {
        "style": "pixel art",
        "resolution": "32x32",
        "frames": 8
      }
    }
  ],
  "requires_approval": true,
  "session_id": "abc123",
  "correlation_id": "req_1704398400_8a3f"
}
```

#### Example 2: ComfyUI Generation with WebSocket Progress

**Step 1: Submit Workflow**
```http
POST /prompt HTTP/1.1
Host: comfyui:8188
Content-Type: application/json

{
  "prompt": {
    "1": {"class_type": "CheckpointLoaderSimple", ...},
    "2": {"class_type": "LoraLoader", ...},
    ...
  },
  "client_id": "gbstudio_abc123"
}
```

**Response**:
```json
{
  "prompt_id": "def456",
  "number": 1,
  "node_errors": {}
}
```

**Step 2: WebSocket Progress Messages**

Frontend connects to: `ws://comfyui:8188/ws?clientId=gbstudio_abc123`

**Message 1 - Execution Started**:
```json
{
  "type": "execution_start",
  "data": {
    "prompt_id": "def456"
  }
}
```

**Message 2 - Node Executing**:
```json
{
  "type": "executing",
  "data": {
    "node": "6",
    "prompt_id": "def456"
  }
}
```

**Message 3 - Progress Update** (during KSampler):
```json
{
  "type": "progress",
  "data": {
    "value": 15,
    "max": 20,
    "prompt_id": "def456",
    "node": "6"
  }
}
```

**Message 4 - Node Complete**:
```json
{
  "type": "executed",
  "data": {
    "node": "18",
    "prompt_id": "def456",
    "output": {
      "images": [
        {
          "filename": "sprite_sheet_preview_00001.png",
          "subfolder": "",
          "type": "output"
        }
      ]
    }
  }
}
```

**Message 5 - Execution Complete**:
```json
{
  "type": "execution_cached",
  "data": {
    "nodes": [],
    "prompt_id": "def456"
  }
}
```

---

## Validation Criteria with Test Cases

### Test Case 1: Sprite Frame Dimension Validation

**CORRECT Frame**:
```python
from PIL import Image

frame = Image.open('/app/output/sprite_frame_0_00001.png')
assert frame.size == (32, 32), f"Expected (32, 32), got {frame.size}"
assert frame.mode in ['RGB', 'RGBA', 'P'], f"Invalid mode: {frame.mode}"
# ✓ PASS
```

**INCORRECT Frame Examples**:

```python
# Example 1: Wrong dimensions
frame = Image.open('bad_frame_1.png')
frame.size == (64, 64)  # ✗ FAIL: Too large

# Example 2: Wrong aspect ratio
frame = Image.open('bad_frame_2.png')
frame.size == (32, 64)  # ✗ FAIL: Should be square

# Example 3: Empty/corrupt file
frame = Image.open('bad_frame_3.png')
frame.size == (0, 0)  # ✗ FAIL: Corrupt PNG
```

**Expected Error Messages**:
```json
{
  "valid": false,
  "errors": [
    "Frame 0 has incorrect dimensions: (64, 64), expected (32, 32)",
    "Frame 2 has incorrect aspect ratio: (32, 64), must be square",
    "Frame 3 appears to be corrupt: (0, 0)"
  ]
}
```

### Test Case 2: Color Palette Consistency

**CORRECT Palette** (high similarity):

```python
# Frame 0 palette (extracted via KMeans)
palette_0 = np.array([
    [15, 56, 15],    # Dark green
    [48, 98, 48],    # Medium green
    [139, 172, 15],  # Light green
    [155, 188, 15]   # Lightest green
])

# Frame 1 palette
palette_1 = np.array([
    [16, 55, 16],    # Dark green (slightly different due to pose)
    [47, 99, 47],    # Medium green
    [140, 171, 16],  # Light green
    [156, 187, 16]   # Lightest green
])

# Calculate similarity
def calculate_palette_similarity(p1, p2):
    min_distances = []
    for color1 in p1:
        distances = [np.linalg.norm(color1 - color2) for color2 in p2]
        min_distances.append(min(distances))
    avg_distance = np.mean(min_distances)
    similarity = 1.0 - (avg_distance / 441.0)  # 441 = max RGB distance
    return similarity

similarity = calculate_palette_similarity(palette_0, palette_1)
# Result: 0.97 (97% similar) ✓ PASS (threshold: 0.85)
```

**INCORRECT Palette** (low similarity):

```python
# Frame 0: Knight sprite (green armor)
palette_0 = np.array([
    [15, 56, 15],
    [48, 98, 48],
    [139, 172, 15],
    [155, 188, 15]
])

# Frame 1: Different character (red wizard)
palette_1 = np.array([
    [120, 10, 10],   # Red
    [180, 30, 30],   # Light red
    [80, 5, 5],      # Dark red
    [255, 100, 100]  # Bright red
])

similarity = calculate_palette_similarity(palette_0, palette_1)
# Result: 0.23 (23% similar) ✗ FAIL (threshold: 0.85)
```

**Expected Warning**:
```json
{
  "valid": true,
  "warnings": [
    "Frames have inconsistent color palettes (similarity: 0.23, threshold: 0.85). This may indicate different characters or lighting."
  ],
  "metrics": {
    "palette_similarity": 0.23
  }
}
```

### Test Case 3: Blank Frame Detection

**CORRECT Frame** (has content):
```python
frame = Image.open('sprite_frame_0_00001.png')
pixels = np.array(frame)
unique_colors = len(np.unique(pixels.reshape(-1, 3), axis=0))
# Result: 47 unique colors ✓ PASS

total_pixels = 32 * 32  # 1024
uniformity = (total_pixels - unique_colors) / total_pixels
# Result: 0.95 (95% uniformity) - ACCEPTABLE for pixel art
```

**INCORRECT Frame** (blank/single color):
```python
frame = Image.open('bad_blank_frame.png')
pixels = np.array(frame)
unique_colors = len(np.unique(pixels.reshape(-1, 3), axis=0))
# Result: 1 unique color ✗ FAIL

uniformity = (1024 - 1) / 1024
# Result: 0.999 (99.9% uniformity) - TOO HIGH
```

**Expected Error**:
```json
{
  "valid": false,
  "errors": [
    "Frame 3 appears to be blank (99.9% single color)"
  ]
}
```

### Test Case 4: GBStudio Project Integration

**CORRECT Integration**:

```python
import json
from pathlib import Path

# 1. Load existing project
project_path = Path('/app/project_files/MyGBCGame.gbsproj')
with open(project_path, 'r') as f:
    project = json.load(f)

# 2. Verify initial state
assert 'spriteSheets' in project
initial_sprite_count = len(project['spriteSheets'])

# 3. Combine frames into sprite sheet
from PIL import Image

frames = [Image.open(f'/app/output/sprite_frame_{i}_00001.png') for i in range(8)]
sprite_sheet = Image.new('RGBA', (96, 96), (0, 0, 0, 0))

positions = [
    (0, 0), (32, 0), (64, 0),   # Row 1
    (0, 32), (32, 32), (64, 32), # Row 2
    (0, 64), (32, 64)            # Row 3
]

for i, (x, y) in enumerate(positions):
    sprite_sheet.paste(frames[i], (x, y))

# 4. Convert to indexed 4-color
sprite_sheet_rgb = sprite_sheet.convert('RGB')
sprite_sheet_indexed = sprite_sheet_rgb.convert('P', palette=Image.ADAPTIVE, colors=4)

# 5. Save to assets
sprite_filename = 'knight_20250104_143000.png'
sprite_path = Path('/app/project_files/assets/sprites') / sprite_filename
sprite_sheet_indexed.save(sprite_path, 'PNG', optimize=True)

# 6. Add to project JSON
import hashlib
import time

sprite_id = f"sprite_{hashlib.sha256(sprite_filename.encode()).hexdigest()[:8]}"
sprite_entry = {
    "id": sprite_id,
    "name": "Knight",
    "filename": sprite_filename,
    "numFrames": 8,
    "type": "actor_animated",
    "canvasWidth": 32,
    "canvasHeight": 32,
    "_v": int(time.time() * 1000)
}

project['spriteSheets'].append(sprite_entry)

# 7. Save updated project
with open(project_path, 'w') as f:
    json.dump(project, f, indent=2)

# 8. Verify
with open(project_path, 'r') as f:
    updated_project = json.load(f)

assert len(updated_project['spriteSheets']) == initial_sprite_count + 1
assert any(s['id'] == sprite_id for s in updated_project['spriteSheets'])
assert Path(sprite_path).exists()

# ✓ PASS
```

**INCORRECT Integration Examples**:

```python
# Example 1: Forgot to convert to indexed color
sprite_sheet.save(sprite_path, 'PNG')  # Still RGB mode
# ✗ FAIL: GBStudio will reject RGB sprites

# Example 2: Wrong grid layout
sprite_sheet = Image.new('RGBA', (256, 32))  # 8 frames in single row
# ✗ FAIL: GBStudio expects grid, not strip

# Example 3: Missing required fields
sprite_entry = {
    "id": sprite_id,
    "name": "Knight",
    "filename": sprite_filename,
    "numFrames": 8
    # ✗ MISSING: type, canvasWidth, canvasHeight, _v
}

# Example 4: Invalid filename
sprite_filename = 'Knight Sprite.png'  # Contains space
# ✗ FAIL: GBStudio requires lowercase alphanumeric + underscores only
```

**Expected Error Messages**:
```json
{
  "status": "error",
  "errors": [
    "Sprite sheet is not indexed color (mode: RGB, expected: P)",
    "Grid layout is incorrect (dimensions: 256x32, expected: 96x96 for 8 frames)",
    "Missing required fields: type, canvasWidth, canvasHeight, _v",
    "Invalid filename format: 'Knight Sprite.png' (must match [a-z0-9_]+\\.png)"
  ]
}
```

### Test Case 5: End-to-End Generation Performance

**Success Criteria**:

```python
import time

start_time = time.time()

# 1. Submit prompt
response = requests.post('http://localhost:8000/api/v1/prompt', json={
    "message": "Create a knight sprite",
    "session_id": "test_abc123"
})
assert response.status_code == 200
prompt_time = time.time() - start_time
assert prompt_time < 3.0  # PM response within 3 seconds

# 2. Approve plan
response = requests.post('http://localhost:8000/api/v1/execute', json={
    "plan": response.json()['plan'],
    "session_id": "test_abc123"
})
assert response.status_code == 200

# 3. Monitor generation
generation_start = time.time()
prompt_id = response.json()['prompt_id']

while True:
    status = requests.get(f'http://localhost:8188/history/{prompt_id}')
    if prompt_id in status.json():
        break
    time.sleep(2)
    assert time.time() - generation_start < 360  # Max 6 minutes

generation_time = time.time() - generation_start
assert generation_time < 300  # Target: <5 minutes on Intel Mac

# 4. Verify outputs
result = response.json()
assert 'frames' in result
assert len(result['frames']) == 8
assert 'sprite_id' in result

# 5. Check GBStudio project
with open('/app/project_files/MyGBCGame.gbsproj', 'r') as f:
    project = json.load(f)

assert any(s['id'] == result['sprite_id'] for s in project['spriteSheets'])

total_time = time.time() - start_time
print(f"✓ END-TO-END TEST PASSED")
print(f"  PM Response: {prompt_time:.1f}s")
print(f"  Generation: {generation_time:.1f}s")
print(f"  Total: {total_time:.1f}s")
```

**Expected Output**:
```
✓ END-TO-END TEST PASSED
  PM Response: 1.8s
  Generation: 187.3s
  Total: 189.1s
```

---

## Intel-Mac Ventura Specific Configurations

### Dockerfile.intel-mac

**Critical differences from standard Dockerfile**:

```dockerfile
# BASE IMAGE: Must use Bullseye for Rosetta 2 compatibility
FROM python:3.11-slim-bullseye AS builder

# ARCHITECTURE CHECK: Fail fast if running on ARM
RUN [ "$(uname -m)" = "x86_64" ] || (echo "ERROR: This image requires x86_64 architecture" && exit 1)

# PYTORCH: CPU-only build from official index
RUN pip install --no-cache-dir \
    torch==2.1.0 \
    torchvision==0.16.0 \
    --index-url https://download.pytorch.org/whl/cpu

# FAISS: CPU-only version
RUN pip install --no-cache-dir faiss-cpu==1.7.4

# COMFYUI CUSTOM NODES: Install Impact Pack for DynamicTileSplit
WORKDIR /app/ComfyUI/custom_nodes
RUN git clone https://github.com/ltdrdata/ComfyUI-Impact-Pack.git && \
    cd ComfyUI-Impact-Pack && \
    pip install --no-cache-dir -r requirements.txt

# CLEANUP: Aggressive to stay under 600MB
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* ~/.cache/pip

# ENVIRONMENT: Force CPU device
ENV COMFYUI_DEVICE=cpu
ENV PYTORCH_ENABLE_MPS_FALLBACK=0

# HEALTH CHECK: Verify models exist
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
  CMD python -c "import requests; \
    r = requests.get('http://localhost:8000/health', timeout=5); \
    r.raise_for_status(); \
    services = r.json().get('services', {}); \
    assert services.get('ollama', {}).get('models_loaded', []) != [], 'Models not loaded'"
```

### docker-compose.intel-mac.yml

**Volume mounts for persistence**:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.intel-mac
    volumes:
      # CRITICAL: Bind mounts for data persistence across Docker Desktop restarts
      - ./project_files:/app/project_files:rw
      - ./vectorstore:/app/vectorstore:rw
      - ./agent_memory:/app/agent_memory:rw
      - ./temp_outputs:/app/temp_outputs:rw
    environment:
      - COMFYUI_DEVICE=cpu
      - OLLAMA_PULL_ON_START=true
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G

  ollama:
    image: ollama/ollama:latest
    platform: linux/amd64  # CRITICAL: Force x86_64
    volumes:
      - ollama_models:/root/.ollama:rw
    environment:
      - OLLAMA_NUM_THREADS=4
      - OLLAMA_MAX_LOADED_MODELS=2
    command: >
      sh -c "
        ollama serve &
        sleep 5 &&
        ollama pull llama3:8b &&
        ollama pull nomic-embed-text &&
        wait
      "

  comfyui:
    build:
      context: ./comfyui
      dockerfile: Dockerfile.intel-mac
    volumes:
      - comfyui_models:/app/ComfyUI/models:rw
      - comfyui_output:/app/ComfyUI/output:rw
    environment:
      - COMFYUI_DEVICE=cpu
      - PYTORCH_ENABLE_MPS_FALLBACK=0

volumes:
  ollama_models:
    driver: local
  comfyui_models:
    driver: local
  comfyui_output:
    driver: local

networks:
  default:
    name: gbstudio_network
    driver: bridge
```

### start.sh (Intel Mac)

```bash
#!/bin/bash
set -e

echo "🎮 Starting GBStudio Automation Hub (Intel Mac)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check architecture
if [[ $(uname -m) != "x86_64" ]]; then
    echo "❌ ERROR: This script requires Intel (x86_64) architecture"
    echo "   Current: $(uname -m)"
    exit 1
fi

# Check Docker Desktop is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ ERROR: Docker Desktop is not running"
    echo "   Please start Docker Desktop and try again"
    exit 1
fi

# Check Docker compose
if ! docker compose version > /dev/null 2>&1; then
    echo "❌ ERROR: Docker Compose not available"
    echo "   Please install Docker Desktop 4.25 or later"
    exit 1
fi

# Start services
echo "🚀 Starting services..."
docker compose -f docker-compose.intel-mac.yml up -d

# Wait for services with progress
echo ""
echo "⏳ Waiting for services to become healthy..."
echo "   (This may take 5+ minutes on first run while models download)"
echo ""

TIMEOUT=600  # 10 minutes
ELAPSED=0
INTERVAL=5

while [ $ELAPSED -lt $TIMEOUT ]; do
    # Check backend health
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        HEALTH=$(curl -s http://localhost:8000/health)
        
        # Parse service statuses
        OLLAMA_STATUS=$(echo "$HEALTH" | jq -r '.services.ollama.status // "unknown"')
        COMFYUI_STATUS=$(echo "$HEALTH" | jq -r '.services.comfyui.status // "unknown"')
        
        echo "   Backend: ✓  Ollama: $OLLAMA_STATUS  ComfyUI: $COMFYUI_STATUS"
        
        if [[ "$OLLAMA_STATUS" == "healthy" ]] && [[ "$COMFYUI_STATUS" == "healthy" ]]; then
            echo ""
            echo "✅ All services are healthy!"
            echo ""
            echo "🌐 Access the application at: http://localhost:8000"
            echo "📊 Service Monitor: http://localhost:8000/#monitor"
            echo ""
            echo "📝 Logs: docker compose -f docker-compose.intel-mac.yml logs -f"
            echo "🛑 Stop: ./stop.sh"
            exit 0
        fi
    else
        echo "   Waiting for backend to start..."
    fi
    
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

echo ""
echo "❌ Timeout waiting for services to become healthy"
echo "   Check logs: docker compose -f docker-compose.intel-mac.yml logs"
exit 1
```

---

## Next Steps

This document provides the hyper-specific technical foundation. The following artifacts will contain:

**Part B - Implementation Files**:
1. `backend/main.py` - Complete FastAPI backend (800+ lines)
2. `backend/Dockerfile.intel-mac` - Production Dockerfile
3. `docker-compose.intel-mac.yml` - Complete orchestration
4. `backend/memory/knowledge_base.py` - Full FAISS implementation
5. `backend/comfyui/validator.py` - Complete validation logic
6. `backend/gbstudio/project.py` - GBStudio integration
7. `frontend/index.html` - Complete UI
8. `frontend/src/components/monitor.js` - Service monitor
9. `scripts/start.sh` - Production startup script

**Part C - Testing & Validation**:
1. Complete test suite with expected outputs
2. Validation scripts
3. Debugging procedures

