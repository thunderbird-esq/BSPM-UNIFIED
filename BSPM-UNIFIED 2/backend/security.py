"""
Security Module - Authentication, Rate Limiting, Input Sanitization
Version: 3.4
Platform: Intel Mac (macOS Ventura) + Docker

Provides security features for production deployment.
Now includes bcrypt hashing for API keys.
"""

import logging
import hashlib
import secrets
import time
import bcrypt
from typing import Optional, Dict, Tuple
from pathlib import Path
import re
from fastapi import HTTPException, Header, Request
from functools import wraps

logger = logging.getLogger(__name__)


class APIKeyManager:
    """
    Secure API key authentication with bcrypt hashing.

    API keys are stored as bcrypt hashes in /app/secrets/api_key_hashes.txt.
    Each line contains: hash

    Keys should be generated with: secrets.token_urlsafe(32)
    Hashes are created with: bcrypt.hashpw(key.encode(), bcrypt.gensalt())

    SECURITY IMPROVEMENT: Keys are now hashed, not stored in plaintext.
    """

    def __init__(self, keys_file: str = "/app/secrets/api_key_hashes.txt"):
        self.keys_file = Path(keys_file)
        self.valid_key_hashes: set = set()
        self._load_keys()

    def _load_keys(self):
        """Load API key hashes from file."""
        if not self.keys_file.exists():
            logger.warning(
                f"API key hashes file not found: {self.keys_file}. "
                "All API key auth will fail. Run setup.sh to generate keys."
            )
            return

        try:
            with open(self.keys_file, 'r') as f:
                hashes = [line.strip() for line in f if line.strip()]
                self.valid_key_hashes = set(hashes)

            logger.info(
                f"Loaded {len(self.valid_key_hashes)} API key hashes",
                extra={'keys_file': str(self.keys_file)}
            )
        except Exception as e:
            logger.error(
                f"Failed to load API key hashes: {e}",
                exc_info=True
            )

    def validate_key(self, api_key: str) -> bool:
        """
        Validate an API key against stored hashes using bcrypt.

        Args:
            api_key: API key to validate (plaintext)

        Returns:
            True if valid, False otherwise

        Technical Details:
            Uses bcrypt.checkpw() for constant-time comparison.
            This prevents timing attacks while verifying hashes.
        """
        if not api_key or not self.valid_key_hashes:
            return False

        try:
            api_key_bytes = api_key.encode('utf-8')

            # Check against all stored hashes
            for stored_hash in self.valid_key_hashes:
                try:
                    stored_hash_bytes = stored_hash.encode('utf-8')
                    if bcrypt.checkpw(api_key_bytes, stored_hash_bytes):
                        return True
                except (ValueError, TypeError) as e:
                    # Invalid hash format, skip
                    logger.debug(f"Invalid hash format encountered: {e}")
                    continue

            return False

        except Exception as e:
            logger.error(f"Error validating API key: {e}", exc_info=True)
            return False

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new API key (plaintext).

        Returns:
            URL-safe random key (43 characters)
        """
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_key(api_key: str) -> str:
        """
        Hash an API key using bcrypt.

        Args:
            api_key: Plaintext API key

        Returns:
            Bcrypt hash string (suitable for storage)

        Technical Details:
            Uses bcrypt.gensalt() for automatic salt generation.
            Default work factor is 12 (2^12 = 4096 iterations).
        """
        key_bytes = api_key.encode('utf-8')
        hash_bytes = bcrypt.hashpw(key_bytes, bcrypt.gensalt())
        return hash_bytes.decode('utf-8')

    @staticmethod
    def generate_and_hash_key() -> Tuple[str, str]:
        """
        Generate new API key and its hash.

        Returns:
            Tuple of (plaintext_key, bcrypt_hash)

        Usage:
            plaintext, hash_str = APIKeyManager.generate_and_hash_key()
            # Show plaintext to user (ONCE)
            # Store hash_str in api_key_hashes.txt
        """
        key = APIKeyManager.generate_key()
        hash_str = APIKeyManager.hash_key(key)
        return key, hash_str

    def reload_keys(self):
        """
        Reload key hashes from file.

        Useful after adding new keys without restarting the service.
        """
        self._load_keys()
        logger.info("API key hashes reloaded")


class RateLimiter:
    """
    Token bucket rate limiter.

    Tracks requests per bucket (session/IP/API key) and limits to
    max_requests per time_window.
    """

    def __init__(
        self,
        max_requests: int = 10,
        time_window: float = 60.0  # seconds
    ):
        self.max_requests = max_requests
        self.time_window = time_window

        # bucket_id -> (token_count, last_refill_time)
        self.buckets: Dict[str, tuple] = {}

    def is_allowed(self, bucket_id: str) -> bool:
        """
        Check if request is allowed for given bucket_id.

        Args:
            bucket_id: Identifier (session_id, IP address, or API key hash)

        Returns:
            True if request allowed, False if rate limit exceeded
        """
        current_time = time.time()

        # Get or create bucket
        if bucket_id not in self.buckets:
            self.buckets[bucket_id] = (self.max_requests - 1, current_time)
            return True

        tokens, last_refill = self.buckets[bucket_id]

        # Refill tokens based on elapsed time
        elapsed = current_time - last_refill
        refill_amount = (elapsed / self.time_window) * self.max_requests
        tokens = min(self.max_requests, tokens + refill_amount)

        # Check if request allowed
        if tokens >= 1:
            self.buckets[bucket_id] = (tokens - 1, current_time)
            return True
        else:
            self.buckets[bucket_id] = (tokens, current_time)
            logger.warning(
                f"Rate limit exceeded for {bucket_id}",
                extra={
                    'bucket_id': bucket_id,
                    'max_requests': self.max_requests,
                    'time_window': self.time_window
                }
            )
            return False

    def get_remaining(self, bucket_id: str) -> int:
        """Get remaining requests for bucket_id."""
        if bucket_id not in self.buckets:
            return self.max_requests

        tokens, last_refill = self.buckets[bucket_id]
        current_time = time.time()
        elapsed = current_time - last_refill
        refill_amount = (elapsed / self.time_window) * self.max_requests
        tokens = min(self.max_requests, tokens + refill_amount)

        return int(tokens)

    def reset_bucket(self, bucket_id: str):
        """Reset rate limit for specific bucket (admin function)."""
        if bucket_id in self.buckets:
            del self.buckets[bucket_id]
            logger.info(f"Rate limit reset for {bucket_id}")


# ============================================================================
# Global Instances
# ============================================================================

api_key_manager = APIKeyManager()
rate_limiter = RateLimiter(
    max_requests=int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "10")),
    time_window=60.0
)


# ============================================================================
# FastAPI Dependencies
# ============================================================================

async def check_rate_limit(request: Request, x_api_key: Optional[str] = Header(None)):
    """
    Check rate limit for incoming request.

    Uses API key hash as bucket ID if present (more secure),
    otherwise falls back to IP address.

    Args:
        request: FastAPI Request object
        x_api_key: Optional API key from X-API-Key header

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    import os

    # Determine bucket ID
    if x_api_key and os.getenv("ENVIRONMENT") == "production":
        # Use hash of API key as bucket ID for security
        bucket_id = hashlib.sha256(x_api_key.encode()).hexdigest()[:16]
    else:
        # Use IP address (development mode or no API key)
        bucket_id = request.client.host

    if not rate_limiter.is_allowed(bucket_id):
        remaining = rate_limiter.get_remaining(bucket_id)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. {remaining} requests remaining in window.",
            headers={"X-RateLimit-Remaining": str(remaining)}
        )


async def verify_api_key(x_api_key: str = Header(..., description="API key for authentication")):
    """
    Verify API key for protected endpoints.

    Args:
        x_api_key: API key from X-API-Key header

    Raises:
        HTTPException: 401 if API key invalid or missing

    Usage:
        @router.post("/protected")
        async def endpoint(_api_key = Depends(verify_api_key)):
            ...
    """
    import os

    # Skip in development mode
    if os.getenv("ENVIRONMENT") != "production":
        return

    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide via X-API-Key header."
        )

    if not api_key_manager.validate_key(x_api_key):
        logger.warning(f"Invalid API key attempt from {x_api_key[:8]}...")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )


# ============================================================================
# Input Sanitization
# ============================================================================

def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent injection attacks.

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text

    Security Measures:
        - Strips control characters (except newline/tab)
        - Limits length to prevent DoS
        - Removes null bytes
    """
    # Remove control characters except newline and tab
    sanitized = ''.join(char for char in text if ord(char) >= 32 or char in ['\n', '\t'])

    # Remove null bytes
    sanitized = sanitized.replace('\x00', '')

    # Truncate to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
        logger.warning(f"Input truncated from {len(text)} to {max_length} characters")

    return sanitized.strip()


def validate_session_id(session_id: str) -> bool:
    """
    Validate session ID format.

    Args:
        session_id: Session identifier to validate

    Returns:
        True if valid format

    Security: Prevents path traversal via session IDs in filenames
    """
    # Allow only alphanumeric, hyphens, and underscores
    pattern = r'^[a-zA-Z0-9_-]{1,64}$'
    return bool(re.match(pattern, session_id))


import os
