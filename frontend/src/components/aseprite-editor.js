/**
 * Aseprite Editor Panel Component
 * Version: 1.0
 *
 * Frontend UI for managing Aseprite files through the MCP server
 * - Import PNG sprites to .aseprite format
 * - Export .aseprite files to PNG
 * - Browse and manage .aseprite files
 * - Add frames to existing files
 * - Real-time health monitoring
 */

const API_BASE_URL = 'http://localhost:8000';
const MAX_RETRIES = 3;
const INITIAL_RETRY_DELAY = 1000;

/**
 * Fetch wrapper with retry logic for Aseprite API calls
 */
async function fetchWithRetry(url, options = {}, retries = 0) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }

        return response;

    } catch (error) {
        if (retries < MAX_RETRIES) {
            const delay = INITIAL_RETRY_DELAY * Math.pow(2, retries);
            console.warn(`[Aseprite API] Request failed, retrying in ${delay}ms (attempt ${retries + 1}/${MAX_RETRIES})...`);
            await new Promise(resolve => setTimeout(resolve, delay));
            return fetchWithRetry(url, options, retries + 1);
        }
        throw error;
    }
}

/**
 * Generic API call wrapper
 */
async function apiCall(endpoint, method = 'GET', body = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };

    if (body && method !== 'GET') {
        options.body = JSON.stringify(body);
    }

    const response = await fetchWithRetry(`${API_BASE_URL}${endpoint}`, options);
    return await response.json();
}

/**
 * Main Aseprite Editor Class
 */
class AsepriteEditor {
    constructor() {
        this.currentFile = null;
        this.fileList = [];
        this.isOpen = false;
        this.healthCheckInterval = null;
        this.healthStatus = 'unknown';

        // Initialize on page load
        this.init();
    }

    /**
     * Initialize the component
     */
    init() {
        this.setupUI();
        this.setupEventListeners();
        this.refreshFileList();
        this.startHealthMonitoring();
    }

    /**
     * Create the panel HTML structure
     */
    setupUI() {
        const panelContainer = document.getElementById('aseprite-panel');
        if (!panelContainer) {
            console.error('[Aseprite] Panel container not found');
            return;
        }

        panelContainer.innerHTML = `
            <div class="aseprite-panel-inner">
                <!-- Panel Header -->
                <div class="aseprite-header">
                    <div class="header-title">
                        <span class="title-icon">🎨</span>
                        <h2>ASEPRITE EDITOR</h2>
                    </div>
                    <button class="close-panel-btn" id="close-aseprite-panel" title="Close Panel">
                        ✕
                    </button>
                </div>

                <!-- Health Status Bar -->
                <div class="health-status-bar">
                    <div class="status-indicator">
                        <span class="status-dot status-unknown" id="health-dot"></span>
                        <span class="status-text" id="health-text">Checking...</span>
                    </div>
                    <button class="refresh-btn pixel-button" id="refresh-health" title="Refresh Health">
                        🔄
                    </button>
                </div>

                <!-- File Browser Section -->
                <div class="file-browser-section">
                    <div class="section-header">
                        <h3>📁 FILE BROWSER</h3>
                        <button class="refresh-btn pixel-button" id="refresh-files" title="Refresh Files">
                            🔄 REFRESH
                        </button>
                    </div>

                    <div class="file-list" id="aseprite-file-list">
                        <div class="loading-state">Loading files...</div>
                    </div>
                </div>

                <!-- Current File Preview -->
                <div class="current-file-section" id="current-file-section" style="display: none;">
                    <div class="section-header">
                        <h3>📄 CURRENT FILE</h3>
                    </div>

                    <div class="file-details" id="file-details">
                        <div class="detail-row">
                            <span class="detail-label">Name:</span>
                            <span class="detail-value" id="file-name">-</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Size:</span>
                            <span class="detail-value" id="file-size">-</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Modified:</span>
                            <span class="detail-value" id="file-modified">-</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Type:</span>
                            <span class="detail-value" id="file-type">-</span>
                        </div>
                    </div>

                    <!-- File Actions -->
                    <div class="file-actions">
                        <button class="pixel-button primary" id="btn-export" disabled>
                            💾 EXPORT PNG
                        </button>
                        <button class="pixel-button" id="btn-add-frame" disabled>
                            ➕ ADD FRAME
                        </button>
                    </div>
                </div>

                <!-- Import Section -->
                <div class="import-section">
                    <div class="section-header">
                        <h3>📥 IMPORT SPRITE</h3>
                    </div>

                    <div class="import-form">
                        <div class="form-group">
                            <label for="png-path">PNG File Path:</label>
                            <input
                                type="text"
                                id="png-path"
                                class="pixel-input"
                                placeholder="/path/to/sprite.png"
                            >
                        </div>

                        <button class="pixel-button primary full-width" id="btn-import">
                            📥 IMPORT TO ASEPRITE
                        </button>
                    </div>
                </div>

                <!-- Status Messages -->
                <div class="status-messages" id="status-messages"></div>

                <!-- Info Section -->
                <div class="info-section">
                    <div class="info-box">
                        <p class="info-text">
                            💡 <strong>TIP:</strong> Import PNG sprites to create editable .aseprite files.
                            Select a file to export or add animation frames.
                        </p>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Close panel button
        const closeBtn = document.getElementById('close-aseprite-panel');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.togglePanel());
        }

        // Refresh buttons
        const refreshHealthBtn = document.getElementById('refresh-health');
        if (refreshHealthBtn) {
            refreshHealthBtn.addEventListener('click', () => this.checkHealth());
        }

        const refreshFilesBtn = document.getElementById('refresh-files');
        if (refreshFilesBtn) {
            refreshFilesBtn.addEventListener('click', () => this.refreshFileList());
        }

        // Import button
        const importBtn = document.getElementById('btn-import');
        if (importBtn) {
            importBtn.addEventListener('click', () => this.handleImport());
        }

        // Export button
        const exportBtn = document.getElementById('btn-export');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.handleExport());
        }

        // Add frame button
        const addFrameBtn = document.getElementById('btn-add-frame');
        if (addFrameBtn) {
            addFrameBtn.addEventListener('click', () => this.handleAddFrame());
        }

        // Enter key in PNG path input
        const pngPathInput = document.getElementById('png-path');
        if (pngPathInput) {
            pngPathInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.handleImport();
                }
            });
        }
    }

    /**
     * Toggle panel visibility
     */
    togglePanel() {
        const panel = document.getElementById('aseprite-panel');
        if (!panel) return;

        this.isOpen = !this.isOpen;

        if (this.isOpen) {
            panel.classList.add('open');
            this.refreshFileList();
            this.checkHealth();
        } else {
            panel.classList.remove('open');
        }
    }

    /**
     * Check Aseprite MCP server health
     */
    async checkHealth() {
        const healthDot = document.getElementById('health-dot');
        const healthText = document.getElementById('health-text');

        if (!healthDot || !healthText) return;

        try {
            const response = await apiCall('/api/v1/aseprite/health', 'GET');

            if (response.status === 'healthy') {
                this.healthStatus = 'healthy';
                healthDot.className = 'status-dot status-healthy';
                healthText.textContent = 'Healthy';
                healthText.style.color = 'var(--gb-light)';
            } else {
                this.healthStatus = 'degraded';
                healthDot.className = 'status-dot status-degraded';
                healthText.textContent = 'Degraded';
                healthText.style.color = '#f0ad4e';
            }
        } catch (error) {
            this.healthStatus = 'unhealthy';
            healthDot.className = 'status-dot status-unhealthy';
            healthText.textContent = 'Offline';
            healthText.style.color = '#d9534f';
            console.error('[Aseprite] Health check failed:', error);
        }
    }

    /**
     * Start periodic health monitoring
     */
    startHealthMonitoring() {
        // Check immediately
        this.checkHealth();

        // Then check every 30 seconds
        this.healthCheckInterval = setInterval(() => {
            if (this.isOpen) {
                this.checkHealth();
            }
        }, 30000);
    }

    /**
     * Stop health monitoring
     */
    stopHealthMonitoring() {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
            this.healthCheckInterval = null;
        }
    }

    /**
     * Refresh the file list
     */
    async refreshFileList() {
        const fileListContainer = document.getElementById('aseprite-file-list');
        if (!fileListContainer) return;

        try {
            fileListContainer.innerHTML = '<div class="loading-state">Loading files...</div>';

            const response = await apiCall('/api/v1/aseprite/files', 'GET');
            this.fileList = response.files || [];

            if (this.fileList.length === 0) {
                fileListContainer.innerHTML = `
                    <div class="empty-state">
                        <p>No .aseprite files found</p>
                        <p class="empty-hint">Import a PNG to get started</p>
                    </div>
                `;
                return;
            }

            // Render file list
            const fileItems = this.fileList.map(file => this.renderFileItem(file)).join('');
            fileListContainer.innerHTML = fileItems;

            // Attach click handlers
            fileListContainer.querySelectorAll('.file-item').forEach(item => {
                item.addEventListener('click', () => {
                    const filename = item.dataset.filename;
                    this.selectFile(filename);
                });
            });

        } catch (error) {
            console.error('[Aseprite] Failed to load files:', error);
            fileListContainer.innerHTML = `
                <div class="error-state">
                    <p>❌ Failed to load files</p>
                    <p class="error-hint">${error.message}</p>
                </div>
            `;
        }
    }

    /**
     * Render a single file item
     */
    renderFileItem(file) {
        const sizeKB = (file.size / 1024).toFixed(1);
        const date = new Date(file.modified);
        const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();

        return `
            <div class="file-item" data-filename="${file.name}">
                <div class="file-icon">📄</div>
                <div class="file-info">
                    <div class="file-name">${file.name}</div>
                    <div class="file-meta">
                        <span>${sizeKB} KB</span>
                        <span>•</span>
                        <span>${dateStr}</span>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Select a file from the list
     */
    selectFile(filename) {
        // Update UI to show selected state
        document.querySelectorAll('.file-item').forEach(item => {
            if (item.dataset.filename === filename) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });

        // Find the file in the list
        const file = this.fileList.find(f => f.name === filename);
        if (!file) return;

        this.currentFile = file;

        // Show current file section
        const currentFileSection = document.getElementById('current-file-section');
        if (currentFileSection) {
            currentFileSection.style.display = 'block';
        }

        // Update file details
        document.getElementById('file-name').textContent = file.name;
        document.getElementById('file-size').textContent = `${(file.size / 1024).toFixed(1)} KB`;

        const date = new Date(file.modified);
        document.getElementById('file-modified').textContent =
            date.toLocaleDateString() + ' ' + date.toLocaleTimeString();

        document.getElementById('file-type').textContent = file.type || '.aseprite';

        // Enable action buttons
        document.getElementById('btn-export').disabled = false;
        document.getElementById('btn-add-frame').disabled = false;

        this.showStatus(`Selected: ${filename}`, 'info');
    }

    /**
     * Handle import button click
     */
    async handleImport() {
        const pngPathInput = document.getElementById('png-path');
        const pngPath = pngPathInput.value.trim();

        if (!pngPath) {
            this.showStatus('Please enter a PNG file path', 'error');
            return;
        }

        try {
            this.showStatus('Importing sprite...', 'info');

            const response = await apiCall('/api/v1/aseprite/import', 'POST', {
                png_path: pngPath
            });

            this.showStatus(`✅ Successfully imported: ${response.aseprite_file}`, 'success');

            // Clear input
            pngPathInput.value = '';

            // Refresh file list
            await this.refreshFileList();

        } catch (error) {
            console.error('[Aseprite] Import failed:', error);
            this.showStatus(`❌ Import failed: ${error.message}`, 'error');
        }
    }

    /**
     * Handle export button click
     */
    async handleExport() {
        if (!this.currentFile) {
            this.showStatus('No file selected', 'error');
            return;
        }

        try {
            this.showStatus('Exporting to PNG...', 'info');

            const response = await apiCall('/api/v1/aseprite/export', 'POST', {
                aseprite_path: this.currentFile.path,
                output_path: this.currentFile.path.replace('.aseprite', '_export.png')
            });

            this.showStatus(`✅ Exported to: ${response.png_file}`, 'success');

            // Note: Actual file download would require additional backend support
            // For now, we just show the success message with the path

        } catch (error) {
            console.error('[Aseprite] Export failed:', error);
            this.showStatus(`❌ Export failed: ${error.message}`, 'error');
        }
    }

    /**
     * Handle add frame button click
     */
    async handleAddFrame() {
        if (!this.currentFile) {
            this.showStatus('No file selected', 'error');
            return;
        }

        try {
            this.showStatus('Adding frame...', 'info');

            const response = await apiCall('/api/v1/aseprite/frame', 'POST', {
                aseprite_path: this.currentFile.path
            });

            this.showStatus(`✅ Frame added: ${response.message}`, 'success');

            // Refresh file info
            await this.refreshFileList();

        } catch (error) {
            console.error('[Aseprite] Add frame failed:', error);
            this.showStatus(`❌ Add frame failed: ${error.message}`, 'error');
        }
    }

    /**
     * Show status message
     */
    showStatus(message, type = 'info') {
        const container = document.getElementById('status-messages');
        if (!container) return;

        const statusEl = document.createElement('div');
        statusEl.className = `status-message status-${type}`;
        statusEl.textContent = message;

        container.appendChild(statusEl);

        // Fade in
        setTimeout(() => {
            statusEl.classList.add('show');
        }, 10);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            statusEl.classList.remove('show');
            setTimeout(() => {
                statusEl.remove();
            }, 300);
        }, 5000);
    }

    /**
     * Handle errors and display user-friendly messages
     */
    handleError(error, context = '') {
        console.error(`[Aseprite] Error in ${context}:`, error);

        let message = error.message || 'An unknown error occurred';

        // Provide user-friendly error messages
        if (message.includes('Failed to fetch')) {
            message = 'Cannot connect to Aseprite server. Is it running?';
        } else if (message.includes('404')) {
            message = 'API endpoint not found. Check server configuration.';
        } else if (message.includes('500')) {
            message = 'Server error. Check Aseprite MCP logs.';
        }

        this.showStatus(`❌ ${message}`, 'error');
    }
}

// Initialize the editor when the page loads
let asepriteEditor;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        asepriteEditor = new AsepriteEditor();
    });
} else {
    asepriteEditor = new AsepriteEditor();
}

// Make it globally accessible for the button onclick handler
window.asepriteEditor = asepriteEditor;
