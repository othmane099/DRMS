from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from config import settings as app_settings

Base = declarative_base()

engine_kwargs = {
    "pool_size": app_settings.DATABASE_POOL_SIZE,
    "pool_recycle": app_settings.DATABASE_POOL_TTL,
    "pool_pre_ping": app_settings.DATABASE_POOL_PRE_PING,
}

engine = create_async_engine(app_settings.DATABASE_URL, **engine_kwargs)
async_session = async_sessionmaker(engine, expire_on_commit=False)


def default_session_factory() -> AsyncSession:
    return async_session(bind=engine, autocommit=False, expire_on_commit=False)
