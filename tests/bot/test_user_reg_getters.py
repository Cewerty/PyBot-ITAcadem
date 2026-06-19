from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import cast

import pytest
from aiogram_dialog import DialogManager

from pybot.presentation.bot import get_registration_competencies


@dataclass(slots=True)
class StubDialogManager:
    dialog_data: dict[str, object] = field(default_factory=dict)


@pytest.mark.asyncio
async def test_get_registration_competencies_returns_options_from_dialog_data() -> None:
    manager = StubDialogManager(
        dialog_data={
            "registration_competencies": [
                {"id": 1, "name": "Python"},
                {"id": 2, "name": "SQL"},
            ]
        }
    )

    result = await get_registration_competencies(cast(DialogManager, manager))

    assert result == {
        "registration_competencies": [
            {"id": 1, "name": "Python"},
            {"id": 2, "name": "SQL"},
        ]
    }


@pytest.mark.asyncio
async def test_get_registration_competencies_keeps_options_after_json_round_trip() -> None:
    dialog_data = {
        "registration_competencies": [
            {"id": 1, "name": "Python"},
            {"id": 2, "name": "SQL"},
        ]
    }
    restored_dialog_data = json.loads(json.dumps(dialog_data))
    manager = StubDialogManager(dialog_data=restored_dialog_data)

    result = await get_registration_competencies(cast(DialogManager, manager))

    assert result == dialog_data


@pytest.mark.asyncio
async def test_get_registration_competencies_filters_invalid_entries() -> None:
    manager = StubDialogManager(
        dialog_data={
            "registration_competencies": [
                {"id": 1, "name": "Python"},
                {"id": "2", "name": "SQL"},
                {"id": 3, "name": 100},
                {"id": 4},
                {"name": "Docker"},
                (5, "Legacy tuple"),
                [6, "Legacy list"],
            ]
        }
    )

    result = await get_registration_competencies(cast(DialogManager, manager))

    assert result == {"registration_competencies": [{"id": 1, "name": "Python"}]}
