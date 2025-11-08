/**
 * GBStudio Automation Hub - Frontend Configuration
 * Version: 3.3
 *
 * This file sets global configuration variables for the frontend.
 * Edit these values to match your deployment environment.
 *
 * SECURITY WARNING:
 * - NEVER commit API keys to version control
 * - API_KEY should be set via environment variable or user input
 * - For production, implement session-based authentication
 *
 * For local development:
 * - Use defaults (localhost:8000, localhost:8188, localhost:11434)
 *
 * For production:
 * - Update API_BASE_URL to your backend domain
 * - Update service hosts if using different infrastructure
 * - Set API_KEY via environment variable
 */

// Backend API Configuration
window.__API_BASE_URL__ = 'http://localhost:8000';

// API Key for authenticated endpoints
// SECURITY: Load from environment variable or prompt user
// DO NOT hardcode keys in this file!
// Get your key from: docker exec gbstudio_backend cat /app/secrets/api_keys.txt
window.__API_KEY__ = null;  // User must set this

// Check for API key in localStorage (set by user on first visit)
if (typeof window !== 'undefined' && window.localStorage) {
    const storedKey = localStorage.getItem('gbstudio_api_key');
    if (storedKey) {
        window.__API_KEY__ = storedKey;
    } else {
        // For development only: Check if there's a dev key in session storage
        const devKey = sessionStorage.getItem('gbstudio_dev_api_key');
        if (devKey) {
            window.__API_KEY__ = devKey;
        } else {
            console.warn('[CONFIG] No API key configured. Authenticated endpoints will fail.');
            console.log('[CONFIG] Set your API key with: localStorage.setItem("gbstudio_api_key", "your-key-here")');
        }
    }
}

// External Services
window.__COMFYUI_HOST__ = 'localhost:8188';
window.__OLLAMA_HOST__ = 'localhost:11434';

// Log configuration on startup (DO NOT log the actual API key!)
console.log('[CONFIG] GBStudio Automation Hub Frontend Configuration:', {
    API_BASE_URL: window.__API_BASE_URL__,
    API_KEY_CONFIGURED: !!window.__API_KEY__,
    COMFYUI_HOST: window.__COMFYUI_HOST__,
    OLLAMA_HOST: window.__OLLAMA_HOST__
});
