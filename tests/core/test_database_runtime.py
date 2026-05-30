from __future__ import annotations

import pytest
from sqlalchemy import text

from pybot.db.database import create_database_engine, ensure_sqlite_database_parent_dir


def test_ensure_sqlite_database_parent_dir_creates_missing_data_directory(tmp_path) -> None:
    database_path = tmp_path / "data" / "ensure_parent.sqlite3"

    ensure_sqlite_database_parent_dir(f"sqlite+aiosqlite:///{database_path.as_posix()}")

    assert database_path.parent.is_dir()


@pytest.mark.asyncio
async def test_create_database_engine_enables_sqlite_foreign_keys(tmp_path) -> None:
    database_path = tmp_path / "data" / "runtime_fk.sqlite3"
    database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    engine = create_database_engine(database_url)

    try:
        async with engine.connect() as connection:
            foreign_keys_enabled = await connection.scalar(text("PRAGMA foreign_keys"))
    finally:
        await engine.dispose()

    assert database_path.parent.is_dir()
    assert foreign_keys_enabled == 1
