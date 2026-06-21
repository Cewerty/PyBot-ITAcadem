from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
from aiogram.types import Chat, Message, User

from pybot.core.constants import TaskScheduleKind
from pybot.domain.exceptions import BroadcastMessageNotSpecifiedError
from pybot.dto import BroadcastDTO, BroadcastResult, CompetenceBroadcastDTO, CompetenceReadDTO, RoleBroadcastDTO
from pybot.presentation.bot import _extract_message_for_broadcast, broadcast_command
from pybot.presentation.bot.handlers.broadcast import broadcast_commands as broadcast_commands_module
from pybot.presentation.texts import BROADCAST_MESSAGE_REQUIRED, BROADCAST_USAGE, broadcast_result_summary
from pybot.services.notification_facade import NotificationFacade


def _build_message(text: str, user_id: int = 100_001) -> Message:
    sender = User(id=user_id, is_bot=False, first_name="Admin")
    return Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=user_id, type="private"),
        from_user=sender,
        text=text,
    )


@dataclass(slots=True)
class StubBroadcastService:
    all_messages: list[BroadcastDTO] = field(default_factory=list)
    role_messages: list[RoleBroadcastDTO] = field(default_factory=list)
    competence_messages: list[CompetenceBroadcastDTO] = field(default_factory=list)
    result: BroadcastResult = field(
        default_factory=lambda: BroadcastResult(
            attempted=5,
            sent=3,
            failed_temporary=1,
            failed_permanent=1,
            skipped_invalid_user=0,
        )
    )

    async def broadcast_for_all(self, broadcast_data: BroadcastDTO) -> BroadcastResult:
        self.all_messages.append(broadcast_data)
        return self.result

    async def broadcast_for_users_with_role(self, broadcast_data: RoleBroadcastDTO) -> BroadcastResult:
        self.role_messages.append(broadcast_data)
        return self.result

    async def broadcast_for_users_with_competence(self, broadcast_data: CompetenceBroadcastDTO) -> BroadcastResult:
        self.competence_messages.append(broadcast_data)
        return self.result


@dataclass(slots=True)
class StubCompetenceService:
    competencies: list[CompetenceReadDTO]

    async def find_all_competencies(self) -> list[CompetenceReadDTO]:
        return self.competencies


@dataclass(slots=True)
class StubNotificationFacade:
    notify_user: AsyncMock = field(default_factory=AsyncMock)


def _last_reply_text(reply_mock: AsyncMock) -> str:
    assert reply_mock.await_args_list
    return str(reply_mock.await_args_list[-1][0][0])


def _assert_summary_notification(
    notification_facade: StubNotificationFacade,
    *,
    recipient_id: int,
    result: BroadcastResult,
) -> None:
    notification_facade.notify_user.assert_awaited_once()
    notify_dto = notification_facade.notify_user.await_args.args[0]
    assert notify_dto.recipient_id == recipient_id
    assert notify_dto.kind is TaskScheduleKind.IMMEDIATE
    assert notify_dto.message == broadcast_result_summary(result)
    assert str(result.attempted) in notify_dto.message
    assert str(result.sent) in notify_dto.message
    assert str(result.failed_temporary) in notify_dto.message
    assert str(result.failed_permanent) in notify_dto.message
    assert str(result.skipped_invalid_user) in notify_dto.message


@pytest.mark.asyncio
async def test_extract_message_for_broadcast_after_competence_target() -> None:
    message = _build_message("/broadcast Python hello team")
    extracted = await _extract_message_for_broadcast(message, "Python")
    assert extracted == "hello team"


@pytest.mark.asyncio
async def test_extract_message_for_broadcast_raises_when_message_is_missing() -> None:
    message = _build_message("/broadcast @all")
    with pytest.raises(BroadcastMessageNotSpecifiedError):
        await _extract_message_for_broadcast(message, "@all")


@pytest.mark.asyncio
async def test_broadcast_command_routes_to_all(monkeypatch: pytest.MonkeyPatch) -> None:
    message = _build_message("/broadcast @all hello everyone")
    broadcast_service = StubBroadcastService()
    competence_service = StubCompetenceService(competencies=[])
    notification_facade = StubNotificationFacade()
    reply_mock = AsyncMock()
    monkeypatch.setattr(Message, "reply", reply_mock)

    await broadcast_command(
        message=message,
        broadcast_service=broadcast_service,
        competence_service=competence_service,
        notification_facade=cast(NotificationFacade, notification_facade),
    )

    assert len(broadcast_service.all_messages) == 1
    assert broadcast_service.all_messages[0].message == "hello everyone"
    assert broadcast_service.role_messages == []
    assert broadcast_service.competence_messages == []
    _assert_summary_notification(notification_facade, recipient_id=100_001, result=broadcast_service.result)
    assert reply_mock.await_count == 0


@pytest.mark.asyncio
async def test_broadcast_command_routes_to_role(monkeypatch: pytest.MonkeyPatch) -> None:
    message = _build_message("/broadcast Admin hello role")
    broadcast_service = StubBroadcastService()
    competence_service = StubCompetenceService(competencies=[])
    notification_facade = StubNotificationFacade()
    reply_mock = AsyncMock()
    monkeypatch.setattr(Message, "reply", reply_mock)

    await broadcast_command(
        message=message,
        broadcast_service=broadcast_service,
        competence_service=competence_service,
        notification_facade=cast(NotificationFacade, notification_facade),
    )

    assert broadcast_service.all_messages == []
    assert len(broadcast_service.role_messages) == 1
    assert broadcast_service.role_messages[0].role_name == "Admin"
    assert broadcast_service.role_messages[0].message == "hello role"
    assert broadcast_service.competence_messages == []
    _assert_summary_notification(notification_facade, recipient_id=100_001, result=broadcast_service.result)
    assert reply_mock.await_count == 0


@pytest.mark.asyncio
async def test_broadcast_command_routes_to_competence(monkeypatch: pytest.MonkeyPatch) -> None:
    message = _build_message("/broadcast Python hello competence")
    broadcast_service = StubBroadcastService()
    competence_service = StubCompetenceService(
        competencies=[
            CompetenceReadDTO(id=1, name="Python", description=None),
            CompetenceReadDTO(id=2, name="SQL", description=None),
        ]
    )
    notification_facade = StubNotificationFacade()
    reply_mock = AsyncMock()
    monkeypatch.setattr(Message, "reply", reply_mock)

    await broadcast_command(
        message=message,
        broadcast_service=broadcast_service,
        competence_service=competence_service,
        notification_facade=cast(NotificationFacade, notification_facade),
    )

    assert broadcast_service.all_messages == []
    assert broadcast_service.role_messages == []
    assert len(broadcast_service.competence_messages) == 1
    assert broadcast_service.competence_messages[0].competence_id == 1
    assert broadcast_service.competence_messages[0].message == "hello competence"
    _assert_summary_notification(notification_facade, recipient_id=100_001, result=broadcast_service.result)
    assert reply_mock.await_count == 0


@pytest.mark.asyncio
async def test_broadcast_command_replies_with_summary_when_notification_enqueue_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = _build_message("/broadcast @all hello everyone")
    broadcast_service = StubBroadcastService()
    competence_service = StubCompetenceService(competencies=[])
    notification_facade = StubNotificationFacade(notify_user=AsyncMock(side_effect=RuntimeError("queue down")))
    reply_mock = AsyncMock()
    logger_exception_mock = Mock()
    monkeypatch.setattr(Message, "reply", reply_mock)
    monkeypatch.setattr(broadcast_commands_module.logger, "exception", logger_exception_mock)

    await broadcast_command(
        message=message,
        broadcast_service=broadcast_service,
        competence_service=competence_service,
        notification_facade=cast(NotificationFacade, notification_facade),
    )

    notification_facade.notify_user.assert_awaited_once()
    reply_mock.assert_awaited_once_with(broadcast_result_summary(broadcast_service.result))
    logger_exception_mock.assert_called_once()


@pytest.mark.asyncio
async def test_broadcast_command_replies_when_target_is_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    message = _build_message("/broadcast Unknown hello")
    broadcast_service = StubBroadcastService()
    competence_service = StubCompetenceService(competencies=[CompetenceReadDTO(id=1, name="Python", description=None)])
    notification_facade = StubNotificationFacade()
    reply_mock = AsyncMock()
    monkeypatch.setattr(Message, "reply", reply_mock)

    await broadcast_command(
        message=message,
        broadcast_service=broadcast_service,
        competence_service=competence_service,
        notification_facade=cast(NotificationFacade, notification_facade),
    )

    assert broadcast_service.all_messages == []
    assert broadcast_service.role_messages == []
    assert broadcast_service.competence_messages == []
    notification_facade.notify_user.assert_not_awaited()
    assert reply_mock.await_count == 1
    assert "Не удалось распознать получателя рассылки" in _last_reply_text(reply_mock)


@pytest.mark.asyncio
async def test_broadcast_command_replies_when_broadcast_message_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    message = _build_message("/broadcast @all")
    broadcast_service = StubBroadcastService()
    competence_service = StubCompetenceService(competencies=[])
    notification_facade = StubNotificationFacade()
    reply_mock = AsyncMock()
    monkeypatch.setattr(Message, "reply", reply_mock)

    await broadcast_command(
        message=message,
        broadcast_service=broadcast_service,
        competence_service=competence_service,
        notification_facade=cast(NotificationFacade, notification_facade),
    )

    assert broadcast_service.all_messages == []
    assert broadcast_service.role_messages == []
    assert broadcast_service.competence_messages == []
    notification_facade.notify_user.assert_not_awaited()
    assert reply_mock.await_count == 1
    assert _last_reply_text(reply_mock) == BROADCAST_MESSAGE_REQUIRED


@pytest.mark.asyncio
async def test_broadcast_command_replies_when_target_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    message = _build_message("/broadcast")
    broadcast_service = StubBroadcastService()
    competence_service = StubCompetenceService(competencies=[])
    notification_facade = StubNotificationFacade()
    reply_mock = AsyncMock()
    monkeypatch.setattr(Message, "reply", reply_mock)

    await broadcast_command(
        message=message,
        broadcast_service=broadcast_service,
        competence_service=competence_service,
        notification_facade=cast(NotificationFacade, notification_facade),
    )

    notification_facade.notify_user.assert_not_awaited()
    reply_mock.assert_awaited_once_with(BROADCAST_USAGE)


def test_broadcast_result_summary_contains_all_counters() -> None:
    result = BroadcastResult(
        attempted=10,
        sent=7,
        failed_temporary=1,
        failed_permanent=2,
        skipped_invalid_user=3,
    )

    summary = broadcast_result_summary(result)

    assert "10" in summary
    assert "7" in summary
    assert "1" in summary
    assert "2" in summary
    assert "3" in summary
    assert "Р " not in summary
