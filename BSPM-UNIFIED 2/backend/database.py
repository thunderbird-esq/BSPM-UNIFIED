"""
GBStudio Automation Hub - Database Management
PostgreSQL with SQLAlchemy Async Support

Features:
- Async database engine with connection pooling
- Session management with dependency injection
- Migration support via Alembic
- Health checks and monitoring
- Connection retry logic
"""

import os
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
from datetime import datetime

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, QueuePool
import structlog

# Base class for all models
Base = declarative_base()

# Logger
logger = structlog.get_logger(__name__)


class DatabaseManager:
    """Manages database connections and sessions"""

    def __init__(
        self,
        database_url: str,
        pool_size: int = 20,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        echo: bool = False,
    ):
        """
        Initialize database manager

        Args:
            database_url: PostgreSQL connection string (postgresql+asyncpg://...)
            pool_size: Number of connections to maintain in pool
            max_overflow: Max connections beyond pool_size
            pool_timeout: Seconds to wait for connection from pool
            pool_recycle: Seconds before recycling connections
            echo: Enable SQL query logging
        """
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo = echo

        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None

    def create_engine(self) -> AsyncEngine:
        """Create async database engine with connection pooling"""
        if self._engine:
            return self._engine

        # Determine if we should use connection pooling
        use_pooling = self.pool_size > 0

        if use_pooling:
            poolclass = QueuePool
            pool_kwargs = {
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "pool_timeout": self.pool_timeout,
                "pool_recycle": self.pool_recycle,
                "pool_pre_ping": True,  # Verify connections before use
            }
        else:
            poolclass = NullPool
            pool_kwargs = {}

        self._engine = create_async_engine(
            self.database_url,
            echo=self.echo,
            poolclass=poolclass,
            **pool_kwargs,
            # JSON serializer for JSONB columns
            json_serializer=lambda obj: obj,
            json_deserializer=lambda obj: obj,
        )

        # Log pool events
        if use_pooling:
            @event.listens_for(self._engine.sync_engine, "connect")
            def receive_connect(dbapi_conn, connection_record):
                logger.debug("database.connection.created")

            @event.listens_for(self._engine.sync_engine, "close")
            def receive_close(dbapi_conn, connection_record):
                logger.debug("database.connection.closed")

        logger.info(
            "database.engine.created",
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            use_pooling=use_pooling,
        )

        return self._engine

    def create_session_factory(self) -> async_sessionmaker:
        """Create session factory for database sessions"""
        if not self._engine:
            self.create_engine()

        if not self._session_factory:
            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )

            logger.info("database.session_factory.created")

        return self._session_factory

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session (context manager)

        Usage:
            async with db_manager.session() as session:
                result = await session.execute(query)
        """
        if not self._session_factory:
            self.create_session_factory()

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error("database.session.error", error=str(e))
                raise
            finally:
                await session.close()

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session (dependency injection)

        Usage with FastAPI:
            @app.get("/items")
            async def get_items(session: AsyncSession = Depends(db_manager.get_session)):
                result = await session.execute(query)
        """
        if not self._session_factory:
            self.create_session_factory()

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error("database.session.error", error=str(e))
                raise
            finally:
                await session.close()

    async def health_check(self) -> dict:
        """
        Check database health

        Returns:
            dict: Health status including connection info and pool stats
        """
        try:
            start_time = datetime.now()

            async with self.session() as session:
                # Simple query to test connection
                result = await session.execute(text("SELECT 1"))
                result.scalar()

            duration = (datetime.now() - start_time).total_seconds()

            # Get pool statistics
            pool_stats = {}
            if self._engine and isinstance(self._engine.pool, QueuePool):
                pool = self._engine.pool
                pool_stats = {
                    "pool_size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "total_connections": pool.size() + pool.overflow(),
                }

            return {
                "status": "healthy",
                "database": "postgresql",
                "response_time_seconds": duration,
                "pool_stats": pool_stats,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error("database.health_check.failed", error=str(e))
            return {
                "status": "unhealthy",
                "database": "postgresql",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def initialize_database(self):
        """Create all tables (for development/testing only)"""
        if not self._engine:
            self.create_engine()

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("database.tables.created")

    async def drop_all_tables(self):
        """Drop all tables (for development/testing only)"""
        if not self._engine:
            self.create_engine()

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        logger.warning("database.tables.dropped")

    async def close(self):
        """Close database engine and connections"""
        if self._engine:
            await self._engine.dispose()
            logger.info("database.engine.closed")
            self._engine = None
            self._session_factory = None


# Global database manager instance
db_manager: Optional[DatabaseManager] = None


def get_database_manager(
    database_url: Optional[str] = None,
    pool_size: int = 20,
    max_overflow: int = 10,
) -> DatabaseManager:
    """
    Get or create global database manager

    Args:
        database_url: Database connection string
        pool_size: Connection pool size
        max_overflow: Max overflow connections

    Returns:
        DatabaseManager instance
    """
    global db_manager

    if db_manager is None:
        if database_url is None:
            database_url = os.getenv(
                "DATABASE_URL",
                "postgresql+asyncpg://gbstudio:password@postgres:5432/gbstudio_hub"
            )

        db_manager = DatabaseManager(
            database_url=database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",
        )

    return db_manager


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(query)
    """
    db = get_database_manager()
    async for session in db.get_session():
        yield session
