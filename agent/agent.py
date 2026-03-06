"""LogisticsMindAgent — main entry point."""
from dataclasses import dataclass
from agent.core.pipeline import build_pipeline


@dataclass
class AgentResponse:
    message: str
    tools_used: list[dict]
    proactive: str | None
    thinking: str | None  # inner monologue — debug only

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

        return AgentResponse(
            message=result["final_response"],
            tools_used=result["tool_calls"],
            proactive=result["proactive"],
            thinking=result["monologue"] if self.debug else None,
        )

    async def reset(self, user_id: str):
        from agent.core.session import SessionManager
        await SessionManager(user_id).clear()
