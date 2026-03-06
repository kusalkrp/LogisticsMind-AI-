"""Context trimmer with LLM summarization."""
from agent.core.llm import get_llm
from agent.prompts.trim_summary import TRIM_SUMMARY_PROMPT


async def smart_trim(history: list, keep_latest: int = 5) -> list:
    """
    When history exceeds MAX_TURNS:
    - Take the oldest turns
    - Summarise them with LLM
    - Replace with a single summary node
    - Keep the latest N turns in full
    """
    if not history:
        return history

    oldest = history[:-keep_latest]
    latest = history[-keep_latest:]

    if not oldest:
        return latest

    summary = await get_llm().generate(
        system=TRIM_SUMMARY_PROMPT,
        messages=oldest,
        tier="flash"
    )

    summary_node = {
        "role": "system",
        "content": f"[Earlier conversation summary: {summary}]"
    }

    return [summary_node] + latest
