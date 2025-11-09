"""
User Repository - CRUD operations for User model
"""

from typing import List, Optional
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
import structlog

from backend.models import User, UserRole

logger = structlog.get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRepository:
    """Repository for User operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ========================================================================
    # Create
    # ========================================================================

    async def create(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        role: UserRole = UserRole.USER,
        full_name: Optional[str] = None,
    ) -> User:
        """
        Create new user

        Args:
            username: Username (unique)
            password: Plain text password (will be hashed)
            email: Email address (optional)
            role: User role
            full_name: Full name (optional)

        Returns:
            User: Created user
        """
        hashed_password = pwd_context.hash(password)

        user = User(
            id=str(uuid4()),
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=role,
            full_name=full_name,
            is_active=True,
            created_at=datetime.utcnow(),
        )

        self.session.add(user)
        await self.session.flush()

        logger.info("user.created", user_id=user.id, username=username)
        return user

    # ========================================================================
    # Read
    # ========================================================================

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        return user

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        return user

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        return user

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        active_only: bool = False,
    ) -> List[User]:
        """
        List all users

        Args:
            limit: Max number of users to return
            offset: Offset for pagination
            active_only: Only return active users

        Returns:
            List[User]: List of users
        """
        query = select(User)

        if active_only:
            query = query.where(User.is_active == True)

        query = query.limit(limit).offset(offset).order_by(User.created_at.desc())

        result = await self.session.execute(query)
        users = result.scalars().all()
        return list(users)

    async def count(self, active_only: bool = False) -> int:
        """Count total users"""
        from sqlalchemy import func

        query = select(func.count(User.id))

        if active_only:
            query = query.where(User.is_active == True)

        result = await self.session.execute(query)
        count = result.scalar()
        return count or 0

    # ========================================================================
    # Update
    # ========================================================================

    async def update(
        self,
        user_id: str,
        **kwargs,
    ) -> Optional[User]:
        """
        Update user

        Args:
            user_id: User ID
            **kwargs: Fields to update

        Returns:
            User: Updated user or None if not found
        """
        # Remove fields that shouldn't be updated directly
        kwargs.pop("id", None)
        kwargs.pop("created_at", None)
        kwargs["updated_at"] = datetime.utcnow()

        # Hash password if provided
        if "password" in kwargs:
            kwargs["hashed_password"] = pwd_context.hash(kwargs.pop("password"))

        await self.session.execute(
            update(User).where(User.id == user_id).values(**kwargs)
        )
        await self.session.flush()

        logger.info("user.updated", user_id=user_id, fields=list(kwargs.keys()))
        return await self.get_by_id(user_id)

    async def update_last_login(self, user_id: str) -> bool:
        """Update last login timestamp"""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.utcnow())
        )
        await self.session.flush()
        return True

    async def deactivate(self, user_id: str) -> bool:
        """Deactivate user account"""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_active=False, updated_at=datetime.utcnow())
        )
        await self.session.flush()

        logger.info("user.deactivated", user_id=user_id)
        return True

    async def activate(self, user_id: str) -> bool:
        """Activate user account"""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_active=True, updated_at=datetime.utcnow())
        )
        await self.session.flush()

        logger.info("user.activated", user_id=user_id)
        return True

    # ========================================================================
    # Delete
    # ========================================================================

    async def delete(self, user_id: str) -> bool:
        """
        Delete user (hard delete)

        Args:
            user_id: User ID

        Returns:
            bool: True if deleted
        """
        result = await self.session.execute(
            delete(User).where(User.id == user_id)
        )
        await self.session.flush()

        deleted = result.rowcount > 0
        if deleted:
            logger.info("user.deleted", user_id=user_id)

        return deleted

    # ========================================================================
    # Authentication
    # ========================================================================

    async def verify_password(self, user_id: str, password: str) -> bool:
        """Verify user password"""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        return pwd_context.verify(password, user.hashed_password)

    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate user

        Args:
            username: Username
            password: Plain text password

        Returns:
            User: User if authenticated, None otherwise
        """
        user = await self.get_by_username(username)
        if not user:
            # Prevent timing attacks
            pwd_context.hash(password)
            return None

        if not user.is_active:
            return None

        if not pwd_context.verify(password, user.hashed_password):
            return None

        # Update last login
        await self.update_last_login(user.id)

        logger.info("user.authenticated", user_id=user.id, username=username)
        return user
