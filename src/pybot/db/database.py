from __future__ import annotations

from sqlalchemy.ext.asyncio import create_async_engine

from ..core.config import settings

if not settings.database_url:
    raise ValueError("Database URL is not configured.")

engine = create_async_engine(settings.database_url, echo=False)
