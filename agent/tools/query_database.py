"""NL → SQL → execute → results."""
import asyncpg
import os
import re
from agent.core.llm import get_llm
from agent.schema_context import SCHEMA_CONTEXT

SQL_SYSTEM = f"""
You are a PostgreSQL expert for the CeyLog logistics database.

{SCHEMA_CONTEXT}

Rules:
- Always schema-qualify table names: core.companies, fleet.trips, etc.
- Never SELECT * — name columns explicitly
- Add LIMIT 500 unless aggregating
- Default time range: last 90 days if none specified
- For district names always JOIN core.districts
- Prefer CTEs for multi-step queries
- Return ONLY the raw SQL query — no explanation, no markdown fences
"""

FORBIDDEN_KEYWORDS = ["DELETE", "UPDATE", "DROP", "INSERT", "CREATE", "ALTER", "TRUNCATE"]


async def _get_conn():
    url = os.environ.get("DATABASE_URL_SYNC", "postgresql://user:password@postgres:5432/ceylog")
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    return await asyncpg.connect(url)


async def query_database(question: str, time_range_days: str = "90") -> dict:
    sql = await get_llm().generate(
        system=SQL_SYSTEM,
        messages=[{"role": "user", "content":
            f"Write SQL to answer: {question}\nTime range: last {time_range_days} days"
        }],
        tier="flash"
    )
    sql = sql.strip().replace("```sql", "").replace("```", "").strip()

    sql_upper = sql.upper()
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", sql_upper):
            return {"success": False, "error": f"Unsafe operation detected: {kw}", "sql": sql, "rows": []}

    return await _execute_with_retry(sql, question)


async def _execute_with_retry(sql: str, original_question: str) -> dict:
    conn = await _get_conn()
    try:
        rows = await conn.fetch(sql)
        columns = list(rows[0].keys()) if rows else []
        data = [_serialize_row(r) for r in rows]
        return {"success": True, "sql": sql, "columns": columns, "rows": data, "row_count": len(data)}
    except Exception as e:
        await conn.close()
        fixed_sql = await get_llm().generate(
            system=SQL_SYSTEM,
            messages=[
                {"role": "user", "content": f"Write SQL for: {original_question}"},
                {"role": "assistant", "content": sql},
                {"role": "user", "content": f"That query failed with: {str(e)}\nFix the SQL."},
            ],
            tier="flash"
        )
        fixed_sql = fixed_sql.strip().replace("```sql", "").replace("```", "").strip()
        conn2 = await _get_conn()
        try:
            rows = await conn2.fetch(fixed_sql)
            columns = list(rows[0].keys()) if rows else []
            data = [_serialize_row(r) for r in rows]
            return {"success": True, "sql": fixed_sql, "columns": columns, "rows": data, "row_count": len(data)}
        except Exception as e2:
            return {"success": False, "sql": fixed_sql, "error": str(e2), "rows": []}
        finally:
            await conn2.close()
    finally:
        try:
            await conn.close()
        except Exception:
            pass


def _serialize_row(row) -> dict:
    """Convert asyncpg Record to JSON-safe dict."""
    import datetime
    import decimal
    import uuid as _uuid
    result = {}
    for k, v in dict(row).items():
        if isinstance(v, (datetime.datetime, datetime.date)):
            result[k] = v.isoformat()
        elif isinstance(v, decimal.Decimal):
            result[k] = float(v)
        elif isinstance(v, _uuid.UUID):
            result[k] = str(v)
        else:
            result[k] = v
    return result
