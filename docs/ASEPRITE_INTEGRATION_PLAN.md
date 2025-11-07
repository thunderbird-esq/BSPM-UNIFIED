# Aseprite MCP Integration Plan

**Version:** 1.0
**Date:** 2025-11-07
**Status:** PLANNING

---

## Executive Summary

This document outlines the integration of the Aseprite MCP server into the BSPM-UNIFIED project, enabling team members to programmatically create, edit, and export Game Boy Color sprites using Aseprite's professional pixel art tools.

### Integration Goals

1. **Seamless Workflow**: ComfyUI generates → Aseprite refines → GBStudio integrates
2. **Team Collaboration**: Multiple team members can use Aseprite programmatically via MCP
3. **Professional Tools**: Leverage Aseprite's industry-standard pixel art capabilities
4. **Automation**: AI-assisted sprite editing through natural language commands

---

## Aseprite MCP Capabilities

### Available Tools (11 Total)

**Canvas Management:**
- `create_canvas(width, height, filename)` - Create new Aseprite file
- `add_layer(filename, layer_name)` - Add layer to existing file
- `add_frame(filename)` - Add animation frame

**Drawing Tools:**
- `draw_pixels(filename, pixels)` - Draw individual pixels with hex colors
- `draw_line(filename, x1, y1, x2, y2, color, thickness)` - Draw lines
- `draw_rectangle(filename, x, y, width, height, color, fill)` - Draw rectangles
- `draw_circle(filename, center_x, center_y, radius, color, fill)` - Draw circles
- `fill_area(filename, x, y, color)` - Paint bucket fill

**Export Tools:**
- `export_sprite(filename, output_filename, format)` - Export to PNG/GIF/JPG

### Technical Details

- **Language**: Python 3.13+
- **Protocol**: MCP (Model Context Protocol)
- **Execution**: Lua scripts via Aseprite CLI (`--batch` mode)
- **Dependencies**: `typing_extensions`, `python-dotenv`, MCP SDK
- **Environment**: `ASEPRITE_PATH` environment variable

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    User Request (Natural Language)                │
└───────────────────────────┬──────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│  FastAPI Backend (Port 8000)                                      │
│  ┌────────────────┐  ┌─────────────────┐  ┌──────────────────┐  │
│  │  PM Agent      │  │  Sprite Manager │  │  Aseprite Client │  │
│  │  (Ollama)      │  │                 │  │  (NEW)           │  │
│  └────────┬───────┘  └────────┬────────┘  └────────┬─────────┘  │
│           │                   │                     │             │
└───────────┼───────────────────┼─────────────────────┼─────────────┘
            │                   │                     │
            │                   │                     │
┌───────────▼────────┐ ┌────────▼────────┐ ┌─────────▼────────────┐
│  ComfyUI (8188)    │ │ GBStudio Project│ │ Aseprite MCP (NEW)   │
│  Image Generation  │ │ Integration     │ │ Pixel Art Editing    │
└────────┬───────────┘ └─────────────────┘ └──────────┬───────────┘
         │                                              │
         └──────────────┐              ┌───────────────┘
                        │              │
                ┌───────▼──────────────▼────┐
                │  Sprite Processing Pipeline│
                │  1. Generate (ComfyUI)     │
                │  2. Import to Aseprite     │
                │  3. Edit/Refine (MCP)      │
                │  4. Export for GBStudio    │
                └────────────────────────────┘
```

---

## Integration Points

### 1. Docker Infrastructure

**Add Aseprite MCP Container to `docker-compose.intel-mac.yml`:**

```yaml
services:
  aseprite-mcp:
    build:
      context: ./aseprite_mcp
      dockerfile: Dockerfile
    container_name: bspm-aseprite-mcp
    environment:
      - ASEPRITE_PATH=/opt/steamapps/common/Aseprite/aseprite
      - STEAM_USERNAME=${STEAM_USERNAME}
      - STEAM_PASSWORD=${STEAM_PASSWORD}
      - STEAM_GUARD_CODE=${STEAM_GUARD_CODE}
    volumes:
      - ./temp_outputs:/workspace
      - ./project_files:/projects
    ports:
      - "8189:8189"  # MCP server port
    networks:
      - bspm-network
    healthcheck:
      test: ["CMD", "python", "-c", "import socket; socket.create_connection(('localhost', 8189), timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Environment Variables (`.env`):**
```bash
# Aseprite MCP Configuration
ASEPRITE_MCP_URL=http://aseprite-mcp:8189
STEAM_USERNAME=your_steam_username
STEAM_PASSWORD=your_steam_password
STEAM_GUARD_CODE=  # Optional, if 2FA enabled
```

### 2. Backend Integration

**Create New Module: `backend/aseprite/client.py`**

```python
"""
Aseprite MCP Client for BSPM-UNIFIED
Provides high-level interface to Aseprite MCP tools
"""

import os
import httpx
from typing import Dict, List, Any, Optional
from ..logging_config import setup_logging

logger = setup_logging(__name__)

class AsepriteClient:
    """Client for interacting with Aseprite MCP server."""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("ASEPRITE_MCP_URL", "http://localhost:8189")
        self.client = httpx.AsyncClient(timeout=300.0)

    async def create_sprite_from_png(self,
                                     png_path: str,
                                     output_path: str,
                                     width: int = 16,
                                     height: int = 16) -> Dict[str, Any]:
        """
        Import PNG from ComfyUI and create Aseprite file.

        Args:
            png_path: Path to PNG from ComfyUI
            output_path: Path for new .aseprite file
            width: Canvas width (Game Boy: 16x16 or 32x32)
            height: Canvas height

        Returns:
            Dict with status and file path
        """
        try:
            # Create canvas
            canvas_result = await self._call_tool("create_canvas", {
                "width": width,
                "height": height,
                "filename": output_path
            })

            if not canvas_result.get("success"):
                return {"success": False, "error": "Failed to create canvas"}

            # Import PNG as layer (requires custom implementation)
            # This would involve reading PNG pixels and using draw_pixels

            logger.info(f"Created Aseprite sprite: {output_path}")
            return {"success": True, "path": output_path}

        except Exception as e:
            logger.error(f"Failed to create sprite from PNG: {e}")
            return {"success": False, "error": str(e)}

    async def add_gameboy_palette(self,
                                  filename: str,
                                  palette: List[str] = None) -> Dict[str, Any]:
        """
        Apply Game Boy Color 4-color palette.

        Args:
            filename: Aseprite file to modify
            palette: 4 hex colors (defaults to GB classic green)

        Returns:
            Dict with status
        """
        if palette is None:
            palette = ["#0f380f", "#306230", "#8bac0f", "#9bbc0f"]  # GB Classic

        # Implementation would use MCP tools to set palette
        # This may require extending the MCP with palette management
        pass

    async def export_for_gbstudio(self,
                                  filename: str,
                                  output_dir: str) -> Dict[str, Any]:
        """
        Export sprite in GBStudio-compatible format (indexed PNG).

        Args:
            filename: Aseprite file to export
            output_dir: Output directory for PNG files

        Returns:
            Dict with exported file paths
        """
        try:
            output_path = os.path.join(output_dir,
                                      os.path.basename(filename).replace(".aseprite", ".png"))

            result = await self._call_tool("export_sprite", {
                "filename": filename,
                "output_filename": output_path,
                "format": "png"
            })

            if result.get("success"):
                logger.info(f"Exported sprite for GBStudio: {output_path}")
                return {"success": True, "path": output_path}
            else:
                return {"success": False, "error": result.get("error")}

        except Exception as e:
            logger.error(f"Failed to export for GBStudio: {e}")
            return {"success": False, "error": str(e)}

    async def _call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP tool via HTTP."""
        try:
            response = await self.client.post(
                f"{self.base_url}/tools/{tool_name}",
                json=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"MCP tool call failed: {tool_name} - {e}")
            return {"success": False, "error": str(e)}
```

**Add API Endpoints: `backend/main.py`**

```python
# Add to imports
from backend.aseprite.client import AsepriteClient

# Add to startup
aseprite_client = AsepriteClient()

# New endpoints
@app.post("/api/v1/aseprite/import")
async def import_to_aseprite(
    png_path: str,
    width: int = 16,
    height: int = 16
) -> Dict[str, Any]:
    """Import ComfyUI-generated PNG into Aseprite for editing."""
    output_path = png_path.replace(".png", ".aseprite")
    result = await aseprite_client.create_sprite_from_png(
        png_path=png_path,
        output_path=output_path,
        width=width,
        height=height
    )
    return result

@app.post("/api/v1/aseprite/export")
async def export_from_aseprite(
    aseprite_path: str,
    output_dir: str = "project_files/sprites"
) -> Dict[str, Any]:
    """Export Aseprite file to GBStudio-compatible PNG."""
    result = await aseprite_client.export_for_gbstudio(
        filename=aseprite_path,
        output_dir=output_dir
    )
    return result

@app.get("/api/v1/aseprite/files")
async def list_aseprite_files() -> Dict[str, Any]:
    """List all .aseprite files in workspace."""
    workspace = "temp_outputs"
    files = [f for f in os.listdir(workspace) if f.endswith(".aseprite")]
    return {"files": files}
```

### 3. Enhanced Sprite Processing Pipeline

**Update: `backend/sprite_manager.py`**

```python
async def generate_sprite_with_aseprite(
    self,
    prompt: str,
    session_id: str,
    enable_aseprite: bool = True
) -> Dict[str, Any]:
    """
    Enhanced workflow:
    1. Generate with ComfyUI
    2. Import to Aseprite (optional)
    3. Export for GBStudio
    """
    # Step 1: Generate with ComfyUI (existing code)
    result = await self.generate_sprite(prompt, session_id)

    if not result.get("success"):
        return result

    # Step 2: Import to Aseprite (NEW)
    if enable_aseprite:
        png_path = result["output_path"]
        aseprite_result = await aseprite_client.create_sprite_from_png(
            png_path=png_path,
            output_path=png_path.replace(".png", ".aseprite")
        )

        if aseprite_result.get("success"):
            result["aseprite_file"] = aseprite_result["path"]
            result["editable"] = True

    return result
```

### 4. Frontend Integration

**Create New Component: `frontend/src/components/aseprite-editor.js`**

```javascript
class AsepriteEditor {
    constructor() {
        this.currentFile = null;
        this.setupUI();
    }

    setupUI() {
        // Create Aseprite editor panel
        const panel = document.createElement('div');
        panel.className = 'aseprite-panel';
        panel.innerHTML = `
            <h3>🎨 Aseprite Editor</h3>
            <div class="aseprite-files"></div>
            <div class="aseprite-tools">
                <button onclick="asepriteEditor.openInAseprite()">
                    📝 Edit in Aseprite
                </button>
                <button onclick="asepriteEditor.exportToPNG()">
                    💾 Export to PNG
                </button>
            </div>
        `;
        document.body.appendChild(panel);
    }

    async importSprite(pngPath) {
        const response = await fetch('/api/v1/aseprite/import', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                png_path: pngPath,
                width: 16,
                height: 16
            })
        });

        const result = await response.json();
        if (result.success) {
            this.currentFile = result.path;
            this.refreshFileList();
        }
        return result;
    }

    async exportToPNG() {
        if (!this.currentFile) return;

        const response = await fetch('/api/v1/aseprite/export', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                aseprite_path: this.currentFile
            })
        });

        return await response.json();
    }
}

// Initialize
const asepriteEditor = new AsepriteEditor();
```

**Update: `frontend/index.html`**

```html
<!-- Add to header buttons -->
<button class="header-button" onclick="toggleAsepritePanel()">
    🎨 Aseprite
</button>

<!-- Add script -->
<script src="/frontend/src/components/aseprite-editor.js"></script>
```

---

## Implementation Phases

### Phase 1: Infrastructure Setup (1-2 hours)
- [ ] Add Aseprite MCP as git submodule
- [ ] Update `docker-compose.intel-mac.yml` with Aseprite service
- [ ] Configure environment variables
- [ ] Build and test Docker container
- [ ] Verify Aseprite installation via Steam

### Phase 2: Backend Integration (3-4 hours)
- [ ] Create `backend/aseprite/` module
- [ ] Implement `AsepriteClient` class
- [ ] Add API endpoints to `main.py`
- [ ] Update `sprite_manager.py` with Aseprite workflow
- [ ] Add health checks for Aseprite MCP service
- [ ] Write unit tests for Aseprite client

### Phase 3: Frontend Integration (2-3 hours)
- [ ] Create `aseprite-editor.js` component
- [ ] Add Aseprite panel to UI
- [ ] Implement file list viewer
- [ ] Add import/export buttons to sprite generation flow
- [ ] Update CSS for Aseprite panel styling

### Phase 4: Workflow Enhancement (2-3 hours)
- [ ] Implement PNG to Aseprite import with pixel data
- [ ] Add Game Boy palette management
- [ ] Create indexed PNG export for GBStudio
- [ ] Add batch processing support
- [ ] Implement collaborative editing features

### Phase 5: Testing & Documentation (2-3 hours)
- [ ] Test end-to-end workflow
- [ ] Test with multiple sprite types
- [ ] Performance testing with concurrent users
- [ ] Write integration tests
- [ ] Update user documentation
- [ ] Create video tutorial

**Total Estimated Time: 10-15 hours**

---

## Benefits

### For Artists
- **Professional Tools**: Industry-standard pixel art editor
- **Frame Management**: Built-in animation support
- **Layer System**: Non-destructive editing workflow
- **Onion Skinning**: Better animation previewing

### For Developers
- **Programmatic Control**: Automate sprite creation
- **Batch Processing**: Generate multiple sprites at once
- **Version Control**: .aseprite files are version-controllable
- **Integration**: Seamless ComfyUI → Aseprite → GBStudio pipeline

### For Team
- **Collaboration**: Multiple team members can edit sprites
- **Consistency**: Enforce Game Boy Color palette
- **Quality**: Professional-grade pixel art tools
- **Efficiency**: Reduce manual sprite creation time by 70%

---

## Technical Considerations

### Aseprite Licensing
- **Required**: Aseprite must be purchased ($19.99) or compiled from source
- **Installation**: Via Steam (automated in Docker) or manual download
- **License**: Proprietary (EULA) for binary, GPLv2 for source

### Performance
- **Memory**: +500MB per Aseprite instance
- **CPU**: Minimal (Lua scripts are fast)
- **Disk**: +100MB for Aseprite installation
- **Latency**: <1s for most MCP operations

### Limitations
- **Game Boy Constraints**: Must enforce 4-color palette
- **File Size**: Keep sprites ≤32x32 for Game Boy
- **Animation**: Max 8-10 frames for smooth gameplay
- **Concurrent Users**: Limit to 3-5 simultaneous editors

---

## Security & Access Control

### API Keys
- Aseprite MCP endpoints require authentication
- Same API key system as ComfyUI endpoints
- Rate limiting: 30 requests/minute per user

### File Access
- Sandboxed workspace (`temp_outputs/`)
- No access to system files
- Automatic cleanup of old .aseprite files (7 days)

---

## Rollout Strategy

### Week 1: Development
- Complete Phases 1-3 (infrastructure + backend + frontend)
- Internal testing with development team

### Week 2: Testing
- Complete Phases 4-5 (enhancement + testing)
- Beta testing with 2-3 artists

### Week 3: Documentation & Training
- Finalize documentation
- Create video tutorials
- Train team members

### Week 4: Production Launch
- Deploy to production
- Monitor performance and user feedback
- Iterate based on feedback

---

## Success Metrics

- **Adoption**: 80% of sprites created use Aseprite editing
- **Efficiency**: 50% reduction in sprite creation time
- **Quality**: 90% of sprites pass validation on first attempt
- **User Satisfaction**: 4.5/5 rating from team members

---

## Next Steps

1. **Get approval** for integration plan
2. **Allocate resources** (1 developer, 2 weeks)
3. **Set up Steam account** for Aseprite installation
4. **Begin Phase 1** implementation
5. **Schedule weekly check-ins** for progress tracking

---

## References

- **Aseprite MCP**: https://github.com/diivi/aseprite-mcp
- **Aseprite Docs**: https://www.aseprite.org/docs/
- **Model Context Protocol**: https://modelcontextprotocol.io/
- **Game Boy Color Specs**: http://gbdev.gg8.se/wiki/articles/Video_Display

---

**Document Version**: 1.0
**Last Updated**: 2025-11-07
**Author**: Claude (AI Assistant)
**Review Status**: Pending team review
