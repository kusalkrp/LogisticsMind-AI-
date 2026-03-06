"""User style detection — adapts responses to analyst preferences."""
import json
from agent.core.llm import get_llm


async def detect_style(history: list, current_style: dict) -> dict:
    """
    Detects the analyst's communication preferences.
    Only re-runs every 5 turns — cached in session.
    """
    if current_style and len(history) % 5 != 0:
        return current_style

    if len(history) < 2:
        return {
            "formality": "casual",
            "detail_preference": "detailed",
            "prefers_charts": True
        }

    user_messages = [
        m["content"] for m in history[-6:]
        if m.get("role") == "user"
    ][:3]

    result = await get_llm().generate(
        system="""Analyse these messages from a data analyst.
        Return ONLY valid JSON:
        {
          "formality": "formal|casual",
          "detail_preference": "brief|detailed",
          "prefers_charts": true|false
        }""",
        messages=[{"role": "user", "content": "\n".join(user_messages)}],
        tier="flash"
    )

    try:
        return json.loads(result.replace("```json", "").replace("```", "").strip())
    except Exception:
        return current_style or {
            "formality": "casual",
            "detail_preference": "detailed",
            "prefers_charts": True
        }
