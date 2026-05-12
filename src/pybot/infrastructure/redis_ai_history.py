"""Redis implementation of AI history port."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import TypeAdapter
from pydantic_ai.messages import ModelMessage

from ..services.ports.ai_history_port import AIHistoryPort

if TYPE_CHECKING:
    from redis.asyncio import Redis


# TODO Проверить код
class RedisAIHistoryAdapter(AIHistoryPort):
    """Redis-backed storage for AI conversation history."""

    def __init__(self, redis: Redis, ttl_seconds: int = 3600 * 24, history_limit: int = 20) -> None:
        """
        Initialize the adapter.

        Args:
            redis: Async Redis client.
            ttl_seconds: Expiration time for history keys.
            history_limit: Maximum number of messages to keep in history.
        """
        self._redis = redis
        self._ttl = ttl_seconds
        self._limit = history_limit
        self._adapter = TypeAdapter(list[ModelMessage])

    async def get_history(self, chat_id: int) -> list[ModelMessage]:
        """Load history from Redis and deserialize JSON."""
        raw_data = await self._redis.get(f"ai_history:{chat_id}")
        if not raw_data:
            return []
        return self._adapter.validate_json(raw_data)

    async def update_history(self, chat_id: int, messages: list[ModelMessage]) -> None:
        """Serialize history to JSON and save to Redis with TTL."""
        # Cap history to keep only the last N messages
        trimmed_messages = messages[-self._limit :]
        data = self._adapter.dump_json(trimmed_messages)
        await self._redis.set(f"ai_history:{chat_id}", data, ex=self._ttl)
