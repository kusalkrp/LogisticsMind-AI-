"""Long-term memory stored in PostgreSQL."""
import asyncio
import json
import logging
import os
import asyncpg

from agent.core.llm import get_llm
from agent.prompts.memory_extract import MEMORY_EXTRACTION_PROMPT


async def get_db():
    url = os.environ.get(
        "DATABASE_URL_SYNC",
        "postgresql://user:password@postgres:5432/ceylog"
    )
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    return await asyncpg.connect(url)


class MemoryStore:
    def __init__(self, user_id: str):
        self.user_id = user_id

    async def get_facts(self) -> list[str]:
        conn = await get_db()
        try:
            rows = await conn.fetch("""
                SELECT fact FROM analyst_facts
                WHERE user_id = $1
                ORDER BY updated_at DESC
                LIMIT 20
            """, self.user_id)
            return [r["fact"] for r in rows]
        finally:
            await conn.close()

    async def get_recent_sessions(self, limit: int = 3) -> list[str]:
        conn = await get_db()
        try:
            rows = await conn.fetch("""
                SELECT summary FROM analyst_sessions
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, self.user_id, limit)
            return [r["summary"] for r in rows]
        finally:
            await conn.close()

    async def upsert_facts(self, facts: list[str]):
        conn = await get_db()
        try:
            for fact in facts:
                await conn.execute("""
                    INSERT INTO analyst_facts (user_id, fact, updated_at)
                    VALUES ($1, $2, NOW())
                    ON CONFLICT (user_id, fact)
                    DO UPDATE SET updated_at = NOW()
                """, self.user_id, fact)
        finally:
            await conn.close()

    async def save_session_summary(self, summary: str, topics: list[str]):
        conn = await get_db()
        try:
            await conn.execute("""
                INSERT INTO analyst_sessions (user_id, summary, topics, created_at)
                VALUES ($1, $2, $3, NOW())
            """, self.user_id, summary, topics)
        finally:
            await conn.close()


async def extract_and_store(user_id: str, history: list):
    """
    Runs after each session ends (fire-and-forget).
    Extracts facts + session summary and stores to PostgreSQL.
    """
    try:
        if not history:
            return
        # Serialize history into a single user message to avoid Gemini turn-ordering issues
        transcript = "\n".join(
            f"{m['role'].upper()}: {m.get('content', '')}"
            for m in history
            if m.get("content")
        )
        raw = await get_llm().generate(
            system=MEMORY_EXTRACTION_PROMPT,
            messages=[{"role": "user", "content": f"Conversation to analyse:\n\n{transcript}"}],
            tier="flash"
        )
        if not raw or not raw.strip():
            return
        clean = raw.replace("```json", "").replace("```", "").strip()
        # Find the JSON object within the response
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start == -1 or end == 0:
            return
        data = json.loads(clean[start:end])
        store = MemoryStore(user_id)

        if data.get("facts"):
            await store.upsert_facts(data["facts"])

        if data.get("session_summary"):
            await store.save_session_summary(
                summary=data["session_summary"],
                topics=data.get("topics", [])
            )
    except Exception as e:
        logging.warning(f"Memory extraction failed for {user_id}: {e}")
