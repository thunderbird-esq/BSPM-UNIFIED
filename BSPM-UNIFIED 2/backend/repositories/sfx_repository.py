"""
SFX Repository - CRUD operations for SoundEffect model
"""

from typing import List, Optional
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from backend.models import SoundEffect

logger = structlog.get_logger(__name__)


class SFXRepository:
    """Repository for SoundEffect operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
        description: str,
        file_path: str,
        **kwargs,
    ) -> SoundEffect:
        """Create new sound effect"""
        sfx = SoundEffect(
            sfx_id=str(uuid4()),
            user_id=user_id,
            description=description,
            file_path=file_path,
            created_at=datetime.utcnow(),
            **kwargs,
        )

        self.session.add(sfx)
        await self.session.flush()

        logger.info("sfx.created", sfx_id=sfx.sfx_id, user_id=user_id)
        return sfx

    async def get_by_id(self, sfx_id: str) -> Optional[SoundEffect]:
        """Get sound effect by ID"""
        result = await self.session.execute(
            select(SoundEffect).where(SoundEffect.sfx_id == sfx_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        category: Optional[str] = None,
    ) -> List[SoundEffect]:
        """List sound effects by user"""
        query = select(SoundEffect).where(SoundEffect.user_id == user_id)

        if category:
            query = query.where(SoundEffect.category == category)

        query = query.limit(limit).offset(offset).order_by(SoundEffect.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, sfx_id: str, **kwargs) -> Optional[SoundEffect]:
        """Update sound effect"""
        kwargs.pop("sfx_id", None)
        kwargs.pop("created_at", None)
        kwargs["updated_at"] = datetime.utcnow()

        await self.session.execute(
            update(SoundEffect).where(SoundEffect.sfx_id == sfx_id).values(**kwargs)
        )
        await self.session.flush()

        logger.info("sfx.updated", sfx_id=sfx_id)
        return await self.get_by_id(sfx_id)

    async def delete(self, sfx_id: str) -> bool:
        """Delete sound effect"""
        result = await self.session.execute(
            delete(SoundEffect).where(SoundEffect.sfx_id == sfx_id)
        )
        await self.session.flush()

        deleted = result.rowcount > 0
        if deleted:
            logger.info("sfx.deleted", sfx_id=sfx_id)

        return deleted

    async def count_by_user(self, user_id: str) -> int:
        """Count sound effects by user"""
        result = await self.session.execute(
            select(func.count(SoundEffect.sfx_id)).where(SoundEffect.user_id == user_id)
        )
        return result.scalar() or 0
