/**
 * Sprite Manager UI Component
 * Version: 3.2
 *
 * UI for editing, deleting, duplicating, and exporting sprites.
 */

import { apiCall } from '../utils/api.js';
import { sanitizeHTML, escapeHTML, sanitizeAttribute } from '../utils/sanitizer.js';

class SpriteManager {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.sprites = [];
        this.filterType = null;
        this.searchQuery = '';
    }
    
    async init() {
        await this.loadSprites();
        this.render();
    }
    
    async loadSprites() {
        try {
            const params = new URLSearchParams();
            if (this.filterType) params.append('filter_type', this.filterType);
            if (this.searchQuery) params.append('search_name', this.searchQuery);
            
            const data = await apiCall(`/api/v1/sprites?${params}`, 'GET');
            this.sprites = data.sprites || [];
        } catch (error) {
            console.error('Failed to load sprites:', error);
            this.sprites = [];
        }
    }
    
    render() {
        const html = `
            <div class="sprite-manager">
                <div class="manager-header">
                    <h2>Sprite Manager</h2>
                    <div class="manager-controls">
                        <input type="text"
                               id="sprite-search"
                               placeholder="Search sprites..."
                               value="${sanitizeAttribute(this.searchQuery)}">
                        <select id="sprite-filter">
                            <option value="">All Types</option>
                            <option value="actor_animated" ${this.filterType === 'actor_animated' ? 'selected' : ''}>Actor Animated</option>
                            <option value="actor" ${this.filterType === 'actor' ? 'selected' : ''}>Actor</option>
                            <option value="static" ${this.filterType === 'static' ? 'selected' : ''}>Static</option>
                            <option value="ui" ${this.filterType === 'ui' ? 'selected' : ''}>UI</option>
                        </select>
                    </div>
                </div>
                
                <div class="sprite-list">
                    ${this.sprites.length === 0 ? 
                        '<p class="no-sprites">No sprites found</p>' :
                        this.sprites.map(sprite => this.renderSpriteCard(sprite)).join('')
                    }
                </div>
            </div>
        `;
        
        this.container.innerHTML = html;
        this.attachEventListeners();
    }
    
    renderSpriteCard(sprite) {
        return `
            <div class="sprite-card" data-sprite-id="${sanitizeAttribute(sprite.id)}">
                <div class="sprite-preview">
                    <img src="/project_files/assets/sprites/${sanitizeAttribute(sprite.filename)}"
                         alt="${sanitizeAttribute(sprite.name)}"
                         onerror="this.src='/frontend/assets/placeholder.png'">
                </div>

                <div class="sprite-info">
                    <h3 class="sprite-name">${escapeHTML(sprite.name)}</h3>
                    <div class="sprite-meta">
                        <span class="meta-item">Type: ${escapeHTML(sprite.type)}</span>
                        <span class="meta-item">Frames: ${sprite.numFrames}</span>
                        <span class="meta-item">${sprite.canvasWidth}×${sprite.canvasHeight}</span>
                    </div>
                </div>

                <div class="sprite-actions">
                    <button class="btn-icon btn-edit" data-action="edit" data-sprite-id="${sanitizeAttribute(sprite.id)}" title="Edit">
                        ✏️
                    </button>
                    <button class="btn-icon btn-duplicate" data-action="duplicate" data-sprite-id="${sanitizeAttribute(sprite.id)}" title="Duplicate">
                        📋
                    </button>
                    <button class="btn-icon btn-export" data-action="export" data-sprite-id="${sanitizeAttribute(sprite.id)}" title="Export">
                        💾
                    </button>
                    <button class="btn-icon btn-delete" data-action="delete" data-sprite-id="${sanitizeAttribute(sprite.id)}" title="Delete">
                        🗑️
                    </button>
                </div>
            </div>
        `;
    }
    
    attachEventListeners() {
        // Search input
        const searchInput = document.getElementById('sprite-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchQuery = e.target.value;
                this.debounce(() => this.refresh(), 300);
            });
        }
        
        // Filter dropdown
        const filterSelect = document.getElementById('sprite-filter');
        if (filterSelect) {
            filterSelect.addEventListener('change', (e) => {
                this.filterType = e.target.value || null;
                this.refresh();
            });
        }
        
        // Action buttons
        document.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                const spriteId = e.target.dataset.spriteId;
                this.handleAction(action, spriteId);
            });
        });
    }
    
    async handleAction(action, spriteId) {
        switch (action) {
            case 'edit':
                await this.showEditModal(spriteId);
                break;
            case 'duplicate':
                await this.showDuplicateModal(spriteId);
                break;
            case 'export':
                await this.showExportModal(spriteId);
                break;
            case 'delete':
                await this.handleDelete(spriteId);
                break;
        }
    }
    
    async showEditModal(spriteId) {
        const sprite = this.sprites.find(s => s.id === spriteId);
        if (!sprite) return;
        
        const modal = this.createModal('Edit Sprite', `
            <form id="edit-sprite-form">
                <div class="form-group">
                    <label for="edit-name">Name:</label>
                    <input type="text" id="edit-name" value="${sanitizeAttribute(sprite.name)}" required>
                </div>
                <div class="form-group">
                    <label for="edit-type">Type:</label>
                    <select id="edit-type">
                        <option value="actor_animated" ${sprite.type === 'actor_animated' ? 'selected' : ''}>Actor Animated</option>
                        <option value="actor" ${sprite.type === 'actor' ? 'selected' : ''}>Actor</option>
                        <option value="static" ${sprite.type === 'static' ? 'selected' : ''}>Static</option>
                        <option value="ui" ${sprite.type === 'ui' ? 'selected' : ''}>UI</option>
                    </select>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn-primary">Save Changes</button>
                    <button type="button" class="btn-secondary modal-close">Cancel</button>
                </div>
            </form>
        `);
        
        const form = document.getElementById('edit-sprite-form');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.saveEdit(spriteId, {
                name: document.getElementById('edit-name').value,
                sprite_type: document.getElementById('edit-type').value
            });
            modal.remove();
        });
    }
    
    async saveEdit(spriteId, updates) {
        try {
            await apiCall('/api/v1/sprites/edit', 'PUT', {
                sprite_id: spriteId,
                ...updates
            });
            
            this.showNotification('Sprite updated successfully', 'success');
            await this.refresh();
        } catch (error) {
            console.error('Edit failed:', error);
            this.showNotification('Failed to update sprite', 'error');
        }
    }
    
    async showDuplicateModal(spriteId) {
        const sprite = this.sprites.find(s => s.id === spriteId);
        if (!sprite) return;
        
        const modal = this.createModal('Duplicate Sprite', `
            <form id="duplicate-sprite-form">
                <div class="form-group">
                    <label for="duplicate-name">New Name:</label>
                    <input type="text" id="duplicate-name" value="${sanitizeAttribute(sprite.name)} (Copy)" required>
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="apply-variation">
                        Apply visual variation
                    </label>
                </div>
                <div class="form-group" id="variation-options" style="display:none;">
                    <label for="variation-type">Variation Type:</label>
                    <select id="variation-type">
                        <option value="hue_shift">Hue Shift</option>
                        <option value="brightness">Brightness</option>
                        <option value="contrast">Contrast</option>
                    </select>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn-primary">Duplicate</button>
                    <button type="button" class="btn-secondary modal-close">Cancel</button>
                </div>
            </form>
        `);
        
        // Show/hide variation options
        document.getElementById('apply-variation').addEventListener('change', (e) => {
            document.getElementById('variation-options').style.display = 
                e.target.checked ? 'block' : 'none';
        });
        
        const form = document.getElementById('duplicate-sprite-form');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.saveDuplicate(spriteId, {
                new_name: document.getElementById('duplicate-name').value,
                apply_variation: document.getElementById('apply-variation').checked,
                variation_type: document.getElementById('variation-type').value
            });
            modal.remove();
        });
    }
    
    async saveDuplicate(spriteId, options) {
        try {
            await apiCall('/api/v1/sprites/duplicate', 'POST', {
                sprite_id: spriteId,
                ...options
            });
            
            this.showNotification('Sprite duplicated successfully', 'success');
            await this.refresh();
        } catch (error) {
            console.error('Duplicate failed:', error);
            this.showNotification('Failed to duplicate sprite', 'error');
        }
    }
    
    async showExportModal(spriteId) {
        const modal = this.createModal('Export Sprite', `
            <form id="export-sprite-form">
                <div class="form-group">
                    <label for="export-format">Export Format:</label>
                    <select id="export-format">
                        <option value="grid">Grid (3×3)</option>
                        <option value="strip">Horizontal Strip</option>
                        <option value="individual_frames">Individual Frames</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="export-scale">Scale:</label>
                    <select id="export-scale">
                        <option value="1">1× (Original)</option>
                        <option value="2">2× (Double)</option>
                        <option value="4">4× (4×)</option>
                        <option value="8">8× (8×)</option>
                    </select>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn-primary">Export</button>
                    <button type="button" class="btn-secondary modal-close">Cancel</button>
                </div>
            </form>
        `);
        
        const form = document.getElementById('export-sprite-form');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleExport(spriteId, {
                export_format: document.getElementById('export-format').value,
                scale: parseInt(document.getElementById('export-scale').value)
            });
            modal.remove();
        });
    }
    
    async handleExport(spriteId, options) {
        try {
            const result = await apiCall('/api/v1/sprites/export', 'POST', {
                sprite_id: spriteId,
                ...options
            });
            
            this.showNotification(`Exported to: ${result.export_path}`, 'success');
        } catch (error) {
            console.error('Export failed:', error);
            this.showNotification('Failed to export sprite', 'error');
        }
    }
    
    async handleDelete(spriteId) {
        const sprite = this.sprites.find(s => s.id === spriteId);
        if (!sprite) return;

        // Use plain text for confirm dialog (safe from XSS)
        if (!confirm(`Delete "${sprite.name}"? This cannot be undone.`)) {
            return;
        }
        
        try {
            await apiCall('/api/v1/sprites/delete', 'DELETE', {
                sprite_id: spriteId,
                delete_file: true
            });
            
            this.showNotification('Sprite deleted successfully', 'success');
            await this.refresh();
        } catch (error) {
            console.error('Delete failed:', error);
            this.showNotification('Failed to delete sprite', 'error');
        }
    }
    
    createModal(title, content) {
        const modal = document.createElement('div');
        modal.className = 'modal-backdrop';

        // Create modal structure using DOM methods
        const modalContent = document.createElement('div');
        modalContent.className = 'modal-content';

        const modalHeader = document.createElement('div');
        modalHeader.className = 'modal-header';

        const modalTitle = document.createElement('h2');
        modalTitle.textContent = title; // Safe from XSS

        const closeBtn = document.createElement('button');
        closeBtn.className = 'modal-close';
        closeBtn.textContent = '✕';

        modalHeader.appendChild(modalTitle);
        modalHeader.appendChild(closeBtn);

        const modalBody = document.createElement('div');
        modalBody.className = 'modal-body';
        // Content is expected to be sanitized by caller
        modalBody.innerHTML = content;

        modalContent.appendChild(modalHeader);
        modalContent.appendChild(modalBody);
        modal.appendChild(modalContent);

        document.body.appendChild(modal);

        modal.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => modal.remove());
        });

        return modal;
    }
    
    async refresh() {
        await this.loadSprites();
        this.render();
    }
    
    debounce(func, wait) {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(func, wait);
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

export { SpriteManager };
