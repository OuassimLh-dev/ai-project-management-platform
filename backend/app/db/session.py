from collections.abc import Generator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings


def create_db_engine(database_url: str) -> Engine:
    """Build an engine without connecting; SQLite is supplied explicitly by tests."""
    url = make_url(database_url)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    return create_engine(url, pool_pre_ping=True)


@lru_cache
def get_session_factory(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=create_db_engine(database_url), expire_on_commit=False)


def get_db(settings: Annotated[Settings, Depends(get_settings)]) -> Generator[Session, None, None]:
    """Yield a request session; callers commit explicitly, close rolls back pending work."""
    with get_session_factory(settings.database_url)() as session:
        yield session
