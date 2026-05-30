from __future__ import annotations

from pathlib import Path
from typing import Protocol

from sqlalchemy import event
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import ConnectionPoolEntry


class _SQLiteCursorProtocol(Protocol):
    def execute(self, statement: str) -> object: ...

    def close(self) -> None: ...


class _SQLiteConnectionProtocol(Protocol):
    def cursor(self) -> _SQLiteCursorProtocol: ...


def _is_sqlite_url(database_url: str) -> bool:
    """Проверяет, является ли URL базы данных адресом SQLite.

    Args:
        database_url: Строка подключения к базе данных.

    Returns:
        bool: True, если бэкенд — sqlite, иначе False.
    """
    url: URL = make_url(database_url)
    return url.get_backend_name() == "sqlite"


def _get_sqlite_file_path(database_url: str) -> Path | None:
    """Return SQLite file path for file-based SQLite URLs."""
    if not _is_sqlite_url(database_url):
        return None

    url: URL = make_url(database_url)
    database_name = url.database
    if not database_name or database_name == ":memory:":
        return None

    return Path(database_name)


def ensure_sqlite_database_parent_dir(database_url: str) -> None:
    """Create parent directory for file-based SQLite databases when needed."""
    sqlite_path = _get_sqlite_file_path(database_url)
    if sqlite_path is None:
        return

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)


def _attach_sqlite_foreign_keys_pragma(engine: AsyncEngine) -> None:
    """Прикрепляет обработчик события для включения внешних ключей в SQLite.

    SQLite по умолчанию не проверяет ограничения внешних ключей. Этот метод
    настраивает движок на выполнение 'PRAGMA foreign_keys=ON' при каждом подключении.

    Args:
        engine: Асинхронный движок SQLAlchemy.
    """

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(
        dbapi_connection: _SQLiteConnectionProtocol,
        _connection_record: ConnectionPoolEntry,
    ) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_database_engine(database_url: str) -> AsyncEngine:
    """Создает и настраивает асинхронный движок базы данных.

    Если используется SQLite, автоматически включает поддержку внешних ключей.

    Args:
        database_url: Строка подключения к базе данных.

    Returns:
        AsyncEngine: Сконфигурированный асинхронный движок SQLAlchemy.

    Raises:
        ValueError: Если URL базы данных не настроен.
    """
    if not database_url:
        raise ValueError("Database URL is not configured.")

    ensure_sqlite_database_parent_dir(database_url)
    engine = create_async_engine(database_url, echo=False)
    if _is_sqlite_url(database_url):
        _attach_sqlite_foreign_keys_pragma(engine)
    return engine
