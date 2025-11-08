/**
 * GBStudio Automation Hub - API Client
 * Version: 3.2
 * Platform: Intel Mac (macOS Ventura) + Docker
 *
 * Fetch wrappers with retry logic and error handling
 * All requests use exponential backoff on failure
 *
 * Environment Variables (optional):
 * - VITE_API_BASE_URL: Backend API base URL (default: http://localhost:8000)
 * - VITE_API_KEY: API key for authenticated endpoints
 * - VITE_COMFYUI_HOST: ComfyUI host (default: localhost:8188)
 */

// Configuration with environment variable support
const API_BASE_URL = typeof window !== 'undefined' && window.__API_BASE_URL__
    ? window.__API_BASE_URL__
    : 'http://localhost:8000';

const API_KEY = typeof window !== 'undefined' && window.__API_KEY__
    ? window.__API_KEY__
    : null;

const COMFYUI_HOST = typeof window !== 'undefined' && window.__COMFYUI_HOST__
    ? window.__COMFYUI_HOST__
    : 'localhost:8188';

const MAX_RETRIES = 3;
const INITIAL_RETRY_DELAY = 1000; // 1 second

/**
 * Get authentication headers if API key is configured
 *
 * @returns {Object} Auth headers object
 */
function getAuthHeaders() {
    if (API_KEY) {
        return {
            'X-API-Key': API_KEY
        };
    }
    return {};
}

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
                ...getAuthHeaders(),
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
 * Generic API call wrapper - CRITICAL FUNCTION for frontend integration
 *
 * All components import and use this function for API requests.
 * Handles relative URLs, authentication, retry logic, and error handling.
 *
 * @param {string} endpoint - API endpoint (relative or absolute URL)
 * @param {string} method - HTTP method (GET, POST, PUT, DELETE)
 * @param {Object|null} data - Request body data (for POST/PUT)
 * @param {Object} options - Additional fetch options
 * @returns {Promise<Object>} Response data as JSON
 *
 * @example
 * // GET request
 * const sprites = await apiCall('/api/v1/sprites', 'GET');
 *
 * // POST request with data
 * const result = await apiCall('/api/v1/prompt', 'POST', {
 *     message: 'Create a knight sprite',
 *     session_id: 'session123'
 * });
 */
export async function apiCall(endpoint, method = 'GET', data = null, options = {}) {
    // Construct full URL (support both relative and absolute URLs)
    const url = endpoint.startsWith('http')
        ? endpoint
        : `${API_BASE_URL}${endpoint}`;

    // Build request options
    const fetchOptions = {
        method,
        ...options
    };

    // Add body for POST/PUT/PATCH requests
    if (data && ['POST', 'PUT', 'PATCH'].includes(method.toUpperCase())) {
        fetchOptions.body = JSON.stringify(data);
    }

    // Make request with retry logic
    const response = await fetchWithRetry(url, fetchOptions);

    // Parse and return JSON response
    return await response.json();
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
    const comfyUrl = `http://${COMFYUI_HOST}/history/${promptId}`;
    const response = await fetchWithRetry(comfyUrl, {
        method: 'GET'
    });

    return await response.json();
}

/**
 * Get current configuration (for debugging)
 *
 * @returns {Object} Current API configuration
 */
export function getConfig() {
    return {
        API_BASE_URL,
        COMFYUI_HOST,
        API_KEY_CONFIGURED: !!API_KEY,
        MAX_RETRIES,
        INITIAL_RETRY_DELAY
    };
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
