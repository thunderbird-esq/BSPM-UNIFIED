/**
 * Regeneration UI Component
 * Version: 3.2
 * 
 * Provides regenerate button and A/B comparison modal for sprite results.
 */

import { apiCall } from '../utils/api.js';

class RegenerationUI {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.sessionId = null;
        this.attempts = [];
        this.comparisonModal = null;
    }
    
    renderRegenerateButton(sessionId, spriteId) {
        this.sessionId = sessionId;
        
        const buttonHtml = `
            <div class="regeneration-controls">
                <button id="regenerate-btn" class="btn-regenerate">
                    🔄 Regenerate with Different Seed
                </button>
                <button id="compare-btn" class="btn-compare" style="display:none;">
                    ⚖️ Compare All Attempts
                </button>
            </div>
        `;
        
        this.container.innerHTML = buttonHtml;
        
        // Attach event listeners
        const regenBtn = document.getElementById('regenerate-btn');
        regenBtn.addEventListener('click', () => this.handleRegenerate());
        
        const compareBtn = document.getElementById('compare-btn');
        compareBtn.addEventListener('click', () => this.showComparisonModal());
    }
    
    async handleRegenerate(preset = null) {
        const regenBtn = document.getElementById('regenerate-btn');
        regenBtn.disabled = true;
        regenBtn.textContent = '⏳ Regenerating...';
        
        try {
            const response = await apiCall('/api/v1/regenerate', 'POST', {
                session_id: this.sessionId,
                preset: preset
            });
            
            // Show success message
            this.showNotification('Regeneration queued! Check back in a few minutes.', 'success');
            
            // Enable comparison button after first regeneration
            const compareBtn = document.getElementById('compare-btn');
            if (compareBtn) {
                compareBtn.style.display = 'inline-block';
            }
            
            // Reset button
            regenBtn.disabled = false;
            regenBtn.textContent = '🔄 Regenerate Again';
            
        } catch (error) {
            console.error('Regeneration failed:', error);
            this.showNotification('Regeneration failed: ' + error.message, 'error');
            
            regenBtn.disabled = false;
            regenBtn.textContent = '🔄 Regenerate with Different Seed';
        }
    }
    
    async showComparisonModal() {
        try {
            // Fetch comparison data
            const data = await apiCall(`/api/v1/regenerate/${this.sessionId}/comparison`, 'GET');
            
            this.attempts = data.attempts || [];
            
            if (this.attempts.length === 0) {
                this.showNotification('No completed attempts to compare yet', 'info');
                return;
            }
            
            this.renderComparisonModal(data);
            
        } catch (error) {
            console.error('Failed to load comparison data:', error);
            this.showNotification('Failed to load comparison data', 'error');
        }
    }
    
    renderComparisonModal(data) {
        // Create modal backdrop
        const modal = document.createElement('div');
        modal.className = 'modal-backdrop';
        modal.id = 'comparison-modal';
        
        const modalContent = `
            <div class="modal-content comparison-modal">
                <div class="modal-header">
                    <h2>Compare Sprite Attempts</h2>
                    <button class="modal-close" onclick="document.getElementById('comparison-modal').remove()">✕</button>
                </div>
                
                <div class="modal-body">
                    <div class="comparison-info">
                        <p><strong>Prompt:</strong> ${data.original_prompt}</p>
                        <p><strong>Total Attempts:</strong> ${this.attempts.length}</p>
                    </div>
                    
                    <div class="comparison-grid">
                        ${this.attempts.map((attempt, index) => this.renderAttemptCard(attempt, index)).join('')}
                    </div>
                </div>
                
                <div class="modal-footer">
                    <button class="btn-secondary" onclick="document.getElementById('comparison-modal').remove()">Close</button>
                </div>
            </div>
        `;
        
        modal.innerHTML = modalContent;
        document.body.appendChild(modal);
        
        // Attach event listeners for "Mark as Best" buttons
        this.attempts.forEach((attempt, index) => {
            const markBtn = document.getElementById(`mark-best-${index}`);
            if (markBtn) {
                markBtn.addEventListener('click', () => this.markAsBest(attempt.attempt_id));
            }
        });
    }
    
    renderAttemptCard(attempt, index) {
        const isBest = attempt.is_best;
        const score = attempt.validation_score || 0;
        
        return `
            <div class="attempt-card ${isBest ? 'best-attempt' : ''}">
                <div class="attempt-header">
                    <span class="attempt-number">Attempt ${index + 1}</span>
                    ${isBest ? '<span class="best-badge">⭐ BEST</span>' : ''}
                </div>
                
                <div class="attempt-preview">
                    <img src="/api/v1/sprites/${attempt.sprite_id}/preview" 
                         alt="Sprite attempt ${index + 1}"
                         onerror="this.src='/frontend/assets/placeholder.png'">
                </div>
                
                <div class="attempt-info">
                    <div class="info-row">
                        <span class="label">Preset:</span>
                        <span class="value">${this.formatPresetName(attempt.preset)}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Seed:</span>
                        <span class="value">${attempt.seed}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Score:</span>
                        <span class="value score-${this.getScoreClass(score)}">${score.toFixed(1)}/100</span>
                    </div>
                </div>
                
                <div class="attempt-actions">
                    ${!isBest ? `
                        <button id="mark-best-${index}" class="btn-mark-best">
                            Mark as Best
                        </button>
                    ` : ''}
                    <button class="btn-view-details" onclick="window.open('/sprites/${attempt.sprite_id}', '_blank')">
                        View Details
                    </button>
                </div>
            </div>
        `;
    }
    
    async markAsBest(attemptId) {
        try {
            await apiCall(`/api/v1/regenerate/${this.sessionId}/mark-best?attempt_id=${attemptId}`, 'POST');
            
            this.showNotification('Marked as best attempt!', 'success');
            
            // Refresh comparison view
            document.getElementById('comparison-modal').remove();
            this.showComparisonModal();
            
        } catch (error) {
            console.error('Failed to mark as best:', error);
            this.showNotification('Failed to mark as best', 'error');
        }
    }
    
    formatPresetName(preset) {
        return preset
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }
    
    getScoreClass(score) {
        if (score >= 80) return 'high';
        if (score >= 60) return 'medium';
        return 'low';
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

export { RegenerationUI };
