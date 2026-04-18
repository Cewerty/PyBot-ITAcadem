from __future__ import annotations

from dishka.integrations.taskiq import FromDishka, inject

from ....core import logger, settings
from ....services.weekly_leaderboard_publisher import WeeklyLeaderboardPublisherService
from ..taskiq_app import get_taskiq_broker

broker = get_taskiq_broker()


@broker.task(task_name="leaderboard.publish_weekly")
@inject(patch_module=True)
async def publish_weekly_leaderboard_task(
    *,
    recipient_id: int,
    limit: int,
    service: FromDishka[WeeklyLeaderboardPublisherService],
) -> dict[str, int]:
    """Publish previous-week leaderboard to configured recipient."""
    await service.publish_weekly(
        recipient_id=recipient_id,
        limit=limit,
        business_tz=str(settings.leaderboard_weekly_timezone),
    )
    payload = {
        "recipient_id": recipient_id,
        "limit": limit,
    }
    logger.info("TaskIQ weekly leaderboard task finished with payload={payload}", payload=payload)
    return payload
