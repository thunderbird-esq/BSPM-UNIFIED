"""
Session-Based Authentication Tests
Version: 1.0
Platform: Intel Mac (macOS Ventura) + Docker

Tests for session authentication system including:
- Login/logout flow
- Token generation and validation
- Session management
- Password change
- User registration
- CSRF protection
- Account lockout
"""

import pytest
import time
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from backend.main import app, settings
from backend.session_auth import SessionManager
from backend.user_manager import UserManager, PasswordValidator


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def session_manager():
    """Create session manager for testing"""
    return SessionManager(
        secret_key="test-secret-key-for-testing-only",
        algorithm="HS256",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7
    )


@pytest.fixture
def user_manager(tmp_path):
    """Create user manager with temp file"""
    users_file = tmp_path / "test_users.json"
    password_validator = PasswordValidator(
        min_length=8,
        require_uppercase=True,
        require_digit=True
    )
    manager = UserManager(
        users_file=str(users_file),
        password_validator=password_validator
    )

    # Create test user
    manager.create_user(
        username="testuser",
        password="TestPass123",
        role="user"
    )

    # Create admin user
    manager.create_user(
        username="admin",
        password="AdminPass123",
        role="admin"
    )

    return manager


# ============================================================================
# Session Manager Tests
# ============================================================================

def test_create_access_token(session_manager):
    """Test access token creation"""
    token = session_manager.create_access_token(
        user_id="usr_123",
        username="testuser",
        role="user"
    )

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_refresh_token(session_manager):
    """Test refresh token creation"""
    token = session_manager.create_refresh_token(
        user_id="usr_123",
        username="testuser",
        role="user"
    )

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_verify_token_success(session_manager):
    """Test successful token verification"""
    token = session_manager.create_access_token(
        user_id="usr_123",
        username="testuser",
        role="user"
    )

    payload = session_manager.verify_token(token, expected_type="access")

    assert payload.sub == "usr_123"
    assert payload.username == "testuser"
    assert payload.role == "user"
    assert payload.token_type == "access"


def test_verify_token_wrong_type(session_manager):
    """Test token verification with wrong type"""
    access_token = session_manager.create_access_token(
        user_id="usr_123",
        username="testuser",
        role="user"
    )

    # Should fail when expecting refresh token
    with pytest.raises(Exception):
        session_manager.verify_token(access_token, expected_type="refresh")


def test_create_session(session_manager):
    """Test session creation"""
    session_data = session_manager.create_session(
        user_id="usr_123",
        username="testuser",
        role="user"
    )

    assert "access_token" in session_data
    assert "refresh_token" in session_data
    assert "csrf_token" in session_data
    assert session_data["user_id"] == "usr_123"
    assert session_data["username"] == "testuser"
    assert session_data["role"] == "user"


def test_invalidate_session(session_manager):
    """Test session invalidation"""
    session_data = session_manager.create_session(
        user_id="usr_123",
        username="testuser",
        role="user"
    )

    # Session should exist
    assert "usr_123" in session_manager.active_sessions

    # Invalidate session
    session_manager.invalidate_session("usr_123")

    # Session should be removed
    assert "usr_123" not in session_manager.active_sessions

    # Token should be blacklisted
    assert session_data["access_token"] in session_manager.token_blacklist


def test_refresh_session(session_manager):
    """Test session refresh"""
    session_data = session_manager.create_session(
        user_id="usr_123",
        username="testuser",
        role="user"
    )

    refresh_token = session_data["refresh_token"]

    # Refresh session
    new_tokens = session_manager.refresh_session(refresh_token)

    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["access_token"] != session_data["access_token"]
    assert new_tokens["refresh_token"] != session_data["refresh_token"]

    # Old refresh token should be blacklisted
    assert refresh_token in session_manager.token_blacklist


def test_login_attempts_tracking(session_manager):
    """Test login attempt tracking and lockout"""
    username = "testuser"

    # Should allow login initially
    assert session_manager.check_login_attempts(username) is True

    # Record failed attempts
    for i in range(session_manager.max_login_attempts):
        session_manager.record_login_attempt(username, success=False)

    # Should be locked out now
    assert session_manager.check_login_attempts(username) is False


def test_successful_login_clears_attempts(session_manager):
    """Test that successful login clears failed attempts"""
    username = "testuser"

    # Record some failed attempts
    for i in range(5):
        session_manager.record_login_attempt(username, success=False)

    # Verify attempts were recorded
    assert username in session_manager.login_attempts

    # Record successful login
    session_manager.record_login_attempt(username, success=True)

    # Attempts should be cleared
    assert username not in session_manager.login_attempts


# ============================================================================
# User Manager Tests
# ============================================================================

def test_create_user(user_manager):
    """Test user creation"""
    user = user_manager.create_user(
        username="newuser",
        password="NewPass123",
        role="user"
    )

    assert user.username == "newuser"
    assert user.role == "user"
    assert user.user_id.startswith("usr_")
    assert user.verify_password("NewPass123") is True


def test_create_duplicate_user(user_manager):
    """Test creating user with duplicate username"""
    with pytest.raises(ValueError, match="already exists"):
        user_manager.create_user(
            username="testuser",  # Already exists
            password="TestPass123",
            role="user"
        )


def test_weak_password_rejected(user_manager):
    """Test that weak passwords are rejected"""
    # Too short
    with pytest.raises(ValueError, match="at least"):
        user_manager.create_user(
            username="weakuser",
            password="short",
            role="user"
        )

    # No uppercase
    with pytest.raises(ValueError, match="uppercase"):
        user_manager.create_user(
            username="weakuser2",
            password="nouppercas123",
            role="user"
        )

    # No digit
    with pytest.raises(ValueError, match="digit"):
        user_manager.create_user(
            username="weakuser3",
            password="NoDigits",
            role="user"
        )


def test_authenticate_success(user_manager):
    """Test successful authentication"""
    user = user_manager.authenticate(
        username="testuser",
        password="TestPass123"
    )

    assert user is not None
    assert user.username == "testuser"
    assert user.last_login is not None


def test_authenticate_wrong_password(user_manager):
    """Test authentication with wrong password"""
    user = user_manager.authenticate(
        username="testuser",
        password="WrongPassword123"
    )

    assert user is None


def test_authenticate_nonexistent_user(user_manager):
    """Test authentication with non-existent user"""
    user = user_manager.authenticate(
        username="nonexistent",
        password="SomePass123"
    )

    assert user is None


def test_change_password(user_manager):
    """Test password change"""
    user = user_manager.get_user_by_username("testuser")

    # Change password
    result = user_manager.change_password(
        user_id=user.user_id,
        current_password="TestPass123",
        new_password="NewPass456"
    )

    assert result is True

    # Should authenticate with new password
    auth_user = user_manager.authenticate(
        username="testuser",
        password="NewPass456"
    )
    assert auth_user is not None

    # Should not authenticate with old password
    auth_user = user_manager.authenticate(
        username="testuser",
        password="TestPass123"
    )
    assert auth_user is None


# ============================================================================
# API Endpoint Tests
# ============================================================================

def test_login_endpoint_success(client):
    """Test login endpoint with valid credentials"""
    response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "admin123"  # Default password from users.json
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data

    # Check cookies are set
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


def test_login_endpoint_wrong_password(client):
    """Test login endpoint with wrong password"""
    response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401


def test_get_current_user_endpoint(client):
    """Test getting current user info"""
    # First login
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "admin123"
        }
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Get user info
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["username"] == "admin"
    assert data["role"] == "admin"
    assert "user_id" in data


def test_logout_endpoint(client):
    """Test logout endpoint"""
    # First login
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "admin123"
        }
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Logout
    response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert "message" in response.json()


def test_protected_endpoint_without_auth(client):
    """Test accessing protected endpoint without authentication"""
    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_admin_only_endpoint(client):
    """Test admin-only endpoint access control"""
    # Login as admin
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "admin123"
        }
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Should be able to list users (admin only)
    response = client.get(
        "/api/auth/users",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_authentication_flow(client):
    """Test complete authentication flow"""
    # 1. Login
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "admin123"
        }
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    refresh_token = login_response.json()["refresh_token"]

    # 2. Access protected resource
    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_response.status_code == 200

    # 3. Refresh token
    refresh_response = client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {refresh_token}"}
    )
    assert refresh_response.status_code == 200
    new_access_token = refresh_response.json()["access_token"]
    assert new_access_token != access_token

    # 4. Use new access token
    me_response2 = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {new_access_token}"}
    )
    assert me_response2.status_code == 200

    # 5. Logout
    logout_response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {new_access_token}"}
    )
    assert logout_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
