# ACTION PLAN WITH SPECIFIC CODE FIXES
## BSPM-UNIFIED Repository Remediation

**Generated:** 2025-11-07
**Priority:** CRITICAL → HIGH → MEDIUM → LOW
**Format:** Issue → Current Code → Fixed Code → Testing

---

## 🔴 PHASE 1: CRITICAL SECURITY FIXES (IMMEDIATE)

### FIX 1.1: CORS Wildcard Configuration

**File:** `backend/main.py`
**Lines:** 249-255
**Time Estimate:** 15 minutes
**Priority:** CRITICAL

#### Current Code (VULNERABLE):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ❌ CRITICAL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Fixed Code:
```python
import os
from typing import List

# At top of file, add to imports
from fastapi.middleware.cors import CORSMiddleware

# After Settings class definition
ALLOWED_ORIGINS = os.getenv(
    'ALLOWED_ORIGINS',
    'http://localhost:8000,http://localhost:3000'
).split(',')

# Replace CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # ✅ Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Session-ID"],
    max_age=600,  # Cache preflight for 10 minutes
)
```

#### Environment Configuration:
Add to `.env` file:
```bash
# Development
ALLOWED_ORIGINS=http://localhost:8000,http://localhost:3000

# Production
# ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

#### Testing:
```python
# Add to tests/test_security.py
def test_cors_blocks_unauthorized_origins(client):
    response = client.get(
        '/health',
        headers={'Origin': 'http://malicious-site.com'}
    )
    assert 'access-control-allow-origin' not in response.headers or \
           response.headers['access-control-allow-origin'] != 'http://malicious-site.com'

def test_cors_allows_configured_origins(client):
    response = client.get(
        '/health',
        headers={'Origin': 'http://localhost:8000'}
    )
    assert response.headers['access-control-allow-origin'] == 'http://localhost:8000'
```

---

### FIX 1.2: Add Authentication to Admin Endpoints

**File:** `backend/main.py`
**Lines:** 1032-1154 (8 endpoints)
**Time Estimate:** 1 hour
**Priority:** CRITICAL

#### Current Code (VULNERABLE):
```python
@app.get("/api/v1/admin/kb/documents")
async def list_kb_documents():  # ❌ No authentication
    try:
        docs = kb_admin.list_documents()
        return {"documents": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### Fixed Code:
```python
from backend.security import verify_api_key, check_rate_limit

@app.get("/api/v1/admin/kb/documents")
async def list_kb_documents(
    api_key: str = Depends(verify_api_key),  # ✅ Require API key
    rate_limit: bool = Depends(check_rate_limit)  # ✅ Rate limit
):
    try:
        docs = kb_admin.list_documents()
        logger.info(
            "Admin KB documents listed",
            extra={'api_key_prefix': api_key[:8], 'count': len(docs)}
        )
        return {"documents": docs}
    except Exception as e:
        logger.error(f"Failed to list KB documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/admin/kb/upload")
async def upload_kb_document(
    file: UploadFile,
    api_key: str = Depends(verify_api_key),  # ✅ Require API key
    rate_limit: bool = Depends(check_rate_limit)
):
    try:
        content = await file.read()
        doc_id = kb_admin.upload_document(
            filename=file.filename,
            content=content.decode('utf-8')
        )
        logger.info(
            "Admin KB document uploaded",
            extra={'api_key_prefix': api_key[:8], 'doc_id': doc_id}
        )
        return {"doc_id": doc_id, "filename": file.filename}
    except Exception as e:
        logger.error(f"Failed to upload KB document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/admin/kb/documents")
async def delete_all_kb_documents(
    api_key: str = Depends(verify_api_key),  # ✅ Require API key
    rate_limit: bool = Depends(check_rate_limit),
    confirm: bool = False  # ✅ Require explicit confirmation
):
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true to delete all documents"
        )

    try:
        count = kb_admin.delete_all_documents()
        logger.warning(
            "Admin KB all documents deleted",
            extra={'api_key_prefix': api_key[:8], 'count': count}
        )
        return {"deleted": count}
    except Exception as e:
        logger.error(f"Failed to delete all KB documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

#### Apply to All 8 Admin Endpoints:
1. `GET /api/v1/admin/kb/documents`
2. `GET /api/v1/admin/kb/documents/{doc_id}`
3. `POST /api/v1/admin/kb/reindex`
4. `POST /api/v1/admin/kb/upload`
5. `DELETE /api/v1/admin/kb/documents`
6. `POST /api/v1/admin/kb/search-test`
7. `GET /api/v1/admin/kb/stats`
8. `POST /api/v1/admin/kb/rebuild`

#### Testing:
```python
# tests/test_security.py
def test_admin_endpoint_requires_auth(client):
    response = client.get('/api/v1/admin/kb/documents')
    assert response.status_code == 403  # Forbidden without API key

def test_admin_endpoint_with_valid_key(client):
    response = client.get(
        '/api/v1/admin/kb/documents',
        headers={'X-API-Key': 'valid-test-key'}
    )
    assert response.status_code == 200

def test_admin_delete_requires_confirmation(client):
    response = client.delete(
        '/api/v1/admin/kb/documents',
        headers={'X-API-Key': 'valid-test-key'}
    )
    assert response.status_code == 400
    assert 'confirm' in response.json()['detail'].lower()
```

---

### FIX 1.3: Path Traversal Vulnerability

**File:** `backend/kb_admin.py`
**Lines:** 154-167, 222, 245-255
**Time Estimate:** 30 minutes
**Priority:** HIGH

#### Current Code (VULNERABLE):
```python
def reindex_document(self, source_file: str) -> Dict[str, Any]:
    file_path = self.docs_dir / source_file  # ❌ Direct user input
    if not file_path.exists():
        raise FileNotFoundError(f"Document not found: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
```

#### Fixed Code:
```python
import os
from pathlib import Path
from typing import Dict, Any

class KBAdmin:
    def __init__(self, docs_dir: str, vectorstore_dir: str):
        self.docs_dir = Path(docs_dir).resolve()  # ✅ Resolve to absolute
        self.vectorstore_dir = Path(vectorstore_dir).resolve()
        self.logger = structlog.get_logger(__name__)

    def _validate_safe_path(self, filename: str, base_dir: Path) -> Path:
        """
        Validate that filename doesn't contain path traversal attempts.

        Args:
            filename: User-provided filename
            base_dir: Base directory (must be absolute)

        Returns:
            Validated absolute path within base_dir

        Raises:
            ValueError: If path traversal detected
        """
        # Remove any directory components, keep only basename
        safe_name = os.path.basename(filename)

        # Ensure it's a markdown file
        if not safe_name.endswith('.md'):
            safe_name = f"{safe_name}.md"

        # Construct full path
        full_path = (base_dir / safe_name).resolve()

        # Verify path is within base directory
        try:
            full_path.relative_to(base_dir)
        except ValueError:
            self.logger.warning(
                "Path traversal attempt detected",
                extra={'filename': filename, 'base_dir': str(base_dir)}
            )
            raise ValueError(
                f"Invalid file path: {filename} attempts to access "
                f"outside allowed directory"
            )

        return full_path

    def reindex_document(self, source_file: str) -> Dict[str, Any]:
        """
        Reindex a document in the knowledge base.

        Args:
            source_file: Filename (basename only, no paths)

        Returns:
            Reindex result with status and chunk count

        Raises:
            ValueError: If path traversal detected
            FileNotFoundError: If document doesn't exist
        """
        # Validate path
        file_path = self._validate_safe_path(source_file, self.docs_dir)

        if not file_path.exists():
            raise FileNotFoundError(
                f"Document not found: {file_path.name}"
            )

        # Read and reindex
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        chunk_ids = self.kb.add_project_document(
            content=content,
            source_file=file_path.name
        )

        self.logger.info(
            "Document reindexed",
            extra={
                'filename': file_path.name,
                'chunks': len(chunk_ids)
            }
        )

        return {
            "status": "reindexed",
            "filename": file_path.name,
            "chunks": len(chunk_ids)
        }

    def delete_document(self, source_file: str) -> Dict[str, Any]:
        """
        Delete document from knowledge base.

        Args:
            source_file: Filename (basename only)

        Returns:
            Delete result with chunk count
        """
        # Validate path
        file_path = self._validate_safe_path(source_file, self.docs_dir)

        # Find and delete chunks
        deleted_count = 0
        for doc_id, doc in list(self.kb.documents.items()):
            if doc.metadata.get('source_file') == file_path.name:
                # Remove from FAISS index and metadata
                self.kb._remove_document(doc_id)
                deleted_count += 1

        self.logger.info(
            "Document deleted from KB",
            extra={
                'filename': file_path.name,
                'chunks_deleted': deleted_count
            }
        )

        return {
            "status": "deleted",
            "filename": file_path.name,
            "chunks_deleted": deleted_count
        }

    def upload_document(self, filename: str, content: str) -> str:
        """
        Upload new document to knowledge base.

        Args:
            filename: Desired filename (will be sanitized)
            content: Document content (markdown)

        Returns:
            Document ID
        """
        # Validate and sanitize filename
        safe_path = self._validate_safe_path(filename, self.docs_dir)

        # Check if file already exists
        if safe_path.exists():
            self.logger.warning(
                "Attempted to upload existing document",
                extra={'filename': safe_path.name}
            )
            raise ValueError(
                f"Document {safe_path.name} already exists. "
                f"Use reindex endpoint to update."
            )

        # Write file
        safe_path.write_text(content, encoding='utf-8')

        # Index in knowledge base
        chunk_ids = self.kb.add_project_document(
            content=content,
            source_file=safe_path.name
        )

        self.logger.info(
            "Document uploaded and indexed",
            extra={
                'filename': safe_path.name,
                'chunks': len(chunk_ids),
                'size_bytes': len(content)
            }
        )

        return chunk_ids[0] if chunk_ids else None
```

#### Testing:
```python
# tests/test_security.py
def test_path_traversal_blocked():
    kb_admin = KBAdmin(docs_dir='/app/docs', vectorstore_dir='/app/vectorstore')

    # Test various path traversal attempts
    malicious_paths = [
        '../../../etc/passwd',
        '..\\..\\..\\windows\\system32\\config',
        'docs/../../../etc/hosts',
        '/etc/passwd',
        '../../../../secrets/api_keys.txt'
    ]

    for malicious_path in malicious_paths:
        with pytest.raises(ValueError, match="path traversal|outside allowed"):
            kb_admin._validate_safe_path(malicious_path, Path('/app/docs'))

def test_valid_filename_allowed():
    kb_admin = KBAdmin(docs_dir='/app/docs', vectorstore_dir='/app/vectorstore')

    valid_path = kb_admin._validate_safe_path('technical_guide.md', Path('/app/docs'))

    assert valid_path == Path('/app/docs/technical_guide.md')
    assert valid_path.is_relative_to(Path('/app/docs'))
```

---

### FIX 1.4: XSS Vulnerabilities in Frontend

**Files:** Multiple frontend components
**Time Estimate:** 1.5 hours
**Priority:** HIGH

#### Install DOMPurify (Recommended Approach):

**Option 1: Use DOMPurify Library**

Add to `frontend/index.html`:
```html
<script src="https://cdn.jsdelivr.net/npm/dompurify@3.0.6/dist/purify.min.js"></script>
```

**Option 2: Create Sanitizer Utility (No Dependencies)**

Create `frontend/src/utils/sanitizer.js`:
```javascript
/**
 * Sanitize HTML to prevent XSS attacks
 * Removes all potentially dangerous tags and attributes
 */
export class HTMLSanitizer {
    constructor() {
        // Allowed tags (whitelist)
        this.allowedTags = [
            'p', 'br', 'strong', 'em', 'u', 'span', 'div',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li',
            'code', 'pre',
            'a'
        ];

        // Allowed attributes per tag
        this.allowedAttributes = {
            'a': ['href', 'title'],
            'span': ['class'],
            'div': ['class'],
            'code': ['class']
        };
    }

    /**
     * Escape HTML special characters
     */
    escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /**
     * Sanitize HTML string
     */
    sanitize(html) {
        const temp = document.createElement('div');
        temp.innerHTML = html;

        return this._sanitizeNode(temp).innerHTML;
    }

    /**
     * Recursively sanitize DOM node
     */
    _sanitizeNode(node) {
        const clean = document.createElement('div');

        Array.from(node.childNodes).forEach(child => {
            if (child.nodeType === Node.TEXT_NODE) {
                clean.appendChild(document.createTextNode(child.textContent));
            } else if (child.nodeType === Node.ELEMENT_NODE) {
                const tagName = child.tagName.toLowerCase();

                if (this.allowedTags.includes(tagName)) {
                    const newElement = document.createElement(tagName);

                    // Copy allowed attributes
                    const allowedAttrs = this.allowedAttributes[tagName] || [];
                    Array.from(child.attributes).forEach(attr => {
                        if (allowedAttrs.includes(attr.name)) {
                            // Extra validation for href
                            if (attr.name === 'href') {
                                const href = attr.value;
                                // Only allow http, https, and relative URLs
                                if (href.match(/^(https?:\/\/|\/|\.\/)/)) {
                                    newElement.setAttribute(attr.name, href);
                                }
                            } else {
                                newElement.setAttribute(attr.name, attr.value);
                            }
                        }
                    });

                    // Recursively sanitize children
                    const sanitizedChild = this._sanitizeNode(child);
                    newElement.innerHTML = sanitizedChild.innerHTML;

                    clean.appendChild(newElement);
                }
            }
        });

        return clean;
    }
}

// Create singleton instance
export const sanitizer = new HTMLSanitizer();

// Convenience functions
export function sanitizeHTML(html) {
    return sanitizer.sanitize(html);
}

export function escapeHTML(str) {
    return sanitizer.escapeHTML(str);
}
```

#### Fix sprite-manager-ui.js:

**File:** `frontend/src/components/sprite-manager-ui.js`
**Lines:** 66, 345

```javascript
import { sanitizeHTML, escapeHTML } from '../utils/sanitizer.js';

class SpriteManagerUI {
    // ... existing code ...

    renderSpriteList(sprites) {
        // ❌ OLD (VULNERABLE):
        // this.container.innerHTML = html;

        // ✅ NEW (SAFE):
        const html = sprites.map(sprite => `
            <div class="sprite-item" data-sprite-id="${escapeHTML(sprite.id)}">
                <span class="sprite-name"></span>
                <span class="sprite-type"></span>
                <button class="edit-btn">Edit</button>
            </div>
        `).join('');

        this.container.innerHTML = html;

        // Set text content safely
        sprites.forEach((sprite, index) => {
            const item = this.container.children[index];
            item.querySelector('.sprite-name').textContent = sprite.name;
            item.querySelector('.sprite-type').textContent = sprite.type;
        });
    }

    showEditModal(sprite) {
        // ❌ OLD (VULNERABLE):
        // modal.innerHTML = `<div>${sprite.name}</div>`;

        // ✅ NEW (SAFE):
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <h3>Edit Sprite</h3>
                <label>Name: <input type="text" class="sprite-name-input" /></label>
                <label>Type: <select class="sprite-type-select">
                    <option value="idle">Idle</option>
                    <option value="walk">Walk</option>
                    <option value="attack">Attack</option>
                </select></label>
                <button class="save-btn">Save</button>
                <button class="cancel-btn">Cancel</button>
            </div>
        `;

        // Set values safely
        modal.querySelector('.sprite-name-input').value = sprite.name;
        modal.querySelector('.sprite-type-select').value = sprite.type;

        document.body.appendChild(modal);
    }
}
```

#### Fix kb-admin.js:

**File:** `frontend/src/components/kb-admin.js`
**Lines:** 371, 423

```javascript
import { sanitizeHTML, escapeHTML } from '../utils/sanitizer.js';

class KBAdminUI {
    // ... existing code ...

    async searchKB(query) {
        const response = await fetch('/api/v1/admin/kb/search-test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, limit: 5 })
        });

        const data = await response.json();

        // ❌ OLD (VULNERABLE):
        // resultsDiv.innerHTML = `<h4>Results for "${data.query}"...</h4>`;

        // ✅ NEW (SAFE):
        const resultsDiv = document.getElementById('search-results');
        resultsDiv.innerHTML = '';

        const header = document.createElement('h4');
        header.textContent = `Results for "${data.query}" (${data.results.length} found)`;
        resultsDiv.appendChild(header);

        data.results.forEach((result, index) => {
            const resultEl = document.createElement('div');
            resultEl.className = 'result-item';

            const titleEl = document.createElement('h5');
            titleEl.textContent = `Result ${index + 1}`;

            const contentEl = document.createElement('div');
            contentEl.className = 'result-content';
            // Use sanitizer for user-generated content
            contentEl.innerHTML = sanitizeHTML(result.content);

            const metaEl = document.createElement('div');
            metaEl.className = 'result-meta';
            metaEl.textContent = `Type: ${result.metadata.type}, Distance: ${result.distance.toFixed(3)}`;

            resultEl.appendChild(titleEl);
            resultEl.appendChild(contentEl);
            resultEl.appendChild(metaEl);
            resultsDiv.appendChild(resultEl);
        });
    }
}
```

#### Testing:
```javascript
// tests/frontend/test_sanitizer.js
import { sanitizeHTML, escapeHTML } from '../src/utils/sanitizer.js';

describe('HTML Sanitizer', () => {
    it('escapes dangerous HTML', () => {
        const dangerous = '<script>alert("XSS")</script>';
        const escaped = escapeHTML(dangerous);
        assert.equal(escaped, '&lt;script&gt;alert("XSS")&lt;/script&gt;');
    });

    it('removes script tags', () => {
        const html = '<div>Safe</div><script>alert("XSS")</script>';
        const clean = sanitizeHTML(html);
        assert.isFalse(clean.includes('<script>'));
        assert.isTrue(clean.includes('<div>Safe</div>'));
    });

    it('removes event handlers', () => {
        const html = '<div onclick="alert(\'XSS\')">Click me</div>';
        const clean = sanitizeHTML(html);
        assert.isFalse(clean.includes('onclick'));
    });

    it('allows safe tags', () => {
        const html = '<p>Paragraph</p><strong>Bold</strong><em>Italic</em>';
        const clean = sanitizeHTML(html);
        assert.equal(clean, html);
    });

    it('sanitizes href attributes', () => {
        const html = '<a href="javascript:alert(\'XSS\')">Click</a>';
        const clean = sanitizeHTML(html);
        assert.isFalse(clean.includes('javascript:'));
    });
});
```

---

### FIX 1.5: Race Conditions in Shared State

**Files:** `backend/graceful_degradation.py`, `backend/security.py`
**Time Estimate:** 45 minutes
**Priority:** CRITICAL

#### Fix graceful_degradation.py:

```python
import threading
import time
from typing import Dict, Optional
import structlog

logger = structlog.get_logger(__name__)


class DegradedMode:
    """
    Thread-safe degraded mode manager.
    Tracks which services are degraded and provides fallback responses.
    """

    def __init__(self):
        self.degraded_services: Dict[str, Dict] = {}
        self._lock = threading.RLock()  # ✅ Reentrant lock for thread safety
        logger.info("DegradedMode initialized")

    def mark_degraded(self, service: str, reason: str) -> None:
        """
        Mark a service as degraded (thread-safe).

        Args:
            service: Service name (e.g., 'ollama', 'comfyui')
            reason: Reason for degradation
        """
        with self._lock:  # ✅ Synchronized access
            self.degraded_services[service] = {
                'reason': reason,
                'marked_at': time.time()
            }
            logger.warning(
                f"Service marked as degraded: {service}",
                extra={'service': service, 'reason': reason}
            )

    def mark_recovered(self, service: str) -> None:
        """
        Mark a service as recovered (thread-safe).

        Args:
            service: Service name
        """
        with self._lock:  # ✅ Synchronized access
            if service in self.degraded_services:
                del self.degraded_services[service]
                logger.info(
                    f"Service recovered: {service}",
                    extra={'service': service}
                )

    def is_degraded(self, service: str) -> bool:
        """
        Check if service is degraded (thread-safe).

        Args:
            service: Service name

        Returns:
            True if service is degraded
        """
        with self._lock:  # ✅ Synchronized read
            return service in self.degraded_services

    def get_degraded_services(self) -> Dict[str, Dict]:
        """
        Get all degraded services (thread-safe).

        Returns:
            Copy of degraded services dict
        """
        with self._lock:  # ✅ Synchronized read
            return self.degraded_services.copy()  # Return copy to prevent external modification

    def get_fallback_response(self, service: str) -> Dict:
        """
        Get fallback response for degraded service (thread-safe).

        Args:
            service: Service name

        Returns:
            Fallback response dict
        """
        with self._lock:  # ✅ Synchronized read
            degradation_info = self.degraded_services.get(service, {})

        return {
            "status": "degraded",
            "service": service,
            "reason": degradation_info.get('reason', 'Unknown'),
            "degraded_since": degradation_info.get('marked_at'),
            "message": f"Service {service} is currently degraded. Using fallback response."
        }
```

#### Fix security.py:

```python
import threading
import time
from typing import Dict, Tuple, Optional
import structlog

logger = structlog.get_logger(__name__)


class RateLimiter:
    """
    Thread-safe token bucket rate limiter.
    Limits requests per bucket (e.g., per IP or API key).
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds

        # bucket_id -> (token_count, last_refill_time)
        self.buckets: Dict[str, Tuple[int, float]] = {}
        self._lock = threading.RLock()  # ✅ Reentrant lock for thread safety

        logger.info(
            "RateLimiter initialized",
            extra={
                'max_requests': max_requests,
                'window_seconds': window_seconds
            }
        )

    def is_allowed(self, bucket_id: str) -> bool:
        """
        Check if request is allowed (thread-safe).

        Args:
            bucket_id: Identifier for rate limit bucket (IP, API key, etc.)

        Returns:
            True if request allowed, False if rate limit exceeded
        """
        with self._lock:  # ✅ Synchronized access
            current_time = time.time()

            # Get or create bucket
            if bucket_id not in self.buckets:
                self.buckets[bucket_id] = (self.max_requests - 1, current_time)
                return True

            tokens, last_refill = self.buckets[bucket_id]

            # Calculate token refill
            time_passed = current_time - last_refill
            tokens_to_add = int(time_passed / self.window_seconds * self.max_requests)

            if tokens_to_add > 0:
                tokens = min(self.max_requests, tokens + tokens_to_add)
                last_refill = current_time

            # Check if request allowed
            if tokens > 0:
                self.buckets[bucket_id] = (tokens - 1, last_refill)
                return True
            else:
                self.buckets[bucket_id] = (tokens, last_refill)
                logger.warning(
                    "Rate limit exceeded",
                    extra={'bucket_id': bucket_id}
                )
                return False

    def get_remaining(self, bucket_id: str) -> int:
        """
        Get remaining requests for bucket (thread-safe).

        Args:
            bucket_id: Bucket identifier

        Returns:
            Number of remaining requests
        """
        with self._lock:  # ✅ Synchronized read
            if bucket_id not in self.buckets:
                return self.max_requests

            tokens, _ = self.buckets[bucket_id]
            return max(0, tokens)

    def cleanup_old_buckets(self, max_age_seconds: int = 3600) -> int:
        """
        Remove old buckets to prevent memory leak (thread-safe).

        Args:
            max_age_seconds: Maximum age of bucket before cleanup

        Returns:
            Number of buckets removed
        """
        with self._lock:  # ✅ Synchronized access
            current_time = time.time()
            old_buckets = [
                bucket_id
                for bucket_id, (_, last_refill) in self.buckets.items()
                if current_time - last_refill > max_age_seconds
            ]

            for bucket_id in old_buckets:
                del self.buckets[bucket_id]

            if old_buckets:
                logger.info(
                    f"Cleaned up {len(old_buckets)} old rate limit buckets"
                )

            return len(old_buckets)
```

#### Testing:
```python
# tests/test_thread_safety.py
import threading
import time
from backend.graceful_degradation import DegradedMode
from backend.security import RateLimiter


def test_degraded_mode_thread_safety():
    """Test concurrent access to DegradedMode."""
    degraded = DegradedMode()
    errors = []

    def mark_degraded():
        try:
            for i in range(100):
                degraded.mark_degraded(f'service{i % 5}', f'reason{i}')
        except Exception as e:
            errors.append(e)

    def check_degraded():
        try:
            for i in range(100):
                _ = degraded.is_degraded(f'service{i % 5}')
        except Exception as e:
            errors.append(e)

    # Create 10 threads
    threads = []
    for _ in range(5):
        threads.append(threading.Thread(target=mark_degraded))
        threads.append(threading.Thread(target=check_degraded))

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for completion
    for thread in threads:
        thread.join()

    # No errors should occur
    assert len(errors) == 0


def test_rate_limiter_thread_safety():
    """Test concurrent access to RateLimiter."""
    limiter = RateLimiter(max_requests=100, window_seconds=1)
    allowed_count = 0
    lock = threading.Lock()
    errors = []

    def make_requests():
        nonlocal allowed_count
        try:
            for i in range(50):
                if limiter.is_allowed('test_bucket'):
                    with lock:
                        allowed_count += 1
        except Exception as e:
            errors.append(e)

    # Create 10 threads
    threads = [threading.Thread(target=make_requests) for _ in range(10)]

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for completion
    for thread in threads:
        thread.join()

    # No errors should occur
    assert len(errors) == 0

    # Total allowed should not exceed limit
    assert allowed_count <= 100
```

---

## 🟡 PHASE 2: HIGH PRIORITY FIXES

### FIX 2.1: Silent Error Handling

**Files:** Multiple
**Time Estimate:** 4 hours
**Priority:** HIGH

#### Pattern to Fix:

**Before (SILENT):**
```python
except Exception:
    pass  # ❌ Silent failure
```

**After (LOGGED):**
```python
except Exception as e:
    logger.error(
        "Operation failed",
        exc_info=True,
        extra={'context': 'relevant_data'}
    )
    # Optionally re-raise or return error response
```

#### Specific Fixes:

**1. comfyui/executor.py:98-99**
```python
# BEFORE:
except aiohttp.ClientError:
    pass  # Continue polling

# AFTER:
except aiohttp.ClientError as e:
    logger.debug(
        "Polling error (retrying)",
        extra={
            'error': str(e),
            'prompt_id': prompt_id,
            'elapsed': time.time() - start_time
        }
    )
    await asyncio.sleep(0.5)  # Brief delay before retry
    continue
```

**2. memory/conversation.py:58-59**
```python
# BEFORE:
except json.JSONDecodeError:
    continue  # Skip corrupted line

# AFTER:
except json.JSONDecodeError as e:
    logger.warning(
        "Corrupted conversation turn detected",
        extra={
            'line_number': i,
            'line_preview': line[:100],
            'error': str(e)
        }
    )
    continue
```

**3. Add to ALL exception handlers:**
- Log with appropriate level (debug/info/warning/error)
- Include relevant context in `extra` dict
- Use `exc_info=True` for ERROR level
- Consider metrics increment for error tracking

---

### FIX 2.2: Input Validation with Pydantic

**Files:** Multiple API endpoints
**Time Estimate:** 3 hours
**Priority:** HIGH

#### Create validation models:

**File:** `backend/models.py` (new file)
```python
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal, List
from enum import Enum


class SpriteType(str, Enum):
    """Allowed sprite types."""
    IDLE = 'idle'
    WALK = 'walk'
    ATTACK = 'attack'
    JUMP = 'jump'
    HURT = 'hurt'


class ExportFormat(str, Enum):
    """Allowed export formats."""
    GRID = 'grid'
    STRIP = 'strip'
    INDIVIDUAL_FRAMES = 'individual_frames'


class PromptRequest(BaseModel):
    """Request to PM agent."""
    message: str = Field(..., min_length=1, max_length=5000)
    session_id: Optional[str] = Field(None, max_length=100)

    @validator('message')
    def message_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty or whitespace')
        return v.strip()


class SpriteEditRequest(BaseModel):
    """Request to edit sprite."""
    sprite_id: str = Field(..., min_length=1, max_length=100)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    sprite_type: Optional[SpriteType] = None

    @validator('name')
    def name_alphanumeric(cls, v):
        if v and not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Sprite name must be alphanumeric (allow _ and -)')
        return v


class BatchCSVRow(BaseModel):
    """Single row in batch CSV."""
    character: str = Field(..., min_length=1, max_length=200)
    action: str = Field(..., min_length=1, max_length=200)
    style: str = Field(..., min_length=1, max_length=200)
    priority: Optional[int] = Field(1, ge=1, le=10)


class KBSearchRequest(BaseModel):
    """Knowledge base search request."""
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(5, ge=1, le=50)
    filter_type: Optional[Literal['project_doc', 'conversation']] = None


class SpriteGenerationParams(BaseModel):
    """Sprite generation parameters."""
    character: str = Field(..., min_length=1, max_length=200)
    action: str = Field(..., min_length=1, max_length=200)
    style: str = Field('pixel art', max_length=200)
    num_frames: int = Field(8, ge=1, le=16)
    width: int = Field(32, ge=16, le=128)
    height: int = Field(32, ge=16, le=128)
    steps: int = Field(20, ge=10, le=50)
    cfg_scale: float = Field(7.0, ge=1.0, le=20.0)
```

#### Apply to endpoints:

**File:** `backend/main.py`
```python
from backend.models import (
    PromptRequest,
    SpriteEditRequest,
    KBSearchRequest,
    SpriteGenerationParams
)

# BEFORE:
@app.post("/api/v1/prompt")
async def send_prompt(request: dict):
    message = request.get('message')  # ❌ No validation
    ...

# AFTER:
@app.post("/api/v1/prompt")
async def send_prompt(request: PromptRequest):  # ✅ Validated
    message = request.message  # Guaranteed to be valid
    session_id = request.session_id or f"session_{uuid.uuid4()}"
    ...


# BEFORE:
@app.put("/api/v1/sprites/edit")
async def edit_sprite(sprite_id: str, name: str = None, sprite_type: str = None):
    # ❌ No validation of sprite_type

# AFTER:
@app.put("/api/v1/sprites/edit")
async def edit_sprite(request: SpriteEditRequest):  # ✅ Validated
    manager = create_sprite_manager(settings.gbstudio_project_path)
    result = manager.edit_sprite(
        sprite_id=request.sprite_id,
        name=request.name,
        sprite_type=request.sprite_type.value if request.sprite_type else None
    )
    ...
```

---

### FIX 2.3: Code Deduplication

**Files:** Multiple
**Time Estimate:** 2 hours
**Priority:** MEDIUM

#### Extract sprite lookup helper:

**File:** `backend/sprite_manager.py`
```python
def _find_sprite_by_id(self, sprite_id: str) -> Optional[Dict[str, Any]]:
    """
    Find sprite by ID in project.

    Args:
        sprite_id: Sprite ID to find

    Returns:
        Sprite dict or None if not found
    """
    project = self._load_project()
    return next(
        (s for s in project.get('spriteSheets', []) if s.get('id') == sprite_id),
        None
    )

def _find_sprite_index(self, sprite_id: str) -> Tuple[Optional[int], Optional[Dict]]:
    """
    Find sprite index and data.

    Args:
        sprite_id: Sprite ID to find

    Returns:
        Tuple of (index, sprite_dict) or (None, None)
    """
    project = self._load_project()
    for i, sprite in enumerate(project.get('spriteSheets', [])):
        if sprite.get('id') == sprite_id:
            return i, sprite
    return None, None

# Now replace all 5 instances:
def get_sprite(self, sprite_id: str) -> Dict[str, Any]:
    sprite = self._find_sprite_by_id(sprite_id)  # ✅ Use helper
    if not sprite:
        raise ValueError(f"Sprite {sprite_id} not found")
    return sprite

def edit_sprite(self, sprite_id: str, **kwargs) -> Dict[str, Any]:
    index, sprite = self._find_sprite_index(sprite_id)  # ✅ Use helper
    if sprite is None:
        raise ValueError(f"Sprite {sprite_id} not found")
    # ... edit logic
```

#### Extract health check sub-functions:

**File:** `backend/main.py`
```python
async def _check_ollama_health() -> Dict[str, Any]:
    """Check Ollama service health."""
    try:
        start = time.time()
        response = requests.get(
            settings.ollama_tags_url,
            timeout=5
        )
        latency = (time.time() - start) * 1000

        if response.status_code == 200:
            models = response.json().get("models", [])
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "models_loaded": len(models),
                "required_models_ok": all(
                    m in [model["name"] for model in models]
                    for m in [settings.pm_model, settings.embedding_model]
                )
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def _check_comfyui_health() -> Dict[str, Any]:
    """Check ComfyUI service health."""
    try:
        start = time.time()
        response = requests.get(
            f"{settings.comfyui_api_url}/system_stats",
            timeout=5
        )
        latency = (time.time() - start) * 1000

        if response.status_code == 200:
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "stats": response.json()
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@app.get("/health")
async def health_check():
    """Simplified health check using sub-functions."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "ollama": await _check_ollama_health(),
            "comfyui": await _check_comfyui_health(),
            "task_queue": {
                "pending": task_queue.queue.qsize(),
                "running": len(task_queue.running_tasks)
            }
        }
    }
```

---

## 📝 TESTING STRATEGY

### Create Comprehensive Test Files

**1. tests/test_security.py** (2 hours)
```python
"""
Comprehensive security tests.
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestCORS:
    def test_cors_blocks_wildcard(self, client):
        """CORS should not allow all origins."""
        response = client.get(
            '/health',
            headers={'Origin': 'http://malicious-site.com'}
        )
        # Should either block or only allow configured origins
        if 'access-control-allow-origin' in response.headers:
            assert response.headers['access-control-allow-origin'] != '*'


class TestAuthentication:
    def test_admin_endpoints_require_auth(self, client):
        """All admin endpoints should require API key."""
        admin_endpoints = [
            '/api/v1/admin/kb/documents',
            '/api/v1/admin/kb/stats',
        ]

        for endpoint in admin_endpoints:
            response = client.get(endpoint)
            assert response.status_code in [401, 403]  # Unauthorized or Forbidden

    def test_valid_api_key_grants_access(self, client):
        """Valid API key should grant access."""
        response = client.get(
            '/api/v1/admin/kb/documents',
            headers={'X-API-Key': 'valid-test-key'}
        )
        assert response.status_code == 200


class TestPathTraversal:
    def test_path_traversal_blocked(self, client):
        """Path traversal attempts should be blocked."""
        malicious_paths = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32',
            '/etc/hosts'
        ]

        for path in malicious_paths:
            response = client.post(
                '/api/v1/admin/kb/reindex',
                json={'source_file': path},
                headers={'X-API-Key': 'valid-test-key'}
            )
            assert response.status_code in [400, 403]


class TestRateLimiting:
    def test_rate_limit_enforced(self, client):
        """Rate limiting should prevent excessive requests."""
        # Make 20 requests rapidly
        responses = []
        for i in range(20):
            response = client.post(
                '/api/v1/prompt',
                json={'message': f'Test {i}'}
            )
            responses.append(response.status_code)

        # Some should be rate limited (429)
        assert 429 in responses


class TestInputValidation:
    def test_invalid_sprite_type_rejected(self, client):
        """Invalid sprite types should be rejected."""
        response = client.put(
            '/api/v1/sprites/edit',
            json={
                'sprite_id': 'test123',
                'sprite_type': 'invalid_type'  # Not in enum
            }
        )
        assert response.status_code == 422

    def test_oversized_input_rejected(self, client):
        """Oversized inputs should be rejected."""
        response = client.post(
            '/api/v1/prompt',
            json={'message': 'x' * 10000}  # Exceeds max_length
        )
        assert response.status_code == 422


class TestXSSPrevention:
    def test_xss_payload_escaped(self, client):
        """XSS payloads should be escaped in responses."""
        xss_payload = '<script>alert("XSS")</script>'

        response = client.post(
            '/api/v1/prompt',
            json={'message': xss_payload}
        )

        assert response.status_code == 200
        # Response should not contain unescaped script tag
        assert '<script>' not in response.text
```

---

## 🎯 SUMMARY

This action plan provides:

1. **Specific code fixes** for all critical vulnerabilities
2. **Before/After examples** for clarity
3. **Testing strategies** for validation
4. **Time estimates** for planning
5. **Priority ordering** for efficient remediation

**Total Estimated Time:**
- Phase 1 (Critical): 4 hours
- Phase 2 (High Priority): 9 hours
- **Total:** 13 hours for critical and high priority fixes

**Recommended Implementation Order:**
1. Fix CORS (15 min)
2. Add authentication to admin endpoints (1 hour)
3. Fix path traversal (30 min)
4. Add thread synchronization (45 min)
5. Fix XSS vulnerabilities (1.5 hours)
6. Fix silent error handling (4 hours)
7. Add input validation (3 hours)
8. Code deduplication (2 hours)

**Next Steps:**
1. Review this action plan
2. Implement Phase 1 fixes immediately
3. Create feature branch for each fix
4. Write tests before implementing fixes (TDD)
5. Code review each fix
6. Deploy to staging for testing
7. Monitor for regressions

---

**Document Version:** 1.0
**Last Updated:** 2025-11-07
