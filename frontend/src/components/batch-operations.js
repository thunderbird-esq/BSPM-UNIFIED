/**
 * Batch Operations UI Component
 * Version: 3.2
 * 
 * Interface for CSV upload, character sets, and project templates.
 */

import { apiCall } from '../utils/api.js';

class BatchOperations {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.activeBatches = new Map();
        this.pollInterval = null;
    }
    
    render() {
        const html = `
            <div class="batch-operations">
                <h2>Batch Sprite Generation</h2>
                
                <div class="batch-tabs">
                    <button class="tab-btn active" data-tab="csv">CSV Upload</button>
                    <button class="tab-btn" data-tab="character">Character Set</button>
                    <button class="tab-btn" data-tab="template">Project Template</button>
                </div>
                
                <div class="tab-content">
                    <div id="csv-tab" class="tab-pane active">
                        ${this.renderCSVUpload()}
                    </div>
                    <div id="character-tab" class="tab-pane">
                        ${this.renderCharacterSet()}
                    </div>
                    <div id="template-tab" class="tab-pane">
                        ${this.renderTemplateSelector()}
                    </div>
                </div>
                
                <div id="active-batches">
                    ${this.renderActiveBatches()}
                </div>
            </div>
        `;
        
        this.container.innerHTML = html;
        this.attachEventListeners();
    }
    
    renderCSVUpload() {
        return `
            <div class="csv-upload">
                <h3>Upload CSV File</h3>
                <p class="help-text">
                    CSV format: <code>character,action,style,priority</code><br>
                    Example: <code>knight,idle,pixel art,normal</code>
                </p>
                
                <div class="upload-area" id="csv-drop-zone">
                    <input type="file" id="csv-file-input" accept=".csv" hidden>
                    <label for="csv-file-input" class="upload-label">
                        📁 Click to select CSV file or drag here
                    </label>
                    <div id="csv-file-name" class="file-name"></div>
                </div>
                
                <button id="process-csv-btn" class="btn-primary" disabled>
                    Process CSV Batch
                </button>
            </div>
        `;
    }
    
    renderCharacterSet() {
        return `
            <div class="character-set">
                <h3>Generate Character Set</h3>
                <p class="help-text">
                    Generate a complete animation set for a character (idle, walk, attack, hurt)
                </p>
                
                <form id="character-set-form">
                    <div class="form-group">
                        <label for="character-name">Character Description:</label>
                        <input type="text" 
                               id="character-name" 
                               placeholder="e.g., knight in armor"
                               required>
                    </div>
                    
                    <div class="form-group">
                        <label for="character-style">Art Style:</label>
                        <select id="character-style">
                            <option value="pixel art">Pixel Art</option>
                            <option value="retro">Retro</option>
                            <option value="modern pixel">Modern Pixel</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label>Include Actions:</label>
                        <div class="checkbox-group">
                            <label><input type="checkbox" name="action" value="idle" checked> Idle</label>
                            <label><input type="checkbox" name="action" value="walk" checked> Walk</label>
                            <label><input type="checkbox" name="action" value="attack" checked> Attack</label>
                            <label><input type="checkbox" name="action" value="hurt" checked> Hurt</label>
                            <label><input type="checkbox" name="action" value="jump"> Jump</label>
                            <label><input type="checkbox" name="action" value="crouch"> Crouch</label>
                        </div>
                    </div>
                    
                    <button type="submit" class="btn-primary">
                        Generate Character Set
                    </button>
                </form>
            </div>
        `;
    }
    
    renderTemplateSelector() {
        return `
            <div class="template-selector">
                <h3>Apply Project Template</h3>
                <p class="help-text">
                    Generate a complete set of sprites for common game types
                </p>
                
                <div class="template-grid">
                    <div class="template-card" data-template="platformer">
                        <div class="template-icon">🎮</div>
                        <h4>Platformer</h4>
                        <p>Player, enemies, collectibles</p>
                        <span class="sprite-count">8 sprites</span>
                    </div>
                    
                    <div class="template-card" data-template="rpg">
                        <div class="template-icon">⚔️</div>
                        <h4>RPG</h4>
                        <p>Hero, NPCs, monsters</p>
                        <span class="sprite-count">8 sprites</span>
                    </div>
                    
                    <div class="template-card" data-template="shooter">
                        <div class="template-icon">🚀</div>
                        <h4>Shooter</h4>
                        <p>Ships, enemies, powerups</p>
                        <span class="sprite-count">8 sprites</span>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderActiveBatches() {
        if (this.activeBatches.size === 0) {
            return '';
        }
        
        return `
            <div class="active-batches-section">
                <h3>Active Batches</h3>
                ${Array.from(this.activeBatches.entries()).map(([id, batch]) => 
                    this.renderBatchProgress(id, batch)
                ).join('')}
            </div>
        `;
    }
    
    renderBatchProgress(batchId, batch) {
        const progress = batch.completed / batch.total * 100;
        
        return `
            <div class="batch-progress" data-batch-id="${batchId}">
                <div class="batch-header">
                    <span class="batch-name">${batch.name}</span>
                    <span class="batch-status">
                        ${batch.completed}/${batch.total} 
                        (${batch.failed} failed)
                    </span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress}%"></div>
                </div>
            </div>
        `;
    }
    
    attachEventListeners() {
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });
        
        // CSV file input
        const fileInput = document.getElementById('csv-file-input');
        const dropZone = document.getElementById('csv-drop-zone');
        const processBtn = document.getElementById('process-csv-btn');
        
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                this.handleCSVSelect(e.target.files[0]);
            });
        }
        
        if (dropZone) {
            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropZone.classList.add('drag-over');
            });
            
            dropZone.addEventListener('dragleave', () => {
                dropZone.classList.remove('drag-over');
            });
            
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('drag-over');
                this.handleCSVSelect(e.dataTransfer.files[0]);
            });
        }
        
        if (processBtn) {
            processBtn.addEventListener('click', () => this.processCSV());
        }
        
        // Character set form
        const charSetForm = document.getElementById('character-set-form');
        if (charSetForm) {
            charSetForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.generateCharacterSet();
            });
        }
        
        // Template cards
        document.querySelectorAll('.template-card').forEach(card => {
            card.addEventListener('click', () => {
                this.applyTemplate(card.dataset.template);
            });
        });
    }
    
    switchTab(tabName) {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.remove('active');
        });
        
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        document.getElementById(`${tabName}-tab`).classList.add('active');
    }
    
    handleCSVSelect(file) {
        if (!file || !file.name.endsWith('.csv')) {
            this.showNotification('Please select a valid CSV file', 'error');
            return;
        }
        
        this.selectedCSVFile = file;
        document.getElementById('csv-file-name').textContent = file.name;
        document.getElementById('process-csv-btn').disabled = false;
    }
    
    async processCSV() {
        if (!this.selectedCSVFile) return;
        
        const formData = new FormData();
        formData.append('file', this.selectedCSVFile);
        
        try {
            // Upload file first
            const uploadResponse = await fetch('/api/v1/upload', {
                method: 'POST',
                body: formData
            });
            
            const uploadData = await uploadResponse.json();
            const csvPath = uploadData.path;
            
            // Process CSV
            const sessionId = `batch_${Date.now()}`;
            const response = await apiCall('/api/v1/batch/csv', 'POST', {
                csv_path: csvPath,
                session_id: sessionId
            });
            
            this.addBatch(response.batch_id, {
                name: this.selectedCSVFile.name,
                total: response.total_requests,
                completed: 0,
                failed: 0,
                task_ids: response.task_ids
            });
            
            this.showNotification(`Batch queued: ${response.total_requests} sprites`, 'success');
            this.startPolling();
            
        } catch (error) {
            console.error('CSV processing failed:', error);
            this.showNotification('Failed to process CSV', 'error');
        }
    }
    
    async generateCharacterSet() {
        const characterName = document.getElementById('character-name').value;
        const style = document.getElementById('character-style').value;
        
        const checkedActions = Array.from(
            document.querySelectorAll('input[name="action"]:checked')
        ).map(cb => cb.value);
        
        if (checkedActions.length === 0) {
            this.showNotification('Select at least one action', 'error');
            return;
        }
        
        try {
            const sessionId = `charset_${Date.now()}`;
            const response = await apiCall('/api/v1/batch/character-set', 'POST', {
                character_name: characterName,
                style: style,
                session_id: sessionId,
                include_actions: checkedActions
            });
            
            this.addBatch(response.batch_id, {
                name: `${characterName} Character Set`,
                total: response.total_sprites,
                completed: 0,
                failed: 0,
                task_ids: response.task_ids
            });
            
            this.showNotification(`Character set queued: ${response.total_sprites} sprites`, 'success');
            this.startPolling();
            
        } catch (error) {
            console.error('Character set generation failed:', error);
            this.showNotification('Failed to generate character set', 'error');
        }
    }
    
    async applyTemplate(templateName) {
        if (!confirm(`Generate all sprites from the ${templateName} template?`)) {
            return;
        }
        
        try {
            const sessionId = `template_${Date.now()}`;
            const response = await apiCall('/api/v1/batch/template', 'POST', {
                template_name: templateName,
                session_id: sessionId
            });
            
            this.addBatch(response.batch_id, {
                name: `${templateName.charAt(0).toUpperCase() + templateName.slice(1)} Template`,
                total: response.total_sprites,
                completed: 0,
                failed: 0,
                task_ids: response.task_ids
            });
            
            this.showNotification(`Template queued: ${response.total_sprites} sprites`, 'success');
            this.startPolling();
            
        } catch (error) {
            console.error('Template application failed:', error);
            this.showNotification('Failed to apply template', 'error');
        }
    }
    
    addBatch(batchId, batchData) {
        this.activeBatches.set(batchId, batchData);
        this.updateActiveBatchesDisplay();
    }
    
    updateActiveBatchesDisplay() {
        const batchesContainer = document.getElementById('active-batches');
        if (batchesContainer) {
            batchesContainer.innerHTML = this.renderActiveBatches();
        }
    }
    
    startPolling() {
        if (this.pollInterval) return;
        
        this.pollInterval = setInterval(() => {
            this.updateBatchStatuses();
        }, 5000);
    }
    
    async updateBatchStatuses() {
        for (const [batchId, batch] of this.activeBatches.entries()) {
            try {
                const params = new URLSearchParams();
                batch.task_ids.forEach(id => params.append('task_ids', id));
                
                const status = await apiCall(
                    `/api/v1/batch/${batchId}/status?${params}`,
                    'GET'
                );
                
                batch.completed = status.completed;
                batch.failed = status.failed;
                
                if (status.completed + status.failed === batch.total) {
                    this.activeBatches.delete(batchId);
                    this.showNotification(
                        `Batch complete: ${batch.name} (${status.failed} failed)`,
                        status.failed === 0 ? 'success' : 'warning'
                    );
                }
                
            } catch (error) {
                console.error(`Failed to update batch ${batchId}:`, error);
            }
        }
        
        this.updateActiveBatchesDisplay();
        
        if (this.activeBatches.size === 0) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => notification.classList.add('show'), 100);
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

export { BatchOperations };
