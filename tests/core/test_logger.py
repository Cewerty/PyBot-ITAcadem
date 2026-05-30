from __future__ import annotations

import json

import pytest
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from pybot.core.config import BotSettings
from pybot.core.logger import setup_logger

ADMIN_TG_ID = 123_456_789
USER_ID = 42


class BotSettingsWithoutDotenv(BotSettings):
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings, env_settings)


def test_json_logger_emits_flat_loki_friendly_record(capsys: pytest.CaptureFixture[str]) -> None:
    settings = BotSettingsWithoutDotenv(
        BOT_TOKEN="123456:prod",
        BOT_TOKEN_TEST="123456:test",
        BOT_MODE="prod",
        DATABASE_URL="sqlite+aiosqlite:///./data/test.db",
        ROLE_REQUEST_ADMIN_TG_ID=ADMIN_TG_ID,
        LOG_FORMAT="json",
    )

    logger = setup_logger(settings)
    logger.bind(event="probe", user_id=USER_ID).info("Привет, {target}", target="Loki")

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload["level"] == "INFO"
    assert payload["record_level_name"] == "INFO"
    assert payload["message"] == "Привет, Loki"
    assert payload["event"] == "probe"
    assert payload["user_id"] == USER_ID
    assert payload["target"] == "Loki"
    assert payload["extra"]["event"] == "probe"
    assert "timestamp" in payload
    assert "elapsed_ms" in payload


def test_json_logger_preserves_exception_context(capsys: pytest.CaptureFixture[str]) -> None:
    settings = BotSettingsWithoutDotenv(
        BOT_TOKEN="123456:prod",
        BOT_TOKEN_TEST="123456:test",
        BOT_MODE="prod",
        DATABASE_URL="sqlite+aiosqlite:///./data/test.db",
        ROLE_REQUEST_ADMIN_TG_ID=ADMIN_TG_ID,
        LOG_FORMAT="json",
    )

    logger = setup_logger(settings)
    try:
        _raise_runtime_error()
    except RuntimeError:
        logger.exception("Runtime failed")

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload["level"] == "ERROR"
    assert payload["exception_type"] == "RuntimeError"
    assert payload["exception_message"] == "boom"
    assert "RuntimeError: boom" in payload["exception_traceback"]


def _raise_runtime_error() -> None:
    raise RuntimeError("boom")
