from __future__ import annotations

import pytest

from tests.database import validate_test_database_url


@pytest.mark.parametrize(
    "database_url",
    (
        "postgresql+asyncpg://test:test@127.0.0.1:5432/test",
        "postgresql+asyncpg://test:test@127.0.0.1:5432/pybot_test",
    ),
)
def test_validate_test_database_url_accepts_test_database(database_url: str) -> None:
    assert validate_test_database_url(database_url) == database_url


@pytest.mark.parametrize(
    "database_url",
    (
        "postgresql+asyncpg://test:test@127.0.0.1:5432/pybot",
        "postgresql://test:test@127.0.0.1:5432/pybot_test",
        "mysql+aiomysql://test:test@127.0.0.1:3306/pybot_test",
    ),
)
def test_validate_test_database_url_rejects_unsafe_target(database_url: str) -> None:
    with pytest.raises(ValueError, match="PYBOT_TEST_DATABASE_URL"):
        validate_test_database_url(database_url)
