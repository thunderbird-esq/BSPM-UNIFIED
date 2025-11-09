"""
Script Repository - CRUD operations for Script model
"""

from typing import List, Optional
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from backend.models import Script

logger = structlog.get_logger(__name__)


class ScriptRepository:
    """Repository for Script operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
        name: str,
        events: dict,
        **kwargs,
    ) -> Script:
        """Create new script"""
        script = Script(
            script_id=str(uuid4()),
            user_id=user_id,
            name=name,
            events=events,
            created_at=datetime.utcnow(),
            **kwargs,
        )

        self.session.add(script)
        await self.session.flush()

        logger.info("script.created", script_id=script.script_id, user_id=user_id)
        return script

    async def get_by_id(self, script_id: str) -> Optional[Script]:
        """Get script by ID"""
        result = await self.session.execute(
            select(Script).where(Script.script_id == script_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        script_type: Optional[str] = None,
    ) -> List[Script]:
        """List scripts by user"""
        query = select(Script).where(Script.user_id == user_id)

        if script_type:
            query = query.where(Script.script_type == script_type)

        query = query.limit(limit).offset(offset).order_by(Script.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, script_id: str, **kwargs) -> Optional[Script]:
        """Update script"""
        kwargs.pop("script_id", None)
        kwargs.pop("created_at", None)
        kwargs["updated_at"] = datetime.utcnow()

        await self.session.execute(
            update(Script).where(Script.script_id == script_id).values(**kwargs)
        )
        await self.session.flush()

        logger.info("script.updated", script_id=script_id)
        return await self.get_by_id(script_id)

    async def delete(self, script_id: str) -> bool:
        """Delete script"""
        result = await self.session.execute(
            delete(Script).where(Script.script_id == script_id)
        )
        await self.session.flush()

        deleted = result.rowcount > 0
        if deleted:
            logger.info("script.deleted", script_id=script_id)

        return deleted

    async def count_by_user(self, user_id: str) -> int:
        """Count scripts by user"""
        result = await self.session.execute(
            select(func.count(Script.script_id)).where(Script.user_id == user_id)
        )
        return result.scalar() or 0
