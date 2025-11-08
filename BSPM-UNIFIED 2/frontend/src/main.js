/**
 * Main Application Entry Point
 * Version: 3.2
 * 
 * Integrates all components including medium-priority features.
 */

// Import existing components
import { ChatWindow } from './components/chat.js';
import { ServiceMonitor } from './components/monitor.js';
import { ComfyUIWebSocket } from './components/websocket.js';
import { apiCall } from './utils/api.js';

// Import medium-priority components
import { StylePresetSelector } from './components/style-preset-selector.js';
import { RegenerationUI } from './components/regeneration-ui.js';
import { SpriteManager } from './components/sprite-manager-ui.js';  // FIXED
import { BatchOperations } from './components/batch-operations.js';
import { KBAdmin } from './components/kb-admin.js';

// Global state
const state = {
    sessionId: generateSessionId(),
    currentPreset: 'clean_pixel_art',
    activePanel: null,
    chatWindow: null,
    serviceMonitor: null,
    stylePresetSelector: null,
    regenerationUI: null,
    spriteManager: null,
    batchOps: null,
    kbAdmin: null,
    comfyWSConnection: null
};

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    initializeBarryModal();
});

function initializeBarryModal() {
    const barryModal = document.getElementById('barry-modal');
    const startBtn = document.getElementById('barry-start');

    startBtn.addEventListener('click', () => {
        // Add startup animation
        triggerStartupAnimation(barryModal);

        // Hide modal and show main container after animation
        setTimeout(() => {
            barryModal.style.display = 'none';
            document.getElementById('main-container').style.display = 'block';
            initializeApp();
        }, 600);
    });
}

function triggerStartupAnimation(barryModal) {
    // Add fade-out class to modal
    barryModal.style.transition = 'opacity 0.5s ease-out, transform 0.5s ease-out';
    barryModal.style.opacity = '0';
    barryModal.style.transform = 'scale(0.95)';

    // Add fade-in class to main container
    const mainContainer = document.getElementById('main-container');
    mainContainer.style.opacity = '0';
    mainContainer.style.transform = 'scale(1.05)';
    mainContainer.style.transition = 'opacity 0.5s ease-in, transform 0.5s ease-in';

    setTimeout(() => {
        mainContainer.style.opacity = '1';
        mainContainer.style.transform = 'scale(1)';
    }, 100);
}

async function initializeApp() {
    console.log('Initializing GBStudio Automation Hub v3.2...');
    
    // Initialize core components
    state.chatWindow = new ChatWindow('chat-window');
    state.serviceMonitor = new ServiceMonitor();
    
    // Initialize medium-priority components
    state.stylePresetSelector = new StylePresetSelector(
        'style-preset-selector',
        handlePresetChange
    );
    
    state.regenerationUI = new RegenerationUI('regeneration-controls');
    
    state.spriteManager = new SpriteManager('sprite-manager-panel');
    state.batchOps = new BatchOperations('batch-ops-panel');
    state.kbAdmin = new KBAdmin('kb-admin-panel');
    
    // Set up event listeners
    setupEventListeners();
    
    // Start service monitoring
    state.serviceMonitor.startPolling();
    
    // Welcome message
    state.chatWindow.addMessage(
        'system',
        'Welcome to GBStudio Automation Hub v3.2! Type your sprite generation request below.',
        { timestamp: new Date() }
    );
    
    console.log('Application initialized successfully');
}

function setupEventListeners() {
    // Chat input
    const sendBtn = document.getElementById('send-btn');
    const chatInput = document.getElementById('chat-input');
    
    sendBtn.addEventListener('click', handleSendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });
    
    // Panel toggles
    document.getElementById('toggle-monitor')?.addEventListener('click', () => {
        togglePanel('monitor');
    });
    
    document.getElementById('toggle-sprite-manager')?.addEventListener('click', () => {
        togglePanel('sprite-manager');
    });
    
    document.getElementById('toggle-batch-ops')?.addEventListener('click', () => {
        togglePanel('batch-ops');
    });
    
    document.getElementById('toggle-kb-admin')?.addEventListener('click', () => {
        togglePanel('kb-admin');
    });
}

function togglePanel(panelName) {
    const panels = {
        'monitor': document.getElementById('service-monitor'),
        'sprite-manager': document.getElementById('sprite-manager-panel'),
        'batch-ops': document.getElementById('batch-ops-panel'),
        'kb-admin': document.getElementById('kb-admin-panel')
    };
    
    if (panelName === 'monitor') {
        // Toggle monitor visibility
        const monitor = panels.monitor;
        monitor.style.display = monitor.style.display === 'none' ? 'block' : 'none';
        return;
    }
    
    // Close all side panels
    Object.keys(panels).forEach(key => {
        if (key !== 'monitor') {
            panels[key].style.display = 'none';
        }
    });
    
    // Open requested panel
    if (state.activePanel === panelName) {
        state.activePanel = null;
    } else {
        panels[panelName].style.display = 'block';
        state.activePanel = panelName;
        
        // Initialize panel if needed
        if (panelName === 'sprite-manager' && !state.spriteManager.initialized) {
            state.spriteManager.init();
            state.spriteManager.initialized = true;
        } else if (panelName === 'batch-ops' && !state.batchOps.initialized) {
            state.batchOps.render();
            state.batchOps.initialized = true;
        } else if (panelName === 'kb-admin' && !state.kbAdmin.initialized) {
            state.kbAdmin.init();
            state.kbAdmin.initialized = true;
        }
    }
}

async function handleSendMessage() {
    const chatInput = document.getElementById('chat-input');
    const message = chatInput.value.trim();

    if (!message) return;

    // Clear input
    chatInput.value = '';

    // Add user message to chat
    state.chatWindow.addMessage('user', message, { timestamp: new Date() });

    // Show typing indicator
    state.chatWindow.showTypingIndicator();

    // Update status
    updateStatus('Sending to PM Agent...');

    try {
        // Send to PM agent with selected preset
        const response = await apiCall('/api/v1/prompt', 'POST', {
            message: message,
            session_id: state.sessionId,
            preset: state.currentPreset
        });

        // Hide typing indicator
        state.chatWindow.hideTypingIndicator();

        // Add PM response
        const pmMessage = state.chatWindow.addMessage(
            'assistant',
            response.message,
            { timestamp: new Date() }
        );

        // If requires approval, add approval buttons
        if (response.requires_approval && response.plan) {
            pmMessage.addApprovalButtons(
                response.plan,
                () => handleApproval(response.plan),
                () => handleCancel()
            );
        }

        updateStatus('Ready');

    } catch (error) {
        console.error('Failed to send message:', error);

        // Hide typing indicator on error
        state.chatWindow.hideTypingIndicator();

        state.chatWindow.addMessage(
            'system',
            `Error: ${error.message}`,
            { timestamp: new Date(), type: 'error' }
        );
        updateStatus('Error occurred');
    }
}

async function handleApproval(plan) {
    updateStatus('Executing generation plan...');
    
    try {
        // Execute plan
        const response = await apiCall('/api/v1/execute', 'POST', {
            plan: plan,
            session_id: state.sessionId
        });
        
        const promptId = response.prompt_id;
        
        // Add progress message
        const progressMessage = state.chatWindow.addMessage(
            'system',
            'Generation started...',
            { timestamp: new Date() }
        );
        
        const progressBar = progressMessage.addProgressBar(promptId);
        
        // Connect to ComfyUI WebSocket for progress
        connectComfyUIWebSocket(promptId, progressBar);
        
        // Poll for completion
        pollGenerationStatus(promptId, progressBar);
        
    } catch (error) {
        console.error('Execution failed:', error);
        state.chatWindow.addMessage(
            'system',
            `Execution failed: ${error.message}`,
            { timestamp: new Date(), type: 'error' }
        );
        updateStatus('Execution failed');
    }
}

function handleCancel() {
    state.chatWindow.addMessage(
        'system',
        'Generation cancelled by user.',
        { timestamp: new Date() }
    );
    updateStatus('Ready');
}

function connectComfyUIWebSocket(promptId, progressBar) {
    if (state.comfyWSConnection) {
        state.comfyWSConnection.close();
    }
    
    state.comfyWSConnection = new ComfyUIWebSocket(
        `ws://localhost:8188/ws?clientId=gbstudio_${state.sessionId}`,
        {
            onMessage: (data) => {
                if (data.type === 'progress' && data.data.prompt_id === promptId) {
                    const percent = (data.data.value / data.data.max) * 100;
                    progressBar.update(percent);
                }
            },
            onError: (error) => {
                console.error('WebSocket error:', error);
            }
        }
    );
    
    state.comfyWSConnection.connect();
}

async function pollGenerationStatus(promptId, progressBar) {
    const maxAttempts = 120; // 10 minutes (5s interval)
    let attempts = 0;
    
    const interval = setInterval(async () => {
        attempts++;
        
        try {
            const status = await apiCall(`/api/v1/generation/${promptId}/status`, 'GET');
            
            if (status.status === 'completed') {
                clearInterval(interval);
                progressBar.complete();
                
                // Add success message with sprite info
                state.chatWindow.addMessage(
                    'system',
                    `âœ… Sprite generation complete! Sprite ID: ${status.sprite_id}`,
                    { timestamp: new Date(), type: 'success' }
                );
                
                // Show regeneration controls
                showRegenerationControls(status.sprite_id);
                
                updateStatus('Ready');
                
            } else if (status.status === 'failed') {
                clearInterval(interval);
                progressBar.error();
                
                state.chatWindow.addMessage(
                    'system',
                    `❌ Generation failed: ${status.error}`,
                    { timestamp: new Date(), type: 'error' }
                );
                
                updateStatus('Generation failed');
            }
            
        } catch (error) {
            console.error('Status poll failed:', error);
        }
        
        if (attempts >= maxAttempts) {
            clearInterval(interval);
            progressBar.error();
            state.chatWindow.addMessage(
                'system',
                '⏱️ Generation timed out',
                { timestamp: new Date(), type: 'error' }
            );
        }
    }, 5000);
}

function showRegenerationControls(spriteId) {
    const regenControls = document.getElementById('regeneration-controls');
    regenControls.style.display = 'block';
    
    state.regenerationUI.renderRegenerateButton(state.sessionId, spriteId);
}

function handlePresetChange(presetName) {
    state.currentPreset = presetName;
    console.log(`Style preset changed to: ${presetName}`);
}

function updateStatus(text) {
    const statusText = document.getElementById('status-text');
    if (statusText) {
        statusText.textContent = text;
    }
}

function generateSessionId() {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// Export for debugging
window.gbstudioApp = state;
