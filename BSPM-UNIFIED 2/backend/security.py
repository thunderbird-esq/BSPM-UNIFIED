"""
Security Module - Authentication, Rate Limiting, Input Sanitization
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Provides security features for production deployment.
"""

import logging
import hashlib
import secrets
import time
from typing import Optional, Dict
from pathlib import Path
import re
from fastapi import HTTPException, Header, Request
from functools import wraps

logger = logging.getLogger(__name__)


class APIKeyManager:
    """
    Simple API key authentication.
    
    API keys stored in ./app/secrets/api_keys.txt (one per line).
    Keys should be generated with: secrets.token_urlsafe(32)
    """

    def __init__(self, keys_file: str = None):
        if keys_file is None:
            import os
            keys_file = os.getenv("API_KEYS_FILE", "./app/secrets/api_keys.txt")
        self.keys_file = Path(keys_file)
        self.valid_keys: set = set()
        self._load_keys()
    
    def _load_keys(self):
        """Load API keys from file."""
        if not self.keys_file.exists():
            logger.warning(
                f"API keys file not found: {self.keys_file}. "
                "All API key auth will fail."
            )
            return
        
        try:
            with open(self.keys_file, 'r') as f:
                keys = [line.strip() for line in f if line.strip()]
                self.valid_keys = set(keys)
            
            logger.info(
                f"Loaded {len(self.valid_keys)} API keys",
                extra={'keys_file': str(self.keys_file)}
            )
        except Exception as e:
            logger.error(
                f"Failed to load API keys: {e}",
                exc_info=True
            )
    
    def validate_key(self, api_key: str) -> bool:
        """
        Validate an API key.
        
        Args:
            api_key: API key to validate
        
        Returns:
            True if valid, False otherwise
        """
        # Constant-time comparison to prevent timing attacks
        if not api_key or not self.valid_keys:
            return False
        
        return any(
            secrets.compare_digest(api_key, valid_key)
            for valid_key in self.valid_keys
        )
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new API key."""
        return secrets.token_urlsafe(32)


class RateLimiter:
    """
    Token bucket rate limiter.
    
    Tracks requests per session/IP and limits to max_requests per time_window.
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
            bucket_id: Identifier (session_id or IP address)
        
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
    
    def cleanup_old_buckets(self, max_age: float = 3600):
        """Remove buckets that haven't been used in max_age seconds."""
        current_time = time.time()
        to_remove = [
            bucket_id
            for bucket_id, (_, last_refill) in self.buckets.items()
            if current_time - last_refill > max_age
        ]
        
        for bucket_id in to_remove:
            del self.buckets[bucket_id]
        
        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} old rate limit buckets")


class InputSanitizer:
    """
    Sanitize user inputs to prevent injection attacks.
    """
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path traversal.
        
        Rules:
        - Remove directory separators (/, \)
        - Remove parent directory references (..)
        - Allow only alphanumeric, underscore, dash, period
        - Convert to lowercase
        
        Args:
            filename: Unsanitized filename
        
        Returns:
            Sanitized filename
        
        Raises:
            ValueError: If filename is empty or invalid after sanitization
        """
        # Remove directory separators and parent references
        filename = filename.replace('/', '_').replace('\\', '_')
        filename = filename.replace('..', '')
        
        # Allow only safe characters
        filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)
        
        # Convert to lowercase
        filename = filename.lower()
        
        # Ensure not empty
        if not filename or filename == '.':
            raise ValueError("Filename is empty or invalid after sanitization")
        
        # Ensure doesn't start with dot (hidden file)
        if filename.startswith('.'):
            filename = filename[1:]
        
        if not filename:
            raise ValueError("Filename is empty or invalid after sanitization")
        
        logger.debug(f"Sanitized filename: {filename}")
        return filename
    
    @staticmethod
    def sanitize_session_id(session_id: str) -> str:
        """
        Sanitize session ID.
        
        Rules:
        - Allow only alphanumeric, underscore, dash
        - Max length: 64 characters
        
        Args:
            session_id: Unsanitized session ID
        
        Returns:
            Sanitized session ID
        
        Raises:
            ValueError: If session ID is invalid
        """
        # Allow only safe characters
        session_id = re.sub(r'[^a-zA-Z0-9_\-]', '', session_id)
        
        # Enforce max length
        if len(session_id) > 64:
            session_id = session_id[:64]
        
        if not session_id:
            raise ValueError("Session ID is empty or invalid")
        
        return session_id
    
    @staticmethod
    def sanitize_prompt(prompt: str, max_length: int = 10000) -> str:
        """
        Sanitize user prompt.
        
        Rules:
        - Trim to max_length
        - Remove null bytes
        - Strip leading/trailing whitespace
        
        Args:
            prompt: User prompt
            max_length: Maximum allowed length
        
        Returns:
            Sanitized prompt
        """
        # Remove null bytes
        prompt = prompt.replace('\x00', '')
        
        # Trim to max length
        if len(prompt) > max_length:
            prompt = prompt[:max_length]
        
        # Strip whitespace
        prompt = prompt.strip()
        
        return prompt


# Global instances
api_key_manager = APIKeyManager()
rate_limiter = RateLimiter(max_requests=10, time_window=60.0)


# Dependency functions for FastAPI

async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    FastAPI dependency for API key authentication.
    
    Usage:
        @app.post("/api/v1/execute", dependencies=[Depends(verify_api_key)])
        async def execute_plan(plan: dict):
            # This endpoint requires valid API key
            pass
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide X-API-Key header."
        )
    
    if not api_key_manager.validate_key(x_api_key):
        logger.warning(
            "Invalid API key attempt",
            extra={'provided_key_prefix': x_api_key[:8] if x_api_key else None}
        )
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    
    return x_api_key


async def check_rate_limit(request: Request, session_id: Optional[str] = None):
    """
    FastAPI dependency for rate limiting.
    
    Usage:
        @app.post("/api/v1/prompt")
        async def prompt(
            request: PromptRequest,
            _rate_limit = Depends(check_rate_limit)
        ):
            # This endpoint is rate limited
            pass
    """
    # Use session_id if provided, otherwise use client IP
    bucket_id = session_id if session_id else request.client.host
    
    if not rate_limiter.is_allowed(bucket_id):
        remaining = rate_limiter.get_remaining(bucket_id)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again later.",
            headers={
                "X-RateLimit-Limit": str(rate_limiter.max_requests),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(time.time() + rate_limiter.time_window))
            }
        )


def require_api_key_for_production():
    """
    Check if API key authentication should be enforced.
    
    Returns:
        True if running in production mode
    """
    import os
    return os.getenv('ENVIRONMENT', 'development').lower() == 'production'
