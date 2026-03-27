from datetime import date

import pytest

from pybot.core.constants import PointsTypeEnum
from pybot.dto import CompetenceReadDTO, LevelReadDTO, ProfileViewDTO, UserCreateDTO, UserLevelReadDTO, UserReadDTO
from pybot.dto.value_objects import Points
from pybot.domain.exceptions import NameInputValidationError
from pybot.utils import progress_bar


def test_validate_name_input_returns_clean_value_for_valid_name() -> None:
    result = UserCreateDTO.validate_name_input("  Иван  ")

    assert result == "Иван"


def test_validate_name_input_rejects_invalid_symbols() -> None:
    with pytest.raises(NameInputValidationError) as exc_info:
        UserCreateDTO.validate_name_input("Иван123")

    assert exc_info.value.reason == "invalid_symbols"


def test_validate_name_input_returns_none_for_empty_optional_value() -> None:
    result = UserCreateDTO.validate_name_input("   ", allow_empty=True)

    assert result is None


def test_validate_name_input_rejects_too_long_name() -> None:
    with pytest.raises(NameInputValidationError) as exc_info:
        UserCreateDTO.validate_name_input("И" * (UserCreateDTO.NAME_MAX_LENGTH + 1))

    assert exc_info.value.reason == "too_long"
    assert exc_info.value.max_length == UserCreateDTO.NAME_MAX_LENGTH


def test_profile_view_dto_builds_progress_bars_from_points_data() -> None:
    profile_view = ProfileViewDTO(
        user=UserReadDTO(
            id=1,
            first_name="Иван",
            last_name="Иванов",
            patronymic=None,
            telegram_id=123_456,
            academic_points=Points(value=80, point_type=PointsTypeEnum.ACADEMIC),
            reputation_points=Points(value=30, point_type=PointsTypeEnum.REPUTATION),
            join_date=date(2025, 1, 1),
        ),
        academic_progress=Points(value=80, point_type=PointsTypeEnum.ACADEMIC),
        academic_level=UserLevelReadDTO(
            current_level=LevelReadDTO(
                name="A1",
                required_points=Points(value=50, point_type=PointsTypeEnum.ACADEMIC),
            ),
            next_level=LevelReadDTO(
                name="A2",
                required_points=Points(value=100, point_type=PointsTypeEnum.ACADEMIC),
            ),
        ),
        academic_current_points=Points(value=30, point_type=PointsTypeEnum.ACADEMIC),
        academic_next_points=Points(value=50, point_type=PointsTypeEnum.ACADEMIC),
        reputation_progress=Points(value=30, point_type=PointsTypeEnum.REPUTATION),
        reputation_level=UserLevelReadDTO(
            current_level=LevelReadDTO(
                name="R1",
                required_points=Points(value=20, point_type=PointsTypeEnum.REPUTATION),
            ),
            next_level=LevelReadDTO(
                name="R2",
                required_points=Points(value=60, point_type=PointsTypeEnum.REPUTATION),
            ),
        ),
        reputation_current_points=Points(value=10, point_type=PointsTypeEnum.REPUTATION),
        reputation_next_points=Points(value=40, point_type=PointsTypeEnum.REPUTATION),
        roles_data=["Student"],
        competences=[CompetenceReadDTO(id=1, name="Python", description="Backend")],
    )

    assert profile_view.academic_progress_bar == progress_bar(30, 50)
    assert profile_view.reputation_progress_bar == progress_bar(10, 40)
