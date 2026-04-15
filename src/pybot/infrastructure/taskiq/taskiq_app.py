from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import TYPE_CHECKING, Any

from dishka import AsyncContainer
from dishka.integrations.taskiq import setup_dishka
from taskiq import AsyncBroker, TaskiqEvents, TaskiqScheduler, TaskiqState
from taskiq_redis import ListRedisScheduleSource, RedisStreamBroker

from ...core import logger, settings
from ...di.containers import setup_taskiq_container

if TYPE_CHECKING:
    from taskiq.kicker import AsyncKicker
    from taskiq.scheduler.scheduled_task import ScheduledTask

LEADERBOARD_WEEKLY_SCHEDULE_ID = "leaderboard:weekly"
LEADERBOARD_WEEKLY_TASK_NAME = "leaderboard.publish_weekly"


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


def _resolve_publish_weekly_leaderboard_kicker() -> AsyncKicker[Any, Any]:
    task_module = import_module(".tasks.leaderboard", package=__package__)
    task = task_module.publish_weekly_leaderboard_task
    return task.kicker()


def _is_expected_weekly_schedule(
    schedule: ScheduledTask,
    *,
    cron_expression: str,
    timezone_name: str,
    recipient_id: int,
    limit: int,
) -> bool:
    if schedule.task_name != LEADERBOARD_WEEKLY_TASK_NAME:
        return False
    if schedule.cron != cron_expression:
        return False
    if str(schedule.cron_offset) != timezone_name:
        return False

    return schedule.kwargs.get("recipient_id") == recipient_id and schedule.kwargs.get("limit") == limit


async def ensure_weekly_leaderboard_schedule(
    *,
    broker: AsyncBroker | None = None,
    schedule_source: ListRedisScheduleSource | None = None,
) -> None:
    """Idempotently ensure one weekly leaderboard cron schedule in Redis source."""
    runtime_broker = broker or get_taskiq_broker()
    if not runtime_broker.is_scheduler_process:
        logger.debug("событие=leaderboard_weekly_ensure status=skipped причина=not_scheduler_process")
        return

    if not settings.leaderboard_weekly_enabled:
        logger.info("событие=leaderboard_weekly_ensure status=skipped причина=disabled")
        return

    recipient_id = settings.leaderboard_weekly_recipient_id
    if recipient_id is None:
        raise RuntimeError("LEADERBOARD_WEEKLY_RECIPIENT_ID must be set when LEADERBOARD_WEEKLY_ENABLED=true")

    cron_expression = str(settings.leaderboard_weekly_cron)
    timezone_name = str(settings.leaderboard_weekly_timezone)
    limit = settings.leaderboard_weekly_limit

    source = schedule_source or get_taskiq_schedule_source()
    existing_schedule = next(
        (item for item in await source.get_schedules() if item.schedule_id == LEADERBOARD_WEEKLY_SCHEDULE_ID),
        None,
    )

    if existing_schedule is not None and _is_expected_weekly_schedule(
        existing_schedule,
        cron_expression=cron_expression,
        timezone_name=timezone_name,
        recipient_id=recipient_id,
        limit=limit,
    ):
        logger.info(
            "событие=leaderboard_weekly_ensure status=up_to_date schedule_id={schedule_id}",
            schedule_id=LEADERBOARD_WEEKLY_SCHEDULE_ID,
        )
        return

    if existing_schedule is not None:
        await source.delete_schedule(LEADERBOARD_WEEKLY_SCHEDULE_ID)
        logger.info(
            "событие=leaderboard_weekly_ensure status=replaced schedule_id={schedule_id}",
            schedule_id=LEADERBOARD_WEEKLY_SCHEDULE_ID,
        )

    await (
        _resolve_publish_weekly_leaderboard_kicker()
        .with_schedule_id(LEADERBOARD_WEEKLY_SCHEDULE_ID)
        .with_labels(cron_offset=timezone_name)
        .schedule_by_cron(
            source,
            cron_expression,
            recipient_id=recipient_id,
            limit=limit,
        )
    )
    logger.info(
        "событие=leaderboard_weekly_ensure status=created schedule_id={schedule_id}",
        schedule_id=LEADERBOARD_WEEKLY_SCHEDULE_ID,
    )


async def _on_client_startup(_state: TaskiqState) -> None:
    """Scheduler startup hook for periodic schedules ensure."""
    await ensure_weekly_leaderboard_schedule()


def get_taskiq_broker() -> AsyncBroker:
    """Вернуть singleton брокера TaskIQ для worker и scheduler runtime."""
    if _runtime_state.broker is not None:
        return _runtime_state.broker

    broker = RedisStreamBroker(settings.redis_url)
    broker.add_event_handler(TaskiqEvents.WORKER_STARTUP, _on_worker_startup)
    broker.add_event_handler(TaskiqEvents.WORKER_SHUTDOWN, _on_worker_shutdown)
    broker.add_event_handler(TaskiqEvents.CLIENT_STARTUP, _on_client_startup)

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
