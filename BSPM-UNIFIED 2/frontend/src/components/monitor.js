/**
 * GBStudio Automation Hub - Service Monitor
 * Version: 3.1
 * Platform: Intel Mac (macOS Ventura) + Docker
 * 
 * Real-time service health monitoring with latency tracking
 */

export class ServiceMonitor {
    constructor() {
        this.services = {
            backend: { 
                name: 'FastAPI Backend', 
                url: 'http://localhost:8000/health', 
                status: 'unknown', 
                latency: null 
            },
            ollama: { 
                name: 'Ollama LLM', 
                url: 'http://localhost:11434/api/tags', 
                status: 'unknown', 
                latency: null 
            },
            comfyui: { 
                name: 'ComfyUI', 
                url: 'http://localhost:8188/system_stats', 
                status: 'unknown', 
                latency: null 
            }
        };
        this.pollInterval = 5000; // 5 seconds
        this.isPolling = false;
        this.pollIntervalId = null;
    }
    
    /**
     * Check individual service health
     * @param {string} serviceKey - Service identifier
     * @returns {Promise<Object>}
     */
    async checkService(serviceKey) {
        const service = this.services[serviceKey];
        const startTime = performance.now();
        
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 3000); // 3s timeout
            
            const response = await fetch(service.url, {
                method: 'GET',
                signal: controller.signal,
                cache: 'no-store'
            });
            
            clearTimeout(timeoutId);
            
            const latency = Math.round(performance.now() - startTime);
            
            if (response.ok) {
                this.updateServiceState(serviceKey, 'online', latency);
                return { status: 'online', latency };
            } else {
                this.updateServiceState(serviceKey, 'degraded', latency);
                return { status: 'degraded', latency };
            }
        } catch (error) {
            const latency = Math.round(performance.now() - startTime);
            this.updateServiceState(serviceKey, 'offline', latency);
            return { status: 'offline', latency, error: error.message };
        }
    }
    
    /**
     * Update service state
     * @param {string} serviceKey
     * @param {string} status - online, degraded, offline
     * @param {number} latency - Response time in ms
     */
    updateServiceState(serviceKey, status, latency) {
        this.services[serviceKey].status = status;
        this.services[serviceKey].latency = latency;
        this.renderServiceRow(serviceKey);
    }
    
    /**
     * Render individual service row
     * @param {string} serviceKey
     */
    renderServiceRow(serviceKey) {
        const service = this.services[serviceKey];
        const row = document.getElementById(`service-${serviceKey}`);
        
        if (!row) return;
        
        const statusDot = row.querySelector('.status-dot');
        const statusText = row.querySelector('.status-text');
        const latencyText = row.querySelector('.latency-text');
        
        // Update status indicator
        statusDot.className = `status-dot status-${service.status}`;
        statusText.textContent = service.status.toUpperCase();
        statusText.className = `status-text status-${service.status}`;
        
        // Update latency
        if (service.latency !== null) {
            let latencyClass = 'latency-good';
            if (service.latency > 1000) latencyClass = 'latency-slow';
            else if (service.latency > 500) latencyClass = 'latency-medium';
            
            latencyText.className = `latency-text ${latencyClass}`;
            latencyText.textContent = `${service.latency}ms`;
        } else {
            latencyText.textContent = '-';
        }
    }
    
    /**
     * Check all services
     */
    async checkAllServices() {
        const checks = Object.keys(this.services).map(key => this.checkService(key));
        await Promise.all(checks);
    }
    
    /**
     * Start polling loop
     */
    startPolling() {
        if (this.isPolling) return;
        
        this.isPolling = true;
        this.checkAllServices(); // Immediate check
        
        this.pollIntervalId = setInterval(() => {
            this.checkAllServices();
        }, this.pollInterval);
        
        console.log('[ServiceMonitor] Started polling');
    }
    
    /**
     * Stop polling loop
     */
    stopPolling() {
        if (this.pollIntervalId) {
            clearInterval(this.pollIntervalId);
            this.isPolling = false;
            console.log('[ServiceMonitor] Stopped polling');
        }
    }
    
    /**
     * Render complete dashboard
     */
    renderDashboard() {
        const container = document.getElementById('service-monitor');
        
        container.innerHTML = Object.entries(this.services).map(([key, service]) => `
            <div id="service-${key}" class="service-row">
                <span class="status-dot status-unknown"></span>
                <span class="service-name">${service.name}</span>
                <span class="status-text">CHECKING...</span>
                <span class="latency-text">-</span>
            </div>
        `).join('');
    }
}
