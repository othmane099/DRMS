import json
import logging
from typing import Protocol

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_CHAT_TTL = 86_400  # 24 hours
_MAX_MESSAGES = 20  # keep last 20 messages


class ChatStoreService(Protocol):
    async def load_history(
        self, document_id: str, version_id: str, user_id: str
    ) -> list[dict[str, str]]: ...

    async def save_history(
        self,
        document_id: str,
        version_id: str,
        user_id: str,
        messages: list[dict[str, str]],
    ) -> None: ...


class ChatStoreServiceImpl(ChatStoreService):
    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    def _key(self, document_id: str, version_id: str, user_id: str) -> str:
        return f"doc_chat:{document_id}:{version_id}:{user_id}"

    async def load_history(
        self, document_id: str, version_id: str, user_id: str
    ) -> list[dict[str, str]]:
        raw = await self._redis.get(self._key(document_id, version_id, user_id))
        return json.loads(raw) if raw else []

    async def save_history(
        self,
        document_id: str,
        version_id: str,
        user_id: str,
        messages: list[dict[str, str]],
    ) -> None:
        trimmed = messages[-_MAX_MESSAGES:]
        await self._redis.set(
            self._key(document_id, version_id, user_id),
            json.dumps(trimmed),
            ex=_CHAT_TTL,
        )
