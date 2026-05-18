from aiogram import Router, F

from ...filters import create_chat_type_routers

from .ai_handler import ai_agent_private_router

ai_private_router, ai_group_router, ai_global_router = create_chat_type_routers("ai")

ai_private_router.include_router(ai_agent_private_router)

ai_router = Router(name="ai")
ai_router.include_routers(
    ai_private_router,
    ai_group_router,
    ai_global_router,
)
