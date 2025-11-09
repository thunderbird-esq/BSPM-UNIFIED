/**
 * GBStudio Automation Hub - ComfyUI WebSocket Client
 * Version: 3.1
 * Platform: Intel Mac (macOS Ventura) + Docker
 * 
 * WebSocket wrapper with exponential backoff reconnection
 */

export class ComfyUIWebSocket {
    constructor(url, callbacks = {}) {
        this.url = url;
        this.callbacks = callbacks;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start at 1 second
        this.connect();
    }
    
    /**
     * Establish WebSocket connection
     */
    connect() {
        try {
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = () => {
                console.log('[WebSocket] Connected to ComfyUI');
                this.reconnectAttempts = 0;
                this.reconnectDelay = 1000;
                if (this.callbacks.onOpen) this.callbacks.onOpen();
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (this.callbacks.onMessage) this.callbacks.onMessage(data);
                } catch (error) {
                    console.error('[WebSocket] Failed to parse message:', error);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('[WebSocket] Error:', error);
                if (this.callbacks.onError) this.callbacks.onError(error);
            };
            
            this.ws.onclose = (event) => {
                console.log(`[WebSocket] Disconnected: ${event.reason} (${event.code})`);
                if (this.callbacks.onClose) this.callbacks.onClose(event);
                
                // Attempt reconnection with exponential backoff
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
                    console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                    setTimeout(() => this.connect(), delay);
                } else {
                    console.error('[WebSocket] Max reconnection attempts reached');
                    if (this.callbacks.onMaxReconnectFailed) this.callbacks.onMaxReconnectFailed();
                }
            };
        } catch (error) {
            console.error('[WebSocket] Failed to create connection:', error);
        }
    }
    
    /**
     * Send data through WebSocket
     * @param {Object} data - Data to send
     */
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.warn('[WebSocket] Cannot send - connection not open');
        }
    }
    
    /**
     * Close WebSocket connection
     */
    close() {
        if (this.ws) {
            this.reconnectAttempts = this.maxReconnectAttempts; // Prevent auto-reconnect
            this.ws.close();
        }
    }
}
