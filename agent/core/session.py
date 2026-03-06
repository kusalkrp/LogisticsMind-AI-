"""Redis-backed session manager."""
import json
import os
import redis.asyncio as aioredis
from agent.core.trimmer import smart_trim

SESSION_TTL = 3600   # 1 hour inactivity = new session
MAX_TURNS = 15
TRIM_OLDEST = 10

_redis = None


async def get_redis():
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            os.environ.get("REDIS_URL", "redis://redis:6379/0"),
            decode_responses=True
        )
    return _redis


class SessionManager:
    def __init__(self, user_id: str):
        self.key = f"logisticsmind:session:{user_id}"

    async def load(self) -> dict:
        redis = await get_redis()
        raw = await redis.get(self.key)
        if raw:
            return json.loads(raw)
        return {
            "history": [],
            "style": {},
            "turn_count": 0,
        }

    async def save(self, session: dict):
        if len(session["history"]) > MAX_TURNS:
            session["history"] = await smart_trim(
                session["history"],
                keep_latest=MAX_TURNS - TRIM_OLDEST
            )
        redis = await get_redis()
        await redis.setex(self.key, SESSION_TTL, json.dumps(session))

    async def clear(self):
        redis = await get_redis()
        await redis.delete(self.key)
