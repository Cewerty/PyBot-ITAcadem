from __future__ import annotations

import os
import random
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from alembic.config import Config
from dishka import AsyncContainer, make_async_container
from faker import Faker
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from alembic import command

# Ensure test settings materialization works in CI even without repository .env.
os.environ.setdefault("BOT_TOKEN", "123456:TEST_TOKEN")
os.environ.setdefault("BOT_TOKEN_TEST", "123456:TEST_TOKEN")
os.environ.setdefault("ROLE_REQUEST_ADMIN_TG_ID", "999999999")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@127.0.0.1:5432/pybot_unit_test",
)
os.environ["BOT_MODE"] = "test"

from pybot.core.config import AppSettings, get_settings
from pybot.db.models import Base
from pybot.di import containers as di_containers
from pybot.di.containers import (
    ConfigProvider,
    DomainServiceProvider,
    HealthProvider,
    RedisProvider,
    RepositoryProvider,
    ServiceProvider,
)
from tests.database import TEST_DATABASE_ENV, validate_test_database_url
from tests.providers import TestDatabaseProvider, TestOverridesProvider

_TEST_POSTGRES_IMAGE = "postgres:18-alpine"


@pytest.fixture(autouse=True)
def faker_seed() -> Generator[None]:
    """Seed all pseudo-random generators for deterministic tests."""
    random.seed(42)
    Faker.seed(42)
    yield


@pytest.fixture(autouse=True)
def settings_obj() -> Generator[AppSettings]:
    """Provide mutable settings without starting integration infrastructure."""
    get_settings.cache_clear()
    runtime_settings = get_settings().model_copy(deep=True)
    runtime_settings.database_url = "postgresql+asyncpg://test:test@127.0.0.1:5432/pybot_unit_test"
    runtime_settings.bot_mode = "test"
    runtime_settings.bot_token = os.environ["BOT_TOKEN"]
    runtime_settings.bot_token_test = os.environ["BOT_TOKEN_TEST"]
    runtime_settings.notification_backend = "telegram"
    runtime_settings.role_request_admin_tg_id = 999999999
    runtime_settings.auto_admin_telegram_ids = set()
    runtime_settings.health_api_enabled = False
    yield runtime_settings
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def patch_di_settings_getter(
    monkeypatch: pytest.MonkeyPatch,
    settings_obj: AppSettings,
) -> Generator[None]:
    """Route DI settings requests to the per-test settings object."""
    monkeypatch.setattr(di_containers, "get_settings", lambda: settings_obj)
    yield


@pytest.fixture(scope="session")
def test_database_url() -> Generator[str]:
    """Provide one PostgreSQL database for the integration test session."""
    configured_url = os.environ.get(TEST_DATABASE_ENV)
    if configured_url:
        try:
            validated_url = validate_test_database_url(configured_url)
        except ValueError as err:
            raise pytest.UsageError(str(err)) from err
        yield validated_url
        return

    with PostgresContainer(
        image=_TEST_POSTGRES_IMAGE,
        username="test",
        password="test",  # noqa: S106 - isolated disposable test database
        dbname="pybot_test",
        driver="asyncpg",
    ) as postgres:
        yield validate_test_database_url(postgres.get_connection_url())


@pytest.fixture(scope="session")
def migrated_test_database(test_database_url: str) -> Generator[None]:
    """Apply the real Alembic baseline once to the integration database."""
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_database_url
    try:
        command.upgrade(Config("alembic.ini"), "head")
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
    yield


@pytest_asyncio.fixture
async def test_engine(
    migrated_test_database: None,
    test_database_url: str,
) -> AsyncGenerator[AsyncEngine]:
    """Create a function-scoped engine for the migrated PostgreSQL database."""
    engine = create_async_engine(test_database_url, echo=False)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def clean_database(test_engine: AsyncEngine) -> AsyncGenerator[None]:
    """Reset all application tables before and after each integration test."""
    table_names = [
        test_engine.dialect.identifier_preparer.quote(table.name) for table in reversed(Base.metadata.sorted_tables)
    ]
    truncate_statement = text(f"TRUNCATE TABLE {', '.join(table_names)} RESTART IDENTITY CASCADE")

    async with test_engine.begin() as connection:
        await connection.execute(truncate_statement)
    try:
        yield
    finally:
        async with test_engine.begin() as connection:
            await connection.execute(truncate_statement)


@pytest.fixture
def db_session_maker(
    clean_database: None,
    test_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture
async def db_session(
    db_session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession]:
    """Request-scoped async session with explicit teardown."""
    async with db_session_maker() as session:
        try:
            yield session
        finally:
            if session.in_transaction():
                await session.rollback()


@pytest_asyncio.fixture
async def dishka_test_container(
    clean_database: None,
    test_engine: AsyncEngine,
) -> AsyncGenerator[AsyncContainer]:
    """Build isolated Dishka test container with fake outbound adapters."""
    container = make_async_container(
        TestDatabaseProvider(test_engine),
        RepositoryProvider(),
        ServiceProvider(),
        DomainServiceProvider(),
        RedisProvider(),
        HealthProvider(),
        ConfigProvider(),
        TestOverridesProvider(),
    )

    try:
        yield container
    finally:
        await container.close()


@pytest_asyncio.fixture
async def dishka_request_container(
    dishka_test_container: AsyncContainer,
) -> AsyncGenerator[AsyncContainer]:
    """Open Dishka request scope for service-level tests."""
    async with dishka_test_container() as request_container:
        yield request_container


@pytest.fixture
def patched_public_di_engine(
    clean_database: None,
    monkeypatch: pytest.MonkeyPatch,
    test_engine: AsyncEngine,
) -> AsyncEngine:
    """Route public DI container setup through the isolated test engine."""
    monkeypatch.setattr(di_containers, "global_engine", test_engine)
    return test_engine
