"""Модуль бота IT Academ."""

from aiogram.filters import Command
from aiogram.types import Message
from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities.modes import StartMode
from dishka.integrations.aiogram import FromDishka

from .....dto import UserReadDTO
from .....services.user_services import UserProfileService, UserService
from ....texts import PROFILE_GROUP_REGISTRATION_REQUIRED, render_profile_message
from ...dialogs.user_reg.states import CreateProfileSG
from ...filters import create_chat_type_routers

user_profile_private_router, user_profile_group_router, user_profile_global_router = create_chat_type_routers(
    "user_profile"
)


# /profile - в личном чате
@user_profile_private_router.message(Command("profile"))
async def cmd_profile_private(
    message: Message,
    dialog_manager: DialogManager,
    user_service: FromDishka[UserService],
    user_profile_service: FromDishka[UserProfileService],
) -> None:
    """Обработчик команды /profile_private."""
    if message.from_user:
        user = await user_service.find_user_by_telegram_id(message.from_user.id)
        if user:
            await _answer_profile(message, user, user_profile_service)
            return

    await dialog_manager.start(CreateProfileSG.welcome, mode=StartMode.RESET_STACK)


# /profile - в группе или супергруппе
@user_profile_group_router.message(Command("profile"))
async def cmd_profile_group(
    message: Message,
    user_service: FromDishka[UserService],
    user_profile_service: FromDishka[UserProfileService],
) -> None:
    """Обработчик публичного self-profile в группах."""
    if not message.from_user:
        await message.answer(PROFILE_GROUP_REGISTRATION_REQUIRED)
        return

    user = await user_service.find_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer(PROFILE_GROUP_REGISTRATION_REQUIRED)
        return

    await _answer_profile(message, user, user_profile_service)


async def _answer_profile(
    message: Message,
    user: UserReadDTO,
    user_profile_service: UserProfileService,
) -> None:
    user_profile_dto = await user_profile_service.build_profile_view(user)
    await message.answer(render_profile_message(user_profile_dto), parse_mode="HTML")
