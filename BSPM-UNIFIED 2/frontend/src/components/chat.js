/**
 * GBStudio Automation Hub - Chat Components
 * Version: 3.1
 * Platform: Intel Mac (macOS Ventura) + Docker
 * 
 * ChatWindow and ChatMessage classes for conversational interface
 */

/**
 * ChatMessage - Individual message with metadata and actions
 */
export class ChatMessage {
    constructor(sender, content, metadata = {}) {
        this.id = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        this.sender = sender;
        this.content = content;
        this.metadata = metadata;
        this.timestamp = new Date();
        this.element = null;
    }
    
    /**
     * Render message to DOM element
     * @returns {HTMLElement}
     */
    render() {
        const messageEl = document.createElement('div');
        messageEl.className = 'message';
        messageEl.id = this.id;
        messageEl.setAttribute('data-sender', this.sender);
        messageEl.setAttribute('role', 'article');
        messageEl.setAttribute('aria-label', `Message from ${this.sender}`);
        
        // Header
        const header = document.createElement('div');
        header.className = 'message-header';
        
        const senderBadge = document.createElement('span');
        senderBadge.className = `message-sender sender-${this.sender.toLowerCase()}`;
        senderBadge.textContent = this.sender.toUpperCase();
        
        const timestamp = document.createElement('span');
        timestamp.className = 'message-timestamp';
        timestamp.textContent = this.formatTimestamp();
        
        header.appendChild(senderBadge);
        header.appendChild(timestamp);
        
        // Content
        const contentEl = document.createElement('div');
        contentEl.className = 'message-content';
        contentEl.innerHTML = this.sanitizeHTML(this.content);
        
        messageEl.appendChild(header);
        messageEl.appendChild(contentEl);
        
        this.element = messageEl;
        return messageEl;
    }
    
    /**
     * Format timestamp as HH:MM
     * @returns {string}
     */
    formatTimestamp() {
        const hours = this.timestamp.getHours().toString().padStart(2, '0');
        const minutes = this.timestamp.getMinutes().toString().padStart(2, '0');
        return `${hours}:${minutes}`;
    }
    
    /**
     * Sanitize HTML content to prevent XSS
     * @param {string} html
     * @returns {string}
     */
    sanitizeHTML(html) {
        const temp = document.createElement('div');
        temp.textContent = html;
        return temp.innerHTML.replace(/\n/g, '<br>');
    }
    
    /**
     * Add approval buttons for plan review
     * @param {Array} plan - Delegation plan
     * @param {Function} onApprove - Approval callback
     * @param {Function} onCancel - Cancel callback
     */
    addApprovalButtons(plan, onApprove, onCancel) {
        if (!this.element) return;
        
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'approval-buttons';
        
        const approveBtn = document.createElement('button');
        approveBtn.className = 'pixel-button approve';
        approveBtn.innerHTML = '✓ APPROVE';
        approveBtn.setAttribute('aria-label', 'Approve plan');
        approveBtn.onclick = () => {
            buttonContainer.remove();
            onApprove(plan);
        };
        
        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'pixel-button cancel';
        cancelBtn.innerHTML = '✕ CANCEL';
        cancelBtn.setAttribute('aria-label', 'Cancel plan');
        cancelBtn.onclick = () => {
            buttonContainer.remove();
            onCancel();
        };
        
        buttonContainer.appendChild(approveBtn);
        buttonContainer.appendChild(cancelBtn);
        
        const contentEl = this.element.querySelector('.message-content');
        contentEl.appendChild(buttonContainer);
    }
    
    /**
     * Add progress bar for long-running operations
     * @param {string} promptId - Operation identifier
     * @returns {Object} Progress control object
     */
    addProgressBar(promptId) {
        if (!this.element) return null;
        
        const progressContainer = document.createElement('div');
        progressContainer.id = `progress-${promptId}`;
        progressContainer.className = 'progress-container';
        progressContainer.innerHTML = `
            <div class="progress-bar-wrapper">
                <div class="progress-bar" style="width: 0%"></div>
            </div>
            <p class="progress-text">Initializing...</p>
        `;
        
        const contentEl = this.element.querySelector('.message-content');
        contentEl.appendChild(progressContainer);
        
        return {
            update: (value, max) => {
                const percent = Math.round((value / max) * 100);
                const bar = progressContainer.querySelector('.progress-bar');
                const text = progressContainer.querySelector('.progress-text');
                bar.style.width = `${percent}%`;
                text.textContent = `Generating... ${percent}%`;
            },
            complete: (message = 'Complete!') => {
                const bar = progressContainer.querySelector('.progress-bar');
                const text = progressContainer.querySelector('.progress-text');
                bar.style.width = '100%';
                text.textContent = message;
                progressContainer.classList.add('complete');
            },
            error: (message = 'Error occurred') => {
                const text = progressContainer.querySelector('.progress-text');
                text.textContent = message;
                progressContainer.classList.add('error');
            }
        };
    }
}

/**
 * ChatWindow - Container for messages with auto-scroll
 */
export class ChatWindow {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.messages = [];
        this.autoScroll = true;
    }
    
    /**
     * Add message to chat window
     * @param {string} sender - Message sender (User, PM, System)
     * @param {string} content - Message content
     * @param {Object} metadata - Additional metadata
     * @returns {ChatMessage}
     */
    addMessage(sender, content, metadata = {}) {
        const message = new ChatMessage(sender, content, metadata);
        const element = message.render();
        
        this.container.appendChild(element);
        this.messages.push(message);
        
        if (this.autoScroll) {
            this.scrollToBottom();
        }
        
        return message;
    }
    
    /**
     * Scroll to bottom of chat window
     */
    scrollToBottom() {
        this.container.scrollTop = this.container.scrollHeight;
    }
    
    /**
     * Clear all messages
     */
    clear() {
        this.container.innerHTML = '';
        this.messages = [];
    }
    
    /**
     * Get last message
     * @returns {ChatMessage|null}
     */
    getLastMessage() {
        return this.messages[this.messages.length - 1] || null;
    }
}
