/**
 * GBStudio Automation Hub - Frontend Configuration
 * Version: 3.2
 *
 * This file sets global configuration variables for the frontend.
 * Edit these values to match your deployment environment.
 *
 * For local development:
 * - Use defaults (localhost:8000, localhost:8188, localhost:11434)
 *
 * For production:
 * - Update API_BASE_URL to your backend domain
 * - Update service hosts if using different infrastructure
 * - Set API_KEY for authenticated endpoints
 */

// Backend API Configuration
window.__API_BASE_URL__ = 'http://localhost:8000';

// API Key for authenticated endpoints (optional for development)
// Required for: /api/v1/execute, /api/v1/admin/kb/upload
// Get from: docker exec gbstudio_backend cat /app/secrets/api_keys.txt
window.__API_KEY__ = 'test-api-key-49a07b1d54218c8df192114e5eb35dcd';

// External Services
window.__COMFYUI_HOST__ = 'localhost:8188';
window.__OLLAMA_HOST__ = 'localhost:11434';

// Log configuration on startup
console.log('[CONFIG] GBStudio Automation Hub Frontend Configuration:', {
    API_BASE_URL: window.__API_BASE_URL__,
    API_KEY_CONFIGURED: !!window.__API_KEY__,
    COMFYUI_HOST: window.__COMFYUI_HOST__,
    OLLAMA_HOST: window.__OLLAMA_HOST__
});
