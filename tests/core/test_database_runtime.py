from __future__ import annotations

import pytest
from sqlalchemy import text

from pybot.db.database import create_database_engine


def test_create_database_engine_rejects_empty_url() -> None:
    with pytest.raises(ValueError, match="not configured"):
        create_database_engine("")


@pytest.mark.parametrize(
    "database_url",
    (
        "postgresql://test:test@127.0.0.1:5432/pybot_test",
        "mysql+aiomysql://test:test@127.0.0.1:3306/pybot_test",
    ),
)
def test_create_database_engine_rejects_unsupported_driver(database_url: str) -> None:
    with pytest.raises(ValueError, match=r"Only postgresql\+asyncpg is supported"):
        create_database_engine(database_url)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_database_engine_connects_to_postgresql(test_database_url: str) -> None:
    engine = create_database_engine(test_database_url)

    try:
        async with engine.connect() as connection:
            result = await connection.scalar(text("SELECT 1"))
    finally:
        await engine.dispose()

    assert result == 1
