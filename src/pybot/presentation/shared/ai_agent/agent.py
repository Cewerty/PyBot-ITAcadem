from pydantic_ai import Agent, RunContext

from pybot.dto import ProfileViewDTO

from .deps import AgentDeps

# TODO Рефакторить этот ИИ код
ai_agent = Agent(
    deps_type=AgentDeps,
    system_prompt=(
        "You are a helpful AI assistant for an IT Academy platform. "
        "You can help students check their profile, balance, and levels. "
        "Always be polite and concise. Use tools to get real data."
    ),
)


@ai_agent.tool
async def get_current_user_profile(ctx: RunContext[AgentDeps]) -> ProfileViewDTO | str:
    """Get the full profile data of the current user, including their academic and reputation points, level, and roles.

    Call this tool when the user asks about their balance, points, level, or general profile information.
    """
    user_read = await ctx.deps.user_service.find_user_by_telegram_id(ctx.deps.current_telegram_id)
    if not user_read:
        return "User not found in the system. They might need to register first."

    profile_view = await ctx.deps.user_profile_service.build_profile_view(user_read)
    return profile_view
