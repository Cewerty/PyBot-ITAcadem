from pydantic_ai import Agent, RunContext

from ....dto import ProfileViewDTO

# System prompt is defined in the texts layer (single source of truth for user-facing content).
from ...texts.texts import AI_SYSTEM_PROMPT
from .deps import AgentDeps

ai_agent = Agent(
    deps_type=AgentDeps,
    system_prompt=AI_SYSTEM_PROMPT,
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


@ai_agent.tool
async def get_user_points(ctx: RunContext[AgentDeps]) -> str:
    """Get only the current point balances (academic and reputation) of the user.

    Call this tool when the user asks specifically about their points or balance,
    without needing full profile details like level, roles, or competences.
    """
    user_read = await ctx.deps.user_service.find_user_by_telegram_id(ctx.deps.current_telegram_id)
    if not user_read:
        return "User not found in the system. They might need to register first."

    return f"Academic points: {user_read.academic_points.value}, Reputation points: {user_read.reputation_points.value}"


@ai_agent.tool
async def get_user_level(ctx: RunContext[AgentDeps]) -> str:
    """Get the current academic and reputation levels of the user.

    Call this tool when the user asks specifically about their level or rank,
    without needing full profile details like points breakdown or competences.
    """
    user_read = await ctx.deps.user_service.find_user_by_telegram_id(ctx.deps.current_telegram_id)
    if not user_read:
        return "User not found in the system. They might need to register first."

    profile_view = await ctx.deps.user_profile_service.build_profile_view(user_read)
    return (
        f"Academic level: {profile_view.academic_level.current_level.name}, "
        f"Reputation level: {profile_view.reputation_level.current_level.name}"
    )
