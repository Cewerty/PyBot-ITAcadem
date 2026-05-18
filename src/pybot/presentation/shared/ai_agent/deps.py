from dataclasses import dataclass

from pybot.services.user_services import UserProfileService, UserService


# TODO Рефакторинг: подумать как это можно реализовать через общие интерфейсы в DI
@dataclass
class AgentDeps:
    """Dependencies for the AI Agent."""

    user_service: UserService
    user_profile_service: UserProfileService
    current_telegram_id: int
