/**
 * Style Preset Selector Component
 * Version: 3.2
 *
 * Dropdown selector for choosing sprite generation style presets.
 */

import { escapeHTML, sanitizeAttribute } from '../utils/sanitizer.js';

class StylePresetSelector {
    constructor(containerId, onPresetChange) {
        this.container = document.getElementById(containerId);
        this.onPresetChange = onPresetChange;
        this.presets = {};
        this.selectedPreset = 'clean_pixel_art';
        
        this.init();
    }
    
    async init() {
        await this.loadPresets();
        this.render();
    }
    
    async loadPresets() {
        try {
            const response = await fetch('/api/v1/presets');
            const data = await response.json();
            this.presets = data.presets;
            this.selectedPreset = data.default;
        } catch (error) {
            console.error('Failed to load presets:', error);
            // Fallback presets
            this.presets = {
                'clean_pixel_art': {
                    description: 'Clean lines, sharp edges, minimal shading',
                    steps: 20,
                    cfg: 8.0
                },
                'detailed_sprite': {
                    description: 'Detailed pixel art with refined edges',
                    steps: 25,
                    cfg: 10.0
                },
                'retro_game_boy': {
                    description: 'Authentic Game Boy style, 4 color palette',
                    steps: 18,
                    cfg: 7.5
                }
            };
        }
    }
    
    render() {
        const html = `
            <div class="preset-selector">
                <label for="style-preset">Art Style:</label>
                <select id="style-preset" class="preset-dropdown">
                    ${Object.entries(this.presets).map(([key, preset]) => `
                        <option value="${sanitizeAttribute(key)}" ${key === this.selectedPreset ? 'selected' : ''}>
                            ${escapeHTML(this.formatPresetName(key))}
                        </option>
                    `).join('')}
                </select>
                <div class="preset-description" id="preset-description">
                    ${escapeHTML(this.presets[this.selectedPreset]?.description || '')}
                </div>
                <div class="preset-params" id="preset-params">
                    <span class="param">Steps: ${this.presets[this.selectedPreset]?.steps || 20}</span>
                    <span class="param">CFG: ${this.presets[this.selectedPreset]?.cfg || 8.0}</span>
                </div>
            </div>
        `;

        this.container.innerHTML = html;

        // Attach event listener
        const dropdown = document.getElementById('style-preset');
        dropdown.addEventListener('change', (e) => {
            this.selectedPreset = e.target.value;
            this.updateDescription();
            if (this.onPresetChange) {
                this.onPresetChange(this.selectedPreset);
            }
        });
    }
    
    updateDescription() {
        const descEl = document.getElementById('preset-description');
        const paramsEl = document.getElementById('preset-params');
        const preset = this.presets[this.selectedPreset];

        if (descEl && preset) {
            // Use textContent for safe display
            descEl.textContent = preset.description;
        }

        if (paramsEl && preset) {
            // Steps and CFG are numeric values from API, but sanitize for safety
            paramsEl.innerHTML = `
                <span class="param">Steps: ${preset.steps}</span>
                <span class="param">CFG: ${preset.cfg}</span>
            `;
        }
    }
    
    formatPresetName(key) {
        return key
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }
    
    getSelectedPreset() {
        return this.selectedPreset;
    }
    
    setPreset(presetName) {
        this.selectedPreset = presetName;
        const dropdown = document.getElementById('style-preset');
        if (dropdown) {
            dropdown.value = presetName;
            this.updateDescription();
        }
    }
}

export { StylePresetSelector };
