from __future__ import annotations

from collections.abc import Awaitable
from typing import Protocol, cast

import pytest

from pybot.infrastructure.taskiq.tasks.leaderboard import publish_weekly_leaderboard_task
from pybot.services.weekly_leaderboard_publisher import WeeklyLeaderboardPublisherService


class WeeklyPublisherServiceSpy(WeeklyLeaderboardPublisherService):
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, str]] = []

    async def publish_weekly(self, *, recipient_id: int, limit: int, business_tz: str) -> None:
        self.calls.append((recipient_id, limit, business_tz))


class DishkaContainer(Protocol):
    async def get(
        self,
        dependency_type: type[WeeklyLeaderboardPublisherService],
        *args: object,
        component: str | None = None,
        **kwargs: object,
    ) -> WeeklyLeaderboardPublisherService: ...


class TaskCallable(Protocol):
    def __call__(
        self,
        *,
        recipient_id: int,
        limit: int,
        dishka_container: DishkaContainer,
    ) -> Awaitable[dict[str, int]]: ...


class DishkaContainerStub:
    def __init__(self, service: WeeklyLeaderboardPublisherService) -> None:
        self._service = service

    async def get(
        self,
        dependency_type: type[WeeklyLeaderboardPublisherService],
        *args: object,
        component: str | None = None,
        **kwargs: object,
    ) -> WeeklyLeaderboardPublisherService:
        assert dependency_type is WeeklyLeaderboardPublisherService
        resolved_component = component
        if args:
            resolved_component = args[0]
        elif "component" in kwargs:
            resolved_component = kwargs["component"]

        assert resolved_component in ("", None)
        return self._service


@pytest.mark.asyncio
async def test_publish_weekly_leaderboard_task_uses_service_and_returns_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = WeeklyPublisherServiceSpy()
    dishka_container = DishkaContainerStub(service)
    task = cast(TaskCallable, publish_weekly_leaderboard_task)

    monkeypatch.setattr(
        "pybot.infrastructure.taskiq.tasks.leaderboard.settings.leaderboard_weekly_timezone",
        "Asia/Yekaterinburg",
    )

    payload = await task(
        recipient_id=-100_200_300,
        limit=12,
        dishka_container=dishka_container,
    )

    assert payload == {
        "recipient_id": -100_200_300,
        "limit": 12,
    }
    assert service.calls == [(-100_200_300, 12, "Asia/Yekaterinburg")]
