"""
Authentication Middleware
Version: 1.0
Platform: Intel Mac (macOS Ventura) + Docker

Provides unified authentication middleware supporting both:
1. Session-based authentication (JWT tokens) - Primary method
2. API key authentication - Backward compatibility (deprecated)

Features:
- Dual authentication method support
- Token extraction from headers and cookies
- User context injection
- Role-based access control decorators
- Audit logging for authentication events
"""

import logging
from typing import Optional, Callable
from datetime import datetime
from functools import wraps

from fastapi import HTTPException, Header, Cookie, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.session_auth import SessionManager, TokenPayload
from backend.user_manager import UserManager, User
from backend.security import api_key_manager

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme for OpenAPI docs
bearer_scheme = HTTPBearer(auto_error=False)


# ============================================================================
# Authentication Context
# ============================================================================

class AuthContext:
    """
    Authentication context containing user information and auth method.
    """

    def __init__(
        self,
        user: User,
        auth_method: str,
        token_payload: Optional[TokenPayload] = None
    ):
        self.user = user
        self.auth_method = auth_method  # "session" or "api_key"
        self.token_payload = token_payload
        self.authenticated_at = datetime.utcnow()

    @property
    def user_id(self) -> str:
        return self.user.user_id

    @property
    def username(self) -> str:
        return self.user.username

    @property
    def role(self) -> str:
        return self.user.role

    def is_admin(self) -> bool:
        """Check if user has admin role"""
        return self.role == "admin"

    def has_role(self, role: str) -> bool:
        """Check if user has specific role"""
        return self.role == role

    def to_dict(self):
        """Convert to dictionary for logging"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role,
            "auth_method": self.auth_method,
            "authenticated_at": self.authenticated_at.isoformat()
        }


# ============================================================================
# Authentication Dependencies
# ============================================================================

async def get_current_user(
    request: Request,
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    access_token_cookie: Optional[str] = Cookie(None, alias="access_token"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    session_manager: SessionManager = None,
    user_manager: UserManager = None
) -> AuthContext:
    """
    Universal authentication dependency supporting both session and API key auth.

    Priority order:
    1. Session token (Bearer token in Authorization header)
    2. Session token (Cookie)
    3. API key (X-API-Key header) - deprecated, logs warning

    Args:
        request: FastAPI request
        authorization: Bearer token from Authorization header
        access_token_cookie: Access token from cookie
        x_api_key: API key from header
        session_manager: Session manager instance
        user_manager: User manager instance

    Returns:
        AuthContext with user information

    Raises:
        HTTPException: If authentication fails
    """
    # Get managers from app state if not provided
    if session_manager is None:
        session_manager = request.app.state.session_manager
    if user_manager is None:
        user_manager = request.app.state.user_manager

    # Try session authentication first (Bearer token)
    if authorization and authorization.credentials:
        try:
            token_payload = session_manager.verify_token(
                authorization.credentials,
                expected_type="access"
            )

            user = user_manager.get_user(token_payload.sub)
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="User not found"
                )

            if not user.is_active:
                raise HTTPException(
                    status_code=401,
                    detail="User account is inactive"
                )

            logger.debug(f"Authenticated via session token: {user.username}", extra={
                'user_id': user.user_id,
                'auth_method': 'session'
            })

            return AuthContext(
                user=user,
                auth_method="session",
                token_payload=token_payload
            )

        except HTTPException as e:
            # Re-raise HTTP exceptions
            raise e
        except Exception as e:
            logger.warning(f"Session token validation failed: {e}")
            # Continue to try other methods

    # Try session authentication (Cookie)
    if access_token_cookie:
        try:
            token_payload = session_manager.verify_token(
                access_token_cookie,
                expected_type="access"
            )

            user = user_manager.get_user(token_payload.sub)
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="User not found"
                )

            if not user.is_active:
                raise HTTPException(
                    status_code=401,
                    detail="User account is inactive"
                )

            logger.debug(f"Authenticated via session cookie: {user.username}", extra={
                'user_id': user.user_id,
                'auth_method': 'session_cookie'
            })

            return AuthContext(
                user=user,
                auth_method="session",
                token_payload=token_payload
            )

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.warning(f"Session cookie validation failed: {e}")
            # Continue to try API key

    # Fall back to API key authentication (deprecated)
    if x_api_key:
        if api_key_manager.validate_key(x_api_key):
            logger.warning(
                "API key authentication used (DEPRECATED). Please migrate to session-based auth.",
                extra={
                    'api_key_prefix': x_api_key[:8] if x_api_key else None,
                    'endpoint': request.url.path
                }
            )

            # Create a synthetic admin user for API key auth
            # In production, you might want to map API keys to specific users
            synthetic_user = User(
                user_id="api_key_user",
                username="api_key_user",
                hashed_password="",  # Not used for API key auth
                role="admin",  # API keys have admin privileges
                created_at=datetime.utcnow().isoformat()
            )

            return AuthContext(
                user=synthetic_user,
                auth_method="api_key"
            )

        else:
            logger.warning(
                "Invalid API key attempt",
                extra={
                    'api_key_prefix': x_api_key[:8] if x_api_key else None,
                    'endpoint': request.url.path
                }
            )
            raise HTTPException(
                status_code=403,
                detail="Invalid API key"
            )

    # No valid authentication provided
    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide Bearer token, session cookie, or API key."
    )


async def get_current_active_user(
    auth_context: AuthContext = Depends(get_current_user)
) -> AuthContext:
    """
    Dependency that ensures user is active.

    Args:
        auth_context: Authentication context

    Returns:
        AuthContext if user is active

    Raises:
        HTTPException: If user is inactive
    """
    if not auth_context.user.is_active:
        raise HTTPException(
            status_code=401,
            detail="User account is inactive"
        )

    return auth_context


async def get_current_admin_user(
    auth_context: AuthContext = Depends(get_current_active_user)
) -> AuthContext:
    """
    Dependency that ensures user has admin role.

    Args:
        auth_context: Authentication context

    Returns:
        AuthContext if user is admin

    Raises:
        HTTPException: If user is not admin
    """
    if not auth_context.is_admin():
        logger.warning(
            f"Unauthorized admin access attempt by {auth_context.username}",
            extra={
                'user_id': auth_context.user_id,
                'role': auth_context.role
            }
        )
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )

    return auth_context


# ============================================================================
# Optional Authentication
# ============================================================================

async def get_optional_user(
    request: Request,
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    access_token_cookie: Optional[str] = Cookie(None, alias="access_token"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Optional[AuthContext]:
    """
    Optional authentication dependency that returns None if not authenticated.

    Useful for endpoints that have different behavior for authenticated vs
    anonymous users.

    Args:
        request: FastAPI request
        authorization: Bearer token
        access_token_cookie: Session cookie
        x_api_key: API key

    Returns:
        AuthContext if authenticated, None otherwise
    """
    try:
        return await get_current_user(
            request,
            authorization,
            access_token_cookie,
            x_api_key
        )
    except HTTPException:
        return None


# ============================================================================
# Role-Based Access Control Decorators
# ============================================================================

def require_role(required_role: str):
    """
    Decorator to require specific role for endpoint.

    Usage:
        @app.get("/admin/users")
        @require_role("admin")
        async def list_users(auth: AuthContext = Depends(get_current_user)):
            ...

    Args:
        required_role: Required role (admin, user, viewer)

    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, auth_context: AuthContext = None, **kwargs):
            if not auth_context:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )

            if not auth_context.has_role(required_role):
                logger.warning(
                    f"Unauthorized access attempt",
                    extra={
                        'user_id': auth_context.user_id,
                        'required_role': required_role,
                        'user_role': auth_context.role
                    }
                )
                raise HTTPException(
                    status_code=403,
                    detail=f"Role '{required_role}' required"
                )

            return await func(*args, auth_context=auth_context, **kwargs)

        return wrapper
    return decorator


def require_any_role(*roles: str):
    """
    Decorator to require any of the specified roles.

    Usage:
        @app.get("/content/edit")
        @require_any_role("admin", "user")
        async def edit_content(auth: AuthContext = Depends(get_current_user)):
            ...

    Args:
        *roles: Allowed roles

    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, auth_context: AuthContext = None, **kwargs):
            if not auth_context:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )

            if not any(auth_context.has_role(role) for role in roles):
                logger.warning(
                    f"Unauthorized access attempt",
                    extra={
                        'user_id': auth_context.user_id,
                        'allowed_roles': list(roles),
                        'user_role': auth_context.role
                    }
                )
                raise HTTPException(
                    status_code=403,
                    detail=f"One of these roles required: {', '.join(roles)}"
                )

            return await func(*args, auth_context=auth_context, **kwargs)

        return wrapper
    return decorator


# ============================================================================
# Audit Logging
# ============================================================================

class AuditLogger:
    """
    Logs authentication events for security auditing.
    """

    @staticmethod
    def log_login(username: str, success: bool, ip_address: str, auth_method: str):
        """Log login attempt"""
        if success:
            logger.info(
                f"Successful login: {username}",
                extra={
                    'event': 'login_success',
                    'username': username,
                    'ip_address': ip_address,
                    'auth_method': auth_method
                }
            )
        else:
            logger.warning(
                f"Failed login: {username}",
                extra={
                    'event': 'login_failed',
                    'username': username,
                    'ip_address': ip_address,
                    'auth_method': auth_method
                }
            )

    @staticmethod
    def log_logout(user_id: str, username: str):
        """Log logout"""
        logger.info(
            f"User logout: {username}",
            extra={
                'event': 'logout',
                'user_id': user_id,
                'username': username
            }
        )

    @staticmethod
    def log_password_change(user_id: str, username: str, changed_by: str):
        """Log password change"""
        logger.info(
            f"Password changed: {username}",
            extra={
                'event': 'password_change',
                'user_id': user_id,
                'username': username,
                'changed_by': changed_by
            }
        )

    @staticmethod
    def log_account_lockout(username: str, attempts: int):
        """Log account lockout"""
        logger.warning(
            f"Account locked: {username}",
            extra={
                'event': 'account_lockout',
                'username': username,
                'failed_attempts': attempts
            }
        )

    @staticmethod
    def log_token_refresh(user_id: str, username: str):
        """Log token refresh"""
        logger.info(
            f"Token refreshed: {username}",
            extra={
                'event': 'token_refresh',
                'user_id': user_id,
                'username': username
            }
        )

    @staticmethod
    def log_unauthorized_access(user_id: str, username: str, endpoint: str, required_role: str):
        """Log unauthorized access attempt"""
        logger.warning(
            f"Unauthorized access: {username} -> {endpoint}",
            extra={
                'event': 'unauthorized_access',
                'user_id': user_id,
                'username': username,
                'endpoint': endpoint,
                'required_role': required_role
            }
        )


# Create global audit logger instance
audit_logger = AuditLogger()
