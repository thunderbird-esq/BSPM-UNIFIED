"""
Test Suite: Security Module
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Tests for API key authentication, rate limiting, and input sanitization.
"""

import pytest
import time
from pathlib import Path
from backend.security import (
    APIKeyManager, RateLimiter, InputSanitizer,
    verify_api_key, check_rate_limit,
    require_api_key_for_production
)
from fastapi import HTTPException, Request
from unittest.mock import Mock, patch


class TestAPIKeyManager:
    """Test API key management."""

    def test_load_keys_from_file(self, mock_api_key_file):
        """Successfully load API keys from file."""
        manager = APIKeyManager(keys_file=str(mock_api_key_file))

        assert len(manager.valid_keys) == 2
        assert "test_key_123456789abcdef" in manager.valid_keys
        assert "another_valid_key_xyz" in manager.valid_keys

    def test_missing_keys_file(self, temp_dir):
        """Handle missing API keys file gracefully."""
        manager = APIKeyManager(keys_file=str(temp_dir / "nonexistent.txt"))

        assert len(manager.valid_keys) == 0

    def test_validate_valid_key(self, mock_api_key_file):
        """Valid API key passes validation."""
        manager = APIKeyManager(keys_file=str(mock_api_key_file))

        assert manager.validate_key("test_key_123456789abcdef") is True

    def test_validate_invalid_key(self, mock_api_key_file):
        """Invalid API key fails validation."""
        manager = APIKeyManager(keys_file=str(mock_api_key_file))

        assert manager.validate_key("invalid_key") is False

    def test_validate_empty_key(self, mock_api_key_file):
        """Empty key fails validation."""
        manager = APIKeyManager(keys_file=str(mock_api_key_file))

        assert manager.validate_key("") is False
        assert manager.validate_key(None) is False

    def test_constant_time_comparison(self, mock_api_key_file):
        """Use constant-time comparison to prevent timing attacks."""
        manager = APIKeyManager(keys_file=str(mock_api_key_file))

        # Both should take similar time
        start1 = time.time()
        manager.validate_key("a")
        time1 = time.time() - start1

        start2 = time.time()
        manager.validate_key("a" * 100)
        time2 = time.time() - start2

        # Time difference should be minimal (not proportional to string length)
        # This is a rough test - timing attacks are hard to test precisely
        assert abs(time1 - time2) < 0.01

    def test_generate_key(self):
        """Generate new API key."""
        key = APIKeyManager.generate_key()

        assert isinstance(key, str)
        assert len(key) > 20  # Should be reasonably long
        assert key.isalnum() or '-' in key or '_' in key  # URL-safe characters


class TestRateLimiter:
    """Test rate limiting functionality."""

    def test_first_request_allowed(self):
        """First request is always allowed."""
        limiter = RateLimiter(max_requests=10, time_window=60)

        assert limiter.is_allowed("user_1") is True

    def test_within_limit_allowed(self):
        """Requests within limit are allowed."""
        limiter = RateLimiter(max_requests=5, time_window=60)

        # Make 5 requests
        for i in range(5):
            assert limiter.is_allowed("user_1") is True

    def test_exceed_limit_denied(self):
        """Requests exceeding limit are denied."""
        limiter = RateLimiter(max_requests=3, time_window=60)

        # First 3 allowed
        for i in range(3):
            assert limiter.is_allowed("user_1") is True

        # 4th denied
        assert limiter.is_allowed("user_1") is False

    def test_different_buckets_independent(self):
        """Different bucket IDs have independent limits."""
        limiter = RateLimiter(max_requests=2, time_window=60)

        # User 1: 2 requests
        assert limiter.is_allowed("user_1") is True
        assert limiter.is_allowed("user_1") is True

        # User 2: Still has full quota
        assert limiter.is_allowed("user_2") is True
        assert limiter.is_allowed("user_2") is True

    def test_token_refill_over_time(self):
        """Tokens refill over time."""
        limiter = RateLimiter(max_requests=2, time_window=2.0)  # 2 seconds

        # Use both tokens
        assert limiter.is_allowed("user_1") is True
        assert limiter.is_allowed("user_1") is True

        # No tokens left
        assert limiter.is_allowed("user_1") is False

        # Wait for refill (half the time window = 1 token)
        time.sleep(1.1)

        # Should have ~1 token now
        assert limiter.is_allowed("user_1") is True

    def test_get_remaining_tokens(self):
        """Get remaining requests for bucket."""
        limiter = RateLimiter(max_requests=5, time_window=60)

        # New bucket has full quota
        assert limiter.get_remaining("new_user") == 5

        # After 2 requests
        limiter.is_allowed("user_1")
        limiter.is_allowed("user_1")

        remaining = limiter.get_remaining("user_1")
        assert 2 <= remaining <= 3  # Should be ~3

    def test_cleanup_old_buckets(self):
        """Old buckets are cleaned up."""
        limiter = RateLimiter(max_requests=10, time_window=60)

        # Create some buckets
        limiter.is_allowed("user_1")
        limiter.is_allowed("user_2")

        # Manually age one bucket
        limiter.buckets["user_1"] = (5, time.time() - 7200)  # 2 hours ago

        # Cleanup buckets older than 1 hour
        limiter.cleanup_old_buckets(max_age=3600)

        assert "user_1" not in limiter.buckets
        assert "user_2" in limiter.buckets


class TestInputSanitizer:
    """Test input sanitization."""

    def test_sanitize_filename_basic(self):
        """Sanitize basic filename."""
        result = InputSanitizer.sanitize_filename("my_sprite_01.png")

        assert result == "my_sprite_01.png"

    def test_sanitize_filename_path_traversal(self):
        """Remove path traversal attempts."""
        result = InputSanitizer.sanitize_filename("../../../etc/passwd")

        assert ".." not in result
        assert "/" not in result
        assert result == "etcpasswd"

    def test_sanitize_filename_special_chars(self):
        """Remove special characters."""
        result = InputSanitizer.sanitize_filename("sprite@#$%^&*.png")

        assert result == "sprite______.png"

    def test_sanitize_filename_lowercase(self):
        """Convert to lowercase."""
        result = InputSanitizer.sanitize_filename("MySprite.PNG")

        assert result == "mysprite.png"

    def test_sanitize_filename_empty_raises(self):
        """Empty filename raises ValueError."""
        with pytest.raises(ValueError, match="empty or invalid"):
            InputSanitizer.sanitize_filename("")

    def test_sanitize_filename_dot_only_raises(self):
        """Filename with only dots raises ValueError."""
        with pytest.raises(ValueError, match="empty or invalid"):
            InputSanitizer.sanitize_filename("..")

    def test_sanitize_session_id_valid(self):
        """Sanitize valid session ID."""
        result = InputSanitizer.sanitize_session_id("session_123_abc")

        assert result == "session_123_abc"

    def test_sanitize_session_id_special_chars(self):
        """Remove special characters from session ID."""
        result = InputSanitizer.sanitize_session_id("session@#$%123")

        assert result == "session123"

    def test_sanitize_session_id_max_length(self):
        """Enforce max length on session ID."""
        long_id = "a" * 100
        result = InputSanitizer.sanitize_session_id(long_id)

        assert len(result) == 64

    def test_sanitize_session_id_empty_raises(self):
        """Empty session ID raises ValueError."""
        with pytest.raises(ValueError, match="empty or invalid"):
            InputSanitizer.sanitize_session_id("")

    def test_sanitize_prompt_basic(self):
        """Sanitize basic prompt."""
        result = InputSanitizer.sanitize_prompt("  Create a knight sprite  ")

        assert result == "Create a knight sprite"

    def test_sanitize_prompt_null_bytes(self):
        """Remove null bytes from prompt."""
        result = InputSanitizer.sanitize_prompt("prompt\x00with\x00nulls")

        assert "\x00" not in result
        assert result == "promptwithnulls"

    def test_sanitize_prompt_max_length(self):
        """Trim prompt to max length."""
        long_prompt = "a" * 15000
        result = InputSanitizer.sanitize_prompt(long_prompt, max_length=10000)

        assert len(result) == 10000


class TestFastAPIIntegration:
    """Test FastAPI dependency functions."""

    @pytest.mark.asyncio
    async def test_verify_api_key_valid(self, mock_api_key_file):
        """Valid API key passes verification."""
        with patch('backend.security.api_key_manager') as mock_manager:
            mock_manager.validate_key.return_value = True

            result = await verify_api_key(x_api_key="valid_key")

            assert result == "valid_key"

    @pytest.mark.asyncio
    async def test_verify_api_key_missing(self):
        """Missing API key raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(x_api_key=None)

        assert exc_info.value.status_code == 401
        assert "required" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_verify_api_key_invalid(self, mock_api_key_file):
        """Invalid API key raises 403."""
        with patch('backend.security.api_key_manager') as mock_manager:
            mock_manager.validate_key.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(x_api_key="invalid_key")

            assert exc_info.value.status_code == 403
            assert "invalid" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self):
        """Request within rate limit is allowed."""
        with patch('backend.security.rate_limiter') as mock_limiter:
            mock_limiter.is_allowed.return_value = True

            mock_request = Mock()
            mock_request.client.host = "127.0.0.1"

            # Should not raise
            await check_rate_limit(mock_request, session_id="test_session")

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self):
        """Request exceeding rate limit raises 429."""
        with patch('backend.security.rate_limiter') as mock_limiter:
            mock_limiter.is_allowed.return_value = False
            mock_limiter.get_remaining.return_value = 0
            mock_limiter.max_requests = 10
            mock_limiter.time_window = 60

            mock_request = Mock()
            mock_request.client.host = "127.0.0.1"

            with pytest.raises(HTTPException) as exc_info:
                await check_rate_limit(mock_request, session_id="test_session")

            assert exc_info.value.status_code == 429
            assert "rate limit" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_check_rate_limit_uses_session_id(self):
        """Rate limit uses session ID if provided."""
        with patch('backend.security.rate_limiter') as mock_limiter:
            mock_limiter.is_allowed.return_value = True

            mock_request = Mock()
            mock_request.client.host = "127.0.0.1"

            await check_rate_limit(mock_request, session_id="my_session")

            # Should use session_id as bucket
            mock_limiter.is_allowed.assert_called_once_with("my_session")

    @pytest.mark.asyncio
    async def test_check_rate_limit_uses_ip(self):
        """Rate limit uses IP if no session ID."""
        with patch('backend.security.rate_limiter') as mock_limiter:
            mock_limiter.is_allowed.return_value = True

            mock_request = Mock()
            mock_request.client.host = "192.168.1.100"

            await check_rate_limit(mock_request, session_id=None)

            # Should use IP as bucket
            mock_limiter.is_allowed.assert_called_once_with("192.168.1.100")


class TestProductionMode:
    """Test production mode detection."""

    def test_production_mode_enabled(self):
        """Detect production mode from environment."""
        with patch.dict('os.environ', {'ENVIRONMENT': 'production'}):
            assert require_api_key_for_production() is True

    def test_production_mode_disabled(self):
        """Development mode doesn't require API keys."""
        with patch.dict('os.environ', {'ENVIRONMENT': 'development'}):
            assert require_api_key_for_production() is False

    def test_production_mode_default(self):
        """Default to development mode if not specified."""
        with patch.dict('os.environ', {}, clear=True):
            assert require_api_key_for_production() is False


# Run with: pytest tests/test_security.py -v
# Run with coverage: pytest tests/test_security.py --cov=backend.security --cov-report=html
