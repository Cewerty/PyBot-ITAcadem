from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.base import BaseStorage, DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage
from aiogram_dialog import setup_dialogs
from dishka import AsyncContainer
from dishka.integrations.aiogram import setup_dishka

from ..core import logger
from ..core.config import settings
from ..di.containers import setup_container
from .dialogs import user_router
from .handlers import (
    broadcast_router,
    common_router,
    points_router,
    profile_router,
    roles_router,
)
from .handlers.common.dialog_errors import register_dialog_error_handlers
from .middlewares import (
    LoggerMiddleware,
    RateLimitMiddleware,
    RoleMiddleware,
    UserActivityMiddleware,
)


async def setup_dispatcher() -> Dispatcher:
    """Создать dispatcher с нужным backend для FSM."""
    if settings.fsm_storage_backend == "redis":
        storage = RedisStorage.from_url(
            settings.redis_url,
            key_builder=DefaultKeyBuilder(with_destiny=True),
        )
        logger.info("событие=инициализация_fsm backend=redis redis_url={redis_url}", redis_url=settings.redis_url)
        return Dispatcher(storage=storage)

    logger.info("событие=инициализация_fsm backend=memory")
    return Dispatcher()


async def setup_middlewares(dp: Dispatcher) -> None:
    """Подключить middleware к dispatcher."""
    if settings.enable_logging_middleware:
        logging_middleware = LoggerMiddleware(enabled=True)
        dp.message.middleware(logging_middleware)
        dp.callback_query.middleware(logging_middleware)
        dp.inline_query.middleware(logging_middleware)
        logger.info("событие=подключение_middleware middleware=LoggerMiddleware status=enabled")
    else:
        logger.info("событие=подключение_middleware middleware=LoggerMiddleware status=disabled")

    if settings.enable_user_activity_middleware:
        dp.message.middleware(UserActivityMiddleware())
        dp.callback_query.middleware(UserActivityMiddleware())
        logger.info("событие=подключение_middleware middleware=UserActivityMiddleware status=enabled")
    else:
        logger.info("событие=подключение_middleware middleware=UserActivityMiddleware status=disabled")

    if settings.enable_role_middleware:
        dp.message.middleware(RoleMiddleware())
        dp.callback_query.middleware(RoleMiddleware())
        dp.inline_query.middleware(RoleMiddleware())
        logger.info("событие=подключение_middleware middleware=RoleMiddleware status=enabled")
    else:
        logger.info("событие=подключение_middleware middleware=RoleMiddleware status=disabled")

    if settings.enable_rate_limit:
        dp.update.middleware(RateLimitMiddleware())
        dp.message.middleware(RateLimitMiddleware())
        dp.callback_query.middleware(RateLimitMiddleware())
        logger.info("событие=подключение_middleware middleware=RateLimitMiddleware status=enabled")
    else:
        logger.info("событие=подключение_middleware middleware=RateLimitMiddleware status=disabled")


async def setup_di(dp: Dispatcher) -> AsyncContainer:
    """Поднять DI-контейнер и подключить его к aiogram."""
    container = await setup_container()
    logger.debug("событие=инициализация_di status=success container={container}", container=container)
    setup_dishka(container, dp, auto_inject=True)
    return container


async def setup_bot(container: AsyncContainer) -> Bot:
    """Получить экземпляр бота из DI-контейнера."""
    return await container.get(Bot)


def setup_handlers(dp: Dispatcher) -> None:
    """Подключить роутеры и dialog-слой."""
    register_dialog_error_handlers(dp)
    dp.include_router(common_router)
    dp.include_router(points_router)
    dp.include_router(profile_router)
    dp.include_router(user_router)
    dp.include_router(roles_router)
    dp.include_router(broadcast_router)
    setup_dialogs(dp)


async def tg_bot_main() -> None:
    """Запустить бота с корректным shutdown-путём."""
    container: AsyncContainer | None = None
    dp: Dispatcher | None = None
    try:
        logger.info("событие=инициализация_бота status=started")
        dp = await setup_dispatcher()
        container = await setup_di(dp)
        bot = await setup_bot(container)
        await setup_middlewares(dp)
        setup_handlers(dp)
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("событие=инициализация_бота status=completed")
        logger.info("событие=запуск_polling status=started")
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logger.info("событие=завершение_бота причина=cancelled")
        raise
    except Exception:
        logger.exception("событие=неожиданная_ошибка_runtime")
        raise
    finally:
        logger.info("событие=graceful_shutdown status=started")

        if dp is not None:
            storage: BaseStorage | None = getattr(dp, "storage", None)
            if storage is not None:
                try:
                    await storage.close()
                    logger.info("событие=закрытие_fsm_storage status=success")
                except Exception:
                    logger.exception("событие=закрытие_fsm_storage status=failed")

        if container is not None:
            try:
                await container.close()
                logger.info("событие=закрытие_container status=success")
            except Exception:
                logger.exception("событие=закрытие_container status=failed")

        logger.info("событие=graceful_shutdown status=completed")
