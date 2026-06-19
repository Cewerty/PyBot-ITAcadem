"""Модуль бота IT Academ."""

from typing import TypedDict

from aiogram_dialog import DialogManager


class RegistrationCompetenceOption(TypedDict):
    id: int
    name: str


async def get_registration_competencies(
    dialog_manager: DialogManager,
    **kwargs: object,
) -> dict[str, list[RegistrationCompetenceOption]]:
    """Вспомогательная функция get_registration_competencies."""
    del kwargs
    raw_options = dialog_manager.dialog_data.get("registration_competencies")
    return {"registration_competencies": _normalize_competence_options(raw_options)}


def _normalize_competence_options(raw_options: object) -> list[RegistrationCompetenceOption]:
    if not isinstance(raw_options, list):
        return []

    normalized_options: list[RegistrationCompetenceOption] = []
    for option in raw_options:
        match option:
            case {"id": int(competence_id), "name": str(competence_name)}:
                normalized_options.append({"id": competence_id, "name": competence_name})

    return normalized_options
