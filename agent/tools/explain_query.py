"""Show generated SQL without executing it."""
from agent.core.llm import get_llm
from agent.schema_context import SCHEMA_CONTEXT

SQL_SYSTEM = f"""
You are a PostgreSQL expert for the CeyLog logistics database.

{SCHEMA_CONTEXT}

Rules:
- Always schema-qualify table names
- Never SELECT * — name columns explicitly
- Add LIMIT 500 unless aggregating
- Return ONLY the raw SQL query — no explanation, no markdown fences
"""


async def explain_query(question: str) -> dict:
    sql = await get_llm().generate(
        system=SQL_SYSTEM,
        messages=[{"role": "user", "content": f"Write SQL to answer: {question}"}],
        tier="flash"
    )
    sql = sql.strip().replace("```sql", "").replace("```", "").strip()

    explanation = await get_llm().generate(
        system="You are a SQL expert. Explain the following SQL query in plain English, clause by clause. Be concise.",
        messages=[{"role": "user", "content": f"Explain this SQL:\n{sql}"}],
        tier="flash"
    )

    return {
        "success": True,
        "sql": sql,
        "explanation": explanation,
        "question": question,
    }
