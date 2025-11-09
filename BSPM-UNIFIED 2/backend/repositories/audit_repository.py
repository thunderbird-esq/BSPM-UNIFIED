"""
Audit Repository - Operations for AuditLog model
"""

from typing import List, Optional
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from backend.models import AuditLog

logger = structlog.get_logger(__name__)


class AuditRepository:
    """Repository for AuditLog operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        action: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        success: Optional[bool] = None,
        error_message: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> AuditLog:
        """Create audit log entry"""
        log = AuditLog(
            id=str(uuid4()),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            success=success,
            error_message=error_message,
            details=details or {},
            timestamp=datetime.utcnow(),
        )

        self.session.add(log)
        await self.session.flush()

        return log

    async def get_by_id(self, log_id: str) -> Optional[AuditLog]:
        """Get audit log by ID"""
        result = await self.session.execute(
            select(AuditLog).where(AuditLog.id == log_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[AuditLog]:
        """List audit logs by user"""
        query = select(AuditLog).where(AuditLog.user_id == user_id)

        if start_date:
            query = query.where(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.where(AuditLog.timestamp <= end_date)

        query = query.limit(limit).offset(offset).order_by(AuditLog.timestamp.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_by_action(
        self,
        action: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """List audit logs by action"""
        query = (
            select(AuditLog)
            .where(AuditLog.action == action)
            .limit(limit)
            .offset(offset)
            .order_by(AuditLog.timestamp.desc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """List audit logs by resource"""
        query = (
            select(AuditLog)
            .where(AuditLog.resource_type == resource_type)
            .where(AuditLog.resource_id == resource_id)
            .limit(limit)
            .offset(offset)
            .order_by(AuditLog.timestamp.desc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def cleanup_old_logs(self, days: int = 90) -> int:
        """
        Delete audit logs older than specified days

        Args:
            days: Number of days to keep logs

        Returns:
            int: Number of logs deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = await self.session.execute(
            delete(AuditLog).where(AuditLog.timestamp < cutoff_date)
        )
        await self.session.flush()

        deleted = result.rowcount
        if deleted > 0:
            logger.info("audit_logs.cleaned_up", count=deleted, days=days)

        return deleted

    async def count_by_user(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Count audit logs by user"""
        query = select(func.count(AuditLog.id)).where(AuditLog.user_id == user_id)

        if start_date:
            query = query.where(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.where(AuditLog.timestamp <= end_date)

        result = await self.session.execute(query)
        return result.scalar() or 0
