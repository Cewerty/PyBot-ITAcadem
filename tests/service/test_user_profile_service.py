from __future__ import annotations

import pytest
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from pybot.core.constants import PointsTypeEnum
from pybot.domain.exceptions import LevelNotFoundError
from pybot.mappers.user_mappers import map_orm_user_to_user_read_dto
from pybot.services import UserProfileService
from tests.factories.model_factories import UserSpec, attach_user_level, create_level, create_user


@pytest.mark.asyncio
async def test_build_profile_view_returns_profile_data_with_user_progress(
    dishka_request_container: AsyncContainer,
) -> None:
    db_session = await dishka_request_container.get(AsyncSession)
    user_profile_service = await dishka_request_container.get(UserProfileService)

    user = await create_user(
        db_session,
        spec=UserSpec(
            telegram_id=700_321,
            first_name="Ilya",
            academic_points=120,
            reputation_points=40,
        ),
    )
    academic_current = await create_level(
        db_session,
        name="Scholar",
        level_type=PointsTypeEnum.ACADEMIC,
        required_points=100,
    )
    await create_level(
        db_session,
        name="Expert",
        level_type=PointsTypeEnum.ACADEMIC,
        required_points=200,
    )
    reputation_current = await create_level(
        db_session,
        name="Known",
        level_type=PointsTypeEnum.REPUTATION,
        required_points=20,
    )
    await create_level(
        db_session,
        name="Trusted",
        level_type=PointsTypeEnum.REPUTATION,
        required_points=80,
    )
    await attach_user_level(db_session, user=user, level=academic_current)
    await attach_user_level(db_session, user=user, level=reputation_current)
    await db_session.commit()

    user_read = await map_orm_user_to_user_read_dto(user)

    profile_view = await user_profile_service.build_profile_view(user_read)

    assert profile_view.user.telegram_id == user.telegram_id
    assert profile_view.user.first_name == "Ilya"
    assert profile_view.academic_level.current_level.name == "Scholar"
    assert profile_view.reputation_level.current_level.name == "Known"
    assert profile_view.academic_progress.value == 120
    assert profile_view.reputation_progress.value == 40
    assert profile_view.academic_current_points.value == 20
    assert profile_view.academic_next_points.value == 100
    assert profile_view.reputation_current_points.value == 20
    assert profile_view.reputation_next_points.value == 60
    assert profile_view.academic_progress_bar
    assert profile_view.reputation_progress_bar


@pytest.mark.asyncio
async def test_build_profile_view_raises_when_some_level_track_is_missing(
    dishka_request_container: AsyncContainer,
) -> None:
    db_session = await dishka_request_container.get(AsyncSession)
    user_profile_service = await dishka_request_container.get(UserProfileService)

    user = await create_user(
        db_session,
        spec=UserSpec(
            telegram_id=700_654,
            first_name="Mira",
            academic_points=50,
            reputation_points=30,
        ),
    )
    academic_current = await create_level(
        db_session,
        name="Scholar",
        level_type=PointsTypeEnum.ACADEMIC,
        required_points=0,
    )
    await attach_user_level(db_session, user=user, level=academic_current)
    await db_session.commit()

    user_read = await map_orm_user_to_user_read_dto(user)

    with pytest.raises(LevelNotFoundError, match="Уровень не найден"):
        await user_profile_service.build_profile_view(user_read)
