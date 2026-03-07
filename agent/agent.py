"""LogisticsMindAgent — main entry point."""
import logging
from dataclasses import dataclass
from agent.core.pipeline import build_pipeline
from agent.core.cache import get_cached, set_cached


@dataclass
class AgentResponse:
    message: str
    tools_used: list[dict]
    proactive: str | None
    thinking: str | None  # inner monologue — debug only
    cached: bool = False

    def __str__(self):
        return self.message


class LogisticsMindAgent:
    """
    Main agent entry point.
    Usage:
        agent = LogisticsMindAgent()
        response = await agent.chat(user_id="analyst_1", message="show me delays")
    """

    def __init__(self, debug: bool = False):
        self.debug = debug
        self._pipeline = None

    def _get_pipeline(self):
        if self._pipeline is None:
            self._pipeline = build_pipeline()
        return self._pipeline

    async def chat(self, user_id: str, message: str) -> AgentResponse:
        # Check cache first (skips context-dependent follow-ups automatically)
        cached = await get_cached(message)
        if cached:
            logging.info(f"Cache hit for: {message[:60]}")
            return AgentResponse(
                message=cached["message"],
                tools_used=cached["tools_used"],
                proactive=cached.get("proactive"),
                thinking=None,
                cached=True,
            )

        initial_state = {
            "user_id": user_id,
            "message": message,
            "history": [],
            "style": {},
            "turn_count": 0,
            "memory_context": "",
            "monologue": "",
            "tool_calls": [],
            "tool_context": "",
            "final_response": "",
            "proactive": None,
        }

        result = await self._get_pipeline().ainvoke(initial_state)

        response = AgentResponse(
            message=result["final_response"],
            tools_used=result["tool_calls"],
            proactive=result["proactive"],
            thinking=result["monologue"] if self.debug else None,
        )

        # Store in cache for future identical questions
        await set_cached(message, {
            "message": response.message,
            "tools_used": response.tools_used,
            "proactive": response.proactive,
        })

        return response

    async def reset(self, user_id: str):
        from agent.core.session import SessionManager
        await SessionManager(user_id).clear()
