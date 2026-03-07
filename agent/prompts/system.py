"""System prompt builder — assembles context for the LLM."""
from agent.persona import LOGISTICSMIND_PERSONA


def build_system_prompt(state: dict) -> str:
    memory = state.get("memory_context", "")
    style = state.get("style", {})

    memory_section = ""
    if memory:
        memory_section = f"\n## What You Know About This Analyst\n{memory}"

    style_section = _style_instruction(style)

    proactive_rules = """
## Proactive Intelligence
After answering, ask yourself: "What will they ask next?"
If the answer is obvious — give it now without being asked.
If the data reveals something surprising — flag it proactively.
Wrap proactive additions in <proactive>...</proactive> tags.
Only do this when the value is genuinely high — not every turn.
"""

    return f"""
{LOGISTICSMIND_PERSONA}

## Communication Style
{style_section}

{memory_section}

{proactive_rules}

## Response Rules
1. Lead with the direct answer — numbers first, explanation second
2. Use actual values from the data — never say "significant" without a number
3. Never ask more than ONE follow-up question per response
4. When you use a tool, briefly explain what you're looking at and why
5. If a chart would make the answer clearer — call the generate_chart tool. NEVER output Mermaid diagrams, ASCII charts, or any diagram markup in your text. Charts must always be produced via the generate_chart tool.
6. After querying route, driver, warehouse, or time-series data with 3+ rows — always call generate_chart automatically without being asked.
7. For tabular data with many columns (e.g. full route lists) — use generate_chart with chart_type='table'. Do NOT write markdown tables manually.
""".strip()


def _style_instruction(style: dict) -> str:
    if not style:
        return "Be precise and data-driven. Use numbers. Keep it direct."

    detail = style.get("detail_preference", "detailed")
    formal = style.get("formality", "casual")
    charts = style.get("prefers_charts", True)

    parts = []
    parts.append("Detailed analytical responses." if detail == "detailed" else "Concise answers, key numbers only.")
    parts.append("Professional tone." if formal == "formal" else "Conversational but precise.")
    if charts:
        parts.append("Offer charts when they would clarify the data.")
    return " ".join(parts)
