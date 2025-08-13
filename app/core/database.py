import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, Session as SyncSession
from sqlalchemy import create_engine
from contextlib import asynccontextmanager, contextmanager
from . import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = (
    f"postgresql+asyncpg://{config.POSTGRES_USER}:{config.POSTGRES_PASSWORD}"
    f"@{config.POSTGRES_HOST}:{config.POSTGRES_PORT}/{config.POSTGRES_DB}"
)

DATABASE_URL_SYNC = (
    f"postgresql://{config.POSTGRES_USER}:{config.POSTGRES_PASSWORD}"
    f"@{config.POSTGRES_HOST}:{config.POSTGRES_PORT}/{config.POSTGRES_DB}"
)

# connection pool parameters
POOL_SIZE = 100
MAX_OVERFLOW = 20
POOL_TIMEOUT = 30


class AsyncCustomSession(AsyncSession):
    async def commit(self):
        """Commit the current transaction."""
        try:
            if config.API_ENV.lower() != "test":
                await super().commit()
        except Exception as e:
            logger.error(f"Error committing session: {e}")
            await self.rollback()
            raise

# create async engine
engine = create_async_engine(
    DATABASE_URL,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT
)

# create sync engine
sync_engine = create_engine(
    DATABASE_URL_SYNC,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT
)

class AsyncCustomSessionMixin(AsyncSession):
    async def commit(self):
        """Commit the current transaction."""
        try:
            if config.API_ENV.lower() != "test":
                await super().commit()
        except Exception as e:
            logger.error(f"Error committing session: {e}")
            await self.rollback()
            raise
    
    async def refresh(self, obj, *, with_for_update: bool = False):
        """Refresh the state of the object."""
        try:
            if config.API_ENV.lower() != "test":
                await super().refresh(obj, with_for_update=with_for_update)
        except Exception as e:
            logger.error(f"Error refreshing session: {e}")
            raise

class SyncCustomSessionMixin(SyncSession):
    pass

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncCustomSessionMixin,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    class_=SyncCustomSessionMixin,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

# ORM model base class
DBBase = declarative_base()


# provide async context manager to manage database session
@asynccontextmanager
async def get_async_session():
    """Provide a transactional scope for database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database transaction error: {e}", exc_info=True)
            raise

# provide sync context manager to manage database session
@contextmanager
def get_sync_session():
    """Provide a transactional scope for synchronous database session."""
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database transaction error (sync): {e}", exc_info=True)
        raise
    finally:
        session.close()