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
 * Generic API call wrapper
 *
 * @param {string} endpoint - API endpoint (e.g., '/api/v1/prompt')
 * @param {string} method - HTTP method (GET, POST, DELETE, etc.)
 * @param {Object} body - Request body (for POST/PUT)
 * @returns {Promise<Object>} Response data
 */
export async function apiCall(endpoint, method = 'GET', body = null) {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };

    if (body) {
        options.body = JSON.stringify(body);
    }

    const response = await fetchWithRetry(url, options);
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
