from __future__ import annotations

from dataclasses import dataclass

from dishka import AsyncContainer
from dishka.integrations.taskiq import setup_dishka
from taskiq import AsyncBroker, TaskiqEvents, TaskiqScheduler, TaskiqState
from taskiq_redis import ListRedisScheduleSource, RedisStreamBroker

from ...core import logger, settings
from ...di.containers import setup_taskiq_container


@dataclass(slots=True)
class _TaskiqRuntimeState:
    """Хранит process-local состояние TaskIQ интеграции."""

    broker: AsyncBroker | None = None
    scheduler: TaskiqScheduler | None = None
    schedule_source: ListRedisScheduleSource | None = None
    container: AsyncContainer | None = None


_runtime_state = _TaskiqRuntimeState()


async def _on_worker_startup(_state: TaskiqState) -> None:
    """Поднять DI-контейнер Dishka и подключить его к TaskIQ воркеру."""
    if _runtime_state.container is not None:
        logger.warning("событие=инициализация_taskiq_worker status=skipped причина=container_already_initialized")
        return
    if _runtime_state.broker is None:
        raise RuntimeError("TaskIQ broker is not initialized.")

    container = setup_taskiq_container()
    setup_dishka(container=container, broker=_runtime_state.broker)
    _runtime_state.container = container
    logger.info("событие=инициализация_taskiq_worker status=success")


async def _on_worker_shutdown(_state: TaskiqState) -> None:
    """Корректно закрыть DI-контейнер Dishka при остановке воркера."""
    if _runtime_state.container is None:
        logger.warning("событие=завершение_taskiq_worker status=skipped причина=container_not_initialized")
        return

    await _runtime_state.container.close()
    _runtime_state.container = None
    logger.info("событие=завершение_taskiq_worker status=success")


def get_taskiq_broker() -> AsyncBroker:
    """Вернуть singleton брокера TaskIQ для worker и scheduler runtime."""
    if _runtime_state.broker is not None:
        return _runtime_state.broker

    broker = RedisStreamBroker(settings.redis_url)
    broker.add_event_handler(TaskiqEvents.WORKER_STARTUP, _on_worker_startup)
    broker.add_event_handler(TaskiqEvents.WORKER_SHUTDOWN, _on_worker_shutdown)

    _runtime_state.broker = broker
    return _runtime_state.broker


def get_taskiq_schedule_source() -> ListRedisScheduleSource:
    """Вернуть singleton schedule source для scheduler-процесса."""
    if _runtime_state.schedule_source is not None:
        return _runtime_state.schedule_source

    _runtime_state.schedule_source = ListRedisScheduleSource(settings.redis_url)
    return _runtime_state.schedule_source


def get_taskiq_scheduler() -> TaskiqScheduler:
    """Вернуть singleton scheduler для отложенных и periodic задач."""
    if _runtime_state.scheduler is not None:
        return _runtime_state.scheduler

    broker = get_taskiq_broker()
    source = get_taskiq_schedule_source()
    _runtime_state.scheduler = TaskiqScheduler(broker=broker, sources=[source])
    return _runtime_state.scheduler
