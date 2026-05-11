from aiogram.filters import Command
from aiogram.types import Message
from dishka.integrations.aiogram import FromDishka
from pydantic_ai.models import Model

from .....presentation.shared.ai_agent import AgentDeps, ai_agent
from .....services import PointsService, UserProfileService, UserService
from ...filters import create_chat_type_routers

# TODO Рефакторинг: код иишки
ai_agent_private_router, ai_agent_group_router, ai_agent_global_router = create_chat_type_routers("ai_agent")


@ai_agent_private_router.message(Command("ai", "ask"))
async def handle_ai_command(
    message: Message,
    user_service: FromDishka[UserService],
    user_profile_service: FromDishka[UserProfileService],
    points_service: FromDishka[PointsService],
    model: FromDishka[Model],
) -> None:
    """Обрабатывает запросы к ИИ-агенту.

    Собирает контекст (зависимости), обращается к агенту и возвращает текстовый ответ.
    """
    if not message.text or not message.from_user:
        return

    # TODO Рефактор: В отдельную функцию
    # Извлекаем текст запроса (убираем команду /ai)
    query = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    if not query:
        await message.answer("Пожалуйста, напишите свой вопрос после команды /ai.")
        return

    # TODO добавить Provider для этого объекта в Dishka.
    # Формируем зависимости для агента
    deps = AgentDeps(
        user_service=user_service,
        user_profile_service=user_profile_service,
        points_service=points_service,
        current_telegram_id=message.from_user.id,
    )

    try:
        # Отправляем индикатор набора текста
        await message.chat.do("typing")

        # Запускаем агента
        result = await ai_agent.run(
            query,
            deps=deps,
            model=model,
        )
        # TODO добавить функцию для нормализации вывода ИИ-шки, либо добавить это в системный промпт
        await message.answer(result.output)
    except Exception as e:
        await message.answer(f"Произошла ошибка при обращении к ИИ: {e}")
