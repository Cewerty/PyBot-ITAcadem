"""Port for AI conversation history persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic_ai.messages import ModelMessage


# TODO проверить код
class AIHistoryPort(ABC):
    """Protocol for AI message history storage."""

    @abstractmethod
    async def get_history(self, chat_id: int) -> list[ModelMessage]:
        """
        Load conversation history for a specific chat.

        Args:
            chat_id: Unique chat identifier.

        Returns:
            List of previously exchanged messages.
        """

    @abstractmethod
    async def update_history(self, chat_id: int, messages: list[ModelMessage]) -> None:
        """
        Update/save conversation history.

        Args:
            chat_id: Unique chat identifier.
            messages: Full updated list of messages.
        """
