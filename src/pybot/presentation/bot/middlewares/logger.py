"""Модуль бота IT Academ."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, ChatMemberUpdated, InlineQuery, Message, TelegramObject

from ....core import logger
from ....core.config import AppSettings


class LoggerMiddleware(BaseMiddleware):
    """Middleware for uniform update lifecycle logging without user payload data."""

    def __init__(self, settings: AppSettings, *, enabled: bool = False, log_sensitive: bool = False) -> None:
        """Initialize update lifecycle logging middleware.

        Args:
            enabled: Whether to enable the middleware explicitly.
            log_sensitive: Deprecated compatibility flag kept for constructor stability.
            settings: Bot runtime settings.
        """
        super().__init__()
        del log_sensitive
        self.settings = settings
        self.enabled = self.settings.enable_logging_middleware and enabled

    def _build_event_id(self, telegram_obj: TelegramObject, data: dict[str, Any]) -> str:
        """Build a correlation key for one update without embedding Telegram user/chat ids."""
        event_update = data.get("event_update")
        update_id = getattr(event_update, "update_id", None)
        if isinstance(update_id, int):
            return f"update:{update_id}"

        return f"{type(telegram_obj).__name__.lower()}:{id(telegram_obj)}"

    def _extract_minimal_info(self, telegram_obj: TelegramObject, data: dict[str, Any]) -> dict[str, str]:
        """Extract minimal non-PII metadata from a Telegram update."""
        info = {
            "event_type": "UNKNOWN",
            "event_id": self._build_event_id(telegram_obj, data),
        }

        supported_types = (Message, CallbackQuery, InlineQuery, ChatMemberUpdated)
        if not isinstance(telegram_obj, supported_types):
            logger.debug(
                "событие=неподдерживаемый_update event_id={event_id} тип={type}",
                event_id=info["event_id"],
                type=type(telegram_obj).__name__,
            )
            return info

        match telegram_obj:
            case Message():
                info["event_type"] = "MESSAGE"
            case CallbackQuery():
                info["event_type"] = "CALLBACK"
            case InlineQuery():
                info["event_type"] = "INLINE"
            case ChatMemberUpdated():
                info["event_type"] = "MEMBER_STATUS"

        return info

    def _get_handler_name(self, data: dict[str, Any]) -> str:
        """Get handler name without serializing the whole handler object."""
        if "handler" in data:
            handler = data["handler"]
            if hasattr(handler, "callback"):
                callback = handler.callback
                if hasattr(callback, "__name__"):
                    return callback.__name__

        return "unknown_handler"

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Log start, finish, and failure of update processing."""
        if not self.enabled:
            return await handler(event, data)

        event_info = self._extract_minimal_info(event, data)
        handler_name = self._get_handler_name(data)

        with logger.contextualize(update_id=event_info["event_id"], request_id=event_info["event_id"]):
            logger.info(
                "событие=получен_update event_id={event_id} тип={event_type} handler={handler_name}",
                event_id=event_info["event_id"],
                event_type=event_info["event_type"],
                handler_name=handler_name,
            )

            start_time = time.monotonic()
            try:
                result = await handler(event, data)
                elapsed = time.monotonic() - start_time

                logger.info(
                    "событие=обработан_update event_id={event_id} тип={event_type} handler={handler_name} "
                    "status=success elapsed_ms={elapsed_ms}",
                    event_id=event_info["event_id"],
                    event_type=event_info["event_type"],
                    handler_name=handler_name,
                    elapsed_ms=round(elapsed * 1000),
                )

                if elapsed > 1.0:
                    logger.warning(
                        "событие=медленный_handler event_id={event_id} тип={event_type} handler={handler_name} "
                        "elapsed_ms={elapsed_ms}",
                        event_id=event_info["event_id"],
                        event_type=event_info["event_type"],
                        handler_name=handler_name,
                        elapsed_ms=round(elapsed * 1000),
                    )
            except Exception as exc:
                elapsed = time.monotonic() - start_time
                logger.error(
                    "событие=ошибка_handler event_id={event_id} тип={event_type} handler={handler_name} "
                    "error_type={error_type} elapsed_ms={elapsed_ms}",
                    event_id=event_info["event_id"],
                    event_type=event_info["event_type"],
                    handler_name=handler_name,
                    error_type=type(exc).__name__,
                    elapsed_ms=round(elapsed * 1000),
                    exc_info=True,
                )
                raise
            else:
                return result
