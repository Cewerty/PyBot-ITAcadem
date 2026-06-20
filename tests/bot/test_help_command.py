from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from aiogram.types import Chat, Message, User

from pybot.presentation.bot import start_handlers_module
from pybot.presentation.texts import HELP_PRIVATE, HELP_PRIVATE_PUBLIC


def _build_message(*, text: str = "/help", from_user_id: int = 930_001) -> Message:
    sender = User(id=from_user_id, is_bot=False, first_name="Tester")
    return Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=from_user_id, type="private"),
        from_user=sender,
        text=text,
    )


@dataclass(slots=True)
class StubUserRolesService:
    roles: Sequence[str] = ()
    find_user_roles_mock: AsyncMock = field(init=False)

    def __post_init__(self) -> None:
        self.find_user_roles_mock = AsyncMock(return_value=self.roles)

    async def find_user_roles(self, user_id: int) -> Sequence[str]:
        return await self.find_user_roles_mock(user_id)


@pytest.mark.asyncio
async def test_help_private_without_user_id_returns_public_help(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_roles_service = StubUserRolesService(roles=["Admin"])
    message = _build_message()
    answer_mock = AsyncMock()
    monkeypatch.setattr(Message, "answer", answer_mock)

    await start_handlers_module.cmd_help_private(
        message=message,
        user_roles_service=user_roles_service,
        user_id=None,
    )

    user_roles_service.find_user_roles_mock.assert_not_awaited()
    answer_mock.assert_awaited_once_with(HELP_PRIVATE_PUBLIC)


@pytest.mark.asyncio
async def test_help_private_registered_non_admin_returns_public_help(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_roles_service = StubUserRolesService(roles=["Student"])
    message = _build_message()
    answer_mock = AsyncMock()
    monkeypatch.setattr(Message, "answer", answer_mock)

    await start_handlers_module.cmd_help_private(
        message=message,
        user_roles_service=user_roles_service,
        user_id=42,
    )

    user_roles_service.find_user_roles_mock.assert_awaited_once_with(42)
    answer_mock.assert_awaited_once_with(HELP_PRIVATE_PUBLIC)


@pytest.mark.asyncio
async def test_help_private_registered_admin_returns_admin_help(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_roles_service = StubUserRolesService(roles=["Admin"])
    message = _build_message()
    answer_mock = AsyncMock()
    monkeypatch.setattr(Message, "answer", answer_mock)

    await start_handlers_module.cmd_help_private(
        message=message,
        user_roles_service=user_roles_service,
        user_id=42,
    )

    user_roles_service.find_user_roles_mock.assert_awaited_once_with(42)
    answer_mock.assert_awaited_once_with(HELP_PRIVATE)
