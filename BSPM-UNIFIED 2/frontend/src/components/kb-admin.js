/**
 * Knowledge Base Admin UI Component
 * Version: 3.2
 *
 * Dashboard for managing indexed documentation.
 */

import { apiCall } from '../utils/api.js';
import { sanitizeHTML, escapeHTML, sanitizeAttribute } from '../utils/sanitizer.js';

class KBAdmin {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.documents = [];
        this.stats = null;
        this.filterType = null;
    }
    
    async init() {
        await Promise.all([
            this.loadDocuments(),
            this.loadStats()
        ]);
        this.render();
    }
    
    async loadDocuments() {
        try {
            const params = this.filterType ? `?filter_type=${this.filterType}` : '';
            const data = await apiCall(`/api/v1/admin/kb/documents${params}`, 'GET');
            this.documents = data.documents || [];
        } catch (error) {
            console.error('Failed to load documents:', error);
            this.documents = [];
        }
    }
    
    async loadStats() {
        try {
            this.stats = await apiCall('/api/v1/admin/kb/stats', 'GET');
        } catch (error) {
            console.error('Failed to load stats:', error);
            this.stats = null;
        }
    }
    
    render() {
        const html = `
            <div class="kb-admin">
                <div class="admin-header">
                    <h2>Knowledge Base Administration</h2>
                    <div class="admin-actions">
                        <button id="upload-doc-btn" class="btn-primary">
                            📄 Upload Document
                        </button>
                        <button id="rebuild-index-btn" class="btn-secondary">
                            🔄 Rebuild Index
                        </button>
                        <button id="test-search-btn" class="btn-secondary">
                            🔍 Test Search
                        </button>
                    </div>
                </div>
                
                ${this.renderStats()}
                
                <div class="documents-section">
                    <div class="section-header">
                        <h3>Documents</h3>
                        <select id="doc-type-filter">
                            <option value="">All Types</option>
                            <option value="project_doc" ${this.filterType === 'project_doc' ? 'selected' : ''}>Project Docs</option>
                            <option value="conversation" ${this.filterType === 'conversation' ? 'selected' : ''}>Conversations</option>
                            <option value="task" ${this.filterType === 'task' ? 'selected' : ''}>Tasks</option>
                        </select>
                    </div>
                    
                    <div class="documents-list">
                        ${this.documents.length === 0 ? 
                            '<p class="no-docs">No documents found</p>' :
                            this.documents.map(doc => this.renderDocumentCard(doc)).join('')
                        }
                    </div>
                </div>
            </div>
        `;
        
        this.container.innerHTML = html;
        this.attachEventListeners();
    }
    
    renderStats() {
        if (!this.stats) {
            return '<div class="stats-loading">Loading statistics...</div>';
        }
        
        return `
            <div class="kb-stats">
                <div class="stat-card">
                    <div class="stat-value">${this.stats.total_documents}</div>
                    <div class="stat-label">Total Documents</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${this.stats.project_documents}</div>
                    <div class="stat-label">Project Docs</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${this.stats.conversations}</div>
                    <div class="stat-label">Conversations</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${this.stats.total_files || 0}</div>
                    <div class="stat-label">Source Files</div>
                </div>
            </div>
        `;
    }
    
    renderDocumentCard(doc) {
        return `
            <div class="doc-card" data-doc-id="${sanitizeAttribute(doc.doc_id)}">
                <div class="doc-header">
                    <span class="doc-type-badge type-${sanitizeAttribute(doc.type)}">${escapeHTML(doc.type)}</span>
                    <span class="doc-source">${escapeHTML(doc.source)}</span>
                </div>
                <div class="doc-preview">
                    ${escapeHTML(doc.content_preview)}
                </div>
                <div class="doc-meta">
                    ${doc.chunk_index !== undefined ?
                        `<span>Chunk ${doc.chunk_index + 1}/${doc.total_chunks}</span>` :
                        ''
                    }
                    <span>${escapeHTML(doc.created_at)}</span>
                </div>
                <div class="doc-actions">
                    <button class="btn-sm btn-view" data-action="view" data-doc-id="${sanitizeAttribute(doc.doc_id)}">
                        View
                    </button>
                    ${doc.type === 'project_doc' ? `
                        <button class="btn-sm btn-reindex" data-action="reindex" data-source="${sanitizeAttribute(doc.source)}">
                            Re-index
                        </button>
                        <button class="btn-sm btn-delete" data-action="delete" data-source="${sanitizeAttribute(doc.source)}">
                            Delete
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    attachEventListeners() {
        // Header buttons
        document.getElementById('upload-doc-btn')?.addEventListener('click', () => {
            this.showUploadModal();
        });
        
        document.getElementById('rebuild-index-btn')?.addEventListener('click', () => {
            this.handleRebuildIndex();
        });
        
        document.getElementById('test-search-btn')?.addEventListener('click', () => {
            this.showSearchTestModal();
        });
        
        // Filter dropdown
        document.getElementById('doc-type-filter')?.addEventListener('change', (e) => {
            this.filterType = e.target.value || null;
            this.refresh();
        });
        
        // Document action buttons
        document.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                const docId = e.target.dataset.docId;
                const source = e.target.dataset.source;
                this.handleDocAction(action, docId, source);
            });
        });
    }
    
    async handleDocAction(action, docId, source) {
        switch (action) {
            case 'view':
                await this.showDocumentDetails(docId);
                break;
            case 'reindex':
                await this.reindexDocument(source);
                break;
            case 'delete':
                await this.deleteDocument(source);
                break;
        }
    }
    
    async showDocumentDetails(docId) {
        try {
            const doc = await apiCall(`/api/v1/admin/kb/documents/${docId}`, 'GET');

            const modal = this.createModal('Document Details', `
                <div class="doc-details">
                    <div class="detail-row">
                        <strong>ID:</strong> ${escapeHTML(doc.doc_id)}
                    </div>
                    <div class="detail-row">
                        <strong>Type:</strong> ${escapeHTML(doc.metadata.type)}
                    </div>
                    <div class="detail-row">
                        <strong>Source:</strong> ${escapeHTML(doc.metadata.source_file || 'N/A')}
                    </div>
                    <div class="detail-row">
                        <strong>Length:</strong> ${doc.content_length} chars (${doc.word_count} words)
                    </div>
                    <div class="detail-content">
                        <strong>Content:</strong>
                        <pre>${escapeHTML(doc.content)}</pre>
                    </div>
                    <div class="detail-metadata">
                        <strong>Metadata:</strong>
                        <pre>${escapeHTML(JSON.stringify(doc.metadata, null, 2))}</pre>
                    </div>
                </div>
            `);

        } catch (error) {
            console.error('Failed to load document details:', error);
            this.showNotification('Failed to load document details', 'error');
        }
    }
    
    async reindexDocument(source) {
        // Use plain text for confirm dialog (safe from XSS)
        if (!confirm(`Re-index ${source}? This will replace all existing chunks.`)) {
            return;
        }
        
        try {
            const result = await apiCall(`/api/v1/admin/kb/reindex?source_file=${encodeURIComponent(source)}`, 'POST');
            
            this.showNotification(
                `Re-indexed: removed ${result.removed_chunks}, added ${result.added_chunks} chunks`,
                'success'
            );
            
            await this.refresh();
            
        } catch (error) {
            console.error('Re-indexing failed:', error);
            this.showNotification('Failed to re-index document', 'error');
        }
    }
    
    async deleteDocument(source) {
        // Use plain text for confirm dialog (safe from XSS)
        if (!confirm(`Delete ${source}? This will remove all chunks and the source file.`)) {
            return;
        }
        
        try {
            const result = await apiCall(`/api/v1/admin/kb/documents?source_file=${encodeURIComponent(source)}`, 'DELETE');
            
            this.showNotification(
                `Deleted: removed ${result.chunks_removed} chunks${result.file_deleted ? ', file deleted' : ''}`,
                'success'
            );
            
            await this.refresh();
            
        } catch (error) {
            console.error('Deletion failed:', error);
            this.showNotification('Failed to delete document', 'error');
        }
    }
    
    showUploadModal() {
        const modal = this.createModal('Upload Document', `
            <form id="upload-doc-form">
                <div class="form-group">
                    <label for="doc-filename">Filename (.md):</label>
                    <input type="text" id="doc-filename" placeholder="my_document.md" required>
                </div>
                <div class="form-group">
                    <label for="doc-content">Content:</label>
                    <textarea id="doc-content" rows="15" placeholder="# My Document&#10;&#10;Content here..." required></textarea>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn-primary">Upload</button>
                    <button type="button" class="btn-secondary modal-close">Cancel</button>
                </div>
            </form>
        `);
        
        document.getElementById('upload-doc-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.uploadDocument(
                document.getElementById('doc-filename').value,
                document.getElementById('doc-content').value
            );
            modal.remove();
        });
    }
    
    async uploadDocument(filename, content) {
        try {
            const result = await apiCall('/api/v1/admin/kb/upload', 'POST', {
                filename,
                content
            });
            
            this.showNotification(
                `Uploaded: ${result.filename} (${result.chunks_created} chunks)`,
                'success'
            );
            
            await this.refresh();
            
        } catch (error) {
            console.error('Upload failed:', error);
            this.showNotification('Failed to upload document', 'error');
        }
    }
    
    showSearchTestModal() {
        const modal = this.createModal('Test Search', `
            <form id="search-test-form">
                <div class="form-group">
                    <label for="search-query">Search Query:</label>
                    <input type="text" id="search-query" placeholder="sprite resolution" required>
                </div>
                <div class="form-group">
                    <label for="search-limit">Results Limit:</label>
                    <select id="search-limit">
                        <option value="3">3</option>
                        <option value="5" selected>5</option>
                        <option value="10">10</option>
                    </select>
                </div>
                <button type="submit" class="btn-primary">Search</button>
            </form>
            <div id="search-results" class="search-results"></div>
        `);
        
        document.getElementById('search-test-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const query = document.getElementById('search-query').value;
            const limit = parseInt(document.getElementById('search-limit').value);
            
            const results = await this.testSearch(query, limit);
            this.displaySearchResults(results);
        });
    }
    
    async testSearch(query, limit) {
        try {
            return await apiCall('/api/v1/admin/kb/search-test', 'POST', { query, limit });
        } catch (error) {
            console.error('Search test failed:', error);
            this.showNotification('Search test failed', 'error');
            return { results: [] };
        }
    }
    
    displaySearchResults(data) {
        const resultsDiv = document.getElementById('search-results');
        if (!resultsDiv) return;

        if (data.results.length === 0) {
            resultsDiv.innerHTML = '<p class="no-results">No results found</p>';
            return;
        }

        resultsDiv.innerHTML = `
            <h4>Results for "${escapeHTML(data.query)}" (${data.num_results} found)</h4>
            ${data.results.map((r, i) => `
                <div class="search-result">
                    <div class="result-header">
                        <span class="result-rank">#${i + 1}</span>
                        <span class="result-distance">Distance: ${r.distance.toFixed(3)}</span>
                    </div>
                    <div class="result-content">${escapeHTML(r.content)}</div>
                    <div class="result-meta">
                        Type: ${escapeHTML(r.metadata.type)} | Source: ${escapeHTML(r.metadata.source_file || 'N/A')}
                    </div>
                </div>
            `).join('')}
        `;
    }
    
    async handleRebuildIndex() {
        // Use plain text for confirm dialog (safe from XSS)
        if (!confirm('Rebuild entire knowledge base? This will re-index all source files.')) {
            return;
        }
        
        const rebuildBtn = document.getElementById('rebuild-index-btn');
        rebuildBtn.disabled = true;
        rebuildBtn.textContent = '⏳ Rebuilding...';
        
        try {
            const result = await apiCall('/api/v1/admin/kb/rebuild', 'POST');
            
            if (result.status === 'success') {
                this.showNotification(
                    `Rebuilt: ${result.files_processed} files, ${result.total_chunks} chunks`,
                    'success'
                );
            } else {
                this.showNotification(result.message || 'Rebuild failed', 'warning');
            }
            
            await this.refresh();
            
        } catch (error) {
            console.error('Rebuild failed:', error);
            this.showNotification('Failed to rebuild index', 'error');
        } finally {
            rebuildBtn.disabled = false;
            rebuildBtn.textContent = '🔄 Rebuild Index';
        }
    }
    
    createModal(title, content) {
        const modal = document.createElement('div');
        modal.className = 'modal-backdrop';

        // Create modal structure using DOM methods
        const modalContent = document.createElement('div');
        modalContent.className = 'modal-content kb-modal';

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
        await Promise.all([
            this.loadDocuments(),
            this.loadStats()
        ]);
        this.render();
    }
    
    // Note: escapeHtml is now handled by the sanitizer utility
    // This method is kept for backwards compatibility but delegates to escapeHTML
    escapeHtml(text) {
        return escapeHTML(text);
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

export { KBAdmin };
