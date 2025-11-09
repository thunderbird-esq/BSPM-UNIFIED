"""
Sprite Repository - CRUD operations for Sprite model
"""

from typing import List, Optional
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from backend.models import Sprite

logger = structlog.get_logger(__name__)


class SpriteRepository:
    """Repository for Sprite operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
        description: str,
        file_path: str,
        **kwargs,
    ) -> Sprite:
        """Create new sprite"""
        sprite = Sprite(
            sprite_id=str(uuid4()),
            user_id=user_id,
            description=description,
            file_path=file_path,
            created_at=datetime.utcnow(),
            **kwargs,
        )

        self.session.add(sprite)
        await self.session.flush()

        logger.info("sprite.created", sprite_id=sprite.sprite_id, user_id=user_id)
        return sprite

    async def get_by_id(self, sprite_id: str) -> Optional[Sprite]:
        """Get sprite by ID"""
        result = await self.session.execute(
            select(Sprite).where(Sprite.sprite_id == sprite_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        category: Optional[str] = None,
    ) -> List[Sprite]:
        """List sprites by user"""
        query = select(Sprite).where(Sprite.user_id == user_id)

        if category:
            query = query.where(Sprite.category == category)

        query = query.limit(limit).offset(offset).order_by(Sprite.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def search(
        self,
        user_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Sprite]:
        """Search sprites with filters"""
        query = select(Sprite)

        if user_id:
            query = query.where(Sprite.user_id == user_id)

        if category:
            query = query.where(Sprite.category == category)

        # Note: For tags filtering with JSON arrays, you'd need database-specific syntax
        # This is a placeholder for PostgreSQL JSONB contains
        # if tags:
        #     query = query.where(Sprite.tags.contains(tags))

        query = query.limit(limit).offset(offset).order_by(Sprite.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, sprite_id: str, **kwargs) -> Optional[Sprite]:
        """Update sprite"""
        kwargs.pop("sprite_id", None)
        kwargs.pop("created_at", None)
        kwargs["updated_at"] = datetime.utcnow()

        await self.session.execute(
            update(Sprite).where(Sprite.sprite_id == sprite_id).values(**kwargs)
        )
        await self.session.flush()

        logger.info("sprite.updated", sprite_id=sprite_id)
        return await self.get_by_id(sprite_id)

    async def delete(self, sprite_id: str) -> bool:
        """Delete sprite"""
        result = await self.session.execute(
            delete(Sprite).where(Sprite.sprite_id == sprite_id)
        )
        await self.session.flush()

        deleted = result.rowcount > 0
        if deleted:
            logger.info("sprite.deleted", sprite_id=sprite_id)

        return deleted

    async def count_by_user(self, user_id: str) -> int:
        """Count sprites by user"""
        result = await self.session.execute(
            select(func.count(Sprite.sprite_id)).where(Sprite.user_id == user_id)
        )
        return result.scalar() or 0
