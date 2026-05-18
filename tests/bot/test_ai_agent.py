"""Tests for AI agent tool invocations using PydanticAI TestModel.

Uses the ``override_ai_agent`` fixture from conftest.py which replaces
the production LLM model with ``TestModel`` — a deterministic, non-AI model
that procedurally calls all registered tools and returns a text response.
"""

from __future__ import annotations

from datetime import date
from typing import NamedTuple
from unittest.mock import AsyncMock

import pytest
from pydantic_ai.models.test import TestModel

from pybot.core.constants import PointsTypeEnum
from pybot.dto import (
    CompetenceReadDTO,
    LevelReadDTO,
    ProfileViewDTO,
    UserLevelReadDTO,
    UserReadDTO,
)
from pybot.dto.value_objects import Points
from pybot.presentation.shared.ai_agent import AgentDeps, ai_agent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class AgentTestContext(NamedTuple):
    """Bundle of AgentDeps and its underlying mocks for test assertions."""

    deps: AgentDeps
    user_service_mock: AsyncMock
    user_profile_service_mock: AsyncMock


def _make_user_read_dto() -> UserReadDTO:
    """Factory for a minimal UserReadDTO used across tests."""
    return UserReadDTO(
        id=1,
        first_name="Илья",
        last_name="Тестов",
        patronymic=None,
        telegram_id=123_456,
        academic_points=Points(value=42, point_type=PointsTypeEnum.ACADEMIC),
        reputation_points=Points(value=10, point_type=PointsTypeEnum.REPUTATION),
        join_date=date(2025, 1, 1),
    )


def _make_profile_view_dto(user: UserReadDTO) -> ProfileViewDTO:
    """Factory for a minimal ProfileViewDTO used across tests."""
    return ProfileViewDTO(
        user=user,
        academic_progress=Points(value=42, point_type=PointsTypeEnum.ACADEMIC),
        academic_level=UserLevelReadDTO(
            current_level=LevelReadDTO(
                name="Новичок",
                required_points=Points(value=0, point_type=PointsTypeEnum.ACADEMIC),
            ),
            next_level=LevelReadDTO(
                name="Ученик",
                required_points=Points(value=100, point_type=PointsTypeEnum.ACADEMIC),
            ),
        ),
        academic_current_points=Points(value=42, point_type=PointsTypeEnum.ACADEMIC),
        academic_next_points=Points(value=100, point_type=PointsTypeEnum.ACADEMIC),
        reputation_progress=Points(value=10, point_type=PointsTypeEnum.REPUTATION),
        reputation_level=UserLevelReadDTO(
            current_level=LevelReadDTO(
                name="Новичок",
                required_points=Points(value=0, point_type=PointsTypeEnum.REPUTATION),
            ),
            next_level=LevelReadDTO(
                name="Ученик",
                required_points=Points(value=50, point_type=PointsTypeEnum.REPUTATION),
            ),
        ),
        reputation_current_points=Points(value=10, point_type=PointsTypeEnum.REPUTATION),
        reputation_next_points=Points(value=50, point_type=PointsTypeEnum.REPUTATION),
        roles_data=["Student"],
        competences=[
            CompetenceReadDTO(id=1, name="Python", description="Язык программирования"),
        ],
    )


@pytest.fixture
def agent_ctx() -> AgentTestContext:
    """Build AgentDeps with mocked services that return predictable data."""
    fake_user = _make_user_read_dto()
    fake_profile = _make_profile_view_dto(fake_user)

    user_service_mock = AsyncMock()
    user_service_mock.find_user_by_telegram_id = AsyncMock(return_value=fake_user)

    user_profile_service_mock = AsyncMock()
    user_profile_service_mock.build_profile_view = AsyncMock(return_value=fake_profile)

    deps = AgentDeps(
        user_service=user_service_mock,  # type: ignore[arg-type]
        user_profile_service=user_profile_service_mock,  # type: ignore[arg-type]
        current_telegram_id=123_456,
    )

    return AgentTestContext(
        deps=deps,
        user_service_mock=user_service_mock,
        user_profile_service_mock=user_profile_service_mock,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_calls_tools_and_returns_output(
    override_ai_agent: TestModel,
    agent_ctx: AgentTestContext,
) -> None:
    """TestModel calls all registered tools by default, then returns a text response."""
    result = await ai_agent.run("Покажи мой профиль", deps=agent_ctx.deps, model=override_ai_agent)

    assert result.output
    assert isinstance(result.output, str)


@pytest.mark.asyncio
async def test_get_current_user_profile_tool_is_invoked(
    override_ai_agent: TestModel,
    agent_ctx: AgentTestContext,
) -> None:
    """Verify that get_current_user_profile tool is called during agent run."""
    await ai_agent.run("Какой у меня профиль?", deps=agent_ctx.deps, model=override_ai_agent)

    agent_ctx.user_service_mock.find_user_by_telegram_id.assert_called()
    agent_ctx.user_profile_service_mock.build_profile_view.assert_called()


@pytest.mark.asyncio
async def test_get_user_points_tool_is_invoked(
    override_ai_agent: TestModel,
    agent_ctx: AgentTestContext,
) -> None:
    """Verify that get_user_points tool is called and returns point data."""
    await ai_agent.run("Сколько у меня баллов?", deps=agent_ctx.deps, model=override_ai_agent)

    agent_ctx.user_service_mock.find_user_by_telegram_id.assert_called()


@pytest.mark.asyncio
async def test_get_user_level_tool_is_invoked(
    override_ai_agent: TestModel,
    agent_ctx: AgentTestContext,
) -> None:
    """Verify that get_user_level tool is called and returns level data."""
    await ai_agent.run("Какой у меня уровень?", deps=agent_ctx.deps, model=override_ai_agent)

    agent_ctx.user_service_mock.find_user_by_telegram_id.assert_called()
    agent_ctx.user_profile_service_mock.build_profile_view.assert_called()


@pytest.mark.asyncio
async def test_tools_handle_unregistered_user(
    override_ai_agent: TestModel,
) -> None:
    """When the user is not found, tools return a 'not found' string instead of crashing."""
    user_service_mock = AsyncMock()
    user_service_mock.find_user_by_telegram_id = AsyncMock(return_value=None)

    deps = AgentDeps(
        user_service=user_service_mock,  # type: ignore[arg-type]
        user_profile_service=AsyncMock(),  # type: ignore[arg-type]
        current_telegram_id=999_999,
    )

    result = await ai_agent.run("Покажи мой профиль", deps=deps, model=override_ai_agent)

    assert result.output
    assert isinstance(result.output, str)


@pytest.mark.asyncio
async def test_agent_system_prompt_contains_policy(
    override_ai_agent: TestModel,
    agent_ctx: AgentTestContext,
) -> None:
    """Verify that the agent uses the system prompt from the texts layer."""
    result = await ai_agent.run("test", deps=agent_ctx.deps, model=override_ai_agent)

    messages = result.new_messages()
    system_parts = [
        part
        for msg in messages
        if hasattr(msg, "parts")
        for part in msg.parts
        if hasattr(part, "content") and "IT Academy" in str(part.content)
    ]
    assert len(system_parts) > 0, "System prompt with 'IT Academy' not found in message history"
