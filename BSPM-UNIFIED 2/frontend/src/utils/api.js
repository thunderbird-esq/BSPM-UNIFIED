/**
 * GBStudio Automation Hub - API Client
 * Version: 3.1
 * Platform: Intel Mac (macOS Ventura) + Docker
 * 
 * Fetch wrappers with retry logic and error handling
 * All requests use exponential backoff on failure
 */

const API_BASE_URL = 'http://localhost:8000';
const MAX_RETRIES = 3;
const INITIAL_RETRY_DELAY = 1000; // 1 second

/**
 * Fetch wrapper with retry logic
 * 
 * @param {string} url - Full URL to fetch
 * @param {Object} options - Fetch options
 * @param {number} retries - Number of retries attempted
 * @returns {Promise<Response>}
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
            // Exponential backoff: 1s, 2s, 4s
            const delay = INITIAL_RETRY_DELAY * Math.pow(2, retries);

            console.warn(`[API] Request failed, retrying in ${delay}ms (attempt ${retries + 1}/${MAX_RETRIES})...`);

            await sleep(delay);
            return fetchWithRetry(url, options, retries + 1);
        }

        // Max retries reached - show error UI
        console.error('[API] Max retries reached:', error);
        throw error;
    }
}

/**
 * Send user prompt to PM agent
 * 
 * @param {string} message - User message
 * @param {string} sessionId - Session identifier
 * @returns {Promise<Object>} PM response with plan
 */
export async function sendPrompt(message, sessionId) {
    const response = await fetchWithRetry(`${API_BASE_URL}/api/v1/prompt`, {
        method: 'POST',
        body: JSON.stringify({
            message,
            session_id: sessionId
        })
    });
    
    return await response.json();
}

/**
 * Execute approved delegation plan
 * 
 * @param {Array} plan - Delegation tasks array
 * @param {string} sessionId - Session identifier
 * @returns {Promise<Object>} Execution results
 */
export async function executeApprovedPlan(plan, sessionId) {
    const response = await fetchWithRetry(`${API_BASE_URL}/api/v1/execute`, {
        method: 'POST',
        body: JSON.stringify({
            plan,
            session_id: sessionId
        })
    });
    
    return await response.json();
}

/**
 * Check backend health status
 * 
 * @returns {Promise<Object>} Health status
 */
export async function checkHealth() {
    const response = await fetchWithRetry(`${API_BASE_URL}/health`, {
        method: 'GET'
    });
    
    return await response.json();
}

/**
 * Get ComfyUI history for a prompt
 * 
 * @param {string} promptId - ComfyUI prompt ID
 * @returns {Promise<Object>} History data
 */
export async function getComfyUIHistory(promptId) {
    const response = await fetchWithRetry(`http://localhost:8188/history/${promptId}`, {
        method: 'GET'
    });
    
    return await response.json();
}

/**
 * Sleep utility for retry delays
 *
 * @param {number} ms - Milliseconds to sleep
 * @returns {Promise<void>}
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Display error message with retry option
 *
 * @param {Error} error - Error object
 * @param {string} endpoint - API endpoint that failed
 */
export async function handleApiError(error, endpoint) {
    // Remove any existing error messages
    const existingErrors = document.querySelectorAll('.error-message');
    existingErrors.forEach(el => el.remove());

    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.setAttribute('role', 'alert');
    errorDiv.setAttribute('aria-live', 'assertive');

    errorDiv.innerHTML = `
        <p>ERROR: ${error.message || 'Network request failed'}</p>
        <button class="retry-button" onclick="window.retryRequest('${endpoint}')">RETRY</button>
    `;

    // Insert at top of main container
    const mainContainer = document.getElementById('main-container') || document.body;
    mainContainer.insertBefore(errorDiv, mainContainer.firstChild);

    // Auto-hide after 5 seconds
    setTimeout(() => {
        errorDiv.style.animation = 'slideInUp 0.3s ease-out reverse';
        setTimeout(() => errorDiv.remove(), 300);
    }, 5000);
}

/**
 * Show offline indicator
 */
export function showOfflineIndicator() {
    // Check if already exists
    if (document.getElementById('offline-indicator')) return;

    const indicator = document.createElement('div');
    indicator.id = 'offline-indicator';
    indicator.className = 'offline-indicator';
    indicator.setAttribute('role', 'alert');
    indicator.textContent = '⚠️ OFFLINE - Check your connection';

    document.body.insertBefore(indicator, document.body.firstChild);
}

/**
 * Hide offline indicator
 */
export function hideOfflineIndicator() {
    const indicator = document.getElementById('offline-indicator');
    if (indicator) {
        indicator.remove();
    }
}

/**
 * Monitor network status
 */
export function initNetworkMonitoring() {
    window.addEventListener('online', () => {
        hideOfflineIndicator();
        showSuccessToast('Connection restored');
    });

    window.addEventListener('offline', () => {
        showOfflineIndicator();
    });

    // Initial check
    if (!navigator.onLine) {
        showOfflineIndicator();
    }
}

/**
 * Show success toast notification
 */
function showSuccessToast(message) {
    const toast = document.createElement('div');
    toast.className = 'success-message';
    toast.style.cssText = 'position: fixed; bottom: 20px; right: 20px; z-index: 1800;';
    toast.innerHTML = `<p>${message}</p>`;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideInUp 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Global retry function for error buttons
 * This allows inline onclick handlers to work
 */
window.retryRequest = async function(endpoint) {
    console.log(`Retrying request to ${endpoint}...`);

    // Remove error message
    const errorMessages = document.querySelectorAll('.error-message');
    errorMessages.forEach(el => el.remove());

    // Show loading state
    const statusText = document.getElementById('status-text');
    if (statusText) {
        statusText.textContent = 'Retrying...';
    }

    // Trigger appropriate retry based on endpoint
    try {
        if (endpoint.includes('/prompt')) {
            // Retry last prompt - would need to be implemented in main.js
            console.log('Retry prompt request');
        } else if (endpoint.includes('/execute')) {
            // Retry execution
            console.log('Retry execution request');
        } else if (endpoint.includes('/health')) {
            await checkHealth();
            showSuccessToast('Health check successful');
        }
    } catch (error) {
        handleApiError(error, endpoint);
    } finally {
        if (statusText) {
            statusText.textContent = 'Ready';
        }
    }
};
