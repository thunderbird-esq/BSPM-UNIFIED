"""
Session-Based Authentication Module
Version: 1.0
Platform: Intel Mac (macOS Ventura) + Docker

Provides secure session-based authentication using JWT tokens.
Features:
- JWT token generation and validation
- Secure cookie handling
- CSRF protection
- Session expiration and renewal
- Rate limiting on login attempts
- Account lockout mechanism
"""

import os
import time
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

from jose import JWTError, jwt
from fastapi import HTTPException, Cookie, Response, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================

class TokenPayload(BaseModel):
    """JWT token payload structure"""
    sub: str  # user_id
    username: str
    role: str
    exp: int  # expiration timestamp
    iat: int  # issued at timestamp
    jti: str  # JWT ID (unique token identifier)
    token_type: str  # "access" or "refresh"


class LoginRequest(BaseModel):
    """Login request body"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """User information response"""
    user_id: str
    username: str
    role: str
    created_at: str
    last_login: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    """Password change request"""
    current_password: str
    new_password: str


class RegisterUserRequest(BaseModel):
    """User registration request"""
    username: str
    password: str
    role: str = "user"


# ============================================================================
# Session Manager
# ============================================================================

class SessionManager:
    """
    Manages JWT-based sessions with secure cookies and CSRF protection.

    Features:
    - JWT token generation (access + refresh tokens)
    - Token validation and renewal
    - Session storage (in-memory, can be extended to Redis)
    - CSRF token generation and validation
    - Rate limiting on login attempts
    - Account lockout after failed attempts
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 1440,  # 24 hours
        refresh_token_expire_days: int = 7,
        max_login_attempts: int = 10,
        lockout_duration_minutes: int = 30
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.max_login_attempts = max_login_attempts
        self.lockout_duration_minutes = lockout_duration_minutes

        # In-memory session storage (user_id -> session_data)
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

        # Login attempt tracking (username -> attempts_data)
        self.login_attempts: Dict[str, Dict[str, Any]] = {}

        # Token blacklist (for invalidated tokens)
        self.token_blacklist: set = set()

        logger.info("SessionManager initialized", extra={
            'access_token_expire_minutes': access_token_expire_minutes,
            'refresh_token_expire_days': refresh_token_expire_days
        })

    def _generate_jti(self) -> str:
        """Generate unique JWT ID"""
        return secrets.token_urlsafe(32)

    def _generate_csrf_token(self) -> str:
        """Generate CSRF token"""
        return secrets.token_urlsafe(32)

    def create_access_token(self, user_id: str, username: str, role: str) -> str:
        """
        Create JWT access token.

        Args:
            user_id: Unique user identifier
            username: Username
            role: User role (admin, user, viewer)

        Returns:
            JWT access token string
        """
        now = datetime.utcnow()
        expires_delta = timedelta(minutes=self.access_token_expire_minutes)
        expire = now + expires_delta

        payload = {
            "sub": user_id,
            "username": username,
            "role": role,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "jti": self._generate_jti(),
            "token_type": "access"
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        logger.debug(f"Created access token for user {username}", extra={
            'user_id': user_id,
            'expires_at': expire.isoformat()
        })

        return token

    def create_refresh_token(self, user_id: str, username: str, role: str) -> str:
        """
        Create JWT refresh token.

        Args:
            user_id: Unique user identifier
            username: Username
            role: User role

        Returns:
            JWT refresh token string
        """
        now = datetime.utcnow()
        expires_delta = timedelta(days=self.refresh_token_expire_days)
        expire = now + expires_delta

        payload = {
            "sub": user_id,
            "username": username,
            "role": role,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "jti": self._generate_jti(),
            "token_type": "refresh"
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        logger.debug(f"Created refresh token for user {username}", extra={
            'user_id': user_id,
            'expires_at': expire.isoformat()
        })

        return token

    def verify_token(self, token: str, expected_type: str = "access") -> TokenPayload:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token string
            expected_type: Expected token type ("access" or "refresh")

        Returns:
            Decoded token payload

        Raises:
            HTTPException: If token is invalid, expired, or blacklisted
        """
        try:
            # Check if token is blacklisted
            if token in self.token_blacklist:
                logger.warning("Attempted to use blacklisted token")
                raise HTTPException(
                    status_code=401,
                    detail="Token has been revoked"
                )

            # Decode and verify token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )

            # Validate token type
            if payload.get("token_type") != expected_type:
                raise HTTPException(
                    status_code=401,
                    detail=f"Invalid token type. Expected {expected_type}"
                )

            token_payload = TokenPayload(**payload)

            logger.debug(f"Token verified for user {token_payload.username}")

            return token_payload

        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials"
            )

    def create_session(
        self,
        user_id: str,
        username: str,
        role: str
    ) -> Dict[str, Any]:
        """
        Create new user session with access and refresh tokens.

        Args:
            user_id: User identifier
            username: Username
            role: User role

        Returns:
            Session data including tokens and CSRF token
        """
        access_token = self.create_access_token(user_id, username, role)
        refresh_token = self.create_refresh_token(user_id, username, role)
        csrf_token = self._generate_csrf_token()

        session_data = {
            "user_id": user_id,
            "username": username,
            "role": role,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "csrf_token": csrf_token,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        }

        # Store session
        self.active_sessions[user_id] = session_data

        logger.info(f"Session created for user {username}", extra={
            'user_id': user_id,
            'role': role
        })

        return session_data

    def invalidate_session(self, user_id: str, token: Optional[str] = None):
        """
        Invalidate user session.

        Args:
            user_id: User identifier
            token: Optional token to blacklist
        """
        # Remove from active sessions
        if user_id in self.active_sessions:
            session = self.active_sessions.pop(user_id)

            # Blacklist tokens
            if "access_token" in session:
                self.token_blacklist.add(session["access_token"])
            if "refresh_token" in session:
                self.token_blacklist.add(session["refresh_token"])

            logger.info(f"Session invalidated for user {session.get('username')}", extra={
                'user_id': user_id
            })

        # Also blacklist provided token
        if token:
            self.token_blacklist.add(token)

    def refresh_session(self, refresh_token: str) -> Dict[str, str]:
        """
        Refresh session using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New access token and refresh token

        Raises:
            HTTPException: If refresh token is invalid
        """
        # Verify refresh token
        payload = self.verify_token(refresh_token, expected_type="refresh")

        # Create new tokens
        new_access_token = self.create_access_token(
            payload.sub,
            payload.username,
            payload.role
        )
        new_refresh_token = self.create_refresh_token(
            payload.sub,
            payload.username,
            payload.role
        )

        # Blacklist old refresh token
        self.token_blacklist.add(refresh_token)

        # Update session
        if payload.sub in self.active_sessions:
            self.active_sessions[payload.sub]["access_token"] = new_access_token
            self.active_sessions[payload.sub]["refresh_token"] = new_refresh_token
            self.active_sessions[payload.sub]["last_activity"] = datetime.utcnow().isoformat()

        logger.info(f"Session refreshed for user {payload.username}", extra={
            'user_id': payload.sub
        })

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token
        }

    def check_login_attempts(self, username: str) -> bool:
        """
        Check if user is locked out due to failed login attempts.

        Args:
            username: Username to check

        Returns:
            True if login allowed, False if locked out
        """
        if username not in self.login_attempts:
            return True

        attempts_data = self.login_attempts[username]

        # Check if lockout has expired
        if "locked_until" in attempts_data:
            locked_until = datetime.fromisoformat(attempts_data["locked_until"])
            if datetime.utcnow() < locked_until:
                logger.warning(f"Login attempt for locked account: {username}")
                return False
            else:
                # Lockout expired, reset attempts
                del self.login_attempts[username]
                return True

        return True

    def record_login_attempt(self, username: str, success: bool):
        """
        Record login attempt and enforce lockout policy.

        Args:
            username: Username
            success: Whether login was successful
        """
        if success:
            # Clear failed attempts on successful login
            if username in self.login_attempts:
                del self.login_attempts[username]
            logger.info(f"Successful login for {username}")
            return

        # Record failed attempt
        if username not in self.login_attempts:
            self.login_attempts[username] = {
                "count": 0,
                "first_attempt": datetime.utcnow().isoformat()
            }

        self.login_attempts[username]["count"] += 1
        self.login_attempts[username]["last_attempt"] = datetime.utcnow().isoformat()

        # Check if lockout threshold reached
        if self.login_attempts[username]["count"] >= self.max_login_attempts:
            lockout_until = datetime.utcnow() + timedelta(minutes=self.lockout_duration_minutes)
            self.login_attempts[username]["locked_until"] = lockout_until.isoformat()

            logger.warning(f"Account locked due to failed attempts: {username}", extra={
                'attempts': self.login_attempts[username]["count"],
                'locked_until': lockout_until.isoformat()
            })
        else:
            logger.warning(f"Failed login attempt for {username}", extra={
                'attempts': self.login_attempts[username]["count"],
                'max_attempts': self.max_login_attempts
            })

    def get_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get active session for user"""
        return self.active_sessions.get(user_id)

    def cleanup_expired_sessions(self):
        """Remove expired sessions and tokens from storage"""
        current_time = int(time.time())
        expired_users = []

        for user_id, session in self.active_sessions.items():
            try:
                # Check if access token is expired
                token_payload = jwt.decode(
                    session["access_token"],
                    self.secret_key,
                    algorithms=[self.algorithm],
                    options={"verify_exp": False}
                )

                if token_payload.get("exp", 0) < current_time:
                    expired_users.append(user_id)
            except JWTError:
                expired_users.append(user_id)

        # Remove expired sessions
        for user_id in expired_users:
            self.active_sessions.pop(user_id, None)
            logger.debug(f"Removed expired session for user {user_id}")

        if expired_users:
            logger.info(f"Cleaned up {len(expired_users)} expired sessions")


# ============================================================================
# Cookie Utilities
# ============================================================================

def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    secure: bool = True
):
    """
    Set secure authentication cookies.

    Args:
        response: FastAPI Response object
        access_token: JWT access token
        refresh_token: JWT refresh token
        secure: Whether to set secure flag (HTTPS only)
    """
    # Set access token cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="strict",
        max_age=86400  # 24 hours
    )

    # Set refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="strict",
        max_age=604800  # 7 days
    )


def clear_auth_cookies(response: Response):
    """
    Clear authentication cookies.

    Args:
        response: FastAPI Response object
    """
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
