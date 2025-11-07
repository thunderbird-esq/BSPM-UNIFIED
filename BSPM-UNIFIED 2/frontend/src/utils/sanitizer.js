/**
 * HTML Sanitizer Utility
 * Version: 1.0
 *
 * Provides safe HTML sanitization and escaping to prevent XSS attacks.
 */

class HTMLSanitizer {
    constructor() {
        // Whitelist of allowed HTML tags
        this.allowedTags = new Set([
            'p', 'br', 'strong', 'em', 'u', 'span', 'div',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li',
            'code', 'pre',
            'a'
        ]);

        // Allowed attributes per tag
        this.allowedAttributes = {
            'a': ['href', 'title'],
            '*': ['class', 'id']  // Global attributes
        };

        // Safe URL protocols
        this.allowedProtocols = ['http:', 'https:'];
    }

    /**
     * Escapes HTML special characters to prevent XSS
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHTML(text) {
        if (typeof text !== 'string') {
            return '';
        }

        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Sanitizes HTML by removing dangerous tags and attributes
     * @param {string} html - HTML to sanitize
     * @returns {string} Sanitized HTML
     */
    sanitize(html) {
        if (typeof html !== 'string') {
            return '';
        }

        // Create a temporary DOM element
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;

        // Recursively sanitize the DOM tree
        this._sanitizeNode(tempDiv);

        return tempDiv.innerHTML;
    }

    /**
     * Recursively sanitizes a DOM node and its children
     * @private
     */
    _sanitizeNode(node) {
        // Process child nodes (iterate backwards to handle removals)
        for (let i = node.childNodes.length - 1; i >= 0; i--) {
            const child = node.childNodes[i];

            if (child.nodeType === Node.ELEMENT_NODE) {
                const tagName = child.tagName.toLowerCase();

                // Remove disallowed tags
                if (!this.allowedTags.has(tagName)) {
                    node.removeChild(child);
                    continue;
                }

                // Sanitize attributes
                this._sanitizeAttributes(child, tagName);

                // Recursively sanitize children
                this._sanitizeNode(child);

            } else if (child.nodeType === Node.TEXT_NODE) {
                // Text nodes are safe, keep them
                continue;
            } else {
                // Remove other node types (comments, processing instructions, etc.)
                node.removeChild(child);
            }
        }
    }

    /**
     * Sanitizes attributes of an element
     * @private
     */
    _sanitizeAttributes(element, tagName) {
        const allowedForTag = this.allowedAttributes[tagName] || [];
        const globalAllowed = this.allowedAttributes['*'] || [];
        const allowed = new Set([...allowedForTag, ...globalAllowed]);

        // Remove disallowed attributes
        const attrs = Array.from(element.attributes);
        for (const attr of attrs) {
            const attrName = attr.name.toLowerCase();

            // Remove event handlers (onclick, onerror, etc.)
            if (attrName.startsWith('on')) {
                element.removeAttribute(attr.name);
                continue;
            }

            // Remove disallowed attributes
            if (!allowed.has(attrName)) {
                element.removeAttribute(attr.name);
                continue;
            }

            // Validate href attributes
            if (attrName === 'href') {
                if (!this._isValidURL(attr.value)) {
                    element.removeAttribute(attr.name);
                }
            }
        }
    }

    /**
     * Validates URL to ensure it uses a safe protocol
     * @private
     */
    _isValidURL(url) {
        try {
            const parsed = new URL(url, window.location.href);
            return this.allowedProtocols.includes(parsed.protocol);
        } catch (e) {
            // Relative URLs are allowed
            return url.startsWith('/') || url.startsWith('./') || url.startsWith('../');
        }
    }

    /**
     * Sanitizes text for use in HTML attributes
     * @param {string} value - Attribute value to sanitize
     * @returns {string} Sanitized attribute value
     */
    sanitizeAttribute(value) {
        if (typeof value !== 'string') {
            return '';
        }

        return value
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#x27;')
            .replace(/\//g, '&#x2F;');
    }
}

// Create singleton instance
const sanitizer = new HTMLSanitizer();

// Export convenience functions
export function sanitizeHTML(html) {
    return sanitizer.sanitize(html);
}

export function escapeHTML(text) {
    return sanitizer.escapeHTML(text);
}

export function sanitizeAttribute(value) {
    return sanitizer.sanitizeAttribute(value);
}

export { HTMLSanitizer };
export default sanitizer;
