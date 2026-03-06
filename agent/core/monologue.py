"""Inner monologue engine — private reasoning before response."""
import re
from agent.core.llm import get_llm
from agent.prompts.monologue import MONOLOGUE_PROMPT


async def run_inner_monologue(
    system: str,
    history: list,
    message: str,
) -> tuple[str, str]:
    """
    Runs private reasoning before generating a response.
    Returns: (monologue_text, clean_response_without_think_tags)
    """
    full_system = system + "\n\n" + MONOLOGUE_PROMPT
    full_history = history + [{"role": "user", "content": message}]

    raw = await get_llm().generate(
        system=full_system,
        messages=full_history,
        tier="flash"
    )

    think_match = re.search(r"<think>(.*?)</think>", raw, re.DOTALL)
    monologue = think_match.group(1).strip() if think_match else ""

    clean = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    return monologue, clean
