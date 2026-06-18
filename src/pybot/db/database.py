from __future__ import annotations

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def create_database_engine(database_url: str) -> AsyncEngine:
    """Create an asynchronous PostgreSQL engine.

    Args:
        database_url: PostgreSQL connection URL.

    Returns:
        Configured SQLAlchemy asynchronous engine.

    Raises:
        ValueError: If the URL is missing or does not target PostgreSQL.
    """
    if not database_url:
        raise ValueError("Database URL is not configured.")

    url = make_url(database_url)
    if url.drivername != "postgresql+asyncpg":
        raise ValueError(f"Only postgresql+asyncpg is supported; received driver {url.drivername!r}.")

    return create_async_engine(database_url, echo=False)
