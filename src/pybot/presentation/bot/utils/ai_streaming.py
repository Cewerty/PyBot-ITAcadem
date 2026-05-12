"""Utilities for AI response streaming in Telegram."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiogram import Bot
    from pydantic_ai.result import StreamedRunResult


# TODO рефактор этот код
async def stream_ai_response(
    bot: Bot,
    chat_id: int,
    stream: StreamedRunResult,
    debounce_s: float = 0.25,
) -> str:
    """
    Stream AI response text to a Telegram chat using native sendMessageDraft.

    Args:
        bot: The bot instance.
        chat_id: Target chat ID.
        stream: The PydanticAI streamed result.
        debounce_s: Interval between draft updates in seconds.

    Returns:
        The full final text of the response.
    """
    draft_id = _generate_draft_id()
    full_text = ""

    async for text_chunk in stream.stream_text(debounce_by=debounce_s):
        full_text = text_chunk
        await bot.send_message_draft(
            chat_id=chat_id,
            draft_id=draft_id,
            text=full_text,
        )

    return full_text


def _generate_draft_id() -> int:
    """Generate a stable 32-bit draft_id for the current streaming session."""
    return int(time.time() * 1000) % 2147483647
