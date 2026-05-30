"""CI-only bot runtime bootstrap smoke-check.

This script verifies that the bot process can assemble its runtime wiring inside
the production-like Compose graph without touching the real Telegram Bot API.
It intentionally stops before webhook deletion and polling, because CI does not
have a real token and the parity scope here is process wiring, not Telegram I/O.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress

from aiogram import Dispatcher
from dishka import AsyncContainer

from src.pybot.core import logger
from src.pybot.core.config import get_settings
from src.pybot.presentation.bot.tg_bot_run import (
    setup_bot,
    setup_di,
    setup_dispatcher,
    setup_handlers,
    setup_middlewares,
    setup_runtime_alerts_service,
)


async def close_dispatcher_storage(dispatcher: Dispatcher) -> None:
    """Close FSM storage resolved by the dispatcher when it exists."""
    storage = getattr(dispatcher, "storage", None)
    if storage is None:
        return

    await storage.close()


async def bootstrap_bot_runtime() -> tuple[Dispatcher, AsyncContainer]:
    """Assemble bot runtime dependencies up to the Telegram API boundary."""
    settings = get_settings()
    dispatcher = await setup_dispatcher(settings)
    container = await setup_di(dispatcher)

    await setup_bot(container)
    await setup_runtime_alerts_service(container)
    await setup_middlewares(dispatcher, settings)
    setup_handlers(dispatcher)

    logger.info("event=ci_parity_bot_runtime status=ready")
    return dispatcher, container


async def main() -> None:
    """Hold the container alive after successful runtime bootstrap."""
    dispatcher: Dispatcher | None = None
    container: AsyncContainer | None = None

    try:
        dispatcher, container = await bootstrap_bot_runtime()
        await asyncio.Event().wait()
    finally:
        if dispatcher is not None:
            with suppress(Exception):
                await close_dispatcher_storage(dispatcher)

        if container is not None:
            with suppress(Exception):
                await container.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("event=ci_parity_bot_runtime status=interrupted")
