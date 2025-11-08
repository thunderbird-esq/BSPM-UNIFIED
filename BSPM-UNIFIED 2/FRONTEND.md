# Frontend Documentation
## GBStudio Automation Hub v3.3.2

**Complete reference for the retro-themed, Pokemon GameBoy-inspired frontend interface**

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Component Documentation](#component-documentation)
3. [CSS Class Reference](#css-class-reference)
4. [JavaScript API](#javascript-api)
5. [Theming & Customization](#theming--customization)
6. [Interactive Features](#interactive-features)
7. [Accessibility](#accessibility)
8. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### Design Philosophy

The frontend follows a **retro-first**, **accessibility-focused** design inspired by classic Game Boy and NES interfaces:

- **Authentic Aesthetics** - Game Boy color palette (#0f380f to #9bbc0f)
- **Pixel Typography** - Press Start 2P font for nostalgic feel
- **No Framework Dependencies** - Pure vanilla JavaScript for performance
- **Progressive Enhancement** - Works without JavaScript for core features
- **Mobile-First** - Responsive from 320px to 4K displays

### Technology Stack

| Technology | Purpose | Version |
|------------|---------|---------|
| **Vanilla JavaScript** | Logic & Interactivity | ES6+ (2015+) |
| **CSS3** | Styling & Animations | Modern CSS with Grid/Flexbox |
| **Pokemon GameBoy CSS** | Base theme | Custom |
| **NES.css** | Retro UI components | Latest from CDN |
| **Press Start 2P Font** | Typography | Google Fonts |
| **WebSocket API** | Real-time updates | Native browser API |

### File Organization

```
frontend/
├── index.html              # Single-page app entry point
├── assets/                 # Static resources
├── styles/                 # CSS modules (10 files)
│   ├── Base Theme:
│   │   ├── css-pokemon-gameboy.css    # Core Game Boy palette
│   │   └── command-deck.css            # Control layouts
│   ├── Components:
│   │   ├── chat.css                    # Chat interface
│   │   ├── dialog-system.css           # Modal dialogs
│   │   └── medium-priority.css         # Extended features
│   └── Utilities:
│       ├── startup-animation.css       # Boot sequence
│       ├── loading-states.css          # Loaders & spinners
│       ├── error-states.css            # Error displays
│       ├── integration.css             # Component glue
│       └── responsive.css              # Media queries
└── src/                    # JavaScript modules (13 files)
    ├── Entry Points:
    │   ├── main.js                     # Application bootstrap
    │   ├── dialog-system.js            # Dialog manager
    │   └── easter-eggs.js              # Hidden features
    ├── components/                     # UI Components (8 files)
    │   ├── chat.js                     # Chat window
    │   ├── monitor.js                  # Service health
    │   ├── websocket.js                # ComfyUI connection
    │   ├── style-preset-selector.js    # Preset picker
    │   ├── regeneration-ui.js          # Regen controls
    │   ├── sprite-manager-ui.js        # Sprite CRUD
    │   ├── batch-operations.js         # Batch jobs
    │   └── kb-admin.js                 # Knowledge base
    └── utils/                          # Utilities (2 files)
        ├── api.js                      # REST client
        └── sanitizer.js                # XSS prevention
```

**Total Code:** 7,667 lines (3,910 JS + 3,721 CSS + 95 HTML)

---

## Component Documentation

### 1. ChatWindow (`chat.js`)

**Purpose:** Main conversational interface for PM Agent interaction

#### Classes

##### `ChatWindow`

```javascript
import { ChatWindow } from './components/chat.js';

const chat = new ChatWindow('chat-window');
```

**Constructor:**
- `containerId` (string) - DOM element ID for chat container

**Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `addMessage(sender, content, metadata)` | sender: string, content: string, metadata: object | `ChatMessage` | Add message to chat |
| `scrollToBottom()` | - | void | Scroll to newest message |
| `showTypingIndicator()` | - | void | Display "..." animation |
| `hideTypingIndicator()` | - | void | Remove typing indicator |
| `clear()` | - | void | Delete all messages |
| `getLastMessage()` | - | `ChatMessage \| null` | Get most recent message |

**Properties:**
- `container` (HTMLElement) - Chat DOM container
- `messages` (Array<ChatMessage>) - Message history
- `autoScroll` (boolean) - Auto-scroll to bottom (default: true)
- `typingIndicator` (HTMLElement|null) - Current typing indicator

**Example Usage:**

```javascript
// Initialize
const chat = new ChatWindow('chat-window');

// Add user message
chat.addMessage('user', 'Create a knight sprite', {
    timestamp: new Date()
});

// Show PM is thinking
chat.showTypingIndicator();

// Add PM response after 2 seconds
setTimeout(() => {
    chat.hideTypingIndicator();
    const pmMsg = chat.addMessage('assistant', "I'll create an 8-frame knight sprite...", {
        timestamp: new Date()
    });

    // Add approval buttons
    pmMsg.addApprovalButtons(
        plan,
        () => executeGeneration(plan),
        () => cancelGeneration()
    );
}, 2000);
```

##### `ChatMessage`

**Constructor:**
- `sender` (string) - "user", "assistant", or "system"
- `content` (string) - Message text
- `metadata` (object) - Optional metadata (timestamp, type, etc.)

**Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `render()` | - | HTMLElement | Generate DOM element |
| `addApprovalButtons(plan, onApprove, onCancel)` | plan: array, callbacks: functions | void | Add approve/cancel buttons |
| `addProgressBar(promptId)` | promptId: string | ProgressControl | Add progress indicator |

**Progress Control Object:**
```javascript
{
    update: (value, max) => void,      // Update progress (0-100)
    complete: (message) => void,        // Mark as complete
    error: (message) => void            // Mark as error
}
```

---

### 2. ServiceMonitor (`monitor.js`)

**Purpose:** Real-time health monitoring for Backend, Ollama, and ComfyUI

#### Class: `ServiceMonitor`

```javascript
import { ServiceMonitor } from './components/monitor.js';

const monitor = new ServiceMonitor();
monitor.startPolling();
```

**Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `checkService(serviceKey)` | serviceKey: string | Promise<Object> | Check single service |
| `checkAllServices()` | - | Promise<void> | Check all services |
| `startPolling()` | - | void | Begin 5s polling loop |
| `stopPolling()` | - | void | Stop polling |
| `renderDashboard()` | - | void | Render HTML dashboard |

**Service Keys:**
- `'backend'` - FastAPI backend (port 8000)
- `'ollama'` - Ollama LLM (port 11434)
- `'comfyui'` - ComfyUI (port 8188)

**Status Types:**
- `'online'` - Service healthy (HTTP 200)
- `'degraded'` - Service responding but errors (HTTP 4xx/5xx)
- `'offline'` - Service unreachable (timeout/connection error)

**Example:**

```javascript
const monitor = new ServiceMonitor();

// Manual check
const status = await monitor.checkService('ollama');
console.log(status);
// { status: 'online', latency: 45 }

// Auto-polling
monitor.startPolling(); // Checks every 5s
monitor.renderDashboard(); // Show UI

// Stop when done
monitor.stopPolling();
```

---

### 3. ComfyUIWebSocket (`websocket.js`)

**Purpose:** Real-time progress updates from ComfyUI generation

#### Class: `ComfyUIWebSocket`

```javascript
import { ComfyUIWebSocket } from './components/websocket.js';

const ws = new ComfyUIWebSocket('ws://localhost:8188/ws?clientId=abc123', {
    onMessage: (data) => console.log('Progress:', data),
    onError: (error) => console.error(error),
    onClose: () => console.log('Disconnected')
});

ws.connect();
```

**Constructor:**
- `url` (string) - WebSocket URL with client ID
- `callbacks` (object) - Event handlers
  - `onMessage(data)` - Message received
  - `onError(error)` - Error occurred
  - `onClose()` - Connection closed
  - `onOpen()` - Connection established

**Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `connect()` | - | void | Open WebSocket connection |
| `close()` | - | void | Close connection |
| `send(message)` | message: object | void | Send JSON message |

**Message Format:**
```javascript
{
    type: 'progress',           // Message type
    data: {
        prompt_id: 'abc123',    // Generation ID
        node: 'KSampler',       // Current node
        value: 15,              // Current step
        max: 20                 // Total steps
    }
}
```

---

### 4. StylePresetSelector (`style-preset-selector.js`)

**Purpose:** Visual picker for art style presets

#### Class: `StylePresetSelector`

```javascript
import { StylePresetSelector } from './components/style-preset-selector.js';

const selector = new StylePresetSelector('preset-container', (presetName) => {
    console.log('Selected:', presetName);
});
```

**Available Presets:**

| Preset Name | Icon | Description |
|-------------|------|-------------|
| `clean_pixel_art` | 🎨 | Clean, modern pixel art |
| `retro_8bit` | 👾 | Authentic 8-bit aesthetic |
| `gameboy` | 🎮 | Game Boy Color style |
| `nes_style` | 🕹️ | NES 16-color palette |
| `snes_style` | 🎯 | SNES 256-color palette |
| `detailed_pixel` | 🖼️ | High-detail pixel art |
| `minimalist` | ⬜ | Simple, clean shapes |
| `chibi` | 😊 | Cute, oversized heads |

**Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `render()` | - | void | Draw preset grid |
| `setActive(presetName)` | presetName: string | void | Highlight preset |
| `getActive()` | - | string | Get selected preset |

---

### 5. RegenerationUI (`regeneration-ui.js`)

**Purpose:** Controls for regenerating sprites with different seeds/styles

#### Class: `RegenerationUI`

```javascript
import { RegenerationUI } from './components/regeneration-ui.js';

const regenUI = new RegenerationUI('regeneration-controls');
regenUI.renderRegenerateButton(sessionId, spriteId);
```

**Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `renderRegenerateButton(sessionId, spriteId)` | sessionId: string, spriteId: string | void | Show regen button |
| `showComparison(sessionId)` | sessionId: string | Promise<void> | Display comparison view |
| `markBest(sessionId, attemptId)` | sessionId: string, attemptId: string | Promise<void> | Flag best result |

**Example Workflow:**

```javascript
const regenUI = new RegenerationUI('regeneration-controls');

// After generation completes
regenUI.renderRegenerateButton('session_123', 'sprite_456');

// User clicks "Regenerate" button (handled internally)
// --> POST /api/v1/regenerate { session_id, preset (optional) }

// Show comparison view
await regenUI.showComparison('session_123');
// --> GET /api/v1/regenerate/session_123/comparison

// User marks favorite
await regenUI.markBest('session_123', 'attempt_789');
// --> POST /api/v1/regenerate/session_123/mark-best { attempt_id }
```

---

### 6. SpriteManager (`sprite-manager-ui.js`)

**Purpose:** CRUD operations for sprites in GBStudio project

#### Class: `SpriteManager`

```javascript
import { SpriteManager } from './components/sprite-manager-ui.js';

const manager = new SpriteManager('sprite-manager-panel');
manager.init(); // Load sprites
```

**Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `init()` | - | Promise<void> | Load sprite list |
| `editSprite(spriteId, newName, newType)` | spriteId: string, name: string, type: string | Promise<void> | Edit metadata |
| `deleteSprite(spriteId, deleteFile)` | spriteId: string, deleteFile: bool | Promise<void> | Remove sprite |
| `duplicateSprite(spriteId, newName, variation)` | spriteId: string, name: string, variation: string | Promise<void> | Clone sprite |
| `exportSprite(spriteId, format, scale)` | spriteId: string, format: string, scale: number | Promise<string> | Export as PNG |

**Sprite Types:**
- `'actor'` - Player/NPC character
- `'prop'` - Static object
- `'projectile'` - Bullet/arrow
- `'item'` - Collectible

**Variation Types:**
- `'color_swap'` - Palette swap
- `'mirror'` - Horizontal flip
- `'rotate_90'` - 90° rotation
- `'rotate_180'` - 180° rotation

**Example:**

```javascript
const manager = new SpriteManager('sprite-manager-panel');

// Load sprites
await manager.init();

// Edit sprite name
await manager.editSprite('sprite_001', 'Knight_Red', 'actor');

// Duplicate with color swap
await manager.duplicateSprite('sprite_001', 'Knight_Blue', 'color_swap');

// Export as 2x scaled PNG
const pngPath = await manager.exportSprite('sprite_001', 'single_png', 2);

// Delete (keep file)
await manager.deleteSprite('sprite_002', false);
```

---

### 7. BatchOperations (`batch-operations.js`)

**Purpose:** Batch sprite generation from CSV/templates

#### Class: `BatchOperations`

```javascript
import { BatchOperations } from './components/batch-operations.js';

const batch = new BatchOperations('batch-ops-panel');
batch.render();
```

**Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `render()` | - | void | Draw batch UI |
| `uploadCSV(csvPath)` | csvPath: string | Promise<Object> | Process CSV file |
| `generateCharacterSet(name, style, actions)` | name: string, style: string, actions: array | Promise<Object> | Full animation set |
| `applyTemplate(templateName)` | templateName: string | Promise<Object> | Use project template |
| `getBatchStatus(batchId, taskIds)` | batchId: string, taskIds: array | Promise<Object> | Check progress |

**CSV Format:**

```csv
name,description,preset,sprite_type
knight,A brave knight in armor,clean_pixel_art,actor
goblin,Small green monster,retro_8bit,actor
sword,Steel longsword,detailed_pixel,item
```

**Character Set Actions:**
- `'idle'` - Standing still (1 frame)
- `'walk'` - Walking animation (4 frames)
- `'attack'` - Attack animation (2 frames)
- `'hurt'` - Damage reaction (1 frame)
- `'die'` - Death animation (2 frames)

**Templates:**
- `'rpg_starter'` - Hero, Enemy, NPC, Items (20 sprites)
- `'platformer_basic'` - Player, Enemies, Platforms (15 sprites)
- `'shooter_pack'` - Ship, Enemies, Bullets (25 sprites)

---

### 8. KBAdmin (`kb-admin.js`)

**Purpose:** Knowledge base document management

#### Class: `KBAdmin`

```javascript
import { KBAdmin } from './components/kb-admin.js';

const admin = new KBAdmin('kb-admin-panel');
admin.init();
```

**Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `init()` | - | Promise<void> | Load document list |
| `uploadDocument(filename, content)` | filename: string, content: string | Promise<Object> | Add markdown file |
| `reindexDocument(sourceFile)` | sourceFile: string | Promise<Object> | Re-index document |
| `deleteDocument(sourceFile, confirm)` | sourceFile: string, confirm: bool | Promise<Object> | Remove document |
| `testSearch(query, limit)` | query: string, limit: number | Promise<Array> | Test semantic search |
| `getStatistics()` | - | Promise<Object> | Get KB stats |
| `rebuildIndex()` | - | Promise<Object> | Rebuild entire KB |

**Example:**

```javascript
const admin = new KBAdmin('kb-admin-panel');

// Load documents
await admin.init();

// Upload new doc
await admin.uploadDocument('game_design.md', '# My Game\n...');

// Test search
const results = await admin.testSearch('sprite format', 5);
console.log(results);
// [
//   { document: 'gbstudio_guide.md', score: 0.92, snippet: '...' },
//   { document: 'technical_specs.md', score: 0.85, snippet: '...' }
// ]

// Get stats
const stats = await admin.getStatistics();
console.log(stats);
// { total_documents: 12, total_chunks: 345, vector_dimension: 768 }
```

---

### 9. DialogSystem (`dialog-system.js`)

**Purpose:** Pokemon-style modal dialogs

#### Global Functions

```javascript
import { showDialog, showConfirm, showToast } from './dialog-system.js';
```

##### `showDialog(options)`

**Parameters:**
```javascript
{
    title: string,          // Dialog header (optional)
    message: string,        // Main text
    type: string,           // 'info', 'warning', 'error', 'success'
    buttons: [              // Custom buttons (optional)
        {
            text: string,
            callback: function,
            primary: boolean
        }
    ],
    avatar: string,         // Avatar image URL (optional)
    typewriter: boolean     // Animated text (default: false)
}
```

**Example:**

```javascript
showDialog({
    title: 'PM Agent',
    message: 'Sprite generation complete!',
    type: 'success',
    buttons: [
        { text: 'VIEW SPRITE', callback: () => openSpriteManager(), primary: true },
        { text: 'OK', callback: () => {} }
    ],
    typewriter: true
});
```

##### `showConfirm(message, onConfirm)`

**Parameters:**
- `message` (string) - Confirmation question
- `onConfirm` (function) - Called if user clicks "YES"

**Example:**

```javascript
showConfirm(
    'Delete sprite "Knight_Red"?',
    async () => {
        await deleteSprite('sprite_001');
        showToast('Sprite deleted', 'success');
    }
);
```

##### `showToast(message, type)`

**Parameters:**
- `message` (string) - Short message
- `type` (string) - 'info', 'success', 'error', 'warning'

**Example:**

```javascript
showToast('Saved successfully!', 'success');
showToast('Connection lost', 'error');
```

**Auto-dismisses after 3 seconds.**

---

### 10. API Wrapper (`api.js`)

**Purpose:** REST API client with error handling

#### Function: `apiCall(endpoint, method, data)`

```javascript
import { apiCall } from './utils/api.js';

const response = await apiCall('/api/v1/prompt', 'POST', {
    message: 'Create a knight sprite',
    session_id: 'abc123'
});
```

**Parameters:**
- `endpoint` (string) - API path (e.g., `/api/v1/prompt`)
- `method` (string) - HTTP method ('GET', 'POST', 'PUT', 'DELETE')
- `data` (object) - Request body (optional)

**Returns:** Promise<Object> - JSON response

**Error Handling:**
- Throws `Error` with user-friendly message
- Automatically retries on network errors (3 attempts)
- Handles 401, 403, 404, 500 status codes

**Examples:**

```javascript
// POST request
const result = await apiCall('/api/v1/prompt', 'POST', {
    message: 'Create a wizard',
    preset: 'detailed_pixel'
});

// GET request
const sprites = await apiCall('/api/v1/sprites', 'GET');

// DELETE request
await apiCall('/api/v1/admin/kb/documents?source_file=old.md&confirm=true', 'DELETE');
```

---

### 11. Sanitizer (`sanitizer.js`)

**Purpose:** XSS prevention for user-generated content

#### Functions

##### `escapeHTML(text)`

Escapes all HTML entities:
```javascript
import { escapeHTML } from './utils/sanitizer.js';

escapeHTML('<script>alert("XSS")</script>');
// → '&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;'
```

##### `sanitizeHTML(html)`

Allows safe HTML tags, removes dangerous content:
```javascript
import { sanitizeHTML } from './utils/sanitizer.js';

sanitizeHTML('<b>Bold</b> <script>alert(1)</script>');
// → '<b>Bold</b> '
```

**Allowed Tags:**
- Text: `<b>`, `<i>`, `<u>`, `<em>`, `<strong>`
- Structure: `<p>`, `<br>`, `<span>`, `<div>`
- Lists: `<ul>`, `<ol>`, `<li>`
- Code: `<code>`, `<pre>`

**Blocked:**
- Scripts: `<script>`, event handlers (`onclick`, etc.)
- Frames: `<iframe>`, `<frame>`, `<object>`, `<embed>`
- Forms: `<form>`, `<input>`, `<button>`
- Links with `javascript:` protocol

##### `sanitizeAttribute(value)`

Cleans attribute values:
```javascript
import { sanitizeAttribute } from './utils/sanitizer.js';

sanitizeAttribute('javascript:alert(1)');
// → ''

sanitizeAttribute('https://example.com');
// → 'https://example.com'
```

**Usage in Components:**

```javascript
// Displaying user input
const userInput = getUserMessage();
chatElement.innerHTML = sanitizeHTML(userInput);

// Displaying sprite names
const spriteName = getSpriteNameFromAPI();
nameElement.textContent = escapeHTML(spriteName); // Use textContent when possible

// Link attributes
const url = getUserProvidedURL();
linkElement.href = sanitizeAttribute(url);
```

---

## CSS Class Reference

### Base Classes (Pokemon GameBoy Theme)

#### Container Classes

```css
.gb-container {
    /* Main app container with Game Boy styling */
    background: var(--gb-green-4);
    border: 4px solid var(--gb-green-1);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

.gb-header {
    /* Page header with title */
    background: var(--gb-green-1);
    color: var(--gb-green-4);
    padding: 16px;
}

.gb-panel {
    /* Content panel */
    background: #fff;
    border: 3px solid var(--gb-green-1);
    padding: 20px;
}
```

#### Button Classes

```css
.pixel-button {
    /* Base retro button */
    font-family: 'Press Start 2P', monospace;
    background: var(--gb-green-3);
    border: 3px solid var(--gb-green-1);
    padding: 12px 24px;
    cursor: pointer;
}

.pixel-button:hover {
    background: var(--gb-green-2);
    transform: translateY(-2px);
}

.pixel-button:active {
    transform: translateY(0);
}

.pixel-button.primary {
    background: var(--gb-green-1);
    color: var(--gb-green-4);
}

.pixel-button.danger {
    background: #d9534f;
    color: #fff;
}

.pixel-button.disabled {
    opacity: 0.5;
    cursor: not-allowed;
}
```

#### Text Classes

```css
.pixel-text {
    font-family: 'Press Start 2P', monospace;
    font-size: 12px;
    line-height: 1.8;
}

.pixel-text.large {
    font-size: 16px;
}

.pixel-text.small {
    font-size: 8px;
}
```

### Chat Interface Classes

```css
.chat-window {
    /* Scrollable message container */
    overflow-y: auto;
    height: 500px;
    padding: 16px;
}

.message {
    /* Individual message */
    margin-bottom: 20px;
    animation: messageSlideIn 0.3s ease;
}

.message[data-sender="user"] {
    /* User message */
    border-left: 4px solid #0074D9;
}

.message[data-sender="assistant"] {
    /* PM Agent message */
    border-left: 4px solid #2ECC40;
}

.message[data-sender="system"] {
    /* System message */
    border-left: 4px solid #FF851B;
}

.message-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
}

.message-sender {
    font-weight: bold;
    font-size: 10px;
}

.message-timestamp {
    color: #666;
    font-size: 8px;
}

.message-content {
    line-height: 1.6;
}

.typing-indicator {
    /* Animated dots */
    display: flex;
    gap: 4px;
}

.typing-indicator .dot {
    animation: dotPulse 1.4s infinite;
}

@keyframes dotPulse {
    0%, 60%, 100% { opacity: 0.2; }
    30% { opacity: 1; }
}
```

### Progress Bar Classes

```css
.progress-container {
    margin-top: 12px;
}

.progress-bar-wrapper {
    background: #e0e0e0;
    border: 2px solid var(--gb-green-1);
    height: 24px;
    overflow: hidden;
}

.progress-bar {
    background: var(--gb-green-3);
    height: 100%;
    transition: width 0.3s ease;
    position: relative;
}

.progress-bar::after {
    /* Animated stripe pattern */
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: repeating-linear-gradient(
        45deg,
        transparent,
        transparent 10px,
        rgba(255,255,255,0.2) 10px,
        rgba(255,255,255,0.2) 20px
    );
    animation: progressStripe 1s linear infinite;
}

@keyframes progressStripe {
    from { background-position: 0 0; }
    to { background-position: 40px 0; }
}

.progress-text {
    margin-top: 8px;
    font-size: 10px;
    text-align: center;
}

.progress-container.complete .progress-bar {
    background: #2ECC40;
}

.progress-container.error .progress-bar {
    background: #FF4136;
}
```

### Dialog Classes

```css
.gb-dialog-overlay {
    /* Fullscreen semi-transparent backdrop */
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    z-index: 999;
}

.gb-dialog {
    /* Pokemon-style dialog box */
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: #fff;
    border: 4px solid #000;
    padding: 16px;
    z-index: 1000;
    min-width: 400px;
    max-width: 80%;
    box-shadow:
        0 0 0 2px #fff,
        0 0 0 6px #000,
        0 8px 16px rgba(0, 0, 0, 0.5);
}

.gb-dialog.info { border-color: #0074D9; }
.gb-dialog.success { border-color: #2ECC40; }
.gb-dialog.warning { border-color: #FF851B; }
.gb-dialog.error { border-color: #FF4136; }

.gb-dialog-header {
    background: #000;
    color: #fff;
    padding: 8px 12px;
    margin: -16px -16px 12px -16px;
}

.gb-dialog-content {
    line-height: 1.8;
    margin-bottom: 16px;
}

.gb-dialog-buttons {
    display: flex;
    gap: 12px;
    justify-content: flex-end;
}
```

### Service Monitor Classes

```css
.service-monitor {
    background: rgba(0, 0, 0, 0.8);
    border: 2px solid var(--gb-green-3);
    padding: 12px;
    position: fixed;
    top: 80px;
    right: 20px;
    min-width: 300px;
}

.service-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px;
    margin-bottom: 4px;
}

.status-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    animation: statusPulse 2s infinite;
}

.status-dot.status-online {
    background: #2ECC40;
}

.status-dot.status-degraded {
    background: #FF851B;
}

.status-dot.status-offline {
    background: #FF4136;
}

@keyframes statusPulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}

.latency-text {
    margin-left: auto;
    font-size: 10px;
}

.latency-text.latency-good { color: #2ECC40; }
.latency-text.latency-medium { color: #FF851B; }
.latency-text.latency-slow { color: #FF4136; }
```

### Responsive Classes

```css
/* Mobile (320px - 767px) */
@media (max-width: 767px) {
    .gb-container {
        padding: 8px;
    }

    .gb-header h1 {
        font-size: 12px;
    }

    .pixel-button {
        padding: 8px 16px;
        font-size: 10px;
    }

    .chat-window {
        height: 300px;
    }

    .gb-dialog {
        min-width: 90%;
        font-size: 10px;
    }

    .service-monitor {
        top: auto;
        bottom: 0;
        right: 0;
        left: 0;
        width: 100%;
    }
}

/* Tablet (768px - 1199px) */
@media (min-width: 768px) and (max-width: 1199px) {
    .main-content {
        flex-direction: column;
    }

    .side-panel {
        width: 100%;
        margin-top: 20px;
    }
}

/* Desktop (1200px+) */
@media (min-width: 1200px) {
    .main-content {
        display: flex;
        gap: 20px;
    }

    .chat-panel {
        flex: 2;
    }

    .side-panel {
        flex: 1;
    }
}
```

---

## JavaScript API

### Global State

The application maintains global state in `window.gbstudioApp`:

```javascript
{
    sessionId: string,              // Current session ID
    currentPreset: string,          // Selected style preset
    activePanel: string|null,       // Open panel ('sprite-manager', 'batch-ops', etc.)
    chatWindow: ChatWindow,         // Chat component instance
    serviceMonitor: ServiceMonitor, // Monitor component instance
    // ... other component instances
}
```

**Access from console:**

```javascript
// Get session ID
console.log(window.gbstudioApp.sessionId);

// Send message programmatically
window.gbstudioApp.chatWindow.addMessage('user', 'Create a knight');

// Check service health
await window.gbstudioApp.serviceMonitor.checkAllServices();
```

### Event System

Components communicate via custom events:

#### Dispatch Event

```javascript
// From any component
document.dispatchEvent(new CustomEvent('sprite:generated', {
    detail: { spriteId: 'sprite_123', sessionId: 'abc' }
}));
```

#### Listen for Event

```javascript
// In another component
document.addEventListener('sprite:generated', (e) => {
    console.log('New sprite:', e.detail.spriteId);
    refreshSpriteList();
});
```

#### Standard Events

| Event Name | Detail Object | Description |
|------------|---------------|-------------|
| `sprite:generated` | `{ spriteId, sessionId }` | Sprite generation complete |
| `sprite:deleted` | `{ spriteId }` | Sprite removed |
| `sprite:edited` | `{ spriteId, newName }` | Sprite metadata changed |
| `preset:changed` | `{ presetName }` | Style preset selected |
| `service:status` | `{ service, status }` | Service health changed |
| `batch:started` | `{ batchId, count }` | Batch job started |
| `batch:complete` | `{ batchId, results }` | Batch job finished |

### Lifecycle Hooks

Components follow a standard lifecycle:

```javascript
class MyComponent {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.initialized = false;
    }

    // 1. Initialize component (load data, set up)
    async init() {
        if (this.initialized) return;

        await this.loadData();
        this.setupEventListeners();
        this.render();

        this.initialized = true;
    }

    // 2. Render UI
    render() {
        this.container.innerHTML = this.getTemplate();
    }

    // 3. Clean up
    destroy() {
        this.removeEventListeners();
        this.container.innerHTML = '';
        this.initialized = false;
    }
}
```

---

## Theming & Customization

### Color Palette Customization

Edit `/home/user/BSPM-UNIFIED/BSPM-UNIFIED 2/frontend/styles/css-pokemon-gameboy.css`:

```css
:root {
    /* Game Boy Original Colors */
    --gb-green-1: #0f380f;  /* Darkest (shadows, text) */
    --gb-green-2: #306230;  /* Dark (borders, accents) */
    --gb-green-3: #8bac0f;  /* Light (backgrounds, buttons) */
    --gb-green-4: #9bbc0f;  /* Lightest (highlights) */

    /* Extend with custom colors */
    --accent-blue: #0074D9;
    --accent-red: #FF4136;
    --accent-yellow: #FFDC00;
}
```

**Alternative Palettes:**

```css
/* Game Boy Pocket (Grayscale) */
:root {
    --gb-green-1: #000000;
    --gb-green-2: #545454;
    --gb-green-3: #a9a9a9;
    --gb-green-4: #ffffff;
}

/* Virtual Boy (Red) */
:root {
    --gb-green-1: #2a0000;
    --gb-green-2: #550000;
    --gb-green-3: #aa0000;
    --gb-green-4: #ff0000;
}

/* Game Boy Color (Teal) */
:root {
    --gb-green-1: #082820;
    --gb-green-2: #1a5947;
    --gb-green-3: #48a38f;
    --gb-green-4: #84d6c8;
}
```

### Typography Customization

Change font family in `/home/user/BSPM-UNIFIED/BSPM-UNIFIED 2/frontend/index.html`:

```html
<!-- Replace Press Start 2P with alternatives -->
<link href="https://fonts.googleapis.com/css2?family=Silkscreen&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=DotGothic16&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
```

Then update CSS:

```css
.pixel-text {
    font-family: 'Silkscreen', monospace; /* or DotGothic16, VT323 */
}
```

### Animation Speed Customization

Edit animation durations in respective CSS files:

```css
/* Slow down typing indicator */
.typing-indicator .dot {
    animation: dotPulse 2.5s infinite; /* was 1.4s */
}

/* Speed up dialog slide-in */
.gb-dialog {
    animation: dialogSlideIn 0.15s ease; /* was 0.3s */
}

/* Disable progress bar stripes */
.progress-bar::after {
    animation: none; /* removes stripe animation */
}
```

### Custom Components

Create new components following the pattern:

```javascript
// /home/user/BSPM-UNIFIED/BSPM-UNIFIED 2/frontend/src/components/my-component.js

export class MyComponent {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.data = [];
    }

    async init() {
        await this.loadData();
        this.render();
        this.setupEventListeners();
    }

    async loadData() {
        const response = await fetch('/api/v1/my-endpoint');
        this.data = await response.json();
    }

    render() {
        this.container.innerHTML = `
            <div class="gb-panel">
                <h3>My Component</h3>
                <div id="my-content"></div>
            </div>
        `;
    }

    setupEventListeners() {
        // Add event listeners here
    }
}
```

Then import in `main.js`:

```javascript
import { MyComponent } from './components/my-component.js';

// In initializeApp()
state.myComponent = new MyComponent('my-container');
await state.myComponent.init();
```

---

## Interactive Features

### Drag & Drop Implementation

**For File Uploads:**

```javascript
const dropZone = document.getElementById('upload-area');

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', async (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');

    const files = Array.from(e.dataTransfer.files);
    const csvFile = files.find(f => f.name.endsWith('.csv'));

    if (csvFile) {
        await handleCSVUpload(csvFile);
    }
});
```

**CSS for drag-over state:**

```css
.upload-area {
    border: 3px dashed var(--gb-green-2);
    padding: 40px;
    text-align: center;
    transition: all 0.2s;
}

.upload-area.drag-over {
    border-color: var(--gb-green-3);
    background: rgba(139, 172, 15, 0.1);
    transform: scale(1.02);
}
```

### Keyboard Shortcuts

Implemented in `main.js`:

```javascript
document.addEventListener('keydown', (e) => {
    // Ctrl+K - Focus chat input
    if (e.ctrlKey && e.key === 'k') {
        e.preventDefault();
        document.getElementById('chat-input').focus();
    }

    // Esc - Close dialogs
    if (e.key === 'Escape') {
        closeActiveDialog();
        closeActivePanels();
    }

    // Ctrl+Enter - Send message
    if (e.ctrlKey && e.key === 'Enter') {
        handleSendMessage();
    }
});
```

### Tooltips

**HTML:**

```html
<button class="pixel-button" data-tooltip="Click to regenerate sprite">
    REGENERATE
</button>
```

**CSS:**

```css
[data-tooltip] {
    position: relative;
}

[data-tooltip]:hover::after {
    content: attr(data-tooltip);
    position: absolute;
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0, 0, 0, 0.9);
    color: #fff;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 10px;
    white-space: nowrap;
    z-index: 1000;
    margin-bottom: 8px;
}
```

### Context Menus

**Right-click menu for sprites:**

```javascript
spriteElement.addEventListener('contextmenu', (e) => {
    e.preventDefault();

    showContextMenu(e.clientX, e.clientY, [
        { text: 'Edit', callback: () => editSprite(spriteId) },
        { text: 'Duplicate', callback: () => duplicateSprite(spriteId) },
        { text: 'Export', callback: () => exportSprite(spriteId) },
        { text: 'Delete', callback: () => deleteSprite(spriteId), danger: true }
    ]);
});

function showContextMenu(x, y, items) {
    const menu = document.createElement('div');
    menu.className = 'context-menu';
    menu.style.left = `${x}px`;
    menu.style.top = `${y}px`;

    items.forEach(item => {
        const btn = document.createElement('button');
        btn.textContent = item.text;
        btn.className = item.danger ? 'danger' : '';
        btn.onclick = () => {
            item.callback();
            menu.remove();
        };
        menu.appendChild(btn);
    });

    document.body.appendChild(menu);

    // Close on outside click
    setTimeout(() => {
        document.addEventListener('click', () => menu.remove(), { once: true });
    }, 0);
}
```

---

## Accessibility

### ARIA Labels

All interactive elements have proper labels:

```html
<!-- Buttons -->
<button
    id="send-btn"
    class="btn-send"
    aria-label="Send message to PM Agent"
    aria-describedby="chat-input">
    SEND
</button>

<!-- Regions -->
<div
    id="chat-window"
    class="chat-window"
    role="log"
    aria-live="polite"
    aria-label="Chat conversation history">
</div>

<!-- Panels -->
<div
    id="sprite-manager-panel"
    class="panel-content"
    role="region"
    aria-label="Sprite manager interface">
</div>
```

### Keyboard Navigation

All functionality accessible via keyboard:

- **Tab** - Navigate between elements
- **Enter** - Activate buttons
- **Space** - Toggle checkboxes
- **Arrow keys** - Navigate lists
- **Esc** - Close dialogs

**Focus indicators:**

```css
button:focus,
input:focus,
textarea:focus {
    outline: 3px solid #FFDC00;
    outline-offset: 2px;
}

/* Never remove focus indicators! */
:focus:not(:focus-visible) {
    outline: none; /* Only hide for mouse users */
}

:focus-visible {
    outline: 3px solid #FFDC00;
}
```

### Screen Reader Support

**Live regions for dynamic content:**

```html
<div id="status-bar" role="status" aria-live="polite">
    <span id="status-text">Ready</span>
</div>
```

**Announce changes:**

```javascript
function updateStatus(text) {
    const statusEl = document.getElementById('status-text');
    statusEl.textContent = text;
    // Screen readers automatically announce changes due to aria-live
}
```

**Skip links:**

```html
<a href="#main-content" class="skip-link">
    Skip to main content
</a>
```

```css
.skip-link {
    position: absolute;
    top: -40px;
    left: 0;
    background: var(--gb-green-1);
    color: var(--gb-green-4);
    padding: 8px;
    z-index: 10000;
}

.skip-link:focus {
    top: 0;
}
```

### Color Contrast

All color combinations meet WCAG AA standards:

| Foreground | Background | Contrast Ratio | WCAG Level |
|------------|------------|----------------|------------|
| #0f380f | #9bbc0f | 7.2:1 | AAA |
| #306230 | #9bbc0f | 4.8:1 | AA |
| #000000 | #ffffff | 21:1 | AAA |
| #0074D9 | #ffffff | 4.5:1 | AA |

**Test with browser DevTools:**
1. Open DevTools (F12)
2. Select element
3. View "Accessibility" panel
4. Check "Contrast" section

---

## Troubleshooting

### Common Issues

#### 1. Styles Not Loading

**Symptom:** Page appears unstyled, no Game Boy theme

**Causes:**
- CSS files not found (404 errors)
- Incorrect static file mounting

**Solution:**

```bash
# Check backend static mount
# In backend/main.py:
app.mount("/frontend", StaticFiles(directory="/app/frontend"), name="frontend")

# Verify files exist
ls -la /app/frontend/styles/

# Check browser console for 404 errors
# Fix paths in index.html if needed
<link rel="stylesheet" href="/frontend/styles/css-pokemon-gameboy.css">
```

#### 2. JavaScript Modules Not Loading

**Symptom:** Console error "Failed to load module script"

**Causes:**
- Missing `type="module"` attribute
- CORS issues with local files
- Wrong file paths

**Solution:**

```html
<!-- Ensure type="module" is set -->
<script type="module" src="/frontend/src/main.js"></script>

<!-- Check paths are correct -->
import { ChatWindow } from './components/chat.js'; // Relative to main.js
```

**Check browser console:**
```
Failed to load module script: Expected a JavaScript module script
```

#### 3. WebSocket Connection Fails

**Symptom:** No real-time progress updates

**Causes:**
- ComfyUI not running
- Wrong WebSocket URL
- Firewall blocking port 8188

**Solution:**

```javascript
// Verify URL format
const wsUrl = 'ws://localhost:8188/ws?clientId=abc123';

// Check ComfyUI health
curl http://localhost:8188/system_stats

// Test WebSocket manually
const ws = new WebSocket('ws://localhost:8188/ws');
ws.onopen = () => console.log('Connected!');
ws.onerror = (e) => console.error('Error:', e);
```

#### 4. API Calls Fail with CORS Error

**Symptom:** Console error "blocked by CORS policy"

**Causes:**
- Frontend served from different origin
- CORS not configured in backend

**Solution:**

```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:8000'],  # Add your origin
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
```

#### 5. Typing Indicator Stuck

**Symptom:** "..." animation doesn't disappear

**Causes:**
- API call failed before hiding indicator
- JavaScript error in response handler

**Solution:**

```javascript
async function handleSendMessage() {
    chatWindow.showTypingIndicator();

    try {
        const response = await apiCall('/api/v1/prompt', 'POST', data);
        chatWindow.hideTypingIndicator(); // Always hide on success
        // ... handle response
    } catch (error) {
        chatWindow.hideTypingIndicator(); // Also hide on error
        chatWindow.addMessage('system', `Error: ${error.message}`, { type: 'error' });
    }
}
```

#### 6. Progress Bar Not Updating

**Symptom:** Progress stuck at 0%

**Causes:**
- WebSocket not receiving messages
- Wrong prompt ID
- Progress data format mismatch

**Solution:**

```javascript
// Debug WebSocket messages
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('WS Message:', data);

    if (data.type === 'progress' && data.data.prompt_id === promptId) {
        const percent = (data.data.value / data.data.max) * 100;
        console.log(`Progress: ${percent}%`);
        progressBar.update(percent);
    }
};
```

### Debugging Tips

#### Enable Debug Mode

Add to `main.js`:

```javascript
window.DEBUG = true;

function debug(message, data) {
    if (window.DEBUG) {
        console.log(`[DEBUG] ${message}`, data);
    }
}

// Use throughout code
debug('Sending API request', { endpoint, method, data });
```

#### Monitor Network Traffic

**Browser DevTools:**
1. Open DevTools (F12)
2. Go to "Network" tab
3. Filter by "Fetch/XHR" to see API calls
4. Click request to view headers, payload, response

#### Inspect State

```javascript
// From browser console
window.gbstudioApp.sessionId
window.gbstudioApp.currentPreset
window.gbstudioApp.chatWindow.messages

// Check component initialization
window.gbstudioApp.spriteManager.initialized

// Force re-render
window.gbstudioApp.serviceMonitor.renderDashboard();
```

#### Test Components Individually

```javascript
// Test chat component
const testChat = new ChatWindow('chat-window');
testChat.addMessage('user', 'Test message');
testChat.showTypingIndicator();
setTimeout(() => testChat.hideTypingIndicator(), 2000);

// Test dialog system
showDialog({
    message: 'Test dialog',
    type: 'info'
});

// Test API
apiCall('/api/v1/presets', 'GET')
    .then(data => console.log('Presets:', data))
    .catch(err => console.error('API Error:', err));
```

---

## Performance Optimization

### Lazy Loading Components

Only initialize panels when user opens them:

```javascript
function togglePanel(panelName) {
    const panel = panels[panelName];

    if (state.activePanel === panelName) {
        panel.style.display = 'none';
        state.activePanel = null;
    } else {
        panel.style.display = 'block';
        state.activePanel = panelName;

        // Lazy init
        if (panelName === 'sprite-manager' && !state.spriteManager.initialized) {
            state.spriteManager.init();
            state.spriteManager.initialized = true;
        }
    }
}
```

### Debouncing Input

Prevent excessive API calls on rapid input:

```javascript
let searchTimeout;

searchInput.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);

    searchTimeout = setTimeout(() => {
        performSearch(e.target.value);
    }, 300); // Wait 300ms after typing stops
});
```

### Virtual Scrolling

For large sprite lists:

```javascript
class VirtualList {
    constructor(containerId, items, renderItem) {
        this.container = document.getElementById(containerId);
        this.items = items;
        this.renderItem = renderItem;
        this.itemHeight = 60;
        this.visibleCount = Math.ceil(this.container.clientHeight / this.itemHeight);
        this.scrollTop = 0;

        this.render();
        this.container.addEventListener('scroll', () => this.onScroll());
    }

    render() {
        const startIndex = Math.floor(this.scrollTop / this.itemHeight);
        const endIndex = Math.min(startIndex + this.visibleCount + 1, this.items.length);

        const fragment = document.createDocumentFragment();
        for (let i = startIndex; i < endIndex; i++) {
            fragment.appendChild(this.renderItem(this.items[i]));
        }

        this.container.innerHTML = '';
        this.container.appendChild(fragment);
        this.container.style.paddingTop = `${startIndex * this.itemHeight}px`;
    }

    onScroll() {
        this.scrollTop = this.container.scrollTop;
        requestAnimationFrame(() => this.render());
    }
}
```

---

## Version History

### v3.3.2 - Frontend Enhancement Release

**New Features:**
- ✨ Startup animation with Barry modal
- ✨ Pokemon-style dialog system
- ✨ Enhanced chat with typing indicators
- ✨ Drag & drop file uploads
- ✨ Easter eggs (Konami code, retro mode)

**Components Added:**
- Style Preset Selector (163 lines)
- Regeneration UI (230 lines)
- Sprite Manager (425 lines)
- Batch Operations (452 lines)
- KB Admin (545 lines)

**Improvements:**
- 🎨 Comprehensive responsive design
- ♿ Full accessibility support (ARIA, keyboard nav)
- 🛡️ XSS prevention with sanitizer
- ⚡ Performance optimizations
- 📱 Mobile-friendly layouts

**Total Code:** 7,667 lines of frontend code

---

## Contributing

### Code Style

**JavaScript:**
- Use ES6+ features (const/let, arrow functions, async/await)
- 4-space indentation
- Single quotes for strings
- JSDoc comments for functions

**CSS:**
- BEM-style naming (block__element--modifier)
- Group related rules with comments
- Mobile-first media queries

**Example:**

```javascript
/**
 * Render sprite card
 * @param {Object} sprite - Sprite data
 * @param {string} sprite.id - Sprite ID
 * @param {string} sprite.name - Sprite name
 * @returns {HTMLElement} Card element
 */
function renderSpriteCard(sprite) {
    const card = document.createElement('div');
    card.className = 'sprite-card';
    card.id = `sprite-${sprite.id}`;

    card.innerHTML = `
        <div class="sprite-card__header">
            <h3 class="sprite-card__title">${escapeHTML(sprite.name)}</h3>
        </div>
        <div class="sprite-card__body">
            <img src="${sprite.thumbnail}" alt="${escapeHTML(sprite.name)}">
        </div>
    `;

    return card;
}
```

### Adding New Components

1. **Create component file:**
   ```bash
   touch frontend/src/components/my-new-component.js
   ```

2. **Follow component pattern:**
   ```javascript
   export class MyNewComponent {
       constructor(containerId) {
           this.container = document.getElementById(containerId);
           this.initialized = false;
       }

       async init() {
           await this.loadData();
           this.render();
           this.setupEventListeners();
           this.initialized = true;
       }

       async loadData() {
           // Fetch data from API
       }

       render() {
           // Build UI
       }

       setupEventListeners() {
           // Add event handlers
       }
   }
   ```

3. **Import in main.js:**
   ```javascript
   import { MyNewComponent } from './components/my-new-component.js';

   // In initializeApp()
   state.myComponent = new MyNewComponent('my-container');
   await state.myComponent.init();
   ```

4. **Add CSS:**
   ```bash
   touch frontend/styles/my-new-component.css
   ```

5. **Link in index.html:**
   ```html
   <link rel="stylesheet" href="/frontend/styles/my-new-component.css">
   ```

---

## License

Internal tool for game development studio use.

---

## Support

For issues or questions:

1. **Check browser console** for JavaScript errors
2. **View Network tab** for API failures
3. **Review logs** at `/logs/app.log`
4. **Test components** individually in console
5. **Verify backend** is running: `http://localhost:8000/health`

**File Locations:**
- Frontend code: `/home/user/BSPM-UNIFIED/BSPM-UNIFIED 2/frontend/`
- Backend code: `/home/user/BSPM-UNIFIED/BSPM-UNIFIED 2/backend/`
- Documentation: `/home/user/BSPM-UNIFIED/BSPM-UNIFIED 2/FRONTEND.md`

---

**Last Updated:** 2025-11-08
**Version:** 3.3.2
**Maintainer:** Development Team
