from collections.abc import Sequence
from datetime import datetime
from zoneinfo import ZoneInfo

import pendulum
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.constants import PointsTypeEnum
from ..dto import WeeklyLeaderboardRowDTO
from ..infrastructure import PointsTransactionRepository


class LeaderboardService:
    def __init__(
        self,
        db: AsyncSession,
        points_transaction_repository: PointsTransactionRepository,
    ) -> None:
        self.db = db
        self.points_transaction_repository = points_transaction_repository

    async def get_previous_calendar_week_leaderboard(
        self,
        *,
        points_type: PointsTypeEnum,
        limit: int = 10,
        business_tz: str = "Asia/Yekaterinburg",
    ) -> Sequence[WeeklyLeaderboardRowDTO]:
        """Вернуть топ получателей за предыдущую календарную неделю.

        Период рассчитывается в бизнес-часовом поясе ``business_tz``.
        SQL-границы конвертируются в UTC-naive для совместимости с SQLite.
        Display-даты остаются timezone-aware в бизнес-TZ и передаются в DTO
        для корректного отображения пользователю.
        """
        now = pendulum.now(business_tz)
        start_local = now.start_of("week").subtract(weeks=1)
        end_local = start_local.add(weeks=1)

        # Timezone-aware даты в бизнес-TZ — только для отображения в DTO.
        business_timezone = ZoneInfo(business_tz)
        display_period_start = datetime.fromtimestamp(start_local.timestamp(), tz=business_timezone)
        display_period_end = datetime.fromtimestamp(end_local.timestamp(), tz=business_timezone)

        return await self.points_transaction_repository.find_top_recipients_for_period(
            self.db,
            points_type=points_type,
            period_start=display_period_start,
            period_end=display_period_end,
            limit=limit,
        )
