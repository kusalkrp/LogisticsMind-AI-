"""Health check endpoint."""
import os
from fastapi import APIRouter
import asyncpg
import redis.asyncio as aioredis

router = APIRouter()


@router.get("/health")
async def health():
    pg_ok = False
    redis_ok = False

    try:
        url = os.environ.get("DATABASE_URL_SYNC", "postgresql://user:password@postgres:5432/ceylog")
        url = url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(url)
        await conn.fetchval("SELECT 1")
        await conn.close()
        pg_ok = True
    except Exception:
        pass

    try:
        r = aioredis.from_url(
            os.environ.get("REDIS_URL", "redis://redis:6379/0"),
            decode_responses=True
        )
        await r.ping()
        await r.close()
        redis_ok = True
    except Exception:
        pass

    return {
        "status": "ok" if (pg_ok and redis_ok) else "degraded",
        "postgres": pg_ok,
        "redis": redis_ok,
    }
