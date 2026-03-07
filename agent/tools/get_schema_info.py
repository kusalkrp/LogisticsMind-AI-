"""Schema introspection tool — returns relevant table info."""
from agent.core.llm import get_llm
from agent.schema_context import SCHEMA_CONTEXT


async def get_schema_info(topic: str) -> dict:
    result = await get_llm().generate(
        system=f"""You are a database documentation expert.
Given the following schema, answer questions about table structures,
columns, relationships, and query patterns.

{SCHEMA_CONTEXT}

Return a clear, structured answer with:
1. Relevant table(s) and their key columns
2. Important relationships (foreign keys)
3. Sample query patterns for common questions about this topic
""",
        messages=[{"role": "user", "content":
            f"What tables and columns are relevant for: {topic}"
        }],
        tier="flash"
    )

    return {
        "success": True,
        "topic": topic,
        "info": result,
    }
