"""
User Management Module
Version: 1.0
Platform: Intel Mac (macOS Ventura) + Docker

Provides user account management with password hashing and role-based access.
Features:
- User registration and authentication
- Password hashing with bcrypt
- Role-based access control (admin, user, viewer)
- Password validation and complexity requirements
- User storage in JSON file (Redis migration ready)
- Password reset functionality
"""

import os
import json
import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from uuid import uuid4

from passlib.context import CryptContext
from fastapi import HTTPException

logger = logging.getLogger(__name__)


# ============================================================================
# Password Hashing
# ============================================================================

# Password context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================================
# Password Validation
# ============================================================================

class PasswordValidator:
    """
    Validates password complexity requirements.
    """

    def __init__(
        self,
        min_length: int = 8,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = False
    ):
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digit = require_digit
        self.require_special = require_special

    def validate(self, password: str) -> tuple[bool, List[str]]:
        """
        Validate password against complexity requirements.

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check length
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long")

        # Check uppercase
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")

        # Check lowercase
        if self.require_lowercase and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")

        # Check digit
        if self.require_digit and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")

        # Check special character
        if self.require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")

        return len(errors) == 0, errors


# ============================================================================
# User Model
# ============================================================================

class User:
    """User account model"""

    def __init__(
        self,
        user_id: str,
        username: str,
        hashed_password: str,
        role: str = "user",
        created_at: Optional[str] = None,
        last_login: Optional[str] = None,
        is_active: bool = True
    ):
        self.user_id = user_id
        self.username = username
        self.hashed_password = hashed_password
        self.role = role
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.last_login = last_login
        self.is_active = is_active

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "hashed_password": self.hashed_password,
            "role": self.role,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "is_active": self.is_active
        }

    def to_response(self) -> Dict[str, Any]:
        """Convert user to response format (without password)"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "is_active": self.is_active
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'User':
        """Create user from dictionary"""
        return User(**data)

    def verify_password(self, password: str) -> bool:
        """Verify password"""
        return verify_password(password, self.hashed_password)

    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow().isoformat()


# ============================================================================
# User Manager
# ============================================================================

class UserManager:
    """
    Manages user accounts and authentication.

    Stores users in JSON file for simplicity. Can be extended to use Redis
    or a proper database for production deployments.
    """

    VALID_ROLES = ["admin", "user", "viewer"]

    def __init__(
        self,
        users_file: str = "/app/secrets/users.json",
        password_validator: Optional[PasswordValidator] = None
    ):
        self.users_file = Path(users_file)
        self.password_validator = password_validator or PasswordValidator()
        self.users: Dict[str, User] = {}

        # Ensure secrets directory exists
        self.users_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing users
        self._load_users()

        logger.info(f"UserManager initialized with {len(self.users)} users", extra={
            'users_file': str(self.users_file)
        })

    def _load_users(self):
        """Load users from JSON file"""
        if not self.users_file.exists():
            logger.info("Users file does not exist, will be created on first user registration")
            self._save_users()  # Create empty file
            return

        try:
            with open(self.users_file, 'r') as f:
                data = json.load(f)

            users_list = data.get("users", [])
            self.users = {
                user_data["user_id"]: User.from_dict(user_data)
                for user_data in users_list
            }

            logger.info(f"Loaded {len(self.users)} users from {self.users_file}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse users file: {e}", exc_info=True)
            self.users = {}
        except Exception as e:
            logger.error(f"Failed to load users: {e}", exc_info=True)
            self.users = {}

    def _save_users(self):
        """Save users to JSON file"""
        try:
            data = {
                "users": [user.to_dict() for user in self.users.values()],
                "last_updated": datetime.utcnow().isoformat()
            }

            # Write to temp file first, then rename (atomic operation)
            temp_file = self.users_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)

            temp_file.rename(self.users_file)

            logger.debug(f"Saved {len(self.users)} users to {self.users_file}")

        except Exception as e:
            logger.error(f"Failed to save users: {e}", exc_info=True)
            raise

    def create_user(
        self,
        username: str,
        password: str,
        role: str = "user",
        created_by: Optional[str] = None
    ) -> User:
        """
        Create new user account.

        Args:
            username: Unique username
            password: Plain text password
            role: User role (admin, user, viewer)
            created_by: User ID of admin creating this user (for audit)

        Returns:
            Created User object

        Raises:
            ValueError: If username exists or validation fails
            HTTPException: If user creation fails
        """
        # Validate username
        if self.get_user_by_username(username):
            raise ValueError(f"Username '{username}' already exists")

        # Validate username format
        if not re.match(r'^[a-zA-Z0-9_-]{3,32}$', username):
            raise ValueError(
                "Username must be 3-32 characters and contain only "
                "letters, numbers, underscores, and hyphens"
            )

        # Validate password
        is_valid, errors = self.password_validator.validate(password)
        if not is_valid:
            raise ValueError("; ".join(errors))

        # Validate role
        if role not in self.VALID_ROLES:
            raise ValueError(f"Invalid role. Must be one of: {', '.join(self.VALID_ROLES)}")

        # Create user
        user = User(
            user_id=f"usr_{uuid4().hex[:16]}",
            username=username,
            hashed_password=hash_password(password),
            role=role,
            created_at=datetime.utcnow().isoformat()
        )

        # Store user
        self.users[user.user_id] = user
        self._save_users()

        logger.info(f"User created: {username}", extra={
            'user_id': user.user_id,
            'role': role,
            'created_by': created_by or 'system'
        })

        return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate user with username and password.

        Args:
            username: Username
            password: Plain text password

        Returns:
            User object if authentication successful, None otherwise
        """
        user = self.get_user_by_username(username)

        if not user:
            logger.warning(f"Authentication failed: user not found", extra={
                'username': username
            })
            return None

        if not user.is_active:
            logger.warning(f"Authentication failed: user inactive", extra={
                'username': username
            })
            return None

        if not user.verify_password(password):
            logger.warning(f"Authentication failed: invalid password", extra={
                'username': username
            })
            return None

        # Update last login
        user.update_last_login()
        self._save_users()

        logger.info(f"User authenticated: {username}", extra={
            'user_id': user.user_id
        })

        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        for user in self.users.values():
            if user.username.lower() == username.lower():
                return user
        return None

    def list_users(self) -> List[User]:
        """List all users"""
        return list(self.users.values())

    def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Change user password.

        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password

        Returns:
            True if password changed successfully

        Raises:
            ValueError: If validation fails
            HTTPException: If user not found or current password incorrect
        """
        user = self.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify current password
        if not user.verify_password(current_password):
            raise HTTPException(status_code=401, detail="Current password is incorrect")

        # Validate new password
        is_valid, errors = self.password_validator.validate(new_password)
        if not is_valid:
            raise ValueError("; ".join(errors))

        # Update password
        user.hashed_password = hash_password(new_password)
        self._save_users()

        logger.info(f"Password changed for user {user.username}", extra={
            'user_id': user_id
        })

        return True

    def reset_password(
        self,
        user_id: str,
        new_password: str,
        admin_user_id: str
    ) -> bool:
        """
        Reset user password (admin only).

        Args:
            user_id: User ID to reset
            new_password: New password
            admin_user_id: Admin user performing the reset

        Returns:
            True if password reset successfully

        Raises:
            ValueError: If validation fails
            HTTPException: If user not found
        """
        user = self.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Validate new password
        is_valid, errors = self.password_validator.validate(new_password)
        if not is_valid:
            raise ValueError("; ".join(errors))

        # Update password
        user.hashed_password = hash_password(new_password)
        self._save_users()

        logger.info(f"Password reset for user {user.username}", extra={
            'user_id': user_id,
            'admin_user_id': admin_user_id
        })

        return True

    def deactivate_user(self, user_id: str, admin_user_id: str) -> bool:
        """
        Deactivate user account (admin only).

        Args:
            user_id: User ID to deactivate
            admin_user_id: Admin user performing the action

        Returns:
            True if user deactivated successfully
        """
        user = self.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.is_active = False
        self._save_users()

        logger.info(f"User deactivated: {user.username}", extra={
            'user_id': user_id,
            'admin_user_id': admin_user_id
        })

        return True

    def activate_user(self, user_id: str, admin_user_id: str) -> bool:
        """
        Activate user account (admin only).

        Args:
            user_id: User ID to activate
            admin_user_id: Admin user performing the action

        Returns:
            True if user activated successfully
        """
        user = self.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.is_active = True
        self._save_users()

        logger.info(f"User activated: {user.username}", extra={
            'user_id': user_id,
            'admin_user_id': admin_user_id
        })

        return True

    def update_role(self, user_id: str, new_role: str, admin_user_id: str) -> bool:
        """
        Update user role (admin only).

        Args:
            user_id: User ID
            new_role: New role
            admin_user_id: Admin user performing the action

        Returns:
            True if role updated successfully

        Raises:
            ValueError: If role is invalid
        """
        if new_role not in self.VALID_ROLES:
            raise ValueError(f"Invalid role. Must be one of: {', '.join(self.VALID_ROLES)}")

        user = self.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        old_role = user.role
        user.role = new_role
        self._save_users()

        logger.info(f"User role updated: {user.username}", extra={
            'user_id': user_id,
            'old_role': old_role,
            'new_role': new_role,
            'admin_user_id': admin_user_id
        })

        return True

    def delete_user(self, user_id: str, admin_user_id: str) -> bool:
        """
        Delete user account (admin only).

        Args:
            user_id: User ID to delete
            admin_user_id: Admin user performing the action

        Returns:
            True if user deleted successfully
        """
        user = self.users.pop(user_id, None)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        self._save_users()

        logger.info(f"User deleted: {user.username}", extra={
            'user_id': user_id,
            'admin_user_id': admin_user_id
        })

        return True
