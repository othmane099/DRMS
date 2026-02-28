import json
import logging

import redis.asyncio as aioredis

from config import settings

logger = logging.getLogger(__name__)

_CHAT_TTL = 86_400  # 24 hours
_MAX_MESSAGES = 20  # keep last 20 messages


def _key(document_id: str, version_id: str, user_id: str) -> str:
    return f"doc_chat:{document_id}:{version_id}:{user_id}"


async def load_history(
    document_id: str, version_id: str, user_id: str
) -> list[dict[str, str]]:
    client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    async with client:
        raw = await client.get(_key(document_id, version_id, user_id))
        return json.loads(raw) if raw else []


async def save_history(
    document_id: str,
    version_id: str,
    user_id: str,
    messages: list[dict[str, str]],
) -> None:
    trimmed = messages[-_MAX_MESSAGES:]
    client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    async with client:
        await client.set(
            _key(document_id, version_id, user_id),
            json.dumps(trimmed),
            ex=_CHAT_TTL,
        )
