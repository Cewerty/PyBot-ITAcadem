from aiogram import Bot
from aiogram.filters import Command
from aiogram.types import Message
from dishka.integrations.aiogram import FromDishka
from pydantic_ai.models import Model

from .....core import logger
from .....presentation.shared.ai_agent import AgentDeps, ai_agent
from .....services import UserProfileService, UserService
from .....services.ports import AIHistoryPort
from ...filters import create_chat_type_routers
from ...utils.ai_streaming import stream_ai_response

# TODO Рефакторинг: код иишки
ai_agent_private_router, ai_agent_group_router, ai_agent_global_router = create_chat_type_routers("ai_agent")


@ai_agent_private_router.message(Command("ai", "ask"))
async def handle_ai_command(  # noqa: PLR0913
    message: Message,
    bot: Bot,
    user_service: FromDishka[UserService],
    user_profile_service: FromDishka[UserProfileService],
    history_repo: FromDishka[AIHistoryPort],
    model: FromDishka[Model],
) -> None:
    """Обрабатывает запросы к ИИ-агенту с поддержкой истории и стриминга.

    Собирает контекст, загружает историю из Redis, запускает поток генерации
    и сохраняет обновленную историю.
    """
    # TODO Использовать для этого функцию-фильтр
    if not message.text or not message.from_user:
        return

    # TODO Выделить в отдельную функцию
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
        current_telegram_id=message.from_user.id,
    )

    try:
        # Отправляем индикатор набора текста
        await message.chat.do("typing")

        # Загружаем историю диалога
        history = await history_repo.get_history(message.chat.id)

        # Запускаем стрим через pydantic-ai
        # Почему-то сама full typed библиотека тут делает unknow
        async with ai_agent.run_stream(
            query,
            deps=deps,
            model=model,
            message_history=history,
        ) as result:
            # Стримим черновик через утилиту
            final_text = await stream_ai_response(
                bot=bot,
                chat_id=message.chat.id,
                stream=result,
            )

            # Сохраняем обновленную историю
            await history_repo.update_history(message.chat.id, result.new_messages())

            # Финализируем ответ обычным сообщением
            await message.answer(final_text)

    except Exception:
        logger.exception("AI agent error for chat_id=%s", message.chat.id)
        await message.answer("Произошла ошибка при обращении к ИИ. Попробуйте позже.")
