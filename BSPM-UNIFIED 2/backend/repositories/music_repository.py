"""
Music Repository - CRUD operations for MusicTrack model
"""

from typing import List, Optional
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from backend.models import MusicTrack

logger = structlog.get_logger(__name__)


class MusicRepository:
    """Repository for MusicTrack operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
        description: str,
        file_path: str,
        **kwargs,
    ) -> MusicTrack:
        """Create new music track"""
        track = MusicTrack(
            track_id=str(uuid4()),
            user_id=user_id,
            description=description,
            file_path=file_path,
            created_at=datetime.utcnow(),
            **kwargs,
        )

        self.session.add(track)
        await self.session.flush()

        logger.info("music.created", track_id=track.track_id, user_id=user_id)
        return track

    async def get_by_id(self, track_id: str) -> Optional[MusicTrack]:
        """Get music track by ID"""
        result = await self.session.execute(
            select(MusicTrack).where(MusicTrack.track_id == track_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        category: Optional[str] = None,
    ) -> List[MusicTrack]:
        """List music tracks by user"""
        query = select(MusicTrack).where(MusicTrack.user_id == user_id)

        if category:
            query = query.where(MusicTrack.category == category)

        query = query.limit(limit).offset(offset).order_by(MusicTrack.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, track_id: str, **kwargs) -> Optional[MusicTrack]:
        """Update music track"""
        kwargs.pop("track_id", None)
        kwargs.pop("created_at", None)
        kwargs["updated_at"] = datetime.utcnow()

        await self.session.execute(
            update(MusicTrack).where(MusicTrack.track_id == track_id).values(**kwargs)
        )
        await self.session.flush()

        logger.info("music.updated", track_id=track_id)
        return await self.get_by_id(track_id)

    async def delete(self, track_id: str) -> bool:
        """Delete music track"""
        result = await self.session.execute(
            delete(MusicTrack).where(MusicTrack.track_id == track_id)
        )
        await self.session.flush()

        deleted = result.rowcount > 0
        if deleted:
            logger.info("music.deleted", track_id=track_id)

        return deleted

    async def count_by_user(self, user_id: str) -> int:
        """Count music tracks by user"""
        result = await self.session.execute(
            select(func.count(MusicTrack.track_id)).where(MusicTrack.user_id == user_id)
        )
        return result.scalar() or 0
