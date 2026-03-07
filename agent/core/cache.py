"""Two-layer query response cache.

L1 — Redis   : fast, 10-minute TTL, lost on restart
L2 — PostgreSQL : persistent, survives restarts, no expiry

Flow:
  read  → L1 hit → return immediately
        → L1 miss → L2 hit → repopulate L1 → return
        → L2 miss → run full pipeline → write both → return
  write → L1 (10 min TTL) + L2 (permanent, upsert)

Context-dependent follow-ups (e.g. "tell me more about that") are never cached.
"""
import hashlib
import json
import logging
import re

REDIS_TTL = 600  # 10 minutes

_CONTEXT_PATTERNS = re.compile(
    r"\b(that|those|them|it|they|the (route|driver|warehouse|company|vehicle|one|ones|result|chart|data) "
    r"(we|you|i) (discussed|mentioned|showed|found|looked at)|previous|above|earlier|last one|the same|"
    r"this route|that route|these routes|go deeper|drill down|investigate (it|that|them)|"
    r"tell me more|explain (that|it|more)|why (is|are|did|does) (it|that|this))\b",
    re.IGNORECASE,
)
_MIN_LENGTH = 25


def _cache_key(question: str) -> str:
    return hashlib.md5(question.lower().strip().encode()).hexdigest()


def _is_cacheable(question: str) -> bool:
    if len(question.strip()) < _MIN_LENGTH:
        return False
    if _CONTEXT_PATTERNS.search(question):
        return False
    return True


# ── L1: Redis ──────────────────────────────────────────────────────────────

async def _redis_get(key: str) -> dict | None:
    try:
        from agent.core.session import get_redis
        redis = await get_redis()
        raw = await redis.get(f"logisticsmind:qcache:{key}")
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def _redis_set(key: str, data: dict) -> None:
    try:
        from agent.core.session import get_redis
        redis = await get_redis()
        await redis.setex(f"logisticsmind:qcache:{key}", REDIS_TTL, json.dumps(data))
    except Exception:
        pass


# ── L2: PostgreSQL ─────────────────────────────────────────────────────────

async def _pg_get(key: str) -> dict | None:
    try:
        from agent.core.memory import get_db
        conn = await get_db()
        try:
            row = await conn.fetchrow(
                "SELECT response_json FROM analyst_query_cache WHERE question_hash = $1", key
            )
            if row:
                # Bump hit count asynchronously (fire and forget style)
                await conn.execute(
                    "UPDATE analyst_query_cache SET hit_count = hit_count + 1, last_hit_at = NOW() "
                    "WHERE question_hash = $1", key
                )
                return dict(row["response_json"])
        finally:
            await conn.close()
    except Exception as e:
        logging.debug(f"PG cache read failed: {e}")
    return None


async def _pg_set(key: str, question: str, data: dict) -> None:
    try:
        from agent.core.memory import get_db
        conn = await get_db()
        try:
            await conn.execute(
                """
                INSERT INTO analyst_query_cache (question_hash, question_text, response_json)
                VALUES ($1, $2, $3::jsonb)
                ON CONFLICT (question_hash) DO UPDATE
                    SET hit_count  = analyst_query_cache.hit_count + 1,
                        last_hit_at = NOW()
                """,
                key, question, json.dumps(data)
            )
        finally:
            await conn.close()
    except Exception as e:
        logging.debug(f"PG cache write failed: {e}")


# ── Public API ─────────────────────────────────────────────────────────────

async def get_cached(question: str) -> dict | None:
    if not _is_cacheable(question):
        return None
    key = _cache_key(question)

    # L1 — Redis
    hit = await _redis_get(key)
    if hit:
        logging.info(f"Cache L1 hit: {question[:60]}")
        return hit

    # L2 — PostgreSQL
    hit = await _pg_get(key)
    if hit:
        logging.info(f"Cache L2 hit: {question[:60]}")
        await _redis_set(key, hit)   # repopulate L1
        return hit

    return None


async def set_cached(question: str, response: dict) -> None:
    if not _is_cacheable(question):
        return
    key = _cache_key(question)
    await _redis_set(key, response)
    await _pg_set(key, question, response)
